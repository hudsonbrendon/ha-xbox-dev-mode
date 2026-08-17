"""Test switch platform for Xbox Dev Mode integration."""
from custom_components.xbox_dev_mode.const import STATE_DEV
from custom_components.xbox_dev_mode.coordinator import XboxData
from custom_components.xbox_dev_mode.switch import SWITCHES
from xbox_devportal.models import Setting


def test_switch_value_fn_is_case_insensitive():
    """The devportal lib stringifies the raw value with str(...), so a JSON
    boolean ``true`` arrives as ``"True"`` (capital T), not ``"true"``. The
    switch's value_fn must not compare with case-sensitive equality or the
    switch is stuck reporting off forever.
    """
    allow_hdr = next(s for s in SWITCHES if s.key == "allow_hdr")

    on_lower = XboxData(state=STATE_DEV, settings={"AllowHDR": Setting("AllowHDR", "true", ())})
    on_title = XboxData(state=STATE_DEV, settings={"AllowHDR": Setting("AllowHDR", "True", ())})
    off_title = XboxData(state=STATE_DEV, settings={"AllowHDR": Setting("AllowHDR", "False", ())})
    missing = XboxData(state=STATE_DEV, settings={})

    assert allow_hdr.value_fn(on_lower) is True
    assert allow_hdr.value_fn(on_title) is True
    assert allow_hdr.value_fn(off_title) is False
    assert allow_hdr.value_fn(missing) is False


async def test_allow_hdr_toggle_off(hass, setup_integration, mock_devportal):
    """Test Allow HDR switch toggle off."""
    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": "switch.xbox_allow_hdr"},
        blocking=True,
    )
    mock_devportal.set_setting.assert_awaited_with("AllowHDR", "false")


async def test_setting_switch_unavailable_when_not_fetched(hass, setup_integration_off):
    """Test setting switch is unavailable when setting not fetched.

    When console is in OFF state or settings haven't been fetched,
    setting switches should be unavailable.
    """
    # setup_integration_off returns device in OFF state, so no settings fetched
    state = hass.states.get("switch.xbox_allow_4k")
    assert state is not None
    assert state.state == "unavailable"
