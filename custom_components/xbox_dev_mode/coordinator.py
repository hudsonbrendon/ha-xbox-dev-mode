"""Xbox Dev Mode Coordinator with tri-state logic."""
import logging
from dataclasses import dataclass, field

from datetime import timedelta
from icmplib import async_ping
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.exceptions import ConfigEntryAuthFailed
from xbox_devportal import (
    AuthError,
    DevPortalUnreachable,
    DeviceInfo,
    SystemPerf,
    Process,
    Package,
    Setting,
)

from .const import DOMAIN, STATE_DEV, STATE_RETAIL, STATE_OFF

_LOGGER = logging.getLogger(__name__)


@dataclass
class XboxData:
    """Data class for Xbox device state and telemetry."""

    state: str
    info: DeviceInfo | None = None
    perf: SystemPerf | None = None
    foreground: Process | None = None
    sideloaded: list[Package] = field(default_factory=list)
    settings: dict[str, Setting] = field(default_factory=dict)
    screenshot: bytes | None = None
    sandbox: str | None = None


class XboxDevModeCoordinator(DataUpdateCoordinator[XboxData]):
    """Coordinator for Xbox Dev Mode integration.

    Implements tri-state logic:
    - No ping response → STATE_OFF
    - Ping ok but Device Portal unreachable → STATE_RETAIL
    - Device Portal responsive → STATE_DEV (with full telemetry)
    """

    def __init__(self, hass, client, host, scan, shot, settings_iv, entry=None):
        """Initialize coordinator.

        Args:
            hass: Home Assistant instance
            client: XboxDevPortal client instance
            host: Device IP address
            scan: Scan interval in seconds
            shot: Screenshot interval in seconds
            settings_iv: Settings fetch interval in seconds
            entry: Config entry (optional, for first refresh)
        """
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=scan), config_entry=entry
        )
        self.client = client
        self._host = host
        self._shot_iv = shot
        self._settings_iv = settings_iv
        self._tick = 0
        self._last_settings: dict = {}
        self._last_shot: bytes | None = None
        self._last_sandbox: str | None = None
        self.selected_app: str | None = None

    def _due(self, interval: int) -> bool:
        """Check if an interval-based collection is due this update cycle.

        Args:
            interval: Target interval in seconds (0 = never).

        Returns:
            True if this tick is a collection cycle for the interval.
        """
        if not interval:
            return False
        every = max(1, interval // (self.update_interval.total_seconds() or 30))
        return self._tick % every == 0

    async def _async_update_data(self) -> XboxData:
        """Fetch device state and telemetry.

        Tri-state detection, portal first:
        1. Call info(). If it answers, the console is in Dev Mode — done.
        2. Only if the portal fails, ping to tell RETAIL (host up) from OFF (host down).

        The portal is checked first on purpose. Pinging first and short-circuiting on
        `is_alive == False` made the whole integration report OFF whenever ICMP was
        unavailable to the Home Assistant process — which is exactly what happened on a
        real install: the portal answered 401 from another machine while every entity sat
        unavailable. ICMP is a permission-sensitive side channel; the portal answering is
        the authoritative signal, so it goes first.

        Raises:
            ConfigEntryAuthFailed: If AuthError is raised by the client.

        Returns:
            XboxData with current state and telemetry.
        """
        try:
            info = await self.client.info()
        except AuthError as e:
            raise ConfigEntryAuthFailed from e
        except DevPortalUnreachable:
            # Sem portal: pode ser Retail (ligado) ou desligado. O ping decide — e se o
            # proprio ping falhar por falta de permissao, assume RETAIL, porque afirmar
            # "desligado" sem evidencia e pior que admitir incerteza.
            try:
                ping = await async_ping(self._host, count=1, timeout=1, privileged=False)
            except Exception:
                _LOGGER.debug("ICMP indisponivel; sem distinguir retail de desligado")
                return XboxData(state=STATE_RETAIL)
            return XboxData(state=STATE_RETAIL if ping.is_alive else STATE_OFF)

        # Step 3: Device Portal is responsive; fetch full telemetry
        perf = await self.client.system_perf()
        fg = await self.client.foreground_app()
        side = await self.client.packages(sideloaded_only=True)

        # Auto-select first sideloaded app if none selected
        if self.selected_app is None and side:
            self.selected_app = side[0].name

        # Fetch settings on cadence
        if self._due(self._settings_iv):
            self._last_settings = await self.client.settings()

        # Fetch screenshot on cadence
        if self._due(self._shot_iv):
            self._last_shot = await self.client.screenshot()

        # Fetch sandbox mode on settings cadence (rarely changes). Cached like
        # settings/screenshot so the sensor doesn't flicker to unknown between
        # cadence ticks (it used to be reset to None every cycle).
        if self._due(self._settings_iv):
            self._last_sandbox = await self.client.sandbox()

        # Advance cadence tick only after a successful dev-mode cycle, and
        # after the _due() checks above (so tick 0 = first cycle = due).
        self._tick += 1

        return XboxData(
            state=STATE_DEV,
            info=info,
            perf=perf,
            foreground=fg,
            sideloaded=side,
            settings=self._last_settings,
            screenshot=self._last_shot,
            sandbox=self._last_sandbox,
        )
