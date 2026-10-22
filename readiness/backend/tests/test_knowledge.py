import json
from pathlib import Path
import pytest
from app.graph.schema import (
    ManualDocument, Symptom, Cause, Procedure, Part, Incident, Asset, KnowledgePack
)


def get_knowledge_dir() -> Path:
    base = Path(__file__).resolve().parent.parent.parent / "knowledge"
    if not base.exists():
        base = Path("/app/knowledge")
    return base


def test_knowledge_pack_schema_validation():
    k_dir = get_knowledge_dir()
    pack_file = k_dir / "knowledge_pack.json"
    assert pack_file.exists(), f"Missing {pack_file}"

    with open(pack_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validates full pack against Pydantic schema
    pack = KnowledgePack.model_validate(data)
    assert len(pack.manuals) >= 6
    assert len(pack.symptoms) >= 14
    assert len(pack.causes) >= 10
    assert len(pack.procedures) >= 10
    assert len(pack.incidents) >= 12
    assert len(pack.assets) >= 5


def test_provenance_and_source_links():
    k_dir = get_knowledge_dir()
    with open(k_dir / "knowledge_pack.json", "r", encoding="utf-8") as f:
        pack = KnowledgePack.model_validate(json.load(f))

    doc_sections = set()
    for m in pack.manuals:
        for s in m.sections:
            doc_sections.add((m.doc_id, s.section_id))

    # Every cause must link to a valid doc_id + section
    for cause in pack.causes:
        assert (cause.source_doc_id, cause.section) in doc_sections, (
            f"Cause {cause.id} references invalid source ({cause.source_doc_id}, {cause.section})"
        )

    # Every procedure must link to a valid doc_id + section
    for proc in pack.procedures:
        assert (proc.source_doc_id, proc.section) in doc_sections, (
            f"Procedure {proc.id} references invalid source ({proc.source_doc_id}, {proc.section})"
        )


def test_deliberate_traps_present():
    k_dir = get_knowledge_dir()
    with open(k_dir / "knowledge_pack.json", "r", encoding="utf-8") as f:
        pack = KnowledgePack.model_validate(json.load(f))

    # Trap 1: A procedure that applies ONLY to DuraTorq-IM50-VFD
    vfd_procs = [p for p in pack.procedures if "DuraTorq-IM50-VFD" in p.applicable_models and "DuraTorq-IM50" not in p.applicable_models]
    assert len(vfd_procs) >= 1, "Trap 1 (VFD-only procedure) missing"
    assert vfd_procs[0].id == "PROC-VFD-HARMONIC-TUNING"

    # Trap 2: Superseded manual revision present
    superseded = [m for m in pack.manuals if m.superseded_by is not None]
    assert len(superseded) >= 1, "Trap 2 (superseded manual) missing"
    assert superseded[0].doc_id == "DOC-MAN-CP200-A"
    assert superseded[0].superseded_by == "DOC-MAN-CP200-B"

    # Trap 3: Differing causes between pump models for same symptom (discharge pulsation)
    puls_causes = [c for c in pack.causes if "ApexFlow-CP200" in c.applicable_models and "ApexFlow-CP100" not in c.applicable_models]
    assert any("RESONANCE" in c.id for c in puls_causes), "Trap 3 (CP200 specific pulsation cause) missing"

    cp100_puls_causes = [c for c in pack.causes if "ApexFlow-CP100" in c.applicable_models and "ApexFlow-CP200" not in c.applicable_models]
    assert any("VALVE" in c.id for c in cp100_puls_causes), "Trap 3 (CP100 specific pulsation cause) missing"
