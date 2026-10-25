"""Shared SafeConnect device and caching behavior."""
from __future__ import annotations
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .coordinator import SafeConnectCoordinator
from .const import CONF_VIN, CONF_VEHICLE_NAME
from .freshness import SECURITY_KEYS, security_sample_time, security_state_is_fresh


class SafeConnectEntity(CoordinatorEntity[SafeConnectCoordinator]):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: SafeConnectCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{coordinator.entry.data[CONF_VIN]}_{key}"

    @property
    def device_info(self):
        return {
            "identifiers": {("safeconnect", self.coordinator.entry.data[CONF_VIN])},
            "name": self.coordinator.entry.data.get(CONF_VEHICLE_NAME, "Ford Vehicle"),
            "manufacturer": "Ford",
        }

    @property
    def available(self) -> bool:
        data = self.coordinator.data or {}
        if self._key in SECURITY_KEYS:
            # For doors and locks, expose unavailable instead of hours-old
            # open/closed/locked values as a supposedly current state.
            return security_state_is_fresh(data, self._key)
        return data.get(self._key) is not None

    @property
    def extra_state_attributes(self):
        values = self.coordinator.data or {}
        attrs = {
            "ford_cloud_received_at": self.coordinator.cloud_fetch_time,
            "vehicle_reported_at": values.get("vehicle_update_time"),
            "cached": True,
        }
        if self._key in SECURITY_KEYS:
            attrs["security_sample_time"] = security_sample_time(values, self._key)
            attrs["security_state_fresh"] = security_state_is_fresh(values, self._key)
        return attrs
