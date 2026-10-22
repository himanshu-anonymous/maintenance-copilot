import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.workflow.models import WorkOrder, Session, Asset
from app.workflow.audit import log_audit_event


async def create_workorder(
    db: AsyncSession,
    asset_id: str,
    title: str,
    priority: str = "medium",
    session_id: Optional[str] = None,
    assignee_id: Optional[str] = None,
    required_parts: Optional[List[str]] = None,
    findings_summary: Optional[str] = None,
    created_by: str = "usr-tech-01"
) -> WorkOrder:
    asset = await db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

    wo_id = f"WO-{uuid.uuid4().hex[:6].upper()}"

    wo = WorkOrder(
        id=wo_id,
        session_id=session_id,
        asset_id=asset_id,
        title=title,
        status="draft",
        priority=priority,
        assignee_id=assignee_id or created_by,
        required_parts=json.dumps(required_parts or []),
        findings_summary=findings_summary,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(wo)

    if session_id:
        session = await db.get(Session, session_id)
        if session:
            session.status = "work_order_created"
            session.updated_at = datetime.utcnow()

    # Asset moves to maintenance_required if priority is critical or high
    if priority in ["critical", "high"]:
        asset.status = "maintenance_required"

    await log_audit_event(
        db=db,
        entity_type="work_order",
        entity_id=wo_id,
        action="create",
        user_id=created_by,
        user_role="technician",
        details={
            "asset_id": asset_id,
            "title": title,
            "priority": priority,
            "session_id": session_id
        }
    )

    await db.commit()
    await db.refresh(wo)
    return wo


async def submit_resolution(
    db: AsyncSession,
    workorder_id: str,
    user_id: str,
    confirmed_cause: str,
    action_taken: str,
    parts_used: Optional[str] = None,
    result: str = "resolved"
) -> WorkOrder:
    """
    Technician records the field findings and submits the resolution.
    Transitions status to 'pending_approval' for supervisor review.
    NOTE: The AI and technician NEVER mark the asset ready or repaired directly.
    """
    wo = await db.get(WorkOrder, workorder_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"WorkOrder {workorder_id} not found")

    if wo.status in ["approved", "pending_approval"]:
        raise HTTPException(status_code=400, detail=f"WorkOrder is already in status {wo.status}")

    wo.resolution_confirmed_cause = confirmed_cause
    wo.resolution_action_taken = action_taken
    wo.resolution_parts_used = parts_used
    wo.resolution_result = result
    wo.submitted_by = user_id
    wo.submitted_at = datetime.utcnow()
    wo.status = "pending_approval"
    wo.updated_at = datetime.utcnow()

    await log_audit_event(
        db=db,
        entity_type="work_order",
        entity_id=wo.id,
        action="submit_resolution",
        user_id=user_id,
        user_role="technician",
        details={
            "confirmed_cause": confirmed_cause,
            "action_taken": action_taken,
            "result": result
        }
    )

    await db.commit()
    await db.refresh(wo)
    return wo


async def list_workorders(
    db: AsyncSession,
    asset_id: Optional[str] = None,
    status_filter: Optional[str] = None
) -> List[WorkOrder]:
    stmt = select(WorkOrder)
    if asset_id:
        stmt = stmt.where(WorkOrder.asset_id == asset_id)
    if status_filter:
        stmt = stmt.where(WorkOrder.status == status_filter)
    stmt = stmt.order_by(WorkOrder.created_at.desc())
    res = await db.execute(stmt)
    return list(res.scalars().all())
