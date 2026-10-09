// =============================================================================
// DEC Deepal — Tarjeta para los paneles de Home Assistant
// =============================================================================
//
//   type: custom:dec-deepal-card
//   device_id: <dispositivo del coche>     (opcional: si falta, el primero)
//
// Qué muestra (diseño cerrado con bocetos, 09-10-2026):
//   - Cabecera: nombre del coche, "Actualizado: ..." y botón de actualizar.
//   - Vista isométrica del coche (la entidad de imagen de la integración).
//     Tocarla no hace nada (a propósito).
//   - Batería: icono según el nivel (verde ≥ 50 %, amarillo < 50 %, rojo
//     < 15 %; con rayo si carga), autonomía y estado de carga, más la barra.
//   - Línea de estado (encima de la batería, a la derecha): un tic verde si
//     no hay avisos; si los hay, el icono de cada testigo encendido.
//   - Testigo de mantenimiento (una llave inglesa en la línea de estado):
//     ámbar cuando se acerca la revisión, rojo si está vencida. Es el único
//     testigo que se puede pulsar: abre una ventana con los días y kilómetros
//     que quedan, lo que incluye la revisión, el historial y el botón para
//     registrarla (con confirmación).
//   - Cinco botones: Confort, Bloqueo, Maletero, Ventilar y Localizar
//     vehículo (este abre un menú con luces, claxon y las dos cosas).
//   - "Confort" abre una ventana con la vista interior y, encima de la foto,
//     los botones de volante y asientos (sin color: blanco = encendido,
//     atenuado = apagado, con el nivel 1-3), la temperatura y el climatizador.
//   - Bloqueo, Maletero y Ventilar usan el PIN: piden confirmación y, si el
//     usuario tiene el modo "desbloqueo previo", la tarjeta lo hace sola.
//
// Cómo encuentra las entidades
// ----------------------------
// No hay que configurarlas. Cada entidad de la integración lleva una clave
// interna (translation_key: "battery_level", "doors"...) que no cambia aunque
// el usuario renombre la entidad. La tarjeta busca, entre las entidades del
// dispositivo elegido, la de cada clave (hass.entities).
//
// Sin herramientas de compilación: JavaScript plano en un solo archivo, sin
// dependencias. Lo carga dec-icons.js (ver frontend.py).
// =============================================================================

(() => {
  const TAG = "dec-deepal-card";
  if (customElements.get(TAG)) return;

  const DOMAIN = "dec_deepal";

  // Recorte de la vista interior (1125×1500) que se enseña en "Confort" y
  // posición de cada botón sobre ese recorte, en % (Deepal S05).
  const INTERIOR = { width: 1125, height: 1500, crop: { x: 190, y: 300, w: 745, h: 560 } };
  // Recorte de la vista isométrica (750×500): se quita el aire de los lados y
  // de abajo, dejando sitio arriba para el capó y el portón abiertos.
  const ISOMETRIC = { width: 750, height: 500, crop: { x: 10, y: 40, w: 730, h: 405 } };
  const HOTSPOTS = [
    { key: "switch.steering_wheel_heat", icon: "mdi:steering", x: 27.4, y: 16, label: "Volante calefactado" },
    { key: "number.seat_vent_driver", icon: "mdi:fan", x: 21.3, y: 57.5, label: "Ventilación asiento conductor" },
    { key: "number.seat_heat_driver", icon: "mdi:heat-wave", x: 30.8, y: 57.5, label: "Calefacción asiento conductor" },
    { key: "number.seat_vent_passenger", icon: "mdi:fan", x: 67, y: 57.5, label: "Ventilación asiento acompañante" },
    { key: "number.seat_heat_passenger", icon: "mdi:heat-wave", x: 76.5, y: 57.5, label: "Calefacción asiento acompañante" },
  ];

  // Testigos de la línea de estado. "red" = grave; el resto, ámbar.
  const AMBER = "var(--warning-color, #f9a825)";
  const RED = "var(--error-color, #db4437)";
  const WARNINGS = [
    { keys: ["binary_sensor.warning_brake"], icon: "mdi:car-brake-alert", color: RED },
    { keys: ["binary_sensor.warning_brake_fluid"], icon: "mdi:car-brake-fluid-level", color: RED },
    { keys: ["binary_sensor.warning_airbag"], icon: "mdi:airbag", color: RED },
    { keys: ["binary_sensor.warning_12v_battery"], icon: "mdi:car-battery", color: RED },
    { keys: ["binary_sensor.warning_coolant_temperature"], icon: "mdi:coolant-temperature", color: RED },
    { keys: ["binary_sensor.warning_power_system"], icon: "mdi:engine", color: RED },
    { keys: ["binary_sensor.warning_abs"], icon: "mdi:car-brake-abs", color: AMBER },
    { keys: ["binary_sensor.warning_eps"], icon: "mdi:steering", color: AMBER },
    {
      keys: [
        "binary_sensor.warning_tpms",
        "binary_sensor.tire_alarm_front_left",
        "binary_sensor.tire_alarm_front_right",
        "binary_sensor.tire_alarm_rear_left",
        "binary_sensor.tire_alarm_rear_right",
      ],
      icon: "mdi:car-tire-alert",
      color: AMBER,
    },
    { keys: ["binary_sensor.warning_power_limit"], icon: "mdi:speedometer-slow", color: AMBER },
    { keys: ["binary_sensor.warning_traction_battery_low"], icon: "mdi:battery-alert", color: AMBER },
    { keys: ["binary_sensor.key_battery_low"], icon: "dec:key_battery_low_on", color: AMBER },
  ];

  // Testigo de mantenimiento (solo existe si el usuario lo activó en Configurar).
  const MAINTENANCE = "binary_sensor.maintenance_due";

  const PIN_NOTE = "con tu PIN guardado. El coche puede tardar unos segundos en responder.";
  const NO_PIN = "Activa el control con PIN en Configurar (integración DEC Deepal) para usar este botón.";

  const escapeHtml = (text) =>
    String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  // ---------------------------------------------------------------------------
  // Estilos
  // ---------------------------------------------------------------------------
  const TILE_BG = "rgba(var(--rgb-primary-text-color, 33, 33, 33), 0.05)";
  const CARD_CSS = `
    :host { display: block; }
    ha-card { overflow: hidden; }
    .hdr { display: flex; align-items: center; gap: 8px; padding: 14px 8px 4px 16px; }
    .grow { flex: 1; min-width: 0; }
    .name { font-size: 20px; line-height: 1.2; color: var(--primary-text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .upd { font-size: 12px; color: var(--secondary-text-color); margin-top: 2px; }
    button { font: inherit; color: inherit; border: 0; background: none; margin: 0; cursor: pointer; -webkit-tap-highlight-color: transparent; }
    .icon-btn { width: 40px; height: 40px; border-radius: 50%; color: var(--secondary-text-color); display: flex; align-items: center; justify-content: center; }
    .icon-btn:hover { background: ${TILE_BG}; }
    .spin ha-icon { animation: dec-spin 1s linear infinite; }
    @keyframes dec-spin { to { transform: rotate(360deg); } }
    .carbox { position: relative; overflow: hidden; aspect-ratio: ${ISOMETRIC.crop.w} / ${ISOMETRIC.crop.h}; }
    .carbox[hidden] { display: none; }
    .carbox.plain { aspect-ratio: auto; }
    .carbox.plain .car { position: static; width: 100%; }
    .car { position: absolute; max-width: none; display: block;
      width: ${(ISOMETRIC.width / ISOMETRIC.crop.w) * 100}%;
      left: ${(-ISOMETRIC.crop.x / ISOMETRIC.crop.w) * 100}%;
      top: ${(-ISOMETRIC.crop.y / ISOMETRIC.crop.h) * 100}%; }
    .range { display: flex; align-items: center; gap: 8px; padding: 0 16px; }
    .range .batt { --mdc-icon-size: 26px; }
    .range .km { font-size: 24px; color: var(--primary-text-color); }
    .range .charge { font-size: 14px; color: var(--secondary-text-color); display: flex; align-items: center; gap: 4px; --mdc-icon-size: 18px; }
    .bar { height: 8px; border-radius: 4px; background: ${TILE_BG}; margin: 6px 16px 14px; overflow: hidden; }
    .bar i { display: block; height: 100%; border-radius: 4px; transition: width .4s; }
    .status { display: flex; justify-content: flex-end; align-items: center; gap: 10px; padding: 0 16px 10px; min-height: 22px; --mdc-icon-size: 22px; }
    .status .ok { color: var(--success-color, #43a047); }
    .status button { padding: 0; display: flex; }
    /* 5 botones: 3 arriba y 2 centrados abajo (rejilla de 6 columnas). */
    .tiles { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 8px; padding: 0 12px 12px; }
    .tiles .tile { grid-column: span 2; }
    .tiles .tile:nth-child(4) { grid-column: 2 / span 2; }
    .tiles .tile:nth-child(5) { grid-column: 4 / span 2; }
    .tile { background: ${TILE_BG}; border-radius: 12px; padding: 10px 6px; display: flex; flex-direction: column; align-items: center; gap: 4px; text-align: center; min-height: 84px; color: var(--secondary-text-color); transition: opacity .2s, transform .1s; }
    .tile:active { transform: scale(.97); }
    .tile.on { color: var(--state-active-color, #ffc107); }
    .tile.pri { color: var(--primary-color); }
    .tile.busy { opacity: .45; pointer-events: none; }
    .tile b { font-size: 12px; font-weight: 500; color: var(--primary-text-color); }
    .tile small { font-size: 11px; color: var(--secondary-text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
    .msg { padding: 16px; color: var(--secondary-text-color); font-size: 14px; }
  `;
  const DIALOG_CSS = `
    :host { position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center; padding: 16px; box-sizing: border-box;
      background: rgba(0, 0, 0, .32); font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif); color: var(--primary-text-color); }
    .dlg { width: 100%; max-width: 440px; max-height: 100%; overflow: auto; background: var(--ha-card-background, var(--card-background-color, #fff));
      border-radius: 28px; box-shadow: 0 8px 24px rgba(0, 0, 0, .3); }
    button { font: inherit; color: inherit; border: 0; background: none; margin: 0; cursor: pointer; -webkit-tap-highlight-color: transparent; }
    .head { display: flex; align-items: center; gap: 4px; padding: 8px 8px 4px; }
    .head h2 { margin: 0; font-size: 20px; font-weight: 400; flex: 1; }
    .icon-btn { width: 40px; height: 40px; border-radius: 50%; color: var(--secondary-text-color); display: flex; align-items: center; justify-content: center; }
    .stage { position: relative; margin: 4px 12px 0; border-radius: 16px; overflow: hidden; background: ${TILE_BG};
      aspect-ratio: ${INTERIOR.crop.w} / ${INTERIOR.crop.h}; }
    .stage img { position: absolute; max-width: none;
      width: ${(INTERIOR.width / INTERIOR.crop.w) * 100}%;
      left: ${(-INTERIOR.crop.x / INTERIOR.crop.w) * 100}%;
      top: ${(-INTERIOR.crop.y / INTERIOR.crop.h) * 100}%; }
    .hot { position: absolute; transform: translate(-50%, -50%); width: 44px; height: 44px; display: flex; align-items: center; justify-content: center;
      color: #fff; --mdc-icon-size: 34px; filter: drop-shadow(0 1px 2px rgba(0, 0, 0, .65)); opacity: .38; transition: opacity .2s; }
    .hot.on { opacity: 1; }
    .hot.busy { animation: dec-pulse .8s ease-in-out infinite; pointer-events: none; }
    @keyframes dec-pulse { 50% { opacity: .25; } }
    .hot u { position: absolute; left: 82%; top: -2px; font-size: 15px; font-weight: 500; text-decoration: none; }
    .temp { display: flex; align-items: center; justify-content: center; gap: 18px; padding: 16px 12px 14px; }
    .temp b { font-size: 40px; font-weight: 400; min-width: 3.2ch; text-align: center; }
    .temp sup { font-size: 16px; color: var(--secondary-text-color); }
    .round { width: 48px; height: 48px; border-radius: 50%; background: ${TILE_BG}; display: flex; align-items: center; justify-content: center; color: var(--secondary-text-color); }
    .power { display: flex; align-items: center; justify-content: center; gap: 8px; margin: 0 12px; width: calc(100% - 24px); padding: 12px; border-radius: 12px;
      background: ${TILE_BG}; font-size: 14px; font-weight: 500; --mdc-icon-size: 20px; }
    .power ha-icon { color: var(--secondary-text-color); }
    .power.on { background: rgba(var(--rgb-primary-color, 3, 169, 244), .15); }
    .power.on ha-icon { color: var(--primary-color); }
    .power.busy { opacity: .5; pointer-events: none; }
    .info { font-size: 12px; color: var(--secondary-text-color); text-align: center; margin: 12px 12px 16px; }
    .three { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; padding: 8px 12px 16px; }
    .tile { background: ${TILE_BG}; border-radius: 12px; padding: 10px 6px; display: flex; flex-direction: column; align-items: center; gap: 4px;
      text-align: center; min-height: 84px; color: var(--secondary-text-color); }
    .tile:active { transform: scale(.97); }
    .tile b { font-size: 12px; font-weight: 500; color: var(--primary-text-color); }
    .tile small { font-size: 11px; color: var(--secondary-text-color); }
    .confirm { padding: 20px 24px 8px; }
    .confirm h2 { margin: 0 0 10px; font-size: 22px; font-weight: 400; }
    .confirm p { margin: 0; font-size: 14px; color: var(--secondary-text-color); line-height: 1.5; }
    .btns { display: flex; justify-content: flex-end; gap: 8px; padding: 14px 16px 16px; }
    .tb { font-size: 14px; font-weight: 500; color: var(--primary-color); padding: 10px 14px; border-radius: 20px; }
    .tb.fill { background: var(--primary-color); color: var(--text-primary-color, #fff); }
    .mt { padding: 0 20px 4px; }
    .mt .next { font-size: 15px; font-weight: 500; margin: 4px 0 10px; display: flex; align-items: center; gap: 8px; --mdc-icon-size: 22px; }
    .mt .two { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
    .mt .stat { background: ${TILE_BG}; border-radius: 12px; padding: 10px 12px; }
    .mt .stat b { display: block; font-size: 24px; font-weight: 400; }
    .mt .stat small, .mt .due { font-size: 12px; color: var(--secondary-text-color); }
    .mt .due { margin: 8px 0 0; }
    .mt h3 { font-size: 13px; font-weight: 500; margin: 16px 0 6px; }
    .mt ul { margin: 0; padding-left: 18px; font-size: 13px; line-height: 1.5; color: var(--secondary-text-color); }
  `;

  // ---------------------------------------------------------------------------
  // Ventana emergente mínima (se cuelga de <body> para quedar por encima)
  // ---------------------------------------------------------------------------
  function openDialog(html, onAction) {
    const host = document.createElement("div");
    const root = host.attachShadow({ mode: "open" });
    root.innerHTML = `<style>${DIALOG_CSS}</style><div class="dlg" role="dialog" aria-modal="true">${html}</div>`;
    const close = () => {
      document.removeEventListener("keydown", onKey);
      host.remove();
      if (dialog.onClose) dialog.onClose();
    };
    const onKey = (event) => event.key === "Escape" && close();
    document.addEventListener("keydown", onKey);
    host.addEventListener("click", (event) => {
      const path = event.composedPath();
      if (path[0] === host) return close(); // toque en el fondo oscuro
      const target = path.find((node) => node.dataset && node.dataset.action);
      if (!target) return undefined;
      if (target.dataset.action === "close") return close();
      return onAction(target.dataset.action, target, dialog);
    });
    const dialog = { root, close, onClose: null };
    document.body.append(host);
    return dialog;
  }

  // ---------------------------------------------------------------------------
  // La tarjeta
  // ---------------------------------------------------------------------------
  class DecDeepalCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._config = {};
      this._ids = {}; // "dominio.clave" → entity_id
      this._seen = []; // estados usados en el último pintado
      this._busy = new Set();
      this._comfort = null; // ventana de Confort abierta
      this._pendingTemp = null;
      this._tempTimer = null;
      this.shadowRoot.addEventListener("click", (event) => this._onClick(event));
    }

    // --- API de las tarjetas de Home Assistant --------------------------------

    static getStubConfig(hass) {
      const first = Object.values((hass && hass.entities) || {}).find((entry) => entry.platform === DOMAIN && entry.device_id);
      return { device_id: first ? first.device_id : "" };
    }

    static getConfigForm() {
      return {
        schema: [{ name: "device_id", selector: { device: { filter: [{ integration: DOMAIN }] } } }],
        computeLabel: () => "Coche",
      };
    }

    setConfig(config) {
      this._config = config || {};
      this._ids = {};
      this._built = false;
      if (this._hass) this._update();
    }

    set hass(hass) {
      this._hass = hass;
      this._update();
    }

    getCardSize() {
      return 8;
    }

    getGridOptions() {
      return { columns: 12, min_columns: 6, min_rows: 6 };
    }

    disconnectedCallback() {
      if (this._comfort) this._comfort.close();
    }

    // --- Entidades -------------------------------------------------------------

    _deviceId() {
      return this._config.device_id || DecDeepalCard.getStubConfig(this._hass).device_id;
    }

    _discover() {
      const deviceId = this._deviceId();
      const ids = {};
      for (const [entityId, entry] of Object.entries(this._hass.entities || {})) {
        if (entry.platform !== DOMAIN || entry.device_id !== deviceId || !entry.translation_key) continue;
        ids[`${entityId.split(".")[0]}.${entry.translation_key}`] = entityId;
      }
      this._ids = ids;
      this._registry = this._hass.entities;
    }

    _state(key) {
      const entityId = this._ids[key];
      return entityId ? this._hass.states[entityId] : undefined;
    }

    _value(key) {
      const state = this._state(key);
      return state && !["unknown", "unavailable"].includes(state.state) ? state.state : undefined;
    }

    _number(key) {
      const value = Number(this._value(key));
      return Number.isFinite(value) ? value : undefined;
    }

    _format(key) {
      const state = this._state(key);
      if (!state || ["unknown", "unavailable"].includes(state.state)) return undefined;
      return this._hass.formatEntityState ? this._hass.formatEntityState(state) : state.state;
    }

    _name() {
      const device = (this._hass.devices || {})[this._deviceId()];
      return (device && (device.name_by_user || device.name)) || "Deepal";
    }

    // --- Pintado ---------------------------------------------------------------

    _update() {
      if (!this._hass) return;
      if (this._registry !== this._hass.entities) this._discover();
      const tracked = Object.values(this._ids).map((entityId) => this._hass.states[entityId]);
      const changed = tracked.length !== this._seen.length || tracked.some((state, index) => state !== this._seen[index]);
      if (!this._built) this._build();
      else if (!changed && !this._dirty) return;
      this._seen = tracked;
      this._dirty = false;
      this._paint();
      if (this._comfort) this._paintComfort();
    }

    _build() {
      this._built = true;
      this._statusSignature = undefined;
      const tile = (action, label) =>
        `<button class="tile" data-action="${action}"><ha-icon></ha-icon><b>${label}</b><small></small></button>`;
      this.shadowRoot.innerHTML = `
        <style>${CARD_CSS}</style>
        <ha-card>
          <div class="hdr">
            <div class="grow"><div class="name"></div><div class="upd"></div></div>
            <button class="icon-btn" data-action="refresh" aria-label="Actualizar datos del vehículo"><ha-icon icon="mdi:refresh"></ha-icon></button>
          </div>
          <div class="carbox" hidden><img class="car" alt=""></div>
          <div class="msg" hidden></div>
          <div class="status"></div>
          <div class="range">
            <ha-icon class="batt"></ha-icon><span class="km"></span><span class="grow"></span>
            <span class="charge"><ha-icon></ha-icon><span></span></span>
          </div>
          <div class="bar"><i></i></div>
          <div class="tiles">
            ${tile("comfort", "Confort")}${tile("lock", "Bloqueo")}${tile("trunk", "Maletero")}
            ${tile("vent", "Ventilar")}${tile("locate", "Localizar vehículo")}
          </div>
        </ha-card>`;
    }

    _paint() {
      const $ = (selector) => this.shadowRoot.querySelector(selector);
      const found = Object.keys(this._ids).length > 0;
      $(".msg").hidden = found;
      $(".msg").textContent = found ? "" : "No encuentro el coche. Elige uno en la configuración de la tarjeta.";
      $(".name").textContent = this._name();
      $(".upd").textContent = `Actualizado: ${this._updatedText()}`;
      $('[data-action="refresh"]').classList.toggle("spin", this._busy.has("refresh"));

      // Imagen: vista isométrica (o, si no existe, la imagen DEC).
      const isometric = this._state("image.isometric_view");
      const image = isometric || this._state("image.dec_photo");
      const img = $(".car");
      const src = this._imageUrl(image);
      $(".carbox").hidden = !src;
      $(".carbox").classList.toggle("plain", !isometric); // la foto DEC va sin recortar
      if (src && img.getAttribute("src") !== src) img.setAttribute("src", src);

      // Batería y autonomía.
      const level = this._number("sensor.battery_level");
      const charging = this._value("binary_sensor.charging") === "on";
      const color = level === undefined ? "var(--secondary-text-color)" : level < 15 ? "var(--error-color, #db4437)" : level < 50 ? "var(--warning-color, #f9a825)" : "var(--success-color, #43a047)";
      $(".batt").setAttribute("icon", this._batteryIcon(level, charging));
      $(".batt").style.color = color;
      $(".km").textContent = this._format("sensor.range") || "—";
      $(".bar i").style.width = `${level === undefined ? 0 : Math.max(0, Math.min(100, level))}%`;
      $(".bar i").style.background = color;
      const plugged = (this._value("sensor.charge_status") || "disconnected") !== "disconnected";
      let chargeText = this._format("sensor.charge_status") || "";
      const remaining = this._value("sensor.remaining_charge_time_hhmm");
      if (charging && remaining) chargeText += ` · ${remaining} h`;
      $(".charge ha-icon").setAttribute("icon", plugged ? "mdi:power-plug" : "mdi:power-plug-off-outline");
      $(".charge span").textContent = chargeText;
      $(".charge").hidden = !chargeText;

      // Línea de estado: tic verde, o el icono de cada testigo encendido.
      // El de mantenimiento va el último y se puede pulsar.
      const active = WARNINGS.filter((warning) => warning.keys.some((key) => this._value(key) === "on"));
      const maintenance = this._value(MAINTENANCE) === "on" ? this._state(MAINTENANCE).attributes.nivel || "soon" : "";
      const signature = `${active.map((warning) => warning.icon).join("|")}#${maintenance}`;
      if (this._statusSignature !== signature) {
        this._statusSignature = signature;
        const icons = active.map((warning) => `<ha-icon icon="${warning.icon}" style="color:${warning.color}"></ha-icon>`);
        if (maintenance)
          icons.push(
            `<button data-action="maintenance" aria-label="Mantenimiento"><ha-icon icon="mdi:wrench" style="color:${maintenance === "overdue" ? RED : AMBER}"></ha-icon></button>`
          );
        $(".status").innerHTML = icons.length ? icons.join("") : '<ha-icon class="ok" icon="mdi:check-circle"></ha-icon>';
      }

      // Los cinco botones.
      const tiles = this._tiles();
      for (const [action, data] of Object.entries(tiles)) {
        const element = $(`.tile[data-action="${action}"]`);
        element.querySelector("ha-icon").setAttribute("icon", data.icon);
        element.querySelector("small").textContent = data.text;
        element.classList.toggle("on", Boolean(data.on));
        element.classList.toggle("pri", Boolean(data.primary));
        element.classList.toggle("busy", this._busy.has(action));
      }
    }

    _tiles() {
      const climateOn = (this._value("climate.cabin_climate") || "off") !== "off";
      const comfortOn = climateOn || HOTSPOTS.some((spot) => this._spotLevel(spot) > 0);
      const climate = this._state("climate.cabin_climate");
      const target = climate && climate.attributes.temperature;
      const inside = this._format("sensor.inside_temperature");
      const comfortText = climateOn
        ? `Encendido${target != null ? ` · ${this._temp(target)} °C` : ""}`
        : `${comfortOn ? "Asientos" : "Apagado"}${inside ? ` · ${inside}` : ""}`;

      const lock = this._value("lock.doors");
      const central = this._value("binary_sensor.central_locking"); // on = desbloqueado
      const unlocked = lock ? lock === "unlocked" : central === "on";
      const lockKnown = Boolean(lock || central);

      const trunkOpen = this._value("binary_sensor.trunk") === "on";
      // La persiana de ventanillas va invertida: "closed" = entreabiertas.
      const venting = this._value("cover.windows") === "closed";
      const anyWindow = ["front_left", "front_right", "rear_left", "rear_right"].some(
        (position) => this._value(`binary_sensor.window_${position}`) === "on"
      );

      return {
        comfort: { icon: "mdi:sun-snowflake-variant", text: comfortText, primary: true },
        lock: {
          icon: unlocked ? "mdi:lock-open-variant" : "mdi:lock",
          text: lockKnown ? (unlocked ? "Desbloqueado" : "Bloqueado") : "—",
          on: lockKnown && unlocked,
        },
        trunk: { icon: trunkOpen ? "dec:trunk_open" : "dec:trunk_closed", text: trunkOpen ? "Abierto" : "Cerrado", on: trunkOpen },
        vent: { icon: "mdi:weather-windy", text: venting ? "Ventilando" : anyWindow ? "Abiertas" : "Cerradas", on: venting || anyWindow },
        locate: { icon: "mdi:car-search", text: "Luces y claxon" },
      };
    }

    _batteryIcon(level, charging) {
      if (level === undefined) return "mdi:battery-unknown";
      const step = Math.round(level / 10) * 10;
      if (charging) return step >= 100 ? "mdi:battery-charging-100" : `mdi:battery-charging-${Math.max(10, step)}`;
      if (step >= 100) return "mdi:battery";
      return step <= 0 ? "mdi:battery-outline" : `mdi:battery-${step}`;
    }

    _imageUrl(state) {
      if (!state || !state.attributes.entity_picture) return undefined;
      const picture = state.attributes.entity_picture;
      return `${picture}${picture.includes("?") ? "&" : "?"}state=${encodeURIComponent(state.state)}`;
    }

    _temp(value) {
      const language = (this._hass.locale && this._hass.locale.language) || "es";
      return Number(value).toLocaleString(language, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    }

    _updatedText() {
      const raw = this._value("sensor.last_update");
      const date = raw ? new Date(raw) : undefined;
      if (!date || Number.isNaN(date.getTime())) return "—";
      const language = (this._hass.locale && this._hass.locale.language) || "es";
      const time = date.toLocaleTimeString(language, { hour: "numeric", minute: "2-digit" });
      const startOfDay = (value) => new Date(value.getFullYear(), value.getMonth(), value.getDate()).getTime();
      const days = Math.round((startOfDay(new Date()) - startOfDay(date)) / 86400000);
      if (days === 0) return `hoy, ${time}`;
      if (days === 1) return `ayer, ${time}`;
      return `${date.toLocaleDateString(language, { day: "numeric", month: "short" })}, ${time}`;
    }

    // --- Acciones ----------------------------------------------------------------

    _toast(message) {
      this.dispatchEvent(new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }));
    }

    async _call(busyKey, domain, service, key, data) {
      const entityId = this._ids[key];
      if (!entityId) return false;
      this._busy.add(busyKey);
      this._repaint();
      try {
        await this._hass.callService(domain, service, { entity_id: entityId, ...(data || {}) });
        return true;
      } catch (error) {
        this._toast((error && error.message) || "No se pudo enviar la orden al coche.");
        return false;
      } finally {
        this._busy.delete(busyKey);
        this._repaint();
      }
    }

    _repaint() {
      this._dirty = true;
      this._update();
    }

    /** Orden con PIN: confirmación y, si hace falta, el desbloqueo previo. */
    _pinCommand(busyKey, title, button, domain, service, key) {
      if (!this._ids[key]) return this._toast(NO_PIN);
      const html = `
        <div class="confirm"><h2>${escapeHtml(title)}</h2>
          <p>Se enviará la orden a <b style="font-weight:500;color:var(--primary-text-color)">${escapeHtml(this._name())}</b> ${PIN_NOTE}</p></div>
        <div class="btns"><button class="tb" data-action="close">Cancelar</button><button class="tb fill" data-action="ok">${escapeHtml(button)}</button></div>`;
      openDialog(html, async (action, _target, dialog) => {
        if (action !== "ok") return;
        dialog.close();
        // Modo "desbloqueo previo": la entidad pin_arm bloqueada = no armado.
        if (this._value("lock.pin_arm") === "locked" && !(await this._call(busyKey, "lock", "unlock", "lock.pin_arm"))) return;
        await this._call(busyKey, domain, service, key);
      });
      return undefined;
    }

    _onClick(event) {
      const target = event.composedPath().find((node) => node.dataset && node.dataset.action);
      if (!target || !this._hass) return;
      const tiles = this._tiles();
      switch (target.dataset.action) {
        case "refresh":
          this._call("refresh", "button", "press", "button.refresh");
          break;
        case "comfort":
          this._openComfort();
          break;
        case "lock":
          if (tiles.lock.on) this._pinCommand("lock", "¿Bloquear las puertas?", "Bloquear", "lock", "lock", "lock.doors");
          else this._pinCommand("lock", "¿Desbloquear las puertas?", "Desbloquear", "lock", "unlock", "lock.doors");
          break;
        case "trunk":
          if (tiles.trunk.on) this._pinCommand("trunk", "¿Cerrar el maletero?", "Cerrar", "cover", "close_cover", "cover.trunk_control");
          else this._pinCommand("trunk", "¿Abrir el maletero?", "Abrir", "cover", "open_cover", "cover.trunk_control");
          break;
        case "vent":
          // Persiana invertida: open_cover SUBE los cristales; close_cover los entreabre.
          if (tiles.vent.on) this._pinCommand("vent", "¿Cerrar las ventanillas?", "Cerrar", "cover", "open_cover", "cover.windows");
          else this._pinCommand("vent", "¿Entreabrir las ventanillas para ventilar?", "Ventilar", "cover", "close_cover", "cover.windows");
          break;
        case "locate":
          this._openLocate();
          break;
        case "maintenance":
          this._openMaintenance();
          break;
        default:
      }
    }

    // --- Menú "Localizar vehículo" ------------------------------------------------

    _openLocate() {
      const option = (key, icon, label, text) =>
        this._ids[key]
          ? `<button class="tile" data-action="go" data-key="${key}"><ha-icon icon="${icon}"></ha-icon><b>${label}</b><small>${text}</small></button>`
          : "";
      const html = `
        <div class="head"><button class="icon-btn" data-action="close" aria-label="Cerrar"><ha-icon icon="mdi:close"></ha-icon></button><h2>Localizar vehículo</h2></div>
        <div class="three">
          ${option("button.flash_lights", "mdi:alarm-light-outline", "Luces", "Parpadear")}
          ${option("button.honk_horn", "mdi:bullhorn", "Claxon", "Tocar")}
          ${option("button.flash_and_honk", "mdi:alarm-light", "Luces y claxon", "Las dos cosas")}
        </div>`;
      openDialog(html, (action, target, dialog) => {
        if (action !== "go") return;
        dialog.close();
        this._call("locate", "button", "press", target.dataset.key);
      });
    }

    // --- Ventana de Mantenimiento ---------------------------------------------------

    _openMaintenance() {
      const state = this._state(MAINTENANCE);
      if (!state) return;
      const data = state.attributes;
      const language = (this._hass.locale && this._hass.locale.language) || "es";
      const number = (value) => Math.abs(Number(value)).toLocaleString(language, { useGrouping: "always" });
      const day = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString(language, { day: "numeric", month: "short", year: "numeric" });
      const overdue = data.nivel === "overdue";
      const stat = (value, unit) =>
        value == null
          ? `<div class="stat"><b>—</b><small>${unit}</small></div>`
          : `<div class="stat"><b>${number(value)}</b><small>${unit} ${Number(value) < 0 ? "de retraso" : "restantes"}</small></div>`;
      const list = (title, items) => (items.length ? `<h3>${title}</h3><ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : "");
      const history = (data.historial || [])
        .slice()
        .reverse()
        .map((item) => `${item.number}ª revisión · ${day(item.date)} · ${number(item.km)} km`);
      const html = `
        <div class="head"><button class="icon-btn" data-action="close" aria-label="Cerrar"><ha-icon icon="mdi:close"></ha-icon></button><h2>Mantenimiento</h2></div>
        <div class="mt">
          <div class="next"><ha-icon icon="mdi:wrench" style="color:${overdue ? RED : AMBER}"></ha-icon>${data.revision}ª revisión${overdue ? " · vencida" : ""}</div>
          <div class="two">${stat(data.dias_restantes, "días")}${stat(data.km_restantes, "km")}</div>
          <p class="due">Prevista el ${day(data.fecha_prevista)} o a los ${number(data.km_previstos)} km, lo que llegue antes.</p>
          ${list("Qué incluye", data.operaciones || [])}
          ${list("Historial", history)}
        </div>
        <div class="btns"><button class="tb fill" data-action="register">Registrar mantenimiento</button></div>`;
      openDialog(html, (action, _target, dialog) => {
        if (action !== "register") return;
        dialog.close();
        this._confirmMaintenance(data.revision);
      });
    }

    /** Confirmación antes de anotar la revisión (hoy, con los km actuales). */
    _confirmMaintenance(revision) {
      const odometer = this._format("sensor.odometer");
      const html = `
        <div class="confirm"><h2>¿Registrar la ${revision}ª revisión?</h2>
          <p>Se anotará que <b style="font-weight:500;color:var(--primary-text-color)">${escapeHtml(this._name())}</b> ha pasado la revisión hoy${
            odometer ? `, con ${escapeHtml(odometer)}` : ""
          }, y se empezará a contar para la siguiente. Si la pasó otro día, regístrala desde Configurar → Mantenimiento.</p></div>
        <div class="btns"><button class="tb" data-action="close">Cancelar</button><button class="tb fill" data-action="ok">Registrar</button></div>`;
      openDialog(html, async (action, _target, dialog) => {
        if (action !== "ok") return;
        dialog.close();
        try {
          await this._hass.callService(DOMAIN, "register_maintenance", { device_id: this._deviceId() });
          this._toast("Mantenimiento registrado.");
        } catch (error) {
          this._toast((error && error.message) || "No se pudo registrar el mantenimiento.");
        }
      });
    }

    // --- Ventana de Confort ----------------------------------------------------

    _spotLevel(spot) {
      if (spot.key.startsWith("switch.")) return this._value(spot.key) === "on" ? 1 : 0;
      return this._number(spot.key) || 0;
    }

    _openComfort() {
      if (this._comfort) return;
      const spots = HOTSPOTS.filter((spot) => this._ids[spot.key])
        .map(
          (spot) =>
            `<button class="hot" data-action="spot" data-key="${spot.key}" aria-label="${escapeHtml(spot.label)}"
               style="left:${spot.x}%;top:${spot.y}%"><ha-icon icon="${spot.icon}"></ha-icon><u></u></button>`
        )
        .join("");
      const html = `
        <div class="head"><button class="icon-btn" data-action="close" aria-label="Cerrar"><ha-icon icon="mdi:close"></ha-icon></button><h2>Confort</h2></div>
        <div class="stage"><img alt="">${spots}</div>
        <div class="temp">
          <button class="round" data-action="temp" data-step="-0.5" aria-label="Bajar temperatura"><ha-icon icon="mdi:minus"></ha-icon></button>
          <b><span class="target"></span><sup> °C</sup></b>
          <button class="round" data-action="temp" data-step="0.5" aria-label="Subir temperatura"><ha-icon icon="mdi:plus"></ha-icon></button>
        </div>
        <button class="power" data-action="power"><ha-icon icon="mdi:power"></ha-icon><span></span></button>
        <p class="info"></p>`;
      this._comfort = openDialog(html, (action, target) => this._onComfort(action, target));
      this._comfort.onClose = () => {
        this._comfort = null;
      };
      this._paintComfort();
    }

    _paintComfort() {
      const root = this._comfort.root;
      const image = this._state("image.interior_view");
      const img = root.querySelector(".stage img");
      const src = this._imageUrl(image);
      if (src && img.getAttribute("src") !== src) img.setAttribute("src", src);

      for (const element of root.querySelectorAll(".hot")) {
        const spot = HOTSPOTS.find((item) => item.key === element.dataset.key);
        const level = this._spotLevel(spot);
        element.classList.toggle("on", level > 0);
        element.classList.toggle("busy", this._busy.has(spot.key));
        element.querySelector("u").textContent = spot.key.startsWith("number.") && level > 0 ? String(level) : "";
      }

      const climate = this._state("climate.cabin_climate");
      const climateOn = (this._value("climate.cabin_climate") || "off") !== "off";
      const target = this._pendingTemp != null ? this._pendingTemp : climate && climate.attributes.temperature;
      root.querySelector(".target").textContent = target != null ? this._temp(target) : "—";
      root.querySelector(".temp").hidden = !climate;
      const power = root.querySelector(".power");
      power.hidden = !climate;
      power.classList.toggle("on", climateOn);
      power.classList.toggle("busy", this._busy.has("power"));
      power.querySelector("span").textContent = climateOn ? "Climatizador encendido" : "Climatizador apagado";

      const parts = [];
      const inside = this._format("sensor.inside_temperature");
      const humidity = this._format("sensor.cabin_humidity");
      const fan = this._value("sensor.fan_level");
      const recirculation = this._value("binary_sensor.air_recirculation");
      if (inside) parts.push(`Interior ${inside}`);
      if (humidity) parts.push(`Humedad ${humidity}`);
      if (climateOn && fan) parts.push(`Ventilador ${fan}`);
      if (climateOn && recirculation) parts.push(recirculation === "on" ? "Recirculando" : "Aire exterior");
      root.querySelector(".info").textContent = parts.join(" · ");
    }

    _onComfort(action, target) {
      if (action === "spot") {
        const key = target.dataset.key;
        if (key.startsWith("switch.")) this._call(key, "switch", "toggle", key);
        else this._call(key, "number", "set_value", key, { value: ((this._number(key) || 0) + 1) % 4 });
      } else if (action === "power") {
        const climateOn = (this._value("climate.cabin_climate") || "off") !== "off";
        this._call("power", "climate", climateOn ? "turn_off" : "turn_on", "climate.cabin_climate");
      } else if (action === "temp") {
        const climate = this._state("climate.cabin_climate");
        if (!climate) return;
        const current = this._pendingTemp != null ? this._pendingTemp : Number(climate.attributes.temperature);
        if (!Number.isFinite(current)) return;
        const min = Number(climate.attributes.min_temp) || 16;
        const max = Number(climate.attributes.max_temp) || 32;
        this._pendingTemp = Math.max(min, Math.min(max, current + Number(target.dataset.step)));
        this._paintComfort();
        // Se espera a que el usuario termine de pulsar antes de enviar la orden.
        clearTimeout(this._tempTimer);
        this._tempTimer = setTimeout(async () => {
          const temperature = this._pendingTemp;
          await this._call("temp", "climate", "set_temperature", "climate.cabin_climate", { temperature });
          if (this._pendingTemp === temperature) this._pendingTemp = null;
          if (this._comfort) this._paintComfort();
        }, 900);
      }
    }
  }

  customElements.define(TAG, DecDeepalCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: TAG,
    name: "DEC Deepal",
    description: "Tu Deepal de un vistazo: vista del coche, batería, confort y acciones rápidas.",
    preview: true,
    documentationURL: "https://github.com/manuelem1984/dec_deepal",
  });
})();
