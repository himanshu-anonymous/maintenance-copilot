from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from app.graph.json_store import graph_store

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])


@router.get("")
async def get_full_graph():
    """Returns the entire in-memory knowledge graph."""
    data = graph_store.to_dict()
    return data


@router.get("/subgraph/{asset_id}")
async def get_asset_subgraph(asset_id: str):
    """
    Returns an interactive subgraph centered around an asset.
    Includes components, applicable symptoms, candidate causes, procedures, and verified outcomes.
    Formatted for @xyflow/react (React Flow).
    """
    asset = graph_store.get_node(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found in graph")

    nodes = []
    edges = []
    node_ids = set()

    # 1. Add Asset Node
    nodes.append({
        "id": asset["id"],
        "type": "assetNode",
        "data": {
            "label": f"{asset.get('name', asset['id'])} ({asset.get('model', '')})",
            "category": asset.get("category", "equipment"),
            "status": asset.get("status", "operational"),
            "raw": asset
        },
        "position": {"x": 250, "y": 50}
    })
    node_ids.add(asset["id"])

    # 2. Add Components
    components = graph_store.get_components_for_equipment(asset_id)
    for idx, comp in enumerate(components):
        cid = comp["id"]
        if cid not in node_ids:
            nodes.append({
                "id": cid,
                "type": "componentNode",
                "data": {
                    "label": comp.get("name", cid),
                    "raw": comp
                },
                "position": {"x": 50 + idx * 160, "y": 180}
            })
            node_ids.add(cid)
            edges.append({
                "id": f"e-{asset_id}-{cid}",
                "source": asset_id,
                "target": cid,
                "label": "HAS_COMPONENT",
                "animated": False,
                "style": {"stroke": "#94a3b8"}
            })

    # 3. Add Verified Incidents & Outcomes
    incidents = graph_store.get_verified_incidents(asset_id=asset_id)
    for idx, inc in enumerate(incidents):
        iid = inc["id"]
        if iid not in node_ids:
            nodes.append({
                "id": iid,
                "type": "incidentNode",
                "data": {
                    "label": f"Verified Outcome: {inc.get('confirmed_cause_id')}",
                    "approved_by": inc.get("approved_by"),
                    "technician": inc.get("technician"),
                    "status": "verified",
                    "raw": inc
                },
                "position": {"x": 500, "y": 150 + idx * 90}
            })
            node_ids.add(iid)
            edges.append({
                "id": f"e-{asset_id}-{iid}",
                "source": asset_id,
                "target": iid,
                "label": "HAS_HISTORY",
                "animated": True,
                "style": {"stroke": "#10b981", "strokeWidth": 2}
            })

            # Also connect to cause if present
            cid = inc.get("confirmed_cause_id")
            if cid:
                cause_node = graph_store.get_node(cid)
                if cause_node and cid not in node_ids:
                    nodes.append({
                        "id": cid,
                        "type": "causeNode",
                        "data": {
                            "label": cause_node.get("name", cid),
                            "raw": cause_node
                        },
                        "position": {"x": 750, "y": 150 + idx * 90}
                    })
                    node_ids.add(cid)
                edges.append({
                    "id": f"e-{iid}-{cid}",
                    "source": iid,
                    "target": cid,
                    "label": "CONFIRMED_CAUSE",
                    "style": {"stroke": "#10b981", "strokeDasharray": "5,5"}
                })

    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges)
    }
