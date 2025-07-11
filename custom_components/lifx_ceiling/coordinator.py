"""LIFX Ceiling Extras data update coordinator."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from awesomeversion import AwesomeVersion
from homeassistant.components.lifx.util import async_execute_lifx
from homeassistant.components.light import ATTR_TRANSITION
from homeassistant.const import ATTR_DEVICE_ID, MAJOR_VERSION, MINOR_VERSION
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import LIFXCeiling
from .const import (
    _LOGGER,
    ATTR_DOWNLIGHT_BRIGHTNESS,
    ATTR_DOWNLIGHT_HUE,
    ATTR_DOWNLIGHT_KELVIN,
    ATTR_DOWNLIGHT_SATURATION,
    ATTR_UPLIGHT_BRIGHTNESS,
    ATTR_UPLIGHT_HUE,
    ATTR_UPLIGHT_KELVIN,
    ATTR_UPLIGHT_SATURATION,
    DOMAIN,
)
from .util import find_lifx_coordinators

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from homeassistant.components.lifx.coordinator import LIFXUpdateCoordinator
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall


type LIFXCeilingConfigEntry = ConfigEntry[LIFXCeilingUpdateCoordinator]


class LIFXCeilingUpdateCoordinator(DataUpdateCoordinator[list[LIFXCeiling]]):
    """LIFX Ceiling data update coordinator."""

    config_entry: LIFXCeilingConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: LIFXCeilingConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            config_entry=config_entry,
            name="LIFX Ceiling",
        )

        self.stop_discovery: Callable[[], None] | None = None
        self._discovery_callback: Callable[[LIFXCeiling], None] | None = None
        self._ceiling_coordinators: dict[str, LIFXUpdateCoordinator] = {}
        self._ceilings: set[LIFXCeiling] = set()
        self._hass_version = AwesomeVersion(f"{MAJOR_VERSION}.{MINOR_VERSION}")

    @property
    def devices(self) -> list[LIFXCeiling]:
        """Return a list of instantiated LIFX Ceiling devices."""
        return list(self._ceilings)

    @property
    def discovery_callback(self) -> Callable[[LIFXCeiling], None] | None:
        """Return the discovery callback for the LIFX Ceiling Finder."""
        return self._discovery_callback

    @callback
    def set_discovery_callback(
        self, callback: Callable[[LIFXCeiling], None]
    ) -> Callable[[LIFXCeiling], None]:
        """Set the discovery callback for the LIFX Ceiling Finder."""
        old_callback = self._discovery_callback
        self._discovery_callback = callback
        return old_callback

    def async_add_core_listener(
        self, device: LIFXCeiling, callback: Callable[[], None]
    ) -> None:
        """Set the update listener for the LIFX Ceiling Finder."""
        self._ceiling_coordinators[device.mac_addr].async_add_listener(callback)

    async def async_update(self, update_time: datetime | None = None) -> None:
        """Fetch new LIFX Ceiling coordinators from the core integration."""
        _LOGGER.debug("Looking for new LIFX Ceiling devices")

        lifx_coordinators = [
            coordinator
            for coordinator in find_lifx_coordinators(self.hass)
            if coordinator.device.mac_addr not in self._ceiling_coordinators
        ]

        for coordinator in lifx_coordinators:
            # Cast the existing connection to a LIFX Ceiling objects
            ceiling = LIFXCeiling.cast(coordinator.device)
            self._ceiling_coordinators[ceiling.mac_addr] = coordinator

            self._ceilings.add(ceiling)

            if self._discovery_callback and callable(self._discovery_callback):
                self._discovery_callback(ceiling)

    async def async_set_state(self, call: ServiceCall) -> None:
        """Handle the set_state service call."""
        device_ids = call.data.get(ATTR_DEVICE_ID)
        if not isinstance(device_ids, list):
            device_ids = [device_ids]

        transition = call.data.get(ATTR_TRANSITION, 0)

        for device_id in device_ids:
            device_registry = dr.async_get(self.hass)
            device_entry = device_registry.async_get(device_id)

            device: LIFXCeiling | None = None
            for identifier in device_entry.identifiers:
                if (
                    identifier[0] == DOMAIN
                    and identifier[1] in self._ceiling_coordinators
                ):
                    device = self._ceiling_coordinators.get(identifier[1]).device

            if device is not None and isinstance(device, LIFXCeiling):
                current_downlight_color = device.downlight_color
                current_uplight_color = device.uplight_color

                downlight_hue = (
                    call.data.get(ATTR_DOWNLIGHT_HUE, current_downlight_color[0])
                    / 360
                    * 65535
                )
                downlight_saturation = (
                    call.data.get(
                        ATTR_DOWNLIGHT_SATURATION, current_downlight_color[1]
                    )
                    / 100
                    * 65535
                )
                downlight_brightness = (
                    call.data.get(
                        ATTR_DOWNLIGHT_BRIGHTNESS, current_downlight_color[2]
                    )
                    / 100
                    * 65535
                )
                downlight_kelvin = call.data.get(
                    ATTR_DOWNLIGHT_KELVIN, current_downlight_color[3]
                )

                uplight_hue = (
                    call.data.get(ATTR_UPLIGHT_HUE, current_uplight_color[0])
                    / 360
                    * 65535
                )
                uplight_saturation = (
                    call.data.get(ATTR_UPLIGHT_SATURATION, current_uplight_color[1])
                    / 100
                    * 65535
                )
                uplight_brightness = (
                    call.data.get(ATTR_UPLIGHT_BRIGHTNESS, current_uplight_color[2])
                    / 100
                    * 65535
                )
                uplight_kelvin = call.data.get(
                    ATTR_UPLIGHT_KELVIN, current_uplight_color[3]
                )

                device.configured_downlight_brightness = downlight_brightness
                device.configured_uplight_brightness = uplight_brightness

                if not device.downlight_is_on:
                    downlight_brightness = 0

                if not device.uplight_is_on:
                    uplight_brightness = 0

                downlight_color = (
                    downlight_hue,
                    downlight_saturation,
                    downlight_brightness,
                    downlight_kelvin,
                )
                uplight_color = (
                    uplight_hue,
                    uplight_saturation,
                    uplight_brightness,
                    uplight_kelvin,
                )

                final_colors = [downlight_color] * 63 + [uplight_color]

                if downlight_brightness == 0 and uplight_brightness == 0:
                    await async_execute_lifx(
                        partial(device.set_power, value="off", duration=transition)
                    )
                else:
                    device.set64(
                        tile_index=0,
                        x=0,
                        y=0,
                        width=8,
                        duration=transition,
                        colors=final_colors,
                    )

    async def turn_uplight_on(
        self, device: LIFXCeiling, color: tuple[int, int, int, int], duration: int = 0
    ) -> None:
        """Turn on the uplight."""
        await device.turn_uplight_on(color, duration)
        await self._ceiling_coordinators[device.mac_addr].async_request_refresh()

    async def turn_uplight_off(self, device: LIFXCeiling, duration: int = 0) -> None:
        """Turn off the uplight."""
        await device.turn_uplight_off(duration)
        await self._ceiling_coordinators[device.mac_addr].async_request_refresh()

    async def turn_downlight_on(
        self, device: LIFXCeiling, color: tuple[int, int, int, int], duration: int = 0
    ) -> None:
        """Turn on the downlight."""
        await device.turn_downlight_on(color, duration)
        await self._ceiling_coordinators[device.mac_addr].async_request_refresh()

    async def turn_downlight_off(self, device: LIFXCeiling, duration: int = 0) -> None:
        """Turn off the downlight."""
        await device.turn_downlight_off(duration)
        await self._ceiling_coordinators[device.mac_addr].async_request_refresh()
