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
