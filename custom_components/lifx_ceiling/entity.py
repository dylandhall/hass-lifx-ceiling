"""Support for LIFX Ceiling lights."""

from __future__ import annotations

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LIFXCeilingUpdateCoordinator


class LIFXCeilingEntity(CoordinatorEntity[LIFXCeilingUpdateCoordinator]):
    """Representation of a LIFX Ceiling entity with a coordinator."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: LIFXCeilingUpdateCoordinator) -> None:
        """Initialise the light."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.data.serial)},
            connections={(dr.CONNECTION_NETWORK_MAC, coordinator.data.serial)},
            serial_number=coordinator.data.serial.replace(":", ""),
            manufacturer="LIFX",
            name=coordinator.data.label,
            model=coordinator.data.model,
            sw_version=coordinator.data.sw_version,
            suggested_area=coordinator.data.suggested_area,
        )
