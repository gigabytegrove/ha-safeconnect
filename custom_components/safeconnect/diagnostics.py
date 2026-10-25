"""Diagnostics never includes GPS coordinates, VIN, auth tokens, or payloads."""
from __future__ import annotations
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    values = coordinator.data or {}
    return {
        "version": "0.2.0a0",
        "poll_minutes": coordinator.poll_minutes,
        "cloud_fetch_time": coordinator.cloud_fetch_time,
        "next_allowed_epoch": coordinator.budget.next_allowed,
        "suspended": coordinator.budget.suspended,
        "requests": coordinator.request_count,
        "throttled": coordinator.rate_limited_count,
        "errors": coordinator.error_count,
        "last_http_error": coordinator.last_http_error,
        "available_metric_names": sorted(values.keys()),
        "remote_engine_controls": False,
        "remote_lock_controls": False,
    }
