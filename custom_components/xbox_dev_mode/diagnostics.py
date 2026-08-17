"""Diagnostics for Xbox Dev Mode integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

# Fields to redact in config entry data
REDACT_CONFIG = {"password"}

# Fields to redact in coordinator data
REDACT_COORDINATOR = {"password"}


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

    # Try to redact SMB credentials if the client exposes them
    try:
        if hasattr(coordinator.client, "smb_credentials"):
            smb_creds = coordinator.client.smb_credentials()
            if isinstance(smb_creds, dict):
                diag["smb_credentials"] = async_redact_data(smb_creds, {"password", "passwd"})
    except Exception:
        # Ignore errors trying to fetch SMB credentials
        pass

    return diag
