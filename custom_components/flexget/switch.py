"""Opt-in automatic-execution switches for FlexGet tasks."""

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
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
    """Create task switches only after controls are explicitly enabled."""
    coordinator = entry.runtime_data
    if not coordinator.controls_enabled or not coordinator.data:
        return
    async_add_entities(
        FlexGetTaskAutomaticExecutionSwitch(entry, control.name)
        for control in coordinator.data.task_controls
    )


class FlexGetTaskAutomaticExecutionSwitch(FlexGetEntity, SwitchEntity):
    """Control whether one task may run automatically."""

    entity_description = SwitchEntityDescription(
        key="task_automatic_execution",
        translation_key="task_automatic_execution",
        entity_category=EntityCategory.CONFIG,
    )

    def __init__(self, entry: FlexGetConfigEntry, task_name: str) -> None:
        super().__init__(entry, f"task_automatic_execution_{task_name}")
        self._task_name = task_name
        self._attr_translation_placeholders = {"task": task_name}

    @property
    def is_on(self) -> bool | None:
        """Return whether automatic execution is allowed."""
        data = self.coordinator.data
        if not data:
            return None
        control = next(
            (control for control in data.task_controls if control.name == self._task_name), None
        )
        return control.automatic_execution if control else None

    async def async_turn_on(self, **kwargs: object) -> None:
        """Allow automatic execution by disabling the manual-only restriction."""
        await self.coordinator.async_set_task_automatic_execution(self._task_name, True)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Restrict the task to explicit execution."""
        await self.coordinator.async_set_task_automatic_execution(self._task_name, False)
