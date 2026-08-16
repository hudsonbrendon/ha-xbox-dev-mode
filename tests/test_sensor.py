"""Tests for Xbox Dev Mode sensor platform."""
from custom_components.xbox_dev_mode.const import STATE_DEV, STATE_OFF


async def test_sensors_created_and_state(hass, setup_integration):
    """Test that sensors are created with correct state in dev mode."""
    assert hass.states.get("sensor.xbox_console_state").state == STATE_DEV
    assert hass.states.get("sensor.xbox_cpu_load").state == "3"


async def test_non_state_sensors_unavailable_when_off(hass, setup_integration_off):
    """Test that non-state sensors become unavailable when console is off."""
    assert hass.states.get("sensor.xbox_console_state").state == STATE_OFF
    assert hass.states.get("sensor.xbox_cpu_load").state == "unavailable"
