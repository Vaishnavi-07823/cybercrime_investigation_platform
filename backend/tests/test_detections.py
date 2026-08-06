from pathlib import Path

from app.detections.rules import RULES
from app.models import Case, NormalizedEvent
from app.parsers import parse_auth_log, parse_eml, parse_generic_json, parse_mailbox_audit
import hashlib
import json


SAMPLES = Path(__file__).resolve().parents[2] / "sample-data"


def to_model(parsed: dict, index: int, evidence_id: str) -> NormalizedEvent:
    payload = {
        "event_type": parsed["event_type"],
        "event_action": parsed["event_action"],
        "event_time": parsed["event_time"],
        "actor": parsed.get("actor", {}),
        "source": parsed.get("source", {}),
        "payload": parsed.get("payload", {}),
    }
    return NormalizedEvent(
        id=f"EVT-TEST-{index}",
        case_id="CASE-TEST",
        evidence_id=evidence_id,
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
        transformation={},
        quality=parsed.get("quality", {}),
        record_hash=hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest(),
    )


def test_demo_dataset_produces_core_findings() -> None:
    parsed = []
    parsed.extend(parse_eml((SAMPLES / "suspicious-email.eml").read_bytes()))
    parsed.extend(parse_auth_log((SAMPLES / "authentication-events.json").read_bytes()))
    parsed.extend(parse_mailbox_audit((SAMPLES / "mailbox-audit-events.json").read_bytes()))
    parsed.extend(parse_generic_json((SAMPLES / "business-events.json").read_bytes()))
    events = [to_model(item, index, f"EVD-{index}") for index, item in enumerate(parsed)]
    case = Case(
        id="CASE-TEST",
        title="Demo",
        case_type="bec",
        severity="high",
        classification="restricted",
        context={"trusted_domains": ["trusted-supplier.example"]},
        created_by="USR-TEST",
    )

    findings = [finding for rule in RULES for finding in rule(events, case)]
    rule_ids = {finding["rule_id"] for finding in findings}
    assert {"DET-001", "DET-002", "DET-003", "DET-004", "DET-005", "DET-006"} <= rule_ids
