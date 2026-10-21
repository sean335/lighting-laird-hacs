# Lighting Controller — Home Assistant Integration & Lovelace Card

A high-performance Home Assistant custom integration for the **Lighting Laird / ESP32 Lighting Controller**.

Features zero-polling real-time WebSocket push updates, native entities for wired lamps and panel inputs, a ready-to-use Home Assistant Automation Blueprint, and a tactile Lovelace keypad card with live glowing pilot LEDs.

---

## Features

- **⚡ Zero-Polling Real-Time Push**: Instant bidirectional WebSocket communication (`ws://<esp32_ip>/ws`).
- **💡 Native Light Entities**: Exposes all wired driver channels (0–179) as native Home Assistant `light` entities with full brightness control.
- **🔘 Native Event Entities**: Exposes every panel button (`press`, `release`), rotary encoder dial (`turn_up`, `turn_down`), and gesture pattern as native Home Assistant `event` entities.
- **🎯 Device Automation Triggers**: Direct integration with the Home Assistant Automation UI (select device $\to$ trigger on button press, dial turn, or pattern match).
- **🚨 Physical Pilot LED Sync**: Service `lighting_controller.set_button_led` allows Home Assistant to control the physical pilot LEDs on your wall switch panels.
- **📜 Pre-built Automation Blueprint**: Map any panel button, dial turn, or pattern match to *any* Home Assistant device (Philips Hue, Zigbee, Z-Wave, Shelly, Sonos, scripts, scenes) with optional pilot LED sync!
- **🎛️ Custom Lovelace Panel Card**: A glassmorphic digital representation of your physical keypads and rotary dials featuring live glowing pilot LEDs.

---

## Installation

### Option 1: Via HACS (Recommended)

1. Open Home Assistant and navigate to **HACS** $\to$ **Integrations**.
2. Click the three dots in the top-right corner and select **Custom repositories**.
3. Enter your repository URL, set the category to **Integration**, and click **Add**.
4. Click **Download**, then restart Home Assistant.

### Option 2: Manual Installation

1. Copy the `custom_components/lighting_controller` directory into your Home Assistant `<config_dir>/custom_components/` folder.
2. Restart Home Assistant.

---

## Configuration

1. In Home Assistant, go to **Settings** $\to$ **Devices & Services**.
2. Click **Add Integration** and search for **Lighting Controller**.
3. Enter the IP address or hostname of your ESP32 controller (port 80 default).
4. Home Assistant will discover all configured lamps, panels, and patterns automatically.

---

## Automation Blueprint

A turnkey blueprint is included in `blueprints/automation/lighting_controller/panel_button_control.yaml`:

1. Copy `panel_button_control.yaml` to your Home Assistant `blueprints/automation/` folder (or import it).
2. Go to **Settings** $\to$ **Automations & Scenes** $\to$ **Blueprints**.
3. Click **Create Automation** on **Lighting Controller — Panel Button, Dial & Pattern Action**.
4. Configure:
   - **Panel ID**: The ID of the physical wall panel (0 to 49).
   - **Button Pin**: The button index (0 to 7).
   - **Trigger Event**: Button Press, Release, Rotary Turn Up/Down, or Pattern Match.
   - **Action**: Any Home Assistant action (e.g. `light.toggle` on a Zigbee/Hue bulb).
   - **Pilot LED Sync Entity (Optional)**: Choose an entity (e.g. `light.living_room_ceiling`). The physical button's LED will glow when the light is on and dim/turn off when the light is off!

---

## Custom Lovelace Card

The custom card `lighting-controller-card` is served automatically by the integration.

To add it to your Lovelace dashboard:

1. In your Lovelace dashboard, click **Edit Dashboard** $\to$ **Add Card** $\to$ **Manual**.
2. Example card configuration:

```yaml
type: custom:lighting-controller-card
title: Living Room Keypad
panel_id: 0
mappings:
  - button_pin: 0
    label: Ceiling Lights
    entity: light.living_room_ceiling
  - button_pin: 1
    label: Reading Lamp
    entity: light.reading_lamp
  - button_pin: 2
    label: Movie Mode
    entity: scene.movie_night
  - button_pin: 3
    type: dial
    label: Dimmer Dial
    entity: light.living_room_ceiling
    step: 20
```

### Live Pilot LEDs
When `entity` is defined on a button mapping:
- The card's pilot LED glows cyan when the entity is `on` or `active`.
- Tapping the button in Lovelace toggles the Home Assistant entity immediately and provides visual feedback.

---

## Services

### `lighting_controller.set_button_led`
Control the physical LED on a button:
```yaml
service: lighting_controller.set_button_led
data:
  panel_id: 0
  pin: 2
  state: true
  brightness: 200 # Optional (0-255)
```

### `lighting_controller.identify_panel`
Flash all LEDs on a panel to locate it physically:
```yaml
service: lighting_controller.identify_panel
data:
  panel_id: 0
```

### `lighting_controller.identify_button`
Flash the LED of a specific button:
```yaml
service: lighting_controller.identify_button
data:
  panel_id: 0
  pin: 1
```

