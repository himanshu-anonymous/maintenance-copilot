from typing import Dict, List, Any, Set, Tuple
import logging

logger = logging.getLogger(__name__)


class GraphValidationError(Exception):
    pass


def validate_graph(graph_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates graph consistency:
    - Node ID uniqueness and valid node types
    - Edge endpoint existence (source & target must exist)
    - Provenance on edges (source_doc_id & section where required)
    - No orphan procedures (must be connected via INVESTIGATED_BY)
    - No orphan causes (must be connected via POSSIBLY_INDICATES)
    - Valid origin and verification status
    """
    errors: List[str] = []
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    node_ids: Set[str] = set()
    node_types: Dict[str, str] = {}

    valid_types = {
        "Equipment", "Component", "Symptom", "Cause",
        "Procedure", "Part", "Incident", "Outcome", "Document"
    }

    # 1. Validate Nodes
    for n in nodes:
        nid = n.get("id")
        ntype = n.get("type")
        if not nid:
            errors.append("Node found with empty or missing 'id'")
            continue
        if nid in node_ids:
            errors.append(f"Duplicate node ID detected: {nid}")
        node_ids.add(nid)

        if ntype not in valid_types:
            errors.append(f"Invalid node type '{ntype}' for node {nid}. Must be one of {valid_types}")
        node_types[nid] = ntype

    # 2. Validate Edges
    procedures_with_cause: Set[str] = set()
    causes_with_symptom: Set[str] = set()

    for idx, e in enumerate(edges):
        src = e.get("source")
        tgt = e.get("target")
        etype = e.get("edge_type")

        if not src or src not in node_ids:
            errors.append(f"Edge #{idx} has invalid source node: '{src}'")
        if not tgt or tgt not in node_ids:
            errors.append(f"Edge #{idx} has invalid target node: '{tgt}'")

        # Track procedure investigations & symptom causes
        if etype == "INVESTIGATED_BY":
            procedures_with_cause.add(tgt)
        elif etype == "POSSIBLY_INDICATES":
            causes_with_symptom.add(tgt)

        # Provenance validation: documented rules must have source_doc_id and section
        origin = e.get("origin", "documented")
        if origin == "documented" and etype in ("POSSIBLY_INDICATES", "INVESTIGATED_BY"):
            if not e.get("source_doc_id"):
                errors.append(f"Documented edge '{etype}' between {src} and {tgt} is missing 'source_doc_id'")
            if not e.get("section"):
                errors.append(f"Documented edge '{etype}' between {src} and {tgt} is missing 'section'")

        # Verification status check
        vstatus = e.get("verification_status", "unverified")
        if vstatus not in ("unverified", "verified"):
            errors.append(f"Edge #{idx} has invalid verification_status: '{vstatus}'")

    # 3. Orphan Detection
    all_procedures = {nid for nid, ntype in node_types.items() if ntype == "Procedure"}
    # Emergency shutdown applies to all and is linked to safety symptoms, but let's check standard procedures
    orphan_procs = all_procedures - procedures_with_cause
    if orphan_procs:
        errors.append(f"Orphan procedure(s) detected without candidate cause: {orphan_procs}")

    all_causes = {nid for nid, ntype in node_types.items() if ntype == "Cause"}
    orphan_causes = all_causes - causes_with_symptom
    if orphan_causes:
        errors.append(f"Orphan cause(s) detected without linked symptom: {orphan_causes}")

    if errors:
        return False, errors
    return True, []
