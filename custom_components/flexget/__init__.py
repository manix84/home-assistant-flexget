"""The FlexGet integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FlexGetClient, FlexGetEndpoint
from .const import CONF_API_PATH, CONF_TOKEN, DEFAULT_API_PATH, PLATFORMS
from .coordinator import FlexGetCoordinator

type FlexGetConfigEntry = ConfigEntry[FlexGetCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: FlexGetConfigEntry) -> bool:
    """Set up FlexGet from a config entry."""
    endpoint = FlexGetEndpoint(
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data.get(CONF_API_PATH, DEFAULT_API_PATH),
    )
    client = FlexGetClient(
        async_get_clientsession(hass),
        endpoint,
        entry.options.get(CONF_TOKEN, entry.data[CONF_TOKEN]),
    )
    coordinator = FlexGetCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FlexGetConfigEntry) -> bool:
    """Unload a FlexGet config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: FlexGetConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
