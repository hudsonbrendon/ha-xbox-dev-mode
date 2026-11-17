"""Diagnostics for Xbox Dev Mode integration."""
from __future__ import annotations

import dataclasses
import logging
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import STATE_DEV

_LOGGER = logging.getLogger(__name__)

# Fields to redact in config entry data
REDACT_CONFIG = {"password"}

# Fields to redact in SMB credentials
REDACT_SMB = {"password"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Redacts sensitive data like passwords and SMB credentials.
    """
    coordinator = entry.runtime_data

    # Get the coordinator's current data
    coordinator_data = coordinator.data

    # Build diagnostics dict
    diag = {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(entry.data, REDACT_CONFIG),
        },
        "coordinator_data": {
            "state": coordinator_data.state,
            "info": {
                "computer_name": coordinator_data.info.computer_name if coordinator_data.info else None,
                "os_version": coordinator_data.info.os_version if coordinator_data.info else None,
                "platform": coordinator_data.info.platform if coordinator_data.info else None,
            } if coordinator_data.info else None,
            "perf": {
                "cpu_load": coordinator_data.perf.cpu_load if coordinator_data.perf else None,
                "total_pages": coordinator_data.perf.total_pages if coordinator_data.perf else None,
                "available_pages": coordinator_data.perf.available_pages if coordinator_data.perf else None,
            } if coordinator_data.perf else None,
            "sideloaded_count": len(coordinator_data.sideloaded) if coordinator_data.sideloaded else 0,
            "settings_keys": list(coordinator_data.settings.keys()) if coordinator_data.settings else [],
            "sandbox": coordinator_data.sandbox,
        },
    }

    # Fetch and redact SMB credentials if the client exposes them. Only
    # attempt this in dev_mode: retail/off consoles don't have Device Portal
    # reachable, so the lookup would just fail (or hang) for no reason.
    if coordinator_data.state == STATE_DEV and hasattr(coordinator.client, "smb_credentials"):
        try:
            smb_creds = await coordinator.client.smb_credentials()
            # Convert dataclass to dict and redact the password field
            smb_dict = dataclasses.asdict(smb_creds)
            diag["smb_credentials"] = async_redact_data(smb_dict, REDACT_SMB)
        except AttributeError:
            _LOGGER.debug("SMB credentials not available on this device")
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Error fetching SMB credentials: %s", err)

    return diag
