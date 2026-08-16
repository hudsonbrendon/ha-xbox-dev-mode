"""Test switch platform for Xbox Dev Mode integration."""


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
