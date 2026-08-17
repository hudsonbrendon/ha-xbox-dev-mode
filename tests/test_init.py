"""Tests for integration setup and unload."""
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError
from custom_components.xbox_dev_mode.const import DEFAULT_PORT, DOMAIN


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
    # Configure services.async_register/has_service to be MagicMocks (not
    # async) since the real Home Assistant methods are synchronous.
    hass.services.async_register = MagicMock()
    hass.services.has_service = MagicMock(return_value=False)

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
    # Configure services.async_register/has_service to be MagicMocks (not
    # async) since the real Home Assistant methods are synchronous.
    hass.services.async_register = MagicMock()
    hass.services.has_service = MagicMock(return_value=False)

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
    # runtime_data must be cleared so a stray service call can't reach a
    # torn-down coordinator.
    assert entry.runtime_data is None


async def test_get_coordinator_raises_clear_error_when_entry_unloaded(hass, setup_integration):
    """_get_coordinator must raise a clear HomeAssistantError, not a raw
    AttributeError, when the entry's coordinator has been torn down (e.g.
    runtime_data cleared after an unload).

    Home Assistant actually *deletes* the runtime_data attribute after a
    successful unload (it doesn't set it to None), so the fixture must
    reflect that with delattr rather than assignment.
    """
    from custom_components.xbox_dev_mode import _get_coordinator

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    delattr(entry, "runtime_data")

    with pytest.raises(HomeAssistantError, match="not loaded"):
        _get_coordinator(hass)


async def test_services_unregistered_after_last_entry_unload(hass, setup_integration):
    """Once the only config entry unloads, its services must be removed so a
    stray service call can't reach a torn-down coordinator with a raw
    AttributeError.
    """
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert hass.services.has_service(DOMAIN, "install_package")

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.services.has_service(DOMAIN, "install_package")


async def test_services_stay_registered_with_another_entry_loaded(hass, setup_integration):
    """Unloading one of several config entries must not remove services that
    another loaded entry still needs.
    """
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry1 = hass.config_entries.async_entries(DOMAIN)[0]

    entry2 = MockConfigEntry(
        domain=DOMAIN,
        title="Xbox (10.0.0.6)",
        data={
            CONF_HOST: "10.0.0.6",
            CONF_USERNAME: "developer",
            CONF_PASSWORD: "devpass",
            CONF_PORT: DEFAULT_PORT,
        },
        unique_id="uuid:test2",
    )
    entry2.add_to_hass(hass)
    await hass.config_entries.async_setup(entry2.entry_id)
    await hass.async_block_till_done()

    await hass.config_entries.async_unload(entry1.entry_id)
    await hass.async_block_till_done()

    assert hass.services.has_service(DOMAIN, "install_package")
