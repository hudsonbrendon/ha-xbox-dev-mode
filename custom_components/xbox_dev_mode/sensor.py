"""Sensor platform for Xbox Dev Mode integration."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import XboxData, XboxDevModeCoordinator
from .entity import XboxEntity


@dataclass
class XboxSensorDescription(SensorEntityDescription):
    """Description for Xbox sensor entities."""

    value_fn: Callable[[XboxData], Any] = field(default=lambda data: None)
    attr_fn: Callable[[XboxData], dict[str, Any] | None] | None = None
    dev_only: bool = True


SENSORS: list[XboxSensorDescription] = [
    XboxSensorDescription(
        key="console_state",
        translation_key="console_state",
        value_fn=lambda data: data.state,
        dev_only=False,
    ),
    XboxSensorDescription(
        key="foreground_app",
        translation_key="foreground_app",
        value_fn=lambda data: data.foreground.image_name if data.foreground else None,
        dev_only=True,
    ),
    XboxSensorDescription(
        key="cpu_load",
        translation_key="cpu_load",
        value_fn=lambda data: data.perf.cpu_load if data.perf else None,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        dev_only=True,
    ),
    XboxSensorDescription(
        key="memory_used",
        translation_key="memory_used",
        value_fn=lambda data: data.perf.memory_used_mb if data.perf else None,
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DATA_SIZE,
        dev_only=True,
    ),
    XboxSensorDescription(
        key="memory_available",
        translation_key="memory_available",
        value_fn=lambda data: data.perf.memory_available_mb if data.perf else None,
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DATA_SIZE,
        dev_only=True,
    ),
    XboxSensorDescription(
        key="gpu_memory_used",
        translation_key="gpu_memory_used",
        value_fn=lambda data: data.perf.gpu_memory_used_mb if data.perf else None,
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DATA_SIZE,
        dev_only=True,
    ),
    XboxSensorDescription(
        key="sideloaded_apps",
        translation_key="sideloaded_apps",
        value_fn=lambda data: len(data.sideloaded),
        state_class=SensorStateClass.MEASUREMENT,
        dev_only=True,
    ),
    XboxSensorDescription(
        key="sandbox",
        translation_key="sandbox",
        value_fn=lambda data: data.sandbox,
        dev_only=False,
    ),
    XboxSensorDescription(
        key="os_version",
        translation_key="os_version",
        value_fn=lambda data: data.info.os_version if data.info else None,
        dev_only=False,
    ),
    XboxSensorDescription(
        key="signed_in_user",
        translation_key="signed_in_user",
        value_fn=lambda data: next(
            (u.gamertag for u in data.users if u.signed_in),
            "Ninguem" if data.users is not None else None),
        attr_fn=lambda data: {
            "email": u.email_address, "xbox_user_id": u.xbox_user_id,
            "auto_sign_in": u.auto_sign_in,
        } if (u := next((x for x in data.users if x.signed_in), None)) else None,
        dev_only=True,
    ),
    XboxSensorDescription(
        key="controllers",
        translation_key="controllers",
        value_fn=lambda data: data.controller_count,
        state_class=SensorStateClass.MEASUREMENT,
        dev_only=True,
    ),
    XboxSensorDescription(
        key="console_model",
        translation_key="console_model",
        value_fn=lambda data: data.xbox_info.console_type if data.xbox_info else None,
        attr_fn=lambda data: {
            "serial_number": data.xbox_info.serial_number,
            "console_id": data.xbox_info.console_id,
            "os_edition": data.xbox_info.os_edition,
        } if data.xbox_info else None,
        dev_only=True,
    ),
    XboxSensorDescription(
        key="devkit_certificate_expiration",
        translation_key="devkit_certificate_expiration",
        value_fn=lambda data: (
            datetime.fromtimestamp(data.xbox_info.devkit_certificate_expiration, tz=timezone.utc)
            if data.xbox_info and data.xbox_info.devkit_certificate_expiration else None),
        device_class=SensorDeviceClass.TIMESTAMP,
        dev_only=True,
    ),
]


class XboxSensor(XboxEntity, SensorEntity):
    """Representation of an Xbox sensor."""

    entity_description: XboxSensorDescription

    def __init__(
        self,
        coordinator: XboxDevModeCoordinator,
        entry_id: str,
        entry_unique_id: str,
        description: XboxSensorDescription,
    ):
        """Initialize Xbox sensor.

        Args:
            coordinator: The coordinator for this entity.
            entry_id: The config entry ID.
            entry_unique_id: The config entry's unique ID.
            description: The sensor description.
        """
        super().__init__(coordinator, entry_id, entry_unique_id)
        self.entity_description = description
        self._dev_only = description.dev_only
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the state value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Attributes opcionais da descricao (email, serial, etc.)."""
        if self.entity_description.attr_fn is None:
            return None
        return self.entity_description.attr_fn(self.coordinator.data)


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities for Xbox Dev Mode."""
    coordinator = entry.runtime_data

    entities = [
        XboxSensor(coordinator, entry.entry_id, entry.unique_id, description)
        for description in SENSORS
    ]

    async_add_entities(entities)
