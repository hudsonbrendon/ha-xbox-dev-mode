"""Sensor platform for Xbox Dev Mode integration."""
from dataclasses import dataclass, field
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
        value_fn=lambda data: data.foreground.image_name if data.foreground else "Nenhum",
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
        value_fn=lambda data: (
            int((data.perf.committed_pages - data.perf.available_pages) * data.perf.page_size / (1024 * 1024))
            if data.perf
            else None
        ),
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DATA_SIZE,
        dev_only=True,
    ),
    XboxSensorDescription(
        key="memory_available",
        translation_key="memory_available",
        value_fn=lambda data: (
            int(data.perf.available_pages * data.perf.page_size / (1024 * 1024))
            if data.perf
            else None
        ),
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DATA_SIZE,
        dev_only=True,
    ),
    XboxSensorDescription(
        key="gpu_memory_used",
        translation_key="gpu_memory_used",
        value_fn=lambda data: (
            int(data.perf.gpu_dedicated_used / (1024 * 1024))
            if data.perf
            else None
        ),
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
