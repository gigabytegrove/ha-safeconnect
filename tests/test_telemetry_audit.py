"""No privacy leaks from a synthetic Postman-style response."""
import importlib.util
import json
from pathlib import Path

source = Path(__file__).resolve().parents[1] / "custom_components/safeconnect/telemetry_audit.py"
spec = importlib.util.spec_from_file_location("safeconnect_telemetry_audit_test", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def test_allowlisted_audit_preserves_only_door_status_structure():
    sample = {
        "vin": "CONFIDENTIAL_VEHICLE",
        "access_token": "SUPER_SECRET_AUTH",
        "updateTime": "2026-10-25T17:10:00Z",
        "metrics": {
            "doorStatus": [
                {"vehicleDoor": "FRONT_LEFT", "value": "CLOSED",
                 "updateTime": "2026-10-25T17:00:00Z",
                 "oemCorrelationId": "PRIVATE_CORRELATION"},
            ],
            "doorLockStatus": [
                {"vehicleDoor": "ALL_DOORS", "value": "LOCKED",
                 "updateTime": "2026-10-25T17:01:00Z"},
            ],
            "position": {"value": {"location": {"lat": 31.1, "lon": -83.1}}},
            "secret_metric": {"value": "SHOULD_NOT_APPEAR"},
        },
    }
    summary = module.summarize_security_response(sample)
    text = json.dumps(summary)
    for value in ("CONFIDENTIAL_VEHICLE", "SUPER_SECRET_AUTH",
                  "PRIVATE_CORRELATION", "SHOULD_NOT_APPEAR", "31.1", "-83.1"):
        assert value not in text
    door = summary["security_records"]["doorStatus"]["records"][0]
    assert door == {
        "position": "FRONT_LEFT", "side": "NOT_REPORTED", "status": "CLOSED",
        "sample_time": "2026-10-25T17:00:00+00:00",
    }

def test_unknown_remote_values_are_not_logged():
    obj = {"metrics": {"doorStatus": [
        {"vehicleDoor": "SENSITIVE_LOCATION", "vehicleSide": "PRIVATE_ID",
         "value": "TOKEN_USER_DETAIL", "updateTime": "unsupported"}
    ]}}
    text = json.dumps(module.summarize_security_response(obj))
    assert "SENSITIVE_LOCATION" not in text
    assert "PRIVATE_ID" not in text
    assert "TOKEN_USER_DETAIL" not in text
    assert "OTHER_OR_UNRECOGNIZED" in text
