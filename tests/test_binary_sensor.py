"""Tests for Xbox Dev Mode binary sensor platform."""


async def test_dev_mode_binary_on_in_dev(hass, setup_integration):
    """Test that dev_mode binary sensor is on when console is in dev mode."""
    assert hass.states.get("binary_sensor.xbox_dev_mode").state == "on"


async def test_dev_mode_binary_off_when_off(hass, setup_integration_off):
    """Test that dev_mode binary sensor is off when console is powered off."""
    assert hass.states.get("binary_sensor.xbox_dev_mode").state == "off"
