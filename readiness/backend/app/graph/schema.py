from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal, Dict, Any


class DocumentSection(BaseModel):
    section_id: str = Field(..., description="Unique section identifier, e.g. SEC-01")
    title: str
    content: str


class ManualDocument(BaseModel):
    doc_id: str = Field(..., description="Unique document identifier, e.g. DOC-MAN-CP200-B")
    title: str
    revision: str = Field(..., description="e.g. Rev A, Rev B")
    effective_date: str = Field(..., description="ISO 8601 date, e.g. 2024-01-15")
    applicable_models: List[str] = Field(..., description="Equipment models this document applies to")
    superseded_by: Optional[str] = Field(default=None, description="Document ID that supersedes this manual, if any")
    sections: List[DocumentSection]


class Symptom(BaseModel):
    id: str = Field(..., description="e.g. SYMP-VIB-01")
    name: str
    description: str
    aliases: List[str] = Field(default_factory=list, description="Plain language aliases and colloquial descriptions")
    alarm_codes: List[str] = Field(default_factory=list, description="Associated SCADA / DCS alarm codes, e.g. ALM-VIB-01")
    category: str = Field(default="mechanical")


class Cause(BaseModel):
    id: str = Field(..., description="e.g. CAUSE-BRG-WEAR")
    name: str
    description: str
    source_doc_id: str = Field(..., description="Must link to a valid ManualDocument doc_id")
    section: str = Field(..., description="Must link to a valid DocumentSection section_id")
    applicable_models: List[str] = Field(..., description="Equipment models this cause applies to")
    component_id: str = Field(..., description="Associated component type, e.g. COMP-BEARING")


class ProcedureStep(BaseModel):
    step_num: int
    instruction: str
    expected_observation: Optional[str] = None
    caution: Optional[str] = None


class Procedure(BaseModel):
    id: str = Field(..., description="e.g. PROC-BRG-CHK")
    title: str
    source_doc_id: str = Field(..., description="Must link to a valid ManualDocument doc_id")
    section: str = Field(..., description="Must link to a valid DocumentSection section_id")
    applicable_models: List[str] = Field(..., description="Equipment models this procedure is authorized for")
    required_expertise: str = Field(default="Mechanical Tech II")
    safety_precautions: List[str] = Field(default_factory=list)
    stop_work_conditions: List[str] = Field(default_factory=list)
    steps: List[ProcedureStep]
    escalation_criteria: str


class Part(BaseModel):
    id: str = Field(..., description="e.g. PART-BRG-6312")
    part_number: str
    name: str
    applicable_models: List[str]
    estimated_lead_time_days: int = Field(default=2)


class Incident(BaseModel):
    id: str = Field(..., description="e.g. INC-2024-001")
    asset_id: str
    symptom_id: str
    confirmed_cause_id: str
    procedure_used_id: str
    outcome_status: Literal["resolved", "escalated", "pending_verification"]
    technician: str
    supervisor_approved: bool
    approved_by: Optional[str] = None
    incident_date: str
    resolution_notes: str


class AssetInspection(BaseModel):
    inspection_id: str
    date: str
    inspector: str
    result: Literal["pass", "conditional", "defect_noted"]
    notes: str


class Asset(BaseModel):
    id: str = Field(..., description="e.g. P-101")
    name: str
    category: str
    model: str
    revision: str
    manual_id: str
    effective_date: str
    criticality: Literal["high", "medium", "low"]
    motor_id: Optional[str] = None
    inspection_history: List[AssetInspection] = Field(default_factory=list)


OriginType = Literal["documented", "technician_reported", "ai_inferred"]
VerificationStatus = Literal["unverified", "verified"]
EdgeType = Literal[
    "HAS_COMPONENT",
    "HAS_HISTORY",
    "POSSIBLY_INDICATES",
    "INVESTIGATED_BY",
    "USES_PART",
    "SUPERSEDES",
    "DOCUMENTED_IN"
]


class GraphEdge(BaseModel):
    source: str
    target: str
    edge_type: EdgeType
    source_doc_id: Optional[str] = None
    section: Optional[str] = None
    applicable_models: List[str] = Field(default_factory=list)
    revision: Optional[str] = None
    effective_date: Optional[str] = None
    origin: OriginType = "documented"
    verification_status: VerificationStatus = "unverified"
    approved_by: Optional[str] = None


class KnowledgePack(BaseModel):
    manuals: List[ManualDocument]
    symptoms: List[Symptom]
    causes: List[Cause]
    procedures: List[Procedure]
    parts: List[Part]
    incidents: List[Incident]
    assets: List[Asset]
