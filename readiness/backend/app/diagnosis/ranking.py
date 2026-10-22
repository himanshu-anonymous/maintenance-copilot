from typing import Dict, List, Any, Optional, Tuple


class DeterministicCauseRanker:
    """
    Ranks diagnostic candidate causes deterministically without arbitrary percentages.
    Outputs qualitative evidence strength ('high', 'moderate', 'low') with explicit reasons:
    - Documented evidence in applicable manual
    - Verified past incidents on same or related equipment
    - Observed operational symptoms matching
    """

    def rank(
        self,
        candidate_causes: List[Dict[str, Any]],
        symptom_match_score: float,
        asset_id: str,
        asset_model: str,
        verified_incidents: List[Dict[str, Any]],
        observations: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        ranked = []

        for cause in candidate_causes:
            cid = cause["id"]
            # 1. Documented evidence score
            has_doc = bool(cause.get("source_doc_id") and cause.get("section"))
            doc_score = 3.0 if has_doc else 0.0

            # 2. Verified incident history
            same_asset_incidents = [inc for inc in verified_incidents if inc.get("confirmed_cause_id") == cid and inc.get("asset_id") == asset_id]
            same_model_incidents = [inc for inc in verified_incidents if inc.get("confirmed_cause_id") == cid]
            
            history_score = (len(same_asset_incidents) * 2.5) + (len(same_model_incidents) * 1.0)

            # 3. Observation alignment score
            obs_score = 0.0
            obs_notes = []
            if observations:
                cause_text = (cause.get("name", "") + " " + cause.get("description", "")).lower()
                for obs in observations:
                    obs_words = [w for w in obs.lower().split() if len(w) > 3]
                    if any(w in cause_text for w in obs_words):
                        obs_score += 1.5
                        obs_notes.append(obs)

            # Total deterministic score
            total_score = (symptom_match_score * 3.0) + doc_score + history_score + obs_score

            # Qualitative Evidence Strength
            reasons = []
            if has_doc:
                reasons.append(f"Documented in {cause.get('source_doc_id')} §{cause.get('section')}")
            if same_asset_incidents:
                reasons.append(f"{len(same_asset_incidents)} verified incident(s) on asset {asset_id}")
            elif same_model_incidents:
                reasons.append(f"{len(same_model_incidents)} verified incident(s) across {asset_model} fleet")
            if obs_notes:
                reasons.append(f"Aligns with recorded observation: '{obs_notes[0]}'")

            if total_score >= 8.0 or len(same_asset_incidents) >= 1:
                strength = "high"
            elif total_score >= 4.5:
                strength = "moderate"
            else:
                strength = "low"

            ranked.append({
                "cause": cause,
                "score": total_score,
                "evidence_strength": strength,
                "evidence_reasons": reasons,
                "same_asset_verified_count": len(same_asset_incidents),
                "fleet_verified_count": len(same_model_incidents),
                "label": "Documented" if has_doc else "Inferred"
            })

        # Sort descending by deterministic score
        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked


cause_ranker = DeterministicCauseRanker()
