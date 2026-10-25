"""Ford vehicle telemetry sensors. Read-only by construction."""
from __future__ import annotations
from dataclasses import dataclass
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .entity import SafeConnectEntity
from .const import DOMAIN


@dataclass(frozen=True)
class SensorSpec:
    key: str
    name: str
    unit: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    icon: str | None = None


SPECS: tuple[SensorSpec, ...] = (
    SensorSpec("fuel_percent", "Fuel level", "%", None, SensorStateClass.MEASUREMENT, "mdi:gas-station"),
    SensorSpec("fuel_range_mi", "Fuel range", "mi", SensorDeviceClass.DISTANCE, SensorStateClass.MEASUREMENT),
    SensorSpec("odometer_mi", "Odometer", "mi", SensorDeviceClass.DISTANCE, SensorStateClass.TOTAL_INCREASING),
    SensorSpec("oil_life_percent", "Oil life", "%", None, SensorStateClass.MEASUREMENT, "mdi:oil"),
    SensorSpec("battery_12v_percent", "12V battery", "%", SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT),
    SensorSpec("battery_12v_volts", "12V voltage", "V", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
    SensorSpec("tire_front_left_psi", "Front left tire", "psi", SensorDeviceClass.PRESSURE, SensorStateClass.MEASUREMENT),
    SensorSpec("tire_front_right_psi", "Front right tire", "psi", SensorDeviceClass.PRESSURE, SensorStateClass.MEASUREMENT),
    SensorSpec("tire_rear_left_psi", "Rear left tire", "psi", SensorDeviceClass.PRESSURE, SensorStateClass.MEASUREMENT),
    SensorSpec("tire_rear_right_psi", "Rear right tire", "psi", SensorDeviceClass.PRESSURE, SensorStateClass.MEASUREMENT),
    SensorSpec("outside_temp_c", "Outside temperature", "°C", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
    SensorSpec("cabin_temp_c", "Cabin temperature", "°C", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
    SensorSpec("coolant_temp_c", "Coolant temperature", "°C", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
    SensorSpec("engine_oil_temp_c", "Engine oil temperature", "°C", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
    SensorSpec("speed_kmh", "Vehicle speed", "km/h", SensorDeviceClass.SPEED, SensorStateClass.MEASUREMENT),
    SensorSpec("engine_rpm", "Engine RPM", "rpm", None, SensorStateClass.MEASUREMENT),
    SensorSpec("ignition", "Ignition status", icon="mdi:engine"),
    SensorSpec("vehicle_activity", "Vehicle activity", icon="mdi:car-info"),
    SensorSpec("gear", "Gear position", icon="mdi:car-shift-pattern"),
    SensorSpec("lock_state", "Door lock status", icon="mdi:car-door-lock"),
    SensorSpec("alarm", "Alarm status", icon="mdi:shield-car"),
    SensorSpec("deep_sleep", "Deep sleep", icon="mdi:sleep"),
    SensorSpec("tire_system_status", "Tire monitoring status", icon="mdi:car-tire-alert"),
    SensorSpec("vehicle_update_time", "Vehicle report time", device_class=SensorDeviceClass.TIMESTAMP),
    SensorSpec("location_sample_time", "GPS report time", device_class=SensorDeviceClass.TIMESTAMP),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SafeConnectSensor(coordinator, spec) for spec in SPECS])


class SafeConnectSensor(SafeConnectEntity, SensorEntity):
    def __init__(self, coordinator, spec: SensorSpec) -> None:
        super().__init__(coordinator, spec.key)
        self._attr_name = spec.name
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_device_class = spec.device_class
        self._attr_state_class = spec.state_class
        self._attr_icon = spec.icon

    @property
    def native_value(self):
        value = (self.coordinator.data or {}).get(self._key)
        if self._attr_device_class == SensorDeviceClass.TIMESTAMP and isinstance(value, str):
            from datetime import datetime
            return datetime.fromisoformat(value)
        return value
