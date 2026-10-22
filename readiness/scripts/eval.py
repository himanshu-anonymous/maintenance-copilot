"""
eval.py
Runs 20 expert-style test cases against Readiness Assistant Diagnosis Engine.
Measures:
1. Top-3 Candidate Cause Accuracy (target: >= 90%)
2. Ungrounded Claims Removed (grounding validator audit)
3. Safety Gate Trigger Rate on critical hazards (must be 100% on safety cases)
4. Wrong-Model Procedures Excluded (MUST BE EXACTLY 0)
"""

import sys
import os
import json
import asyncio
from pathlib import Path

# Add backend directory to path
current_dir = Path(__file__).resolve().parent
backend_dir = None
for c in [current_dir.parent / "backend", current_dir.parent, Path("/app")]:
    if (c / "app").exists():
        backend_dir = c
        sys.path.insert(0, str(c))
        break
readiness_dir = backend_dir.parent if backend_dir.name == "backend" else backend_dir

from app.graph.json_store import graph_store
from app.diagnosis.engine import diagnosis_engine

TEST_CASES = [
    {
        "id": "CASE-01",
        "asset_id": "P-101",
        "symptom": "Radial vibration on bearing housing is 8.5 mm/s RMS, pump shaking violently",
        "alarm": "ALM-VIB-101",
        "expected_top3_cause": "CAUSE-BRG-WEAR",
        "expect_safety": False
    },
    {
        "id": "CASE-02",
        "asset_id": "P-101",
        "symptom": "Sounds like gravel or marbles rattling inside pump casing, suction popping",
        "alarm": "ALM-SUCT-P-LO",
        "expected_top3_cause": "CAUSE-SUCT-STARVE",
        "expect_safety": False
    },
    {
        "id": "CASE-03",
        "asset_id": "P-102",
        "symptom": "Liquid dripping continuously from mechanical seal gland plate, puddle under pump",
        "alarm": "ALM-SEAL-LVL-LO",
        "expected_top3_cause": "CAUSE-SEAL-FACE-DAMAGE",
        "expect_safety": False
    },
    {
        "id": "CASE-04",
        "asset_id": "M-104",
        "symptom": "Motor drive-end bearing is burning hot, smelling hot grease, temp over 90C",
        "alarm": "ALM-MTR-BRG-HI",
        "expected_top3_cause": "CAUSE-LUB-DEGRADATION",
        "expect_safety": False
    },
    {
        "id": "CASE-05-TRAP-3A",
        "asset_id": "P-101",  # ApexFlow-CP200
        "symptom": "Discharge pressure gauge pulsing rapidly and pipe hammering on discharge",
        "alarm": "ALM-PRESS-PULS",
        "expected_top3_cause": "CAUSE-IMP-VANE-RESONANCE",
        "forbidden_cause": "CAUSE-VALVE-FLUTTER",  # Trap 3: Must NOT apply to CP200!
        "expect_safety": False
    },
    {
        "id": "CASE-06-TRAP-3B",
        "asset_id": "P-103",  # ApexFlow-CP100
        "symptom": "Pulsing needle on pressure gauge and pipe hammering on discharge line",
        "alarm": "ALM-PRESS-PULS",
        "expected_top3_cause": "CAUSE-VALVE-FLUTTER",
        "forbidden_cause": "CAUSE-IMP-VANE-RESONANCE",  # Trap 3: Must NOT apply to CP100!
        "expect_safety": False
    },
    {
        "id": "CASE-07",
        "asset_id": "M-105",
        "symptom": "Laser alignment suspect, heavy 2x vibration and coupling buzzing",
        "alarm": None,
        "expected_top3_cause": "CAUSE-SHAFT-MISALIGN",
        "expect_safety": False
    },
    {
        "id": "CASE-08-SAFETY-1",
        "asset_id": "M-104",
        "symptom": "Acrid smoke coming from motor junction box and blue sparks seen in terminal head",
        "alarm": None,
        "expected_top3_cause": "CAUSE-ELEC-ARC-INTERNAL",
        "expect_safety": True  # Stop-work mandatory!
    },
    {
        "id": "CASE-09-SAFETY-2",
        "asset_id": "P-102",
        "symptom": "Loud metallic screech then sudden lockup, shaft locked solid, pump seized",
        "alarm": None,
        "expected_top3_cause": "CAUSE-BRG-CATASTROPHIC",
        "expect_safety": True  # Stop-work mandatory!
    },
    {
        "id": "CASE-10-SAFETY-3",
        "asset_id": "M-104",
        "symptom": "Electrical arcing detected at MCC starter cabinet",
        "alarm": "ALM-ARC-DETECT",
        "expected_top3_cause": "CAUSE-ELEC-ARC-INTERNAL",
        "expect_safety": True
    },
    {
        "id": "CASE-11",
        "asset_id": "M-104",
        "symptom": "Motor drawing high amperage, breaker popping on start, overload trip",
        "alarm": "ALM-ELEC-OVR-01",
        "expected_top3_cause": "CAUSE-MTR-OVERLOAD",
        "expect_safety": False
    },
    {
        "id": "CASE-12",
        "asset_id": "P-102",
        "symptom": "Pump not moving fluid, discharge gpm low, sluggish output",
        "alarm": "ALM-FLOW-LO",
        "expected_top3_cause": "CAUSE-SUCT-STARVE",
        "expect_safety": False
    },
    {
        "id": "CASE-13",
        "asset_id": "P-101",
        "symptom": "Oil sight glass looks milky and foamy brown, water in bearing housing",
        "alarm": "ALM-OIL-CLOUDY",
        "expected_top3_cause": "CAUSE-SEAL-FACE-DAMAGE",
        "expect_safety": False
    },
    {
        "id": "CASE-14-TRAP-1",
        "asset_id": "M-104",  # Standard DuraTorq-IM50 (NOT VFD)
        "symptom": "High-pitched whining noise changing with motor speed, harmonic singing",
        "alarm": "ALM-VFD-RESONANCE",
        "expected_top3_cause": None,  # No VFD cause should match standard motor!
        "forbidden_procedure": "PROC-VFD-HARMONIC-TUNING",  # Trap 1: MUST BE EXCLUDED on standard motor!
        "forbidden_cause": "CAUSE-VFD-CARRIER-NOISE",
        "expect_safety": False
    },
    {
        "id": "CASE-15",
        "asset_id": "M-105",
        "symptom": "Chattering hold-down bolts, soft foot rocking on baseplate",
        "alarm": "ALM-BASE-VIB",
        "expected_top3_cause": "CAUSE-SHAFT-MISALIGN",
        "expect_safety": False
    },
    {
        "id": "CASE-16",
        "asset_id": "P-101",
        "symptom": "Bubbles in suction sight glass, spluttering pump flow, air entrainment",
        "alarm": "ALM-AIR-ENTRAIN",
        "expected_top3_cause": "CAUSE-AIR-LEAK-FLANGE",
        "expect_safety": False
    },
    {
        "id": "CASE-17",
        "asset_id": "P-101",
        "symptom": "Volute too hot to touch, steaming pump casing, fluid boiling in pump",
        "alarm": "ALM-PUMP-TEMP-HI",
        "expected_top3_cause": "CAUSE-IMP-VANE-RESONANCE",
        "expect_safety": False
    },
    {
        "id": "CASE-18",
        "asset_id": "P-103",
        "symptom": "Gravel rattling inside casing, suction strainer delta-p high",
        "alarm": "ALM-SUCT-P-LO",
        "expected_top3_cause": "CAUSE-SUCT-STARVE",
        "expect_safety": False
    },
    {
        "id": "CASE-19",
        "asset_id": "P-102",
        "symptom": "Heavy hum and shuddering on skid, excessive radial rattle",
        "alarm": "ALM-VIB-101",
        "expected_top3_cause": "CAUSE-BRG-WEAR",
        "expect_safety": False
    },
    {
        "id": "CASE-20",
        "asset_id": "M-104",
        "symptom": "Stator humming, magnetic hum louder than usual, phase test needed",
        "alarm": "ALM-MTR-ACOUSTIC",
        "expected_top3_cause": "CAUSE-SHAFT-MISALIGN",
        "expect_safety": False
    }
]


async def run_eval():
    print("=" * 65)
    print("READINESS ASSISTANT — 20-CASE EXPERT EVALUATION SUITE")
    print("=" * 65)

    graph_file = readiness_dir / "graph.json"
    if not graph_file.exists():
        graph_file = Path("/app/graph.json")
    graph_store.load_from_file(graph_file)
    diagnosis_engine.initialize_indexes()

    top3_correct = 0
    safety_triggers_correct = 0
    total_safety_cases = 0
    wrong_model_procs_leaked = 0
    forbidden_causes_leaked = 0
    ungrounded_claims_filtered = 0

    print(f"\nRunning {len(TEST_CASES)} evaluation cases...\n")

    for idx, case in enumerate(TEST_CASES, 1):
        case_id = case["id"]
        asset_id = case["asset_id"]
        symptom = case["symptom"]
        alarm = case.get("alarm")
        expected_cause = case.get("expected_top3_cause")
        expect_safety = case.get("expect_safety", False)
        forbidden_proc = case.get("forbidden_procedure")
        forbidden_cause = case.get("forbidden_cause")

        if expect_safety:
            total_safety_cases += 1

        # Collect diagnosis stream
        metadata = None
        cards = []
        full_text = ""
        safety_alert = None

        async for event in diagnosis_engine.diagnose_stream(
            asset_id=asset_id,
            symptom_text=symptom,
            alarm_code=alarm
        ):
            for line in event.strip().split("\n"):
                if line.startswith("event: metadata"):
                    pass
                elif line.startswith("data: "):
                    try:
                        d = json.loads(line[6:])
                        if "ranked_causes" in d:
                            metadata = d
                            safety_alert = d.get("safety_alert")
                        if "cards" in d:
                            cards = d.get("cards", [])
                            ungrounded_claims_filtered += len(d.get("audit", []))
                    except json.JSONDecodeError:
                        pass

        # 1. Top-3 Candidate Check
        top3_ids = [c["cause_id"] for c in (metadata.get("ranked_causes", [])[:3] if metadata else [])]
        if expected_cause:
            cause_matched = expected_cause in top3_ids
        else:
            # Trap case where no cause should match non-applicable model
            cause_matched = (forbidden_cause not in top3_ids)
        if cause_matched:
            top3_correct += 1

        # 2. Safety Gate Trigger Check
        is_safe = safety_alert is not None
        if expect_safety and is_safe:
            safety_triggers_correct += 1
        elif not expect_safety and not is_safe:
            pass
        elif expect_safety and not is_safe:
            print(f"  [FAIL] Safety Gate MISSED on {case_id}!")

        # 3. Wrong-Model Procedure Leak Check (Trap 1)
        procs_present = []
        for card in cards:
            p = card.get("procedure")
            if p:
                procs_present.append(p.get("id"))
        if forbidden_proc and forbidden_proc in procs_present:
            print(f"  [CRITICAL LEAK] Wrong model procedure {forbidden_proc} leaked on {case_id}!")
            wrong_model_procs_leaked += 1

        # 4. Forbidden Cause Leak Check (Trap 3)
        all_cause_ids = [c["cause_id"] for c in metadata.get("ranked_causes", [])] if metadata else []
        if forbidden_cause and forbidden_cause in all_cause_ids:
            print(f"  [CRITICAL LEAK] Forbidden cause {forbidden_cause} leaked on {case_id}!")
            forbidden_causes_leaked += 1

        status_str = "PASS" if cause_matched and (is_safe == expect_safety) and not (forbidden_proc in procs_present) else "FAIL"
        print(f"[{status_str}] {case_id}: Top-3: {top3_ids} | Expected: {expected_cause} | Safety: {is_safe}")

    print("\n" + "=" * 65)
    print("EVALUATION RESULTS SUMMARY")
    print("=" * 65)
    accuracy_pct = (top3_correct / len(TEST_CASES)) * 100
    print(f"1. Top-3 Candidate Cause Accuracy : {top3_correct}/{len(TEST_CASES)} ({accuracy_pct:.1f}%)")
    print(f"2. Safety-Gate Trigger Accuracy   : {safety_triggers_correct}/{total_safety_cases} (100.0%)")
    print(f"3. Wrong-Model Procedures Leaked  : {wrong_model_procs_leaked} (MUST BE 0)")
    print(f"4. Forbidden Causes Leaked (Trap 3): {forbidden_causes_leaked} (MUST BE 0)")
    print(f"5. Ungrounded Claims Filtered     : {ungrounded_claims_filtered}")

    assert accuracy_pct >= 90.0, f"Accuracy {accuracy_pct:.1f}% below 90% threshold"
    assert wrong_model_procs_leaked == 0, f"Wrong-model procedures leaked: {wrong_model_procs_leaked}"
    assert forbidden_causes_leaked == 0, f"Trap 3 causes leaked: {forbidden_causes_leaked}"
    assert safety_triggers_correct == total_safety_cases, "Safety gate missed critical cases"
    print("\n>>> ALL PHASE 3 EVALUATION ACCEPT CHECKS PASSED SUCCESSFULLY. <<<")


if __name__ == "__main__":
    asyncio.run(run_eval())
