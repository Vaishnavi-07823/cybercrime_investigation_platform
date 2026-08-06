from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EvidenceArtifact, NormalizedEvent
from app.parsers import parse_auth_log, parse_eml, parse_generic_json, parse_mailbox_audit
from app.services.audit import record_audit
from app.services.custody import append_custody_entry
from app.services.search import search
from app.services.storage import storage


Parser = Callable[[bytes], list[dict]]
PARSERS: dict[str, tuple[str, str, Parser]] = {
    "email": ("eml-parser", "1.0.0", parse_eml),
    "eml": ("eml-parser", "1.0.0", parse_eml),
    "auth_log": ("auth-json-parser", "1.0.0", parse_auth_log),
    "identity_log": ("auth-json-parser", "1.0.0", parse_auth_log),
    "mailbox_audit": ("mailbox-audit-parser", "1.0.0", parse_mailbox_audit),
    "generic_json": ("generic-json-parser", "1.0.0", parse_generic_json),
    "business_event": ("generic-json-parser", "1.0.0", parse_generic_json),
}


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def process_evidence(
    db: Session,
    evidence: EvidenceArtifact,
    *,
    user_id: str,
    source_ip: str | None = None,
) -> list[NormalizedEvent]:
    parser_info = PARSERS.get(evidence.source_type.casefold())
    if not parser_info:
        raise ValueError(
            f"Unsupported source_type '{evidence.source_type}'. Supported: {sorted(PARSERS)}"
        )
    parser_name, parser_version, parser = parser_info
    raw = storage.get_bytes(evidence.storage_bucket, evidence.storage_key)
    parsed_events = parser(raw)
    inserted: list[NormalizedEvent] = []

    for parsed in parsed_events:
        record_payload = {
            "case_id": evidence.case_id,
            "evidence_id": evidence.id,
            "event_type": parsed["event_type"],
            "event_action": parsed["event_action"],
            "event_outcome": parsed.get("event_outcome"),
            "event_time": parsed["event_time"],
            "actor": parsed.get("actor", {}),
            "source": parsed.get("source", {}),
            "destination": parsed.get("destination", {}),
            "observables": parsed.get("observables", []),
            "payload": parsed.get("payload", {}),
        }
        digest = canonical_hash(record_payload)
        existing = db.scalar(
            select(NormalizedEvent).where(
                NormalizedEvent.case_id == evidence.case_id,
                NormalizedEvent.record_hash == digest,
            )
        )
        if existing:
            continue
        event = NormalizedEvent(
            case_id=evidence.case_id,
            evidence_id=evidence.id,
            schema_version="1.0.0",
            event_type=parsed["event_type"],
            event_action=parsed["event_action"],
            event_outcome=parsed.get("event_outcome"),
            event_time=parsed["event_time"],
            observed_time=parsed.get("observed_time"),
            actor=parsed.get("actor", {}),
            source=parsed.get("source", {}),
            destination=parsed.get("destination", {}),
            observables=parsed.get("observables", []),
            payload=parsed.get("payload", {}),
            transformation={
                "parser": parser_name,
                "parser_version": parser_version,
                "source_sha256": evidence.sha256,
            },
            quality=parsed.get("quality", {}),
            record_hash=digest,
        )
        db.add(event)
        db.flush()
        inserted.append(event)

    evidence.processed = True
    append_custody_entry(
        db,
        evidence_id=evidence.id,
        action="NORMALIZED",
        actor_id=user_id,
        details={
            "parser": parser_name,
            "parser_version": parser_version,
            "event_count": len(inserted),
            "event_ids": [event.id for event in inserted],
        },
    )
    record_audit(
        db,
        action="evidence.process",
        object_type="evidence",
        object_id=evidence.id,
        case_id=evidence.case_id,
        user_id=user_id,
        source_ip=source_ip,
        details={"parser": parser_name, "event_count": len(inserted)},
    )
    db.commit()

    for event in inserted:
        try:
            search.index_event(event)
        except Exception:
            # PostgreSQL remains authoritative for the MVP. A production system should queue retries.
            pass
    return inserted
