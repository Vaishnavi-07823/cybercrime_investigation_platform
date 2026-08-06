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
    raise ValueError("Authentication log must contain a JSON object or array")


def parse_auth_log(raw: bytes) -> list[dict]:
    output = []
    for record in _records(raw):
        event_time, inferred = parse_time(
            first(record, "event_time", "timestamp", "time", "createdDateTime")
        )
        user = first(record, "user", "username", "userPrincipalName", "email")
        source_ip = first(record, "source_ip", "src_ip", "ipAddress", "ip")
        country = first(record, "country", "countryCode", default=None)
        device_id = first(record, "device_id", "deviceId", "device", default=None)
        managed = bool(first(record, "managed", "isManaged", default=False))
        success = first(record, "success", default=None)
        outcome = first(record, "outcome", "status", default=None)
        if success is not None:
            outcome = "success" if bool(success) else "failure"
        outcome = str(outcome or "unknown").casefold()
        app = first(record, "application", "appDisplayName", "app", default=None)
        session_id = first(record, "session_id", "sessionId", "correlationId", default=None)

        observables = []
        if source_ip:
            observables.append(
                {"type": "ipv6" if ":" in str(source_ip) else "ipv4", "value": str(source_ip)}
            )
        if user and "@" in str(user):
            observables.append({"type": "email", "value": str(user).casefold()})

        output.append(
            {
                "event_type": "identity.authentication",
                "event_action": "login",
                "event_outcome": outcome,
                "event_time": event_time,
                "observed_time": event_time,
                "actor": {"user": user, "email": user if user and "@" in str(user) else None},
                "source": {"ip": source_ip, "country": country},
                "destination": {"application": app},
                "observables": observables,
                "payload": {
                    "device_id": device_id,
                    "managed_device": managed,
                    "authentication_factor": first(
                        record, "authentication_factor", "authenticationRequirement"
                    ),
                    "session_id": session_id,
                    "risk_level": first(record, "risk_level", "riskLevelAggregated"),
                    "is_new_country": bool(first(record, "is_new_country", default=False)),
                    "raw_fields": record,
                },
                "quality": {"timestamp_inferred": inferred, "parse_confidence": 0.95},
            }
        )
    return output
