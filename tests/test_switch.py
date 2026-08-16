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
