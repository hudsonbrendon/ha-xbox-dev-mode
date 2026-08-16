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

    _dev_only: bool = True

    def __init__(self, coordinator: XboxDevModeCoordinator, entry_id: str):
        """Initialize Xbox entity.

        Args:
            coordinator: The coordinator for this entity.
            entry_id: The config entry ID.
        """
        super().__init__(coordinator)
        self._entry_id = entry_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        if not self.coordinator.data or not self.coordinator.data.info:
            # Fallback device info when no data is available yet
            return DeviceInfo(
                identifiers={(DOMAIN, "unknown")},
                manufacturer="Microsoft",
                model="Unknown",
                name="Xbox",
            )
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.data.info.computer_name)},
            manufacturer="Microsoft",
            model=self.coordinator.data.info.platform,
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
