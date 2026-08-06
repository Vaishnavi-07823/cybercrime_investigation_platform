from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import AnalystDecision, Case, NarrativeClaim, User
from app.schemas import ClaimRead, ClaimReviewRequest, OperationResult
from app.services.audit import record_audit
from app.services.narrative import generate_narrative


router = APIRouter(tags=["Narratives"])


@router.post("/cases/{case_id}/narratives/generate", response_model=OperationResult)
def generate_case_narrative(
    case_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OperationResult:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    try:
        claims = generate_narrative(
            db,
            case,
            user_id=user.id,
            source_ip=request.client.host if request.client else None,
        )
    except (ValueError, RuntimeError) as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return OperationResult(
        message="Narrative claims generated",
        count=len(claims),
        details={"claim_ids": [claim.id for claim in claims]},
    )


@router.get("/cases/{case_id}/claims", response_model=list[ClaimRead])
def list_claims(
    case_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[NarrativeClaim]:
    return list(
        db.scalars(
            select(NarrativeClaim)
            .where(NarrativeClaim.case_id == case_id)
            .order_by(NarrativeClaim.created_at.desc())
        )
    )


@router.patch("/claims/{claim_id}/review", response_model=ClaimRead)
def review_claim(
    claim_id: str,
    payload: ClaimReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NarrativeClaim:
    claim = db.get(NarrativeClaim, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if payload.decision == "edited":
        if not payload.edited_text or not payload.edited_text.strip():
            raise HTTPException(status_code=422, detail="edited_text is required for edited decisions")
        claim.text = payload.edited_text.strip()
        claim.status = "approved"
    else:
        claim.status = payload.decision
    decision = AnalystDecision(
        case_id=claim.case_id,
        object_type="narrative_claim",
        object_id=claim.id,
        decision=payload.decision,
        rationale=payload.rationale,
        analyst_id=user.id,
    )
    db.add(decision)
    record_audit(
        db,
        action="claim.review",
        object_type="narrative_claim",
        object_id=claim.id,
        case_id=claim.case_id,
        user_id=user.id,
        source_ip=request.client.host if request.client else None,
        details={"decision": payload.decision, "rationale": payload.rationale},
    )
    db.commit()
    db.refresh(claim)
    return claim
