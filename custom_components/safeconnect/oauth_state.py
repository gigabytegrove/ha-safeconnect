"""Bounded, one-use Ford OAuth state for vendor's 16-character limit.

No Home Assistant monkeypatch lives in this module; pure functions are directly
testable without Home Assistant dependencies. Never log or export nonce maps.
"""
from __future__ import annotations

import re
import secrets
import time
from typing import Any

STATE_KEY = "_safeconnect_oauth_nonces"
NONCE_TTL_SECONDS = 600
MAX_PENDING_NONCES = 32
_NONCE_RE = re.compile(r"[a-f0-9]{16}\Z")


def _prune(pending: dict[str, tuple[str, str, float]], now: float) -> None:
    for nonce, (_, _, created) in list(pending.items()):
        if created > now or now - created >= NONCE_TTL_SECONDS:
            pending.pop(nonce, None)


def create_ford_state(hass: Any, flow_id: str, redirect_uri: str, *, now: float | None = None) -> str:
    """Issue a short state tied to one flow and exact redirect URI."""
    current = time.monotonic() if now is None else now
    pending: dict[str, tuple[str, str, float]] = hass.data.setdefault(STATE_KEY, {})
    _prune(pending, current)
    if len(pending) >= MAX_PENDING_NONCES:
        raise RuntimeError("Too many pending Ford authorizations")
    if not flow_id or not redirect_uri:
        raise ValueError("OAuth flow and callback URL are required")
    for _ in range(8):
        nonce = secrets.token_hex(8)
        if nonce not in pending:
            pending[nonce] = (flow_id, redirect_uri, current)
            return nonce
    raise RuntimeError("Cannot allocate a unique Ford authorization state")


def consume_ford_state(hass: Any, state: str, *, now: float | None = None) -> dict[str, str] | None:
    """Accept only a live one-use nonce originally created for Ford."""
    if not isinstance(state, str) or _NONCE_RE.fullmatch(state) is None:
        return None
    pending = hass.data.get(STATE_KEY)
    if not isinstance(pending, dict):
        return None
    current = time.monotonic() if now is None else now
    _prune(pending, current)
    stored = pending.pop(state, None)
    if stored is None:
        return None
    flow_id, redirect_uri, _created = stored
    return {"flow_id": flow_id, "redirect_uri": redirect_uri}
