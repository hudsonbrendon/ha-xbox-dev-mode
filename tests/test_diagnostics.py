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
    """Test that diagnostics redact SMB credentials properly.

    Verifies that:
    1. SMB credentials are included in diagnostics
    2. The password field is redacted to **REDACTED**
    3. The username and path fields are preserved
    4. The sensitive password never appears in the diagnostic output
    """
    import json
    from custom_components.xbox_dev_mode.diagnostics import async_get_config_entry_diagnostics

    entry = hass.config_entries.async_entries("xbox_dev_mode")[0]
    diag = await async_get_config_entry_diagnostics(hass, entry)

    # SMB credentials should be present
    assert "smb_credentials" in diag

    smb = diag["smb_credentials"]
    # Username and path should be preserved
    assert smb["username"] == "developer"
    assert smb["path"] == r"\\XBOX\Scratch"

    # Password should be redacted
    assert smb["password"] == "**REDACTED**"

    # The original password should never appear anywhere in the diagnostics
    diag_json = json.dumps(diag)
    assert "devpass123" not in diag_json, "Original password leaked in diagnostics!"


async def test_diagnostics_skips_smb_lookup_when_off(hass, setup_integration_off, mock_devportal):
    """SMB credentials live behind the Device Portal, unreachable in
    retail/off. Diagnostics must not even attempt the lookup in that state.
    """
    from custom_components.xbox_dev_mode.diagnostics import async_get_config_entry_diagnostics

    entry = hass.config_entries.async_entries("xbox_dev_mode")[0]
    diag = await async_get_config_entry_diagnostics(hass, entry)

    assert "smb_credentials" not in diag
    mock_devportal.smb_credentials.assert_not_awaited()
