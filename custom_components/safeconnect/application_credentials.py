"""Ford-specific OAuth app registration and short-state callback compatibility.

Ford currently limits the OAuth state length. HA's standard signed state exceeds
that limit. Map a single-use random 64-bit nonce onto HA's pending flow ID.
Only nonce values generated in this integration are accepted; all other state
values use Home Assistant's original, signature-verifying decoder.
"""
from __future__ import annotations
from yarl import URL
from aiohttp import ClientError
from homeassistant.components.application_credentials import (
    AuthorizationServer, AuthImplementation, ClientCredential,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_entry_oauth2_flow import LocalOAuth2Implementation
import homeassistant.helpers.config_entry_oauth2_flow as oauth2_flow
from .const import DOMAIN, FORD_AUTHORIZE_URL, FORD_TOKEN_URL
from .oauth_state import create_ford_state, consume_ford_state

# Home Assistant 2026.11.1 exposes no per-integration callback-state decoder.
# Retain the smallest possible scoped compatibility wrapper until Ford accepts
# normal signed JWT state. All other OAuth states use HA's original verification.
if not getattr(oauth2_flow._decode_jwt, "_safeconnect_wrapper", False):
    _original_decoder = oauth2_flow._decode_jwt

    def _decode_ford_state(hass: HomeAssistant, state: str):
        ford_state = consume_ford_state(hass, state)
        return ford_state if ford_state is not None else _original_decoder(hass, state)

    _decode_ford_state._safeconnect_wrapper = True
    oauth2_flow._decode_jwt = _decode_ford_state


class FordOAuth(LocalOAuth2Implementation):
    async def async_generate_authorize_url(self, flow_id: str) -> str:
        state = create_ford_state(self.hass, flow_id, self.redirect_uri)
        return str(URL(self.authorize_url).with_query({
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
        }))

    async def async_resolve_external_data(self, external_data: dict) -> dict:
        code = external_data.get("code")
        state = external_data.get("state")
        if not isinstance(code, str) or not code or not isinstance(state, dict):
            return {}
        # The authorization code is bound to the redirect URI used when
        # authorization began, not the HA URL configured at callback time.
        redirect_uri = state.get("redirect_uri")
        if not isinstance(redirect_uri, str) or not redirect_uri:
            return {}
        try:
            return await self._token_request({
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            })
        except ClientError:
            return {}


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    return AuthorizationServer(authorize_url=FORD_AUTHORIZE_URL, token_url=FORD_TOKEN_URL)


async def async_get_auth_implementation(
    hass: HomeAssistant, auth_domain: str, credential: ClientCredential,
) -> AuthImplementation:
    server = await async_get_authorization_server(hass)
    return FordOAuth(
        hass, auth_domain, credential.client_id, credential.client_secret,
        server.authorize_url, server.token_url,
    )
