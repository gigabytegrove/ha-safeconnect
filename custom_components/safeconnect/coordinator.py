"""Cached FordConnect coordinator with durable request reservations."""
from __future__ import annotations
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import FordQuery, FordAccessDenied, FordThrottled, FordTransient
from .budget import RequestBudget
from .telemetry import normalize
from .telemetry_audit import summarize_security_response
from .freshness import SECURITY_KEYS
from .const import DOMAIN, CONF_POLL_MINUTES, DEFAULT_POLL_MINUTES

_LOGGER = logging.getLogger(__name__)


class SafeConnectCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """One coordinator per authorized vehicle. Never contacts vehicle directly."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: FordQuery) -> None:
        self.entry = entry
        self.api = api
        # Preserve explicit slower owner choices, but a new installation
        # defaults to a real Ford telemetry query every minute.
        requested_poll = int(entry.options.get(CONF_POLL_MINUTES, DEFAULT_POLL_MINUTES))
        self.poll_minutes = max(1, min(1440, requested_poll))
        self.budget = RequestBudget()
        self.cloud_fetch_time: str | None = None
        self.request_count = 0
        self.rate_limited_count = 0
        self.error_count = 0
        self.last_http_error: str | None = None
        self.telemetry_audit: dict[str, Any] = {}
        self.authorization_epoch = int(entry.data.get("authorization_epoch", 0))
        self.last_options = dict(entry.options)
        self.last_access_token = entry.data.get("token", {}).get("access_token")
        self.store: Store[dict[str, Any]] = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        super().__init__(
            hass, _LOGGER, name=f"{DOMAIN}:{entry.entry_id}",
            # This is a LOCAL check. Cloud pacing is enforced by the
            # persistent budget inside _async_update_data, not by this
            # timer. Cache replays/restarts reset the HA interval, so a
            # one-minute tick prevents a due query being delayed an hour.
            update_interval=timedelta(minutes=1),
            always_update=False,
        )

    async def load_cache(self) -> bool:
        saved = await self.store.async_load()
        if not isinstance(saved, dict):
            return False
        self.budget = RequestBudget(
            next_allowed=saved.get("next_allowed", 0),
            suspended=saved.get("suspended", False),
        )
        if int(saved.get("authorization_epoch", 0)) != self.authorization_epoch:
            # ONLY a fresh explicit Ford authorization may clear an access-denied circuit breaker.
            self.budget.suspended = False
        self.cloud_fetch_time = saved.get("cloud_fetch_time")
        self.request_count = int(saved.get("request_count", 0))
        self.rate_limited_count = int(saved.get("rate_limited_count", 0))
        self.error_count = int(saved.get("error_count", 0))
        self.last_http_error = saved.get("last_http_error")
        audit = saved.get("telemetry_audit")
        self.telemetry_audit = audit if isinstance(audit, dict) else {}
        values = saved.get("values")
        if isinstance(values, dict) and values:
            # Cache migration: assign old security readings the original
            # report timestamp once, so newer top-level reports cannot make
            # a retained old OPEN/UNLOCKED value appear current.
            for key in SECURITY_KEYS:
                stamp = key + "_sample_time"
                if key in values and stamp not in values:
                    values[stamp] = values.get("vehicle_update_time")
            # Restoring cache NEVER triggers a vehicle wake or status refresh.
            self.async_set_updated_data(values)
            return True
        return False

    def _state(self, values_override: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "authorization_epoch": self.authorization_epoch,
            "next_allowed": self.budget.next_allowed,
            "suspended": self.budget.suspended,
            "cloud_fetch_time": self.cloud_fetch_time,
            "request_count": self.request_count,
            "rate_limited_count": self.rate_limited_count,
            "error_count": self.error_count,
            "last_http_error": self.last_http_error,
            "telemetry_audit": self.telemetry_audit,
            "values": values_override if values_override is not None else (self.data if isinstance(self.data, dict) else {}),
        }

    async def _save_now(self, values_override: dict[str, Any] | None = None) -> None:
        await self.store.async_save(self._state(values_override))

    async def _async_update_data(self) -> dict[str, Any]:
        now = time.time()
        if not self.budget.allowed(now):
            if self.data is not None:
                return self.data
            raise UpdateFailed(
                "Cloud queries suspended or cooldown in progress; safe to retry later"
            )

        self.budget.mark_started(now, self.poll_minutes)
        self.request_count += 1
        # Persist request reservation BEFORE any network traffic.
        try:
            await self._save_now()
        except OSError as exc:
            raise UpdateFailed("Cannot persist request budget; request blocked") from exc

        try:
            raw = await self.api.telemetry()
            values = normalize(raw)
            # Retain only allowlisted nonidentifying diagnostic information.
            # No VIN, positions, bearer tokens or raw API payloads are saved.
            self.telemetry_audit = summarize_security_response(raw)
        except FordThrottled as exc:
            self.rate_limited_count += 1
            self.last_http_error = "429"
            self.budget.throttle(time.time(), exc.seconds)
            await self._save_now()
            if self.data is not None:
                return self.data
            raise UpdateFailed("Ford API rate-limited; next request delayed") from exc
        except FordAccessDenied as exc:
            self.error_count += 1
            self.last_http_error = "401/403"
            self.budget.forbid()
            await self._save_now()
            # Surface a reauthorization flow to the owner. Never silently
            # continue making API calls against a denied account.
            raise ConfigEntryAuthFailed("Ford authorization rejected; polling suspended") from exc
        except (FordTransient, ValueError) as exc:
            self.error_count += 1
            self.last_http_error = "temporary_error"
            self.budget.temporary_failure(time.time())
            await self._save_now()
            if self.data is not None:
                return self.data
            raise UpdateFailed("Ford telemetry not available") from exc

        self.cloud_fetch_time = datetime.now(timezone.utc).isoformat()
        self.last_http_error = None
        # Preserve old values if Ford omits a metric for this response;
        # never substitute a made-up "fresh" vehicle sample time.
        merged = {**(self.data or {}), **values}
        await self._save_now(merged)
        return merged
