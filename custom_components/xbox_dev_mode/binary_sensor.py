"""Binary sensor platform for Xbox Dev Mode integration."""
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import STATE_DEV
from .coordinator import XboxDevModeCoordinator
from .entity import XboxEntity


BINARY_SENSORS = [
    BinarySensorEntityDescription(
        key="dev_mode",
        translation_key="dev_mode",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
]


class XboxBinarySensor(XboxEntity, BinarySensorEntity):
    """Representation of an Xbox binary sensor."""

    entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        coordinator: XboxDevModeCoordinator,
        entry_id: str,
        description: BinarySensorEntityDescription,
    ):
        """Initialize Xbox binary sensor.

        Args:
            coordinator: The coordinator for this entity.
            entry_id: The config entry ID.
            description: The binary sensor description.
        """
        super().__init__(coordinator, entry_id)
        self.entity_description = description
        self._dev_only = False  # dev_mode sensor is always available
        self._attr_unique_id = f"{entry_id}_{description.key}"
        # Set display name - will be slugified to form entity_id
        # Using key ensures entity_id matches expected format: xbox_<key>
        self._attr_name = f"Xbox {description.key.replace('_', ' ').title()}"

    @property
    def is_on(self) -> bool:
        """Return True if console is in dev mode."""
        return self.coordinator.data.state == STATE_DEV


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities for Xbox Dev Mode."""
    coordinator = entry.runtime_data

    entities = [
        XboxBinarySensor(coordinator, entry.entry_id, description)
        for description in BINARY_SENSORS
    ]

    async_add_entities(entities)
