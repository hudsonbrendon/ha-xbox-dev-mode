"""Base entity for Xbox Dev Mode integration."""
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, STATE_DEV
from .coordinator import XboxDevModeCoordinator


class XboxEntity(CoordinatorEntity[XboxDevModeCoordinator]):
    """Base entity for Xbox Dev Mode integration.

    All Xbox entities inherit from this class and automatically
    sync with the coordinator.
    """

    _attr_has_entity_name = True
    _dev_only: bool = True

    def __init__(self, coordinator: XboxDevModeCoordinator, entry_id: str, entry_unique_id: str):
        """Initialize Xbox entity.

        Args:
            coordinator: The coordinator for this entity.
            entry_id: The config entry ID.
            entry_unique_id: The config entry's unique ID (stable device identifier).
        """
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._entry_unique_id = entry_unique_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information.

        Uses entry unique_id as stable identifier (does not change across
        console state transitions). Model is cosmetic and can fallback.
        """
        model = "Unknown"
        if self.coordinator.data and self.coordinator.data.info:
            model = self.coordinator.data.info.platform

        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_unique_id)},
            manufacturer="Microsoft",
            model=model,
            name="Xbox",
        )

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Entity is available if:
        1. Coordinator is available (base class check)
        2. If _dev_only=True, console must be in dev_mode
        3. If _dev_only=False, always available regardless of console state
        """
        base_available = super().available
        if not base_available:
            return False

        if self._dev_only:
            return self.coordinator.data.state == STATE_DEV

        return True
