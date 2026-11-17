"""Select platform for Xbox Dev Mode integration."""
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

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
    setting_name: str | None = None  # Xbox Device Portal setting name (None for app select)
    dev_only: bool = True


# Single source of truth for setting selects: (key, setting_name)
SETTING_SELECTS = [
    ("tv_resolution", "TVResolution"),
    ("power_mode", "PowerMode"),
    ("hdmi_audio", "HDMIAudio"),
    ("color_space", "ColorSpace"),
    ("headset_format", "HeadsetFormat"),
    ("default_app", "DefaultApp"),
]


def _make_value_fn(setting_name: str) -> Callable[[XboxData], Any]:
    """Generate value_fn for a setting select."""
    return lambda data: data.settings.get(setting_name).value if data.settings.get(setting_name) else None


def _make_options_fn(setting_name: str) -> Callable[[XboxData], list[str]]:
    """Generate options_fn for a setting select."""
    return lambda data: list(data.settings.get(setting_name).options) if data.settings.get(setting_name) else []


SELECTS: list[XboxSelectDescription] = [
    XboxSelectDescription(
        key="app",
        translation_key="app",
        value_fn=lambda data: None,  # Set dynamically from coordinator.selected_app
        options_fn=lambda data: [pkg.name for pkg in data.sideloaded] if data.sideloaded else [],
        setting_name=None,
        dev_only=True,
    ),
] + [
    XboxSelectDescription(
        key=key,
        translation_key=key,
        value_fn=_make_value_fn(setting_name),
        options_fn=_make_options_fn(setting_name),
        setting_name=setting_name,
        dev_only=True,
    )
    for key, setting_name in SETTING_SELECTS
]


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

        # For settings, only available if the setting has been fetched (present in settings dict)
        setting_name = self.entity_description.setting_name
        if setting_name is None:
            return False

        if self.coordinator.data.settings.get(setting_name) is None:  # noqa: SIM103
            return False

        return True

    async def async_select_option(self, option: str) -> None:
        """Handle select option."""
        if self.entity_description.key == "app":
            # Set selected app on coordinator
            self.coordinator.selected_app = option
        else:
            # Call set_setting on client with the setting name from description
            setting_name = self.entity_description.setting_name
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
