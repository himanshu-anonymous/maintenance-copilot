from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple


class GraphStore(ABC):
    """
    Abstract interface for graph storage and traversal operations.
    JsonGraphStore serves the hot path entirely in memory.
    Neo4jGraphStore serves as an optional mirror writer & cross-equipment query provider.
    """

    @abstractmethod
    def load_from_dict(self, graph_dict: Dict[str, Any]) -> None:
        """Load or reload graph nodes and edges."""
        pass

    @abstractmethod
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve node attributes by unique identifier."""
        pass

    @abstractmethod
    def get_nodes(self, node_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve all nodes, optionally filtered by node type."""
        pass

    @abstractmethod
    def get_edges(
        self,
        source: Optional[str] = None,
        target: Optional[str] = None,
        edge_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query edges with optional endpoint and type filters."""
        pass

    @abstractmethod
    def get_causes_for_symptom(
        self,
        symptom_id: str,
        applicable_model: Optional[str] = None
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Traverse POSSIBLY_INDICATES from Symptom to Cause.
        Filters out causes not applicable to the given equipment model.
        Returns pairs of (Cause Node, Edge).
        """
        pass

    @abstractmethod
    def get_procedures_for_cause(
        self,
        cause_id: str,
        applicable_model: Optional[str] = None
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Traverse INVESTIGATED_BY from Cause to Procedure.
        Filters out procedures not authorized/applicable to the given equipment model.
        Returns pairs of (Procedure Node, Edge).
        """
        pass

    @abstractmethod
    def get_verified_incidents(
        self,
        cause_id: Optional[str] = None,
        asset_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve historical verified incidents matching cause or asset."""
        pass

    @abstractmethod
    def add_verified_outcome(self, outcome_data: Dict[str, Any]) -> None:
        """Atomically incorporate a newly supervisor-verified incident/outcome into the graph."""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize complete graph representation for snapshot or dashboard."""
        pass
