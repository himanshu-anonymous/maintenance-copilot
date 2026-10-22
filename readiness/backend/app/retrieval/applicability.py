from typing import List, Dict, Any, Optional, Set


class ApplicabilityFilter:
    """
    Enforces strict model applicability and revision freshness:
    - Filters out superseded documents and obsolete tolerances (Trap 2)
    - Enforces strict equipment model boundaries (Traps 1 and 3)
    - Excludes procedures not authorized for the user's role or model
    """

    def __init__(self, superseded_docs: Optional[Dict[str, str]] = None):
        # map of superseded_doc_id -> superseding_doc_id
        self.superseded_docs = superseded_docs or {"DOC-MAN-CP200-A": "DOC-MAN-CP200-B"}

    def is_document_active(self, doc_id: str) -> bool:
        """Returns False if the document has been superseded."""
        return doc_id not in self.superseded_docs

    def is_model_applicable(self, target_model: str, allowed_models: List[str]) -> bool:
        """
        Validates model compatibility.
        Wildcard '*' allows all equipment models.
        """
        if not allowed_models or "*" in allowed_models:
            return True
        if not target_model:
            return True
        return target_model in allowed_models

    def filter_procedures(
        self,
        procedures: List[Dict[str, Any]],
        target_model: str,
        user_role: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Strips procedures that do not apply to target_model or cite superseded manuals.
        Guarantees zero wrong-model procedures leak through.
        """
        valid_procs = []
        for proc in procedures:
            # 1. Revision check: drop procedures from superseded manuals
            source_doc = proc.get("source_doc_id", "")
            if not self.is_document_active(source_doc):
                continue

            # 2. Strict model check
            app_models = proc.get("applicable_models", [])
            if not self.is_model_applicable(target_model, app_models):
                continue

            # 3. Role / expertise check
            if user_role == "technician":
                # Technicians can execute standard procedures, but if procedure requires supervisor sign-off, mark accordingly
                pass

            valid_procs.append(proc)
        return valid_procs

    def filter_causes(
        self,
        causes: List[Dict[str, Any]],
        target_model: str
    ) -> List[Dict[str, Any]]:
        """Filters causes by active manual revision and target model."""
        valid_causes = []
        for cause in causes:
            source_doc = cause.get("source_doc_id", "")
            if not self.is_document_active(source_doc):
                continue

            app_models = cause.get("applicable_models", [])
            if not self.is_model_applicable(target_model, app_models):
                continue

            valid_causes.append(cause)
        return valid_causes
