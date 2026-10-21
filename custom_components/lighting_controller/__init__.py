"""The Lighting Controller integration."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntries, ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, PLATFORMS, DEFAULT_PORT
from .coordinator import LightingControllerCoordinator
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Lighting Controller integration."""
    hass.data.setdefault(DOMAIN, {})

    # Register custom frontend card static path
    frontend_path = Path(__file__).parent / "frontend"
    if frontend_path.exists():
        hass.http.register_static_path(
            "/lighting_controller_frontend",
            str(frontend_path),
            cache_headers=False,
        )
        _LOGGER.debug("Registered frontend path at /lighting_controller_frontend")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lighting Controller from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)

    coordinator = LightingControllerCoordinator(hass, host, port, entry.entry_id)
    await coordinator.async_setup()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward setup to light and event platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: LightingControllerCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_unload()

    return unload_ok

