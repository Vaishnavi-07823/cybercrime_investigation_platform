from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Case, CustodyEntry, EvidenceArtifact, User
from app.schemas import CustodyRead, EvidenceRead, LegalHoldRequest, OperationResult
from app.services.evidence import create_evidence, verify_evidence
from app.services.normalization import process_evidence
from app.services.custody import append_custody_entry, verify_custody_chain
from app.services.audit import record_audit


router = APIRouter(tags=["Evidence"])


@router.post("/cases/{case_id}/evidence", response_model=EvidenceRead, status_code=201)
async def upload_evidence(
    case_id: str,
    request: Request,
    source_type: str = Form(...),
    acquisition_method: str = Form("manual_upload"),
    notes: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EvidenceArtifact:
    if not db.get(Case, case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Evidence file is empty")
    if len(data) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Development upload limit is 100 MB")
    try:
        return create_evidence(
            db,
            case_id=case_id,
            source_type=source_type,
            filename=file.filename or "unnamed-evidence",
            media_type=file.content_type,
            data=data,
            user_id=user.id,
            acquisition_method=acquisition_method,
            notes=notes,
            source_ip=request.client.host if request.client else None,
        )
    except FileExistsError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/cases/{case_id}/evidence", response_model=list[EvidenceRead])
def list_evidence(
    case_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[EvidenceArtifact]:
    return list(
        db.scalars(
            select(EvidenceArtifact)
            .where(EvidenceArtifact.case_id == case_id)
            .order_by(EvidenceArtifact.created_at.desc())
        )
    )


@router.get("/evidence/{evidence_id}", response_model=EvidenceRead)
def get_evidence(
    evidence_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> EvidenceArtifact:
    evidence = db.get(EvidenceArtifact, evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return evidence


@router.get("/evidence/{evidence_id}/custody", response_model=list[CustodyRead])
def custody_history(
    evidence_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[CustodyEntry]:
    if not db.get(EvidenceArtifact, evidence_id):
        raise HTTPException(status_code=404, detail="Evidence not found")
    return list(
        db.scalars(
            select(CustodyEntry)
            .where(CustodyEntry.evidence_id == evidence_id)
            .order_by(CustodyEntry.created_at)
        )
    )


@router.get("/evidence/{evidence_id}/custody/verify")
def verify_custody(
    evidence_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    if not db.get(EvidenceArtifact, evidence_id):
        raise HTTPException(status_code=404, detail="Evidence not found")
    return verify_custody_chain(db, evidence_id)


@router.post("/evidence/{evidence_id}/legal-hold", response_model=EvidenceRead)
def set_legal_hold(
    evidence_id: str,
    payload: LegalHoldRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EvidenceArtifact:
    evidence = db.get(EvidenceArtifact, evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    evidence.legal_hold = payload.enabled
    action = "LEGAL_HOLD_APPLIED" if payload.enabled else "LEGAL_HOLD_RELEASED"
    append_custody_entry(
        db,
        evidence_id=evidence.id,
        action=action,
        actor_id=user.id,
        details={"reason": payload.reason},
    )
    record_audit(
        db,
        action="evidence.legal_hold",
        object_type="evidence",
        object_id=evidence.id,
        case_id=evidence.case_id,
        user_id=user.id,
        source_ip=request.client.host if request.client else None,
        details={"enabled": payload.enabled, "reason": payload.reason},
    )
    db.commit()
    db.refresh(evidence)
    return evidence


@router.post("/evidence/{evidence_id}/verify")
def verify(
    evidence_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    evidence = db.get(EvidenceArtifact, evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return verify_evidence(
        db,
        evidence,
        user_id=user.id,
        source_ip=request.client.host if request.client else None,
    )


@router.post("/evidence/{evidence_id}/process", response_model=OperationResult)
def process(
    evidence_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OperationResult:
    evidence = db.get(EvidenceArtifact, evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    try:
        events = process_evidence(
            db,
            evidence,
            user_id=user.id,
            source_ip=request.client.host if request.client else None,
        )
    except (ValueError, UnicodeDecodeError) as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return OperationResult(message="Evidence processed", count=len(events))
