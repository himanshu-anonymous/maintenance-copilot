import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.workflow.models import User
from app.security import get_current_user
from app.workflow.sessions import create_session, add_finding, get_session_by_id

router = APIRouter(prefix="/sessions", tags=["Troubleshooting Sessions"])


class CreateSessionRequest(BaseModel):
    asset_id: str
    symptom_text: str
    alarm_code: Optional[str] = None
    diagnosis_summary: str = ""
    candidate_causes: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    initial_procedures: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


class AddFindingRequest(BaseModel):
    finding_type: str = Field(..., description="observation | measurement | unresolved")
    notes: str
    component_id: Optional[str] = None
    parameter: Optional[str] = None
    value: Optional[str] = None
    photo_url: Optional[str] = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def start_session(
    payload: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    session = await create_session(
        db=db,
        asset_id=payload.asset_id,
        user_id=current_user.id,
        symptom_text=payload.symptom_text,
        alarm_code=payload.alarm_code,
        diagnosis_summary=payload.diagnosis_summary,
        candidate_causes=payload.candidate_causes,
        initial_procedures=payload.initial_procedures
    )
    return {
        "id": session.id,
        "asset_id": session.asset_id,
        "status": session.status,
        "created_at": session.created_at.isoformat()
    }


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    session = await get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    findings = [
        {
            "id": f.id,
            "finding_type": f.finding_type,
            "component_id": f.component_id,
            "parameter": f.parameter,
            "value": f.value,
            "notes": f.notes,
            "photo_url": f.photo_url,
            "created_at": f.created_at.isoformat()
        }
        for f in session.findings
    ]

    return {
        "id": session.id,
        "asset_id": session.asset_id,
        "user_id": session.user_id,
        "symptom_text": session.symptom_text,
        "alarm_code": session.alarm_code,
        "diagnosis_summary": session.diagnosis_summary,
        "candidate_causes": json.loads(session.candidate_causes or "[]"),
        "initial_procedures": json.loads(session.initial_procedures or "[]"),
        "status": session.status,
        "findings": findings,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat()
    }


@router.post("/{session_id}/findings", status_code=status.HTTP_201_CREATED)
async def record_session_finding(
    session_id: str,
    payload: AddFindingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    finding = await add_finding(
        db=db,
        session_id=session_id,
        technician_id=current_user.id,
        finding_type=payload.finding_type,
        notes=payload.notes,
        component_id=payload.component_id,
        parameter=payload.parameter,
        value=payload.value,
        photo_url=payload.photo_url
    )
    return {
        "id": finding.id,
        "session_id": finding.session_id,
        "finding_type": finding.finding_type,
        "parameter": finding.parameter,
        "value": finding.value,
        "notes": finding.notes,
        "created_at": finding.created_at.isoformat()
    }
