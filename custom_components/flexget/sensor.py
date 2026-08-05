"""Sensors for FlexGet."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FlexGetConfigEntry
from .const import ATTR_API_VERSION, ATTR_LATEST_VERSION, ATTR_PHASE, ATTR_PLUGIN, ATTR_STATE_SINCE
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
        value_fn=lambda data: data.version,
        attributes_fn=lambda data: {
            ATTR_LATEST_VERSION: data.latest_version,
            ATTR_API_VERSION: data.api_version,
        },
    ),
    FlexGetSensorDescription(
        key="task_count", translation_key="task_count", value_fn=lambda data: data.task_count
    ),
    FlexGetSensorDescription(
        key="queued_count", translation_key="queued_count", value_fn=lambda data: data.queued_count
    ),
    FlexGetSensorDescription(
        key="active_task",
        translation_key="active_task",
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
        key="last_successful_update",
        translation_key="last_successful_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.last_success,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FlexGetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(FlexGetSensor(entry, description) for description in DESCRIPTIONS)


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
