"""Sensors for FlexGet."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import FlexGetConfigEntry
from .const import (
    ATTR_ACCEPTED_AT,
    ATTR_API_VERSION,
    ATTR_CONFIGURED_TASKS,
    ATTR_PHASE,
    ATTR_PLUGIN,
    ATTR_QUEUED_TASKS,
    ATTR_SCHEDULED_TASKS,
    ATTR_STATE_SINCE,
)
from .entity import FlexGetEntity
from .models import FlexGetData


@dataclass(frozen=True, kw_only=True)
class FlexGetSensorDescription(SensorEntityDescription):
    value_fn: Callable[[FlexGetData], Any]
    attributes_fn: Callable[[FlexGetData], dict[str, Any]] | None = None


DESCRIPTIONS = (
    FlexGetSensorDescription(
        key="version",
        translation_key="version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.version,
        attributes_fn=lambda data: {ATTR_API_VERSION: data.api_version},
    ),
    FlexGetSensorDescription(
        key="latest_version",
        translation_key="latest_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.latest_version,
    ),
    FlexGetSensorDescription(
        key="task_count",
        translation_key="task_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        value_fn=lambda data: data.task_count,
        attributes_fn=lambda data: {ATTR_CONFIGURED_TASKS: list(data.configured_tasks)},
    ),
    FlexGetSensorDescription(
        key="queued_count",
        translation_key="queued_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        value_fn=lambda data: data.queued_count,
        attributes_fn=lambda data: {ATTR_QUEUED_TASKS: list(data.queued_tasks)},
    ),
    FlexGetSensorDescription(
        key="active_task",
        translation_key="active_task",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.active_task.name if data.active_task else None,
        attributes_fn=lambda data: (
            {
                ATTR_PHASE: data.active_task.phase,
                ATTR_PLUGIN: data.active_task.plugin,
                ATTR_STATE_SINCE: data.active_task.state_since,
            }
            if data.active_task
            else {}
        ),
    ),
    FlexGetSensorDescription(
        key="schedule_count",
        translation_key="schedule_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        value_fn=lambda data: data.schedule_count,
        attributes_fn=lambda data: {ATTR_SCHEDULED_TASKS: list(data.scheduled_tasks)},
    ),
    FlexGetSensorDescription(
        key="accepted_count",
        translation_key="accepted_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        value_fn=lambda data: data.accepted_count,
    ),
    FlexGetSensorDescription(
        key="last_accepted_task",
        translation_key="last_accepted_task",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.last_accepted_task,
        attributes_fn=lambda data: {ATTR_ACCEPTED_AT: data.last_accepted_at},
    ),
    FlexGetSensorDescription(
        key="response_time",
        translation_key="response_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        value_fn=lambda data: data.response_time_ms,
    ),
    FlexGetSensorDescription(
        key="active_task_duration",
        translation_key="active_task_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        value_fn=lambda data: (
            max(0, int((dt_util.utcnow() - data.active_task.state_since).total_seconds()))
            if data.active_task and data.active_task.state_since
            else None
        ),
    ),
    FlexGetSensorDescription(
        key="last_executed_task",
        translation_key="last_executed_task",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.last_execution.task if data.last_execution else None,
    ),
    FlexGetSensorDescription(
        key="last_execution_finished",
        translation_key="last_execution_finished",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _timestamp(
            data.last_execution.finished_at if data.last_execution else None
        ),
    ),
    FlexGetSensorDescription(
        key="last_execution_duration",
        translation_key="last_execution_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=1,
        value_fn=lambda data: _execution_duration(data),
    ),
    *(
        FlexGetSensorDescription(
            key=f"last_execution_{field}",
            translation_key=f"last_execution_{field}",
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            suggested_display_precision=0,
            value_fn=lambda data, field=field: (
                getattr(data.last_execution, field) if data.last_execution else None
            ),
        )
        for field in ("accepted", "rejected", "failed")
    ),
    FlexGetSensorDescription(
        key="latest_failed_task",
        translation_key="latest_failed_task",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.latest_failed_execution.task if data.latest_failed_execution else None
        ),
        attributes_fn=lambda data: (
            {"reason": data.latest_failed_execution.abort_reason}
            if data.latest_failed_execution
            else {}
        ),
    ),
    FlexGetSensorDescription(
        key="latest_failed_execution",
        translation_key="latest_failed_execution",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _timestamp(
            data.latest_failed_execution.finished_at if data.latest_failed_execution else None
        ),
    ),
    FlexGetSensorDescription(
        key="last_accepted_time",
        translation_key="last_accepted_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _timestamp(data.last_accepted_at),
    ),
    FlexGetSensorDescription(
        key="failed_entry_count",
        translation_key="failed_entry_count",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        value_fn=lambda data: data.failed_entries.count,
        attributes_fn=lambda data: {
            "latest_failure_at": data.failed_entries.latest_at,
            "latest_title": data.failed_entries.latest_title,
            "latest_reason": data.failed_entries.latest_reason,
            "latest_attempt_count": data.failed_entries.latest_attempt_count,
        },
    ),
    FlexGetSensorDescription(
        key="next_retry_time",
        translation_key="next_retry_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _timestamp(data.failed_entries.next_retry_at),
    ),
    FlexGetSensorDescription(
        key="next_scheduled_run",
        translation_key="next_scheduled_run",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _timestamp(data.next_scheduled_run),
    ),
    FlexGetSensorDescription(
        key="time_until_next_run",
        translation_key="time_until_next_run",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        value_fn=lambda data: _seconds_until(data.next_scheduled_run),
    ),
    FlexGetSensorDescription(
        key="pending_approval_count",
        translation_key="pending_approval_count",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        value_fn=lambda data: data.pending_approvals.count,
        attributes_fn=lambda data: {"oldest_pending_at": data.pending_approvals.oldest_at},
    ),
    *(
        FlexGetSensorDescription(
            key=f"{field}_24h",
            translation_key=f"{field}_24h",
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            suggested_display_precision=0,
            value_fn=lambda data, field=field: getattr(data.operational_stats, field),
        )
        for field in (
            "successful_executions",
            "failed_executions",
            "accepted",
            "rejected",
            "failed_entries",
        )
    ),
    FlexGetSensorDescription(
        key="execution_success_rate_24h",
        translation_key="execution_success_rate_24h",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=1,
        value_fn=lambda data: data.operational_stats.success_rate,
    ),
    FlexGetSensorDescription(
        key="never_run_task_count",
        translation_key="never_run_task_count",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        value_fn=lambda data: data.operational_stats.never_run_tasks,
    ),
    FlexGetSensorDescription(
        key="time_since_last_acceptance",
        translation_key="time_since_last_acceptance",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        value_fn=lambda data: _seconds_since(data.last_accepted_at),
    ),
    FlexGetSensorDescription(
        key="overdue_retry_count",
        translation_key="overdue_retry_count",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        value_fn=lambda data: data.failed_entries.overdue_count,
    ),
    FlexGetSensorDescription(
        key="highest_retry_count",
        translation_key="highest_retry_count",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        value_fn=lambda data: data.failed_entries.highest_attempt_count,
    ),
    FlexGetSensorDescription(
        key="oldest_pending_approval_age",
        translation_key="oldest_pending_approval_age",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        value_fn=lambda data: _seconds_since(data.pending_approvals.oldest_at),
    ),
    FlexGetSensorDescription(
        key="last_successful_update",
        translation_key="last_successful_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.last_success,
    ),
)


def _timestamp(value: str | None) -> datetime | None:
    """Parse a FlexGet timestamp using Home Assistant's configured timezone when absent."""
    parsed = dt_util.parse_datetime(value) if value else None
    return dt_util.as_utc(parsed) if parsed else None


def _execution_duration(data: FlexGetData) -> float | None:
    if not data.last_execution:
        return None
    started = _timestamp(data.last_execution.started_at)
    finished = _timestamp(data.last_execution.finished_at)
    if not started or not finished:
        return None
    return max(0, (finished - started).total_seconds())


def _seconds_until(value: str | None) -> int | None:
    timestamp = _timestamp(value)
    return max(0, int((timestamp - dt_util.utcnow()).total_seconds())) if timestamp else None


def _seconds_since(value: str | None) -> int | None:
    timestamp = _timestamp(value)
    return max(0, int((dt_util.utcnow() - timestamp).total_seconds())) if timestamp else None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FlexGetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(
        [
            *(FlexGetSensor(entry, description) for description in DESCRIPTIONS),
            FlexGetConsecutiveFailedPollsSensor(entry),
        ]
    )


class FlexGetSensor(FlexGetEntity, SensorEntity):
    """A sensor sourced from the shared coordinator snapshot."""

    entity_description: FlexGetSensorDescription

    def __init__(self, entry: FlexGetConfigEntry, description: FlexGetSensorDescription) -> None:
        super().__init__(entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> str | int | datetime | None:
        data = self.coordinator.data
        return self.entity_description.value_fn(data) if data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        if not data or not self.entity_description.attributes_fn:
            return None
        return {
            key: value
            for key, value in self.entity_description.attributes_fn(data).items()
            if value is not None
        }


class FlexGetConsecutiveFailedPollsSensor(FlexGetEntity, SensorEntity):
    """Report failures even while normal coordinator entities are unavailable."""

    entity_description = SensorEntityDescription(
        key="consecutive_failed_polls",
        translation_key="consecutive_failed_polls",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
    )

    def __init__(self, entry: FlexGetConfigEntry) -> None:
        super().__init__(entry, self.entity_description.key)

    @property
    def native_value(self) -> int:
        return self.coordinator.consecutive_failures

    @property
    def available(self) -> bool:
        return True
