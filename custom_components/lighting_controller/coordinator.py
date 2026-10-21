"""DataUpdateCoordinator and WebSocket manager for Lighting Controller."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    EVENT_LIGHTING_CONTROLLER,
    ATTR_EVENT_TYPE,
    ATTR_PANEL_ID,
    ATTR_PANEL_NAME,
    ATTR_PIN,
    ATTR_BUTTON_ID,
    ATTR_BUTTON_NAME,
    ATTR_STATE,
    ATTR_DIRECTION,
    ATTR_STEP,
    ATTR_PATTERN_ID,
    ATTR_PATTERN_NAME,
    ATTR_LAMP_ID,
    ATTR_BRIGHTNESS,
    ATTR_IS_ON,
)

_LOGGER = logging.getLogger(__name__)


class LightingControllerCoordinator:
    """Manages connection, topology, and real-time events from the ESP32 Lighting Controller."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, entry_id: str) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.host = host
        self.port = port
        self.entry_id = entry_id

        self.ws_url = f"ws://{host}:{port}/ws"
        self.http_base = f"http://{host}:{port}"

        self.topology: dict[str, Any] = {"lamps": [], "panels": [], "patterns": []}
        self.lamp_states: dict[int, dict[str, Any]] = {}
        self.panel_map: dict[int, dict[str, Any]] = {}
        self.pattern_map: dict[int, str] = {}

        self._lamp_callbacks: dict[int, list[Callable[[], None]]] = {}
        self._event_callbacks: list[Callable[[dict[str, Any]], None]] = []

        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._reconnect_task: asyncio.Task | None = None
        self._running = False

    async def async_setup(self) -> bool:
        """Fetch initial topology and begin WebSocket connection."""
        success = await self.async_fetch_topology()
        if not success:
            _LOGGER.warning("Could not fetch topology via HTTP, will still attempt WebSocket")

        self._running = True
        self._reconnect_task = asyncio.create_task(self._ws_loop())
        return True

    async def async_fetch_topology(self) -> bool:
        """Fetch complete topology from the controller via HTTP."""
        session = async_get_clientsession(self.hass)
        try:
            url = f"{self.http_base}/getTopology"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                if resp.status == 200:
                    self.topology = await resp.json()
                    self._parse_topology()
                    _LOGGER.info(
                        "Loaded Lighting Controller topology: %d lamps, %d panels, %d patterns",
                        len(self.topology.get("lamps", [])),
                        len(self.topology.get("panels", [])),
                        len(self.topology.get("patterns", [])),
                    )
                    return True
        except Exception as ex:
            _LOGGER.error("Failed to fetch topology from %s: %s", self.host, ex)
        return False

    def _parse_topology(self) -> None:
        """Index topology for fast lookups."""
        for lamp in self.topology.get("lamps", []):
            lamp_id = lamp.get("lamp_id")
            if lamp_id is not None:
                min_bri = lamp.get("min_brightness", 1)
                dimmable_val = lamp.get("dimmable")
                if min_bri == 254:
                    is_dimmable = False
                elif dimmable_val is True:
                    is_dimmable = True
                elif dimmable_val is False and min_bri >= 254:
                    is_dimmable = False
                elif min_bri < 250:
                    is_dimmable = True
                else:
                    is_dimmable = True

                self.lamp_states[lamp_id] = {
                    "name": lamp.get("name", f"Lamp {lamp_id}"),
                    "brightness": lamp.get("brightness", 0),
                    "is_on": lamp.get("is_on", False),
                    "dimmable": is_dimmable,
                    "min_brightness": min_bri,
                }

        for panel in self.topology.get("panels", []):
            panel_id = panel.get("panel_id")
            if panel_id is not None:
                self.panel_map[panel_id] = panel

        for pat in self.topology.get("patterns", []):
            pid = pat.get("pattern_id")
            if pid is not None:
                self.pattern_map[pid] = pat.get("name", f"Pattern {pid}")

    async def _ws_loop(self) -> None:
        """Persistent WebSocket loop with auto-reconnect."""
        backoff = 1
        session = async_get_clientsession(self.hass)

        while self._running:
            try:
                _LOGGER.debug("Connecting to WebSocket: %s", self.ws_url)
                async with session.ws_connect(self.ws_url, heartbeat=25) as ws:
                    self._ws = ws
                    backoff = 1
                    _LOGGER.info("Connected to Lighting Controller WebSocket (%s)", self.host)

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            self._handle_ws_message(msg.data)
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break

            except asyncio.CancelledError:
                break
            except Exception as ex:
                _LOGGER.debug("WebSocket connection error (%s): %s", self.host, ex)
            finally:
                self._ws = None

            if self._running:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)

    def _handle_ws_message(self, raw_data: str) -> None:
        """Parse raw incoming WebSocket messages."""
        raw_data = raw_data.strip()
        if not raw_data:
            return

        # Handle JSON events
        if raw_data.startswith("{") and raw_data.endswith("}"):
            try:
                payload = json.loads(raw_data)
                self._process_json_event(payload)
                return
            except json.JSONDecodeError:
                pass

        # Handle legacy text messages
        parts = raw_data.split(" ")
        cmd = parts[0]
        if cmd == "bl" and len(parts) >= 3:
            try:
                lamp_id = int(parts[1])
                bri = int(parts[2])
                self._update_lamp_state(lamp_id, bri, bri > 0)
            except ValueError:
                pass

    def _process_json_event(self, data: dict[str, Any]) -> None:
        """Process structured JSON event from the controller."""
        event_name = data.get("event")

        if event_name == "lamp":
            lamp_id = data.get("lamp_id")
            brightness = data.get("brightness", 0)
            is_on = data.get("is_on", brightness > 0)
            if lamp_id is not None:
                self._update_lamp_state(lamp_id, brightness, is_on)

        elif event_name == "button":
            panel_id = data.get("panel_id")
            pin = data.get("pin")
            button_id = data.get("button_id")
            state = data.get("state")  # "press" or "release"

            panel_name = self.panel_map.get(panel_id, {}).get("name", f"Panel {panel_id}")
            button_name = self._get_button_name(panel_id, pin)

            event_data = {
                ATTR_EVENT_TYPE: "button",
                ATTR_PANEL_ID: panel_id,
                ATTR_PANEL_NAME: panel_name,
                ATTR_PIN: pin,
                ATTR_BUTTON_ID: button_id,
                ATTR_BUTTON_NAME: button_name,
                ATTR_STATE: state,
            }
            self.hass.bus.async_fire(EVENT_LIGHTING_CONTROLLER, event_data)
            self._notify_event_entities(event_data)

        elif event_name == "dial":
            panel_id = data.get("panel_id")
            pin = data.get("pin")
            button_id = data.get("button_id")
            direction = data.get("direction")  # "up" or "down"
            step = data.get("step", 1)

            panel_name = self.panel_map.get(panel_id, {}).get("name", f"Panel {panel_id}")
            button_name = self._get_button_name(panel_id, pin)

            event_data = {
                ATTR_EVENT_TYPE: "dial",
                ATTR_PANEL_ID: panel_id,
                ATTR_PANEL_NAME: panel_name,
                ATTR_PIN: pin,
                ATTR_BUTTON_ID: button_id,
                ATTR_BUTTON_NAME: button_name,
                ATTR_DIRECTION: direction,
                ATTR_STEP: step,
            }
            self.hass.bus.async_fire(EVENT_LIGHTING_CONTROLLER, event_data)
            self._notify_event_entities(event_data)

        elif event_name == "pattern":
            panel_id = data.get("panel_id")
            pin = data.get("pin")
            button_id = data.get("button_id")
            pattern_id = data.get("pattern_id")
            pattern_name = data.get("pattern_name") or self.pattern_map.get(pattern_id, f"Pattern {pattern_id}")

            panel_name = self.panel_map.get(panel_id, {}).get("name", f"Panel {panel_id}")
            button_name = self._get_button_name(panel_id, pin)

            event_data = {
                ATTR_EVENT_TYPE: "pattern",
                ATTR_PANEL_ID: panel_id,
                ATTR_PANEL_NAME: panel_name,
                ATTR_PIN: pin,
                ATTR_BUTTON_ID: button_id,
                ATTR_BUTTON_NAME: button_name,
                ATTR_PATTERN_ID: pattern_id,
                ATTR_PATTERN_NAME: pattern_name,
            }
            self.hass.bus.async_fire(EVENT_LIGHTING_CONTROLLER, event_data)
            self._notify_event_entities(event_data)

    def _get_button_name(self, panel_id: int | None, pin: int | None) -> str:
        """Resolve friendly button name from topology."""
        if panel_id is None or pin is None:
            return ""
        panel = self.panel_map.get(panel_id)
        if panel:
            for btn in panel.get("buttons", []):
                if btn.get("pin") == pin:
                    return btn.get("name", f"Button {pin + 1}")
        return f"Button {pin + 1}"

    def _update_lamp_state(self, lamp_id: int, brightness: int, is_on: bool) -> None:
        """Update cached lamp state and trigger entity callbacks."""
        if lamp_id not in self.lamp_states:
            self.lamp_states[lamp_id] = {
                "name": f"Lamp {lamp_id}",
                "brightness": brightness,
                "is_on": is_on,
                "dimmable": True,
                "min_brightness": 1,
            }
        else:
            self.lamp_states[lamp_id]["brightness"] = brightness
            self.lamp_states[lamp_id]["is_on"] = is_on

        # Notify registered lamp entity callbacks
        for cb in self._lamp_callbacks.get(lamp_id, []):
            cb()

        # Also fire bus event
        self.hass.bus.async_fire(
            EVENT_LIGHTING_CONTROLLER,
            {
                ATTR_EVENT_TYPE: "lamp",
                ATTR_LAMP_ID: lamp_id,
                ATTR_BRIGHTNESS: brightness,
                ATTR_IS_ON: is_on,
            },
        )

    def register_lamp_callback(self, lamp_id: int, callback: Callable[[], None]) -> None:
        """Register entity callback for lamp changes."""
        self._lamp_callbacks.setdefault(lamp_id, []).append(callback)

    def register_event_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register entity callback for button/dial/pattern events."""
        self._event_callbacks.append(callback)

    def _notify_event_entities(self, event_data: dict[str, Any]) -> None:
        """Deliver event to all registered event entities."""
        for cb in self._event_callbacks:
            cb(event_data)

    async def async_send_ws_cmd(self, payload: dict[str, Any]) -> bool:
        """Send JSON command over active WebSocket or fallback to HTTP."""
        if self._ws is not None and not self._ws.closed:
            try:
                await self._ws.send_str(json.dumps(payload))
                return True
            except Exception as ex:
                _LOGGER.warning("WebSocket send error: %s", ex)

        return False

    async def async_set_lamp(self, lamp_id: int, action: int | str, brightness: int = 254) -> None:
        """Send lamp control command to the controller."""
        payload = {
            "cmd": "set_lamp",
            "lamp_id": lamp_id,
            "action": action,
            "brightness": brightness,
        }
        sent = await self.async_send_ws_cmd(payload)
        if not sent:
            # Fallback to HTTP
            action_code = 1 if action == "turn_on" else (2 if action == "turn_off" else 4)
            url = f"{self.http_base}/sendLampCommand?lampId={lamp_id}&action={action_code}&actionValue={brightness}"
            session = async_get_clientsession(self.hass)
            try:
                await session.get(url, timeout=aiohttp.ClientTimeout(total=4))
            except Exception as ex:
                _LOGGER.error("Failed to send lamp command via HTTP: %s", ex)

    async def async_set_button_led(
        self, panel_id: int, pin: int, state: bool, brightness: int | None = None
    ) -> None:
        """Set a button pilot LED state and brightness."""
        payload: dict[str, Any] = {
            "cmd": "set_button_led",
            "panel_id": panel_id,
            "pin": pin,
            "state": state,
        }
        if brightness is not None:
            payload["brightness"] = brightness

        sent = await self.async_send_ws_cmd(payload)
        if not sent:
            bri_val = brightness if brightness is not None else (254 if state else 0)
            url = f"{self.http_base}/setLEDBrightness?panelId={panel_id}&pinNumber={pin}&brightness={bri_val}"
            session = async_get_clientsession(self.hass)
            try:
                await session.get(url, timeout=aiohttp.ClientTimeout(total=4))
            except Exception as ex:
                _LOGGER.error("Failed to set button LED via HTTP: %s", ex)

    async def async_identify_panel(self, panel_id: int) -> None:
        """Identify panel by blinking its LEDs."""
        session = async_get_clientsession(self.hass)
        try:
            await session.get(
                f"{self.http_base}/identifyPanel?panelId={panel_id}",
                timeout=aiohttp.ClientTimeout(total=4),
            )
        except Exception as ex:
            _LOGGER.error("Failed to identify panel: %s", ex)

    async def async_identify_button(self, panel_id: int, pin: int) -> None:
        """Identify button by blinking its LED."""
        session = async_get_clientsession(self.hass)
        try:
            await session.get(
                f"{self.http_base}/identifyButton?panelId={panel_id}&pinNumber={pin}",
                timeout=aiohttp.ClientTimeout(total=4),
            )
        except Exception as ex:
            _LOGGER.error("Failed to identify button: %s", ex)

    async def async_unload(self) -> None:
        """Shutdown coordinator and close WebSocket."""
        self._running = False
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
        if self._ws and not self._ws.closed:
            await self._ws.close()

