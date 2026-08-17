"""Tests for Xbox Dev Mode services."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch


async def test_install_service_calls_client(hass, setup_integration, mock_devportal):
    """Test that install_package service calls the client's install() method."""
    # Mock is_allowed_path to allow the file
    with patch.object(hass.config, "is_allowed_path", return_value=True):
        await hass.services.async_call(
            "xbox_dev_mode", "install_package", {"path": "/fake/path/x.appx"}, blocking=True
        )
    mock_devportal.install.assert_awaited_once_with("/fake/path/x.appx")


async def test_uninstall_service_calls_client(hass, setup_integration, mock_devportal):
    """Test that uninstall_package service calls the client's uninstall() method."""
    await hass.services.async_call(
        "xbox_dev_mode",
        "uninstall_package",
        {"package_full_name": "1e4c_1.19.0.0_x64__1e4c_x!App"},
        blocking=True,
    )
    mock_devportal.uninstall.assert_awaited_once_with("1e4c_1.19.0.0_x64__1e4c_x!App")


async def test_launch_service_calls_client(hass, setup_integration, mock_devportal):
    """Test that launch service calls the client."""
    mock_devportal.launch = AsyncMock()
    await hass.services.async_call(
        "xbox_dev_mode",
        "launch",
        {"package_full_name": "1e4c_1.19.0.0_x64__1e4c_x!App"},
        blocking=True,
    )
    mock_devportal.launch.assert_awaited_once()


async def test_terminate_service_calls_client(hass, setup_integration, mock_devportal):
    """Test that terminate service calls the client."""
    mock_devportal.terminate = AsyncMock()
    await hass.services.async_call(
        "xbox_dev_mode",
        "terminate",
        {"package_full_name": "1e4c_1.19.0.0_x64__1e4c_x!App"},
        blocking=True,
    )
    mock_devportal.terminate.assert_awaited_once()


async def test_upload_file_service_calls_client(hass, setup_integration, mock_devportal):
    """Test that upload_file service calls the client."""
    mock_devportal.upload_file = AsyncMock()

    # Mock is_allowed_path to allow the file
    with patch.object(hass.config, "is_allowed_path", return_value=True):
        await hass.services.async_call(
            "xbox_dev_mode",
            "upload_file",
            {
                "package_full_name": "1e4c_1.19.0.0_x64__1e4c_x!App",
                "subdir": "documents",
                "path": "/fake/path/test.txt",
            },
            blocking=True,
        )
    mock_devportal.upload_file.assert_awaited_once()


async def test_set_setting_service_calls_client(hass, setup_integration, mock_devportal):
    """Test that set_setting service calls the client."""
    mock_devportal.set_setting = AsyncMock()
    await hass.services.async_call(
        "xbox_dev_mode",
        "set_setting",
        {"name": "TVResolution", "value": "2160p"},
        blocking=True,
    )
    mock_devportal.set_setting.assert_awaited_once()


async def test_install_service_rejects_file_outside_config(hass, setup_integration):
    """Test that install_package rejects files outside config directory."""
    import pytest
    from homeassistant.exceptions import HomeAssistantError

    # Use an absolute path that is NOT within hass.config.path()
    with pytest.raises(HomeAssistantError, match="Path not allowed"):
        await hass.services.async_call(
            "xbox_dev_mode", "install_package", {"path": "/etc/passwd"}, blocking=True
        )


async def test_upload_file_service_rejects_file_outside_config(hass, setup_integration):
    """Test that upload_file rejects files outside config directory."""
    import pytest
    from homeassistant.exceptions import HomeAssistantError

    with pytest.raises(HomeAssistantError, match="Path not allowed"):
        await hass.services.async_call(
            "xbox_dev_mode",
            "upload_file",
            {
                "package_full_name": "1e4c_1.19.0.0_x64__1e4c_x!App",
                "subdir": "documents",
                "path": "/etc/passwd",
            },
            blocking=True,
        )
