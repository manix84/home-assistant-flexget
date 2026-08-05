"""Base entity for the FlexGet integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FlexGetConfigEntry
from .const import DOMAIN
from .coordinator import FlexGetCoordinator


class FlexGetEntity(CoordinatorEntity[FlexGetCoordinator]):
    """Base entity tied to a FlexGet instance device."""

    _attr_has_entity_name = True

    def __init__(self, entry: FlexGetConfigEntry, key: str) -> None:
        super().__init__(entry.runtime_data)
        self._entry = entry
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=entry.title,
            manufacturer="FlexGet",
            model="FlexGet daemon",
            sw_version=(entry.runtime_data.data.version if entry.runtime_data.data else None),
            configuration_url=entry.runtime_data.client.endpoint.base_url,
        )
