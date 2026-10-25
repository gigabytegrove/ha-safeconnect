"""GPS display attributes and privacy tests; no real coordinate samples."""
from pathlib import Path
R = Path(__file__).resolve().parents[1] / "custom_components/safeconnect"

def test_latitude_longitude_are_visible_sensors():
    sensor = (R/"sensor.py").read_text()
    assert 'SensorSpec("latitude", "GPS latitude"' in sensor
    assert 'SensorSpec("longitude", "GPS longitude"' in sensor
    assert "SafeConnectGpsAgeSensor" in sensor
    assert "async_track_time_interval" in sensor

def test_tracker_exposes_last_known_coordinates_and_age():
    tracker = (R/"device_tracker.py").read_text()
    assert "SourceType.GPS" in tracker
    assert '"gps_sample_age_minutes"' in tracker
    assert '"gps_stale"' in tracker
    assert '"is_live_tracking": False' in tracker

def test_downloaded_diagnostics_do_not_expose_coordinates():
    diag = (R/"diagnostics.py").read_text()
    assert '"coordinates_available"' in diag
    assert '"sample_time"' in diag
    assert '"sample_age_minutes"' in diag
    assert '"latitude":' not in diag and '"longitude":' not in diag
