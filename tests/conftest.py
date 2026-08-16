"""Fixtures for Xbox Dev Mode tests."""
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of custom integrations in all tests."""
    yield


@pytest.fixture(autouse=True)
def _instant_request_refresh():
    """Make the coordinator's background refresh fire immediately in tests.

    Setup now calls ``coordinator.async_request_refresh()`` (non-blocking) so
    HA finishes setup even when the device is unreachable.  That request is
    debounced with a 10s cooldown, which never elapses inside
    ``async_block_till_done``. Dropping the cooldown to 0 lets the first
    refresh complete during setup so entity-state assertions stay
    deterministic.
    """
    with patch(
        "homeassistant.helpers.update_coordinator.REQUEST_REFRESH_DEFAULT_COOLDOWN",
        0,
    ):
        yield


@pytest.fixture
def mock_devportal():
    """Patch all coordinator-polled XboxDevPortal methods with overridable AsyncMocks.

    Yields a dict keyed by method name; tests set `.return_value` (or
    `.side_effect`) before calling async_setup to customize responses.
    """
    defaults = {
        "authenticate": AsyncMock(return_value="tok"),
        "get_device_info": AsyncMock(return_value={}),
        "get_system_perf": AsyncMock(return_value={}),
        "list_processes": AsyncMock(return_value=[]),
        "list_packages": AsyncMock(return_value=[]),
        "get_setting": AsyncMock(return_value=None),
        "set_setting": AsyncMock(return_value=None),
        "list_smb_shares": AsyncMock(return_value=[]),
    }
    with patch.multiple(
        "xbox_devportal.XboxDevPortal", create=True, **defaults
    ):
        yield defaults
