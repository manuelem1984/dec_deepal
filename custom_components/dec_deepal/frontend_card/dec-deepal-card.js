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
//     registrarla (con confirmación). La misma ventana se abre siempre desde
//     "Otros → Mantenimiento".
//   - Testigos de ITV (portapapeles) y de seguro (escudo), con las mismas
//     reglas: ámbar si se acerca la fecha, rojo si vence; al pulsarlos abren su
//     ventana, que también está en "Otros". El número de póliza y los
//     teléfonos del seguro no están en ninguna entidad: la tarjeta se los pide
//     a la integración al abrir la ventana.
//   - Seis botones: Confort, Bloqueo, Maletero, Ventilar, Localizar vehículo
//     (abre un menú con luces, claxon y las dos cosas) y Otros (abre un menú
//     con el manual del coche y el mantenimiento).
//   - "Otros → Manual" abre el PDF del manual en el navegador (pestaña
//     nueva). El enlace lo da la integración (manual.py).
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
  const ITV = "binary_sensor.itv_due";
  const INSURANCE = "binary_sensor.insurance_due";
  // Testigos de vencimiento, en el orden en que salen. Todos se pueden pulsar.
  const DUE = [
    { key: MAINTENANCE, action: "maintenance", icon: "mdi:wrench", label: "Mantenimiento" },
    { key: ITV, action: "itv", icon: "mdi:clipboard-check-outline", label: "ITV" },
    { key: INSURANCE, action: "insurance", icon: "mdi:shield-car", label: "Seguro" },
  ];
  const INSURANCE_KINDS = {
    third_party: "Terceros",
    third_party_plus: "Terceros ampliado",
    comprehensive_excess: "Todo riesgo con franquicia",
    comprehensive: "Todo riesgo sin franquicia",
  };

  const NO_ITV = "La ITV de este coche no está activada. Actívala en Ajustes → Dispositivos y servicios → DEC Deepal → Configurar → ITV.";
  const NO_INSURANCE =
    "El seguro de este coche no está activado. Actívalo en Ajustes → Dispositivos y servicios → DEC Deepal → Configurar → Seguro.";
  const NO_MAINTENANCE =
    "El mantenimiento de este coche no está activado. Actívalo en Ajustes → Dispositivos y servicios → DEC Deepal → Configurar → Mantenimiento.";

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
    /* 6 botones en dos filas de 3. */
    .tiles { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; padding: 0 12px 12px; }
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
    /* Menú con menos de tres opciones: centradas, con el mismo ancho que en una fila de tres. */
    .three.center { display: flex; justify-content: center; }
    .three.center .tile { flex: 0 1 calc((100% - 16px) / 3); }
    /* Menú "Otros": de dos en dos, centrado si sobra uno. */
    .three.pairs { display: flex; flex-wrap: wrap; justify-content: center; }
    .three.pairs .tile { flex: 0 1 calc((100% - 8px) / 2); box-sizing: border-box; }
    .mt dl { display: grid; grid-template-columns: auto 1fr; gap: 6px 14px; margin: 0; font-size: 13px; }
    .mt dt { color: var(--secondary-text-color); }
    .mt dd { margin: 0; text-align: right; }
    .calls { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 14px; }
    .calls:empty { display: none; }
    .call { display: flex; align-items: center; justify-content: center; gap: 6px; padding: 10px; border-radius: 12px; font-size: 13px; font-weight: 500;
      text-decoration: none; color: var(--primary-color); background: rgba(var(--rgb-primary-color, 3, 169, 244), .12); --mdc-icon-size: 18px; }
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
    a.tile { text-decoration: none; box-sizing: border-box; }
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
      this._checkManual(deviceId);
    }

    /** Pregunta a la integración (una vez por coche) el enlace del manual. */
    async _checkManual(deviceId) {
      if (!deviceId || this._manualDevice === deviceId || !this._hass.callApi) return;
      this._manualDevice = deviceId;
      this._manualUrl = "";
      try {
        const info = await this._hass.callApi("GET", `dec_deepal/manual_info/${deviceId}`);
        const url = (info && info.url) || "";
        if (this._manualDevice === deviceId && /^https?:\/\//.test(url)) this._manualUrl = url;
      } catch (_error) {
        this._manualDevice = undefined; // se volverá a intentar
      }
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
            ${tile("vent", "Ventilar")}${tile("locate", "Localizar vehículo")}${tile("others", "Otros")}
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
      // Los de vencimiento (mantenimiento, ITV, seguro) van al final y se pueden pulsar.
      const active = WARNINGS.filter((warning) => warning.keys.some((key) => this._value(key) === "on"));
      const due = DUE.map((item) => ({ ...item, level: this._dueLevel(item.key) })).filter((item) => item.level);
      const signature = `${active.map((warning) => warning.icon).join("|")}#${due.map((item) => item.action + item.level).join("|")}`;
      if (this._statusSignature !== signature) {
        this._statusSignature = signature;
        const icons = active.map((warning) => `<ha-icon icon="${warning.icon}" style="color:${warning.color}"></ha-icon>`);
        for (const item of due)
          icons.push(
            `<button data-action="${item.action}" aria-label="${item.label}"><ha-icon icon="${item.icon}" style="color:${item.level === "overdue" ? RED : AMBER}"></ha-icon></button>`
          );
        $(".status").innerHTML = icons.length ? icons.join("") : '<ha-icon class="ok" icon="mdi:check-circle"></ha-icon>';
      }

      // Los seis botones.
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
        others: { icon: "mdi:dots-horizontal", text: this._othersShort() || "Manual y documentos" },
      };
    }

    /** Nivel de un testigo de vencimiento: "", "soon" u "overdue". */
    _dueLevel(key) {
      return this._value(key) === "on" ? this._state(key).attributes.nivel || "soon" : "";
    }

    /** Lo más urgente de mantenimiento, ITV y seguro (primero lo vencido). */
    _othersShort() {
      const items = [
        [this._dueLevel(MAINTENANCE), this._maintenanceShort()],
        [this._dueLevel(ITV), this._itvShort()],
        [this._dueLevel(INSURANCE), this._insuranceShort()],
      ].filter(([level]) => level);
      const urgent = items.find(([level]) => level === "overdue") || items[0];
      return urgent ? urgent[1] : "";
    }

    _days(count) {
      return `${count} ${Math.abs(count) === 1 ? "día" : "días"}`;
    }

    _itvShort() {
      const data = (this._state(ITV) || { attributes: {} }).attributes;
      if (data.dias_restantes == null) return "";
      if (data.dias_restantes < 0) return "ITV vencida";
      return data.dias_restantes === 0 ? "ITV: último día" : `ITV en ${this._days(data.dias_restantes)}`;
    }

    _insuranceShort() {
      const data = (this._state(INSURANCE) || { attributes: {} }).attributes;
      if (data.dias_desistimiento == null) return "";
      if (data.dias_desistimiento === 0) return "Seguro: último día";
      if (data.dias_desistimiento > 0 && data.nivel !== "ok") return `Seguro: ${this._days(data.dias_desistimiento)} para desistir`;
      return `Renueva el ${this._day(data.renovacion)}`;
    }

    /** Fecha ISO ("2027-03-14") como "14 mar 2027". */
    _day(iso) {
      if (!iso) return "—";
      const language = (this._hass.locale && this._hass.locale.language) || "es";
      return new Date(`${iso}T00:00:00`).toLocaleDateString(language, { day: "numeric", month: "short", year: "numeric" });
    }

    /** Resumen corto del mantenimiento, solo si la revisión está próxima o vencida. */
    _maintenanceShort() {
      if (this._value(MAINTENANCE) !== "on") return "";
      const data = this._state(MAINTENANCE).attributes;
      if (data.nivel === "overdue") return "Revisión vencida";
      const days = Number(data.dias_restantes);
      const km = data.km_restantes;
      // Se enseña lo que antes llegue a los escalones de aviso.
      if (km != null && Number(km) <= 3000 && days > 60) return `Revisión en ${Number(km).toLocaleString("es", { useGrouping: "always" })} km`;
      return `Revisión en ${days} ${days === 1 ? "día" : "días"}`;
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
        case "itv":
          this._openItv();
          break;
        case "insurance":
          this._openInsurance();
          break;
        case "others":
          this._openOthers();
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

    // --- Menú "Otros" ---------------------------------------------------------------

    _openOthers() {
      const maintenance = this._state(MAINTENANCE);
      const known = maintenance && maintenance.attributes.revision != null;
      const itv = this._state(ITV);
      const insurance = this._state(INSURANCE);
      const tone = (key) => {
        const level = this._dueLevel(key);
        return level ? ` style="color:${level === "overdue" ? RED : AMBER}"` : "";
      };
      // Un enlace de verdad (no un botón): así el navegador y la app del móvil
      // lo abren fuera, en una pestaña nueva, sin bloquearlo como ventana emergente.
      const manual = this._manualUrl
        ? `<a class="tile" data-action="manual" href="${escapeHtml(this._manualUrl)}" target="_blank" rel="noopener noreferrer"><ha-icon icon="mdi:book-open-variant"></ha-icon><b>Manual</b><small>Abrir PDF</small></a>`
        : "";
      // "ITV en 47 días" → "Quedan 47 días"; "Seguro: último día" → "Último día".
      const plain = (text, name) => {
        const short = text.replace(`${name} en `, "Quedan ").replace(new RegExp(`^${name}:? `), "");
        return short ? short.charAt(0).toUpperCase() + short.slice(1) : "—";
      };
      const option = (action, key, icon, label, text) =>
        `<button class="tile" data-action="${action}"><ha-icon icon="${icon}"${tone(key)}></ha-icon><b>${label}</b><small>${escapeHtml(text)}</small></button>`;
      const html = `
        <div class="head"><button class="icon-btn" data-action="close" aria-label="Cerrar"><ha-icon icon="mdi:close"></ha-icon></button><h2>Otros</h2></div>
        <div class="three pairs">
          ${manual}
          ${option("maintenance", MAINTENANCE, "mdi:wrench", "Mantenimiento", known ? `${maintenance.attributes.revision}ª revisión` : "Sin activar")}
          ${option("itv", ITV, "mdi:clipboard-check-outline", "ITV", itv ? plain(this._itvShort(), "ITV") : "Sin activar")}
          ${option("insurance", INSURANCE, "mdi:shield-car", "Seguro", insurance ? plain(this._insuranceShort(), "Seguro") : "Sin activar")}
        </div>`;
      openDialog(html, (action, _target, dialog) => {
        if (action === "manual") {
          // El enlace se abre solo; el menú se cierra un instante después.
          setTimeout(() => dialog.close(), 300);
          return;
        }
        if (!["maintenance", "itv", "insurance"].includes(action)) return;
        dialog.close();
        if (action === "maintenance") known ? this._openMaintenance() : this._message("Mantenimiento", NO_MAINTENANCE);
        else if (action === "itv") this._openItv();
        else this._openInsurance();
      });
    }

    // --- Ventana de ITV ---------------------------------------------------------------

    _openItv() {
      const state = this._state(ITV);
      if (!state || state.attributes.fecha_limite == null) return this._message("ITV", NO_ITV);
      const data = state.attributes;
      const overdue = data.dias_restantes < 0;
      const tone = overdue ? RED : data.nivel === "soon" ? AMBER : "var(--secondary-text-color)";
      const history = (data.historial || []).slice().reverse();
      const html = `
        <div class="head"><button class="icon-btn" data-action="close" aria-label="Cerrar"><ha-icon icon="mdi:close"></ha-icon></button><h2>ITV</h2></div>
        <div class="mt">
          <div class="next"><ha-icon icon="mdi:clipboard-check-outline" style="color:${tone}"></ha-icon>Próxima ITV${overdue ? " · vencida" : ""}</div>
          <div class="two">
            <div class="stat"><b>${Math.abs(data.dias_restantes)}</b><small>días ${overdue ? "de retraso" : "restantes"}</small></div>
            <div class="stat"><b>${this._day(data.fecha_limite)}</b><small>fecha límite</small></div>
          </div>
          <p class="due">Primera ITV a los 4 años de la matriculación. Después, cada 2 años hasta los 10 y cada año a partir de entonces.</p>
          <h3>Datos</h3>
          <dl><dt>Matriculación</dt><dd>${this._day(data.matriculacion)}</dd>
            <dt>Última ITV</dt><dd>${data.ultima_itv ? this._day(data.ultima_itv) : "Aún no ha pasado ninguna"}</dd></dl>
          ${history.length ? `<h3>Historial</h3><ul>${history.map((item) => `<li>${this._day(item)}</li>`).join("")}</ul>` : ""}
        </div>
        <div class="btns"><button class="tb fill" data-action="register">Registrar ITV pasada</button></div>`;
      openDialog(html, (action, _target, dialog) => {
        if (action !== "register") return;
        dialog.close();
        this._confirmItv();
      });
      return undefined;
    }

    _confirmItv() {
      const html = `
        <div class="confirm"><h2>¿Registrar la ITV?</h2>
          <p>Se anotará que <b style="font-weight:500;color:var(--primary-text-color)">${escapeHtml(this._name())}</b> ha pasado la ITV hoy y se calculará la siguiente. Si la pasó otro día, ponlo en Configurar → ITV.</p></div>
        <div class="btns"><button class="tb" data-action="close">Cancelar</button><button class="tb fill" data-action="ok">Registrar</button></div>`;
      openDialog(html, async (action, _target, dialog) => {
        if (action !== "ok") return;
        dialog.close();
        try {
          await this._hass.callService(DOMAIN, "register_itv", { device_id: this._deviceId() });
          this._toast("ITV registrada.");
        } catch (error) {
          this._toast((error && error.message) || "No se pudo registrar la ITV.");
        }
      });
    }

    // --- Ventana de Seguro ----------------------------------------------------------

    async _openInsurance() {
      const state = this._state(INSURANCE);
      if (!state || state.attributes.renovacion == null) return this._message("Seguro", NO_INSURANCE);
      const data = state.attributes;
      // Póliza y teléfonos: no están en la entidad, se piden a la integración.
      let extra = {};
      try {
        extra = (await this._hass.callApi("GET", `dec_deepal/insurance_info/${this._deviceId()}`)) || {};
      } catch (_error) {
        extra = {};
      }
      const lastDay = data.dias_desistimiento === 0;
      const tone = lastDay ? RED : data.nivel === "soon" ? AMBER : "var(--secondary-text-color)";
      const kind = INSURANCE_KINDS[data.tipo] || "";
      const title = [data.compania, kind].filter(Boolean).join(" · ") || "Seguro";
      const cancel =
        data.dias_desistimiento >= 0
          ? `<div class="stat"><b>${data.dias_desistimiento}</b><small>días para desistir</small></div>`
          : '<div class="stat"><b>—</b><small>plazo para desistir pasado</small></div>';
      const phone = (number, icon, label) =>
        number ? `<a class="call" href="tel:${escapeHtml(String(number).replace(/[^0-9+]/g, ""))}"><ha-icon icon="${icon}"></ha-icon>${label}</a>` : "";
      const html = `
        <div class="head"><button class="icon-btn" data-action="close" aria-label="Cerrar"><ha-icon icon="mdi:close"></ha-icon></button><h2>Seguro</h2></div>
        <div class="mt">
          <div class="next"><ha-icon icon="mdi:shield-car" style="color:${tone}"></ha-icon>${escapeHtml(title)}</div>
          <div class="two"><div class="stat"><b>${data.dias_renovacion}</b><small>días para la renovación</small></div>${cancel}</div>
          <p class="due">Renovación el ${this._day(data.renovacion)}. Para no renovar hay que avisar antes del ${this._day(data.limite_desistimiento)} (${data.dias_aviso} días antes).</p>
          <h3>Póliza</h3>
          <dl><dt>Compañía</dt><dd>${escapeHtml(data.compania || "—")}</dd>
            <dt>Nº de póliza</dt><dd>${escapeHtml(extra.policy || "—")}</dd>
            <dt>Tipo</dt><dd>${escapeHtml(kind || "—")}</dd></dl>
          <div class="calls">${phone(extra.phone_assistance, "mdi:tow-truck", "Asistencia")}${phone(extra.phone_company, "mdi:phone", "Compañía")}</div>
        </div>
        <div class="btns"></div>`;
      openDialog(html, () => undefined);
      return undefined;
    }

    /** Ventana con un texto y un único botón. */
    _message(title, text) {
      const html = `
        <div class="confirm"><h2>${escapeHtml(title)}</h2><p>${escapeHtml(text)}</p></div>
        <div class="btns"><button class="tb fill" data-action="close">Entendido</button></div>`;
      openDialog(html, () => undefined);
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
      // Sin aviso todavía, la llave va en gris; ámbar si se acerca y roja si está vencida.
      const tone = overdue ? RED : data.nivel === "soon" ? AMBER : "var(--secondary-text-color)";
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
          <div class="next"><ha-icon icon="mdi:wrench" style="color:${tone}"></ha-icon>${data.revision}ª revisión${overdue ? " · vencida" : ""}</div>
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
