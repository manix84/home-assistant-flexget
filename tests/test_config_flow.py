"""Tests for FlexGet config flows."""

from ipaddress import ip_address
from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.components.zeroconf import ZeroconfServiceInfo
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.flexget.api import FlexGetAuthenticationError
from custom_components.flexget.const import (
    CONF_API_PATH,
    CONF_ENABLE_CONTROLS,
    CONF_INSTANCE_NAME,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    DOMAIN,
)


async def test_zeroconf_discovery_uses_instance_name_for_card_title(
    hass: HomeAssistant,
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=ZeroconfServiceInfo(
            ip_address=ip_address("192.0.2.10"),
            ip_addresses=[ip_address("192.0.2.10")],
            port=5051,
            hostname="flexget.local.",
            type="_flexget._tcp.local.",
            name="FlexGet Sort._flexget._tcp.local.",
            properties={"name": "Sort", "path": "/api"},
        ),
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zeroconf_confirm"
    progress = next(
        flow
        for flow in hass.config_entries.flow.async_progress()
        if flow["flow_id"] == result["flow_id"]
    )
    assert progress["context"]["title_placeholders"] == {"name": "Sort"}


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
                CONF_HOST: "FLEXGET.local.",
                CONF_PORT: 5053,
                CONF_API_PATH: "api/",
                CONF_TOKEN: "secret",
                CONF_INSTANCE_NAME: "Anime",
            },
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "Anime"
        assert result["data"][CONF_HOST] == "flexget.local"
        assert result["data"][CONF_API_PATH] == "/api"

        second = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        second = await hass.config_entries.flow.async_configure(
            second["flow_id"],
            {
                CONF_HOST: "flexget.local",
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
            CONF_HOST: "flexget.local",
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
                CONF_HOST: "flexget.local",
                CONF_PORT: 5053,
                CONF_API_PATH: "/api",
                CONF_TOKEN: "bad",
                CONF_INSTANCE_NAME: "Anime",
            },
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}


async def test_options_require_explicit_control_opt_in(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Sort",
        data={CONF_TOKEN: "secret-token"},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["data_schema"]({})[CONF_ENABLE_CONTROLS] is False

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_INSTANCE_NAME: "Sort",
            CONF_TOKEN: "secret-token",
            CONF_SCAN_INTERVAL: 60,
            CONF_ENABLE_CONTROLS: True,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_ENABLE_CONTROLS] is True
