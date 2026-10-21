"""Event platform for Lighting Controller buttons, dials, and pattern matches."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ATTR_EVENT_TYPE,
    ATTR_PANEL_ID,
    ATTR_PIN,
    ATTR_STATE,
    ATTR_DIRECTION,
    ATTR_PATTERN_ID,
    ATTR_PATTERN_NAME,
)
from .coordinator import LightingControllerCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lighting Controller event entities from config entry."""
    coordinator: LightingControllerCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[EventEntity] = []

    for panel in coordinator.topology.get("panels", []):
        panel_id = panel.get("panel_id")
        panel_name = panel.get("name", f"Panel {panel_id}")

        for btn in panel.get("buttons", []):
            pin = btn.get("pin")
            btn_name = btn.get("name") or f"Button {pin + 1}"
            btn_type = btn.get("type", 0)

            if pin is None:
                continue

            # Pins configured as Rotary DT cannot have trigger events
            if btn_type == 3:  # ROTARY_DT
                continue

            # Switch button (press/release)
            if btn_type in (0, 1):  # MOMENTARY_SWITCH, LATCHING_SWITCH
                entities.append(
                    LightingControllerButtonEvent(
                        coordinator, panel_id, pin, panel_name, btn_name
                    )
                )

            # Rotary encoder (turn up / turn down) - only on Rotary CLK pin
            elif btn_type == 2:  # ROTARY_CLK
                entities.append(
                    LightingControllerDialEvent(
                        coordinator, panel_id, pin, panel_name, btn_name
                    )
                )

            # Specific event entity for each configured pattern gesture on this button.
            # Only patterns that have already been configured for this button are displayed.
            configured_patterns = sorted(set(btn.get("patterns", [])))
            for pat_id in configured_patterns:
                pat_name = coordinator.pattern_map.get(pat_id)
                if pat_name:
                    entities.append(
                        LightingControllerSpecificPatternEvent(
                            coordinator, panel_id, pin, panel_name, btn_name, pat_id, pat_name
                        )
                    )

    async_add_entities(entities)


class LightingControllerButtonEvent(EventEntity):
    """Event entity for a panel button press or release."""

    _attr_has_entity_name = True
    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = ["press", "release"]

    def __init__(
        self,
        coordinator: LightingControllerCoordinator,
        panel_id: int,
        pin: int,
        panel_name: str,
        button_name: str,
    ) -> None:
        """Initialize the button event entity."""
        self.coordinator = coordinator
        self.panel_id = panel_id
        self.pin = pin
        self._attr_name = f"{button_name}"
        self._attr_unique_id = f"{coordinator.entry_id}_btn_{panel_id}_{pin}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.entry_id}_panel_{panel_id}")},
            name=f"Panel: {panel_name}",
            via_device=(DOMAIN, coordinator.entry_id),
            manufacturer="Lighting Laird",
            model="Switch Panel",
        )

    async def async_added_to_hass(self) -> None:
        """Register event callback."""
        self.coordinator.register_event_callback(self._handle_event)

    def _handle_event(self, data: dict[str, Any]) -> None:
        """Handle incoming event from coordinator."""
        if (
            data.get(ATTR_EVENT_TYPE) == "button"
            and data.get(ATTR_PANEL_ID) == self.panel_id
            and data.get(ATTR_PIN) == self.pin
        ):
            state = data.get(ATTR_STATE)  # "press" or "release"
            if state in self._attr_event_types:
                self._trigger_event(state, data)
                self.async_write_ha_state()


class LightingControllerDialEvent(EventEntity):
    """Event entity for rotary dial turns."""

    _attr_has_entity_name = True
    _attr_event_types = ["turn_up", "turn_down"]

    def __init__(
        self,
        coordinator: LightingControllerCoordinator,
        panel_id: int,
        pin: int,
        panel_name: str,
        button_name: str,
    ) -> None:
        """Initialize the dial event entity."""
        self.coordinator = coordinator
        self.panel_id = panel_id
        self.pin = pin
        self._attr_name = f"{button_name} Dial"
        self._attr_unique_id = f"{coordinator.entry_id}_dial_{panel_id}_{pin}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.entry_id}_panel_{panel_id}")},
            name=f"Panel: {panel_name}",
            via_device=(DOMAIN, coordinator.entry_id),
            manufacturer="Lighting Laird",
            model="Switch Panel",
        )

    async def async_added_to_hass(self) -> None:
        """Register event callback."""
        self.coordinator.register_event_callback(self._handle_event)

    def _handle_event(self, data: dict[str, Any]) -> None:
        """Handle incoming event from coordinator."""
        if (
            data.get(ATTR_EVENT_TYPE) == "dial"
            and data.get(ATTR_PANEL_ID) == self.panel_id
            and data.get(ATTR_PIN) == self.pin
        ):
            direction = data.get(ATTR_DIRECTION)  # "up" or "down"
            event_type = f"turn_{direction}"
            if event_type in self._attr_event_types:
                self._trigger_event(event_type, data)
                self.async_write_ha_state()


class LightingControllerSpecificPatternEvent(EventEntity):
    """Event entity for a specific pattern gesture on a button."""

    _attr_has_entity_name = True
    _attr_event_types = ["triggered"]

    def __init__(
        self,
        coordinator: LightingControllerCoordinator,
        panel_id: int,
        pin: int,
        panel_name: str,
        button_name: str,
        pattern_id: int,
        pattern_name: str,
    ) -> None:
        """Initialize the specific pattern event entity."""
        self.coordinator = coordinator
        self.panel_id = panel_id
        self.pin = pin
        self.pattern_id = pattern_id
        self.pattern_name = pattern_name
        self._attr_name = f"{button_name} {pattern_name}"
        self._attr_unique_id = f"{coordinator.entry_id}_pat_{panel_id}_{pin}_{pattern_id}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.entry_id}_panel_{panel_id}")},
            name=f"Panel: {panel_name}",
            via_device=(DOMAIN, coordinator.entry_id),
            manufacturer="Lighting Laird",
            model="Switch Panel",
        )

    async def async_added_to_hass(self) -> None:
        """Register event callback."""
        self.coordinator.register_event_callback(self._handle_event)

    def _handle_event(self, data: dict[str, Any]) -> None:
        """Handle incoming pattern event from coordinator."""
        if (
            data.get(ATTR_EVENT_TYPE) == "pattern"
            and data.get(ATTR_PANEL_ID) == self.panel_id
            and data.get(ATTR_PIN) == self.pin
        ):
            matched_id = data.get(ATTR_PATTERN_ID)
            matched_name = data.get(ATTR_PATTERN_NAME)
            if (matched_id is not None and matched_id == self.pattern_id) or (
                matched_name is not None and matched_name == self.pattern_name
            ):
                self._trigger_event("triggered", data)
                self.async_write_ha_state()

