"""Select platform for Xbox Dev Mode integration."""
from dataclasses import dataclass, field
from typing import Any, Callable

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import XboxData, XboxDevModeCoordinator
from .entity import XboxEntity


@dataclass
class XboxSelectDescription(SelectEntityDescription):
    """Description for Xbox select entities."""

    value_fn: Callable[[XboxData], Any] = field(default=lambda data: None)
    options_fn: Callable[[XboxData], list[str]] = field(default=lambda data: [])
    dev_only: bool = True


SELECTS: list[XboxSelectDescription] = [
    XboxSelectDescription(
        key="app",
        translation_key="app",
        value_fn=lambda data: None,  # Will be set dynamically from coordinator.selected_app
        options_fn=lambda data: [pkg.name for pkg in data.sideloaded] if data.sideloaded else [],
        dev_only=True,
    ),
    XboxSelectDescription(
        key="tv_resolution",
        translation_key="tv_resolution",
        value_fn=lambda data: data.settings.get("TVResolution").value if data.settings.get("TVResolution") else None,
        options_fn=lambda data: list(data.settings.get("TVResolution").options) if data.settings.get("TVResolution") else [],
        dev_only=True,
    ),
    XboxSelectDescription(
        key="power_mode",
        translation_key="power_mode",
        value_fn=lambda data: data.settings.get("PowerMode").value if data.settings.get("PowerMode") else None,
        options_fn=lambda data: list(data.settings.get("PowerMode").options) if data.settings.get("PowerMode") else [],
        dev_only=True,
    ),
    XboxSelectDescription(
        key="hdmi_audio",
        translation_key="hdmi_audio",
        value_fn=lambda data: data.settings.get("HDMIAudio").value if data.settings.get("HDMIAudio") else None,
        options_fn=lambda data: list(data.settings.get("HDMIAudio").options) if data.settings.get("HDMIAudio") else [],
        dev_only=True,
    ),
    XboxSelectDescription(
        key="color_space",
        translation_key="color_space",
        value_fn=lambda data: data.settings.get("ColorSpace").value if data.settings.get("ColorSpace") else None,
        options_fn=lambda data: list(data.settings.get("ColorSpace").options) if data.settings.get("ColorSpace") else [],
        dev_only=True,
    ),
    XboxSelectDescription(
        key="headset_format",
        translation_key="headset_format",
        value_fn=lambda data: data.settings.get("HeadsetFormat").value if data.settings.get("HeadsetFormat") else None,
        options_fn=lambda data: list(data.settings.get("HeadsetFormat").options) if data.settings.get("HeadsetFormat") else [],
        dev_only=True,
    ),
    XboxSelectDescription(
        key="default_app",
        translation_key="default_app",
        value_fn=lambda data: data.settings.get("DefaultApp").value if data.settings.get("DefaultApp") else None,
        options_fn=lambda data: list(data.settings.get("DefaultApp").options) if data.settings.get("DefaultApp") else [],
        dev_only=True,
    ),
]

# Map setting keys to their Xbox Device Portal names
SETTING_NAME_MAP = {
    "tv_resolution": "TVResolution",
    "power_mode": "PowerMode",
    "hdmi_audio": "HDMIAudio",
    "color_space": "ColorSpace",
    "headset_format": "HeadsetFormat",
    "default_app": "DefaultApp",
}


class XboxSelect(XboxEntity, SelectEntity):
    """Representation of an Xbox select entity."""

    entity_description: XboxSelectDescription

    def __init__(
        self,
        coordinator: XboxDevModeCoordinator,
        entry_id: str,
        entry_unique_id: str,
        description: XboxSelectDescription,
    ):
        """Initialize Xbox select.

        Args:
            coordinator: The coordinator for this entity.
            entry_id: The config entry ID.
            entry_unique_id: The config entry's unique ID.
            description: The select description.
        """
        super().__init__(coordinator, entry_id, entry_unique_id)
        self.entity_description = description
        self._dev_only = description.dev_only
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def current_option(self) -> str | None:
        """Return the current option."""
        if self.entity_description.key == "app":
            # For app select, use coordinator.selected_app
            return self.coordinator.selected_app
        # For settings, use the value_fn
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def options(self) -> list[str]:
        """Return list of options."""
        return self.entity_description.options_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Return if entity is available.

        For app select, just check base availability.
        For settings, also check that the setting has been fetched.
        """
        base_available = super().available
        if not base_available:
            return False

        # For app select, always available if dev_mode
        if self.entity_description.key == "app":
            return True

        # For settings, only available if the setting has been fetched (has options)
        if not self.options:
            return False

        return True

    async def async_select_option(self, option: str) -> None:
        """Handle select option."""
        if self.entity_description.key == "app":
            # Set selected app on coordinator
            self.coordinator.selected_app = option
        else:
            # Call set_setting on client with the mapped setting name
            setting_name = SETTING_NAME_MAP.get(self.entity_description.key)
            if setting_name:
                await self.coordinator.client.set_setting(setting_name, option)
                # Request refresh to get updated state
                await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities for Xbox Dev Mode."""
    coordinator = entry.runtime_data

    entities = [
        XboxSelect(coordinator, entry.entry_id, entry.unique_id, description)
        for description in SELECTS
    ]

    async_add_entities(entities)
