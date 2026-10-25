"""Only authenticated read-only FordConnect Query HTTPS endpoints."""
from __future__ import annotations
from typing import Any
import aiohttp
from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session
from .budget import retry_after_seconds
from .const import TELEMETRY_URL


class FordAccessDenied(Exception):
    """Stop automatically after an account authorization error."""


class FordThrottled(Exception):
    def __init__(self, seconds: int) -> None:
        super().__init__("Ford requested request throttling")
        self.seconds = seconds


class FordTransient(Exception):
    """Temporary service error; don't retry immediately."""


class FordQuery:
    def __init__(self, oauth: OAuth2Session) -> None:
        self._oauth = oauth

    async def telemetry(self) -> dict[str, Any]:
        try:
            # HA refreshes expired access tokens through this OAuth2 session.
            response = await self._oauth.async_request("GET", TELEMETRY_URL)
            async with response:
                if response.status == 429:
                    raise FordThrottled(retry_after_seconds(response.headers.get("Retry-After")))
                if response.status in (401, 403):
                    raise FordAccessDenied("Ford authorization denied")
                if response.status >= 400:
                    raise FordTransient(f"Ford returned HTTP {response.status}")
                data = await response.json(content_type=None)
                if not isinstance(data, dict):
                    raise FordTransient("Ford did not return a JSON object")
                return data
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise FordTransient("Ford service unavailable") from exc
