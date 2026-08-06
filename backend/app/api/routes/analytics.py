from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Case, Entity, Finding, NormalizedEvent, Relationship, User
from app.schemas import EntityRead, EventRead, FindingRead, OperationResult, RelationshipRead
from app.services.correlation import run_correlations
from app.services.detection import run_detections


router = APIRouter(tags=["Analytics"])


@router.get("/cases/{case_id}/events", response_model=list[EventRead])
def list_events(
    case_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[NormalizedEvent]:
    return list(
        db.scalars(
            select(NormalizedEvent)
            .where(NormalizedEvent.case_id == case_id)
            .order_by(NormalizedEvent.event_time)
        )
    )


@router.get("/cases/{case_id}/findings", response_model=list[FindingRead])
def list_findings(
    case_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Finding]:
    return list(
        db.scalars(
            select(Finding).where(Finding.case_id == case_id).order_by(Finding.created_at.desc())
        )
    )


@router.post("/cases/{case_id}/detections/run", response_model=OperationResult)
def run_case_detections(
    case_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OperationResult:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    created = run_detections(
        db,
        case,
        user_id=user.id,
        source_ip=request.client.host if request.client else None,
    )
    return OperationResult(
        message="Detection run completed",
        count=len(created),
        details={"finding_ids": [item.id for item in created]},
    )


@router.post("/cases/{case_id}/correlations/run", response_model=OperationResult)
def run_case_correlations(
    case_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OperationResult:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    entities, relationships = run_correlations(
        db,
        case,
        user_id=user.id,
        source_ip=request.client.host if request.client else None,
    )
    return OperationResult(
        message="Correlation run completed",
        count=len(relationships),
        details={"entities_touched": len(entities), "relationships_touched": len(relationships)},
    )


@router.get("/cases/{case_id}/entities", response_model=list[EntityRead])
def list_entities(
    case_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Entity]:
    return list(
        db.scalars(select(Entity).where(Entity.case_id == case_id).order_by(Entity.entity_type))
    )


@router.get("/cases/{case_id}/relationships", response_model=list[RelationshipRead])
def list_relationships(
    case_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Relationship]:
    return list(
        db.scalars(
            select(Relationship)
            .where(Relationship.case_id == case_id)
            .order_by(Relationship.created_at)
        )
    )
