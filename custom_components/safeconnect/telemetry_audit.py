"""Allowlisted diagnostic summary of FordConnect response structure.

Includes NO vehicle identifiers, coordinates, account details, OAuth tokens,
opaque metadata, or arbitrary text from the backend. Records are collected
only during an already-budgeted normal cloud telemetry request.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

KEYS = ("doorStatus", "doorLockStatus", "lockStatus", "hoodStatus")
POSITIONS = frozenset({
    "FRONT_LEFT", "FRONT_RIGHT", "REAR_LEFT", "REAR_RIGHT",
    "UNSPECIFIED_FRONT", "UNSPECIFIED_REAR", "TAILGATE",
    "INNER_TAILGATE", "LIFTGATE", "ALL_DOORS", "FRUNK",
})
SIDES = frozenset({"DRIVER", "PASSENGER"})
STATES = frozenset({
    "OPEN", "OPENED", "AJAR", "CLOSED", "CLOSE", "LOCKED",
    "DOUBLE_LOCKED", "UNLOCKED", "UNKNOWN", "INVALID",
})


def _date(value: Any) -> str | None:
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result.astimezone(timezone.utc).isoformat() if result.tzinfo else None
    except (TypeError, ValueError, OverflowError):
        return None


def _enum(value: Any, allowed: frozenset[str]) -> str:
    if not isinstance(value, str):
        return "NOT_REPORTED"
    upper = value.upper()
    return upper if upper in allowed else "OTHER_OR_UNRECOGNIZED"


def summarize_security_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Return safe structure and timestamps, never raw telemetry."""
    metrics = payload.get("metrics")
    if not isinstance(metrics, dict):
        return {"metrics_present": False}
    result: dict[str, Any] = {
        "metrics_present": True,
        "metric_names": sorted(
            key for key in metrics
            if isinstance(key, str) and key.isidentifier() and len(key) <= 64
        )[:250],
        "vehicle_update_time": _date(payload.get("updateTime")),
        "security_records": {},
    }
    for key in KEYS:
        raw = metrics.get(key)
        records = [raw] if isinstance(raw, dict) else raw if isinstance(raw, list) else []
        sanitized = []
        for entry in records[:40]:
            if not isinstance(entry, dict):
                continue
            sanitized.append({
                "position": _enum(entry.get("vehicleDoor"), POSITIONS),
                "side": _enum(entry.get("vehicleSide"), SIDES),
                "status": _enum(entry.get("value"), STATES),
                "sample_time": _date(entry.get("updateTime")),
            })
        result["security_records"][key] = {
            "reported_count": len(records),
            "records": sanitized,
        }
    return result
