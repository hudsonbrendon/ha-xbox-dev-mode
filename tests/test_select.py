"""Test select platform for Xbox Dev Mode integration."""


async def test_app_select_lists_sideloaded(hass, setup_integration):
    """Test app select lists sideloaded apps."""
    state = hass.states.get("select.xbox_app")
    assert state is not None
    assert "RetroArch" in state.attributes["options"]


async def test_tv_resolution_calls_set_setting(hass, setup_integration, mock_devportal):
    """Test TV resolution select calls set_setting."""
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.xbox_tv_resolution", "option": "2160p"},
        blocking=True,
    )
    mock_devportal.set_setting.assert_awaited_with("TVResolution", "2160p")
