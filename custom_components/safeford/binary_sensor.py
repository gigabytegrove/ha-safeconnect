"""Per-door binary state, only present when Ford provides definite status."""
from __future__ import annotations
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .entity import SafeFordEntity
from .const import DOMAIN

DOORS = {
    "door_front_left_open": "Front left door",
    "door_front_right_open": "Front right door",
    "door_rear_left_open": "Rear left door",
    "door_rear_right_open": "Rear right door",
    "tailgate_open": "Tailgate",
    "hood_open": "Hood",
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SafeFordDoor(coordinator, key, name) for key, name in DOORS.items()])


class SafeFordDoor(SafeFordEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.DOOR

    def __init__(self, coordinator, key: str, name: str) -> None:
        super().__init__(coordinator, key)
        self._attr_name = name

    @property
    def is_on(self) -> bool | None:
        val = (self.coordinator.data or {}).get(self._key)
        return val if isinstance(val, bool) else None
