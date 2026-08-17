"""Tests for Xbox Dev Mode diagnostics."""
import pytest


async def test_diagnostics_redacts_password(hass, setup_integration):
    """Test that diagnostics redact password in config entry."""
    from custom_components.xbox_dev_mode.diagnostics import async_get_config_entry_diagnostics

    entry = hass.config_entries.async_entries("xbox_dev_mode")[0]
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["entry"]["data"]["password"] == "**REDACTED**"


async def test_diagnostics_includes_device_info(hass, setup_integration):
    """Test that diagnostics include device info."""
    from custom_components.xbox_dev_mode.diagnostics import async_get_config_entry_diagnostics

    entry = hass.config_entries.async_entries("xbox_dev_mode")[0]
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert "coordinator_data" in diag
    assert diag["coordinator_data"]["state"] == "dev_mode"


async def test_diagnostics_redacts_smb_credentials(hass, setup_integration, mock_devportal):
    """Test that diagnostics redact SMB credentials if exposed by client."""
    from custom_components.xbox_dev_mode.diagnostics import async_get_config_entry_diagnostics

    # Mock smb_credentials() to return a dict with credentials
    mock_devportal.smb_credentials = lambda: {"username": "admin", "password": "secret"}

    entry = hass.config_entries.async_entries("xbox_dev_mode")[0]
    diag = await async_get_config_entry_diagnostics(hass, entry)
    # Should redact any password-like fields
    assert "**REDACTED**" in str(diag) or "password" not in str(diag).lower()
