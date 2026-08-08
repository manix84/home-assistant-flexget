"""Binary sensors for FlexGet."""

from datetime import timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

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
            FlexGetAcceptanceActivityBinarySensor(entry),
            FlexGetIRCHealthyBinarySensor(entry),
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


class FlexGetAcceptanceActivityBinarySensor(FlexGetEntity, BinarySensorEntity):
    """Report whether FlexGet accepted an entry in the last 24 hours."""

    entity_description = BinarySensorEntityDescription(
        key="acceptance_activity",
        translation_key="acceptance_activity",
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    def __init__(self, entry: FlexGetConfigEntry) -> None:
        super().__init__(entry, self.entity_description.key)

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if not data or not data.last_accepted_at:
            return None
        parsed = dt_util.parse_datetime(data.last_accepted_at)
        if not parsed:
            return None
        return dt_util.utcnow() - dt_util.as_utc(parsed) <= timedelta(hours=24)


class FlexGetIRCHealthyBinarySensor(FlexGetEntity, BinarySensorEntity):
    """Report whether every configured IRC connection is alive."""

    entity_description = BinarySensorEntityDescription(
        key="irc_healthy",
        translation_key="irc_healthy",
        device_class="connectivity",
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    def __init__(self, entry: FlexGetConfigEntry) -> None:
        super().__init__(entry, self.entity_description.key)

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        return data.inventory.irc_healthy if data else None
