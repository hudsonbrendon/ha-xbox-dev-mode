"""Test button platform for Xbox Dev Mode integration."""
from custom_components.xbox_dev_mode.button import BUTTONS


def test_shutdown_button_has_no_device_class():
    """Only the restart button is an actual "restart" device_class; shutdown
    previously reused it too, which is misleading in the UI.
    """
    shutdown = next(b for b in BUTTONS if b.key == "shutdown")
    restart = next(b for b in BUTTONS if b.key == "restart")
    assert shutdown.device_class is None
    assert restart.device_class == "restart"


async def test_launch_button_launches(hass, setup_integration, mock_devportal):
    """Test launch app button launches the selected app."""
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.xbox_launch_app"},
        blocking=True,
    )
    assert mock_devportal.launch.await_count == 1
    mock_devportal.launch.assert_awaited_once_with("1e4c_1.19.0.0_x64__1e4c_x!App")


async def test_terminate_foreground_button(hass, setup_integration, mock_devportal):
    """Test terminate foreground button terminates the foreground app."""
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.xbox_terminate_foreground"},
        blocking=True,
    )
    assert mock_devportal.terminate.await_count == 1
    mock_devportal.terminate.assert_awaited_once_with("1e4c_1.19.0.0_x64__1e4c_x!App")


async def test_launch_button_noop_when_selected_app_unmatched(hass, setup_integration, mock_devportal):
    """Test launch app button is a no-op when selected_app matches no sideloaded app."""
    entry = hass.config_entries.async_entries("xbox_dev_mode")[0]
    entry.runtime_data.selected_app = "NonExistentApp"

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.xbox_launch_app"},
        blocking=True,
    )
    mock_devportal.launch.assert_not_awaited()


async def test_restart_button_calls_restart(hass, setup_integration, mock_devportal):
    """Test restart button calls restart on client."""
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.xbox_restart"},
        blocking=True,
    )
    mock_devportal.restart.assert_awaited_once()


async def test_shutdown_button_calls_shutdown(hass, setup_integration, mock_devportal):
    """Test shutdown button calls shutdown on client."""
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.xbox_shutdown"},
        blocking=True,
    )
    mock_devportal.shutdown.assert_awaited_once()
