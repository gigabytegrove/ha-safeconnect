"""Strictly local vehicle security-state freshness evaluation.

Never equate a successful cloud GET with a new vehicle sample. In particular,
an old OPEN or UNLOCKED status must not be presented as current.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SECURITY_KEYS = frozenset({
    "door_front_left_open",
    "door_front_right_open",
    "door_rear_left_open",
    "door_rear_right_open",
    "tailgate_open",
    "hood_open",
    "lock_state",
})
SECURITY_MAX_AGE_SECONDS = 60 * 60
ALLOWED_CLOCK_SKEW_SECONDS = 120


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if date.tzinfo is None:
            return None
        return date.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def security_sample_time(values: dict[str, Any], key: str) -> str | None:
    """Prefer the metric's timestamp; fall back only for older cache formats."""
    stamp = key + "_sample_time"
    if stamp in values:
        value = values[stamp]
        return value if isinstance(value, str) else None
    older = values.get("vehicle_update_time")
    return older if isinstance(older, str) else None


def security_state_is_fresh(
    values: dict[str, Any],
    key: str,
    *,
    now: datetime | None = None,
) -> bool:
    if key not in SECURITY_KEYS:
        return False
    value = values.get(key)
    if key == "lock_state":
        if value not in ("locked", "unlocked", "mixed"):
            return False
    elif not isinstance(value, bool):
        return False
    reported = _parse_timestamp(security_sample_time(values, key))
    if reported is None:
        return False
    now = now or datetime.now(timezone.utc)
    age = (now.astimezone(timezone.utc) - reported).total_seconds()
    return -ALLOWED_CLOCK_SKEW_SECONDS <= age <= SECURITY_MAX_AGE_SECONDS
