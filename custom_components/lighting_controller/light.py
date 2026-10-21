"""Light platform for Lighting Controller."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LightingControllerCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lighting Controller lamps from config entry."""
    coordinator: LightingControllerCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[LightingControllerLamp] = []
    for lamp in coordinator.topology.get("lamps", []):
        lamp_id = lamp.get("lamp_id")
        name = lamp.get("name")
        dimmable = lamp.get("dimmable", True)
        if lamp_id is not None and name:
            entities.append(
                LightingControllerLamp(coordinator, lamp_id, name, dimmable)
            )

    async_add_entities(entities)


class LightingControllerLamp(LightEntity):
    """Representation of a Lighting Controller driver lamp channel."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LightingControllerCoordinator,
        lamp_id: int,
        name: str,
        dimmable: bool,
    ) -> None:
        """Initialize the lamp entity."""
        self.coordinator = coordinator
        self.lamp_id = lamp_id
        self._attr_name = name
        self._dimmable = dimmable
        self._attr_unique_id = f"{coordinator.entry_id}_lamp_{lamp_id}"

        if dimmable:
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            self._attr_supported_color_modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry_id)},
            name=f"Lighting Controller ({coordinator.host})",
            manufacturer="Lighting Laird",
            model="ESP32 Lighting Controller",
            sw_version="2.0.0",
        )

    async def async_added_to_hass(self) -> None:
        """Register coordinator callback when added to hass."""
        self.coordinator.register_lamp_callback(self.lamp_id, self._handle_update)

    def _handle_update(self) -> None:
        """Handle state update from coordinator."""
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        state = self.coordinator.lamp_states.get(self.lamp_id)
        if state:
            return state.get("is_on", False)
        return False

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        if not self._dimmable:
            return None
        state = self.coordinator.lamp_states.get(self.lamp_id)
        if state:
            raw_bri = state.get("brightness", 0)
            # Map 0..254 to 0..255
            return int(round((raw_bri / 254.0) * 255.0))
        return 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        if ATTR_BRIGHTNESS in kwargs and self._dimmable:
            ha_bri = kwargs[ATTR_BRIGHTNESS]
            esp_bri = int(round((ha_bri / 255.0) * 254.0))
            esp_bri = max(1, min(254, esp_bri))
            await self.coordinator.async_set_lamp(self.lamp_id, "set_brightness", esp_bri)
        else:
            await self.coordinator.async_set_lamp(self.lamp_id, "turn_on", 254)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self.coordinator.async_set_lamp(self.lamp_id, "turn_off", 0)

