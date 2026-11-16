"""No cloud or HA required: Ford OAuth state replay and exhaustion checks."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "custom_components/safeconnect/oauth_state.py"
spec = importlib.util.spec_from_file_location("safeconnect_oauth_state_test", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def test_binds_exact_flow_and_redirect_and_is_single_use():
    hass = SimpleNamespace(data={})
    with patch.object(module.secrets, "token_hex", return_value="0123456789abcdef"):
        state = module.create_ford_state(hass, "ford-flow", "https://ha.example/auth/external/callback", now=100)
    assert state == "0123456789abcdef"
    assert module.consume_ford_state(hass, state, now=101) == {
        "flow_id": "ford-flow", "redirect_uri": "https://ha.example/auth/external/callback",
    }
    assert module.consume_ford_state(hass, state, now=102) is None

def test_expiry_and_malformed_states_fail_closed():
    hass = SimpleNamespace(data={})
    with patch.object(module.secrets, "token_hex", return_value="aaaaaaaaaaaaaaaa"):
        state = module.create_ford_state(hass, "ford-flow", "https://ha.example/callback", now=100)
    assert module.consume_ford_state(hass, "aaaaaaaaaaaaaaa!", now=101) is None
    assert module.consume_ford_state(hass, state, now=700) is None

def test_bounded_pending_flow_count():
    hass = SimpleNamespace(data={})
    with patch.object(module.secrets, "token_hex", side_effect=[f"{i:016x}" for i in range(32)]):
        for _ in range(32):
            module.create_ford_state(hass, "f", "https://ha.example/callback", now=100)
    try:
        module.create_ford_state(hass, "f", "https://ha.example/callback", now=100)
    except RuntimeError as err:
        assert "Too many" in str(err)
    else:
        raise AssertionError("Unbounded Ford OAuth states")
