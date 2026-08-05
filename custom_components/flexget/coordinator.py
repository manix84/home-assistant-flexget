"""Shared polling coordinator for FlexGet entities."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import FlexGetAuthenticationError, FlexGetClient, FlexGetError
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, EXTENDED_UPDATE_INTERVAL
from .models import (
    ActiveTask,
    FlexGetData,
    count_tasks,
    parse_history_summary,
    parse_queue,
    parse_queued_task_names,
    parse_schedules,
    parse_task_names,
    parse_version,
)

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
        self._extended_updated_at: datetime | None = None
        self._schedules_data: Any = []
        self._history_data: tuple[Any, int | None] = ([], None)

    async def _async_update_data(self) -> FlexGetData:
        now = dt_util.utcnow()
        try:
            version_data, tasks_data, queue_data = await asyncio.gather(
                self.client.async_get_version(),
                self.client.async_get_tasks(),
                self.client.async_get_queue(),
            )
            await self._async_refresh_extended_data(now)
        except FlexGetAuthenticationError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise UpdateFailed("Authentication failed") from err
        except FlexGetError as err:
            raise UpdateFailed(str(err)) from err

        version, latest, api_version = parse_version(version_data)
        queued_count, active = parse_queue(queue_data)
        schedule_count, scheduled_tasks = parse_schedules(self._schedules_data)
        history_payload, history_total = self._history_data
        accepted_count, last_accepted_task, last_accepted_at = parse_history_summary(
            history_payload, history_total
        )
        active = self._with_state_since(active, now)
        return FlexGetData(
            version=version,
            latest_version=latest,
            api_version=api_version,
            task_count=count_tasks(tasks_data),
            configured_tasks=parse_task_names(tasks_data),
            queued_count=queued_count,
            queued_tasks=parse_queued_task_names(queue_data),
            active_task=active,
            schedule_count=schedule_count,
            scheduled_tasks=scheduled_tasks,
            accepted_count=accepted_count,
            last_accepted_task=last_accepted_task,
            last_accepted_at=last_accepted_at,
            last_success=now,
        )

    async def _async_refresh_extended_data(self, now: datetime) -> None:
        """Refresh slower-changing metadata without affecting availability."""
        if (
            self._extended_updated_at is not None
            and now - self._extended_updated_at < EXTENDED_UPDATE_INTERVAL
        ):
            return
        try:
            schedules, history = await asyncio.gather(
                self.client.async_get_schedules(),
                self.client.async_get_history_summary(),
            )
        except FlexGetAuthenticationError:
            raise
        except FlexGetError as err:
            _LOGGER.debug("Unable to refresh extended FlexGet data: %s", err)
            return
        self._schedules_data = schedules
        self._history_data = history
        self._extended_updated_at = now

    def _with_state_since(self, active: ActiveTask | None, now: datetime) -> ActiveTask | None:
        signature = active.signature if active else None
        if signature != self._active_signature:
            self._active_signature = signature
            self._active_since = now if active else None
        return replace(active, state_since=self._active_since) if active else None
