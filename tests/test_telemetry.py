"""Offline tests for data extraction; do not import Home Assistant."""
import importlib.util
from pathlib import Path

import pytest


SRC = Path(__file__).resolve().parents[1] / "custom_components" / "safeford" / "telemetry.py"
spec = importlib.util.spec_from_file_location("safeford_telemetry_test", SRC)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
normalize = module.normalize


def sample():
    return {
        "vin": "3FTTW8B91SRA12345",
        "access_token": "never-store-me",
        "updateTime": "2026-10-25T11:00:00Z",
        "metrics": {
            "position": {"value": {"location": {"lat": 30.8321, "lon": -83.2803}}, "updateTime": "2026-10-25T10:45:00Z"},
            "fuelLevel": {"value": 64.5},
            "fuelRange": {"value": 415},
            "odometer": {"value": 28002.3},
            "oilLifeRemaining": {"value": 74},
            "ignitionStatus": {"value": "OFF"},
            "tirePressure": [
                {"vehicleWheel": "FRONT_LEFT", "value": 242},
                {"vehicleWheel": "FRONT_RIGHT", "value": 241},
                {"vehicleWheel": "REAR_LEFT", "value": 240},
                {"vehicleWheel": "REAR_RIGHT", "value": 243},
            ],
            "doorStatus": [
                {"vehicleDoor": "FRONT_LEFT", "value": "CLOSED"},
                {"vehicleDoor": "FRONT_RIGHT", "value": "OPEN"},
                {"vehicleDoor": "REAR_LEFT", "value": "AJAR"},
                {"vehicleDoor": "REAR_RIGHT", "value": "CLOSED"},
            ],
            "doorLockStatus": [{"vehicleDoor": "ALL_DOORS", "value": "LOCKED"}],
        },
    }


def test_main_maverick_telemetry():
    result = normalize(sample())
    assert result["fuel_percent"] == 64.5
    assert result["fuel_range_mi"] == pytest.approx(257.9)
    assert result["oil_life_percent"] == 74
    assert result["tire_front_left_psi"] == 35.1
    assert result["lock_state"] == "locked"
    assert result["door_front_right_open"] is True
    assert result["door_front_left_open"] is False
    assert result["door_rear_left_open"] is True
    assert result["latitude"] == 30.8321
    assert result["longitude"] == -83.2803
    assert result["location_sample_time"] == "2026-10-25T10:45:00+00:00"
    assert result["vehicle_update_time"] == "2026-10-25T11:00:00+00:00"
    assert "vin" not in result and "access_token" not in result


def test_partial_payload_never_invents_values():
    assert normalize({"metrics": {"ignitionStatus": {"value": "OFF"}}}) == {"ignition": "OFF", "vehicle_activity": "engine off (parking unknown)"}


def test_rejects_invalid_structure():
    with pytest.raises(ValueError):
        normalize({"metrics": []})


def test_invalid_gps_not_exposed():
    item = sample()
    item["metrics"]["position"]["value"]["location"]["lat"] = 390
    result = normalize(item)
    assert "latitude" not in result and "longitude" not in result


def test_mixed_locks_and_unknown_doors():
    item = sample()
    item["metrics"]["doorLockStatus"] = [
        {"vehicleDoor": "FRONT_LEFT", "value": "LOCKED"},
        {"vehicleDoor": "FRONT_RIGHT", "value": "UNLOCKED"},
    ]
    item["metrics"]["doorStatus"][0]["value"] = "UNKNOWN"
    result = normalize(item)
    assert result["lock_state"] == "mixed"
    assert "door_front_left_open" not in result


def test_unknown_lock_not_unlocked():
    item = sample()
    item["metrics"]["doorLockStatus"] = [{"vehicleDoor": "ALL_DOORS", "value": "UNKNOWN"}]
    assert "lock_state" not in normalize(item)


def test_ford_unspecified_door_mapped():
    item = {"metrics": {"doorStatus": [
        {"vehicleDoor": "UNSPECIFIED_FRONT", "vehicleSide": "DRIVER", "value": "OPEN"},
        {"vehicleDoor": "UNSPECIFIED_REAR", "vehicleSide": "PASSENGER", "value": "CLOSED"},
    ]}}
    val = normalize(item)
    assert val["door_front_left_open"] is True
    assert val["door_rear_right_open"] is False


def test_unknown_individual_lock_does_not_claim_locked():
    item = sample()
    item["metrics"]["doorLockStatus"] = [
        {"vehicleDoor": "FRONT_LEFT", "value": "LOCKED"},
        {"vehicleDoor": "REAR_LEFT", "value": "UNKNOWN"},
    ]
    assert normalize(item)["lock_state"] == "unknown"


def test_explicit_all_doors_lock_overrides_unknown_mechanical():
    item = sample()
    item["metrics"]["doorLockStatus"] = [
        {"vehicleDoor": "REAR_LEFT", "value": "UNKNOWN"},
        {"vehicleDoor": "ALL_DOORS", "value": "DOUBLE_LOCKED"},
    ]
    assert normalize(item)["lock_state"] == "locked"


def test_vehicle_activity_is_not_guessed_parked():
    item = sample()
    assert normalize(item)["vehicle_activity"] == "engine off (parking unknown)"
    item["metrics"]["gearLeverPosition"] = {"value": "PARK"}
    assert normalize(item)["vehicle_activity"] == "parked"
    item["metrics"]["ignitionStatus"] = {"value": "RUNNING"}
    assert normalize(item)["vehicle_activity"] == "running"
    item["metrics"]["speed"] = {"value": 45.0}
    assert normalize(item)["vehicle_activity"] == "moving"
