from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.detections import RULES
from app.models import Case, Finding, NormalizedEvent
from app.services.audit import record_audit


def run_detections(
    db: Session,
    case: Case,
    *,
    user_id: str,
    source_ip: str | None = None,
) -> list[Finding]:
    events = list(
        db.scalars(
            select(NormalizedEvent)
            .where(NormalizedEvent.case_id == case.id)
            .order_by(NormalizedEvent.event_time)
        )
    )
    created: list[Finding] = []
    for rule in RULES:
        for candidate in rule(events, case):
            existing = db.scalar(
                select(Finding).where(
                    Finding.case_id == case.id,
                    Finding.fingerprint == candidate["fingerprint"],
                )
            )
            if existing:
                continue
            finding = Finding(case_id=case.id, **candidate)
            db.add(finding)
            db.flush()
            created.append(finding)

    record_audit(
        db,
        action="detections.run",
        object_type="case",
        object_id=case.id,
        case_id=case.id,
        user_id=user_id,
        source_ip=source_ip,
        details={"created_findings": len(created), "evaluated_events": len(events)},
    )
    db.commit()
    return created
