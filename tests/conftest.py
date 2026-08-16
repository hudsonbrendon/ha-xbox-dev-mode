"""Fixtures for Xbox Dev Mode tests."""
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of custom integrations in all tests."""
    yield


@pytest.fixture(autouse=True)
def _mock_async_ping():
    """Mock async_ping to prevent real ICMP socket creation in tests.

    The coordinator's _async_update_data pings the device, which icmplib
    tries to do with a real socket. The test framework blocks this. Mock it
    globally so tests never touch the network.
    """
    with patch("custom_components.xbox_dev_mode.coordinator.async_ping") as mock_ping:
        mock_response = AsyncMock()
        mock_response.is_alive = True
        mock_ping.return_value = mock_response
        yield


@pytest.fixture(autouse=True)
def _mock_xbox_devportal():
    """Mock XboxDevPortal globally to prevent HTTP requests in tests.

    Default mocks all methods to prevent real network calls with proper
    return values that match the xbox-devportal library's actual types.
    """
    from xbox_devportal.models import DeviceInfo, SystemPerf, Process, Package, Setting

    with patch("custom_components.xbox_dev_mode.XboxDevPortal") as mock_portal_class, \
         patch("xbox_devportal.XboxDevPortal") as mock_xbox:
        mock_instance = AsyncMock()
        # Set up proper return values for each method
        mock_instance.info = AsyncMock(
            return_value=DeviceInfo(
                computer_name="XBOX",
                os_version="26100.9426",
                platform="Xbox Series S",
            )
        )
        mock_instance.system_perf = AsyncMock(
            return_value=SystemPerf(
                cpu_load=3,
                total_pages=327680,
                available_pages=45557,
                committed_pages=162427,
                page_size=4096,
                gpu_dedicated=134217728,
                gpu_dedicated_used=123781120,
            )
        )
        mock_instance.foreground_app = AsyncMock(
            return_value=Process(
                image_name="RetroArch.exe",
                package_full_name="1e4c_1.19.0.0_x64__1e4c_x!App",
                private_working_set=209715200,
            )
        )
        mock_instance.packages = AsyncMock(
            return_value=[
                Package(
                    name="RetroArch",
                    package_full_name="1e4c_1.19.0.0_x64__1e4c_x!App",
                    package_relative_id="1e4c_x!App",
                    can_uninstall=True,
                ),
            ]
        )
        mock_instance.settings = AsyncMock(
            return_value={
                "TVResolution": Setting("TVResolution", "1080p", ("720p", "1080p", "2160p")),
                "AllowHDR": Setting("AllowHDR", "true", ()),
            }
        )
        mock_instance.screenshot = AsyncMock(return_value=b"\x89PNG\r\n\x1a\n")
        mock_portal_class.return_value = mock_instance
        mock_xbox.return_value = mock_instance
        yield mock_instance


@pytest.fixture(autouse=True)
def _instant_request_refresh():
    """Make the coordinator's background refresh fire immediately in tests.

    Setup now calls ``coordinator.async_config_entry_first_refresh()`` (blocking) so
    the first refresh completes during setup.  That call respects the
    REQUEST_REFRESH_DEFAULT_COOLDOWN debounce. Dropping the cooldown to 0 lets the
    first refresh complete during setup so entity-state assertions stay
    deterministic.
    """
    with patch(
        "homeassistant.helpers.update_coordinator.REQUEST_REFRESH_DEFAULT_COOLDOWN",
        0,
    ):
        yield


@pytest.fixture
def mock_devportal():
    """Fixture providing default mock data for coordinator tests.

    This fixture doesn't patch anything; instead it provides the data
    that the autouse _mock_xbox_devportal fixture should return.
    """
    from xbox_devportal.models import DeviceInfo, SystemPerf, Process, Package, Setting, SmbShare

    return {
        "info": DeviceInfo(
            computer_name="XBOX",
            os_version="26100.9426",
            platform="Xbox Series S",
        ),
        "system_perf": SystemPerf(
            cpu_load=3,
            total_pages=327680,
            available_pages=45557,
            committed_pages=162427,
            page_size=4096,
            gpu_dedicated=134217728,
            gpu_dedicated_used=123781120,
        ),
        "processes": [
            Process(
                image_name="Explorer.EXE",
                package_full_name="Microsoft.Xbox.Dashboard_2301.1001.1.0_x64__8wekyb3d8bbwe",
                private_working_set=104857600,
            ),
        ],
        "foreground_app": Process(
            image_name="RetroArch.exe",
            package_full_name="1e4c_1.19.0.0_x64__1e4c_x!App",
            private_working_set=209715200,
        ),
        "packages": [
            Package(
                name="RetroArch",
                package_full_name="1e4c_1.19.0.0_x64__1e4c_x!App",
                package_relative_id="1e4c_x!App",
                can_uninstall=True,
            ),
        ],
        "settings": {
            "TVResolution": Setting("TVResolution", "1080p", ("720p", "1080p", "2160p")),
            "AllowHDR": Setting("AllowHDR", "true", ()),
        },
        "sandbox": "RETAIL",
        "screenshot": b"\x89PNG\r\n\x1a\n",  # PNG header
    }


@pytest.fixture
async def setup_integration(hass, mock_devportal):
    """Set up integration with console in dev_mode.

    Console responds to ping and Device Portal is reachable.
    """
    from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.xbox_dev_mode.const import DOMAIN, DEFAULT_PORT

    # Create config entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Xbox (10.0.0.5)",
        data={
            CONF_HOST: "10.0.0.5",
            CONF_USERNAME: "developer",
            CONF_PASSWORD: "devpass",
            CONF_PORT: DEFAULT_PORT,
        },
        unique_id="uuid:test",
    )
    entry.add_to_hass(hass)

    # Use the async_setup_entry async context helper
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    yield hass


@pytest.fixture
async def setup_integration_off(hass, mock_devportal):
    """Set up integration with console powered off.

    Console does not respond to ping.
    """
    from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.xbox_dev_mode.const import DOMAIN, DEFAULT_PORT

    # Override the autouse ping fixture to return not alive
    mock_ping_patcher = patch("custom_components.xbox_dev_mode.coordinator.async_ping")
    with mock_ping_patcher as mock_ping:
        mock_response = AsyncMock()
        mock_response.is_alive = False
        mock_ping.return_value = mock_response

        # Create config entry
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Xbox (10.0.0.5)",
            data={
                CONF_HOST: "10.0.0.5",
                CONF_USERNAME: "developer",
                CONF_PASSWORD: "devpass",
                CONF_PORT: DEFAULT_PORT,
            },
            unique_id="uuid:test_off",
        )
        entry.add_to_hass(hass)

        # Set up the integration
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    yield hass
