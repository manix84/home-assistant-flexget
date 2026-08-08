"""Opt-in task action buttons for FlexGet."""

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FlexGetConfigEntry
from .entity import FlexGetEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FlexGetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create task buttons only after controls are explicitly enabled."""
    coordinator = entry.runtime_data
    if not coordinator.controls_enabled or not coordinator.data:
        return
    async_add_entities(
        FlexGetRunTaskButton(entry, control.name) for control in coordinator.data.task_controls
    )


class FlexGetRunTaskButton(FlexGetEntity, ButtonEntity):
    """Queue an explicit execution of one configured task."""

    entity_description = ButtonEntityDescription(
        key="run_task",
        translation_key="run_task",
        entity_category=EntityCategory.CONFIG,
    )

    def __init__(self, entry: FlexGetConfigEntry, task_name: str) -> None:
        super().__init__(entry, f"run_task_{task_name}")
        self._task_name = task_name
        self._attr_translation_placeholders = {"task": task_name}

    async def async_press(self) -> None:
        """Queue this task through the shared coordinator control path."""
        await self.coordinator.async_execute_task(self._task_name)
