from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import EvidenceArtifact
from app.services.audit import record_audit
from app.services.custody import append_custody_entry
from app.services.storage import storage


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def create_evidence(
    db: Session,
    *,
    case_id: str,
    source_type: str,
    filename: str,
    media_type: str | None,
    data: bytes,
    user_id: str,
    acquisition_method: str = "manual_upload",
    notes: str | None = None,
    source_ip: str | None = None,
) -> EvidenceArtifact:
    settings = get_settings()
    digest = sha256_bytes(data)
    evidence = EvidenceArtifact(
        case_id=case_id,
        source_type=source_type,
        original_filename=filename,
        media_type=media_type,
        sha256=digest,
        size_bytes=len(data),
        storage_bucket=settings.minio_evidence_bucket,
        storage_key="pending",
        acquired_at=datetime.now(timezone.utc),
        acquired_by=user_id,
        acquisition_method=acquisition_method,
        notes=notes,
    )
    db.add(evidence)
    db.flush()

    safe_name = filename.replace("/", "_").replace("\\", "_")
    key = f"{case_id}/{evidence.id}/{digest}/{safe_name}"
    storage.put_bytes(
        bucket=settings.minio_evidence_bucket,
        key=key,
        data=data,
        content_type=media_type or "application/octet-stream",
        prevent_overwrite=True,
    )
    evidence.storage_key = key

    append_custody_entry(
        db,
        evidence_id=evidence.id,
        action="ACQUIRED",
        actor_id=user_id,
        details={
            "sha256": digest,
            "size_bytes": len(data),
            "storage_key": key,
            "acquisition_method": acquisition_method,
        },
    )
    record_audit(
        db,
        action="evidence.upload",
        object_type="evidence",
        object_id=evidence.id,
        case_id=case_id,
        user_id=user_id,
        source_ip=source_ip,
        details={"filename": filename, "sha256": digest, "source_type": source_type},
    )
    db.commit()
    db.refresh(evidence)
    return evidence


def verify_evidence(
    db: Session,
    evidence: EvidenceArtifact,
    *,
    user_id: str,
    source_ip: str | None = None,
) -> dict:
    data = storage.get_bytes(evidence.storage_bucket, evidence.storage_key)
    actual = sha256_bytes(data)
    valid = actual == evidence.sha256 and len(data) == evidence.size_bytes
    append_custody_entry(
        db,
        evidence_id=evidence.id,
        action="INTEGRITY_VERIFIED" if valid else "INTEGRITY_FAILURE",
        actor_id=user_id,
        details={"expected_sha256": evidence.sha256, "actual_sha256": actual, "valid": valid},
    )
    record_audit(
        db,
        action="evidence.verify",
        object_type="evidence",
        object_id=evidence.id,
        case_id=evidence.case_id,
        user_id=user_id,
        source_ip=source_ip,
        details={"valid": valid},
    )
    db.commit()
    return {
        "evidence_id": evidence.id,
        "valid": valid,
        "expected_sha256": evidence.sha256,
        "actual_sha256": actual,
        "expected_size": evidence.size_bytes,
        "actual_size": len(data),
    }


def duplicate_in_case(db: Session, case_id: str, digest: str) -> EvidenceArtifact | None:
    return db.scalar(
        select(EvidenceArtifact).where(
            EvidenceArtifact.case_id == case_id,
            EvidenceArtifact.sha256 == digest,
        )
    )
