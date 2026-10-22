import os
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))
readiness_dir = backend_dir.parent

import json
import logging
from typing import Dict, Any, List
import yaml

from app.graph.schema import KnowledgePack, GraphEdge
from app.graph.validators import validate_graph, GraphValidationError


logger = logging.getLogger(__name__)


def build_knowledge_graph(
    knowledge_dir: Path,
    graph_yaml_path: Path,
    output_path: Path
) -> Dict[str, Any]:
    """
    Constructs graph.json from knowledge_pack.json and graph.yaml.
    Validates provenance, node connectivity, and schema constraints.
    Returns the validated graph dictionary.
    """
    logger.info("Building knowledge graph...")

    pack_file = knowledge_dir / "knowledge_pack.json"
    if not pack_file.exists():
        raise FileNotFoundError(f"Knowledge pack not found at {pack_file}")

    with open(pack_file, "r", encoding="utf-8") as f:
        pack_raw = json.load(f)
    pack = KnowledgePack.model_validate(pack_raw)

    yaml_data: Dict[str, Any] = {}
    if graph_yaml_path.exists():
        with open(graph_yaml_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # 1. Add Equipment Nodes
    for asset in pack.assets:
        nodes.append({
            "id": asset.id,
            "type": "Equipment",
            "name": asset.name,
            "category": asset.category,
            "model": asset.model,
            "revision": asset.revision,
            "manual_id": asset.manual_id,
            "criticality": asset.criticality,
            "motor_id": asset.motor_id,
            "inspections": [i.model_dump() for i in asset.inspection_history]
        })

    # 2. Add Component Nodes
    components = [
        {"id": "COMP-BEARING", "name": "Deep Groove & Angular Contact Bearings", "category": "mechanical"},
        {"id": "COMP-IMPELLER", "name": "Centrifugal Impeller & Diffuser Vanes", "category": "hydraulic"},
        {"id": "COMP-SEAL", "name": "Cartridge & Component Mechanical Seals", "category": "mechanical"},
        {"id": "COMP-COUPLING", "name": "Flexible Elastomer Shaft Coupling", "category": "mechanical"},
        {"id": "COMP-VALVE", "name": "Discharge Check Valve Assembly", "category": "piping"},
        {"id": "COMP-STATOR", "name": "Induction Motor Stator Windings & Insulation", "category": "electrical"},
        {"id": "COMP-MOTOR-VFD", "name": "Inverter-Duty Motor Drive & Shaft Grounding", "category": "electrical"},
        {"id": "COMP-FLANGE", "name": "Suction & Discharge Flange Joints", "category": "piping"},
        {"id": "COMP-MOTOR", "name": "Induction Motor Drive Assembly", "category": "electrical"}
    ]
    for comp in components:
        nodes.append({
            "id": comp["id"],
            "type": "Component",
            "name": comp["name"],
            "category": comp["category"]
        })

    # 3. Add Symptom Nodes
    for s in pack.symptoms:
        nodes.append({
            "id": s.id,
            "type": "Symptom",
            "name": s.name,
            "description": s.description,
            "aliases": s.aliases,
            "alarm_codes": s.alarm_codes,
            "category": s.category
        })

    # 4. Add Cause Nodes
    for c in pack.causes:
        nodes.append({
            "id": c.id,
            "type": "Cause",
            "name": c.name,
            "description": c.description,
            "source_doc_id": c.source_doc_id,
            "section": c.section,
            "applicable_models": c.applicable_models,
            "component_id": c.component_id
        })

    # 5. Add Procedure Nodes
    for p in pack.procedures:
        nodes.append({
            "id": p.id,
            "type": "Procedure",
            "title": p.title,
            "source_doc_id": p.source_doc_id,
            "section": p.section,
            "applicable_models": p.applicable_models,
            "required_expertise": p.required_expertise,
            "safety_precautions": p.safety_precautions,
            "stop_work_conditions": p.stop_work_conditions,
            "steps": [step.model_dump() for step in p.steps],
            "escalation_criteria": p.escalation_criteria
        })

    # 6. Add Part Nodes
    for pt in pack.parts:
        nodes.append({
            "id": pt.id,
            "type": "Part",
            "name": pt.name,
            "part_number": pt.part_number,
            "applicable_models": pt.applicable_models,
            "lead_time_days": pt.estimated_lead_time_days
        })

    # 7. Add Incident Nodes
    for inc in pack.incidents:
        nodes.append({
            "id": inc.id,
            "type": "Incident",
            "asset_id": inc.asset_id,
            "symptom_id": inc.symptom_id,
            "confirmed_cause_id": inc.confirmed_cause_id,
            "procedure_used_id": inc.procedure_used_id,
            "outcome_status": inc.outcome_status,
            "technician": inc.technician,
            "supervisor_approved": inc.supervisor_approved,
            "approved_by": inc.approved_by,
            "incident_date": inc.incident_date,
            "resolution_notes": inc.resolution_notes
        })

    # 8. Add Document Nodes
    for doc in pack.manuals:
        nodes.append({
            "id": doc.doc_id,
            "type": "Document",
            "title": doc.title,
            "revision": doc.revision,
            "effective_date": doc.effective_date,
            "applicable_models": doc.applicable_models,
            "superseded_by": doc.superseded_by,
            "sections": [s.model_dump() for s in doc.sections]
        })

    # Map manual revisions & effective dates for fast edge tagging
    doc_meta = {d.doc_id: (d.revision, d.effective_date) for d in pack.manuals}

    def make_edge(
        src: str,
        tgt: str,
        etype: str,
        doc_id: str,
        section: str,
        models: List[str],
        origin: str = "documented",
        verification_status: str = "verified",
        approved_by: str = "engineering_team"
    ) -> Dict[str, Any]:
        rev, eff_date = doc_meta.get(doc_id, ("Rev 1.0", "2024-01-01"))
        return {
            "source": src,
            "target": tgt,
            "edge_type": etype,
            "source_doc_id": doc_id,
            "section": section,
            "applicable_models": models,
            "revision": rev,
            "effective_date": eff_date,
            "origin": origin,
            "verification_status": verification_status,
            "approved_by": approved_by
        }

    # ----------------------------------------------------
    # Edge Generation: HAS_COMPONENT
    # ----------------------------------------------------
    for asset in pack.assets:
        comps = ["COMP-BEARING", "COMP-COUPLING"]
        if "pump" in asset.category:
            comps.extend(["COMP-IMPELLER", "COMP-SEAL"])
            if "CP100" in asset.model:
                comps.append("COMP-VALVE")
        elif "motor" in asset.category:
            comps.append("COMP-STATOR")
        for c in comps:
            edges.append(make_edge(
                asset.id, c, "HAS_COMPONENT",
                doc_id=asset.manual_id, section="SEC-01",
                models=[asset.model]
            ))

    # ----------------------------------------------------
    # Edge Generation: HAS_HISTORY
    # ----------------------------------------------------
    for inc in pack.incidents:
        edges.append(make_edge(
            inc.asset_id, inc.id, "HAS_HISTORY",
            doc_id=inc.id, section="incident_log",
            models=[],
            origin="technician_reported",
            verification_status="verified" if inc.supervisor_approved else "unverified",
            approved_by=inc.approved_by or "pending"
        ))

    # ----------------------------------------------------
    # Edge Generation: POSSIBLY_INDICATES (Symptom -> Cause)
    # ----------------------------------------------------
    symptom_cause_links = [
        ("SYMP-VIB-01", "CAUSE-BRG-WEAR", "DOC-MAN-CP200-B", "SEC-CP200-04", ["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"]),
        ("SYMP-VIB-01", "CAUSE-SHAFT-MISALIGN", "DOC-MAN-CP200-B", "SEC-CP200-01", ["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"]),
        ("SYMP-CAV-01", "CAUSE-SUCT-STARVE", "DOC-MAN-CP200-B", "SEC-CP200-02", ["ApexFlow-CP200", "ApexFlow-CP100"]),
        ("SYMP-CAV-01", "CAUSE-AIR-LEAK-FLANGE", "DOC-MAN-CP200-B", "SEC-CP200-02", ["ApexFlow-CP200", "ApexFlow-CP100"]),
        ("SYMP-SEAL-01", "CAUSE-SEAL-FACE-DAMAGE", "DOC-MAN-CP200-B", "SEC-CP200-03", ["ApexFlow-CP200", "ApexFlow-CP100"]),
        ("SYMP-TEMP-01", "CAUSE-BRG-WEAR", "DOC-MAN-CP200-B", "SEC-CP200-04", ["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"]),
        ("SYMP-TEMP-01", "CAUSE-LUB-DEGRADATION", "DOC-MAN-CP200-B", "SEC-CP200-04", ["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"]),
        # Trap 3: Discharge pulsation causes differ by model!
        ("SYMP-DISCH-PULS-01", "CAUSE-IMP-VANE-RESONANCE", "DOC-MAN-CP200-B", "SEC-CP200-05", ["ApexFlow-CP200"]),
        ("SYMP-DISCH-PULS-01", "CAUSE-VALVE-FLUTTER", "DOC-MAN-CP100-A", "SEC-CP100-02", ["ApexFlow-CP100"]),
        ("SYMP-FLOW-LO-01", "CAUSE-SUCT-STARVE", "DOC-MAN-CP200-B", "SEC-CP200-02", ["ApexFlow-CP200", "ApexFlow-CP100"]),
        ("SYMP-CURR-HI-01", "CAUSE-MTR-OVERLOAD", "DOC-MAN-IM50-C", "SEC-IM50-01", ["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"]),
        # Safety Gate Symptoms
        ("SYMP-SMOKE-FIRE-01", "CAUSE-ELEC-ARC-INTERNAL", "DOC-MAN-SAFETY-01", "SEC-SAFE-01", ["DuraTorq-IM50", "DuraTorq-IM50-VFD"]),
        ("SYMP-SEIZURE-01", "CAUSE-BRG-CATASTROPHIC", "DOC-MAN-SAFETY-01", "SEC-SAFE-01", ["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"]),
        # Trap 1: VFD-only cause
        ("SYMP-VFD-HARMONIC-01", "CAUSE-VFD-CARRIER-NOISE", "DOC-MAN-IM50-VFD-A", "SEC-VFD-01", ["DuraTorq-IM50-VFD"]),
        ("SYMP-OIL-CONTAM-01", "CAUSE-SEAL-FACE-DAMAGE", "DOC-MAN-CP200-B", "SEC-CP200-03", ["ApexFlow-CP200", "ApexFlow-CP100"]),
        ("SYMP-MOTOR-HUM-01", "CAUSE-SHAFT-MISALIGN", "DOC-MAN-CP200-B", "SEC-CP200-01", ["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"]),
        ("SYMP-LOOSE-MOUNT-01", "CAUSE-SHAFT-MISALIGN", "DOC-MAN-CP200-B", "SEC-CP200-01", ["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"]),
        ("SYMP-AIR-INGRESS-01", "CAUSE-AIR-LEAK-FLANGE", "DOC-MAN-CP200-B", "SEC-CP200-02", ["ApexFlow-CP200", "ApexFlow-CP100"]),
        ("SYMP-PUMP-OVERHEAT-01", "CAUSE-IMP-VANE-RESONANCE", "DOC-MAN-CP200-B", "SEC-CP200-05", ["ApexFlow-CP200"]),
    ]
    for symp_id, cause_id, doc_id, sec, models in symptom_cause_links:
        edges.append(make_edge(symp_id, cause_id, "POSSIBLY_INDICATES", doc_id, sec, models))

    # ----------------------------------------------------
    # Edge Generation: INVESTIGATED_BY (Cause -> Procedure)
    # ----------------------------------------------------
    cause_proc_links = [
        ("CAUSE-BRG-WEAR", "PROC-BRG-CLEARANCE-CHK", "DOC-MAN-CP200-B", "SEC-CP200-04", ["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"]),
        ("CAUSE-SUCT-STARVE", "PROC-NPSH-SUCT-CLEAN", "DOC-MAN-CP200-B", "SEC-CP200-02", ["ApexFlow-CP200", "ApexFlow-CP100"]),
        ("CAUSE-SEAL-FACE-DAMAGE", "PROC-SEAL-FLUSH-INSPECT", "DOC-MAN-CP200-B", "SEC-CP200-03", ["ApexFlow-CP200", "ApexFlow-CP100"]),
        ("CAUSE-SHAFT-MISALIGN", "PROC-LASER-ALIGN", "DOC-MAN-CP200-B", "SEC-CP200-01", ["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"]),
        ("CAUSE-IMP-VANE-RESONANCE", "PROC-PULSATION-CP200", "DOC-MAN-CP200-B", "SEC-CP200-05", ["ApexFlow-CP200"]),
        ("CAUSE-VALVE-FLUTTER", "PROC-VALVE-CP100", "DOC-MAN-CP100-A", "SEC-CP100-02", ["ApexFlow-CP100"]),
        # Trap 1: Procedure applies strictly to DuraTorq-IM50-VFD
        ("CAUSE-VFD-CARRIER-NOISE", "PROC-VFD-HARMONIC-TUNING", "DOC-MAN-IM50-VFD-A", "SEC-VFD-01", ["DuraTorq-IM50-VFD"]),
        ("CAUSE-ELEC-ARC-INTERNAL", "PROC-SAFE-EMERGENCY-SHUTDOWN", "DOC-MAN-SAFETY-01", "SEC-SAFE-01", ["*"]),
        ("CAUSE-ELEC-ARC-INTERNAL", "PROC-MOTOR-MEGGER-TEST", "DOC-MAN-IM50-C", "SEC-IM50-02", ["DuraTorq-IM50", "DuraTorq-IM50-VFD"]),
        ("CAUSE-BRG-CATASTROPHIC", "PROC-SAFE-EMERGENCY-SHUTDOWN", "DOC-MAN-SAFETY-01", "SEC-SAFE-01", ["*"]),
        ("CAUSE-BRG-CATASTROPHIC", "PROC-BRG-CLEARANCE-CHK", "DOC-MAN-CP200-B", "SEC-CP200-04", ["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"]),
        ("CAUSE-LUB-DEGRADATION", "PROC-LUB-FLUSH-FILL", "DOC-MAN-CP200-B", "SEC-CP200-04", ["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"]),
        ("CAUSE-AIR-LEAK-FLANGE", "PROC-NPSH-SUCT-CLEAN", "DOC-MAN-CP200-B", "SEC-CP200-02", ["ApexFlow-CP200", "ApexFlow-CP100"]),
        ("CAUSE-MTR-OVERLOAD", "PROC-MOTOR-MEGGER-TEST", "DOC-MAN-IM50-C", "SEC-IM50-02", ["DuraTorq-IM50", "DuraTorq-IM50-VFD"]),
    ]
    for cause_id, proc_id, doc_id, sec, models in cause_proc_links:
        edges.append(make_edge(cause_id, proc_id, "INVESTIGATED_BY", doc_id, sec, models))

    # ----------------------------------------------------
    # Edge Generation: USES_PART (Procedure -> Part)
    # ----------------------------------------------------
    proc_part_links = [
        ("PROC-BRG-CLEARANCE-CHK", "PART-BRG-6312", ["ApexFlow-CP200"]),
        ("PROC-BRG-CLEARANCE-CHK", "PART-BRG-7312", ["ApexFlow-CP200"]),
        ("PROC-BRG-CLEARANCE-CHK", "PART-BRG-6310", ["DuraTorq-IM50", "DuraTorq-IM50-VFD"]),
        ("PROC-NPSH-SUCT-CLEAN", "PART-STRAINER-BASKET", ["ApexFlow-CP200", "ApexFlow-CP100"]),
        ("PROC-SEAL-FLUSH-INSPECT", "PART-SEAL-CP200", ["ApexFlow-CP200"]),
        ("PROC-SEAL-FLUSH-INSPECT", "PART-SEAL-CP100", ["ApexFlow-CP100"]),
        ("PROC-LASER-ALIGN", "PART-COUPLING-INSERT", ["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"]),
        ("PROC-VALVE-CP100", "PART-VALVE-PIN-100", ["ApexFlow-CP100"]),
        ("PROC-VFD-HARMONIC-TUNING", "PART-VFD-BRUSH", ["DuraTorq-IM50-VFD"])
    ]
    for proc_id, part_id, models in proc_part_links:
        edges.append(make_edge(
            proc_id, part_id, "USES_PART",
            doc_id="DOC-MAN-CP200-B", section="parts_catalog",
            models=models
        ))

    # ----------------------------------------------------
    # Edge Generation: SUPERSEDES (Document -> Document)
    # ----------------------------------------------------
    for doc in pack.manuals:
        if doc.superseded_by:
            # doc.superseded_by SUPERSEDES doc.doc_id
            edges.append(make_edge(
                doc.superseded_by, doc.doc_id, "SUPERSEDES",
                doc_id=doc.superseded_by, section="revision_history",
                models=doc.applicable_models
            ))

    # ----------------------------------------------------
    # Edge Generation: DOCUMENTED_IN (Node -> Document)
    # ----------------------------------------------------
    for c in pack.causes:
        edges.append(make_edge(
            c.id, c.source_doc_id, "DOCUMENTED_IN",
            doc_id=c.source_doc_id, section=c.section,
            models=c.applicable_models
        ))
    for p in pack.procedures:
        edges.append(make_edge(
            p.id, p.source_doc_id, "DOCUMENTED_IN",
            doc_id=p.source_doc_id, section=p.section,
            models=p.applicable_models
        ))

    # ----------------------------------------------------
    # Edge Generation: Incident-Specific Verified Outcomes
    # (Incident -> Cause) with technician_reported origin
    # ----------------------------------------------------
    for inc in pack.incidents:
        if inc.supervisor_approved:
            edges.append(make_edge(
                inc.id, inc.confirmed_cause_id, "POSSIBLY_INDICATES",
                doc_id=inc.id, section="resolution_notes",
                models=[],
                origin="technician_reported",
                verification_status="verified",
                approved_by=inc.approved_by or "supervisor_sarah"
            ))

    graph_dict = {
        "version": "1.0.0",
        "category": "centrifugal_pump_and_induction_motor",
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "total_nodes": len(nodes),
            "total_edges": len(edges)
        }
    }

    # Validate graph integrity
    is_valid, validation_errors = validate_graph(graph_dict)
    if not is_valid:
        raise GraphValidationError(f"Knowledge graph validation failed:\n" + "\n".join(validation_errors))

    # Write output JSON
    os.makedirs(output_path.parent, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph_dict, f, indent=2)

    logger.info(f"Knowledge graph built successfully: {len(nodes)} nodes, {len(edges)} edges -> {output_path}")
    return graph_dict


if __name__ == "__main__":
    k_dir = readiness_dir / "knowledge"
    yaml_path = readiness_dir / "graph.yaml"
    out_file = readiness_dir / "graph.json"
    build_knowledge_graph(k_dir, yaml_path, out_file)
    print(f"Graph built successfully: {out_file}")
