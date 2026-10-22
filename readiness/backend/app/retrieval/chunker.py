from typing import List, Dict, Any, Optional
from app.graph.json_store import graph_store


class DocumentChunker:
    """Retrieves relevant manual document sections with exact doc_id and section_id citations."""

    def __init__(self):
        pass

    def get_sections_for_sources(self, source_tuples: List[tuple]) -> List[Dict[str, Any]]:
        """
        source_tuples: List of (doc_id, section_id)
        Returns list of section dicts with content and metadata.
        """
        results = []
        seen = set()

        for doc_id, sec_id in source_tuples:
            key = (doc_id, sec_id)
            if key in seen:
                continue
            seen.add(key)

            doc_node = graph_store.get_node(doc_id)
            if not doc_node:
                continue

            for section in doc_node.get("sections", []):
                if section.get("section_id") == sec_id or sec_id == "*":
                    results.append({
                        "doc_id": doc_id,
                        "doc_title": doc_node.get("title"),
                        "revision": doc_node.get("revision"),
                        "section_id": section.get("section_id"),
                        "section_title": section.get("title"),
                        "content": section.get("content")
                    })
        return results
