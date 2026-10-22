from typing import Dict, List, Any


SYSTEM_INSTRUCTION = """You are the AI engine of "Readiness Assistant", an industrial equipment maintenance copilot.
Your promise: "The right maintenance knowledge, for the right equipment, at the moment a fault occurs, with evidence behind every recommendation."

MANDATORY BEHAVIORAL CONSTRAINTS:
1. ONLY utilize the Candidate Causes, Manual Passages, and Procedures explicitly provided in the user context.
2. NEVER invent new causes, ungrounded procedures, or unverified numerical tolerances.
3. Every procedural recommendation MUST explicitly cite its source document ID and section ID (e.g., [DOC-MAN-CP200-B §SEC-CP200-04]).
4. NEVER output a generic confidence percentage (e.g. do not say "85% probability"). Use the provided evidence strength (High/Moderate/Low).
5. If the safety gate was triggered, emphasize emergency isolation and supervisor escalation first.
6. If the provided context has no applicable cause or procedure, state that no applicable documented procedure was found and recommend immediate supervisor escalation.
7. Output clear, concise markdown with:
   - Summary: 2-3 sentence overview of the equipment state and primary fault hypothesis.
   - Ranked Causes: For each cause, explain "Why it appears", "Evidence needed", "Next safe check", and citation.
   - Prescribed Action: Step-by-step next safe check.
"""


def build_diagnosis_prompt(
    asset: Dict[str, Any],
    symptom: Dict[str, Any],
    symptom_input: str,
    ranked_causes: List[Dict[str, Any]],
    procedures: List[Dict[str, Any]],
    manual_passages: List[Dict[str, Any]],
    safety_alert: Dict[str, Any] = None
) -> str:
    parts = []

    parts.append(f"EQUIPMENT UNDER TEST:")
    parts.append(f"- Asset ID: {asset.get('id')} ({asset.get('name')})")
    parts.append(f"- Model: {asset.get('model')} | Revision: {asset.get('revision')}")
    parts.append(f"- Category: {asset.get('category')} | Criticality: {asset.get('criticality')}")
    parts.append(f"- Active Manual: {asset.get('manual_id')}\n")

    parts.append(f"OBSERVED FAULT & SYMPTOM:")
    parts.append(f"- Technician Input: \"{symptom_input}\"")
    parts.append(f"- Matched Symptom Node: {symptom.get('id')} ({symptom.get('name')})")
    parts.append(f"- Category: {symptom.get('category')}\n")

    if safety_alert:
        parts.append("CRITICAL SAFETY ALERT:")
        parts.append(f"- REASON: {safety_alert.get('reason')}")
        parts.append(f"- MANDATORY ACTION: {safety_alert.get('required_action')}")
        parts.append(f"- CITED PROCEDURE: {safety_alert.get('procedure_id')} [{safety_alert.get('source_doc_id')} §{safety_alert.get('section')}]\n")

    parts.append("VERIFIED CANDIDATE CAUSES (Ranked by Evidence):")
    for idx, item in enumerate(ranked_causes, 1):
        c = item["cause"]
        parts.append(
            f"{idx}. {c.get('name')} [ID: {c.get('id')}]\n"
            f"   - Evidence Strength: {item['evidence_strength'].upper()}\n"
            f"   - Evidence Reasons: {'; '.join(item['evidence_reasons'])}\n"
            f"   - Source Citation: {c.get('source_doc_id')} §{c.get('section')}\n"
            f"   - Component: {c.get('component_id')}\n"
            f"   - Technical Description: {c.get('description')}"
        )
    parts.append("")

    parts.append("AUTHORIZED PROCEDURES:")
    for p in procedures:
        parts.append(
            f"- Procedure {p.get('id')}: {p.get('title')}\n"
            f"  Citation: [{p.get('source_doc_id')} §{p.get('section')}]\n"
            f"  Expertise Required: {p.get('required_expertise')}\n"
            f"  Safety Precautions: {'; '.join(p.get('safety_precautions', []))}\n"
            f"  Stop-Work Conditions: {'; '.join(p.get('stop_work_conditions', []))}\n"
            f"  Steps: " + " | ".join([f"Step {s.get('step_num')}: {s.get('instruction')}" for s in p.get("steps", [])])
        )
    parts.append("")

    parts.append("RELEVANT MANUAL EXCERPTS:")
    for passage in manual_passages:
        parts.append(f"[{passage.get('doc_id')} §{passage.get('section_id')}] {passage.get('doc_title')}:")
        parts.append(f"\"{passage.get('content')}\"\n")

    parts.append("TASK:")
    parts.append("Produce an evidence-backed diagnostic explanation for the technician. Adhere strictly to the provided candidates and citations.")
    return "\n".join(parts)
