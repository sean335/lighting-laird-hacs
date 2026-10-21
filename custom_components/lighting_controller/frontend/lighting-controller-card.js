/**
 * Lighting Controller Lovelace Card
 * =================================
 * Custom card for Home Assistant displaying physical lighting panels,
 * tactile push buttons with live glowing pilot LEDs, and rotary encoders.
 *
 * Can map buttons to any Home Assistant entity (lights, switches, scenes, scripts)
 * or directly control wired controller lamps.
 */

class LightingControllerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._topology = null;
  }

  setConfig(config) {
    this._config = {
      title: config.title || "Lighting Controller",
      panel_id: config.panel_id !== undefined ? config.panel_id : null,
      mappings: config.mappings || [],
      ...config,
    };
    this._render();
  }

  set hass(hass) {
    const oldHass = this._hass;
    this._hass = hass;

    // Re-render LEDs if mapped entities changed state
    if (oldHass && this._config.mappings) {
      let changed = false;
      for (const m of this._config.mappings) {
        if (m.entity && oldHass.states[m.entity]?.state !== hass.states[m.entity]?.state) {
          changed = true;
          break;
        }
      }
      if (changed) {
        this._updateLedStates();
      }
    }

    if (!this._topology && hass) {
      this._loadTopology();
    }
  }

  async _loadTopology() {
    // If user provided custom mappings, we can render immediately without controller topology
    if (this._config.mappings && this._config.mappings.length > 0 && !this._config.host) {
      return;
    }
  }

  _render() {
    if (!this.shadowRoot) return;

    const title = this._config.title || "Lighting Controller";
    const mappings = this._config.mappings || [];

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
        }
        ha-card {
          background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.95));
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 18px;
          padding: 20px;
          color: #f8fafc;
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 20px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          padding-bottom: 12px;
        }
        .header h2 {
          margin: 0;
          font-size: 1.25rem;
          font-weight: 600;
          letter-spacing: -0.01em;
          color: #f1f5f9;
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .header-badge {
          background: rgba(6, 182, 212, 0.15);
          color: #38bdf8;
          border: 1px solid rgba(56, 189, 248, 0.3);
          font-size: 0.75rem;
          font-weight: 600;
          padding: 3px 10px;
          border-radius: 20px;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .keypad-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
          gap: 14px;
        }
        .button-unit {
          position: relative;
          background: rgba(30, 41, 59, 0.7);
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-radius: 14px;
          padding: 16px 12px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 10px;
          cursor: pointer;
          user-select: none;
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.1), 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        }
        .button-unit:hover {
          background: rgba(51, 65, 85, 0.8);
          border-color: rgba(56, 189, 248, 0.3);
          transform: translateY(-2px);
          box-shadow: 0 8px 12px -2px rgba(0, 0, 0, 0.4);
        }
        .button-unit:active {
          transform: translateY(1px);
          box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.4);
          background: rgba(15, 23, 42, 0.9);
        }
        .pilot-led {
          width: 12px;
          height: 12px;
          border-radius: 50%;
          background: #334155;
          border: 1px solid rgba(0, 0, 0, 0.4);
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.6);
        }
        .pilot-led.on {
          background: #38bdf8;
          border-color: #7dd3fc;
          box-shadow: 0 0 12px #38bdf8, 0 0 20px rgba(56, 189, 248, 0.6), inset 0 1px 1px #e0f2fe;
        }
        .button-label {
          font-size: 0.85rem;
          font-weight: 500;
          color: #cbd5e1;
          text-align: center;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          max-width: 100%;
        }
        .button-subtext {
          font-size: 0.7rem;
          color: #64748b;
          text-align: center;
        }
        .dial-unit {
          grid-column: span 2;
          background: rgba(30, 41, 59, 0.7);
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-radius: 14px;
          padding: 16px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
        }
        .dial-controls {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .dial-btn {
          width: 38px;
          height: 38px;
          border-radius: 10px;
          background: rgba(51, 65, 85, 0.8);
          border: 1px solid rgba(255, 255, 255, 0.1);
          color: #38bdf8;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.1rem;
          cursor: pointer;
          transition: all 0.15s ease;
        }
        .dial-btn:hover {
          background: rgba(56, 189, 248, 0.2);
          border-color: #38bdf8;
        }
        .dial-btn:active {
          transform: scale(0.92);
        }
        .dial-indicator {
          display: flex;
          flex-direction: column;
        }
        .dial-title {
          font-size: 0.9rem;
          font-weight: 600;
          color: #f1f5f9;
        }
        .dial-value {
          font-size: 0.75rem;
          color: #94a3b8;
        }
        .empty-hint {
          text-align: center;
          color: #94a3b8;
          font-size: 0.85rem;
          padding: 20px 0;
        }
      </style>
      <ha-card>
        <div class="header">
          <h2>${title}</h2>
          <span class="header-badge">Panel ${this._config.panel_id ?? 0}</span>
        </div>
        <div class="keypad-grid" id="grid">
          ${this._buildButtonsHtml(mappings)}
        </div>
      </ha-card>
    `;

    this._bindEvents();
    this._updateLedStates();
  }

  _buildButtonsHtml(mappings) {
    if (!mappings || mappings.length === 0) {
      // Default 8-button panel representation
      let html = "";
      for (let i = 0; i < 8; i++) {
        html += `
          <div class="button-unit" data-pin="${i}">
            <div class="pilot-led" id="led-${i}"></div>
            <span class="button-label">Button ${i + 1}</span>
            <span class="button-subtext">Pin ${i}</span>
          </div>
        `;
      }
      return html;
    }

    let html = "";
    mappings.forEach((m, idx) => {
      if (m.type === "dial") {
        html += `
          <div class="dial-unit" data-index="${idx}">
            <div class="dial-indicator">
              <span class="dial-title">${m.label || `Encoder Pin ${m.button_pin}`}</span>
              <span class="dial-value">${m.entity || "Rotary Dial"}</span>
            </div>
            <div class="dial-controls">
              <div class="dial-btn dial-down" data-action="down" data-index="${idx}">−</div>
              <div class="dial-btn dial-up" data-action="up" data-index="${idx}">+</div>
            </div>
          </div>
        `;
      } else {
        const pin = m.button_pin !== undefined ? m.button_pin : idx;
        const label = m.label || (m.entity ? m.entity.split(".")[1].replace(/_/g, " ") : `Button ${pin + 1}`);
        html += `
          <div class="button-unit" data-pin="${pin}" data-entity="${m.entity || ""}" data-index="${idx}">
            <div class="pilot-led" id="led-${pin}"></div>
            <span class="button-label">${label}</span>
            <span class="button-subtext">${m.entity ? "HA Entity" : `Pin ${pin}`}</span>
          </div>
        `;
      }
    });
    return html;
  }

  _bindEvents() {
    const root = this.shadowRoot;
    if (!root) return;

    // Button clicks
    root.querySelectorAll(".button-unit").forEach((el) => {
      el.addEventListener("click", () => {
        const pin = parseInt(el.getAttribute("data-pin") || "0", 10);
        const entity = el.getAttribute("data-entity");
        this._handleButtonPress(pin, entity);
      });
    });

    // Dial turn buttons
    root.querySelectorAll(".dial-btn").forEach((el) => {
      el.addEventListener("click", (e) => {
        e.stopPropagation();
        const action = el.getAttribute("data-action");
        const idx = parseInt(el.getAttribute("data-index") || "0", 10);
        const mapping = (this._config.mappings || [])[idx];
        this._handleDialTurn(mapping, action);
      });
    });
  }

  _handleButtonPress(pin, entity) {
    if (entity && this._hass) {
      // Toggle entity in Home Assistant
      const domain = entity.split(".")[0];
      const service = domain === "scene" ? "turn_on" : "toggle";
      this._hass.callService(domain, service, { entity_id: entity });

      // Immediate visual feedback
      const led = this.shadowRoot.getElementById(`led-${pin}`);
      if (led) {
        led.classList.toggle("on");
      }
    } else if (this._hass) {
      // Fire bus event or call set_button_led
      const panelId = this._config.panel_id !== null ? this._config.panel_id : 0;
      this._hass.callService("lighting_controller", "set_button_led", {
        panel_id: panelId,
        pin: pin,
        state: true,
      });
      setTimeout(() => {
        this._hass.callService("lighting_controller", "set_button_led", {
          panel_id: panelId,
          pin: pin,
          state: false,
        });
      }, 300);
    }
  }

  _handleDialTurn(mapping, direction) {
    if (!mapping || !this._hass) return;
    if (mapping.entity) {
      // Step brightness up or down for a light entity
      const stateObj = this._hass.states[mapping.entity];
      if (stateObj && stateObj.attributes.brightness !== undefined) {
        const curBri = stateObj.attributes.brightness;
        const step = (mapping.step || 15) * (direction === "up" ? 1 : -1);
        const newBri = Math.max(0, Math.min(255, curBri + step));
        this._hass.callService("light", "turn_on", {
          entity_id: mapping.entity,
          brightness: newBri,
        });
      }
    }
  }

  _updateLedStates() {
    if (!this.shadowRoot || !this._hass) return;

    const mappings = this._config.mappings || [];
    mappings.forEach((m, idx) => {
      const pin = m.button_pin !== undefined ? m.button_pin : idx;
      const led = this.shadowRoot.getElementById(`led-${pin}`);
      if (led && m.entity) {
        const stateObj = this._hass.states[m.entity];
        const isOn = stateObj && (stateObj.state === "on" || stateObj.state === "active");
        if (isOn) {
          led.classList.add("on");
        } else {
          led.classList.remove("on");
        }
      }
    });
  }

  getCardSize() {
    return 3;
  }

  static getStubConfig() {
    return {
      title: "Lighting Keypad",
      panel_id: 0,
      mappings: [
        { button_pin: 0, label: "Overhead Lights", entity: "" },
        { button_pin: 1, label: "Reading Lamp", entity: "" },
        { button_pin: 2, label: "Nightlight", entity: "" },
        { button_pin: 3, label: "Room Dimmer", type: "dial", entity: "" }
      ]
    };
  }
}

// Register the custom element
if (!customElements.get("lighting-controller-card")) {
  customElements.define("lighting-controller-card", LightingControllerCard);
}

// Register with Home Assistant Lovelace card picker
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "lighting-controller-card")) {
  window.customCards.push({
    type: "lighting-controller-card",
    name: "Lighting Controller Panel Card",
    description: "Tactile lighting panel with live glowing pilot LEDs and encoder dials.",
    preview: true,
  });
}

