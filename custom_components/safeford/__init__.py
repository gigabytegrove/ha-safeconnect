"""SafeFord: intentionally read-only FordConnect Query HA integration."""
from __future__ import annotations
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_entry_oauth2_flow import (
    OAuth2Session, async_get_config_entry_implementation,
)
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.const import Platform
from .api import FordQuery
from .coordinator import SafeFordCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.DEVICE_TRACKER]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    try:
        implementation = await async_get_config_entry_implementation(hass, entry)
    except ValueError as exc:
        raise ConfigEntryNotReady("SafeFord OAuth application credentials are unavailable") from exc
    session = OAuth2Session(hass, entry, implementation)
    coordinator = SafeFordCoordinator(hass, entry, FordQuery(session))
    cached = await coordinator.load_cache()
    if not cached:
        # First run only. If Ford is unavailable, HA can retry while our
        # persisted request budget prevents rapid repeated HTTP traffic.
        await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_update_listener))
    return True


async def _update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator is not None:
        current_access_token = entry.data.get("token", {}).get("access_token")
        same_options = coordinator.last_options == dict(entry.options)
        same_authorization = coordinator.authorization_epoch == int(entry.data.get("authorization_epoch", 0))
        if same_options and same_authorization and coordinator.last_access_token != current_access_token:
            # A regular OAuth token refresh should NEVER restart the entire
            # integration or trigger duplicate cloud requests.
            coordinator.last_access_token = current_access_token
            return
    # Explicit option changes and fresh user authorization reload safely;
    # the persisted request reservation prevents duplicate Ford requests.
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok
