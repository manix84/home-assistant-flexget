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
    coordinator = FlexGetCoordinator(hass, entry, client)

    data = await coordinator._async_update_data()
    assert data.version == "3.15.31"
    assert data.task_count == 2
    assert data.queued_count == 1
    assert data.active_task is not None
    assert data.active_task.name == "anime"
    assert data.active_task.state_since is not None


async def test_unavailable_instance_raises_update_failed(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="Offline", data={})
    entry.add_to_hass(hass)
    client = AsyncMock()
    client.async_get_version.side_effect = FlexGetConnectionError("offline")
    coordinator = FlexGetCoordinator(hass, entry, client)

    with pytest.raises(UpdateFailed, match="offline"):
        await coordinator._async_update_data()
