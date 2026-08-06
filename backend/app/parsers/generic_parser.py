from __future__ import annotations

import json
from typing import Any

from app.parsers.common import first, parse_time


def parse_generic_json(raw: bytes) -> list[dict]:
    value: Any = json.loads(raw.decode("utf-8-sig"))
    records = value if isinstance(value, list) else value.get("events", [value])
    if not isinstance(records, list):
        raise ValueError("Generic JSON must contain an object, array, or events array")

    output = []
    for record in records:
        event_time, inferred = parse_time(first(record, "event_time", "timestamp", "time"))
        output.append(
            {
                "event_type": str(first(record, "event_type", "type", default="business.event")),
                "event_action": str(first(record, "event_action", "action", default="observed")),
                "event_outcome": first(record, "event_outcome", "outcome", default="unknown"),
                "event_time": event_time,
                "observed_time": event_time,
                "actor": record.get("actor", {}),
                "source": record.get("source", {}),
                "destination": record.get("destination", {}),
                "observables": record.get("observables", []),
                "payload": record.get("payload", record),
                "quality": {"timestamp_inferred": inferred, "parse_confidence": 0.90},
            }
        )
    return output
