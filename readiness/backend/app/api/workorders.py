import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.workflow.models import User, WorkOrder
from app.security import get_current_user, require_role
from app.workflow.workorders import create_workorder, submit_resolution, list_workorders
from app.workflow.outcomes import approve_workorder, reject_workorder

router = APIRouter(prefix="/workorders", tags=["Work Orders"])


class CreateWorkOrderRequest(BaseModel):
    asset_id: str
    title: str
    priority: str = Field(default="medium", description="critical | high | medium | low")
    session_id: Optional[str] = None
    assignee_id: Optional[str] = None
    required_parts: Optional[List[str]] = Field(default_factory=list)
    findings_summary: Optional[str] = None


class SubmitResolutionRequest(BaseModel):
    confirmed_cause: str = Field(..., description="Root cause ID e.g. CAUSE-BRG-WEAR")
    action_taken: str = Field(..., description="Corrective maintenance performed")
    parts_used: Optional[str] = Field(default="", description="Replaced components/parts")
    result: str = Field(default="resolved", description="resolved | temporary_fix | unresolved")


class SupervisorApprovalRequest(BaseModel):
    downtime_hours: float = Field(default=2.0)
    notes: Optional[str] = None


class SupervisorRejectionRequest(BaseModel):
    rejection_reason: str = Field(..., description="Explanation why resolution was rejected")


@router.get("")
async def get_all_workorders(
    asset_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    wos = await list_workorders(db, asset_id=asset_id, status_filter=status_filter)
    return [
        {
            "id": wo.id,
            "session_id": wo.session_id,
            "asset_id": wo.asset_id,
            "title": wo.title,
            "status": wo.status,
            "priority": wo.priority,
            "assignee_id": wo.assignee_id,
            "required_parts": json.loads(wo.required_parts or "[]"),
            "findings_summary": wo.findings_summary,
            "resolution_confirmed_cause": wo.resolution_confirmed_cause,
            "resolution_action_taken": wo.resolution_action_taken,
            "resolution_parts_used": wo.resolution_parts_used,
            "resolution_result": wo.resolution_result,
            "submitted_by": wo.submitted_by,
            "submitted_at": wo.submitted_at.isoformat() if wo.submitted_at else None,
            "approved_by": wo.approved_by,
            "approved_at": wo.approved_at.isoformat() if wo.approved_at else None,
            "rejection_reason": wo.rejection_reason,
            "created_at": wo.created_at.isoformat(),
            "updated_at": wo.updated_at.isoformat()
        }
        for wo in wos
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def draft_workorder(
    payload: CreateWorkOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    wo = await create_workorder(
        db=db,
        asset_id=payload.asset_id,
        title=payload.title,
        priority=payload.priority,
        session_id=payload.session_id,
        assignee_id=payload.assignee_id,
        required_parts=payload.required_parts,
        findings_summary=payload.findings_summary,
        created_by=current_user.id
    )
    return {
        "id": wo.id,
        "title": wo.title,
        "status": wo.status,
        "asset_id": wo.asset_id,
        "priority": wo.priority,
        "created_at": wo.created_at.isoformat()
    }


@router.get("/{workorder_id}")
async def get_workorder_detail(
    workorder_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    wo = await db.get(WorkOrder, workorder_id)
    if not wo:
        raise HTTPException(status_code=404, detail="WorkOrder not found")
    return {
        "id": wo.id,
        "session_id": wo.session_id,
        "asset_id": wo.asset_id,
        "title": wo.title,
        "status": wo.status,
        "priority": wo.priority,
        "assignee_id": wo.assignee_id,
        "required_parts": json.loads(wo.required_parts or "[]"),
        "findings_summary": wo.findings_summary,
        "resolution_confirmed_cause": wo.resolution_confirmed_cause,
        "resolution_action_taken": wo.resolution_action_taken,
        "resolution_parts_used": wo.resolution_parts_used,
        "resolution_result": wo.resolution_result,
        "submitted_by": wo.submitted_by,
        "submitted_at": wo.submitted_at.isoformat() if wo.submitted_at else None,
        "approved_by": wo.approved_by,
        "approved_at": wo.approved_at.isoformat() if wo.approved_at else None,
        "rejection_reason": wo.rejection_reason,
        "created_at": wo.created_at.isoformat()
    }


@router.post("/{workorder_id}/submit-resolution")
async def submit_wo_resolution(
    workorder_id: str,
    payload: SubmitResolutionRequest,
    current_user: User = Depends(require_role(["technician", "supervisor"])),
    db: AsyncSession = Depends(get_db_session)
):
    wo = await submit_resolution(
        db=db,
        workorder_id=workorder_id,
        user_id=current_user.id,
        confirmed_cause=payload.confirmed_cause,
        action_taken=payload.action_taken,
        parts_used=payload.parts_used,
        result=payload.result
    )
    return {
        "id": wo.id,
        "status": wo.status,
        "resolution_confirmed_cause": wo.resolution_confirmed_cause,
        "submitted_by": wo.submitted_by,
        "submitted_at": wo.submitted_at.isoformat()
    }


@router.post("/{workorder_id}/approve")
async def supervisor_approve(
    workorder_id: str,
    payload: SupervisorApprovalRequest,
    current_user: User = Depends(require_role(["supervisor"])),
    db: AsyncSession = Depends(get_db_session)
):
    outcome = await approve_workorder(
        db=db,
        workorder_id=workorder_id,
        supervisor_user=current_user,
        downtime_hours=payload.downtime_hours,
        supervisor_notes=payload.notes
    )
    return {
        "status": "approved",
        "outcome_id": outcome.id,
        "workorder_id": outcome.work_order_id,
        "asset_id": outcome.asset_id,
        "confirmed_cause_id": outcome.confirmed_cause_id,
        "verified_by": current_user.username,
        "verification_timestamp": outcome.verification_timestamp.isoformat(),
        "graph_edge_id": outcome.graph_edge_id
    }


@router.post("/{workorder_id}/reject")
async def supervisor_reject(
    workorder_id: str,
    payload: SupervisorRejectionRequest,
    current_user: User = Depends(require_role(["supervisor"])),
    db: AsyncSession = Depends(get_db_session)
):
    wo = await reject_workorder(
        db=db,
        workorder_id=workorder_id,
        supervisor_user=current_user,
        rejection_reason=payload.rejection_reason
    )
    return {
        "status": "rejected",
        "workorder_id": wo.id,
        "rejection_reason": wo.rejection_reason
    }
