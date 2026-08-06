from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AuditEvent


def record_audit(
    db: Session,
    *,
    action: str,
    object_type: str,
    user_id: str | None = None,
    object_id: str | None = None,
    case_id: str | None = None,
    details: dict | None = None,
    source_ip: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        user_id=user_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        case_id=case_id,
        details=details or {},
        source_ip=source_ip,
    )
    db.add(event)
    db.flush()
    return event
