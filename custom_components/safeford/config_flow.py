"""User-driven FordConnect OAuth flow and conservative polling options."""
from __future__ import annotations
import logging
import time
from typing import Any
import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import (
    DOMAIN, GARAGE_URL, CONF_VIN, CONF_VEHICLE_NAME,
    CONF_POLL_MINUTES, DEFAULT_POLL_MINUTES, MIN_POLL_MINUTES, MAX_POLL_MINUTES,
)

_LOGGER = logging.getLogger(__name__)


class SafeFordConfigFlow(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Authenticate through an owner-registered Ford Developer OAuth app."""

    # AbstractOAuth2FlowHandler.__init__ requires this class attribute.
    # Class registration via domain=DOMAIN does not populate it.
    DOMAIN = DOMAIN
    VERSION = 1

    @property
    def logger(self) -> logging.Logger:
        return _LOGGER

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await super().async_step_user(user_input)

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> ConfigFlowResult:
        token = data.get("token", {}).get("access_token")
        if not isinstance(token, str) or not token:
            return self.async_abort(reason="authorization_failed")
        try:
            client = async_get_clientsession(self.hass)
            async with client.get(
                GARAGE_URL,
                headers={"Authorization": f"Bearer {token}"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    return self.async_abort(reason="authorization_failed")
                garage = await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError):
            return self.async_abort(reason="cannot_connect")
        # Ford's consent flow usually grants one selected vehicle. Accept only
        # an unambiguous VIN, never silently choose a random garage entry.
        if not isinstance(garage, dict):
            return self.async_abort(reason="no_vehicle")
        vehicles = garage.get("vehicles")
        if isinstance(vehicles, list):
            if len(vehicles) != 1 or not isinstance(vehicles[0], dict):
                return self.async_abort(reason="select_one_vehicle")
            garage = vehicles[0]
        vin = garage.get("vin")
        if not isinstance(vin, str) or len(vin) != 17 or not vin.isalnum():
            return self.async_abort(reason="no_vehicle")
        vin = vin.upper()
        vehicle_name = str(garage.get("vehicleType") or garage.get("modelName") or "Ford Vehicle")[:80]
        await self.async_set_unique_id(vin)
        if self.source == config_entries.SOURCE_REAUTH:
            self._abort_if_unique_id_mismatch()
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(), data_updates={**data, CONF_VIN: vin, CONF_VEHICLE_NAME: vehicle_name, "authorization_epoch": int(time.time())},
            )
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=vehicle_name,
            data={**data, CONF_VIN: vin, CONF_VEHICLE_NAME: vehicle_name, "authorization_epoch": int(time.time())},
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return await super().async_step_pick_implementation(None)
        return self.async_show_form(step_id="reauth_confirm")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> OptionsFlow:
        return SafeFordOptionsFlow()


class SafeFordOptionsFlow(OptionsFlow):
    """Only allow low-frequency cloud reads."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        schema = vol.Schema({
            vol.Required(
                CONF_POLL_MINUTES,
                default=self.config_entry.options.get(CONF_POLL_MINUTES, DEFAULT_POLL_MINUTES),
            ): vol.All(vol.Coerce(int), vol.Range(min=MIN_POLL_MINUTES, max=MAX_POLL_MINUTES)),
        })
        return self.async_show_form(step_id="init", data_schema=schema)
