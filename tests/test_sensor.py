"""Tests for Xbox Dev Mode sensor platform."""
from custom_components.xbox_dev_mode.const import STATE_DEV, STATE_OFF
from custom_components.xbox_dev_mode.coordinator import XboxData
from custom_components.xbox_dev_mode.sensor import SENSORS
from xbox_devportal.models import SystemPerf


async def test_sensors_created_and_state(hass, setup_integration):
    """Test that sensors are created with correct state in dev mode."""
    assert hass.states.get("sensor.xbox_console_state").state == STATE_DEV
    assert hass.states.get("sensor.xbox_cpu_load").state == "3"


async def test_non_state_sensors_unavailable_when_off(hass, setup_integration_off):
    """Test that non-state sensors become unavailable when console is off."""
    assert hass.states.get("sensor.xbox_console_state").state == STATE_OFF
    assert hass.states.get("sensor.xbox_cpu_load").state == "unavailable"


async def test_sandbox_sensor_state(hass, setup_integration):
    """Test that the sandbox sensor reports the value from client.sandbox()."""
    assert hass.states.get("sensor.xbox_sandbox").state == "XDKS.1"


async def test_sandbox_sensor_available_when_off(hass, setup_integration_off):
    """Test sandbox sensor availability when off.

    sandbox has dev_only=False, so it stays available (not "unavailable")
    even with the console off; there's just no value yet (state "unknown"),
    since sandbox is only fetched on the settings cadence while in dev_mode.
    """
    state = hass.states.get("sensor.xbox_sandbox")
    assert state.state != "unavailable"
    assert state.state == "unknown"


def test_foreground_app_fallback_is_none():
    """The sensor's default language is English; the "no foreground app"
    fallback must be None (-> unknown state), not a hardcoded PT-BR string.
    """
    foreground = next(s for s in SENSORS if s.key == "foreground_app")
    data = XboxData(state=STATE_DEV, foreground=None)
    assert foreground.value_fn(data) is None


def test_memory_used_matches_lib_memory_used_mb():
    """memory_used must use SystemPerf.memory_used_mb (total - available), not committed - available.

    Real console payload: total_pages=327680, available_pages=45557,
    committed_pages=1624279, page_size=4096.
    Correct value: (327680 - 45557) * 4096 // (1024*1024) = 1102 MB.
    The old (buggy) formula used committed_pages instead of total_pages and
    reported 6166 MB, over 5x the true 1280 MB total.
    """
    perf = SystemPerf(
        cpu_load=3,
        total_pages=327680,
        available_pages=45557,
        committed_pages=1624279,
        page_size=4096,
        gpu_dedicated=134217728,
        gpu_dedicated_used=123781120,
    )
    data = XboxData(state=STATE_DEV, perf=perf)

    memory_used = next(s for s in SENSORS if s.key == "memory_used")

    assert memory_used.value_fn(data) == perf.memory_used_mb == 1102
