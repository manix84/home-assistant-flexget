"""Diagnostics support for FlexGet."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import FlexGetConfigEntry
from .const import CONF_TOKEN

TO_REDACT = {CONF_TOKEN}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: FlexGetConfigEntry
) -> dict[str, Any]:
    """Return credential-safe diagnostics for a FlexGet entry."""
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "entry": async_redact_data(
            {"data": dict(entry.data), "options": dict(entry.options)}, TO_REDACT
        ),
        "last_update_success": coordinator.last_update_success,
        "data": (
            {
                "version": data.version,
                "latest_version": data.latest_version,
                "api_version": data.api_version,
                "task_count": data.task_count,
                "configured_tasks": data.configured_tasks,
                "queued_count": data.queued_count,
                "queued_tasks": data.queued_tasks,
                "active_task": data.active_task.name if data.active_task else None,
                "schedule_count": data.schedule_count,
                "scheduled_tasks": data.scheduled_tasks,
                "accepted_count": data.accepted_count,
                "last_accepted_task": data.last_accepted_task,
                "last_accepted_at": data.last_accepted_at,
                "last_execution": (
                    {
                        "task": data.last_execution.task,
                        "started_at": data.last_execution.started_at,
                        "finished_at": data.last_execution.finished_at,
                        "succeeded": data.last_execution.succeeded,
                        "produced": data.last_execution.produced,
                        "accepted": data.last_execution.accepted,
                        "rejected": data.last_execution.rejected,
                        "failed": data.last_execution.failed,
                        "abort_reason": data.last_execution.abort_reason,
                    }
                    if data.last_execution
                    else None
                ),
                "failed_entry_count": data.failed_entries.count,
                "next_retry_at": data.failed_entries.next_retry_at,
                "next_scheduled_run": data.next_scheduled_run,
                "scheduler_enabled": data.scheduler_enabled,
                "pending_approval_count": data.pending_approvals.count,
                "operational_stats": {
                    "successful_executions_24h": data.operational_stats.successful_executions,
                    "failed_executions_24h": data.operational_stats.failed_executions,
                    "accepted_24h": data.operational_stats.accepted,
                    "rejected_24h": data.operational_stats.rejected,
                    "failed_entries_24h": data.operational_stats.failed_entries,
                    "never_run_tasks": data.operational_stats.never_run_tasks,
                },
                "task_controls": [
                    {
                        "task": control.name,
                        "automatic_execution": control.automatic_execution,
                    }
                    for control in data.task_controls
                ],
                "inventory": {
                    "plugin_count": data.inventory.plugin_count,
                    "builtin_plugin_count": data.inventory.builtin_plugin_count,
                    "third_party_plugin_count": data.inventory.third_party_plugin_count,
                    "debug_plugin_count": data.inventory.debug_plugin_count,
                    "irc_connection_count": data.inventory.irc_connection_count,
                    "irc_connected_count": data.inventory.irc_connected_count,
                    "irc_connected_channel_count": data.inventory.irc_connected_channel_count,
                    "tracked_series_count": data.inventory.tracked_series_count,
                    "entry_list_count": data.inventory.entry_list_count,
                    "movie_list_count": data.inventory.movie_list_count,
                    "pending_list_count": data.inventory.pending_list_count,
                },
                "response_time_ms": data.response_time_ms,
                "consecutive_failures": coordinator.consecutive_failures,
                "last_success": data.last_success.isoformat(),
            }
            if data
            else None
        ),
    }
