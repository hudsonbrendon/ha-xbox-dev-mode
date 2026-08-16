"""Switch platform for Xbox Dev Mode integration."""
from dataclasses import dataclass, field
from typing import Any, Callable

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import XboxData, XboxDevModeCoordinator
from .entity import XboxEntity


@dataclass
class XboxSwitchDescription(SwitchEntityDescription):
    """Description for Xbox switch entities."""

    value_fn: Callable[[XboxData], bool] = field(default=lambda data: False)
    dev_only: bool = True


SWITCHES: list[XboxSwitchDescription] = [
    XboxSwitchDescription(
        key="allow_hdr",
        translation_key="allow_hdr",
        value_fn=lambda data: data.settings.get("AllowHDR").value == "true" if data.settings.get("AllowHDR") else False,
        dev_only=True,
    ),
    XboxSwitchDescription(
        key="allow_4k",
        translation_key="allow_4k",
        value_fn=lambda data: data.settings.get("Allow4K").value == "true" if data.settings.get("Allow4K") else False,
        dev_only=True,
    ),
    XboxSwitchDescription(
        key="allow_vrr",
        translation_key="allow_vrr",
        value_fn=lambda data: data.settings.get("AllowVRR").value == "true" if data.settings.get("AllowVRR") else False,
        dev_only=True,
    ),
    XboxSwitchDescription(
        key="allow_allm",
        translation_key="allow_allm",
        value_fn=lambda data: data.settings.get("AllowALLM").value == "true" if data.settings.get("AllowALLM") else False,
        dev_only=True,
    ),
]

# Map switch keys to their Xbox Device Portal names
SETTING_NAME_MAP = {
    "allow_hdr": "AllowHDR",
    "allow_4k": "Allow4K",
    "allow_vrr": "AllowVRR",
    "allow_allm": "AllowALLM",
}


class XboxSwitch(XboxEntity, SwitchEntity):
    """Representation of an Xbox switch entity."""

    entity_description: XboxSwitchDescription

    def __init__(
        self,
        coordinator: XboxDevModeCoordinator,
        entry_id: str,
        entry_unique_id: str,
        description: XboxSwitchDescription,
    ):
        """Initialize Xbox switch.

        Args:
            coordinator: The coordinator for this entity.
            entry_id: The config entry ID.
            entry_unique_id: The config entry's unique ID.
            description: The switch description.
        """
        super().__init__(coordinator, entry_id, entry_unique_id)
        self.entity_description = description
        self._dev_only = description.dev_only
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def is_on(self) -> bool:
        """Return True if the switch is on."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Switch is available if:
        1. Coordinator is available (base class check)
        2. If _dev_only=True, console must be in dev_mode
        3. The setting has been fetched (value is not None)
        """
        base_available = super().available
        if not base_available:
            return False

        # Check if the setting has been fetched
        setting_name = SETTING_NAME_MAP.get(self.entity_description.key)
        if setting_name:
            setting = self.coordinator.data.settings.get(setting_name)
            if setting is None:
                return False

        return True

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the switch."""
        setting_name = SETTING_NAME_MAP.get(self.entity_description.key)
        if setting_name:
            await self.coordinator.client.set_setting(setting_name, "true")
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the switch."""
        setting_name = SETTING_NAME_MAP.get(self.entity_description.key)
        if setting_name:
            await self.coordinator.client.set_setting(setting_name, "false")
            await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities for Xbox Dev Mode."""
    coordinator = entry.runtime_data

    entities = [
        XboxSwitch(coordinator, entry.entry_id, entry.unique_id, description)
        for description in SWITCHES
    ]

    async_add_entities(entities)
