from unittest.mock import AsyncMock, patch
from homeassistant import data_entry_flow
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.helpers.service_info.ssdp import SsdpServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.xbox_dev_mode.const import DOMAIN


def _patch_client(ok=True):
    m = AsyncMock()
    if not ok:
        from xbox_devportal import AuthError
        m.info.side_effect = AuthError("bad")
    return patch("custom_components.xbox_dev_mode.config_flow.XboxDevPortal", return_value=m)


async def test_user_flow_success(hass):
    with _patch_client():
        r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        r2 = await hass.config_entries.flow.async_configure(r["flow_id"], {
            "host": "10.0.0.5", "port": 11443, "username": "u", "password": "p"})
    assert r2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert r2["data"]["host"] == "10.0.0.5"


async def test_user_flow_bad_auth(hass):
    with _patch_client(ok=False):
        r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        r2 = await hass.config_entries.flow.async_configure(r["flow_id"], {
            "host": "10.0.0.5", "port": 11443, "username": "u", "password": "x"})
    assert r2["type"] == data_entry_flow.FlowResultType.FORM
    assert r2["errors"]["base"] == "invalid_auth"


async def test_ssdp_shows_form(hass):
    info = SsdpServiceInfo(ssdp_usn="usn", ssdp_st="st",
                           ssdp_udn="uuid:08e2300a-1a55", ssdp_location="http://10.0.0.5:2869/x",
                           upnp={})
    r = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "ssdp"}, data=info)
    assert r["type"] == data_entry_flow.FlowResultType.FORM
    assert r["step_id"] == "user"


async def test_reauth_flow_success(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, title="Xbox (10.0.0.5)",
        data={CONF_HOST: "10.0.0.5", CONF_PORT: 11443, CONF_USERNAME: "old_user", CONF_PASSWORD: "old_pass"},
        unique_id="10.0.0.5:11443")
    entry.add_to_hass(hass)

    with _patch_client():
        r = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "reauth", "entry_id": entry.entry_id})
        r2 = await hass.config_entries.flow.async_configure(r["flow_id"], {
            "username": "new_user", "password": "new_pass"})

    assert r2["type"] == data_entry_flow.FlowResultType.ABORT
    assert r2["reason"] == "reauth_successful"
    assert entry.data[CONF_USERNAME] == "new_user"
    assert entry.data[CONF_PASSWORD] == "new_pass"
