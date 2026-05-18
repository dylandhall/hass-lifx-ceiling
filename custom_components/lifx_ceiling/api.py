"""Extra methods for LIFX Ceiling."""

from __future__ import annotations

import asyncio
from functools import partial
from typing import TYPE_CHECKING, Any

from aiolifx.aiolifx import UDP_BROADCAST_PORT, Light
from aiolifx.products import products_dict

from .const import (
    LIFX_CEILING_128ZONES_PRODUCT_IDS,
)
from .util import async_execute_lifx

if TYPE_CHECKING:
    import asyncio

MESSAGE_TIMEOUT = 3


class LIFXCeilingError(Exception):
    """LIFX Ceiling specific exception."""


class LIFXCeiling(Light):
    """Represents a LIFX Ceiling."""

    uplight_zone: int
    downlight_zones: slice
    total_zones: int

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        mac_addr: str,
        ip_addr: str,
        port: int = UDP_BROADCAST_PORT,
        parent: Any | None = None,
    ) -> None:
        """Initialize the LIFX Ceiling."""
        super().__init__(loop, mac_addr, ip_addr, port, parent)
        self._configured_downlight_brightness: int = 0
        self._configured_uplight_brightness: int = 0
        self._is_downlight_on: bool = False
        self._is_uplight_on: bool = False

    @classmethod
    def cast(cls, device: Light) -> LIFXCeiling:
        """Cast the device to LIFXCeiling."""
        assert isinstance(device, Light)  # noqa: S101
        device.__class__ = cls
        assert isinstance(device, LIFXCeiling)  # noqa: S101
        if not hasattr(device, "_is_downlight_on"):
            try:
                downlight_brightness = (
                    max(b for _, _, b, _ in device.chain[0][device.downlight_zones])
                    >> 8
                )
                uplight_brightness = device.chain[0][device.uplight_zone][2] >> 8
            except (AttributeError, IndexError, ValueError, KeyError):
                downlight_brightness = 0
                uplight_brightness = 0
            device._configured_downlight_brightness = downlight_brightness  # noqa: SLF001
            device._configured_uplight_brightness = uplight_brightness  # noqa: SLF001
            device._is_downlight_on = bool(  # noqa: SLF001
                (device.power_level or 0) > 0 and downlight_brightness > 0
            )
            device._is_uplight_on = bool(  # noqa: SLF001
                (device.power_level or 0) > 0 and uplight_brightness > 0
            )
        return device

    @property
    def total_zones(self) -> int:
        """Return the total number of zones."""
        if self.product in LIFX_CEILING_128ZONES_PRODUCT_IDS:
            return 128
        return 64

    @property
    def uplight_zone(self) -> int:
        """Return the uplight zone index."""
        if self.product in LIFX_CEILING_128ZONES_PRODUCT_IDS:
            return 127
        return 63

    @property
    def downlight_zones(self) -> slice:
        """Return the slice for downlight zones."""
        if self.product in LIFX_CEILING_128ZONES_PRODUCT_IDS:
            return slice(127)
        return slice(63)

    @property
    def min_kelvin(self) -> int:
        """Return the minimum kelvin value."""
        return products_dict[self.product].min_kelvin

    @property
    def max_kelvin(self) -> int:
        """Return the maximum kelvin value."""
        return products_dict[self.product].max_kelvin

    @property
    def model(self) -> str:
        """Return a friendly model name."""
        return products_dict[self.product].name

    @property
    def uplight_color(self) -> tuple[int, int, int, int]:
        """Return the HSBK values for the last zone."""
        hue, saturation, brightness, kelvin = self.chain[0][self.uplight_zone]
        if hasattr(self, "_configured_uplight_brightness"):
            brightness = min(brightness, self._configured_uplight_brightness)
        return hue, saturation, brightness, kelvin

    @property
    def uplight_hs_color(self) -> tuple[float, float]:
        """Return hue, saturation as a tuple."""
        hue, saturation, _, _ = self.chain[0][self.uplight_zone]
        hue = hue / 65535 * 360
        saturation = saturation / 65535 * 100
        return hue, saturation

    @property
    def uplight_brightness(self) -> int:
        """Return uplight brightness."""
        if (
            hasattr(self, "_is_uplight_on")
            and not self._is_uplight_on
            and hasattr(self, "_configured_uplight_brightness")
        ):
            return self._configured_uplight_brightness
        _, _, brightness, _ = self.chain[0][self.uplight_zone]
        return brightness >> 8

    @property
    def uplight_kelvin(self) -> int:
        """Return uplight kelvin."""
        _, _, _, kelvin = self.chain[0][self.uplight_zone]
        return kelvin

    @property
    def downlight_hs_color(self) -> tuple[float, float]:
        """Return the hue, saturation from zone 0."""
        hue, saturation, _, _ = self.chain[0][0]
        hue = hue / 65535 * 360
        saturation = saturation / 65535 * 100
        return hue, saturation

    @property
    def downlight_brightness(self) -> int:
        """Return max brightness value for all downlight zones."""
        if (
            hasattr(self, "_is_downlight_on")
            and not self._is_downlight_on
            and hasattr(self, "_configured_downlight_brightness")
        ):
            return self._configured_downlight_brightness
        unscaled = max(
            brightness for _, _, brightness, _ in self.chain[0][self.downlight_zones]
        )
        return unscaled >> 8

    @property
    def downlight_kelvin(self) -> int:
        """Return kelvin from zone 0."""
        _, _, _, kelvin = self.chain[0][0]
        return kelvin

    @property
    def downlight_color(self) -> tuple[int, int, int, int]:
        """Return zone 0 hue, saturation, kelvin with max brightness."""
        brightness = max(
            brightness for _, _, brightness, _ in self.chain[0][self.downlight_zones]
        )
        if hasattr(self, "_configured_downlight_brightness"):
            brightness = min(brightness, self._configured_downlight_brightness)
        hue, saturation, _, kelvin = self.chain[0][0]
        return hue, saturation, brightness, kelvin

    @property
    def configured_downlight_brightness(self) -> int:
        """Return the configured downlight brightness."""
        return self._configured_downlight_brightness

    @configured_downlight_brightness.setter
    def configured_downlight_brightness(self, value: int) -> None:
        """Set the configured downlight brightness."""
        self._configured_downlight_brightness = value

    @property
    def configured_uplight_brightness(self) -> int:
        """Return the configured uplight brightness."""
        return self._configured_uplight_brightness

    @configured_uplight_brightness.setter
    def configured_uplight_brightness(self, value: int) -> None:
        """Set the configured uplight brightness."""
        self._configured_uplight_brightness = value

    @property
    def uplight_is_on(self) -> bool:
        """Return true if power > 0 and uplight brightess > 0."""
        if hasattr(self, "_is_uplight_on"):
            return self._is_uplight_on
        try:
            _, _, brightness, _ = self.chain[0][self.uplight_zone]
        except (AttributeError, IndexError, KeyError):
            return False
        return bool(self.power_level > 0 and brightness > 0)

    @property
    def downlight_is_on(self) -> bool:
        """Return true if power > 0 and downlight zones max brightness > 0."""
        if hasattr(self, "_is_downlight_on"):
            return self._is_downlight_on
        try:
            max_brightness = max(
                b for _, _, b, _ in self.chain[0][self.downlight_zones]
            )
        except (AttributeError, IndexError, ValueError, KeyError):
            return False
        return bool(self.power_level > 0 and max_brightness > 0)

    async def turn_uplight_on(
        self, color: tuple[int, int, int, int], duration: int = 0
    ) -> None:
        """
        Turn the uplight on.

        Color is a tuple of hue, saturation, brightness and kelvin values (0-65535).
        Duration is time in milliseconds to transition from current state to color.
        """
        self._configured_uplight_brightness = color[2]
        colors = self.chain[0][self.downlight_zones]
        if self.power_level == 0:
            # The device is off, so set the downlight zones brightess to 0 first.
            colors = [
                (h, s, 0, k) for h, s, _, k in self.chain[0][self.downlight_zones]
            ]

        colors.append(color)
        await self.async_set64(
            colors=colors, duration=duration, power_on=bool(self.power_level == 0)
        )
        self._is_uplight_on = True

    async def turn_uplight_off(self, duration: int = 0) -> None:
        """
        Turn the uplight off.

        If the downlight is on, lower the brightness of the uplight to zero.
        If the downlight is off, turn off the entire light.
        """
        if self.downlight_is_on is True:
            colors = self.chain[0][self.downlight_zones]
            hue, saturation, current_brightness, kelvin = self.chain[0][
                self.uplight_zone
            ]
            self._configured_uplight_brightness = current_brightness
            colors.append((hue, saturation, 0, kelvin))
            await self.async_set64(colors=colors, duration=duration)
        else:
            await async_execute_lifx(
                partial(self.set_power, value="off", duration=duration * 1000)
            )
        self._is_uplight_on = False

    async def turn_downlight_on(
        self, color: tuple[int, int, int, int], duration: int = 0
    ) -> None:
        """
        Turn the downlight on.

        Color is a tuple of hue, saturation, brightness and kelvin values (0-65535).
        Duration is the time in milliseconds to transition from current state to color.
        """
        self._configured_downlight_brightness = color[2]
        colors = [color] * (self.total_zones - 1)
        if self.power_level > 0:
            colors.append(self.chain[0][self.uplight_zone])
        else:
            hue, saturation, _, kelvin = self.chain[0][self.uplight_zone]
            colors.append((hue, saturation, 0, kelvin))

        await self.async_set64(
            colors=colors, duration=duration, power_on=bool(self.power_level == 0)
        )
        self._is_downlight_on = True

    async def turn_downlight_off(self, duration: int = 0) -> None:
        """
        Turn the downlight off.

        If the uplight is on, lower the downlight brightness to zero.
        If the uplight is off, turn off the entire device.
        """
        current_downlight = max(b for _, _, b, _ in self.chain[0][self.downlight_zones])
        self._configured_downlight_brightness = current_downlight
        colors = [(h, s, 0, k) for h, s, _, k in self.chain[0][self.downlight_zones]]
        if self.uplight_is_on:
            colors.append(self.chain[0][self.uplight_zone])
            await self.async_set64(colors=colors, duration=duration)
        else:
            await async_execute_lifx(
                partial(self.set_power, value="off", duration=duration * 1000)
            )
        self._is_downlight_on = False

    async def async_set64(
        self,
        colors: list[tuple[int, int, int, int]],
        duration: int = 0,
        power_on: bool = False,
    ) -> None:
        """Set the colors for the ceiling light."""
        if len(colors) != self.total_zones:
            msg = f"Expected {self.total_zones} colors, got {len(colors)}"
            raise LIFXCeilingError(msg)

        if self.product in LIFX_CEILING_128ZONES_PRODUCT_IDS:
            await async_execute_lifx(
                [
                    partial(
                        self.set64,
                        tile_index=0,
                        length=1,
                        fb_index=1,
                        x=0,
                        y=0,
                        width=self.tile_device_width,
                        colors=colors[: self.total_zones // 2],
                    ),
                    partial(
                        self.set64,
                        tile_index=0,
                        length=1,
                        fb_index=1,
                        x=0,
                        y=4,
                        width=self.tile_device_width,
                        colors=colors[self.total_zones // 2 :],
                    ),
                ]
            )

        else:
            await async_execute_lifx(
                partial(
                    self.set64,
                    tile_index=0,
                    length=1,
                    fb_index=1,
                    x=0,
                    y=0,
                    width=self.tile_device_width,
                    colors=colors,
                )
            )

        await async_execute_lifx(
            partial(
                self.copy_frame_buffer,
                tile_index=0,
                length=1,
                src_fb_index=1,
                dst_fb_index=0,
                src_x=0,
                src_y=0,
                dst_x=0,
                dst_y=0,
                width=self.tile_device_width,
                duration=duration if power_on is False else 0,
            ),
        )

        if power_on:
            await async_execute_lifx(
                partial(self.set_power, value="on", duration=duration * 1000)
            )
