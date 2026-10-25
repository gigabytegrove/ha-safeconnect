"""No extra cloud request to publish first-fetch or cached values after entity setup."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "custom_components/safeconnect/__init__.py").read_text()

def test_values_republished_after_entities_subscribe():
    forward = SOURCE.index("await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)")
    cache_broadcast = SOURCE.index("coordinator.async_set_updated_data(dict(coordinator.data))")
    assert forward < cache_broadcast
    guarded_block = SOURCE[forward:cache_broadcast]
    assert "if isinstance(coordinator.data, dict) and coordinator.data:" in guarded_block
    assert "async_config_entry_first_refresh" not in guarded_block
    assert "async_request_refresh" not in guarded_block
    assert "telemetry()" not in guarded_block
