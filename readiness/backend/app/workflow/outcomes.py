import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.workflow.models import WorkOrder, Outcome, Asset, User
from app.workflow.audit import log_audit_event
from app.graph.json_store import graph_store
from app.diagnosis.engine import diagnosis_engine


async def approve_workorder(
    db: AsyncSession,
    workorder_id: str,
    supervisor_user: User,
    downtime_hours: float = 2.0,
    supervisor_notes: Optional[str] = None
) -> Outcome:
    """
    Supervisor approval gate:
    1. Only a supervisor can approve a work order.
    2. Transition work order status to 'approved'.
    3. Asset is marked 'operational' with fresh inspection date.
    4. Creates a verified Outcome record.
    5. Injects a new Verified Outcome edge into the in-memory graph with:
       origin = 'technician_reported', verification_status = 'verified', approved_by = supervisor.username.
    6. Graph indexes are incrementally refreshed so future diagnoses incorporate this verified precedent.
    """
    if supervisor_user.role != "supervisor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a supervisor can approve work orders and verify outcomes."
        )

    wo = await db.get(WorkOrder, workorder_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"WorkOrder {workorder_id} not found")

    if wo.status == "approved":
        raise HTTPException(status_code=400, detail="WorkOrder is already approved")

    confirmed_cause = wo.resolution_confirmed_cause or "CAUSE-BRG-WEAR"

    # Fetch Asset
    asset = await db.get(Asset, wo.asset_id)
    if asset:
        asset.status = "operational"
        asset.last_inspection_date = datetime.utcnow().strftime("%Y-%m-%d")

    outcome_id = f"OUT-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.utcnow()

    # 1. Update Work Order
    wo.status = "approved"
    wo.approved_by = supervisor_user.id
    wo.approved_at = now
    wo.updated_at = now

    # 2. Add to In-Memory Graph with Provenance
    graph_edge_id = f"EDGE-{wo.asset_id}-{confirmed_cause}-{outcome_id}"
    graph_payload = {
        "id": outcome_id,
        "asset_id": wo.asset_id,
        "model": asset.model if asset else None,
        "confirmed_cause_id": confirmed_cause,
        "procedure_used_id": "PROC-BRG-INSPECT",
        "technician": wo.submitted_by or "technician",
        "approved_by": supervisor_user.username,
        "incident_date": now.strftime("%Y-%m-%d"),
        "resolution_notes": f"Action: {wo.resolution_action_taken or 'Fixed'}. Result: {wo.resolution_result or 'resolved'}."
    }
    graph_store.add_verified_outcome(graph_payload)
    # Refresh engine indexes with new verified outcome
    diagnosis_engine.initialize_indexes()

    # 3. Create SQLite Outcome record
    outcome = Outcome(
        id=outcome_id,
        work_order_id=wo.id,
        asset_id=wo.asset_id,
        confirmed_cause_id=confirmed_cause,
        procedure_id="PROC-BRG-INSPECT",
        verified_by=supervisor_user.id,
        verification_timestamp=now,
        notes=supervisor_notes or wo.resolution_action_taken,
        downtime_hours=downtime_hours,
        graph_edge_id=graph_edge_id
    )
    db.add(outcome)

    # 4. Record Audit Log
    await log_audit_event(
        db=db,
        entity_type="work_order",
        entity_id=wo.id,
        action="approve",
        user_id=supervisor_user.id,
        user_role=supervisor_user.role,
        details={
            "outcome_id": outcome_id,
            "confirmed_cause": confirmed_cause,
            "graph_edge_id": graph_edge_id,
            "downtime_hours": downtime_hours
        }
    )

    await db.commit()
    await db.refresh(outcome)
    return outcome


async def reject_workorder(
    db: AsyncSession,
    workorder_id: str,
    supervisor_user: User,
    rejection_reason: str
) -> WorkOrder:
    """
    Supervisor rejects work order.
    Status transitions to 'rejected'.
    CRITICAL: Absolutely NO verified graph edge is created!
    """
    if supervisor_user.role != "supervisor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a supervisor can reject work orders."
        )

    wo = await db.get(WorkOrder, workorder_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"WorkOrder {workorder_id} not found")

    wo.status = "rejected"
    wo.approved_by = supervisor_user.id
    wo.rejection_reason = rejection_reason
    wo.updated_at = datetime.utcnow()

    # Log audit event
    await log_audit_event(
        db=db,
        entity_type="work_order",
        entity_id=wo.id,
        action="reject",
        user_id=supervisor_user.id,
        user_role=supervisor_user.role,
        details={"rejection_reason": rejection_reason}
    )

    await db.commit()
    await db.refresh(wo)
    return wo
