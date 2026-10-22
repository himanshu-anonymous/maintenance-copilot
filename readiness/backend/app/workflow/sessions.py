import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.workflow.models import Session, Finding, Asset, User
from app.workflow.audit import log_audit_event


async def create_session(
    db: AsyncSession,
    asset_id: str,
    user_id: str,
    symptom_text: str,
    alarm_code: Optional[str] = None,
    diagnosis_summary: str = "",
    candidate_causes: Optional[List[Dict[str, Any]]] = None,
    initial_procedures: Optional[List[Dict[str, Any]]] = None
) -> Session:
    session_id = f"SES-{uuid.uuid4().hex[:8].upper()}"

    # Verify asset exists
    asset = await db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

    new_session = Session(
        id=session_id,
        asset_id=asset_id,
        user_id=user_id,
        symptom_text=symptom_text,
        alarm_code=alarm_code,
        diagnosis_summary=diagnosis_summary,
        candidate_causes=json.dumps(candidate_causes or []),
        initial_procedures=json.dumps(initial_procedures or []),
        status="open",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_session)

    # Log audit event
    await log_audit_event(
        db=db,
        entity_type="session",
        entity_id=session_id,
        action="create",
        user_id=user_id,
        user_role="technician",
        details={"asset_id": asset_id, "symptom": symptom_text, "alarm_code": alarm_code}
    )

    await db.commit()
    await db.refresh(new_session)
    return new_session


async def add_finding(
    db: AsyncSession,
    session_id: str,
    technician_id: str,
    finding_type: str,
    notes: str,
    component_id: Optional[str] = None,
    parameter: Optional[str] = None,
    value: Optional[str] = None,
    photo_url: Optional[str] = None
) -> Finding:
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    finding_id = f"FND-{uuid.uuid4().hex[:8].upper()}"
    finding = Finding(
        id=finding_id,
        session_id=session_id,
        technician_id=technician_id,
        finding_type=finding_type,
        component_id=component_id,
        parameter=parameter,
        value=value,
        notes=notes,
        photo_url=photo_url,
        created_at=datetime.utcnow()
    )
    db.add(finding)

    # Update session status to in_progress
    session.status = "in_progress"
    session.updated_at = datetime.utcnow()

    # Log audit event
    await log_audit_event(
        db=db,
        entity_type="finding",
        entity_id=finding_id,
        action="create",
        user_id=technician_id,
        user_role="technician",
        details={
            "session_id": session_id,
            "type": finding_type,
            "parameter": parameter,
            "value": value
        }
    )

    await db.commit()
    await db.refresh(finding)
    return finding


async def get_session_by_id(db: AsyncSession, session_id: str) -> Optional[Session]:
    stmt = (
        select(Session)
        .where(Session.id == session_id)
        .options(selectinload(Session.findings))
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()
