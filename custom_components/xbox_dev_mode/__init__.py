"""Xbox Dev Mode integration for Home Assistant."""
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
from xbox_devportal import XboxDevPortal


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

    return True


async def async_unload_entry(hass, entry) -> bool:
    """Unload a config entry.

    Unloads all platforms and cleans up.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return unload_ok
