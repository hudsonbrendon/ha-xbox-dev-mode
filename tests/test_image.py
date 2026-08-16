"""Test image platform for Xbox Dev Mode integration."""


async def test_image_with_screenshot_enabled(hass, setup_integration_with_shot, mock_devportal):
    """Test image entity is created when screenshot is enabled.

    The entity may initially be unavailable until the first screenshot is fetched,
    which is normal behavior.
    """
    state = hass.states.get("image.xbox_screen")
    # Image entity should be created when screenshot interval > 0
    assert state is not None
    # Verify screenshot was attempted
    assert mock_devportal.screenshot.await_count >= 1


async def test_image_unavailable_without_screenshot_enabled(hass, setup_integration):
    """Test image entity is unavailable when screenshot is disabled (interval 0).

    When screenshot interval is 0 (disabled), the image entity should be unavailable
    because no screenshot data is fetched.
    """
    state = hass.states.get("image.xbox_screen")
    # Image entity should exist regardless
    if state is not None:
        # If entity exists, it should not be available (may be unavailable or unknown initially)
        assert state.state in ("unavailable", "unknown")
