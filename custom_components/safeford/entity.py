"""Shared SafeFord device and caching behavior."""
from __future__ import annotations
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .coordinator import SafeFordCoordinator
from .const import CONF_VIN, CONF_VEHICLE_NAME


class SafeFordEntity(CoordinatorEntity[SafeFordCoordinator]):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: SafeFordCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{coordinator.entry.data[CONF_VIN]}_{key}"

    @property
    def device_info(self):
        return {
            "identifiers": {("safeford", self.coordinator.entry.data[CONF_VIN])},
            "name": self.coordinator.entry.data.get(CONF_VEHICLE_NAME, "Ford Vehicle"),
            "manufacturer": "Ford",
        }

    @property
    def available(self) -> bool:
        # Restore stale known values rather than claiming they're current.
        return (self.coordinator.data or {}).get(self._key) is not None

    @property
    def extra_state_attributes(self):
        return {
            "ford_cloud_received_at": self.coordinator.cloud_fetch_time,
            "vehicle_reported_at": (self.coordinator.data or {}).get("vehicle_update_time"),
            "cached": True,
        }
