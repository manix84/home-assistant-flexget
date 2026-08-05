"""Config and options flows for FlexGet."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import zeroconf
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    FlexGetAuthenticationError,
    FlexGetClient,
    FlexGetConnectionError,
    FlexGetEndpoint,
    FlexGetResponseError,
    FlexGetTimeoutError,
    FlexGetUnsupportedApiError,
    normalize_api_path,
)
from .const import (
    CONF_API_PATH,
    CONF_INSTANCE_NAME,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    DEFAULT_API_PATH,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)


def _schema(defaults: dict[str, Any], *, connection: bool = True) -> vol.Schema:
    fields: dict[vol.Marker, Any] = {}
    if connection:
        fields.update(
            {
                vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
                vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
                vol.Required(
                    CONF_API_PATH, default=defaults.get(CONF_API_PATH, DEFAULT_API_PATH)
                ): str,
            }
        )
    fields[vol.Required(CONF_TOKEN, default=defaults.get(CONF_TOKEN, ""))] = str
    fields[vol.Optional(CONF_INSTANCE_NAME, default=defaults.get(CONF_INSTANCE_NAME, ""))] = str
    return vol.Schema(fields)


class FlexGetConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle setup and discovery for one FlexGet daemon."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle manual setup."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                return await self._async_create_entry(user_input)
            except ValueError:
                errors[CONF_API_PATH] = "invalid_api_path"
            except FlexGetAuthenticationError:
                errors["base"] = "invalid_auth"
            except FlexGetTimeoutError:
                errors["base"] = "timeout"
            except FlexGetConnectionError:
                errors["base"] = "cannot_connect"
            except FlexGetUnsupportedApiError:
                errors["base"] = "unsupported_api"
            except FlexGetResponseError:
                errors["base"] = "invalid_response"
        return self.async_show_form(
            step_id="user", data_schema=_schema(user_input or {}), errors=errors
        )

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle an Avahi-advertised FlexGet daemon."""
        host = discovery_info.host.rstrip(".").lower()
        properties = discovery_info.properties
        self._discovery = {
            CONF_HOST: host,
            CONF_PORT: discovery_info.port,
            CONF_API_PATH: properties.get("path", DEFAULT_API_PATH),
            CONF_INSTANCE_NAME: properties.get("name", discovery_info.name.split(".")[0]),
        }
        await self.async_set_unique_id(FlexGetEndpoint(host, discovery_info.port).unique_id)
        self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {"name": self._discovery[CONF_INSTANCE_NAME]}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the token and confirm a discovery hint."""
        errors: dict[str, str] = {}
        if user_input is not None:
            combined = {**self._discovery, **user_input}
            try:
                return await self._async_create_entry(combined)
            except ValueError:
                errors[CONF_API_PATH] = "invalid_api_path"
            except FlexGetAuthenticationError:
                errors["base"] = "invalid_auth"
            except FlexGetTimeoutError:
                errors["base"] = "timeout"
            except FlexGetConnectionError:
                errors["base"] = "cannot_connect"
            except FlexGetUnsupportedApiError:
                errors["base"] = "unsupported_api"
            except FlexGetResponseError:
                errors["base"] = "invalid_response"
        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=_schema(self._discovery, connection=False),
            errors=errors,
            description_placeholders={
                "host": self._discovery.get(CONF_HOST, ""),
                "port": str(self._discovery.get(CONF_PORT, "")),
            },
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Start token reauthentication."""
        self._discovery = dict(entry_data)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate and save a replacement token."""
        errors: dict[str, str] = {}
        if user_input is not None:
            entry = self._get_reauth_entry()
            candidate = {**entry.data, **user_input}
            try:
                await self._async_validate(candidate)
            except FlexGetAuthenticationError:
                errors["base"] = "invalid_auth"
            except FlexGetTimeoutError:
                errors["base"] = "timeout"
            except FlexGetConnectionError:
                errors["base"] = "cannot_connect"
            except (FlexGetUnsupportedApiError, FlexGetResponseError):
                errors["base"] = "unsupported_api"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_TOKEN: user_input[CONF_TOKEN]},
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors=errors,
        )

    async def _async_create_entry(self, values: dict[str, Any]) -> ConfigFlowResult:
        host = values[CONF_HOST].strip().rstrip(".").lower()
        port = int(values[CONF_PORT])
        api_path = normalize_api_path(values.get(CONF_API_PATH, DEFAULT_API_PATH))
        normalized = {**values, CONF_HOST: host, CONF_PORT: port, CONF_API_PATH: api_path}
        endpoint = FlexGetEndpoint(host, port, api_path)
        await self.async_set_unique_id(endpoint.unique_id)
        self._abort_if_unique_id_configured()
        await self._async_validate(normalized)
        title = normalized.get(CONF_INSTANCE_NAME, "").strip() or f"FlexGet {host}:{port}"
        return self.async_create_entry(title=title, data=normalized)

    async def _async_validate(self, values: dict[str, Any]) -> dict[str, Any]:
        endpoint = FlexGetEndpoint(values[CONF_HOST], values[CONF_PORT], values[CONF_API_PATH])
        client = FlexGetClient(async_get_clientsession(self.hass), endpoint, values[CONF_TOKEN])
        return await client.async_get_version()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> FlexGetOptionsFlow:
        return FlexGetOptionsFlow(config_entry)


class FlexGetOptionsFlow(OptionsFlow):
    """Manage mutable FlexGet entry settings."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            title = user_input.pop(CONF_INSTANCE_NAME).strip()
            self.hass.config_entries.async_update_entry(
                self._entry,
                title=title or self._entry.title,
            )
            return self.async_create_entry(title="", data=user_input)

        current_token = self._entry.options.get(CONF_TOKEN, self._entry.data[CONF_TOKEN])
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_INSTANCE_NAME, default=self._entry.title): str,
                    vol.Required(CONF_TOKEN, default=current_token): str,
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self._entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=3600)),
                }
            ),
        )
