"""Tests for FlexGet config flows."""

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.flexget.api import FlexGetAuthenticationError
from custom_components.flexget.const import CONF_API_PATH, CONF_INSTANCE_NAME, CONF_TOKEN, DOMAIN


async def test_manual_flow_and_multi_port_uniqueness(hass: HomeAssistant) -> None:
    with patch(
        "custom_components.flexget.config_flow.FlexGetClient.async_get_version",
        AsyncMock(return_value={"flexget_version": "3.15.31"}),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "TORBOX.local.",
                CONF_PORT: 5053,
                CONF_API_PATH: "api/",
                CONF_TOKEN: "secret",
                CONF_INSTANCE_NAME: "Anime",
            },
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "Anime"
        assert result["data"][CONF_HOST] == "torbox.local"
        assert result["data"][CONF_API_PATH] == "/api"

        second = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        second = await hass.config_entries.flow.async_configure(
            second["flow_id"],
            {
                CONF_HOST: "torbox.local",
                CONF_PORT: 5054,
                CONF_API_PATH: "/api",
                CONF_TOKEN: "different-secret",
                CONF_INSTANCE_NAME: "Movies",
            },
        )
        assert second["type"] is FlowResultType.CREATE_ENTRY


async def test_duplicate_host_port_is_rejected(hass: HomeAssistant) -> None:
    with patch(
        "custom_components.flexget.config_flow.FlexGetClient.async_get_version",
        AsyncMock(return_value={"flexget_version": "3.15.31"}),
    ):
        first = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        values = {
            CONF_HOST: "torbox.local",
            CONF_PORT: 5053,
            CONF_API_PATH: "/api",
            CONF_TOKEN: "secret",
            CONF_INSTANCE_NAME: "Anime",
        }
        await hass.config_entries.flow.async_configure(first["flow_id"], values)
        duplicate = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        duplicate = await hass.config_entries.flow.async_configure(duplicate["flow_id"], values)
        assert duplicate["type"] is FlowResultType.ABORT
        assert duplicate["reason"] == "already_configured"


async def test_invalid_token_shows_auth_error(hass: HomeAssistant) -> None:
    with patch(
        "custom_components.flexget.config_flow.FlexGetClient.async_get_version",
        AsyncMock(side_effect=FlexGetAuthenticationError),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "torbox.local",
                CONF_PORT: 5053,
                CONF_API_PATH: "/api",
                CONF_TOKEN: "bad",
                CONF_INSTANCE_NAME: "Anime",
            },
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}
