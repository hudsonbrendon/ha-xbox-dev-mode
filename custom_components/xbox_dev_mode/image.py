"""Image platform for Xbox Dev Mode integration."""
from datetime import datetime

import homeassistant.util.dt as dt_util
from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import XboxDevModeCoordinator
from .entity import XboxEntity


class XboxScreenImage(XboxEntity, ImageEntity):
    """Representation of Xbox screen screenshot image."""

    _attr_translation_key = "screen"
    _last_screenshot: bytes | None = None
    _last_update_time: datetime | None = None

    def __init__(
        self,
        coordinator: XboxDevModeCoordinator,
        entry_id: str,
        entry_unique_id: str,
    ):
        """Initialize Xbox screen image.

        Args:
            coordinator: The coordinator for this entity.
            entry_id: The config entry ID.
            entry_unique_id: The config entry's unique ID.
        """
        XboxEntity.__init__(self, coordinator, entry_id, entry_unique_id)
        ImageEntity.__init__(self, coordinator.hass)
        self._attr_unique_id = f"{entry_id}_screen"

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Image is available only if:
        1. Base availability is true (coordinator.available and dev_mode)
        2. Screenshot has been fetched and is not None
        """
        base_available = super().available
        if not base_available:
            return False

        # Screenshot must be available and not None
        if self.coordinator.data.screenshot is None:  # noqa: SIM103
            return False

        return True

    @property
    def image_last_updated(self) -> datetime | None:
        """Return the last update of the image."""
        return self._last_update_time

    async def async_image(self) -> bytes | None:
        """Return bytes of image."""
        current_screenshot = self.coordinator.data.screenshot

        # Only update timestamp if screenshot data changed
        if current_screenshot and current_screenshot != self._last_screenshot:
            self._last_screenshot = current_screenshot
            self._last_update_time = dt_util.utcnow()

        return current_screenshot


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up image entities for Xbox Dev Mode."""
    coordinator = entry.runtime_data

    entities = [
        XboxScreenImage(coordinator, entry.entry_id, entry.unique_id),
    ]

    async_add_entities(entities)
