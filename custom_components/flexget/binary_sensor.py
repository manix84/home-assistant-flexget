"""Binary sensors for FlexGet."""

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
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
    async_add_entities(
        [
            FlexGetConnectivityBinarySensor(entry),
            FlexGetTaskRunningBinarySensor(entry),
            FlexGetUpdateAvailableBinarySensor(entry),
            FlexGetLastExecutionSucceededBinarySensor(entry),
            FlexGetFailedEntriesBinarySensor(entry),
            FlexGetSchedulerEnabledBinarySensor(entry),
            FlexGetApprovalRequiredBinarySensor(entry),
        ]
    )


class FlexGetConnectivityBinarySensor(FlexGetEntity, BinarySensorEntity):
    """Report whether the authenticated API is reachable."""

    entity_description = BinarySensorEntityDescription(
        key="connectivity",
        translation_key="connectivity",
        device_class="connectivity",
    )

    def __init__(self, entry: FlexGetConfigEntry) -> None:
        super().__init__(entry, self.entity_description.key)

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def available(self) -> bool:
        return True


class FlexGetTaskRunningBinarySensor(FlexGetEntity, BinarySensorEntity):
    """Report whether FlexGet is currently executing a task."""

    entity_description = BinarySensorEntityDescription(
        key="task_running",
        translation_key="task_running",
        device_class="running",
    )

    def __init__(self, entry: FlexGetConfigEntry) -> None:
        super().__init__(entry, self.entity_description.key)

    @property
    def is_on(self) -> bool:
        return self.coordinator.data is not None and self.coordinator.data.active_task is not None


class FlexGetUpdateAvailableBinarySensor(FlexGetEntity, BinarySensorEntity):
    """Report whether FlexGet advertises a newer release."""

    entity_description = BinarySensorEntityDescription(
        key="update_available",
        translation_key="update_available",
        device_class="update",
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    def __init__(self, entry: FlexGetConfigEntry) -> None:
        super().__init__(entry, self.entity_description.key)

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if data is None or data.latest_version is None:
            return None
        return data.version != data.latest_version


class FlexGetLastExecutionSucceededBinarySensor(FlexGetEntity, BinarySensorEntity):
    """Report the outcome of the most recent task execution."""

    entity_description = BinarySensorEntityDescription(
        key="last_execution_succeeded",
        translation_key="last_execution_succeeded",
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    def __init__(self, entry: FlexGetConfigEntry) -> None:
        super().__init__(entry, self.entity_description.key)

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        return data.last_execution.succeeded if data and data.last_execution else None


class FlexGetFailedEntriesBinarySensor(FlexGetEntity, BinarySensorEntity):
    """Report whether FlexGet has entries awaiting retry."""

    entity_description = BinarySensorEntityDescription(
        key="failed_entries",
        translation_key="failed_entries",
        device_class="problem",
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    def __init__(self, entry: FlexGetConfigEntry) -> None:
        super().__init__(entry, self.entity_description.key)

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        return (
            bool(data.failed_entries.count)
            if data and data.failed_entries.count is not None
            else None
        )


class FlexGetSchedulerEnabledBinarySensor(FlexGetEntity, BinarySensorEntity):
    """Report whether the daemon has active schedules."""

    entity_description = BinarySensorEntityDescription(
        key="scheduler_enabled",
        translation_key="scheduler_enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    def __init__(self, entry: FlexGetConfigEntry) -> None:
        super().__init__(entry, self.entity_description.key)

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        return data.scheduler_enabled if data else None


class FlexGetApprovalRequiredBinarySensor(FlexGetEntity, BinarySensorEntity):
    """Report whether entries are waiting for manual approval."""

    entity_description = BinarySensorEntityDescription(
        key="approval_required",
        translation_key="approval_required",
        device_class="problem",
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    def __init__(self, entry: FlexGetConfigEntry) -> None:
        super().__init__(entry, self.entity_description.key)

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        count = data.pending_approvals.count if data else None
        return bool(count) if count is not None else None
