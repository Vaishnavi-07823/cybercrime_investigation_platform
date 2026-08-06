from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from dateutil import parser as date_parser


def parse_time(value: Any, *, fallback: datetime | None = None) -> tuple[datetime, bool]:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value, tz=timezone.utc)
    elif isinstance(value, str) and value.strip():
        dt = date_parser.parse(value)
    else:
        return fallback or datetime.now(timezone.utc), True

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
        inferred = True
    else:
        inferred = False
    return dt.astimezone(timezone.utc), inferred


def first(record: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return default
