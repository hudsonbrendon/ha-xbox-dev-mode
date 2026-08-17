"""Test image platform for Xbox Dev Mode integration."""
from unittest.mock import MagicMock

from custom_components.xbox_dev_mode.const import STATE_DEV
from custom_components.xbox_dev_mode.coordinator import XboxData
from custom_components.xbox_dev_mode.image import XboxScreenImage


async def test_image_last_updated_is_timezone_aware(hass):
    """async_image() must stamp _last_update_time with dt_util.utcnow()
    (timezone-aware), not the naive datetime.now(), or HA's history/recorder
    can misorder it against other aware timestamps.
    """
    coordinator = MagicMock()
    coordinator.hass = hass
    coordinator.data = XboxData(state=STATE_DEV, screenshot=b"PNG")

    entity = XboxScreenImage(coordinator, "entry1", "unique1")
    await entity.async_image()

    assert entity.image_last_updated is not None
    assert entity.image_last_updated.tzinfo is not None


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
    assert state is not None
    # If entity exists, it should not be available (may be unavailable or unknown initially)
    assert state.state in ("unavailable", "unknown")


async def test_image_entity_picture_is_populated(hass, setup_integration_with_shot, mock_devportal):
    """Test entity_picture is populated once a screenshot has been fetched.

    The Lovelace image card builds its proxy URL from entity_picture. If
    ImageEntity.__init__ is never called, access_tokens stays empty forever
    and entity_picture is permanently None, so the card never shows anything.
    """
    state = hass.states.get("image.xbox_screen")
    assert state is not None
    assert state.attributes.get("entity_picture") is not None
