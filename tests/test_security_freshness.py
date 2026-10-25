"""Offline validation of security sample age. No HA or cloud requests."""
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

source = Path(__file__).resolve().parents[1] / "custom_components/safeconnect/freshness.py"
spec = importlib.util.spec_from_file_location("safeconnect_freshness_test", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
check = module.security_state_is_fresh

def test_stale_open_unavailable_even_if_cloud_just_polled():
    now = datetime(2026, 10, 25, 22, 0, tzinfo=timezone.utc)
    values = {
        "door_front_left_open": True,
        "vehicle_update_time": "2026-10-25T13:37:20Z",
    }
    assert not check(values, "door_front_left_open", now=now)

def test_recent_closed_and_recent_open_both_reported_as_is():
    now = datetime(2026, 10, 25, 22, 0, tzinfo=timezone.utc)
    values = {
        "door_front_left_open": False,
        "door_front_left_open_sample_time": "2026-10-25T21:50:00Z",
        "vehicle_update_time": "2026-10-25T15:00:00Z",
    }
    assert check(values, "door_front_left_open", now=now)
    values["door_front_left_open"] = True
    assert check(values, "door_front_left_open", now=now)

def test_lock_not_inferred_from_door_status():
    now = datetime(2026, 10, 25, 22, 0, tzinfo=timezone.utc)
    values = {
        "door_front_left_open": False,
        "lock_state": "unlocked",
        "lock_state_sample_time": "2026-10-25T19:00:00Z",
        "vehicle_update_time": "2026-10-25T21:59:00Z",
    }
    assert not check(values, "lock_state", now=now)
    assert check(values, "door_front_left_open", now=now)

def test_missing_and_future_times_fail_closed():
    now = datetime(2026, 10, 25, 22, 0, tzinfo=timezone.utc)
    values = {"hood_open": True}
    assert not check(values, "hood_open", now=now)
    values["hood_open_sample_time"] = "2026-10-25T23:30:00Z"
    assert not check(values, "hood_open", now=now)
    values["hood_open_sample_time"] = "not-a-date"
    assert not check(values, "hood_open", now=now)

def test_future_skew_and_exact_expiration():
    now = datetime(2026, 10, 25, 22, 0, tzinfo=timezone.utc)
    values = {"lock_state": "locked", "lock_state_sample_time": (now + timedelta(seconds=100)).isoformat()}
    assert check(values, "lock_state", now=now)
    values["lock_state_sample_time"] = (now - timedelta(seconds=3601)).isoformat()
    assert not check(values, "lock_state", now=now)
