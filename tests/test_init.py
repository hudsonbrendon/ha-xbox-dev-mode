"""Tests for integration setup and unload."""
from unittest.mock import AsyncMock, patch, MagicMock
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.config_entries import ConfigEntryState
from custom_components.xbox_dev_mode.const import DEFAULT_PORT


async def test_async_setup_entry_passes_credentials_to_portal():
    """Test that XboxDevPortal is instantiated with username and password.

    This test FAILS before the fix: __init__.py would call
    XboxDevPortal(host, session=session) without username/password,
    raising TypeError: missing 2 required positional arguments.
    """
    # Create a mock entry object with .data and .options attributes
    entry = MagicMock()
    entry.data = {
        CONF_HOST: "192.168.1.100",
        CONF_USERNAME: "developer",
        CONF_PASSWORD: "devpass",
        CONF_PORT: 11443,
    }
    entry.options = {}

    hass = AsyncMock()
    # Configure services.async_register to be a MagicMock (not async)
    # since the real Home Assistant method is synchronous
    hass.services.async_register = MagicMock()

    with patch("custom_components.xbox_dev_mode.XboxDevPortal") as mock_portal_class, patch(
        "custom_components.xbox_dev_mode.async_get_clientsession"
    ) as mock_session, patch(
        "custom_components.xbox_dev_mode.XboxDevModeCoordinator"
    ) as mock_coordinator_class:
        mock_client = AsyncMock()
        mock_portal_class.return_value = mock_client
        mock_session.return_value = AsyncMock()
        mock_coordinator = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator
        hass.config_entries.async_forward_entry_setups = AsyncMock()

        from custom_components.xbox_dev_mode import async_setup_entry

        await async_setup_entry(hass, entry)

        # CRITICAL: Verify XboxDevPortal was called with all credentials
        call_args = mock_portal_class.call_args
        assert call_args[0][0] == "192.168.1.100", "host not passed"
        assert call_args[0][1] == "developer", "username NOT passed (BUG!)"
        assert call_args[0][2] == "devpass", "password NOT passed (BUG!)"
        assert call_args[1]["port"] == 11443, "port not passed"


async def test_async_setup_entry_uses_configured_port():
    """Test that custom port from entry.data is used, not DEFAULT_PORT."""
    entry = MagicMock()
    entry.data = {
        CONF_HOST: "xbox.local",
        CONF_USERNAME: "admin",
        CONF_PASSWORD: "secret",
        CONF_PORT: 8443,
    }
    entry.options = {}

    hass = AsyncMock()
    # Configure services.async_register to be a MagicMock (not async)
    # since the real Home Assistant method is synchronous
    hass.services.async_register = MagicMock()

    with patch("custom_components.xbox_dev_mode.XboxDevPortal") as mock_portal_class, patch(
        "custom_components.xbox_dev_mode.async_get_clientsession"
    ) as mock_session, patch(
        "custom_components.xbox_dev_mode.XboxDevModeCoordinator"
    ) as mock_coordinator_class:
        mock_client = AsyncMock()
        mock_portal_class.return_value = mock_client
        mock_session.return_value = AsyncMock()
        mock_coordinator = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator
        hass.config_entries.async_forward_entry_setups = AsyncMock()

        from custom_components.xbox_dev_mode import async_setup_entry

        await async_setup_entry(hass, entry)

        call_args = mock_portal_class.call_args
        assert call_args[1]["port"] == 8443, f"Expected 8443, got {call_args[1]['port']}"


async def test_async_unload_entry(hass):
    """Test that async_unload_entry unloads platforms and returns True."""
    from custom_components.xbox_dev_mode.const import PLATFORMS

    # Create config entry
    entry = MagicMock()
    entry.data = {
        CONF_HOST: "192.168.1.100",
        CONF_USERNAME: "developer",
        CONF_PASSWORD: "devpass",
        CONF_PORT: 11443,
    }
    entry.options = {}
    entry.entry_id = "test_entry_id"
    entry.state = ConfigEntryState.LOADED

    # Mock unload_platforms to succeed
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    # Import and call the unload function
    from custom_components.xbox_dev_mode import async_unload_entry

    result = await async_unload_entry(hass, entry)

    # Verify unload succeeded and platforms were unloaded with correct args
    assert result is True, "async_unload_entry should return True"
    hass.config_entries.async_unload_platforms.assert_called_once_with(entry, PLATFORMS)
