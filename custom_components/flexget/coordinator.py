"""Shared polling coordinator for FlexGet entities."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import FlexGetAuthenticationError, FlexGetClient, FlexGetError
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .models import ActiveTask, FlexGetData, count_tasks, parse_queue, parse_version

_LOGGER = logging.getLogger(__name__)


class FlexGetCoordinator(DataUpdateCoordinator[FlexGetData]):
    """Fetch one coherent snapshot for a FlexGet config entry."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: FlexGetClient,
    ) -> None:
        interval = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=interval),
        )
        self.client = client
        self._active_signature: tuple[str, str | None, str | None] | None = None
        self._active_since: datetime | None = None

    async def _async_update_data(self) -> FlexGetData:
        try:
            version_data, tasks_data, queue_data = await asyncio.gather(
                self.client.async_get_version(),
                self.client.async_get_tasks(),
                self.client.async_get_queue(),
            )
        except FlexGetAuthenticationError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise UpdateFailed("Authentication failed") from err
        except FlexGetError as err:
            raise UpdateFailed(str(err)) from err

        version, latest, api_version = parse_version(version_data)
        queued_count, active = parse_queue(queue_data)
        now = dt_util.utcnow()
        active = self._with_state_since(active, now)
        return FlexGetData(
            version=version,
            latest_version=latest,
            api_version=api_version,
            task_count=count_tasks(tasks_data),
            queued_count=queued_count,
            active_task=active,
            last_success=now,
        )

    def _with_state_since(self, active: ActiveTask | None, now: datetime) -> ActiveTask | None:
        signature = active.signature if active else None
        if signature != self._active_signature:
            self._active_signature = signature
            self._active_since = now if active else None
        return replace(active, state_since=self._active_since) if active else None
