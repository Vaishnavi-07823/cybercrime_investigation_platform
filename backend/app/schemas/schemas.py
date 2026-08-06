from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: str
    password: str


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: dict[str, Any]


class UserRead(ORMModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class CaseCreate(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    description: str | None = None
    case_type: str = "bec"
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    classification: str = "restricted"
    context: dict[str, Any] = Field(default_factory=dict)


class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=300)
    description: str | None = None
    status: str | None = None
    severity: Literal["low", "medium", "high", "critical"] | None = None
    assigned_to: str | None = None
    context: dict[str, Any] | None = None


class CaseRead(ORMModel):
    id: str
    title: str
    description: str | None
    case_type: str
    status: str
    severity: str
    classification: str
    context: dict[str, Any]
    created_by: str
    assigned_to: str | None
    created_at: datetime
    updated_at: datetime


class EvidenceRead(ORMModel):
    id: str
    case_id: str
    source_type: str
    original_filename: str
    media_type: str | None
    sha256: str
    size_bytes: int
    storage_bucket: str
    storage_key: str
    acquired_at: datetime
    acquired_by: str
    acquisition_method: str
    legal_hold: bool
    processed: bool
    notes: str | None
    created_at: datetime


class LegalHoldRequest(BaseModel):
    enabled: bool
    reason: str = Field(min_length=3, max_length=1000)


class CustodyRead(ORMModel):
    id: str
    evidence_id: str
    action: str
    actor_id: str | None
    actor_type: str
    details: dict[str, Any]
    previous_hash: str | None
    entry_hash: str
    created_at: datetime


class EventRead(ORMModel):
    id: str
    case_id: str
    evidence_id: str
    schema_version: str
    event_type: str
    event_action: str
    event_outcome: str | None
    event_time: datetime
    observed_time: datetime | None
    ingested_time: datetime
    actor: dict[str, Any]
    source: dict[str, Any]
    destination: dict[str, Any]
    observables: list[Any]
    payload: dict[str, Any]
    transformation: dict[str, Any]
    quality: dict[str, Any]
    record_hash: str


class FindingRead(ORMModel):
    id: str
    case_id: str
    rule_id: str
    rule_version: str
    title: str
    finding_type: str
    severity: str
    confidence: float
    score: float
    status: str
    event_refs: list[str]
    evidence_refs: list[str]
    explanation: list[str]
    details: dict[str, Any]
    fingerprint: str
    created_at: datetime


class EntityRead(ORMModel):
    id: str
    case_id: str
    entity_type: str
    canonical_value: str
    display_value: str
    attributes: dict[str, Any]
    confidence: float
    created_at: datetime


class RelationshipRead(ORMModel):
    id: str
    case_id: str
    source_entity_id: str
    target_entity_id: str
    relation_type: str
    event_refs: list[str]
    evidence_refs: list[str]
    confidence: float
    directly_observed: bool
    attributes: dict[str, Any]
    fingerprint: str
    created_at: datetime


class ClaimRead(ORMModel):
    id: str
    case_id: str
    text: str
    reasoning_type: str
    confidence: str
    evidence_refs: list[str]
    event_refs: list[str]
    finding_refs: list[str]
    limitations: list[str]
    status: str
    generation_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ClaimReviewRequest(BaseModel):
    decision: Literal["approved", "rejected", "needs_evidence", "edited"]
    rationale: str | None = None
    edited_text: str | None = None


class ReportRead(ORMModel):
    id: str
    case_id: str
    report_type: str
    status: str
    template_version: str
    storage_bucket: str
    pdf_storage_key: str
    json_storage_key: str
    pdf_sha256: str
    json_sha256: str
    manifest: dict[str, Any]
    generated_by: str
    created_at: datetime


class AuditRead(ORMModel):
    id: str
    user_id: str | None
    action: str
    object_type: str
    object_id: str | None
    case_id: str | None
    details: dict[str, Any]
    source_ip: str | None
    created_at: datetime


class OperationResult(BaseModel):
    message: str
    count: int = 0
    details: dict[str, Any] = Field(default_factory=dict)
