import json
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.workflow.models import AuditLog


async def log_audit_event(
    db: AsyncSession,
    entity_type: str,
    entity_id: str,
    action: str,
    user_id: str,
    user_role: str,
    details: Dict[str, Any]
) -> AuditLog:
    """Records an immutable audit event for every critical system state change."""
    entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        user_role=user_role,
        details=json.dumps(details),
        timestamp=datetime.utcnow()
    )
    db.add(entry)
    await db.flush()
    return entry
