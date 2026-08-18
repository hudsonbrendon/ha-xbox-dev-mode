"""Entidades adicionadas na 0.2.0: usuario, controles, modelo, certificado, remote."""


async def test_signed_in_user_sensor(hass, setup_integration):
    st = hass.states.get("sensor.xbox_signed_in_user")
    assert st is not None
    assert st.state == "hud7796"
    assert st.attributes.get("xbox_user_id") == "2535419684726904"
    assert st.attributes.get("auto_sign_in") is True
    # email nao vaza como estado, mas aparece como atributo (dado nao-secreto do dispositivo)
    assert st.attributes.get("email") == "dev@example.com"


async def test_controllers_sensor(hass, setup_integration):
    st = hass.states.get("sensor.xbox_connected_controllers")
    assert st is not None
    assert st.state == "1"


async def test_console_model_sensor_maps_codename(hass, setup_integration):
    st = hass.states.get("sensor.xbox_console_model")
    assert st is not None
    assert st.state == "Lockhart"                     # ConsoleType cru
    assert st.attributes.get("serial_number") == "218131213717"


async def test_certificate_expiration_is_timestamp(hass, setup_integration):
    from datetime import datetime, timezone
    st = hass.states.get("sensor.xbox_dev_kit_certificate_expiration")
    assert st is not None
    # device_class timestamp -> estado ISO 8601; 1792168903 = 2026-10-16
    esperado = datetime.fromtimestamp(1792168903, tz=timezone.utc).isoformat()
    assert st.state == esperado


async def test_device_info_uses_commercial_model_and_serial(hass, setup_integration):
    """O device no registry deve mostrar 'Xbox Series S' (de Lockhart) e o serial."""
    from homeassistant.helpers import device_registry as dr
    reg = dr.async_get(hass)
    dev = next(iter(reg.devices.values()))
    assert dev.model == "Xbox Series S"
    assert dev.serial_number == "218131213717"


async def test_disconnect_controllers_button(hass, setup_integration, mock_devportal):
    await hass.services.async_call(
        "button", "press",
        {"entity_id": "button.xbox_disconnect_controllers"}, blocking=True)
    mock_devportal.disconnect_controllers.assert_awaited_once()


async def test_remote_entity_on_in_dev_mode(hass, setup_integration):
    st = hass.states.get("remote.xbox_controller")
    assert st is not None
    assert st.state == "on"


async def test_remote_send_command_presses_button(hass, setup_integration, mock_devportal):
    await hass.services.async_call(
        "remote", "send_command",
        {"entity_id": "remote.xbox_controller", "command": ["dpad_up"]}, blocking=True)
    mock_devportal.press_gamepad_button.assert_awaited_once_with("dpad_up")


async def test_remote_send_command_rejects_invalid(hass, setup_integration, mock_devportal):
    import pytest
    with pytest.raises(Exception):
        await hass.services.async_call(
            "remote", "send_command",
            {"entity_id": "remote.xbox_controller", "command": ["nexus"]}, blocking=True)
    mock_devportal.press_gamepad_button.assert_not_awaited()
