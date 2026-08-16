from urllib.parse import urlparse
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from xbox_devportal import XboxDevPortal, AuthError, DevPortalUnreachable
from .const import (DOMAIN, DEFAULT_PORT, CONF_SCAN_INTERVAL, CONF_SCREENSHOT_INTERVAL,
                    CONF_SETTINGS_INTERVAL, DEFAULT_SCAN_INTERVAL,
                    DEFAULT_SCREENSHOT_INTERVAL, DEFAULT_SETTINGS_INTERVAL)

_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str, vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str})


class XboxDevModeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._discovered = {}

    async def _validate(self, data):
        client = XboxDevPortal(data[CONF_HOST], data[CONF_USERNAME],
                               data[CONF_PASSWORD], port=data[CONF_PORT])
        try:
            await client.info()
        finally:
            await client.close()

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                await self._validate(user_input)
            except AuthError:
                errors["base"] = "invalid_auth"
            except DevPortalUnreachable:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(
                    self._discovered.get("udn") or f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}",
                    raise_on_progress=False)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"Xbox ({user_input[CONF_HOST]})", data=user_input)
        schema = self.add_suggested_values_to_schema(_SCHEMA, self._discovered.get("suggest", {}))
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_ssdp(self, discovery_info):
        host = urlparse(discovery_info.ssdp_location or "").hostname or ""
        self._discovered = {"udn": discovery_info.ssdp_udn, "suggest": {CONF_HOST: host}}
        await self.async_set_unique_id(discovery_info.ssdp_udn)
        self._abort_if_unique_id_configured()
        return await self.async_step_user()

    async def async_step_dhcp(self, discovery_info):
        self._discovered = {"suggest": {CONF_HOST: discovery_info.ip}}
        return await self.async_step_user()

    async def async_step_reauth(self, entry_data):
        return await self.async_step_user()

    @staticmethod
    def async_get_options_flow(entry):
        return XboxDevModeOptionsFlow(entry)


class XboxDevModeOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self._entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        o = self._entry.options
        schema = vol.Schema({
            vol.Optional(CONF_SCAN_INTERVAL, default=o.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): int,
            vol.Optional(CONF_SCREENSHOT_INTERVAL, default=o.get(CONF_SCREENSHOT_INTERVAL, DEFAULT_SCREENSHOT_INTERVAL)): int,
            vol.Optional(CONF_SETTINGS_INTERVAL, default=o.get(CONF_SETTINGS_INTERVAL, DEFAULT_SETTINGS_INTERVAL)): int})
        return self.async_show_form(step_id="init", data_schema=schema)
