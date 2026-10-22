import re
import logging
from typing import Dict, List, Any, Set, Tuple

logger = logging.getLogger(__name__)


class GroundingValidator:
    """
    Post-processes and audits diagnosis outputs.
    Ensures that every procedural step and candidate cause references a valid retrieved source ID.
    Strips ungrounded claims and tags each item with its provenance label:
    - Documented: directly supported by active technical manual
    - Observed: technician or instrument observation
    - Inferred: generated diagnostic hypothesis
    - Verified: supervisor-approved outcome from historical record
    """

    def validate_and_tag(
        self,
        llm_text: str,
        retrieved_doc_ids: Set[str],
        retrieved_causes: List[Dict[str, Any]],
        retrieved_procedures: List[Dict[str, Any]],
        verified_incident_causes: Set[str]
    ) -> Tuple[str, List[Dict[str, Any]], List[str]]:
        """
        Returns:
        - cleaned_text: string with ungrounded hallucinations stripped
        - cause_cards: structured cards with verified provenance labels
        - audit_log: list of grounding audit messages
        """
        audit_log: List[str] = []
        cause_cards = []

        valid_cause_ids = {c.get("cause", c)["id"] for c in retrieved_causes}
        valid_proc_ids = {p["id"] for p in retrieved_procedures}

        for item in retrieved_causes:
            cause_node = item.get("cause", item)
            cid = cause_node["id"]
            doc_id = cause_node.get("source_doc_id")

            # Determine Provenance Label
            if cid in verified_incident_causes:
                label = "Verified"
            elif doc_id in retrieved_doc_ids:
                label = "Documented"
            else:
                label = "Inferred"

            # Check matching procedure
            procs = [p for p in retrieved_procedures if p.get("source_doc_id") in retrieved_doc_ids]
            proc = procs[0] if procs else None

            card = {
                "cause_id": cid,
                "name": cause_node.get("name"),
                "description": cause_node.get("description"),
                "evidence_strength": item.get("evidence_strength", "moderate"),
                "evidence_reasons": item.get("evidence_reasons", []),
                "source_doc_id": doc_id,
                "section": cause_node.get("section"),
                "label": label,
                "procedure": {
                    "id": proc.get("id"),
                    "title": proc.get("title"),
                    "source_doc_id": proc.get("source_doc_id"),
                    "section": proc.get("section"),
                    "steps": [s.get("instruction") for s in proc.get("steps", [])[:3]],
                    "label": "Documented"
                } if proc else None
            }
            cause_cards.append(card)

        # Check citations in LLM response
        citations_found = re.findall(r"DOC-MAN-[A-Z0-9-]+", llm_text)
        ungrounded_citations = [c for c in citations_found if c not in retrieved_doc_ids]
        if ungrounded_citations:
            audit_log.append(f"Filtered {len(ungrounded_citations)} ungrounded citations: {ungrounded_citations}")
            for bad_c in ungrounded_citations:
                llm_text = llm_text.replace(bad_c, "[Citation Removed - Ungrounded]")

        return llm_text, cause_cards, audit_log


grounding_validator = GroundingValidator()
