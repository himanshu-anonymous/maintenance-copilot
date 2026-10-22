import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False)  # "technician" | "supervisor"
    full_name = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class Asset(Base):
    __tablename__ = "assets"

    id = Column(String(32), primary_key=True)  # e.g. "P-101", "M-104"
    tag = Column(String(64), nullable=False)
    name = Column(String(128), nullable=False)
    category = Column(String(64), nullable=False)  # "centrifugal_pump" | "induction_motor"
    model = Column(String(64), nullable=False)
    serial_number = Column(String(64), nullable=False)
    manual_revision = Column(String(32), nullable=False)
    location = Column(String(128), nullable=False)
    critical_rating = Column(String(8), default="B", nullable=False)  # "A" | "B" | "C"
    last_inspection_date = Column(String(32), nullable=False)
    status = Column(String(32), default="operational", nullable=False)  # "operational", "degraded", "maintenance_required", "shutdown"
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True)
    asset_id = Column(String(32), ForeignKey("assets.id"), nullable=False)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    symptom_text = Column(Text, nullable=False)
    alarm_code = Column(String(32), nullable=True)
    diagnosis_summary = Column(Text, nullable=False)
    candidate_causes = Column(Text, nullable=False)  # JSON serialized
    initial_procedures = Column(Text, nullable=False)  # JSON serialized
    status = Column(String(32), default="open", nullable=False)  # "open", "in_progress", "work_order_created", "closed"
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    findings = relationship("Finding", back_populates="session", cascade="all, delete-orphan")


class Finding(Base):
    __tablename__ = "findings"

    id = Column(String(64), primary_key=True)
    session_id = Column(String(64), ForeignKey("sessions.id"), nullable=False)
    technician_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    finding_type = Column(String(32), nullable=False)  # "observation", "measurement", "unresolved"
    component_id = Column(String(64), nullable=True)
    parameter = Column(String(64), nullable=True)  # e.g. "radial_vibration_mm_s", "casing_temp_c"
    value = Column(String(64), nullable=True)  # e.g. "7.4 mm/s", "88 C"
    notes = Column(Text, nullable=False)
    photo_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    session = relationship("Session", back_populates="findings")


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(String(64), primary_key=True)  # "WO-XXXX"
    session_id = Column(String(64), ForeignKey("sessions.id"), nullable=True)
    asset_id = Column(String(32), ForeignKey("assets.id"), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(String(32), default="draft", nullable=False)  # "draft", "assigned", "in_progress", "pending_approval", "approved", "rejected"
    priority = Column(String(16), default="medium", nullable=False)  # "critical", "high", "medium", "low"
    assignee_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    required_parts = Column(Text, default="[]", nullable=False)  # JSON list
    findings_summary = Column(Text, nullable=True)

    # Resolution fields filled by technician
    resolution_confirmed_cause = Column(String(64), nullable=True)
    resolution_action_taken = Column(Text, nullable=True)
    resolution_parts_used = Column(Text, nullable=True)
    resolution_result = Column(String(32), nullable=True)  # "resolved", "temporary_fix", "unresolved"
    submitted_by = Column(String(64), ForeignKey("users.id"), nullable=True)
    submitted_at = Column(DateTime, nullable=True)

    # Supervisor approval fields
    approved_by = Column(String(64), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)


class Outcome(Base):
    __tablename__ = "outcomes"

    id = Column(String(64), primary_key=True)  # "OUT-XXXX"
    work_order_id = Column(String(64), ForeignKey("work_orders.id"), nullable=False)
    asset_id = Column(String(32), ForeignKey("assets.id"), nullable=False)
    confirmed_cause_id = Column(String(64), nullable=False)
    procedure_id = Column(String(64), nullable=True)
    verified_by = Column(String(64), ForeignKey("users.id"), nullable=False)
    verification_timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    notes = Column(Text, nullable=True)
    downtime_hours = Column(Float, default=2.0, nullable=False)
    graph_edge_id = Column(String(128), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(32), nullable=False)  # "session", "finding", "work_order", "outcome", "graph"
    entity_id = Column(String(64), nullable=False)
    action = Column(String(32), nullable=False)  # "create", "update", "status_change", "approve", "reject", "rebuild_graph"
    user_id = Column(String(64), nullable=False)
    user_role = Column(String(32), nullable=False)
    details = Column(Text, nullable=False)  # JSON string
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
