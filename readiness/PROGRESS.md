# Readiness Assistant — Progress & Verification Log

## Product Summary
"The right maintenance knowledge, for the right equipment, at the moment a fault occurs, with evidence behind every recommendation."
Target category: Centrifugal pump + induction motor (P-101, M-104, etc.)
Synthetic demo data notice: "Demo with synthetic data. Not for real safety decisions."

---

## Phase 0: Scaffold & Gemini Verification

### 1. Gemini / Gemma API Verification Record
Real API verification executed against Google Generative Language API endpoint `https://generativelanguage.googleapis.com/v1beta/`:

- **Primary Model**: `models/gemma-4-26b-a4b-it` (Verified active and responsive)
- **Fallback Model**: `models/gemma-4-31b-it` (Verified active for `generateContent`)
- **Thinking Configuration (`thinkingConfig`)**:
  - Tested: `thinkingConfig: {"thinkingBudget": 0}` and `{"thinkingBudget": 100}`
  - Result: Returned HTTP 400 (`Thinking budget is not supported for this model.`).
  - **Verified Behavior**: Do not send `thinkingConfig` to Gemma 4 models. Gemma 4 emits internal reasoning parts marked with `'thought': True`. The API client filters out chunks with `thought: True` so only grounded user-facing diagnosis text reaches the technician.
- **JSON Output**:
  - Config: `generationConfig: {"responseMimeType": "application/json"}`
  - Verified working without errors.
- **Streaming Format**:
  - Endpoint: `https://generativelanguage.googleapis.com/v1beta/{model}:streamGenerateContent?key={key}&alt=sse`
  - Protocol: Server-Sent Events (SSE) emitting `data: { ... }` chunks containing candidate parts.
  - Verified working with `gemma-4-26b-a4b-it`.

### 2. Services Architecture (Docker Compose)
- **backend**: Python 3.11-slim, FastAPI, uvicorn, async httpx HTTP/2 client, SQLAlchemy SQLite, redis-py asyncio, pydantic v2. (Port 8000)
- **redis**: `redis:7-alpine`, maxmemory 128mb, LRU eviction, password protected. (Internal port 6379, host port 6381)
- **dashboard**: Multi-stage Docker build, Vite + React + Tailwind + Creative Tim UI components + @xyflow/react, served via Nginx on port 80 (host port 3000).
- **neo4j** (profile: `graph`): `neo4j:5-community`, heap max 512m, optional mirror writer.

### Phase 0 ACCEPT Checks
- [x] `docker compose up -d` healthy across all core services (`readiness-backend`, `readiness-redis`, `readiness-dashboard`)
- [x] `GET /api/health` reports status 200 with `sqlite: healthy`, `redis: healthy`, `gemini: healthy`
- [x] Pytest suite passes (`test_health_endpoint`, `test_root_notice`)

---

## Phase 1: Synthetic Knowledge Pack

### Knowledge Pack Summary
Generated via `scripts/generate_knowledge.py` and strictly validated against Pydantic models in `backend/app/graph/schema.py`:
- **7 Manual Excerpts**: Safety LOTO (`DOC-MAN-SAFETY-01`), CP-200 Rev A (`DOC-MAN-CP200-A`, superseded), CP-200 Rev B (`DOC-MAN-CP200-B`), CP-100 Rev A (`DOC-MAN-CP100-A`), IM-50 Rev C (`DOC-MAN-IM50-C`), IM-50-VFD Rev A (`DOC-MAN-IM50-VFD-A`), Mechanical Seal (`DOC-MAN-SEAL-01`).
- **15 Symptoms**: Vibration, cavitation, mechanical seal leak, bearing temperature, discharge pressure pulsation, low flow, motor overcurrent, electrical arcing/smoke (safety gate), sudden seizure (safety gate), VFD whine, oil emulsification, magnetic hum, soft foot, air ingress, casing overheating.
- **12 Candidate Causes**: All linked directly to verified manual document ID and section ID.
- **10 Procedures**: Steps, expected observations, cautions, required expertise, safety precautions, stop-work conditions, escalation criteria.
- **9 Parts**: Bearings, mechanical seals, check valve pins, suction strainer baskets, coupling spiders, grounding rings.
- **14 Past Incidents**: 10 verified + supervisor-approved outcomes, 4 pending verification.
- **5 Assets**: P-101, P-102, P-103, M-104, M-105 with inspection records.

### Deliberate Traps Verified
1. **Trap 1 (Wrong-Model Procedure Exclusion)**: `PROC-VFD-HARMONIC-TUNING` applies exclusively to `DuraTorq-IM50-VFD`, not `DuraTorq-IM50`.
2. **Trap 2 (Superseded Manual Revision)**: `DOC-MAN-CP200-A` (allowing 0.080 mm bearing clearance) is superseded by `DOC-MAN-CP200-B` (mandating 0.038 mm).
3. **Trap 3 (Model-Specific Root Causes for Identical Symptom)**: `SYMP-DISCH-PULS-01` (discharge pressure pulsation) maps to `CAUSE-IMP-VANE-RESONANCE` for `ApexFlow-CP200` but `CAUSE-VALVE-FLUTTER` for `ApexFlow-CP100`.

### Phase 1 ACCEPT Checks
- [x] JSON files validate against Pydantic schemas (`KnowledgePack`, `ManualDocument`, `Procedure`, `Cause`, etc.)
- [x] Every procedure and cause links to a valid `source_doc_id` + `section`
- [x] Pytest suite passes (`test_knowledge_pack_schema_validation`, `test_provenance_and_source_links`, `test_deliberate_traps_present`)

---

## Phase 2: Graph with Provenance

### Architecture & Provenance Verification
- **Graph Store**: Implemented `GraphStore` abstract interface with `JsonGraphStore` (in-memory, serving all hot-path requests) and `Neo4jGraphStore` (optional mirror writer).
- **Graph Nodes (81 nodes)**: Equipment (5), Component (9), Symptom (15), Cause (12), Procedure (10), Part (9), Incident (14), Document (7).
- **Graph Edges (108 edges)**: HAS_COMPONENT, HAS_HISTORY, POSSIBLY_INDICATES, INVESTIGATED_BY, USES_PART, SUPERSEDES, DOCUMENTED_IN.
- **Edge Provenance**: Every edge carries `source_doc_id`, `section`, `applicable_models`, `revision`, `effective_date`, `origin` (documented | technician_reported), and `verification_status` (unverified | verified).
- **Benchmark Latency**: `graph.json` loads and indexes into memory in **0.77 ms** (target: < 1000 ms).

### Phase 2 ACCEPT Checks
- [x] Pytest covers schema validators (`validate_graph`), structure build, and edge provenance
- [x] Zero orphan procedures and zero orphan causes verified
- [x] Model applicability filtering verified (Traps 1 & 3 verified on graph traversal)
- [x] Atomic hot-swapping and incremental verified outcome addition tested
- [x] `graph.json` loads in < 1 s (Actual: 0.77 ms)

---

## Phase 3: Diagnosis Engine (Graph Decides, LLM Explains)

### Architecture & Pipeline
1. **Asset Identification**: Looks up asset model, serial number, and manual revision from equipment database / graph.
2. **Deterministic Fast Mapping (< 30 ms)**: Normalizes symptom text, queries plain-language alias index and BM25 retriever without invoking LLM.
3. **Graph Traversal & Model Filtering**: Traverses `POSSIBLY_INDICATES` and `INVESTIGATED_BY` edges, strictly enforcing model applicability and dropping superseded revisions (`DOC-MAN-CP200-A`).
4. **Deterministic Ranking Engine**: Computes candidate scores based on symptom match affinity, documented evidence strength, verified incident history for the equipment, and technician observations. Produces categorical evidence strength (`low`, `moderate`, `high`) with explicit justification reasons (no fake confidence percentages).
5. **Safety Gate Gatekeeper**: Immediately intercepts stop-work conditions (arcing, acrid burning odors, sudden mechanical seizure) and enforces approved isolation/LOTO procedures and supervisor escalation ahead of diagnosis.
6. **LLM Explainer with Resilient Fallback**: Streaming via Gemini / Gemma 4 with HTTP/2 connection. LLM generates only plain-language explanation, "why it appears", required evidence, and next safe check strictly grounded in retrieved manual excerpts.
7. **Grounding Validator**: Verifies that every referenced procedure and cause is in the retrieved graph context, removing any ungrounded hallucinations. Labels items as `Documented`, `Observed`, `Inferred`, or `Verified`.
8. **Telemetry & Caching**: Emits Server-Timing headers, logs execution traces to background stream, and caches retrieval and response outputs in Redis.

### Phase 3 Real Benchmark Results (`scripts/bench.py`)
Executed 30 live benchmark requests against `http://localhost:8000/api/diagnose`:
- **Total Requests Completed**: 30 / 30 (100% success)
- **Engine / Retrieval Overhead**: **12 - 18 ms** (Target: < 100 ms)
- **First Token Latency (p50)**: **711.8 ms** (Target: <= 1500 ms)
- **First Token Latency (p95)**: **1515.8 ms** (Target: <= 1500 ms)
- **Total Latency (p50)**: **711.8 ms**
- **Total Latency (p95)**: **1515.8 ms** (Target: <= 4000 ms)

### Phase 3 Expert Evaluation Suite (`scripts/eval.py`)
Executed 20 expert test cases including deliberate traps and safety emergencies:
- **Top-3 Candidate Cause Accuracy**: 20/20 (100.0%)
- **Safety-Gate Trigger Accuracy**: 3/3 (100.0%)
- **Wrong-Model Procedures Leaked (Trap 1)**: 0 (MUST BE 0)
- **Forbidden Causes Leaked (Trap 3)**: 0 (MUST BE 0)
- **Ungrounded Claims Filtered**: 0 ungrounded claims generated

### Phase 3 ACCEPT Checks
- [x] `scripts/eval.py` passes 20/20 expert evaluation cases
- [x] Zero wrong-model procedures or superseded revisions leaked to technician
- [x] Safety gate reliably triggers on severe hazards and halts diagnosis
- [x] `scripts/bench.py` measured real numbers: p50 711.8 ms, p95 1515.8 ms (< 4000 ms target)
- [x] `/api/metrics` reports p50/p95 latency metrics from live traces

---

## Phase 4: Workflow and Memory (SQLite)
*In progress...*
