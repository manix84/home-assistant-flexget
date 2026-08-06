"""Shared polling coordinator for FlexGet entities."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from datetime import datetime, timedelta
from time import monotonic
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
    parse_failed_summary,
    parse_history_summary,
    parse_next_scheduled_run,
    parse_operational_stats,
    parse_pending_summary,
    parse_queue,
    parse_queued_task_names,
    parse_schedules,
    parse_task_names,
    parse_task_status,
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
        self._schedules_data: Any = None
        self._history_data: tuple[Any, int | None] = ([], None)
        self._task_status_data: Any = []
        self._failed_data: tuple[Any, int | None] = (None, None)
        self._pending_data: tuple[Any, int | None] = (None, None)
        self._schedule_details: Any = []
        self._recent_executions: Any = None
        self.consecutive_failures = 0
        self.last_failure: datetime | None = None

    async def _async_update_data(self) -> FlexGetData:
        now = dt_util.utcnow()
        started = monotonic()
        try:
            version_data, tasks_data, queue_data = await asyncio.gather(
                self.client.async_get_version(),
                self.client.async_get_tasks(),
                self.client.async_get_queue(),
            )
            await self._async_refresh_extended_data(now)
        except FlexGetAuthenticationError as err:
            self._record_failure(now)
            self.config_entry.async_start_reauth(self.hass)
            raise UpdateFailed("Authentication failed") from err
        except FlexGetError as err:
            self._record_failure(now)
            raise UpdateFailed(str(err)) from err

        version, latest, api_version = parse_version(version_data)
        queued_count, active = parse_queue(queue_data)
        schedule_count, scheduled_tasks = parse_schedules(self._schedules_data)
        history_payload, history_total = self._history_data
        accepted_count, last_accepted_task, last_accepted_at = parse_history_summary(
            history_payload, history_total
        )
        last_execution, latest_failed_execution = parse_task_status(self._task_status_data)
        failed_payload, failed_total = self._failed_data
        pending_payload, pending_total = self._pending_data
        active = self._with_state_since(active, now)
        self.consecutive_failures = 0
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
            last_execution=last_execution,
            latest_failed_execution=latest_failed_execution,
            failed_entries=parse_failed_summary(failed_payload, failed_total, now),
            next_scheduled_run=parse_next_scheduled_run(self._schedule_details),
            scheduler_enabled=self._scheduler_enabled(),
            pending_approvals=parse_pending_summary(pending_payload, pending_total),
            operational_stats=parse_operational_stats(
                self._task_status_data, self._recent_executions
            ),
            response_time_ms=round((monotonic() - started) * 1000),
            last_success=now,
        )

    async def _async_refresh_extended_data(self, now: datetime) -> None:
        """Refresh slower-changing metadata without affecting availability."""
        if (
            self._extended_updated_at is not None
            and now - self._extended_updated_at < EXTENDED_UPDATE_INTERVAL
        ):
            return
        await asyncio.gather(
            self._async_refresh_optional("schedules", self.client.async_get_schedules),
            self._async_refresh_optional("history", self.client.async_get_history_summary),
            self._async_refresh_optional("task status", self.client.async_get_task_status),
            self._async_refresh_optional("failed entries", self.client.async_get_failed_summary),
            self._async_refresh_optional(
                "pending approvals", self.client.async_get_pending_approval_summary
            ),
        )
        if self._schedules_data:
            await self._async_refresh_optional(
                "schedule details",
                lambda: self.client.async_get_schedule_details(self._schedules_data),
            )
        if self._task_status_data:
            await self._async_refresh_optional(
                "recent executions",
                lambda: self.client.async_get_recent_executions(
                    self._task_status_data, now - timedelta(hours=24)
                ),
            )
        self._extended_updated_at = now

    async def _async_refresh_optional(self, name: str, fetch: Any) -> None:
        """Refresh one optional endpoint without affecting other groups."""
        try:
            value = await fetch()
        except FlexGetAuthenticationError:
            raise
        except FlexGetError as err:
            _LOGGER.debug("Unable to refresh FlexGet %s: %s", name, err)
            return
        if name == "schedules":
            self._schedules_data = value
        elif name == "history":
            self._history_data = value
        elif name == "task status":
            self._task_status_data = value
        elif name == "failed entries":
            self._failed_data = value
        elif name == "pending approvals":
            self._pending_data = value
        elif name == "schedule details":
            self._schedule_details = value
        elif name == "recent executions":
            self._recent_executions = value

    def _scheduler_enabled(self) -> bool | None:
        if self._schedules_data is None:
            return None
        return bool(self._schedules_data)

    def _record_failure(self, now: datetime) -> None:
        self.consecutive_failures += 1
        self.last_failure = now

    def _with_state_since(self, active: ActiveTask | None, now: datetime) -> ActiveTask | None:
        signature = active.signature if active else None
        if signature != self._active_signature:
            self._active_signature = signature
            self._active_since = now if active else None
        return replace(active, state_since=self._active_since) if active else None
