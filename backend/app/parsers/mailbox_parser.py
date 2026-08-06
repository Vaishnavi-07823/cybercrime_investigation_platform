from __future__ import annotations

import json
from typing import Any

from app.parsers.common import first, parse_time


def _records(raw: bytes) -> list[dict[str, Any]]:
    value = json.loads(raw.decode("utf-8-sig"))
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("events", "records", "value", "items"):
            if isinstance(value.get(key), list):
                return value[key]
        return [value]
    raise ValueError("Mailbox audit log must contain a JSON object or array")


def parse_mailbox_audit(raw: bytes) -> list[dict]:
    output = []
    for record in _records(raw):
        event_time, inferred = parse_time(
            first(record, "event_time", "timestamp", "time", "CreationTime")
        )
        user = first(record, "user", "username", "UserId", "mailbox")
        action = str(first(record, "action", "operation", "Operation", default="unknown"))
        action_lower = action.casefold()
        target = first(
            record,
            "forward_to",
            "forwarding_address",
            "ForwardTo",
            "target",
            default=None,
        )
        rule_name = first(record, "rule_name", "RuleName", "name", default=None)
        external = bool(first(record, "external", "is_external", default=False))
        if target and "@" in str(target) and user and "@" in str(user):
            external = str(target).rsplit("@", 1)[1].casefold() != str(user).rsplit("@", 1)[1].casefold()

        event_type = "mailbox.audit"
        if "forward" in action_lower or "inboxrule" in action_lower or "rule" in action_lower:
            event_type = "mailbox.rule"

        observables = []
        if user and "@" in str(user):
            observables.append({"type": "email", "value": str(user).casefold()})
        if target and "@" in str(target):
            observables.append({"type": "email", "value": str(target).casefold()})

        output.append(
            {
                "event_type": event_type,
                "event_action": action,
                "event_outcome": "success",
                "event_time": event_time,
                "observed_time": event_time,
                "actor": {"user": user, "email": user if user and "@" in str(user) else None},
                "source": {},
                "destination": {"email": target},
                "observables": observables,
                "payload": {
                    "rule_name": rule_name,
                    "forward_to": target,
                    "external_forwarding": external,
                    "client_ip": first(record, "client_ip", "ClientIP"),
                    "raw_fields": record,
                },
                "quality": {"timestamp_inferred": inferred, "parse_confidence": 0.95},
            }
        )
    return output
