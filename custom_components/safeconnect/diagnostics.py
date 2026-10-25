"""Diagnostics never includes GPS coordinates, VIN, auth tokens, or payloads."""
from __future__ import annotations
import time
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN
from .freshness import SECURITY_KEYS, security_sample_time, security_state_is_fresh


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    values = coordinator.data or {}
    return {
        "version": "0.2.0a3",
        "poll_minutes": coordinator.poll_minutes,
        "cloud_fetch_time": coordinator.cloud_fetch_time,
        "next_allowed_epoch": coordinator.budget.next_allowed,
        "cloud_query_permitted_now": coordinator.budget.allowed(time.time()),
        "local_budget_check_minutes": 1,
        "suspended": coordinator.budget.suspended,
        "requests": coordinator.request_count,
        "throttled": coordinator.rate_limited_count,
        "errors": coordinator.error_count,
        "last_http_error": coordinator.last_http_error,
        "security_states": {
            key: {
                "last_vehicle_sample": security_sample_time(values, key),
                "fresh": security_state_is_fresh(values, key),
                # Actual OPEN/LOCKED states are deliberately not included in
                # exported diagnostics; the safe API schema summary below
                # is enough to inspect timestamp/field structure.
            }
            for key in sorted(SECURITY_KEYS)
        },
        "telemetry_schema": coordinator.telemetry_audit,
        "available_metric_names": sorted(values.keys()),
        "remote_engine_controls": False,
        "remote_lock_controls": False,
    }
