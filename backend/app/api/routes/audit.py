from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import AuditEvent, User
from app.schemas import AuditRead


router = APIRouter(tags=["Audit"])


@router.get("/cases/{case_id}/audit", response_model=list[AuditRead])
def list_case_audit(
    case_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "reviewer")),
) -> list[AuditEvent]:
    return list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.case_id == case_id)
            .order_by(AuditEvent.created_at.desc())
        )
    )
