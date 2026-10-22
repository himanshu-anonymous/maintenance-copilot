import time
import json
from pathlib import Path
import pytest
from app.graph.validators import validate_graph
from app.graph.json_store import JsonGraphStore
from app.graph.build import build_knowledge_graph


def get_paths():
    base = Path(__file__).resolve().parent.parent.parent
    k_dir = base / "knowledge"
    yaml_path = base / "graph.yaml"
    json_path = base / "graph.json"
    if not k_dir.exists():
        k_dir = Path("/app/knowledge")
        yaml_path = Path("/app/graph.yaml")
        json_path = Path("/app/graph.json")
    return k_dir, yaml_path, json_path


def test_graph_build_and_validation():
    k_dir, yaml_path, json_path = get_paths()
    graph_dict = build_knowledge_graph(k_dir, yaml_path, json_path)

    assert "nodes" in graph_dict
    assert "edges" in graph_dict
    assert len(graph_dict["nodes"]) >= 70
    assert len(graph_dict["edges"]) >= 90

    # Strict validator execution
    is_valid, errors = validate_graph(graph_dict)
    assert is_valid is True, f"Graph validation errors: {errors}"
    assert len(errors) == 0


def test_graph_json_load_latency():
    """ACCEPT requirement: graph.json loads in < 1 s."""
    _, _, json_path = get_paths()
    assert json_path.exists(), f"graph.json missing at {json_path}"

    store = JsonGraphStore()
    t0 = time.perf_counter()
    store.load_from_file(json_path)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    print(f"\n[BENCHMARK] graph.json loaded in {elapsed_ms:.2f} ms")
    assert elapsed_ms < 1000.0, f"graph.json took {elapsed_ms:.2f}ms to load, exceeded 1s limit"
    assert len(store.get_nodes()) > 50


def test_graph_traversal_and_applicability_filtering():
    _, _, json_path = get_paths()
    store = JsonGraphStore()
    store.load_from_file(json_path)

    # 1. Test Symptom to Cause traversal
    cp200_puls_causes = store.get_causes_for_symptom("SYMP-DISCH-PULS-01", applicable_model="ApexFlow-CP200")
    cause_ids_cp200 = [c["id"] for c, _ in cp200_puls_causes]
    assert "CAUSE-IMP-VANE-RESONANCE" in cause_ids_cp200
    assert "CAUSE-VALVE-FLUTTER" not in cause_ids_cp200, "Trap 3 failed: valve flutter should not apply to CP200"

    cp100_puls_causes = store.get_causes_for_symptom("SYMP-DISCH-PULS-01", applicable_model="ApexFlow-CP100")
    cause_ids_cp100 = [c["id"] for c, _ in cp100_puls_causes]
    assert "CAUSE-VALVE-FLUTTER" in cause_ids_cp100
    assert "CAUSE-IMP-VANE-RESONANCE" not in cause_ids_cp100, "Trap 3 failed: vane resonance should not apply to CP100"

    # 2. Test Procedure applicability (Trap 1: VFD procedure)
    vfd_procs = store.get_procedures_for_cause("CAUSE-VFD-CARRIER-NOISE", applicable_model="DuraTorq-IM50-VFD")
    assert len(vfd_procs) == 1
    assert vfd_procs[0][0]["id"] == "PROC-VFD-HARMONIC-TUNING"

    im50_std_procs = store.get_procedures_for_cause("CAUSE-VFD-CARRIER-NOISE", applicable_model="DuraTorq-IM50")
    assert len(im50_std_procs) == 0, "Trap 1 failed: VFD procedure must NOT apply to standard DuraTorq-IM50"


def test_add_verified_outcome_incremental_update():
    _, _, json_path = get_paths()
    store = JsonGraphStore()
    store.load_from_file(json_path)

    initial_verified = store.get_verified_incidents(cause_id="CAUSE-BRG-WEAR")
    initial_count = len(initial_verified)

    # Add a supervisor verified outcome
    new_outcome = {
        "id": "INC-TEST-999",
        "asset_id": "P-101",
        "symptom_id": "SYMP-VIB-01",
        "confirmed_cause_id": "CAUSE-BRG-WEAR",
        "procedure_used_id": "PROC-BRG-CLEARANCE-CHK",
        "technician": "tech_bob",
        "approved_by": "supervisor_alice",
        "incident_date": "2024-10-22",
        "resolution_notes": "Replaced worn outboard 6312 bearing."
    }
    store.add_verified_outcome(new_outcome)

    updated_verified = store.get_verified_incidents(cause_id="CAUSE-BRG-WEAR")
    assert len(updated_verified) == initial_count + 1
    assert any(inc["id"] == "INC-TEST-999" for inc in updated_verified)
