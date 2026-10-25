"""Pure, conservative extraction of FordConnect Query telemetry.

Never infer live movement from a stale position or an absent ignition state.
Ford reports tire pressure in kPa, distances in km and temperatures in C.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from typing import Any

KPA_TO_PSI = 0.1450377377
KM_TO_MILES = 0.6213711922


def _records(metrics: dict[str, Any], key: str) -> list[dict[str, Any]]:
    item = metrics.get(key)
    if isinstance(item, dict):
        return [item] if "value" in item else []
    if isinstance(item, list):
        return [v for v in item if isinstance(v, dict) and "value" in v]
    return []


def _first(metrics: dict[str, Any], key: str) -> Any:
    records = _records(metrics, key)
    return records[0].get("value") if records else None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if isfinite(number) else None


def _convert(value: Any, multiplier: float = 1, precision: int = 1) -> float | None:
    n = _number(value)
    return round(n * multiplier, precision) if n is not None else None


def _door_key(record: dict[str, Any]) -> str | None:
    door = str(record.get("vehicleDoor", "")).upper()
    side = str(record.get("vehicleSide", "")).upper()
    if door in {"FRONT_LEFT", "FRONT_RIGHT", "REAR_LEFT", "REAR_RIGHT"}:
        return "door_" + door.lower()
    if door in {"UNSPECIFIED_FRONT", "UNSPECIFIED_REAR"} and side in {"DRIVER", "PASSENGER"}:
        return "door_" + ("front" if door == "UNSPECIFIED_FRONT" else "rear") + ("_left" if side == "DRIVER" else "_right")
    if door in {"TAILGATE", "INNER_TAILGATE", "LIFTGATE"}:
        return "tailgate"
    return None


def _wheel_key(record: dict[str, Any]) -> str | None:
    wheel = str(record.get("vehicleWheel", "")).upper()
    for position in ("FRONT_LEFT", "FRONT_RIGHT", "REAR_LEFT", "REAR_RIGHT"):
        if wheel == position:
            return "tire_" + position.lower()
    return None


def _as_open(value: Any) -> bool | None:
    if not isinstance(value, str):
        return None
    value = value.upper()
    if value in {"OPEN", "AJAR", "OPENED"}:
        return True
    if value in {"CLOSED", "CLOSE"}:
        return False
    return None


def _as_iso(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        value = value.replace("Z", "+00:00")
        instant = datetime.fromisoformat(value)
        if instant.tzinfo is None:
            return None
        return instant.astimezone(timezone.utc).isoformat()
    except ValueError:
        return None


def normalize(payload: dict[str, Any]) -> dict[str, Any]:
    """Return allowlisted metrics only; discard raw VIN, tokens, and API metadata."""
    if not isinstance(payload, dict) or not isinstance(payload.get("metrics"), dict):
        raise ValueError("Missing FordConnect telemetry metrics object")
    metrics = payload["metrics"]
    result: dict[str, Any] = {}

    numeric = {
        "fuel_percent": ("fuelLevel", 1, 1),
        "fuel_range_mi": ("fuelRange", KM_TO_MILES, 1),
        "odometer_mi": ("odometer", KM_TO_MILES, 1),
        "oil_life_percent": ("oilLifeRemaining", 1, 1),
        "battery_12v_percent": ("batteryStateOfCharge", 1, 1),
        "battery_12v_volts": ("batteryVoltage", 1, 2),
        "outside_temp_c": ("outsideTemperature", 1, 1),
        "cabin_temp_c": ("cabinTemperature", 1, 1),
        "coolant_temp_c": ("engineCoolantTemp", 1, 1),
        "engine_oil_temp_c": ("engineOilTemp", 1, 1),
        "speed_kmh": ("speed", 1, 1),
        "engine_rpm": ("engineSpeed", 1, 0),
    }
    for name, (source, factor, precision) in numeric.items():
        number = _convert(_first(metrics, source), factor, precision)
        if number is not None:
            result[name] = number

    for name, source in (
        ("ignition", "ignitionStatus"),
        ("gear", "gearLeverPosition"),
        ("alarm", "alarmStatus"),
        ("deep_sleep", "deepSleepMode"),
        ("tire_system_status", "tirePressureSystemStatus"),
    ):
        value = _first(metrics, source)
        if isinstance(value, (str, int, float, bool)):
            result[name] = str(value).lower() if isinstance(value, bool) else value

    # Derived from actual Ford fields only. OFF is *not* evidence that a
    # vehicle is safely parked: it could have been transported/towed.
    ignition = str(result.get("ignition", "")).upper()
    gear = str(result.get("gear", "")).upper()
    speed = result.get("speed_kmh")
    if isinstance(speed, float) and speed > 1:
        result["vehicle_activity"] = "moving"
    elif ignition in {"RUNNING", "ENGINE_RUNNING"}:
        result["vehicle_activity"] = "running"
    elif ignition in {"OFF", "IGNITION_OFF"} and gear in {"P", "PARK", "PARKING"}:
        result["vehicle_activity"] = "parked"
    elif ignition in {"OFF", "IGNITION_OFF"}:
        result["vehicle_activity"] = "engine off (parking unknown)"

    for record in _records(metrics, "tirePressure"):
        key = _wheel_key(record)
        pressure = _convert(record.get("value"), KPA_TO_PSI)
        if key and pressure is not None:
            result[key + "_psi"] = pressure

    for record in _records(metrics, "doorStatus"):
        key = _door_key(record)
        opened = _as_open(record.get("value"))
        if key and opened is not None:
            field = key + "_open"
            record_time = _as_iso(record.get("updateTime"))
            previous_time = result.get(field + "_sample_time")
            # When multiple records describe a door, prefer the most recent
            # documented measurement, not whichever happens to appear last.
            if previous_time and (not record_time or record_time < previous_time):
                continue
            result[field] = opened
            if record_time:
                result[field + "_sample_time"] = record_time
    hood_records = _records(metrics, "hoodStatus")
    hood = _as_open(hood_records[0]["value"]) if hood_records else None
    if hood is not None:
        result["hood_open"] = hood
        hood_time = _as_iso(hood_records[0].get("updateTime"))
        if hood_time:
            result["hood_open_sample_time"] = hood_time

    # Ford can report a lock value for each door or ALL_DOORS. Don't report
    # 'locked' if individual doors disagree. Unknown remains unknown.
    locks: list[str] = []
    lock_times: list[str] = []
    unknown_locks = False
    all_doors_report: str | None = None
    all_doors_time: str | None = None
    for record in _records(metrics, "doorLockStatus") + _records(metrics, "lockStatus"):
        value = record.get("value")
        if not isinstance(value, str):
            unknown_locks = True
            continue
        state = value.upper()
        if state == "DOUBLE_LOCKED":
            state = "LOCKED"
        if state not in {"LOCKED", "UNLOCKED"}:
            unknown_locks = True
            continue
        report_time = _as_iso(record.get("updateTime"))
        if str(record.get("vehicleDoor", "")).upper() == "ALL_DOORS":
            if all_doors_report is None or not all_doors_time or (report_time and report_time >= all_doors_time):
                all_doors_report = state
                all_doors_time = report_time
            continue
        locks.append(state)
        if report_time:
            lock_times.append(report_time)
    if all_doors_report is not None:
        result["lock_state"] = all_doors_report.lower()
        if all_doors_time:
            result["lock_state_sample_time"] = all_doors_time
    elif locks:
        result["lock_state"] = (
            "mixed" if "LOCKED" in locks and "UNLOCKED" in locks
            else "unknown" if unknown_locks
            else "locked" if all(x == "LOCKED" for x in locks)
            else "unlocked"
        )
        # When aggregate status depends on several doors, use the oldest
        # constituent report time. A single old reading makes it stale.
        if lock_times:
            result["lock_state_sample_time"] = min(lock_times)

    # Position can be a single metric record OR a list. Choose the newest
    # valid coordinate pair, not the first item, and keep its own timestamp.
    candidates: list[tuple[str | None, float, float]] = []
    for record in _records(metrics, "position"):
        position = record.get("value")
        if not isinstance(position, dict):
            continue
        loc = position.get("location")
        if not isinstance(loc, dict):
            continue
        lat = _number(loc.get("lat"))
        lon = _number(loc.get("lon"))
        if lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180:
            candidates.append((_as_iso(record.get("updateTime")), lat, lon))
    if candidates:
        timestamp, lat, lon = max(candidates, key=lambda v: (v[0] is not None, v[0] or ""))
        result["latitude"] = lat
        result["longitude"] = lon
        if timestamp:
            result["location_sample_time"] = timestamp
    top_time = _as_iso(payload.get("updateTime"))
    if top_time:
        result["vehicle_update_time"] = top_time

    # Pin each new security value to its OWN snapshot's report time.
    # If that field is missing in a future query, a newer vehicle-wide
    # timestamp MUST NOT make its old value look fresh.
    for key in (
        "door_front_left_open", "door_front_right_open",
        "door_rear_left_open", "door_rear_right_open",
        "tailgate_open", "hood_open", "lock_state",
    ):
        if key in result and key + "_sample_time" not in result:
            result[key + "_sample_time"] = top_time
    return result
