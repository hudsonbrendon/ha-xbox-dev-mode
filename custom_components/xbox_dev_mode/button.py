"""Button platform for Xbox Dev Mode integration."""
from dataclasses import dataclass, field
from typing import Any, Callable

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import XboxDevModeCoordinator
from .entity import XboxEntity


@dataclass
class XboxButtonDescription(ButtonEntityDescription):
    """Description for Xbox button entities."""

    press_fn: Callable[[XboxDevModeCoordinator], Any] = field(default=lambda coordinator: None)
    dev_only: bool = True


# Single source of truth for button descriptions
BUTTONS: list[XboxButtonDescription] = [
    XboxButtonDescription(
        key="launch_app",
        translation_key="launch_app",
        press_fn=lambda coordinator: coordinator.client.launch(
            _get_package_full_name(coordinator)
        ) if _get_package_full_name(coordinator) else None,
    ),
    XboxButtonDescription(
        key="terminate_foreground",
        translation_key="terminate_foreground",
        press_fn=lambda coordinator: coordinator.client.terminate(
            coordinator.data.foreground.package_full_name
        ) if coordinator.data.foreground else None,
    ),
    XboxButtonDescription(
        key="restart",
        translation_key="restart",
        press_fn=lambda coordinator: coordinator.client.restart(),
        device_class="restart",
        entity_category=EntityCategory.CONFIG,
    ),
    XboxButtonDescription(
        key="shutdown",
        translation_key="shutdown",
        press_fn=lambda coordinator: coordinator.client.shutdown(),
        device_class="restart",
        entity_category=EntityCategory.CONFIG,
    ),
]


def _get_package_full_name(coordinator: XboxDevModeCoordinator) -> str | None:
    """Get the package full name for the selected app.

    Args:
        coordinator: The coordinator instance.

    Returns:
        The package_full_name of the selected app, or None if not found.
    """
    if not coordinator.selected_app or not coordinator.data.sideloaded:
        return None
    for pkg in coordinator.data.sideloaded:
        if pkg.name == coordinator.selected_app:
            return pkg.package_full_name
    return None


class XboxButton(XboxEntity, ButtonEntity):
    """Representation of an Xbox button entity."""

    entity_description: XboxButtonDescription

    def __init__(
        self,
        coordinator: XboxDevModeCoordinator,
        entry_id: str,
        entry_unique_id: str,
        description: XboxButtonDescription,
    ):
        """Initialize Xbox button.

        Args:
            coordinator: The coordinator for this entity.
            entry_id: The config entry ID.
            entry_unique_id: The config entry's unique ID.
            description: The button description.
        """
        super().__init__(coordinator, entry_id, entry_unique_id)
        self.entity_description = description
        self._dev_only = description.dev_only
        self._attr_unique_id = f"{entry_id}_{description.key}"

    async def async_press(self) -> None:
        """Handle button press."""
        result = self.entity_description.press_fn(self.coordinator)
        # Handle both sync and async callables
        if hasattr(result, "__await__"):
            await result


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities for Xbox Dev Mode."""
    coordinator = entry.runtime_data

    entities = [
        XboxButton(coordinator, entry.entry_id, entry.unique_id, description)
        for description in BUTTONS
    ]

    async_add_entities(entities)
