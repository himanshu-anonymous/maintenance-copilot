import re
from typing import Dict, List, Optional, Tuple, Set


def normalize_text(text: str) -> str:
    """Normalize input text: lowercased, punctuation stripped, extra spaces removed."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class SymptomAliasMapper:
    """
    Rapid symptom mapper using exact alarm code lookup, alias dictionary matching,
    and phrase containment. Runs in < 2 ms without LLM overhead.
    """

    def __init__(self, symptoms: List[Dict]):
        self._alarm_map: Dict[str, str] = {}
        self._alias_map: Dict[str, str] = {}
        self._symptom_keywords: Dict[str, List[str]] = {}

        for s in symptoms:
            sid = s["id"]
            # Map alarm codes
            for code in s.get("alarm_codes", []):
                self._alarm_map[normalize_text(code)] = sid
                self._alarm_map[code.upper().strip()] = sid

            # Map aliases
            for alias in s.get("aliases", []):
                self._alias_map[normalize_text(alias)] = sid

            # Name and keywords
            norm_name = normalize_text(s["name"])
            self._alias_map[norm_name] = sid
            self._symptom_keywords[sid] = norm_name.split()

    def match(
        self,
        symptom_text: str,
        alarm_code: Optional[str] = None
    ) -> List[Tuple[str, float, str]]:
        """
        Returns list of (symptom_id, match_score, match_type).
        Match types: 'alarm_code', 'exact_alias', 'phrase_contains', 'keyword'
        """
        results: Dict[str, Tuple[float, str]] = {}
        norm_input = normalize_text(symptom_text)

        # 1. Alarm code match (highest confidence)
        if alarm_code:
            norm_alarm = normalize_text(alarm_code)
            raw_alarm = alarm_code.upper().strip()
            if raw_alarm in self._alarm_map:
                sid = self._alarm_map[raw_alarm]
                results[sid] = (1.0, "alarm_code")
            elif norm_alarm in self._alarm_map:
                sid = self._alarm_map[norm_alarm]
                results[sid] = (1.0, "alarm_code")

        # 2. Check alarm codes present within symptom_text
        for code, sid in self._alarm_map.items():
            if code in norm_input or code in symptom_text.upper():
                if sid not in results:
                    results[sid] = (0.95, "alarm_code_in_text")

        # 3. Exact alias match
        if norm_input in self._alias_map:
            sid = self._alias_map[norm_input]
            if sid not in results or results[sid][0] < 0.90:
                results[sid] = (0.90, "exact_alias")

        # 4. Phrase containment
        for alias, sid in self._alias_map.items():
            if alias and (alias in norm_input or norm_input in alias):
                score = 0.85 if len(alias) > 6 else 0.70
                if sid not in results or results[sid][0] < score:
                    results[sid] = (score, "phrase_contains")

        # 5. Fallback keyword overlap
        input_tokens = set(norm_input.split())
        for sid, kw_list in self._symptom_keywords.items():
            overlap = input_tokens.intersection(set(kw_list))
            if overlap:
                score = 0.50 + (0.15 * len(overlap))
                if sid not in results or results[sid][0] < score:
                    results[sid] = (min(score, 0.75), "keyword_overlap")

        sorted_matches = sorted(
            [(sid, score, mtype) for sid, (score, mtype) in results.items()],
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_matches
