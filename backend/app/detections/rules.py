from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import timedelta
from typing import Any

from rapidfuzz.distance import Levenshtein

from app.models import Case, NormalizedEvent


RULE_VERSION = "1.0.0"


def _fingerprint(rule_id: str, event_refs: list[str], extra: dict[str, Any] | None = None) -> str:
    payload = {
        "rule_id": rule_id,
        "events": sorted(event_refs),
        "extra": extra or {},
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _finding(
    *,
    rule_id: str,
    title: str,
    finding_type: str,
    severity: str,
    confidence: float,
    score: float,
    events: list[NormalizedEvent],
    explanation: list[str],
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event_refs = [event.id for event in events]
    evidence_refs = sorted({event.evidence_id for event in events})
    details = details or {}
    return {
        "rule_id": rule_id,
        "rule_version": RULE_VERSION,
        "title": title,
        "finding_type": finding_type,
        "severity": severity,
        "confidence": confidence,
        "score": score,
        "event_refs": event_refs,
        "evidence_refs": evidence_refs,
        "explanation": explanation,
        "details": details,
        "fingerprint": _fingerprint(rule_id, event_refs, details),
    }


def detect_new_country(events: list[NormalizedEvent], _: Case) -> list[dict[str, Any]]:
    findings = []
    countries_by_user: dict[str, set[str]] = defaultdict(set)
    auth_events = [event for event in events if event.event_type == "identity.authentication"]
    for event in sorted(auth_events, key=lambda item: item.event_time):
        user = str(event.actor.get("email") or event.actor.get("user") or "").casefold()
        country = str(event.source.get("country") or "").upper()
        explicit = bool(event.payload.get("is_new_country"))
        previously_seen = countries_by_user[user]
        is_new = explicit or (bool(previously_seen) and country and country not in previously_seen)
        if is_new and event.event_outcome == "success":
            findings.append(
                _finding(
                    rule_id="DET-001",
                    title="Successful login from a new country",
                    finding_type="identity_anomaly",
                    severity="high",
                    confidence=0.90,
                    score=0.90,
                    events=[event],
                    explanation=[
                        f"The successful authentication for {user or 'the account'} originated from "
                        f"country {country or 'unknown'}, which was marked or observed as new."
                    ],
                    details={"user": user, "country": country},
                )
            )
        if user and country:
            previously_seen.add(country)
    return findings


def detect_unmanaged_device(events: list[NormalizedEvent], _: Case) -> list[dict[str, Any]]:
    findings = []
    for event in events:
        if (
            event.event_type == "identity.authentication"
            and event.event_outcome == "success"
            and event.payload.get("managed_device") is False
        ):
            findings.append(
                _finding(
                    rule_id="DET-002",
                    title="Successful login from an unmanaged device",
                    finding_type="identity_anomaly",
                    severity="medium",
                    confidence=0.80,
                    score=0.75,
                    events=[event],
                    explanation=["A successful authentication originated from an unmanaged device."],
                    details={
                        "user": event.actor.get("email") or event.actor.get("user"),
                        "device_id": event.payload.get("device_id"),
                    },
                )
            )
    return findings


def detect_external_forwarding(events: list[NormalizedEvent], _: Case) -> list[dict[str, Any]]:
    findings = []
    for event in events:
        if event.event_type == "mailbox.rule" and event.payload.get("external_forwarding"):
            findings.append(
                _finding(
                    rule_id="DET-003",
                    title="External mailbox forwarding rule created",
                    finding_type="mailbox_persistence",
                    severity="high",
                    confidence=0.98,
                    score=0.97,
                    events=[event],
                    explanation=[
                        "A mailbox rule forwards messages to an address outside the user's domain."
                    ],
                    details={
                        "user": event.actor.get("email") or event.actor.get("user"),
                        "forward_to": event.payload.get("forward_to"),
                        "rule_name": event.payload.get("rule_name"),
                    },
                )
            )
    return findings


def detect_lookalike_domain(events: list[NormalizedEvent], case: Case) -> list[dict[str, Any]]:
    trusted_domains = {
        str(domain).casefold().strip(".") for domain in case.context.get("trusted_domains", [])
    }
    findings = []
    if not trusted_domains:
        return findings

    for event in events:
        if event.event_type != "email.message":
            continue
        sender_domain = str(event.payload.get("sender_domain") or "").casefold().strip(".")
        if not sender_domain or sender_domain in trusted_domains:
            continue
        nearest = min(trusted_domains, key=lambda domain: Levenshtein.distance(sender_domain, domain))
        distance = Levenshtein.distance(sender_domain, nearest)
        if distance <= 2:
            findings.append(
                _finding(
                    rule_id="DET-004",
                    title="Potential lookalike supplier domain",
                    finding_type="email_impersonation",
                    severity="high",
                    confidence=0.90 if distance == 1 else 0.80,
                    score=0.93 if distance == 1 else 0.82,
                    events=[event],
                    explanation=[
                        f"Sender domain '{sender_domain}' is {distance} edit(s) from trusted domain "
                        f"'{nearest}'."
                    ],
                    details={
                        "sender_domain": sender_domain,
                        "trusted_domain": nearest,
                        "edit_distance": distance,
                    },
                )
            )
    return findings


def detect_rapid_payee_payment(events: list[NormalizedEvent], _: Case) -> list[dict[str, Any]]:
    changes = [event for event in events if event.event_type == "payment.payee_change"]
    approvals = [event for event in events if event.event_type == "payment.approval"]
    findings = []
    for change in changes:
        account = change.payload.get("bank_account") or change.destination.get("bank_account")
        for approval in approvals:
            approved_account = approval.payload.get("bank_account") or approval.destination.get(
                "bank_account"
            )
            delta = approval.event_time - change.event_time
            if (
                account
                and account == approved_account
                and timedelta(0) <= delta <= timedelta(hours=4)
            ):
                findings.append(
                    _finding(
                        rule_id="DET-005",
                        title="New payee followed by rapid payment approval",
                        finding_type="payment_fraud",
                        severity="critical",
                        confidence=0.92,
                        score=0.96,
                        events=[change, approval],
                        explanation=[
                            f"A payment to the newly changed bank account was approved {delta} later."
                        ],
                        details={"bank_account": account, "elapsed_seconds": delta.total_seconds()},
                    )
                )
    return findings


def detect_suspicious_oauth(events: list[NormalizedEvent], _: Case) -> list[dict[str, Any]]:
    findings = []
    for event in events:
        if event.event_type != "identity.oauth_consent":
            continue
        permissions = {str(item).casefold() for item in event.payload.get("permissions", [])}
        unfamiliar = bool(event.payload.get("unfamiliar_application", False))
        mail_access = any("mail" in permission for permission in permissions)
        if unfamiliar and mail_access:
            findings.append(
                _finding(
                    rule_id="DET-006",
                    title="Unfamiliar OAuth application granted mail access",
                    finding_type="cloud_persistence",
                    severity="high",
                    confidence=0.88,
                    score=0.89,
                    events=[event],
                    explanation=[
                        "An unfamiliar OAuth application received one or more mail-related permissions."
                    ],
                    details={"permissions": sorted(permissions)},
                )
            )
    return findings


RULES = [
    detect_new_country,
    detect_unmanaged_device,
    detect_external_forwarding,
    detect_lookalike_domain,
    detect_rapid_payee_payment,
    detect_suspicious_oauth,
]
