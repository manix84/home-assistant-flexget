"""Shared polling coordinator for FlexGet entities."""

from __future__ import annotations

import asyncio
import logging
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta
from time import monotonic
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import FlexGetAuthenticationError, FlexGetClient, FlexGetError, FlexGetResponseError
from .const import (
    CONF_ENABLE_CONTROLS,
    CONF_SCAN_INTERVAL,
    DEFAULT_ENABLE_CONTROLS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EXTENDED_UPDATE_INTERVAL,
)
from .models import (
    ActiveTask,
    FlexGetData,
    count_tasks,
    parse_failed_summary,
    parse_history_summary,
    parse_inventory,
    parse_next_scheduled_run,
    parse_operational_stats,
    parse_pending_summary,
    parse_queue,
    parse_queued_task_names,
    parse_schedules,
    parse_task_controls,
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
        self._history_data: tuple[Any, int | None] = (None, None)
        self._task_status_data: Any = None
        self._failed_data: tuple[Any, int | None] = (None, None)
        self._pending_data: tuple[Any, int | None] = (None, None)
        self._schedule_details: Any = None
        self._recent_executions: Any = None
        self._plugins_data: Any = None
        self._irc_data: Any = None
        self._series_count: int | None = None
        self._entry_lists_data: Any = None
        self._movie_lists_data: Any = None
        self._pending_lists_data: Any = None
        self.consecutive_failures = 0
        self.last_failure: datetime | None = None
        self.controls_enabled = bool(
            entry.options.get(CONF_ENABLE_CONTROLS, DEFAULT_ENABLE_CONTROLS)
        )
        self._control_lock = asyncio.Lock()

    async def _async_update_data(self) -> FlexGetData:
        now = dt_util.utcnow()
        started = monotonic()
        try:
            version_data, tasks_data, queue_data = await asyncio.gather(
                self.client.async_get_version(),
                self.client.async_get_tasks(include_config=self.controls_enabled),
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
            task_controls=parse_task_controls(tasks_data),
            inventory=parse_inventory(
                self._plugins_data,
                self._irc_data,
                self._series_count,
                self._entry_lists_data,
                self._movie_lists_data,
                self._pending_lists_data,
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
            self._async_refresh_optional("plugins", self.client.async_get_plugins),
            self._async_refresh_optional("IRC", self.client.async_get_irc_connections),
            self._async_refresh_optional("series count", self.client.async_get_series_count),
            self._async_refresh_optional("entry lists", self.client.async_get_entry_lists),
            self._async_refresh_optional("movie lists", self.client.async_get_movie_lists),
            self._async_refresh_optional("pending lists", self.client.async_get_pending_lists),
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
            self._set_optional_value(name, None)
            return
        self._set_optional_value(name, value)

    def _set_optional_value(self, name: str, value: Any) -> None:
        """Store optional data, clearing dependent caches when it becomes unavailable."""
        if name == "schedules":
            self._schedules_data = value
            if value is None:
                self._schedule_details = None
        elif name == "history":
            self._history_data = value if isinstance(value, tuple) else (None, None)
        elif name == "task status":
            self._task_status_data = value
            if value is None:
                self._recent_executions = None
        elif name == "failed entries":
            self._failed_data = value if isinstance(value, tuple) else (None, None)
        elif name == "pending approvals":
            self._pending_data = value if isinstance(value, tuple) else (None, None)
        elif name == "schedule details":
            self._schedule_details = value
        elif name == "recent executions":
            self._recent_executions = value
        elif name == "plugins":
            self._plugins_data = value
        elif name == "IRC":
            self._irc_data = value
        elif name == "series count":
            self._series_count = value if isinstance(value, int) else None
        elif name == "entry lists":
            self._entry_lists_data = value
        elif name == "movie lists":
            self._movie_lists_data = value
        elif name == "pending lists":
            self._pending_lists_data = value

    def _scheduler_enabled(self) -> bool | None:
        if self._schedules_data is None:
            return None
        return bool(self._schedules_data)

    def _record_failure(self, now: datetime) -> None:
        self.consecutive_failures += 1
        self.last_failure = now

    async def async_set_task_automatic_execution(self, task_name: str, enabled: bool) -> None:
        """Safely change only the task's manual execution setting."""
        self._ensure_controls_enabled()
        if self.data and self.data.active_task and self.data.active_task.name == task_name:
            raise FlexGetError("Cannot change a task while it is running")
        try:
            async with self._control_lock:
                task = await self.client.async_get_task(task_name)
                config = deepcopy(task["config"])
                config["manual"] = not enabled
                await self.client.async_update_task(task_name, config)
                confirmed = await self.client.async_get_task(task_name)
                confirmed_manual = confirmed["config"].get("manual") is True
                if confirmed_manual == enabled:
                    raise FlexGetResponseError("FlexGet did not apply the task control change")
        except FlexGetAuthenticationError:
            self.config_entry.async_start_reauth(self.hass)
            raise
        await self.async_request_refresh()

    async def async_execute_task(
        self, task_name: str, *, now: bool = False, learn: bool = False
    ) -> None:
        """Queue one explicit task execution."""
        self._ensure_controls_enabled()
        try:
            async with self._control_lock:
                await self.client.async_execute_task(task_name, now=now, learn=learn)
        except FlexGetAuthenticationError:
            self.config_entry.async_start_reauth(self.hass)
            raise
        await self.async_request_refresh()

    def _ensure_controls_enabled(self) -> None:
        if not self.controls_enabled:
            raise FlexGetError("FlexGet controls are disabled")

    def _with_state_since(self, active: ActiveTask | None, now: datetime) -> ActiveTask | None:
        signature = active.signature if active else None
        if signature != self._active_signature:
            self._active_signature = signature
            self._active_since = now if active else None
        return replace(active, state_since=self._active_since) if active else None
