"""Opt-in task action buttons for FlexGet."""

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FlexGetConfigEntry
from .entity import FlexGetEntity


@dataclass(frozen=True, kw_only=True)
class FlexGetTaskButtonDescription(ButtonEntityDescription):
    """Describe one supported FlexGet task execution mode."""

    now: bool = False
    learn: bool = False


DESCRIPTIONS = (
    FlexGetTaskButtonDescription(key="run_task", translation_key="run_task"),
    FlexGetTaskButtonDescription(key="run_task_now", translation_key="run_task_now", now=True),
    FlexGetTaskButtonDescription(key="learn_task", translation_key="learn_task", learn=True),
)


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
        FlexGetRunTaskButton(entry, control.name, description)
        for control in coordinator.data.task_controls
        for description in DESCRIPTIONS
    )


class FlexGetRunTaskButton(FlexGetEntity, ButtonEntity):
    """Queue an explicit execution of one configured task."""

    entity_description: FlexGetTaskButtonDescription

    def __init__(
        self,
        entry: FlexGetConfigEntry,
        task_name: str,
        description: FlexGetTaskButtonDescription,
    ) -> None:
        super().__init__(entry, f"{description.key}_{task_name}")
        self.entity_description = description
        self._attr_entity_category = EntityCategory.CONFIG
        self._task_name = task_name
        self._attr_translation_placeholders = {"task": task_name}

    async def async_press(self) -> None:
        """Queue this task through the shared coordinator control path."""
        await self.coordinator.async_execute_task(
            self._task_name,
            now=self.entity_description.now,
            learn=self.entity_description.learn,
        )
