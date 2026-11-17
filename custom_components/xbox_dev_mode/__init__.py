"""Xbox Dev Mode integration for Home Assistant."""
import logging

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from xbox_devportal import XboxDevPortal

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SCREENSHOT_INTERVAL,
    CONF_SETTINGS_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SCREENSHOT_INTERVAL,
    DEFAULT_SETTINGS_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import XboxDevModeCoordinator

_LOGGER = logging.getLogger(__name__)

# Services are registered once per hass instance (not per config entry) and
# removed once the last config entry is unloaded. Keep this list in sync with
# the hass.services.async_register(...) calls in _register_services().
_SERVICES = (
    "install_package",
    "uninstall_package",
    "launch",
    "terminate",
    "upload_file",
    "set_setting",
)


async def async_setup_entry(hass, entry) -> bool:
    """Set up Xbox Dev Mode from a config entry.

    Creates XboxDevPortal client, instantiates coordinator, and registers
    platform integrations.
    """
    # Retrieve configuration
    host = entry.data[CONF_HOST]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)

    # Retrieve or use default intervals
    options = entry.options
    scan_iv = options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    shot_iv = options.get(CONF_SCREENSHOT_INTERVAL, DEFAULT_SCREENSHOT_INTERVAL)
    settings_iv = options.get(CONF_SETTINGS_INTERVAL, DEFAULT_SETTINGS_INTERVAL)

    # Create shared aiohttp session for the client
    session = async_get_clientsession(hass)
    client = XboxDevPortal(host, username, password, port=port, session=session)

    # Create and register coordinator
    coordinator = XboxDevModeCoordinator(
        hass, client, host, scan=scan_iv, shot=shot_iv, settings_iv=settings_iv, entry=entry
    )

    # Perform initial data fetch
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator in runtime data for access by entities
    entry.runtime_data = coordinator

    # Forward entry setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register service handlers once per hass instance. Multiple config
    # entries (multiple consoles) share the same services.
    if not hass.services.has_service(DOMAIN, _SERVICES[0]):
        _register_services(hass)

    return True


async def async_unload_entry(hass, entry) -> bool:
    """Unload a config entry.

    Unloads all platforms, clears the stale coordinator reference, and (once
    no other config entry for this integration is still loaded) removes the
    services so a stray service call can't reach a torn-down coordinator.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry.runtime_data = None

        other_loaded = [
            e
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id and e.state is ConfigEntryState.LOADED
        ]
        if not other_loaded:
            for service in _SERVICES:
                hass.services.async_remove(DOMAIN, service)

    return unload_ok


def _get_coordinator(hass, device_id: str | None = None):
    """Get coordinator by device_id or return the only one if unique.

    Args:
        hass: Home Assistant instance
        device_id: Optional device ID to specify which entry to use

    Returns:
        The coordinator

    Raises:
        HomeAssistantError: If no entry found, multiple entries exist without device_id, etc.
    """
    entries = hass.config_entries.async_entries(DOMAIN)

    if not entries:
        raise HomeAssistantError(f"No {DOMAIN} config entries found")

    if device_id:
        # Find entry by device_id
        for entry in entries:
            coordinator = getattr(entry, "runtime_data", None)
            if coordinator and hasattr(coordinator, "_host"):  # noqa: SIM102
                # Match by host (simple device identifier)
                if coordinator._host == device_id:
                    return coordinator
        raise HomeAssistantError(f"No device found with ID {device_id}")

    # If only one entry, use it
    if len(entries) == 1:
        coordinator = getattr(entries[0], "runtime_data", None)
        if coordinator is None:
            raise HomeAssistantError(
                f"The {DOMAIN} integration is not loaded; reload it and try again"
            )
        return coordinator

    # Multiple entries without device_id
    raise HomeAssistantError(
        f"Multiple {DOMAIN} entries exist, specify device_id in service call"
    )


def _register_services(hass):
    """Register service handlers for Xbox Dev Mode."""
    async def handle_install_package(call):
        """Handle install_package service call."""
        path = call.data.get("path")
        coordinator = _get_coordinator(hass)

        # Validate path is within config directory
        if not hass.config.is_allowed_path(path):
            raise HomeAssistantError(f"Path not allowed: {path}")

        try:
            await coordinator.client.install(path)
        except Exception as e:
            _LOGGER.error("Error installing package: %s", e)
            raise HomeAssistantError(f"Failed to install package: {e}") from e

    async def handle_uninstall_package(call):
        """Handle uninstall_package service call."""
        package_full_name = call.data.get("package_full_name")
        coordinator = _get_coordinator(hass)

        try:
            await coordinator.client.uninstall(package_full_name)
        except Exception as e:
            _LOGGER.error("Error uninstalling package: %s", e)
            raise HomeAssistantError(f"Failed to uninstall package: {e}") from e

    async def handle_launch(call):
        """Handle launch service call."""
        package_full_name = call.data.get("package_full_name")
        coordinator = _get_coordinator(hass)

        try:
            await coordinator.client.launch(package_full_name)
        except Exception as e:
            _LOGGER.error("Error launching app: %s", e)
            raise HomeAssistantError(f"Failed to launch app: {e}") from e

    async def handle_terminate(call):
        """Handle terminate service call."""
        package_full_name = call.data.get("package_full_name")
        coordinator = _get_coordinator(hass)

        try:
            await coordinator.client.terminate(package_full_name)
        except Exception as e:
            _LOGGER.error("Error terminating app: %s", e)
            raise HomeAssistantError(f"Failed to terminate app: {e}") from e

    async def handle_upload_file(call):
        """Handle upload_file service call."""
        package_full_name = call.data.get("package_full_name")
        subdir = call.data.get("subdir")
        path = call.data.get("path")
        coordinator = _get_coordinator(hass)

        # Validate path is within config directory
        if not hass.config.is_allowed_path(path):
            raise HomeAssistantError(f"Path not allowed: {path}")

        try:
            await coordinator.client.upload_file(package_full_name, subdir, path)
        except Exception as e:
            _LOGGER.error("Error uploading file: %s", e)
            raise HomeAssistantError(f"Failed to upload file: {e}") from e

    async def handle_set_setting(call):
        """Handle set_setting service call."""
        name = call.data.get("name")
        value = call.data.get("value")
        coordinator = _get_coordinator(hass)

        try:
            await coordinator.client.set_setting(name, value)
        except Exception as e:
            _LOGGER.error("Error setting value: %s", e)
            raise HomeAssistantError(f"Failed to set setting: {e}") from e

    # Register all services
    hass.services.async_register(
        DOMAIN, "install_package", handle_install_package, supports_response=False
    )
    hass.services.async_register(
        DOMAIN, "uninstall_package", handle_uninstall_package, supports_response=False
    )
    hass.services.async_register(
        DOMAIN, "launch", handle_launch, supports_response=False
    )
    hass.services.async_register(
        DOMAIN, "terminate", handle_terminate, supports_response=False
    )
    hass.services.async_register(
        DOMAIN, "upload_file", handle_upload_file, supports_response=False
    )
    hass.services.async_register(
        DOMAIN, "set_setting", handle_set_setting, supports_response=False
    )
