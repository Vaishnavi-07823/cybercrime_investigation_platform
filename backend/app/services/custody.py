from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CustodyEntry


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _hash_entry(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def append_custody_entry(
    db: Session,
    *,
    evidence_id: str,
    action: str,
    actor_id: str | None,
    actor_type: str = "user",
    details: dict | None = None,
) -> CustodyEntry:
    previous = db.scalar(
        select(CustodyEntry)
        .where(CustodyEntry.evidence_id == evidence_id)
        .order_by(CustodyEntry.created_at.desc(), CustodyEntry.id.desc())
        .limit(1)
    )
    previous_hash = previous.entry_hash if previous else None
    payload = {
        "evidence_id": evidence_id,
        "action": action,
        "actor_id": actor_id,
        "actor_type": actor_type,
        "details": details or {},
        "previous_hash": previous_hash,
    }
    entry = CustodyEntry(
        evidence_id=evidence_id,
        action=action,
        actor_id=actor_id,
        actor_type=actor_type,
        details=details or {},
        previous_hash=previous_hash,
        entry_hash=_hash_entry(payload),
    )
    db.add(entry)
    db.flush()
    return entry


def verify_custody_chain(db: Session, evidence_id: str) -> dict[str, Any]:
    entries = list(
        db.scalars(
            select(CustodyEntry)
            .where(CustodyEntry.evidence_id == evidence_id)
            .order_by(CustodyEntry.created_at, CustodyEntry.id)
        )
    )
    previous_hash: str | None = None
    failures: list[dict[str, Any]] = []
    for position, entry in enumerate(entries, start=1):
        payload = {
            "evidence_id": entry.evidence_id,
            "action": entry.action,
            "actor_id": entry.actor_id,
            "actor_type": entry.actor_type,
            "details": entry.details,
            "previous_hash": previous_hash,
        }
        expected = _hash_entry(payload)
        if entry.previous_hash != previous_hash or entry.entry_hash != expected:
            failures.append(
                {
                    "position": position,
                    "entry_id": entry.id,
                    "stored_previous_hash": entry.previous_hash,
                    "expected_previous_hash": previous_hash,
                    "stored_entry_hash": entry.entry_hash,
                    "expected_entry_hash": expected,
                }
            )
        previous_hash = entry.entry_hash
    return {
        "evidence_id": evidence_id,
        "valid": not failures,
        "entry_count": len(entries),
        "failures": failures,
        "head_hash": previous_hash,
    }
