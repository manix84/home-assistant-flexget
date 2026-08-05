"""Binary sensors for FlexGet."""

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FlexGetConfigEntry
from .entity import FlexGetEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FlexGetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([FlexGetConnectivityBinarySensor(entry)])


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
