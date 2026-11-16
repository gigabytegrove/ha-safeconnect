"""Ford OAuth code exchange preserves the originally authorized redirect URI."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiohttp import ClientError

from custom_components.safeconnect.application_credentials import FordOAuth


def _implementation() -> FordOAuth:
    return FordOAuth(
        SimpleNamespace(),
        "safeconnect",
        "test-client",
        "test-secret",
        "https://ford.example.test/oauth/authorize",
        "https://ford.example.test/oauth/token",
    )


def test_exchange_uses_authorization_state_redirect_not_current_ha_url():
    original_redirect = "https://ha-old.example.test/auth/external/callback"
    impl = _implementation()
    with (
        patch.object(
            FordOAuth,
            "redirect_uri",
            new_callable=lambda: property(lambda _self: "https://ha-new.example.test/auth/external/callback"),
        ),
        patch.object(FordOAuth, "_token_request", new_callable=AsyncMock) as token_request,
    ):
        token_request.return_value = {"access_token": "synthetic-token"}
        result = asyncio.run(
            impl.async_resolve_external_data(
                {
                    "code": "synthetic-code",
                    "state": {
                        "flow_id": "original-flow",
                        "redirect_uri": original_redirect,
                    },
                }
            )
        )
    assert result == {"access_token": "synthetic-token"}
    token_request.assert_awaited_once_with(
        {
            "code": "synthetic-code",
            "grant_type": "authorization_code",
            "redirect_uri": original_redirect,
        }
    )


def test_invalid_state_or_code_does_not_exchange_credentials():
    impl = _implementation()
    with patch.object(FordOAuth, "_token_request", new_callable=AsyncMock) as token_request:
        for value in (
            {"code": "synthetic-code"},
            {"code": "synthetic-code", "state": {}},
            {"code": "synthetic-code", "state": {"redirect_uri": 123}},
            {"code": "", "state": {"redirect_uri": "https://ha.example.test/callback"}},
            {"code": "synthetic-code", "state": "invalid"},
        ):
            assert asyncio.run(impl.async_resolve_external_data(value)) == {}
    token_request.assert_not_awaited()


def test_http_token_exchange_failure_does_not_expose_credentials():
    impl = _implementation()
    with patch.object(
        FordOAuth,
        "_token_request",
        new_callable=AsyncMock,
    ) as token_request:
        token_request.side_effect = ClientError("Synthetic remote failure")
        assert asyncio.run(
            impl.async_resolve_external_data({
                "code": "synthetic-code",
                "state": {"redirect_uri": "https://ha.example.test/callback"},
            })
        ) == {}
