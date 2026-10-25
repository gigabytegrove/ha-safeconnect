"""Ford-specific OAuth app registration and short-state callback compatibility.

Ford currently limits the OAuth state length. HA's standard signed state exceeds
that limit. Map a single-use random 64-bit nonce onto HA's pending flow ID.
Only nonce values generated in this integration are accepted; all other state
values use Home Assistant's original, signature-verifying decoder.
"""
from __future__ import annotations
import secrets
import time
from yarl import URL
from aiohttp import ClientError
from homeassistant.components.application_credentials import (
    AuthorizationServer, AuthImplementation, ClientCredential,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_entry_oauth2_flow import LocalOAuth2Implementation
import homeassistant.helpers.config_entry_oauth2_flow as oauth2_flow
from .const import DOMAIN, FORD_AUTHORIZE_URL, FORD_TOKEN_URL

NONCE_TTL = 600
_NONCE_KEY = "_safeconnect_oauth_nonces"

# Targeted compatibility hook, because Ford's accepted state size differs from
# HA's JWT state. It does not disable JWT verification for any other state.
if not getattr(oauth2_flow._decode_jwt, "_safeconnect_wrapper", False):
    _original_decoder = oauth2_flow._decode_jwt

    def _decode_ford_state(hass: HomeAssistant, state: str):
        pending = hass.data.get(_NONCE_KEY, {})
        now = time.monotonic()
        # Discard expired attempts; consume any matched nonce only once.
        for key, (_, created) in list(pending.items()):
            if now - created > NONCE_TTL:
                pending.pop(key, None)
        entry = pending.pop(state, None)
        if entry is not None:
            flow_id, _created = entry
            return {"flow_id": flow_id}
        return _original_decoder(hass, state)

    _decode_ford_state._safeconnect_wrapper = True
    oauth2_flow._decode_jwt = _decode_ford_state


class FordOAuth(LocalOAuth2Implementation):
    async def async_generate_authorize_url(self, flow_id: str) -> str:
        state = secrets.token_hex(8)  # Ford currently requires <= 16 chars.
        self.hass.data.setdefault(_NONCE_KEY, {})[state] = (flow_id, time.monotonic())
        return str(URL(self.authorize_url).with_query({
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
        }))

    async def async_resolve_external_data(self, external_data: dict) -> dict:
        code = external_data.get("code")
        if not isinstance(code, str) or not code:
            return {}
        try:
            return await self._token_request({
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
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
