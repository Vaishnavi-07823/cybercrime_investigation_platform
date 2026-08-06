from __future__ import annotations

import hashlib
import io
import json
from datetime import datetime, timezone
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Case, EvidenceArtifact, Finding, NarrativeClaim, Report
from app.services.audit import record_audit
from app.services.storage import storage


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _report_payload(db: Session, case: Case) -> dict[str, Any]:
    evidence = list(
        db.scalars(select(EvidenceArtifact).where(EvidenceArtifact.case_id == case.id))
    )
    findings = list(db.scalars(select(Finding).where(Finding.case_id == case.id)))
    claims = list(
        db.scalars(
            select(NarrativeClaim).where(
                NarrativeClaim.case_id == case.id,
                NarrativeClaim.status == "approved",
            )
        )
    )
    if not claims:
        raise ValueError("At least one narrative claim must be approved before report generation")
    return {
        "case": {
            "id": case.id,
            "title": case.title,
            "description": case.description,
            "type": case.case_type,
            "status": case.status,
            "severity": case.severity,
            "classification": case.classification,
            "created_at": case.created_at.isoformat(),
        },
        "approved_claims": [
            {
                "id": claim.id,
                "text": claim.text,
                "reasoning_type": claim.reasoning_type,
                "confidence": claim.confidence,
                "evidence_refs": claim.evidence_refs,
                "event_refs": claim.event_refs,
                "finding_refs": claim.finding_refs,
                "limitations": claim.limitations,
            }
            for claim in claims
        ],
        "findings": [
            {
                "id": finding.id,
                "title": finding.title,
                "severity": finding.severity,
                "confidence": finding.confidence,
                "event_refs": finding.event_refs,
                "evidence_refs": finding.evidence_refs,
                "explanation": finding.explanation,
            }
            for finding in findings
        ],
        "evidence_inventory": [
            {
                "id": item.id,
                "filename": item.original_filename,
                "source_type": item.source_type,
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
                "acquired_at": item.acquired_at.isoformat(),
            }
            for item in evidence
        ],
        "limitations": [
            "Automated findings and narratives require human validation.",
            "The report does not by itself establish the identity of a natural person responsible "
            "for the observed activity.",
        ],
    }


def _build_pdf(payload: dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=payload["case"]["title"],
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Cybercrime Investigation Case Report", styles["Title"]),
        Spacer(1, 8),
        Paragraph(escape(f"Case: {payload['case']['id']} — {payload['case']['title']}"), styles["Heading2"]),
        Paragraph(escape(f"Classification: {payload['case']['classification']}"), styles["Normal"]),
        Paragraph(escape(f"Severity: {payload['case']['severity']}"), styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Executive Findings", styles["Heading1"]),
    ]
    for claim in payload["approved_claims"]:
        story.extend(
            [
                Paragraph(escape(f"{claim['id']} ({claim['reasoning_type']}, {claim['confidence']})"), styles["Heading3"]),
                Paragraph(escape(claim["text"]), styles["BodyText"]),
                Paragraph(
                    escape("Evidence: " + ", ".join(claim["evidence_refs"] + claim["event_refs"] + claim["finding_refs"])),
                    styles["Italic"],
                ),
                Paragraph(escape("Limitations: " + " ".join(claim["limitations"])), styles["BodyText"]),
                Spacer(1, 8),
            ]
        )

    story.extend([PageBreak(), Paragraph("Evidence Inventory", styles["Heading1"])])
    data = [["Evidence ID", "Filename", "Type", "SHA-256"]]
    for item in payload["evidence_inventory"]:
        data.append([item["id"], item["filename"], item["source_type"], item["sha256"][:20] + "…"])
    table = Table(data, repeatRows=1, colWidths=[35 * mm, 55 * mm, 30 * mm, 50 * mm])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(table)
    story.extend([Spacer(1, 12), Paragraph("General Limitations", styles["Heading1"])])
    for limitation in payload["limitations"]:
        story.append(Paragraph(escape(f"• {limitation}"), styles["BodyText"]))
    doc.build(story)
    return buffer.getvalue()


def generate_report(
    db: Session,
    case: Case,
    *,
    user_id: str,
    source_ip: str | None = None,
) -> Report:
    settings = get_settings()
    payload = _report_payload(db, case)
    generated_at = datetime.now(timezone.utc).isoformat()
    json_document = {
        "report_version": "1.0.0",
        "generated_at": generated_at,
        **payload,
    }
    json_bytes = json.dumps(json_document, indent=2, sort_keys=True).encode("utf-8")
    pdf_bytes = _build_pdf(payload)
    report = Report(
        case_id=case.id,
        storage_bucket=settings.minio_report_bucket,
        pdf_storage_key="pending",
        json_storage_key="pending",
        pdf_sha256=_sha256(pdf_bytes),
        json_sha256=_sha256(json_bytes),
        manifest={},
        generated_by=user_id,
    )
    db.add(report)
    db.flush()
    base = f"{case.id}/{report.id}"
    pdf_key = f"{base}/{report.id}.pdf"
    json_key = f"{base}/{report.id}.json"
    storage.put_bytes(
        bucket=settings.minio_report_bucket,
        key=pdf_key,
        data=pdf_bytes,
        content_type="application/pdf",
    )
    storage.put_bytes(
        bucket=settings.minio_report_bucket,
        key=json_key,
        data=json_bytes,
        content_type="application/json",
    )
    report.pdf_storage_key = pdf_key
    report.json_storage_key = json_key
    report.manifest = {
        "report_id": report.id,
        "case_id": case.id,
        "generated_at": generated_at,
        "pdf_sha256": report.pdf_sha256,
        "json_sha256": report.json_sha256,
        "evidence": [
            {"id": item["id"], "sha256": item["sha256"]}
            for item in payload["evidence_inventory"]
        ],
        "approved_claim_ids": [claim["id"] for claim in payload["approved_claims"]],
        "template_version": report.template_version,
    }
    record_audit(
        db,
        action="report.generate",
        object_type="report",
        object_id=report.id,
        case_id=case.id,
        user_id=user_id,
        source_ip=source_ip,
        details={"pdf_sha256": report.pdf_sha256, "json_sha256": report.json_sha256},
    )
    db.commit()
    db.refresh(report)
    return report
