/**
 * Lighting Controller Lovelace Card
 * =================================
 * Custom card for Home Assistant displaying physical lighting panels,
 * tactile push buttons with live glowing pilot LEDs, rotary encoders,
 * dynamic panel selection dropdown, auto-populated buttons, and interactive
 * event triggers for each button.
 */

class LightingControllerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._selectedPanelId = null;
    this._panelsCache = {};
  }

  setConfig(config) {
    this._config = {
      title: config.title || "Lighting Controller",
      panel_id: config.panel_id !== undefined ? Number(config.panel_id) : null,
      show_panel_select: config.show_panel_select !== false,
      ...config,
    };
    if (this._config.panel_id !== null && this._selectedPanelId === null) {
      this._selectedPanelId = this._config.panel_id;
    }
    this._render();
  }

  set hass(hass) {
    const oldHass = this._hass;
    this._hass = hass;

    // Scan hass.states to discover all panels and configured buttons/patterns
    const newPanels = this._discoverPanels();
    const panelsChanged = JSON.stringify(Object.keys(newPanels)) !== JSON.stringify(Object.keys(this._panelsCache));
    this._panelsCache = newPanels;

    // Auto-select first panel if none selected yet
    const panelIds = Object.keys(newPanels).map(Number);
    if (this._selectedPanelId === null || !panelIds.includes(this._selectedPanelId)) {
      if (this._config.panel_id !== null && panelIds.includes(this._config.panel_id)) {
        this._selectedPanelId = this._config.panel_id;
      } else if (panelIds.length > 0) {
        this._selectedPanelId = panelIds[0];
      }
    }

    // Re-render if panels discovered or selection initialized
    if (!oldHass || panelsChanged || !this.shadowRoot.querySelector(".card-content")) {
      this._render();
    } else {
      this._updateLiveStates();
    }
  }

  _discoverPanels() {
    if (!this._hass) return {};
    const panels = {};

    for (const [entityId, entity] of Object.entries(this._hass.states)) {
      const attr = entity.attributes || {};
      if (attr.panel_id !== undefined) {
        const pid = Number(attr.panel_id);
        if (!panels[pid]) {
          panels[pid] = {
            id: pid,
            name: attr.panel_name || `Panel ${pid}`,
            buttons: {},
          };
        }
        const p = panels[pid];
        if (attr.pin !== undefined) {
          const pin = Number(attr.pin);
          if (!p.buttons[pin]) {
            p.buttons[pin] = {
              pin: pin,
              name: attr.button_name || `Button ${pin + 1}`,
              type: attr.button_type || "switch",
              patterns: [],
              hasButtonEvent: false,
              hasDialEvent: false,
              entities: [],
            };
          }
          const btn = p.buttons[pin];
          btn.entities.push(entityId);

          if (attr.pattern_id !== undefined) {
            btn.patterns.push({
              pattern_id: Number(attr.pattern_id),
              name: attr.pattern_name || `Pattern ${attr.pattern_id}`,
              entity_id: entityId,
            });
          } else if (attr.button_type === "dial") {
            btn.type = "dial";
            btn.hasDialEvent = true;
          } else {
            btn.hasButtonEvent = true;
          }
        }
      }
    }

    return panels;
  }

  _render() {
    if (!this.shadowRoot) return;

    const panels = this._panelsCache || {};
    const panelList = Object.values(panels);
    const selectedPanel = panels[this._selectedPanelId] || (panelList.length > 0 ? panelList[0] : null);
    const title = this._config.title || (selectedPanel ? selectedPanel.name : "Lighting Controller");

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
          box-sizing: border-box;
        }
        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 12px;
          margin-bottom: 20px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          padding-bottom: 14px;
        }
        .header-title {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .header-title h2 {
          margin: 0;
          font-size: 1.25rem;
          font-weight: 600;
          letter-spacing: -0.01em;
          color: #f1f5f9;
        }
        .header-icon {
          color: #06b6d4;
          font-size: 1.3rem;
          display: flex;
          align-items: center;
        }
        .header-controls {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .panel-select-wrap {
          position: relative;
          display: flex;
          align-items: center;
        }
        .panel-select {
          appearance: none;
          background: rgba(30, 41, 59, 0.9);
          border: 1px solid rgba(6, 182, 212, 0.3);
          color: #38bdf8;
          font-size: 0.85rem;
          font-weight: 600;
          padding: 7px 32px 7px 12px;
          border-radius: 20px;
          cursor: pointer;
          outline: none;
          transition: all 0.2s ease;
        }
        .panel-select:hover, .panel-select:focus {
          border-color: #38bdf8;
          box-shadow: 0 0 10px rgba(6, 182, 212, 0.3);
        }
        .select-arrow {
          position: absolute;
          right: 12px;
          pointer-events: none;
          font-size: 0.65rem;
          color: #38bdf8;
        }
        .keypad-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 16px;
        }
        .button-card {
          background: rgba(30, 41, 59, 0.7);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 14px;
          padding: 16px;
          display: flex;
          flex-direction: column;
          gap: 12px;
          transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.2s ease;
          position: relative;
          overflow: hidden;
        }
        .button-card:hover {
          border-color: rgba(6, 182, 212, 0.3);
          box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
        }
        .button-card.action-pulse {
          animation: pulseBorder 0.6s cubic-bezier(0.4, 0, 0.2, 1);
        }
        @keyframes pulseBorder {
          0% {
            border-color: #38bdf8;
            box-shadow: 0 0 0 0 rgba(56, 189, 248, 0.7);
          }
          70% {
            border-color: #06b6d4;
            box-shadow: 0 0 0 8px rgba(56, 189, 248, 0);
          }
          100% {
            border-color: rgba(255, 255, 255, 0.08);
            box-shadow: none;
          }
        }
        .card-top {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
        }
        .button-name-group {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        .button-title {
          font-size: 0.95rem;
          font-weight: 600;
          color: #f8fafc;
        }
        .button-meta {
          font-size: 0.75rem;
          color: #94a3b8;
        }
        .pilot-led {
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: #334155;
          border: 2px solid #1e293b;
          box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.6);
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          flex-shrink: 0;
        }
        .pilot-led.on {
          background: #06b6d4;
          box-shadow: 0 0 10px #06b6d4, 0 0 18px rgba(6, 182, 212, 0.6);
        }
        .pilot-led.flash {
          background: #38bdf8 !important;
          box-shadow: 0 0 16px #38bdf8, 0 0 24px rgba(56, 189, 248, 0.8) !important;
          transform: scale(1.2);
        }
        .dial-controls {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
          background: rgba(15, 23, 42, 0.5);
          padding: 8px;
          border-radius: 10px;
          border: 1px solid rgba(255, 255, 255, 0.04);
        }
        .dial-btn {
          background: #1e293b;
          border: 1px solid rgba(255, 255, 255, 0.08);
          color: #38bdf8;
          font-size: 0.85rem;
          font-weight: 600;
          padding: 6px 14px;
          border-radius: 8px;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 6px;
          transition: all 0.15s ease;
        }
        .dial-btn:hover {
          background: #06b6d4;
          color: #0f172a;
          border-color: #06b6d4;
        }
        .dial-btn:active {
          transform: scale(0.95);
        }
        .events-section {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .events-label {
          font-size: 0.7rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: #64748b;
        }
        .events-list {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }
        .event-chip {
          background: rgba(15, 23, 42, 0.6);
          border: 1px solid rgba(255, 255, 255, 0.1);
          color: #cbd5e1;
          font-size: 0.78rem;
          font-weight: 500;
          padding: 5px 10px;
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.15s ease;
          display: inline-flex;
          align-items: center;
          gap: 4px;
          user-select: none;
        }
        .event-chip:hover {
          background: rgba(6, 182, 212, 0.2);
          border-color: #06b6d4;
          color: #38bdf8;
          transform: translateY(-1px);
        }
        .event-chip:active {
          transform: scale(0.95);
          background: #06b6d4;
          color: #0f172a;
        }
        .event-chip.press-chip {
          border-color: rgba(56, 189, 248, 0.25);
          color: #7dd3fc;
        }
        .empty-message {
          text-align: center;
          padding: 30px 10px;
          color: #94a3b8;
          font-size: 0.9rem;
        }
        .identify-btn {
          background: transparent;
          border: 1px solid rgba(255, 255, 255, 0.1);
          color: #94a3b8;
          font-size: 0.75rem;
          padding: 4px 8px;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.15s ease;
        }
        .identify-btn:hover {
          color: #f1f5f9;
          border-color: rgba(255, 255, 255, 0.3);
        }
      </style>

      <ha-card>
        <div class="header">
          <div class="header-title">
            <span class="header-icon">✦</span>
            <h2>${title}</h2>
          </div>
          <div class="header-controls">
            ${this._config.show_panel_select && panelList.length > 0 ? `
              <div class="panel-select-wrap">
                <select id="panelSelect" class="panel-select">
                  ${panelList.map(p => `
                    <option value="${p.id}" ${p.id === this._selectedPanelId ? "selected" : ""}>
                      ${p.name} (Panel ${p.id})
                    </option>
                  `).join("")}
                </select>
                <span class="select-arrow">▼</span>
              </div>
            ` : ""}
            ${selectedPanel ? `
              <button class="identify-btn" id="identifyPanelBtn" title="Flash panel LEDs">
                Identify
              </button>
            ` : ""}
          </div>
        </div>

        <div class="card-content">
          ${!selectedPanel ? `
            <div class="empty-message">
              No lighting panels detected. Ensure the Lighting Controller integration is connected.
            </div>
          ` : Object.keys(selectedPanel.buttons).length === 0 ? `
            <div class="empty-message">
              No configured buttons or dials found on ${selectedPanel.name}.
            </div>
          ` : `
            <div class="keypad-grid">
              ${Object.values(selectedPanel.buttons)
                .sort((a, b) => a.pin - b.pin)
                .map(btn => this._renderButtonCard(selectedPanel.id, btn))
                .join("")}
            </div>
          `}
        </div>
      </ha-card>
    `;

    this._attachEventHandlers(selectedPanel);
  }

  _renderButtonCard(panelId, btn) {
    const isDial = btn.type === "dial";
    const metaText = isDial ? `CLK Pin ${btn.pin + 1} • Rotary Encoder` : `Pin ${btn.pin + 1} • Switch`;

    return `
      <div class="button-card" id="btn-card-${btn.pin}">
        <div class="card-top">
          <div class="button-name-group">
            <span class="button-title">${btn.name}</span>
            <span class="button-meta">${metaText}</span>
          </div>
          <div class="pilot-led" id="led-${btn.pin}" title="Pilot LED"></div>
        </div>

        ${isDial ? `
          <div class="dial-controls">
            <button class="dial-btn" data-panel="${panelId}" data-pin="${btn.pin}" data-dir="down">
              ↺ Turn Down
            </button>
            <button class="dial-btn" data-panel="${panelId}" data-pin="${btn.pin}" data-dir="up">
              ↻ Turn Up
            </button>
          </div>
        ` : `
          <div class="events-section">
            <span class="events-label">Actions</span>
            <div class="events-list">
              <button class="event-chip press-chip" data-panel="${panelId}" data-pin="${btn.pin}" data-event="button" data-state="press">
                ⚡ Press
              </button>
            </div>
          </div>
        `}

        ${btn.patterns && btn.patterns.length > 0 ? `
          <div class="events-section">
            <span class="events-label">Configured Gestures</span>
            <div class="events-list">
              ${btn.patterns.map(pat => `
                <button class="event-chip" data-panel="${panelId}" data-pin="${btn.pin}" data-event="pattern" data-patid="${pat.pattern_id}" data-patname="${pat.name}">
                  ▶ ${pat.name}
                </button>
              `).join("")}
            </div>
          </div>
        ` : ""}
      </div>
    `;
  }

  _attachEventHandlers(selectedPanel) {
    const root = this.shadowRoot;

    // Panel dropdown selection change
    const selectEl = root.getElementById("panelSelect");
    if (selectEl) {
      selectEl.addEventListener("change", (e) => {
        this._selectedPanelId = Number(e.target.value);
        this._render();
      });
    }

    // Identify panel button
    const identifyBtn = root.getElementById("identifyPanelBtn");
    if (identifyBtn && selectedPanel) {
      identifyBtn.addEventListener("click", () => {
        if (this._hass) {
          this._hass.callService("lighting_controller", "identify_panel", {
            panel_id: selectedPanel.id,
          });
        }
      });
    }

    // Dial turn buttons
    root.querySelectorAll(".dial-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const panelId = Number(btn.getAttribute("data-panel"));
        const pin = Number(btn.getAttribute("data-pin"));
        const dir = btn.getAttribute("data-dir");
        this._triggerEvent({
          panel_id: panelId,
          pin: pin,
          event_type: "dial",
          direction: dir,
        });
      });
    });

    // Event & pattern chips
    root.querySelectorAll(".event-chip").forEach((chip) => {
      chip.addEventListener("click", (e) => {
        const panelId = Number(chip.getAttribute("data-panel"));
        const pin = Number(chip.getAttribute("data-pin"));
        const eventType = chip.getAttribute("data-event");

        if (eventType === "pattern") {
          const patId = Number(chip.getAttribute("data-patid"));
          const patName = chip.getAttribute("data-patname");
          this._triggerEvent({
            panel_id: panelId,
            pin: pin,
            event_type: "pattern",
            pattern_id: patId,
            pattern_name: patName,
          });
        } else if (eventType === "button") {
          const state = chip.getAttribute("data-state") || "press";
          this._triggerEvent({
            panel_id: panelId,
            pin: pin,
            event_type: "button",
            state: state,
          });
        }
      });
    });
  }

  _triggerEvent(payload) {
    if (!this._hass) return;

    // 1. Call custom service
    this._hass.callService("lighting_controller", "trigger_event", payload);

    // 2. Visual card pulse effect
    const cardEl = this.shadowRoot.getElementById(`btn-card-${payload.pin}`);
    if (cardEl) {
      cardEl.classList.remove("action-pulse");
      void cardEl.offsetWidth; // force DOM reflow
      cardEl.classList.add("action-pulse");
    }

    // 3. Temporary LED flash feedback
    const ledEl = this.shadowRoot.getElementById(`led-${payload.pin}`);
    if (ledEl) {
      ledEl.classList.add("flash");
      setTimeout(() => ledEl.classList.remove("flash"), 400);
    }
  }

  _updateLiveStates() {
    if (!this.shadowRoot || !this._hass) return;
    // Live updates can reflect any pilot lamp states or recent triggers
  }

  getCardSize() {
    return 4;
  }

  static getStubConfig() {
    return {
      title: "Lighting Panels",
      show_panel_select: true,
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
    description: "Interactive panel keypad with dropdown selector and button gesture triggers.",
    preview: true,
  });
}
