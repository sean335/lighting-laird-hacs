"""Device automation triggers for Lighting Controller."""
from __future__ import annotations

import logging
from typing import Any
import voluptuous as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_PLATFORM,
    CONF_TYPE,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    EVENT_LIGHTING_CONTROLLER,
    ATTR_PANEL_ID,
    ATTR_PIN,
    ATTR_STATE,
    ATTR_DIRECTION,
    ATTR_PATTERN_NAME,
)

_LOGGER = logging.getLogger(__name__)

CONF_PANEL_ID = "panel_id"
CONF_PIN = "pin"
CONF_PATTERN_NAME = "pattern_name"

TRIGGER_TYPES = {
    "button_pressed",
    "button_released",
    "dial_turn_up",
    "dial_turn_down",
    "pattern_matched",
}

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
        vol.Required(CONF_PANEL_ID): int,
        vol.Required(CONF_PIN): int,
        vol.Optional(CONF_PATTERN_NAME): str,
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    """List device triggers for Lighting Controller devices."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)
    if not device:
        return []

    entry_id = next(iter(device.config_entries), None)
    if not entry_id or entry_id not in hass.data.get(DOMAIN, {}):
        return []

    coordinator = hass.data[DOMAIN][entry_id]
    triggers: list[dict[str, Any]] = []

    # Check if this device is a panel or the main controller
    for panel in coordinator.topology.get("panels", []):
        panel_id = panel.get("panel_id")
        for btn in panel.get("buttons", []):
            pin = btn.get("pin")
            btn_type = btn.get("type", 0)
            if pin is None:
                continue

            if btn_type in (0, 1):
                triggers.append(
                    {
                        CONF_PLATFORM: "device",
                        CONF_DOMAIN: DOMAIN,
                        CONF_DEVICE_ID: device_id,
                        CONF_TYPE: "button_pressed",
                        CONF_PANEL_ID: panel_id,
                        CONF_PIN: pin,
                    }
                )
                triggers.append(
                    {
                        CONF_PLATFORM: "device",
                        CONF_DOMAIN: DOMAIN,
                        CONF_DEVICE_ID: device_id,
                        CONF_TYPE: "button_released",
                        CONF_PANEL_ID: panel_id,
                        CONF_PIN: pin,
                    }
                )
            elif btn_type in (2, 3):
                triggers.append(
                    {
                        CONF_PLATFORM: "device",
                        CONF_DOMAIN: DOMAIN,
                        CONF_DEVICE_ID: device_id,
                        CONF_TYPE: "dial_turn_up",
                        CONF_PANEL_ID: panel_id,
                        CONF_PIN: pin,
                    }
                )
                triggers.append(
                    {
                        CONF_PLATFORM: "device",
                        CONF_DOMAIN: DOMAIN,
                        CONF_DEVICE_ID: device_id,
                        CONF_TYPE: "dial_turn_down",
                        CONF_PANEL_ID: panel_id,
                        CONF_PIN: pin,
                    }
                )

            # Patterns
            for pat_id, pat_name in coordinator.pattern_map.items():
                triggers.append(
                    {
                        CONF_PLATFORM: "device",
                        CONF_DOMAIN: DOMAIN,
                        CONF_DEVICE_ID: device_id,
                        CONF_TYPE: "pattern_matched",
                        CONF_PANEL_ID: panel_id,
                        CONF_PIN: pin,
                        CONF_PATTERN_NAME: pat_name,
                    }
                )

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: Any,
    trigger_info: Any,
) -> CALLBACK_TYPE:
    """Attach a trigger to bus events."""
    trigger_type = config[CONF_TYPE]
    panel_id = config[CONF_PANEL_ID]
    pin = config[CONF_PIN]

    event_data: dict[str, Any] = {
        ATTR_PANEL_ID: panel_id,
        ATTR_PIN: pin,
    }

    if trigger_type == "button_pressed":
        event_data["type"] = "button"
        event_data[ATTR_STATE] = "press"
    elif trigger_type == "button_released":
        event_data["type"] = "button"
        event_data[ATTR_STATE] = "release"
    elif trigger_type == "dial_turn_up":
        event_data["type"] = "dial"
        event_data[ATTR_DIRECTION] = "up"
    elif trigger_type == "dial_turn_down":
        event_data["type"] = "dial"
        event_data[ATTR_DIRECTION] = "down"
    elif trigger_type == "pattern_matched":
        event_data["type"] = "pattern"
        if CONF_PATTERN_NAME in config:
            event_data[ATTR_PATTERN_NAME] = config[CONF_PATTERN_NAME]

    event_config = {
        event_trigger.CONF_PLATFORM: "event",
        event_trigger.CONF_EVENT_TYPE: EVENT_LIGHTING_CONTROLLER,
        event_trigger.CONF_EVENT_DATA: event_data,
    }

    event_config = event_trigger.TRIGGER_SCHEMA(event_config)
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )

