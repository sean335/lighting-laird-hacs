"""Services for the Lighting Controller integration."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    SERVICE_SET_BUTTON_LED,
    SERVICE_IDENTIFY_PANEL,
    SERVICE_IDENTIFY_BUTTON,
    ATTR_SERVICE_PANEL_ID,
    ATTR_SERVICE_PIN,
    ATTR_SERVICE_STATE,
    ATTR_SERVICE_BRIGHTNESS,
)

_LOGGER = logging.getLogger(__name__)

SET_BUTTON_LED_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SERVICE_PANEL_ID): cv.positive_int,
        vol.Required(ATTR_SERVICE_PIN): cv.positive_int,
        vol.Required(ATTR_SERVICE_STATE): cv.boolean,
        vol.Optional(ATTR_SERVICE_BRIGHTNESS): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=255)
        ),
    }
)

IDENTIFY_PANEL_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SERVICE_PANEL_ID): cv.positive_int,
    }
)

IDENTIFY_BUTTON_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SERVICE_PANEL_ID): cv.positive_int,
        vol.Required(ATTR_SERVICE_PIN): cv.positive_int,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register custom services."""

    def _get_coordinators() -> list:
        return list(hass.data.get(DOMAIN, {}).values())

    async def async_handle_set_button_led(call: ServiceCall) -> None:
        """Handle setting a button LED."""
        panel_id = call.data[ATTR_SERVICE_PANEL_ID]
        pin = call.data[ATTR_SERVICE_PIN]
        state = call.data[ATTR_SERVICE_STATE]
        brightness = call.data.get(ATTR_SERVICE_BRIGHTNESS)

        for coordinator in _get_coordinators():
            if hasattr(coordinator, "async_set_button_led"):
                await coordinator.async_set_button_led(panel_id, pin, state, brightness)

    async def async_handle_identify_panel(call: ServiceCall) -> None:
        """Handle panel identify."""
        panel_id = call.data[ATTR_SERVICE_PANEL_ID]
        for coordinator in _get_coordinators():
            if hasattr(coordinator, "async_identify_panel"):
                await coordinator.async_identify_panel(panel_id)

    async def async_handle_identify_button(call: ServiceCall) -> None:
        """Handle button identify."""
        panel_id = call.data[ATTR_SERVICE_PANEL_ID]
        pin = call.data[ATTR_SERVICE_PIN]
        for coordinator in _get_coordinators():
            if hasattr(coordinator, "async_identify_button"):
                await coordinator.async_identify_button(panel_id, pin)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_BUTTON_LED,
        async_handle_set_button_led,
        schema=SET_BUTTON_LED_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_IDENTIFY_PANEL,
        async_handle_identify_panel,
        schema=IDENTIFY_PANEL_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_IDENTIFY_BUTTON,
        async_handle_identify_button,
        schema=IDENTIFY_BUTTON_SCHEMA,
    )

