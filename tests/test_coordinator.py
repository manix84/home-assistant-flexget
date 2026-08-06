"""Tests for coordinator updates and failure isolation."""

from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.flexget.api import FlexGetConnectionError
from custom_components.flexget.const import DOMAIN
from custom_components.flexget.coordinator import FlexGetCoordinator


async def test_coordinator_builds_shared_snapshot(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="Anime", data={})
    entry.add_to_hass(hass)
    client = AsyncMock()
    client.async_get_version.return_value = {
        "flexget_version": "3.15.31",
        "latest_version": "3.16.0",
        "api_version": "1.8",
    }
    client.async_get_tasks.return_value = [{"name": "a"}, {"name": "b"}]
    client.async_get_queue.return_value = {
        "queued": [{"name": "next"}],
        "active": {"name": "anime", "phase": "input", "plugin": "rss"},
    }
    client.async_get_schedules.return_value = [{"tasks": ["a", "b"], "interval": {"minutes": 5}}]
    client.async_get_history_summary.return_value = (
        [{"task": "a", "time": "2026-08-05T13:05:49.010966"}],
        42,
    )
    client.async_get_task_status.return_value = [
        {
            "name": "a",
            "last_execution": {
                "start": "2026-08-05T13:00:00+00:00",
                "end": "2026-08-05T13:00:05+00:00",
                "succeeded": False,
                "produced": 4,
                "accepted": 2,
                "rejected": 1,
                "failed": 1,
                "abort_reason": "output failed",
            },
        }
    ]
    client.async_get_failed_summary.return_value = (
        [
            {
                "title": "Example entry",
                "added_at": "2026-08-05T13:01:00+00:00",
                "reason": "download failed",
                "count": 2,
                "retry_time": "2026-08-05T14:00:00+00:00",
            }
        ],
        3,
    )
    client.async_get_pending_approval_summary.return_value = (
        [{"added": "2026-08-05T12:00:00+00:00"}],
        2,
    )
    client.async_get_schedule_details.return_value = [
        {"next_run_time": "2026-08-05T14:30:00+00:00"}
    ]
    coordinator = FlexGetCoordinator(hass, entry, client)

    data = await coordinator._async_update_data()
    assert data.version == "3.15.31"
    assert data.task_count == 2
    assert data.configured_tasks == ("a", "b")
    assert data.queued_count == 1
    assert data.queued_tasks == ("next",)
    assert data.active_task is not None
    assert data.active_task.name == "anime"
    assert data.active_task.state_since is not None
    assert data.schedule_count == 1
    assert data.scheduled_tasks == ("a", "b")
    assert data.accepted_count == 42
    assert data.last_accepted_task == "a"
    assert data.last_accepted_at == "2026-08-05T13:05:49.010966"
    assert data.last_execution is not None
    assert data.last_execution.accepted == 2
    assert data.latest_failed_execution == data.last_execution
    assert data.failed_entries.count == 3
    assert data.pending_approvals.count == 2
    assert data.next_scheduled_run == "2026-08-05T14:30:00+00:00"

    await coordinator._async_update_data()
    client.async_get_schedules.assert_awaited_once()
    client.async_get_history_summary.assert_awaited_once()


async def test_unavailable_instance_raises_update_failed(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="Offline", data={})
    entry.add_to_hass(hass)
    client = AsyncMock()
    client.async_get_version.side_effect = FlexGetConnectionError("offline")
    coordinator = FlexGetCoordinator(hass, entry, client)

    with pytest.raises(UpdateFailed, match="offline"):
        await coordinator._async_update_data()
    assert coordinator.consecutive_failures == 1
    assert coordinator.last_failure is not None


async def test_extended_endpoint_failure_does_not_hide_core_status(hass: HomeAssistant) -> None:
    """Keep the instance available when optional metadata cannot be read."""
    entry = MockConfigEntry(domain=DOMAIN, title="Limited", data={})
    entry.add_to_hass(hass)
    client = AsyncMock()
    client.async_get_version.return_value = {"flexget_version": "3.19.31"}
    client.async_get_tasks.return_value = ["sort"]
    client.async_get_queue.return_value = []
    client.async_get_schedules.side_effect = FlexGetConnectionError("not available")
    client.async_get_history_summary.return_value = ([], None)
    client.async_get_task_status.side_effect = FlexGetConnectionError("not available")
    client.async_get_failed_summary.side_effect = FlexGetConnectionError("not available")
    client.async_get_pending_approval_summary.side_effect = FlexGetConnectionError("not available")
    coordinator = FlexGetCoordinator(hass, entry, client)

    data = await coordinator._async_update_data()
    assert data.version == "3.19.31"
    assert data.task_count == 1
    assert data.schedule_count == 0
    assert data.accepted_count == 0
    assert data.failed_entries.count is None
    assert data.pending_approvals.count is None
