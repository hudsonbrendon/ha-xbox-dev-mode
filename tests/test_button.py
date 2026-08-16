"""Test button platform for Xbox Dev Mode integration."""


async def test_launch_button_launches(hass, setup_integration, mock_devportal):
    """Test launch app button launches the selected app."""
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.xbox_launch_app"},
        blocking=True,
    )
    assert mock_devportal.launch.await_count == 1


async def test_terminate_foreground_button(hass, setup_integration, mock_devportal):
    """Test terminate foreground button terminates the foreground app."""
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.xbox_terminate_foreground"},
        blocking=True,
    )
    assert mock_devportal.terminate.await_count == 1


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
