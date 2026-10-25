"""Ford last-known GPS reporting and age helpers.

Pure functions. Never request Ford data or infer real-time movement.
"""
from __future__ import annotations

from datetime import datetime, timezone

GPS_AGE_STALE_SECONDS = 5 * 60


def gps_age_seconds(values: dict[str, Any], *, now: datetime | None = None) -> float | None:
    """Age of the POSITION metric, not the latest Ford cloud GET."""
    raw = values.get("location_sample_time")
    if not isinstance(raw, str):
        return None
    try:
        timestamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            return None
        instant = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        age = (instant - timestamp.astimezone(timezone.utc)).total_seconds()
        return max(0, age) if age >= -120 else None
    except (TypeError, ValueError, OverflowError):
        return None


def gps_is_stale(values: dict[str, Any], *, now: datetime | None = None) -> bool:
    age = gps_age_seconds(values, now=now)
    return age is None or age > GPS_AGE_STALE_SECONDS


def preserve_newer_gps(previous: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """Do not replace a newer cached GPS position with an older cloud snapshot.

    GPS is a coherent latitude/longitude/time triple. A response that omits
    coordinates never resets the previous position, and a response without a
    GPS timestamp cannot supersede a dated position.
    """
    if not isinstance(previous, dict) or not isinstance(incoming, dict):
        raise ValueError("GPS merge requires dictionaries")
    gps_fields = ("latitude", "longitude", "location_sample_time")
    if not ("latitude" in incoming and "longitude" in incoming):
        # Do not allow an isolated position timestamp to change old GPS age.
        return {k: v for k, v in incoming.items() if k not in gps_fields}
    old_time = previous.get("location_sample_time")
    new_time = incoming.get("location_sample_time")
    if isinstance(old_time, str):
        if not isinstance(new_time, str):
            return {k: v for k, v in incoming.items() if k not in gps_fields}
        try:
            previous_dt = datetime.fromisoformat(old_time.replace("Z", "+00:00"))
            current_dt = datetime.fromisoformat(new_time.replace("Z", "+00:00"))
            if previous_dt.tzinfo is None or current_dt.tzinfo is None:
                raise ValueError("Undated GPS")
            if current_dt <= previous_dt:
                return {k: v for k, v in incoming.items() if k not in gps_fields}
        except (TypeError, ValueError, OverflowError):
            # A dated cached coordinate must not be overwritten by an
            # invalidly timestamped cloud record.
            return {k: v for k, v in incoming.items() if k not in gps_fields}
    return incoming
