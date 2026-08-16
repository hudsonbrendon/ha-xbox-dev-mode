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
    """When device does not respond to ping, state is off."""
    data = await _run(hass, AsyncMock(), alive=False)
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
