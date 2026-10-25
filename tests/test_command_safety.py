"""Guard against adding remote engine operations in this read-only milestone."""
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "custom_components" / "safeconnect"


def test_no_command_endpoints_or_wake_methods():
    code = (BASE / "api.py").read_text(encoding="utf-8")
    assert 'async_request("GET", TELEMETRY_URL)' in code
    assert 'async_request("POST"' not in code
    assert "remoteStart" not in code
    assert "wakeVehicle" not in code
    assert "/commands" not in code


def test_no_automation_accessible_vehicle_controls():
    init = (BASE / "__init__.py").read_text(encoding="utf-8")
    for forbidden in ("Platform.LOCK", "Platform.BUTTON", "Platform.SWITCH", "async_register("):
        assert forbidden not in init
