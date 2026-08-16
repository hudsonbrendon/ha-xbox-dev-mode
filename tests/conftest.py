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

    Uses real method names from xbox-devportal library:
    info, system_perf, processes, foreground_app, packages, launch, terminate,
    settings, set_setting, sandbox, smb_credentials, screenshot, restart,
    shutdown, list_files, upload_file, delete_file, install, uninstall, close.
    """
    from xbox_devportal.models import DeviceInfo, SystemPerf, Process, Package, Setting, SmbShare

    defaults = {
        "info": AsyncMock(
            return_value=DeviceInfo(
                computer_name="XBOX",
                os_version="26100.9426",
                platform="Xbox Series S",
            )
        ),
        "system_perf": AsyncMock(
            return_value=SystemPerf(
                cpu_load=3,
                total_pages=327680,
                available_pages=45557,
                committed_pages=162427,
                page_size=4096,
                gpu_dedicated=134217728,
                gpu_dedicated_used=123781120,
            )
        ),
        "processes": AsyncMock(
            return_value=[
                Process(
                    image_name="Explorer.EXE",
                    package_full_name="Microsoft.Xbox.Dashboard_2301.1001.1.0_x64__8wekyb3d8bbwe",
                    private_working_set=104857600,
                ),
            ]
        ),
        "foreground_app": AsyncMock(
            return_value=Process(
                image_name="RetroArch.exe",
                package_full_name="1e4c_1.19.0.0_x64__1e4c_x!App",
                private_working_set=209715200,
            )
        ),
        "packages": AsyncMock(
            return_value=[
                Package(
                    name="RetroArch",
                    package_full_name="1e4c_1.19.0.0_x64__1e4c_x!App",
                    package_relative_id="1e4c_x!App",
                    can_uninstall=True,
                ),
            ]
        ),
        "launch": AsyncMock(return_value=None),
        "terminate": AsyncMock(return_value=None),
        "settings": AsyncMock(
            return_value={
                "TVResolution": Setting("TVResolution", "1080p", ("720p", "1080p", "2160p")),
                "AllowHDR": Setting("AllowHDR", "true", ()),
            }
        ),
        "set_setting": AsyncMock(return_value=None),
        "sandbox": AsyncMock(return_value="RETAIL"),
        "smb_credentials": AsyncMock(
            return_value=SmbShare(
                path=r"\\xbox.local\Developer$",
                username="xbox_dev",
                password="devpwd",
            )
        ),
        "screenshot": AsyncMock(return_value=b"\x89PNG\r\n\x1a\n"),  # PNG header
        "restart": AsyncMock(return_value=None),
        "shutdown": AsyncMock(return_value=None),
        "list_files": AsyncMock(return_value=[]),
        "upload_file": AsyncMock(return_value=None),
        "delete_file": AsyncMock(return_value=None),
        "install": AsyncMock(return_value=None),
        "uninstall": AsyncMock(return_value=None),
        "close": AsyncMock(return_value=None),
    }
    with patch.multiple(
        "xbox_devportal.XboxDevPortal", create=True, **defaults
    ):
        yield defaults
