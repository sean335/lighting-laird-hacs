"""The Lighting Controller integration."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, CoreState
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, PLATFORMS, DEFAULT_PORT
from .coordinator import LightingControllerCoordinator
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)
CARD_URL = "/lighting_controller_frontend/lighting-controller-card.js"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Lighting Controller integration."""
    hass.data.setdefault(DOMAIN, {})

    # Register custom frontend card static path with backwards & forwards compatibility
    frontend_path = Path(__file__).parent / "frontend"
    if frontend_path.exists():
        try:
            # Home Assistant 2024.7+
            from homeassistant.components.http import StaticPathConfig
            await hass.http.async_register_static_paths(
                [StaticPathConfig("/lighting_controller_frontend", str(frontend_path), False)]
            )
            _LOGGER.debug("Registered frontend path with async_register_static_paths")
        except (ImportError, AttributeError):
            try:
                # Older Home Assistant versions
                if hasattr(hass.http, "register_static_path"):
                    hass.http.register_static_path(
                        "/lighting_controller_frontend",
                        str(frontend_path),
                        cache_headers=False,
                    )
                    _LOGGER.debug("Registered frontend path with register_static_path")
                else:
                    _LOGGER.debug("No compatible static path registration method found on hass.http")
            except Exception as ex:
                _LOGGER.warning("Could not register static frontend path: %s", ex)
        except Exception as ex:
            _LOGGER.warning("Could not register static frontend path: %s", ex)

        # 1. Inject script into all frontend pages so the card is always loaded
        try:
            from homeassistant.components.frontend import add_extra_js_url
            add_extra_js_url(hass, f"{CARD_URL}?v=2.0")
            _LOGGER.debug("Registered card via frontend.add_extra_js_url")
        except Exception as ex:
            _LOGGER.debug("Could not add_extra_js_url: %s", ex)

        # 2. Sync to <config>/www/ so /local/lighting-controller-card.js also works
        try:
            www_dir = Path(hass.config.path("www"))
            if www_dir.exists():
                src_card = frontend_path / "lighting-controller-card.js"
                dst_card = www_dir / "lighting-controller-card.js"
                if src_card.exists():
                    import shutil
                    shutil.copyfile(src_card, dst_card)
                    _LOGGER.debug("Synced lighting-controller-card.js to %s", dst_card)
        except Exception as ex:
            _LOGGER.debug("Could not sync card to www: %s", ex)

        # 3. Automatically register the card as a Lovelace resource in storage mode
        async def _register_lovelace_resource(_event=None) -> None:
            """Automatically add card resource to Lovelace storage mode."""
            if "lovelace" not in hass.data:
                return

            lovelace = hass.data["lovelace"]
            if getattr(lovelace, "mode", None) == "storage":
                resources = getattr(lovelace, "resources", None)
                if resources is not None:
                    try:
                        if not getattr(resources, "loaded", True):
                            await resources.async_load()

                        exists = any(
                            item.get("url") == CARD_URL or item.get("url", "").startswith("/lighting_controller_frontend/")
                            for item in resources.async_items()
                        )
                        if not exists:
                            await resources.async_create_item({
                                "url": CARD_URL,
                                "type": "module",
                            })
                            _LOGGER.info("Successfully registered Lovelace resource: %s", CARD_URL)
                    except Exception as err:
                        _LOGGER.debug("Could not auto-register Lovelace resource: %s", err)

        if hass.state == CoreState.running:
            hass.async_create_task(_register_lovelace_resource())
        else:
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _register_lovelace_resource)

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

