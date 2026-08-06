from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Case, Report, User
from app.schemas import OperationResult, ReportRead
from app.services.reporting import generate_report
from app.services.storage import storage


router = APIRouter(tags=["Reports"])


@router.post("/cases/{case_id}/reports/generate", response_model=ReportRead)
def generate_case_report(
    case_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Report:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    try:
        return generate_report(
            db,
            case,
            user_id=user.id,
            source_ip=request.client.host if request.client else None,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/cases/{case_id}/reports", response_model=list[ReportRead])
def list_reports(
    case_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Report]:
    return list(
        db.scalars(
            select(Report).where(Report.case_id == case_id).order_by(Report.created_at.desc())
        )
    )


@router.get("/reports/{report_id}/download/{format_name}")
def download_report(
    report_id: str,
    format_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> StreamingResponse:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if format_name == "pdf":
        key = report.pdf_storage_key
        media_type = "application/pdf"
        filename = f"{report.id}.pdf"
    elif format_name == "json":
        key = report.json_storage_key
        media_type = "application/json"
        filename = f"{report.id}.json"
    else:
        raise HTTPException(status_code=400, detail="Format must be pdf or json")
    data = storage.get_bytes(report.storage_bucket, key)
    return StreamingResponse(
        io.BytesIO(data),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
