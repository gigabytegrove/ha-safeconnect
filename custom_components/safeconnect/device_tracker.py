"""Last-known vehicle position. Never implies real-time GPS."""
from __future__ import annotations
from datetime import timedelta
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.components.device_tracker import TrackerEntity, SourceType
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .entity import SafeConnectEntity
from .const import DOMAIN
from .gps import gps_age_seconds, gps_is_stale


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SafeConnectTracker(coordinator)])


class SafeConnectTracker(SafeConnectEntity, TrackerEntity):
    _attr_name = "Last known vehicle location"
    # This tracker shows the LAST Ford position, never guaranteed live.
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

    @callback
    def _local_age_tick(self, _now) -> None:
        # Recompute GPS age/staleness locally; no cloud requests are made.
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._local_age_tick, timedelta(minutes=1)
            )
        )

    @property
    def extra_state_attributes(self):
        values = self.coordinator.data or {}
        age = gps_age_seconds(values)
        return {
            "last_gps_reported_at": values.get("location_sample_time"),
            "gps_sample_age_minutes": round(age / 60, 1) if age is not None else None,
            "gps_stale": gps_is_stale(values),
            "ford_cloud_received_at": self.coordinator.cloud_fetch_time,
            "is_live_tracking": False,
        }
