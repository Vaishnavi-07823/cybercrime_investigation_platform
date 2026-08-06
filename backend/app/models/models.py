from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ids import make_id
from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: make_id("USR"))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(32), default="analyst", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: make_id("CASE"))
    title: Mapped[str] = mapped_column(String(300), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    case_type: Mapped[str] = mapped_column(String(80), default="bec", index=True)
    status: Mapped[str] = mapped_column(String(40), default="new", index=True)
    severity: Mapped[str] = mapped_column(String(20), default="medium", index=True)
    classification: Mapped[str] = mapped_column(String(40), default="restricted")
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    assigned_to: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class EvidenceArtifact(Base):
    __tablename__ = "evidence_artifacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: make_id("EVD"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(80), index=True)
    original_filename: Mapped[str] = mapped_column(String(500))
    media_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_bucket: Mapped[str] = mapped_column(String(100))
    storage_key: Mapped[str] = mapped_column(String(1000), unique=True)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    acquired_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    acquisition_method: Mapped[str] = mapped_column(String(100), default="manual_upload")
    legal_hold: Mapped[bool] = mapped_column(Boolean, default=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_evidence_case_sha256", "case_id", "sha256"),
    )


class CustodyEntry(Base):
    __tablename__ = "custody_entries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: make_id("CST"))
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence_artifacts.id"), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(40), default="user")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class NormalizedEvent(Base):
    __tablename__ = "normalized_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: make_id("EVT"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence_artifacts.id"), index=True)
    schema_version: Mapped[str] = mapped_column(String(30), default="1.0.0")
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    event_action: Mapped[str] = mapped_column(String(120), index=True)
    event_outcome: Mapped[str | None] = mapped_column(String(60), nullable=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    observed_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingested_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    actor: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[dict] = mapped_column(JSON, default=dict)
    destination: Mapped[dict] = mapped_column(JSON, default=dict)
    observables: Mapped[list] = mapped_column(JSON, default=list)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    transformation: Mapped[dict] = mapped_column(JSON, default=dict)
    quality: Mapped[dict] = mapped_column(JSON, default=dict)
    record_hash: Mapped[str] = mapped_column(String(64), index=True)

    __table_args__ = (
        UniqueConstraint("case_id", "record_hash", name="uq_case_event_record_hash"),
        Index("ix_event_case_time", "case_id", "event_time"),
    )


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: make_id("FND"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    rule_id: Mapped[str] = mapped_column(String(120), index=True)
    rule_version: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(300))
    finding_type: Mapped[str] = mapped_column(String(100), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    score: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(40), default="new", index=True)
    event_refs: Mapped[list] = mapped_column(JSON, default=list)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[list] = mapped_column(JSON, default=list)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("case_id", "fingerprint", name="uq_case_finding_fingerprint"),
    )


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: make_id("ENT"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    canonical_value: Mapped[str] = mapped_column(String(1000), index=True)
    display_value: Mapped[str] = mapped_column(String(1000))
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint(
            "case_id", "entity_type", "canonical_value", name="uq_case_entity_value"
        ),
    )


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: make_id("REL"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    source_entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"), index=True)
    target_entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(100), index=True)
    event_refs: Mapped[list] = mapped_column(JSON, default=list)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    directly_observed: Mapped[bool] = mapped_column(Boolean, default=True)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("case_id", "fingerprint", name="uq_case_relationship_fingerprint"),
    )


class NarrativeClaim(Base):
    __tablename__ = "narrative_claims"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: make_id("CLM"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    reasoning_type: Mapped[str] = mapped_column(String(30), index=True)
    confidence: Mapped[str] = mapped_column(String(20))
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list)
    event_refs: Mapped[list] = mapped_column(JSON, default=list)
    finding_refs: Mapped[list] = mapped_column(JSON, default=list)
    limitations: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    generation_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class AnalystDecision(Base):
    __tablename__ = "analyst_decisions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: make_id("DEC"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    object_type: Mapped[str] = mapped_column(String(50), index=True)
    object_id: Mapped[str] = mapped_column(String(64), index=True)
    decision: Mapped[str] = mapped_column(String(40), index=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    analyst_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: make_id("RPT"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    report_type: Mapped[str] = mapped_column(String(40), default="case_report")
    status: Mapped[str] = mapped_column(String(30), default="generated")
    template_version: Mapped[str] = mapped_column(String(30), default="1.0.0")
    storage_bucket: Mapped[str] = mapped_column(String(100))
    pdf_storage_key: Mapped[str] = mapped_column(String(1000))
    json_storage_key: Mapped[str] = mapped_column(String(1000))
    pdf_sha256: Mapped[str] = mapped_column(String(64))
    json_sha256: Mapped[str] = mapped_column(String(64))
    manifest: Mapped[dict] = mapped_column(JSON, default=dict)
    generated_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: make_id("AUD"))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    object_type: Mapped[str] = mapped_column(String(80), index=True)
    object_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    case_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    source_ip: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
