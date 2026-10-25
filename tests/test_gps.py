"""GPS freshness and cache protections; all positions are synthetic."""
import importlib.util
from datetime import datetime, timezone
from pathlib import Path

source = Path(__file__).resolve().parents[1] / "custom_components/safeconnect/gps.py"
spec = importlib.util.spec_from_file_location("safeconnect_gps_test", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_old_gps_is_stale_even_after_recent_cloud_get():
    now = datetime(2026, 10, 25, 23, 0, tzinfo=timezone.utc)
    data = {"latitude": 12.3, "longitude": -45.6,
            "location_sample_time": "2026-10-25T17:00:00Z"}
    assert module.gps_is_stale(data, now=now)
    assert module.gps_age_seconds(data, now=now) == 21600


def test_new_gps_is_fresh():
    now = datetime(2026, 10, 25, 23, 0, tzinfo=timezone.utc)
    data = {"latitude": 12.3, "longitude": -45.6,
            "location_sample_time": "2026-10-25T22:58:00Z"}
    assert not module.gps_is_stale(data, now=now)


def test_retains_newer_cache_if_cloud_returns_older_position():
    old = {"latitude": 12.4, "longitude": -45.7,
           "location_sample_time": "2026-10-25T22:58:00+00:00"}
    incoming = {"latitude": 12.3, "longitude": -45.6,
                "location_sample_time": "2026-10-25T17:00:00+00:00",
                "fuel_percent": 42}
    merged = {**old, **module.preserve_newer_gps(old, incoming)}
    assert merged["latitude"] == 12.4
    assert merged["longitude"] == -45.7
    assert merged["location_sample_time"] == old["location_sample_time"]
    assert merged["fuel_percent"] == 42


def test_dated_cache_cannot_be_replaced_by_undated_gps():
    old = {"latitude": 12.4, "longitude": -45.7,
           "location_sample_time": "2026-10-25T22:58:00+00:00"}
    incoming = {"latitude": 12.3, "longitude": -45.6}
    assert not module.preserve_newer_gps(old, incoming)


def test_invalid_or_future_timestamp_stale():
    now = datetime(2026, 10, 25, 23, 0, tzinfo=timezone.utc)
    for stamp in ("broken", "2026-10-25T23:30:00Z", None):
        assert module.gps_is_stale({"location_sample_time": stamp}, now=now)

def test_gps_timestamp_comparison_respects_timezone_offsets():
    previous = {"latitude": 12.4, "longitude": -45.7,
                "location_sample_time": "2026-10-25T17:00:00+00:00"}
    incoming = {"latitude": 12.3, "longitude": -45.6,
                "location_sample_time": "2026-10-25T12:30:00-04:00"}
    # UTC 16:30 is older than UTC 17:00, despite local wallclock string.
    assert not module.preserve_newer_gps(previous, incoming)
