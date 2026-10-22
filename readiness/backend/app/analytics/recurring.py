from datetime import datetime
from typing import Dict, Any, List
from collections import defaultdict
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.workflow.models import Outcome, Asset, WorkOrder
from app.graph.json_store import graph_store


async def calculate_recurring_faults(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Computes recurring fault clusters across assets and causes,
    approximating MTBF (Mean Time Between Failures) based on historical verified incidents.
    """
    # 1. Gather all verified outcomes from graph and DB
    verified_incidents = graph_store.get_verified_incidents()
    
    # Also fetch outcomes from DB
    stmt = select(Outcome)
    res = await db.execute(stmt)
    db_outcomes = list(res.scalars().all())

    # Map causes to readable names
    cause_names = {}
    for c in graph_store.get_nodes("Cause"):
        cause_names[c["id"]] = c.get("name", c["id"])

    # Cluster by (asset_id, confirmed_cause_id)
    clusters = defaultdict(list)

    # Process graph incidents
    for inc in verified_incidents:
        aid = inc.get("asset_id", "UNKNOWN")
        cid = inc.get("confirmed_cause_id", "UNKNOWN")
        date_str = inc.get("incident_date", "2024-01-01")
        clusters[(aid, cid)].append({
            "source": "historical_graph",
            "date": date_str,
            "downtime_hours": 2.5
        })

    # Process DB outcomes
    for out in db_outcomes:
        date_str = out.verification_timestamp.strftime("%Y-%m-%d")
        clusters[(out.asset_id, out.confirmed_cause_id)].append({
            "source": "verified_db",
            "date": date_str,
            "downtime_hours": out.downtime_hours
        })

    results = []
    # Assumed standard continuous operating hours per year = 8760
    operating_hours_window = 8760.0

    for (aid, cid), events in clusters.items():
        count = len(events)
        total_downtime = sum(e["downtime_hours"] for e in events)
        
        # Approximate MTBF: operating hours / failure occurrences
        mtbf_hours = round(operating_hours_window / max(count, 1), 1)

        # Look up component association from cause
        cause_node = graph_store.get_node(cid)
        component_name = "General Machinery"
        if cause_node:
            comp_id = cause_node.get("component_id")
            if comp_id:
                comp_node = graph_store.get_node(comp_id)
                if comp_node:
                    component_name = comp_node.get("name", comp_id)

        results.append({
            "asset_id": aid,
            "cause_id": cid,
            "cause_name": cause_names.get(cid, cid),
            "component_name": component_name,
            "occurrence_count": count,
            "total_downtime_hours": round(total_downtime, 1),
            "approx_mtbf_hours": mtbf_hours,
            "risk_level": "High" if count >= 3 else ("Moderate" if count == 2 else "Low")
        })

    # Sort by occurrence count descending
    results.sort(key=lambda x: x["occurrence_count"], reverse=True)
    return results
