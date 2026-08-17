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
    setting_name: str | None = None
    dev_only: bool = True


# Single source of truth for switch settings: (key, setting_name)
SETTING_SWITCHES = [
    ("allow_hdr", "AllowHDR"),
    ("allow_4k", "Allow4K"),
    ("allow_vrr", "AllowVRR"),
    ("allow_allm", "AllowALLM"),
]


def _make_value_fn(setting_name: str) -> Callable[[XboxData], bool]:
    """Generate value_fn for a switch.

    The devportal library stringifies whatever the console returns
    (``str(value)``), so a JSON ``true`` boolean arrives as ``"True"``, not
    ``"true"``. Compare case-insensitively so the switch isn't stuck off.
    """
    def value_fn(data: XboxData) -> bool:
        setting = data.settings.get(setting_name)
        return setting is not None and setting.value.strip().lower() == "true"

    return value_fn


SWITCHES: list[XboxSwitchDescription] = [
    XboxSwitchDescription(
        key=key,
        translation_key=key,
        value_fn=_make_value_fn(setting_name),
        setting_name=setting_name,
        dev_only=True,
    )
    for key, setting_name in SETTING_SWITCHES
]


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
        3. The setting has been fetched (present in settings dict)
        """
        base_available = super().available
        if not base_available:
            return False

        # Check if the setting has been fetched
        setting_name = self.entity_description.setting_name
        if setting_name is None:
            return False

        if self.coordinator.data.settings.get(setting_name) is None:
            return False

        return True

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the switch."""
        setting_name = self.entity_description.setting_name
        if setting_name:
            await self.coordinator.client.set_setting(setting_name, "true")
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the switch."""
        setting_name = self.entity_description.setting_name
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
