from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Case, User
from app.schemas import CaseCreate, CaseRead, CaseUpdate
from app.services.audit import record_audit


router = APIRouter(prefix="/cases", tags=["Cases"])


@router.post("", response_model=CaseRead, status_code=201)
def create_case(
    payload: CaseCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Case:
    case = Case(**payload.model_dump(), created_by=user.id, assigned_to=user.id)
    db.add(case)
    db.flush()
    record_audit(
        db,
        action="case.create",
        object_type="case",
        object_id=case.id,
        case_id=case.id,
        user_id=user.id,
        source_ip=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(case)
    return case


@router.get("", response_model=list[CaseRead])
def list_cases(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Case]:
    return list(db.scalars(select(Case).order_by(Case.updated_at.desc())))


@router.get("/{case_id}", response_model=CaseRead)
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Case:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.patch("/{case_id}", response_model=CaseRead)
def update_case(
    case_id: str,
    payload: CaseUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Case:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(case, field, value)
    record_audit(
        db,
        action="case.update",
        object_type="case",
        object_id=case.id,
        case_id=case.id,
        user_id=user.id,
        source_ip=request.client.host if request.client else None,
        details={"fields": list(payload.model_fields_set)},
    )
    db.commit()
    db.refresh(case)
    return case
