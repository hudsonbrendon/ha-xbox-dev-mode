"""Tests for XboxDevModeCoordinator tri-state logic."""
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.xbox_dev_mode.coordinator import XboxDevModeCoordinator
from custom_components.xbox_dev_mode.const import STATE_DEV, STATE_RETAIL, STATE_OFF
from xbox_devportal import DevPortalUnreachable


def _ping(alive):
    """Helper to patch async_ping with is_alive result."""
    r = type("R", (), {"is_alive": alive})()
    return patch(
        "custom_components.xbox_dev_mode.coordinator.async_ping",
        AsyncMock(return_value=r),
    )


async def _run(hass, client, alive):
    """Run coordinator update with mocked ping."""
    with _ping(alive):
        coord = XboxDevModeCoordinator(
            hass, client, "10.0.0.5", scan=30, shot=0, settings_iv=120
        )
        return await coord._async_update_data()


async def test_state_off_when_no_ping(hass):
    """Console desligado: portal inacessivel E sem resposta a ping.

    Um `AsyncMock()` cru responderia `info()` normalmente, e o coordinator — que agora
    consulta o portal antes do ping — concluiria dev_mode. Desligado de verdade exige
    as duas evidencias.
    """
    from xbox_devportal import DevPortalUnreachable

    client = AsyncMock()
    client.info.side_effect = DevPortalUnreachable("console desligado")
    data = await _run(hass, client, alive=False)
    assert data.state == STATE_OFF


async def test_state_retail_when_ping_but_portal_down(hass):
    """When ping succeeds but Device Portal is unreachable, state is retail."""
    client = AsyncMock()
    client.info.side_effect = DevPortalUnreachable("x")
    data = await _run(hass, client, alive=True)
    assert data.state == STATE_RETAIL


async def test_state_dev_when_portal_answers(hass):
    """When Device Portal responds, state is dev_mode and data is populated."""
    client = AsyncMock()
    client.info.return_value = object()
    client.system_perf.return_value = object()
    client.foreground_app.return_value = None
    client.packages.return_value = []
    data = await _run(hass, client, alive=True)
    assert data.state == STATE_DEV


async def test_sandbox_cached_across_cadence_cycles(hass):
    """Sandbox must not flicker to unknown between settings-cadence ticks.

    Regression test: with scan=30s and settings_iv=120s, sandbox is only
    fetched every 4th cycle. Before the fix, the ``sandbox`` local was reset
    to None every cycle regardless of cadence, so the sensor showed a value
    once and then "unknown" for the next three cycles. It must now be cached
    like ``_last_settings``/``_last_shot``.
    """
    client = AsyncMock()
    client.info.return_value = object()
    client.system_perf.return_value = object()
    client.foreground_app.return_value = None
    client.packages.return_value = []
    client.settings.return_value = {}
    client.sandbox.return_value = "XDKS.1"

    with _ping(True):
        coord = XboxDevModeCoordinator(
            hass, client, "10.0.0.5", scan=30, shot=0, settings_iv=120
        )
        for _ in range(4):
            data = await coord._async_update_data()
            assert data.sandbox == "XDKS.1"

    # Only fetched once (tick 0), reused on the three following cycles.
    assert client.sandbox.await_count == 1


async def test_dev_mode_mesmo_com_icmp_indisponivel(hass):
    """Portal respondendo vence ICMP quebrado.

    Caso real: numa instalacao de verdade o ICMP nao estava disponivel para o processo do
    Home Assistant, o ping devolvia is_alive=False, e a versao antiga — que pingava
    primeiro e desistia — reportava OFF com todas as entidades unavailable, enquanto o
    Device Portal respondia normalmente de outra maquina.
    """
    client = AsyncMock()
    client.info.return_value = object()
    client.system_perf.return_value = object()
    client.foreground_app.return_value = None
    client.packages.return_value = []
    with _ping(False):                      # ICMP diz que esta morto
        coord = XboxDevModeCoordinator(hass, client, "10.0.0.5", scan=30, shot=0, settings_iv=120)
        data = await coord._async_update_data()
    assert data.state == STATE_DEV           # o portal manda


async def test_retail_quando_icmp_estoura(hass):
    """Se o proprio ping levanta excecao, assume RETAIL em vez de afirmar OFF."""
    from unittest.mock import patch
    from xbox_devportal import DevPortalUnreachable

    client = AsyncMock()
    client.info.side_effect = DevPortalUnreachable("sem portal")
    with patch("custom_components.xbox_dev_mode.coordinator.async_ping",
               AsyncMock(side_effect=PermissionError("sem CAP_NET_RAW"))):
        coord = XboxDevModeCoordinator(hass, client, "10.0.0.5", scan=30, shot=0, settings_iv=120)
        data = await coord._async_update_data()
    assert data.state == STATE_RETAIL


async def test_portal_nao_e_consultado_para_decidir_off(hass):
    """Sem portal e sem ping = OFF (comportamento preservado)."""
    from xbox_devportal import DevPortalUnreachable

    client = AsyncMock()
    client.info.side_effect = DevPortalUnreachable("sem portal")
    with _ping(False):
        coord = XboxDevModeCoordinator(hass, client, "10.0.0.5", scan=30, shot=0, settings_iv=120)
        data = await coord._async_update_data()
    assert data.state == STATE_OFF
