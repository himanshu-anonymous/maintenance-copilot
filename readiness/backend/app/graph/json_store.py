import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
import asyncio

from app.graph.store import GraphStore

logger = logging.getLogger(__name__)


class JsonGraphStore(GraphStore):
    """
    High-performance in-memory graph store.
    All hot-path traversals execute in < 1ms without disk or network I/O.
    Supports atomic hot-swapping after ingestion.
    """

    def __init__(self):
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._nodes_by_type: Dict[str, List[Dict[str, Any]]] = {}
        self._outgoing_edges: Dict[str, List[Dict[str, Any]]] = {}
        self._incoming_edges: Dict[str, List[Dict[str, Any]]] = {}
        self._edges_by_type: Dict[str, List[Dict[str, Any]]] = {}
        self._incidents_by_cause: Dict[str, List[Dict[str, Any]]] = {}
        self._raw_edges: List[Dict[str, Any]] = []
        self._metadata: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    def load_from_file(self, file_path: Path) -> None:
        """Loads and indexes graph.json synchronously."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.load_from_dict(data)

    def load_from_dict(self, graph_dict: Dict[str, Any]) -> None:
        """Rebuilds memory indexes atomically from graph dictionary."""
        new_nodes: Dict[str, Dict[str, Any]] = {}
        new_nodes_by_type: Dict[str, List[Dict[str, Any]]] = {}
        new_outgoing: Dict[str, List[Dict[str, Any]]] = {}
        new_incoming: Dict[str, List[Dict[str, Any]]] = {}
        new_edges_by_type: Dict[str, List[Dict[str, Any]]] = {}
        new_incidents_by_cause: Dict[str, List[Dict[str, Any]]] = {}

        raw_nodes = graph_dict.get("nodes", [])
        raw_edges = graph_dict.get("edges", [])

        for n in raw_nodes:
            nid = n["id"]
            ntype = n.get("type", "Unknown")
            new_nodes[nid] = n
            new_nodes_by_type.setdefault(ntype, []).append(n)

        for e in raw_edges:
            src = e["source"]
            tgt = e["target"]
            etype = e["edge_type"]

            new_outgoing.setdefault(src, []).append(e)
            new_incoming.setdefault(tgt, []).append(e)
            new_edges_by_type.setdefault(etype, []).append(e)

            # Pre-index verified incidents by cause
            if etype == "POSSIBLY_INDICATES" and e.get("origin") == "technician_reported":
                if e.get("verification_status") == "verified":
                    incident_node = new_nodes.get(src)
                    if incident_node:
                        new_incidents_by_cause.setdefault(tgt, []).append(incident_node)

        # Atomic swap
        self._nodes = new_nodes
        self._nodes_by_type = new_nodes_by_type
        self._outgoing_edges = new_outgoing
        self._incoming_edges = new_incoming
        self._edges_by_type = new_edges_by_type
        self._incidents_by_cause = new_incidents_by_cause
        self._raw_edges = raw_edges
        self._metadata = graph_dict.get("metadata", {})

        logger.info(f"JsonGraphStore loaded: {len(self._nodes)} nodes, {len(self._raw_edges)} edges.")

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        return self._nodes.get(node_id)

    def get_nodes(self, node_type: Optional[str] = None) -> List[Dict[str, Any]]:
        if node_type:
            return list(self._nodes_by_type.get(node_type, []))
        return list(self._nodes.values())

    def get_edges(
        self,
        source: Optional[str] = None,
        target: Optional[str] = None,
        edge_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        candidates = self._raw_edges
        if source:
            candidates = self._outgoing_edges.get(source, [])
        elif target:
            candidates = self._incoming_edges.get(target, [])
        elif edge_type:
            candidates = self._edges_by_type.get(edge_type, [])

        results = []
        for e in candidates:
            if source and e["source"] != source:
                continue
            if target and e["target"] != target:
                continue
            if edge_type and e["edge_type"] != edge_type:
                continue
            results.append(e)
        return results

    def _is_applicable(self, edge: Dict[str, Any], model: Optional[str]) -> bool:
        """Check if an edge applies to the requested equipment model."""
        if not model:
            return True
        models = edge.get("applicable_models", [])
        if not models or "*" in models:
            return True
        return model in models

    def get_causes_for_symptom(
        self,
        symptom_id: str,
        applicable_model: Optional[str] = None
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Traverse POSSIBLY_INDICATES from Symptom to Cause.
        Filters out causes not applicable to the given model.
        """
        results: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        outgoing = self._outgoing_edges.get(symptom_id, [])

        for edge in outgoing:
            if edge.get("edge_type") != "POSSIBLY_INDICATES":
                continue
            if not self._is_applicable(edge, applicable_model):
                continue
            cause_node = self._nodes.get(edge["target"])
            if cause_node and cause_node.get("type") == "Cause":
                # Double-check cause node applicable_models
                node_models = cause_node.get("applicable_models", [])
                if not node_models or "*" in node_models or not applicable_model or applicable_model in node_models:
                    results.append((cause_node, edge))

        return results

    def get_procedures_for_cause(
        self,
        cause_id: str,
        applicable_model: Optional[str] = None
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Traverse INVESTIGATED_BY from Cause to Procedure.
        Filters out procedures not applicable to the given model.
        """
        results: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        outgoing = self._outgoing_edges.get(cause_id, [])

        for edge in outgoing:
            if edge.get("edge_type") != "INVESTIGATED_BY":
                continue
            if not self._is_applicable(edge, applicable_model):
                continue
            proc_node = self._nodes.get(edge["target"])
            if proc_node and proc_node.get("type") == "Procedure":
                # Verify procedure node applicable_models
                proc_models = proc_node.get("applicable_models", [])
                if not proc_models or "*" in proc_models or not applicable_model or applicable_model in proc_models:
                    results.append((proc_node, edge))

        return results

    def get_components_for_equipment(self, equipment_id: str) -> List[Dict[str, Any]]:
        """Returns all Component nodes linked via HAS_COMPONENT edges."""
        components = []
        outgoing = self._outgoing_edges.get(equipment_id, [])
        for edge in outgoing:
            if edge.get("edge_type") == "HAS_COMPONENT":
                node = self._nodes.get(edge["target"])
                if node:
                    components.append(node)
        return components

    def get_verified_incidents(
        self,
        cause_id: Optional[str] = None,
        asset_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query historical verified incidents."""
        if cause_id and cause_id in self._incidents_by_cause:
            incidents = self._incidents_by_cause[cause_id]
            if asset_id:
                return [inc for inc in incidents if inc.get("asset_id") == asset_id]
            return list(incidents)

        all_incidents = self._nodes_by_type.get("Incident", [])
        verified = [inc for inc in all_incidents if inc.get("supervisor_approved") is True]
        if cause_id:
            verified = [inc for inc in verified if inc.get("confirmed_cause_id") == cause_id]
        if asset_id:
            verified = [inc for inc in verified if inc.get("asset_id") == asset_id]
        return verified

    def add_verified_outcome(self, outcome_data: Dict[str, Any]) -> None:
        """
        Incorporates a supervisor-verified outcome into the graph.
        Adds Incident node and verified edge to Cause.
        """
        inc_id = outcome_data.get("id") or f"INC-{len(self._nodes_by_type.get('Incident', [])) + 1:04d}"
        incident_node = {
            "id": inc_id,
            "type": "Incident",
            "asset_id": outcome_data.get("asset_id"),
            "symptom_id": outcome_data.get("symptom_id"),
            "confirmed_cause_id": outcome_data.get("confirmed_cause_id"),
            "procedure_used_id": outcome_data.get("procedure_used_id"),
            "outcome_status": "resolved",
            "technician": outcome_data.get("technician", "technician_user"),
            "supervisor_approved": True,
            "approved_by": outcome_data.get("approved_by", "supervisor_user"),
            "incident_date": outcome_data.get("incident_date", "2024-10-22"),
            "resolution_notes": outcome_data.get("resolution_notes", "")
        }

        # New verified edge
        verified_edge = {
            "source": inc_id,
            "target": outcome_data.get("confirmed_cause_id"),
            "edge_type": "POSSIBLY_INDICATES",
            "source_doc_id": inc_id,
            "section": "resolution_notes",
            "applicable_models": [outcome_data.get("model")] if outcome_data.get("model") else [],
            "revision": "Verified Record",
            "effective_date": outcome_data.get("incident_date", "2024-10-22"),
            "origin": "technician_reported",
            "verification_status": "verified",
            "approved_by": outcome_data.get("approved_by")
        }

        # Update in-memory collections
        self._nodes[inc_id] = incident_node
        self._nodes_by_type.setdefault("Incident", []).append(incident_node)
        self._raw_edges.append(verified_edge)
        self._outgoing_edges.setdefault(inc_id, []).append(verified_edge)
        self._incoming_edges.setdefault(verified_edge["target"], []).append(verified_edge)
        self._edges_by_type.setdefault("POSSIBLY_INDICATES", []).append(verified_edge)
        self._incidents_by_cause.setdefault(verified_edge["target"], []).append(incident_node)

        logger.info(f"Added verified outcome {inc_id} to graph for cause {verified_edge['target']}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "nodes": list(self._nodes.values()),
            "edges": list(self._raw_edges),
            "metadata": {
                "total_nodes": len(self._nodes),
                "total_edges": len(self._raw_edges)
            }
        }


# Global in-memory singleton
graph_store = JsonGraphStore()
