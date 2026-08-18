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


_mock_devportal_instance = None


@pytest.fixture(autouse=True)
def _mock_xbox_devportal():
    """Mock XboxDevPortal globally to prevent HTTP requests in tests.

    Default mocks all methods to prevent real network calls with proper
    return values that match the xbox-devportal library's actual types.
    """
    global _mock_devportal_instance
    from xbox_devportal import XboxDevPortal
    from xbox_devportal.models import (DeviceInfo, SystemPerf, Process, Package, Setting,
                                       SmbShare, XboxInfo, XboxUser)

    with patch("custom_components.xbox_dev_mode.XboxDevPortal") as mock_portal_class, \
         patch("xbox_devportal.XboxDevPortal") as mock_xbox:
        mock_instance = AsyncMock(spec=XboxDevPortal)
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
        mock_instance.sandbox = AsyncMock(return_value="XDKS.1")
        mock_instance.set_setting = AsyncMock()
        mock_instance.smb_credentials = AsyncMock(
            return_value=SmbShare(
                path=r"\\XBOX\Scratch",
                username="developer",
                password="devpass123",
            )
        )
        mock_instance.xbox_info = AsyncMock(
            return_value=XboxInfo(
                os_version="10.0.26100.9426",
                dev_mode="Universal Windows App Devkit",
                os_edition="August 2026",
                console_type="Lockhart",
                console_id="fc2e882b.da781302.d95ce169.16d77f0c.01",
                device_id="F4001DA0057F0978",
                serial_number="218131213717",
                devkit_certificate_expiration=1792168903,
            )
        )
        mock_instance.users = AsyncMock(
            return_value=[XboxUser(
                user_id=16, email_address="dev@example.com", gamertag="hud7796",
                xbox_user_id="2535419684726904", signed_in=True, auto_sign_in=True,
            )]
        )
        mock_instance.controller_count = AsyncMock(return_value=1)
        mock_instance.disconnect_controllers = AsyncMock()
        mock_instance.press_gamepad_button = AsyncMock()
        mock_portal_class.return_value = mock_instance
        mock_xbox.return_value = mock_instance
        _mock_devportal_instance = mock_instance
        yield mock_instance
        _mock_devportal_instance = None


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
    """Fixture providing reference to mock portal methods.

    The actual mocking is done by the autouse _mock_xbox_devportal fixture.
    This fixture returns the reference to the mock instance.
    """
    global _mock_devportal_instance
    return _mock_devportal_instance


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
async def setup_integration_with_shot(hass, mock_devportal):
    """Set up integration with console in dev_mode and screenshot enabled.

    Console responds to ping, Device Portal is reachable, and screenshot
    interval is > 0 so screenshot entity is available.
    """
    from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.xbox_dev_mode.const import (
        DOMAIN,
        DEFAULT_PORT,
        CONF_SCAN_INTERVAL,
        CONF_SCREENSHOT_INTERVAL,
        CONF_SETTINGS_INTERVAL,
    )

    # Create config entry with non-zero screenshot interval
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Xbox (10.0.0.5)",
        data={
            CONF_HOST: "10.0.0.5",
            CONF_USERNAME: "developer",
            CONF_PASSWORD: "devpass",
            CONF_PORT: DEFAULT_PORT,
        },
        options={
            CONF_SCAN_INTERVAL: 30,
            CONF_SCREENSHOT_INTERVAL: 10,  # Short interval to ensure it runs on first cycle
            CONF_SETTINGS_INTERVAL: 120,
        },
        unique_id="uuid:test_shot",
    )
    entry.add_to_hass(hass)

    # Use the async_setup_entry async context helper
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    yield hass


@pytest.fixture
async def setup_integration_off(hass, mock_devportal):
    """Set up integration with console powered off.

    Console desligado significa duas coisas ao mesmo tempo: o Device Portal nao responde
    E o host nao responde a ping. Matar so o ping nao basta — desde que o coordinator
    passou a consultar o portal primeiro (para nao reportar OFF quando o ICMP esta
    indisponivel no host do Home Assistant), um cliente mockado que ainda responde
    `info()` resulta em dev_mode, nao em off.
    """
    from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.xbox_dev_mode.const import DOMAIN, DEFAULT_PORT
    from xbox_devportal import DevPortalUnreachable

    # Override the autouse ping fixture to return not alive
    mock_ping_patcher = patch("custom_components.xbox_dev_mode.coordinator.async_ping")
    with mock_ping_patcher as mock_ping:
        mock_response = AsyncMock()
        mock_response.is_alive = False
        mock_ping.return_value = mock_response
        _mock_devportal_instance.info.side_effect = DevPortalUnreachable("console desligado")

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
