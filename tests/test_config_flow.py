import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import respx
from homeassistant import data_entry_flow
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.helpers.service_info.ssdp import SsdpServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.xbox_dev_mode.const import DOMAIN, DEFAULT_PORT

COMPONENT_DIR = Path(__file__).parent.parent / "custom_components" / "xbox_dev_mode"


def _patch_client(ok=True):
    from xbox_devportal.models import DeviceInfo, SystemPerf, Process
    m = AsyncMock()
    if ok:
        m.info = AsyncMock(return_value=DeviceInfo(
            computer_name="XBOX",
            os_version="26100.9426",
            platform="Xbox Series S",
        ))
        m.system_perf = AsyncMock(return_value=SystemPerf(
            cpu_load=10, total_pages=1000, available_pages=500,
            committed_pages=400, page_size=4096,
            gpu_dedicated=1000000, gpu_dedicated_used=900000,
        ))
        m.foreground_app = AsyncMock(return_value=Process(
            image_name="test.exe",
            package_full_name="test_pkg",
            private_working_set=100000000,
        ))
        m.packages = AsyncMock(return_value=[])
        m.settings = AsyncMock(return_value={})
        m.screenshot = AsyncMock(return_value=b"PNG")
    else:
        from xbox_devportal import AuthError
        m.info.side_effect = AuthError("bad")

    # Patch in both config_flow and __init__
    patches = [
        patch("custom_components.xbox_dev_mode.config_flow.XboxDevPortal", return_value=m),
        patch("custom_components.xbox_dev_mode.XboxDevPortal", return_value=m),
    ]

    class _MultiPatch:
        def __enter__(self):
            for p in patches:
                p.__enter__()
            return m

        def __exit__(self, *args):
            for p in reversed(patches):
                p.__exit__(*args)

    return _MultiPatch()


@respx.mock
async def test_user_flow_success(hass):
    with _patch_client():
        r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        r2 = await hass.config_entries.flow.async_configure(r["flow_id"], {
            "host": "10.0.0.5", "port": 11443, "username": "u", "password": "p"})
    assert r2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert r2["data"]["host"] == "10.0.0.5"


@respx.mock
async def test_user_flow_bad_auth(hass):
    with _patch_client(ok=False):
        r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        r2 = await hass.config_entries.flow.async_configure(r["flow_id"], {
            "host": "10.0.0.5", "port": 11443, "username": "u", "password": "x"})
    assert r2["type"] == data_entry_flow.FlowResultType.FORM
    assert r2["errors"]["base"] == "invalid_auth"


@respx.mock
async def test_ssdp_shows_form(hass):
    info = SsdpServiceInfo(ssdp_usn="usn", ssdp_st="st",
                           ssdp_udn="uuid:08e2300a-1a55", ssdp_location="http://10.0.0.5:2869/x",
                           upnp={})
    r = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "ssdp"}, data=info)
    assert r["type"] == data_entry_flow.FlowResultType.FORM
    assert r["step_id"] == "user"


@respx.mock
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

    await hass.async_block_till_done()

    assert r2["type"] == data_entry_flow.FlowResultType.ABORT
    assert r2["reason"] == "reauth_successful"
    assert entry.data[CONF_USERNAME] == "new_user"
    assert entry.data[CONF_PASSWORD] == "new_pass"


@respx.mock
async def test_user_flow_unknown_error_maps_to_unknown(hass):
    """A validation error that is neither AuthError nor DevPortalUnreachable
    must be caught and mapped to the generic "unknown" error key instead of
    propagating as a raw, untranslated exception.
    """
    with _patch_client() as mock_client:
        mock_client.info.side_effect = RuntimeError("boom")
        r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        r2 = await hass.config_entries.flow.async_configure(r["flow_id"], {
            "host": "10.0.0.5", "port": 11443, "username": "u", "password": "p"})
    assert r2["type"] == data_entry_flow.FlowResultType.FORM
    assert r2["errors"]["base"] == "unknown"


async def test_options_flow_rejects_zero_scan_interval(hass):
    """scan_interval=0 would make the coordinator refresh in a tight loop
    (timedelta(seconds=0)); the options flow must reject it.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "10.0.0.5", CONF_PORT: DEFAULT_PORT, CONF_USERNAME: "u", CONF_PASSWORD: "p"},
        unique_id="uuid:opts-scan-zero")
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    with pytest.raises(data_entry_flow.InvalidData):
        await hass.config_entries.options.async_configure(result["flow_id"], {
            "scan_interval": 0, "screenshot_interval": 60, "settings_interval": 120})


async def test_options_flow_rejects_negative_settings_interval(hass):
    """Negative intervals are just as invalid as zero; must be rejected too."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "10.0.0.5", CONF_PORT: DEFAULT_PORT, CONF_USERNAME: "u", CONF_PASSWORD: "p"},
        unique_id="uuid:opts-settings-negative")
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    with pytest.raises(data_entry_flow.InvalidData):
        await hass.config_entries.options.async_configure(result["flow_id"], {
            "scan_interval": 30, "screenshot_interval": 60, "settings_interval": -1})


async def test_options_flow_allows_zero_screenshot_interval(hass):
    """screenshot_interval=0 intentionally means "screenshots off" and must
    stay accepted even though scan/settings reject 0.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "10.0.0.5", CONF_PORT: DEFAULT_PORT, CONF_USERNAME: "u", CONF_PASSWORD: "p"},
        unique_id="uuid:opts-shot-zero")
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result2 = await hass.config_entries.options.async_configure(result["flow_id"], {
        "scan_interval": 30, "screenshot_interval": 0, "settings_interval": 120})

    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["data"]["screenshot_interval"] == 0


def test_translation_files_have_reauth_and_unknown_keys():
    """strings.json/en.json/pt-BR.json must define reauth_successful (used by
    async_update_reload_and_abort) and a generic "unknown" error, since custom
    integrations don't inherit the core's common strings.
    """
    for relpath in ("strings.json", "translations/en.json", "translations/pt-BR.json"):
        data = json.loads((COMPONENT_DIR / relpath).read_text())
        assert data["config"]["abort"]["reauth_successful"], relpath
        assert data["config"]["error"]["unknown"], relpath


def test_translation_files_have_console_state_values():
    """entity.sensor.console_state.state.<value> must exist for dev_mode,
    retail and off in every translation file.
    """
    for relpath in ("strings.json", "translations/en.json", "translations/pt-BR.json"):
        data = json.loads((COMPONENT_DIR / relpath).read_text())
        states = data["entity"]["sensor"]["console_state"]["state"]
        assert set(states) == {"dev_mode", "retail", "off"}, relpath


async def test_user_flow_aborts_when_host_already_configured(hass):
    """Mesmo console nao pode entrar duas vezes.

    O caminho SSDP usa o UDN do UPnP como unique_id e o manual usa host:port. Como sao
    esquemas diferentes, `_abort_if_unique_id_configured()` nao pega a duplicata — numa
    instalacao real isso gerou duas entries carregadas para o mesmo Xbox, com 26
    entidades duplicadas (sufixo _2). A guarda por host cobre os dois caminhos.
    """
    from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    existente = MockConfigEntry(
        domain=DOMAIN,
        unique_id="uuid:08e2300a-1a55-4464-8689-835078580a45",   # veio do SSDP
        data={CONF_HOST: "10.0.0.5", CONF_PORT: 11443,
              CONF_USERNAME: "u", CONF_PASSWORD: "p"},
    )
    existente.add_to_hass(hass)

    with _patch_client():
        r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        r2 = await hass.config_entries.flow.async_configure(r["flow_id"], {
            CONF_HOST: "10.0.0.5", CONF_PORT: 11443,
            CONF_USERNAME: "outro", CONF_PASSWORD: "outra"})

    assert r2["type"] == data_entry_flow.FlowResultType.ABORT
    assert r2["reason"] == "already_configured"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
