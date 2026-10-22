import re
from typing import Dict, Any, List, Tuple, Optional
from app.retrieval.aliases import normalize_text


class SafetyGate:
    """
    Enforces mandatory industrial stop-work safety rules.
    If conditions match fire, smoke, arcing, exposed conductors, or sudden seizure,
    the emergency shutdown procedure is placed FIRST and immediate escalation is required.
    """

    STOP_WORK_PATTERNS = [
        r"\bsmoke\b",
        r"\bsmoking\b",
        r"\bburning\s+(?:smell|odor|plastic|rubber|insulation|wire|cable)\b",
        r"\bacrid\b",
        r"\barc\b",
        r"\barcing\b",
        r"\bsparks?\b",
        r"\bsparking\b",
        r"\bflashover\b",
        r"\blive parts?\b",
        r"\bexposed conductor\b",
        r"\belectrical smell\b",
        r"\bseized?\b",
        r"\bseizure\b",
        r"\blockup\b",
        r"\block\s*rotor\b",
        r"\bgrinding\s+with\s+sudden\b",
        r"\bshaft\s+locked\b",
        r"\bflame\b",
        r"\bfire\b"
    ]

    EMERGENCY_ALARM_CODES = {
        "ALM-ARC-DETECT",
        "ALM-FIRE-SMOKE-01",
        "ALM-STALL-LOCK",
        "SPEED-ZERO-TRIP"
    }

    def evaluate(
        self,
        symptom_text: str,
        alarm_code: Optional[str] = None,
        observations: Optional[List[str]] = None
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Evaluates input text against safety gate rules.
        Returns (is_triggered, trigger_reason, emergency_action_dict).
        """
        combined_text = normalize_text(symptom_text)
        if observations:
            combined_text += " " + " ".join([normalize_text(o) for o in observations])

        # 1. Alarm code check
        if alarm_code and alarm_code.upper().strip() in self.EMERGENCY_ALARM_CODES:
            reason = f"Safety stop-work triggered by critical alarm code: {alarm_code}"
            return True, reason, self._get_emergency_procedure(reason)

        # 2. Text regex pattern checks
        for pattern in self.STOP_WORK_PATTERNS:
            match = re.search(pattern, combined_text)
            if match:
                matched_term = match.group(0)
                reason = f"Mandatory stop-work condition detected: '{matched_term}'. Potential immediate arc flash, electrical fire, or mechanical seizure hazard."
                return True, reason, self._get_emergency_procedure(reason)

        return False, None, None

    def _get_emergency_procedure(self, reason: str) -> Dict[str, Any]:
        return {
            "procedure_id": "PROC-SAFE-EMERGENCY-SHUTDOWN",
            "title": "Emergency Electrical Isolation & Lockout/Tagout (LOTO)",
            "source_doc_id": "DOC-MAN-SAFETY-01",
            "section": "SEC-SAFE-01",
            "reason": reason,
            "required_action": "IMMEDIATE EMERGENCY SHUTDOWN AND ESCALATION TO QUALIFIED PERSONNEL. DO NOT ATTEMPT IN-SERVICE DIAGNOSTIC TESTING.",
            "steps": [
                "1. Immediately depress local Emergency Stop pushbutton.",
                "2. Open breaker in MCC-415; apply personal safety padlock and danger tag.",
                "3. Perform live-dead-live zero voltage verification at junction box.",
                "4. Immediately notify Plant Electrical Supervisor. Do not re-energize without supervisor signoff."
            ],
            "label": "Documented"
        }


safety_gate = SafetyGate()
