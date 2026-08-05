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
                "last_success": data.last_success.isoformat(),
            }
            if data
            else None
        ),
    }
