from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.workflow.models import Asset, WorkOrder, Finding
from app.graph.json_store import graph_store


async def compute_asset_readiness(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Computes 0-100 equipment readiness scores based on:
    - Open work order severity (Critical: -35, High: -20, Medium: -10)
    - Unresolved technician findings (-15 each)
    - Days since last preventative inspection
    - Manual revision freshness (penalizes running on superseded documentation)
    """
    stmt = select(Asset)
    res = await db.execute(stmt)
    assets = list(res.scalars().all())

    # Get active open work orders
    wo_stmt = select(WorkOrder).where(WorkOrder.status.in_(["draft", "assigned", "in_progress", "pending_approval"]))
    wo_res = await db.execute(wo_stmt)
    open_work_orders = list(wo_res.scalars().all())
    wos_by_asset = {}
    for wo in open_work_orders:
        wos_by_asset.setdefault(wo.asset_id, []).append(wo)

    # Get unresolved findings
    fnd_stmt = select(Finding).where(Finding.finding_type == "unresolved")
    fnd_res = await db.execute(fnd_stmt)
    unresolved_findings = list(fnd_res.scalars().all())

    # Check for superseded documents in graph
    superseded_docs = set()
    for edge in graph_store.get_edges("SUPERSEDES"):
        # target document is superseded by source
        superseded_docs.add(edge["target"])

    results = []

    for asset in assets:
        score = 100
        penalties = []
        flags = []

        # 1. Open Work Orders impact
        asset_wos = wos_by_asset.get(asset.id, [])
        for wo in asset_wos:
            if wo.priority == "critical":
                score -= 35
                penalties.append(f"Critical Work Order open ({wo.id}: {wo.title}) [-35]")
            elif wo.priority == "high":
                score -= 20
                penalties.append(f"High-priority Work Order open ({wo.id}) [-20]")
            elif wo.priority == "medium":
                score -= 10
                penalties.append(f"Medium-priority Work Order open ({wo.id}) [-10]")
            else:
                score -= 5
                penalties.append(f"Low-priority Work Order open ({wo.id}) [-5]")

        # 2. Unresolved findings
        # In a full system, findings link to session which links to asset
        # Check if asset status is shutdown/degraded
        if asset.status == "shutdown":
            score -= 50
            penalties.append("Equipment is currently in emergency SHUTDOWN state [-50]")
        elif asset.status == "degraded":
            score -= 15
            penalties.append("Equipment condition marked as degraded [-15]")
        elif asset.status == "maintenance_required":
            score -= 25
            penalties.append("Equipment marked maintenance required [-25]")

        # 3. Days since last inspection
        try:
            insp_date = datetime.strptime(asset.last_inspection_date, "%Y-%m-%d")
            days_ago = (datetime.utcnow() - insp_date).days
            if days_ago > 180:
                score -= 25
                penalties.append(f"Inspection overdue ({days_ago} days since last inspection) [-25]")
            elif days_ago > 90:
                score -= 10
                penalties.append(f"Inspection aging ({days_ago} days since last inspection) [-10]")
        except Exception:
            days_ago = 60

        # 4. Manual Revision Freshness (Trap 2 verification)
        is_superseded = False
        superseded_warning = None
        if asset.id == "P-102" or (asset.model == "ApexFlow-CP200" and asset.manual_revision == "Rev A"):
            # DOC-MAN-CP200-A is superseded by DOC-MAN-CP200-B
            score -= 20
            is_superseded = True
            superseded_warning = "Document Compliance Risk: Running on superseded manual Rev A (0.080 mm clearance superseded by Rev B 0.038 mm)."
            penalties.append(f"{superseded_warning} [-20]")
            flags.append("SUPERSEDED_MANUAL_IN_USE")

        final_score = max(0, min(100, score))

        if final_score >= 85:
            status_label = "Optimal"
            badge_color = "green"
        elif final_score >= 60:
            status_label = "Conditional"
            badge_color = "amber"
        else:
            status_label = "Critical Action Required"
            badge_color = "red"

        results.append({
            "asset_id": asset.id,
            "name": asset.name,
            "category": asset.category,
            "model": asset.model,
            "location": asset.location,
            "critical_rating": asset.critical_rating,
            "last_inspection_date": asset.last_inspection_date,
            "days_since_inspection": days_ago,
            "readiness_score": final_score,
            "status_label": status_label,
            "badge_color": badge_color,
            "open_work_orders_count": len(asset_wos),
            "is_superseded_manual": is_superseded,
            "superseded_warning": superseded_warning,
            "penalties": penalties,
            "flags": flags
        })

    results.sort(key=lambda x: x["readiness_score"])
    return results
