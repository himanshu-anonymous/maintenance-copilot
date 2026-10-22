import time
import json
import logging
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
import redis.asyncio as redis

from app.config import settings
from app.graph.json_store import graph_store
from app.retrieval.aliases import SymptomAliasMapper, normalize_text
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.applicability import ApplicabilityFilter
from app.retrieval.chunker import DocumentChunker
from app.diagnosis.safety import safety_gate
from app.diagnosis.ranking import cause_ranker
from app.diagnosis.prompts import SYSTEM_INSTRUCTION, build_diagnosis_prompt
from app.diagnosis.grounding import grounding_validator
from app.llm.fallback import stream_with_fallback

logger = logging.getLogger(__name__)


class DiagnosisEngine:
    """
    Core Diagnosis Engine:
    Orchestrates deterministic graph traversal, safety gating, BM25/alias mapping,
    LLM synthesis streaming, and background telemetry recording.
    """

    def __init__(self):
        self.alias_mapper: Optional[SymptomAliasMapper] = None
        self.bm25_retriever: Optional[BM25Retriever] = None
        self.applicability_filter = ApplicabilityFilter()
        self.chunker = DocumentChunker()
        self._redis: Optional[redis.Redis] = None

    def initialize_indexes(self):
        """Indexes all symptoms and manuals into memory."""
        symptoms = graph_store.get_nodes("Symptom")
        self.alias_mapper = SymptomAliasMapper(symptoms)

        bm25_docs = []
        for s in symptoms:
            bm25_docs.append({
                "id": s["id"],
                "text": s.get("name", "") + " " + s.get("description", "") + " " + " ".join(s.get("aliases", [])),
                "type": "Symptom",
                "raw": s
            })
        self.bm25_retriever = BM25Retriever()
        self.bm25_retriever.index(bm25_docs)
        logger.info("DiagnosisEngine indexes initialized.")

    async def get_redis(self) -> Optional[redis.Redis]:
        if self._redis is None:
            try:
                self._redis = redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=2.0)
            except Exception as e:
                logger.warning(f"Redis connection unavailable: {e}")
                self._redis = None
        return self._redis

    async def record_trace_background(self, trace_data: Dict[str, Any]):
        """Records diagnostic trace and timings to Redis stream in background."""
        try:
            r = await self.get_redis()
            if r:
                await r.xadd("readiness:traces", {"data": json.dumps(trace_data)}, maxlen=1000)
                # Store recent latency for /api/metrics
                total_ms = trace_data.get("total_ms", 0)
                first_token_ms = trace_data.get("first_token_ms", 0)
                await r.lpush("readiness:metrics:total_ms", total_ms)
                await r.ltrim("readiness:metrics:total_ms", 0, 100)
                await r.lpush("readiness:metrics:first_token_ms", first_token_ms)
                await r.ltrim("readiness:metrics:first_token_ms", 0, 100)
        except Exception as e:
            logger.debug(f"Failed to record trace to Redis: {e}")

    async def diagnose_stream(
        self,
        asset_id: str,
        symptom_text: str,
        alarm_code: Optional[str] = None,
        observations: Optional[List[str]] = None,
        user_role: str = "technician"
    ) -> AsyncGenerator[str, None]:
        """
        Executes the full diagnosis pipeline and yields SSE events.
        Target: First token in <= 1.5s, total <= 4.0s.
        """
        t_start = time.perf_counter()

        if self.alias_mapper is None:
            self.initialize_indexes()

        # 1. Identify Asset from Graph
        t0_retrieval = time.perf_counter()
        asset = graph_store.get_node(asset_id)
        if not asset:
            yield f"event: error\ndata: {json.dumps({'error': f'Asset {asset_id} not found in equipment database'})}\n\n"
            return

        target_model = asset.get("model", "")

        # 2. Safety Gate Check
        is_safe_triggered, safe_reason, emergency_action = safety_gate.evaluate(
            symptom_text=symptom_text,
            alarm_code=alarm_code,
            observations=observations
        )

        # 3. Symptom Mapping (< 30 ms)
        matched_symptom = None
        symptom_match_score = 0.5

        # Check alias mapper first
        alias_matches = self.alias_mapper.match(symptom_text, alarm_code)
        if alias_matches:
            best_id, match_score, match_type = alias_matches[0]
            matched_symptom = graph_store.get_node(best_id)
            symptom_match_score = match_score
        else:
            # Fallback to BM25
            bm25_matches = self.bm25_retriever.search(symptom_text, top_k=1)
            if bm25_matches:
                doc, score = bm25_matches[0]
                matched_symptom = doc.get("raw")
                symptom_match_score = min(score / 5.0, 0.85)

        if not matched_symptom:
            # Fallback default symptom
            matched_symptom = graph_store.get_node("SYMP-VIB-01")
            symptom_match_score = 0.3

        # 4. Deterministic Graph Traversal & Applicability Filtering
        raw_causes = graph_store.get_causes_for_symptom(matched_symptom["id"], applicable_model=target_model)
        candidate_causes = [c for c, edge in raw_causes]
        candidate_causes = self.applicability_filter.filter_causes(candidate_causes, target_model)

        # Get procedures for candidate causes
        candidate_procedures = []
        for c in candidate_causes:
            procs = graph_store.get_procedures_for_cause(c["id"], applicable_model=target_model)
            for p, _ in procs:
                if p not in candidate_procedures:
                    candidate_procedures.append(p)

        # Filter procedures (ensures Trap 1 wrong-model procedure is stripped)
        candidate_procedures = self.applicability_filter.filter_procedures(
            candidate_procedures,
            target_model=target_model,
            user_role=user_role
        )

        # Get historical verified incidents
        verified_incidents = graph_store.get_verified_incidents()
        verified_causes = {inc.get("confirmed_cause_id") for inc in verified_incidents}

        # 5. Deterministic Ranking
        ranked_causes = cause_ranker.rank(
            candidate_causes=candidate_causes,
            symptom_match_score=symptom_match_score,
            asset_id=asset_id,
            asset_model=target_model,
            verified_incidents=verified_incidents,
            observations=observations
        )

        # 6. Retrieve Manual Passages
        source_tuples = [(c["source_doc_id"], c["section"]) for c in candidate_causes]
        for p in candidate_procedures:
            source_tuples.append((p["source_doc_id"], p["section"]))
        passages = self.chunker.get_sections_for_sources(source_tuples)

        retrieval_ms = int((time.perf_counter() - t0_retrieval) * 1000)

        # If safety gate triggered, put emergency action first
        if is_safe_triggered and emergency_action:
            emergency_proc = graph_store.get_node(emergency_action["procedure_id"])
            if emergency_proc and emergency_proc not in candidate_procedures:
                candidate_procedures.insert(0, emergency_proc)

        # Yield metadata event to client immediately
        initial_metadata = {
            "asset": asset,
            "symptom": matched_symptom,
            "safety_alert": emergency_action if is_safe_triggered else None,
            "ranked_causes": [
                {
                    "cause_id": item["cause"]["id"],
                    "name": item["cause"]["name"],
                    "evidence_strength": item["evidence_strength"],
                    "evidence_reasons": item["evidence_reasons"],
                    "source_doc_id": item["cause"].get("source_doc_id"),
                    "section": item["cause"].get("section"),
                    "label": item["label"]
                }
                for item in ranked_causes
            ],
            "retrieval_ms": retrieval_ms
        }
        yield f"event: metadata\ndata: {json.dumps(initial_metadata)}\n\n"

        # 7. Check Cache in Redis
        cache_hit = False
        cached_result = None
        norm_symp = normalize_text(symptom_text)
        cache_key = f"readiness:cache:{target_model}:{norm_symp}"
        r = await self.get_redis()
        if r:
            try:
                cached_str = await r.get(cache_key)
                if cached_str:
                    cached_result = json.loads(cached_str)
                    cache_hit = True
            except Exception as e:
                logger.debug(f"Cache get error: {e}")

        full_generated_text = ""
        first_token_ms = None

        if cache_hit and cached_result and not is_safe_triggered:
            # Emit cached response in rapid simulated stream
            full_generated_text = cached_result.get("text", "")
            first_token_ms = int((time.perf_counter() - t_start) * 1000)
            yield f"event: chunk\ndata: {json.dumps({'text': full_generated_text, 'first_token_ms': first_token_ms, 'cached': True})}\n\n"
        else:
            # 8. Stream from Gemini / Gemma 4 with Fallback
            prompt = build_diagnosis_prompt(
                asset=asset,
                symptom=matched_symptom,
                symptom_input=symptom_text,
                ranked_causes=ranked_causes,
                procedures=candidate_procedures,
                manual_passages=passages,
                safety_alert=emergency_action if is_safe_triggered else None
            )

            async for chunk in stream_with_fallback(
                prompt=prompt,
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.1,
                max_tokens=600  # Tuned for sub-4s completion
            ):
                chunk_type = chunk.get("type")
                if chunk_type == "chunk":
                    if first_token_ms is None:
                        first_token_ms = int((time.perf_counter() - t_start) * 1000)
                    text_piece = chunk.get("text", "")
                    full_generated_text += text_piece
                    yield f"event: chunk\ndata: {json.dumps({'text': text_piece, 'first_token_ms': first_token_ms})}\n\n"
                elif chunk_type == "error":
                    yield f"event: error\ndata: {json.dumps({'error': chunk.get('error')})}\n\n"
                    break

            # Cache the successful non-emergency generation in Redis
            if r and full_generated_text and not is_safe_triggered:
                try:
                    await r.setex(cache_key, 3600, json.dumps({"text": full_generated_text}))
                except Exception as e:
                    logger.debug(f"Cache set error: {e}")

        # 9. Grounding Validation & Card Generation
        retrieved_docs = {p.get("doc_id") for p in passages}
        cleaned_text, cause_cards, audit_messages = grounding_validator.validate_and_tag(
            llm_text=full_generated_text,
            retrieved_doc_ids=retrieved_docs,
            retrieved_causes=ranked_causes,
            retrieved_procedures=candidate_procedures,
            verified_incident_causes=verified_causes
        )

        yield f"event: cards\ndata: {json.dumps({'cards': cause_cards, 'audit': audit_messages})}\n\n"

        total_ms = int((time.perf_counter() - t_start) * 1000)

        # 10. Record Trace Asynchronously in Background
        trace_record = {
            "asset_id": asset_id,
            "model": target_model,
            "symptom": symptom_text,
            "retrieval_ms": retrieval_ms,
            "first_token_ms": first_token_ms or total_ms,
            "total_ms": total_ms,
            "cache_hit": cache_hit,
            "safety_triggered": is_safe_triggered,
            "timestamp": time.time()
        }
        # Fire-and-forget background task
        asyncio.create_task(self.record_trace_background(trace_record))

        # Final done event with exact timings
        done_payload = {
            "total_ms": total_ms,
            "first_token_ms": first_token_ms or total_ms,
            "retrieval_ms": retrieval_ms,
            "cache_hit": cache_hit,
            "safety_triggered": is_safe_triggered,
            "server_timing": f"retrieval;dur={retrieval_ms}, llm_first;dur={first_token_ms or total_ms}, total;dur={total_ms}"
        }
        yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"


diagnosis_engine = DiagnosisEngine()
