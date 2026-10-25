"""Last-known vehicle position. Never implies real-time GPS."""
from __future__ import annotations
from homeassistant.components.device_tracker import TrackerEntity, SourceType
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .entity import SafeFordEntity
from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SafeFordTracker(coordinator)])


class SafeFordTracker(SafeFordEntity, TrackerEntity):
    _attr_name = "Last known vehicle location"
    _attr_icon = "mdi:car-wireless"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "latitude")

    @property
    def available(self):
        data = self.coordinator.data or {}
        return isinstance(data.get("latitude"), (int, float)) and isinstance(data.get("longitude"), (int, float))

    @property
    def latitude(self):
        return (self.coordinator.data or {}).get("latitude")

    @property
    def longitude(self):
        return (self.coordinator.data or {}).get("longitude")

    @property
    def source_type(self):
        return SourceType.GPS

    @property
    def extra_state_attributes(self):
        return {
            "last_gps_reported_at": (self.coordinator.data or {}).get("location_sample_time"),
            "ford_cloud_received_at": self.coordinator.cloud_fetch_time,
            "is_live_tracking": False,
        }
