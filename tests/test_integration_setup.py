"""End-to-end setup tests for FlexGet entities."""

from unittest.mock import AsyncMock, patch

from homeassistant.const import CONF_HOST, CONF_PORT, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.flexget.const import CONF_API_PATH, CONF_ENABLE_CONTROLS, CONF_TOKEN, DOMAIN


async def test_entry_registers_useful_diagnostic_entities(hass: HomeAssistant) -> None:
    """Set up one entry and verify its shared snapshot entities."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Sort",
        unique_id="192.0.2.10:5051",
        data={
            CONF_HOST: "192.0.2.10",
            CONF_PORT: 5051,
            CONF_API_PATH: "/api",
            CONF_TOKEN: "secret-token",
        },
        options={CONF_ENABLE_CONTROLS: True},
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.flexget.api.FlexGetClient.async_get_version",
            AsyncMock(
                return_value={
                    "flexget_version": "3.19.31",
                    "latest_version": "3.20.0",
                    "api_version": "1.8.0",
                }
            ),
        ),
        patch(
            "custom_components.flexget.api.FlexGetClient.async_get_tasks",
            AsyncMock(
                return_value=[
                    {"name": "extract_all", "config": {"manual": True}},
                    {"name": "sort_anime", "config": {"rss": "https://example.test/feed"}},
                ]
            ),
        ),
        patch(
            "custom_components.flexget.api.FlexGetClient.async_get_queue",
            AsyncMock(return_value=[]),
        ),
        patch(
            "custom_components.flexget.api.FlexGetClient.async_get_schedules",
            AsyncMock(return_value=[{"tasks": ["extract_*", "sort_*"]}]),
        ),
        patch(
            "custom_components.flexget.api.FlexGetClient.async_get_history_summary",
            AsyncMock(
                return_value=(
                    [{"task": "sort_anime", "time": "2026-08-05T13:05:49.010966"}],
                    42,
                )
            ),
        ),
        patch(
            "custom_components.flexget.api.FlexGetClient.async_get_task_status",
            AsyncMock(
                return_value=[
                    {
                        "id": 1,
                        "name": "sort_anime",
                        "last_execution": {
                            "start": "2026-08-05T13:00:00+00:00",
                            "end": "2026-08-05T13:00:05+00:00",
                            "succeeded": True,
                            "produced": 3,
                            "accepted": 2,
                            "rejected": 1,
                            "failed": 0,
                            "abort_reason": None,
                        },
                    }
                ]
            ),
        ),
        patch(
            "custom_components.flexget.api.FlexGetClient.async_get_failed_summary",
            AsyncMock(return_value=([], 0)),
        ),
        patch(
            "custom_components.flexget.api.FlexGetClient.async_get_pending_approval_summary",
            AsyncMock(return_value=([], 0)),
        ),
        patch(
            "custom_components.flexget.api.FlexGetClient.async_get_schedule_details",
            AsyncMock(return_value=[]),
        ),
        patch(
            "custom_components.flexget.api.FlexGetClient.async_get_recent_executions",
            AsyncMock(
                return_value=[[{"succeeded": True, "accepted": 2, "rejected": 1, "failed": 0}]]
            ),
        ),
        patch(
            "custom_components.flexget.api.FlexGetClient.async_get_plugins",
            AsyncMock(
                return_value=[
                    {"name": "rss", "builtin": True, "debug": False},
                    {"name": "custom", "builtin": False, "debug": True},
                ]
            ),
        ),
        patch(
            "custom_components.flexget.api.FlexGetClient.async_get_irc_connections",
            AsyncMock(return_value=[{"announce": {"alive": True, "connected_channels": ["one"]}}]),
        ),
        patch(
            "custom_components.flexget.api.FlexGetClient.async_get_series_count",
            AsyncMock(return_value=9),
        ),
        patch(
            "custom_components.flexget.api.FlexGetClient.async_get_entry_lists",
            AsyncMock(return_value=[{"name": "entries"}]),
        ),
        patch(
            "custom_components.flexget.api.FlexGetClient.async_get_movie_lists",
            AsyncMock(return_value=[{"name": "movies"}]),
        ),
        patch(
            "custom_components.flexget.api.FlexGetClient.async_get_pending_lists",
            AsyncMock(return_value=[]),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    task_count = hass.states.get("sensor.sort_configured_tasks")
    assert task_count is not None
    assert task_count.state == "2"
    assert task_count.attributes["configured_tasks"] == ["extract_all", "sort_anime"]

    queued_count = hass.states.get("sensor.sort_queued_tasks")
    assert queued_count is not None
    assert queued_count.state == "0"
    assert hass.states.get("binary_sensor.sort_task_running").state == "off"
    assert hass.states.get("binary_sensor.sort_update_available").state == "on"
    assert hass.states.get("sensor.sort_schedules").state == "1"
    assert hass.states.get("sensor.sort_accepted_entries").state == "42"
    assert hass.states.get("sensor.sort_last_accepted_task").state == "sort_anime"
    assert hass.states.get("sensor.sort_last_executed_task").state == "sort_anime"
    assert hass.states.get("sensor.sort_last_execution_accepted").state == "2"
    assert hass.states.get("binary_sensor.sort_last_execution_succeeded").state == "on"
    assert hass.states.get("binary_sensor.sort_failed_entries_present").state == "off"
    assert hass.states.get("binary_sensor.sort_approval_required").state == "off"
    assert hass.states.get("sensor.sort_successful_executions_24_h").state == "1"
    assert hass.states.get("sensor.sort_execution_success_rate_24_h").state == "100.0"
    assert hass.states.get("switch.sort_extract_all_automatic_execution").state == "off"
    assert hass.states.get("switch.sort_sort_anime_automatic_execution").state == "on"
    assert hass.states.get("button.sort_run_extract_all") is not None
    assert hass.states.get("button.sort_run_sort_anime") is not None
    assert hass.states.get("button.sort_run_sort_anime_now") is not None
    assert hass.states.get("button.sort_learn_sort_anime") is not None
    assert hass.states.get("sensor.sort_registered_plugins").state == "2"
    assert hass.states.get("sensor.sort_third_party_plugins").state == "1"
    assert hass.states.get("binary_sensor.sort_irc_healthy").state == "on"
    assert hass.states.get("sensor.sort_tracked_series").state == "9"
    assert hass.states.get("sensor.sort_entry_lists").state == "1"

    registry = er.async_get(hass)
    assert (
        registry.async_get("switch.sort_sort_anime_automatic_execution").entity_category
        is EntityCategory.CONFIG
    )
    assert registry.async_get("button.sort_run_sort_anime").entity_category is EntityCategory.CONFIG
    assert (
        registry.async_get("button.sort_run_sort_anime_now").entity_category
        is EntityCategory.CONFIG
    )
    for entity_id in (
        "sensor.sort_configured_tasks",
        "sensor.sort_queued_tasks",
        "sensor.sort_schedules",
        "sensor.sort_accepted_entries",
    ):
        assert registry.async_get(entity_id).entity_category is EntityCategory.DIAGNOSTIC
