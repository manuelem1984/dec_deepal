// =============================================================================
// Banco de pruebas de la tarjeta: un Home Assistant falso, lo justo para ella
// =============================================================================
// Uso (desde las pruebas o desde la consola del navegador):
//
//   banco.montar({ idioma: "es", estados: { "climate.cabin_climate": ["heat_cool"] } })
//   banco.cambiar({ "binary_sensor.warning_abs": ["on"] })   // llega otra lectura
//   banco.registro                                            // qué ha pedido la tarjeta
//   banco.ventana()                                           // la ventana abierta encima
//
// Las entidades se nombran por su clave ("sensor.battery_level"), como hace la
// tarjeta. Sus entity_id son distintos a propósito (como si el usuario las
// hubiera renombrado): la tarjeta no debe depender de ellos.
// =============================================================================

(() => {
  const DEVICE = "dev1";
  // Imagen de relleno: la tarjeta solo necesita que haya "algo" que enseñar.
  const PIXEL = "coche.svg";
  const id = (key) => {
    const [domain, name] = key.split(".");
    return `${domain}.changote_${name}_x`;
  };

  /** Coche aparcado, cerrado, sin cargar y con todo apagado. `[estado, atributos]`. */
  const BASE = {
    "sensor.battery_level": [78],
    "sensor.range": [378, { unit_of_measurement: "km" }],
    "sensor.charge_status": ["disconnected"],
    "sensor.remaining_charge_time_hhmm": ["unknown"],
    "sensor.last_update": [new Date().toISOString()],
    "sensor.inside_temperature": [26, { unit_of_measurement: "°C" }],
    "sensor.cabin_humidity": [12, { unit_of_measurement: "%" }],
    "sensor.fan_level": [2],
    "sensor.odometer": [37500, { unit_of_measurement: "km" }],
    "binary_sensor.charging": ["off"],
    "binary_sensor.trunk": ["off"],
    "binary_sensor.central_locking": ["off"],
    "binary_sensor.window_front_left": ["off"],
    "binary_sensor.window_front_right": ["off"],
    "binary_sensor.window_rear_left": ["off"],
    "binary_sensor.window_rear_right": ["off"],
    "binary_sensor.air_recirculation": ["off"],
    "binary_sensor.key_battery_low": ["off"],
    "binary_sensor.warning_tpms": ["off"],
    "binary_sensor.warning_12v_battery": ["off"],
    "binary_sensor.warning_abs": ["off"],
    "binary_sensor.warning_airbag": ["off"],
    "binary_sensor.tire_alarm_front_left": ["off"],
    "binary_sensor.maintenance_due": ["off", {
      nivel: "ok", revision: 2, fecha_prevista: "2027-03-10", km_previstos: 39500,
      dias_restantes: 152, km_restantes: 8500,
      operaciones: ["Inspección general", "Cambio del líquido de frenos"],
      historial: [{ number: 1, date: "2026-03-10", km: 19500 }],
    }],
    "binary_sensor.itv_due": ["off", {
      nivel: "ok", fecha_limite: "2028-11-26", dias_restantes: 600,
      matriculacion: "2024-11-26", ultima_itv: null, historial: [],
    }],
    "binary_sensor.insurance_due": ["off", {
      nivel: "ok", renovacion: "2027-03-14", limite_desistimiento: "2027-02-12",
      dias_renovacion: 156, dias_desistimiento: 126, dias_aviso: 30,
      compania: "Mutua Ejemplo", tipo: "comprehensive_excess",
    }],
    "image.isometric_view": ["2026-10-09T12:00:00", { entity_picture: PIXEL }],
    "image.top_view": ["2026-10-09T12:00:00", { entity_picture: `${PIXEL}#planta` }],
    "image.interior_view": ["2026-10-09T12:00:00", { entity_picture: PIXEL }],
    "image.dec_photo": ["2026-10-09T12:00:00", {}],
    "climate.cabin_climate": ["off", { temperature: 22.5, min_temp: 16, max_temp: 32 }],
    "lock.doors": ["locked"],
    "lock.pin_arm": ["locked"],
    "cover.windows": ["open"], // invertida: "open" = cerradas
    "cover.trunk_control": ["closed"],
    "button.refresh": ["unknown"],
    "button.flash_lights": ["unknown"],
    "button.honk_horn": ["unknown"],
    "button.flash_and_honk": ["unknown"],
    "switch.steering_wheel_heat": ["off"],
    "number.seat_heat_driver": [0],
    "number.seat_heat_passenger": [0],
    "number.seat_vent_driver": [0],
    "number.seat_vent_passenger": [0],
  };

  const state = (key, [value, attributes = {}]) => ({ entity_id: id(key), state: String(value), attributes });

  const banco = {
    DEVICE,
    id,
    /** Lo que la tarjeta ha pedido: "dominio.servicio {datos}" y "api GET ruta". */
    registro: [],
    /** Avisos breves que la tarjeta ha enseñado (hass-notification). */
    avisos: [],
    card: null,
    hass: null,

    /**
     * Crea la tarjeta con un coche.
     *
     * @param {object} opciones
     *   idioma    idioma del usuario ("es" por defecto)
     *   estados   cambios sobre el coche base: { clave: [estado, atributos] }
     *   sin       claves de entidades que este coche no tiene
     *   manual    respuesta de manual_info ({ available, url, itv, silent_warnings })
     *   seguro    respuesta de insurance_info, o null si no hay ficha
     *   textos    textos de Home Assistant para hass.localize ({ clave: texto })
     */
    montar(opciones = {}) {
      document.getElementById("mount").replaceChildren();
      for (const host of document.querySelectorAll("body > div:not(#mount)")) host.remove();
      banco.registro = [];
      banco.avisos = [];
      const absent = new Set(opciones.sin || []);
      const all = { ...BASE, ...(opciones.estados || {}) };
      const entities = {};
      const states = {};
      for (const [key, value] of Object.entries(all)) {
        if (absent.has(key)) continue;
        const name = key.split(".")[1];
        entities[id(key)] = { entity_id: id(key), device_id: DEVICE, platform: "dec_deepal", translation_key: name };
        states[id(key)] = state(key, [].concat(value));
      }
      const manual = opciones.manual || {
        available: true, url: "https://example.com/manual.pdf", itv: true, silent_warnings: ["warning_airbag"],
      };
      const seguro = "seguro" in opciones ? opciones.seguro : { policy: "0123 4567 89", phone_assistance: "900 000 000", phone_company: "910 000 000" };
      const hass = {
        entities,
        states,
        devices: { [DEVICE]: { name: "Changote" } },
        locale: { language: opciones.idioma || "es" },
        localize: banco._localize(opciones.textos),
        // Como Home Assistant: número con su unidad; los estados de texto, tal cual.
        formatEntityState: (s) => `${String(s.state).replace(".", ",")}${s.attributes.unit_of_measurement ? " " + s.attributes.unit_of_measurement : ""}`,
        callApi: async (method, path) => {
          banco.registro.push(`api ${method} ${path}`);
          if (path.includes("insurance_info")) {
            if (seguro === null) throw new Error("404");
            return seguro;
          }
          return manual;
        },
        callService: async (domain, service, data) => {
          banco.registro.push(`${domain}.${service} ${JSON.stringify(data)}`);
          if (opciones.fallo) throw new Error(opciones.fallo);
          banco._react(domain, service, data);
        },
      };
      banco.hass = hass;
      // `tarjeta`: "dec-deepal-card" (por defecto) o "dec-deepal-top-card"; `config`: más opciones.
      const tag = opciones.tarjeta || "dec-deepal-card";
      const card = document.createElement(tag);
      card.addEventListener("hass-notification", (event) => banco.avisos.push(event.detail.message));
      card.setConfig({ type: `custom:${tag}`, device_id: DEVICE, ...(opciones.config || {}) });
      card.hass = hass;
      document.getElementById("mount").append(card);
      banco.card = card;
    },

    _localize: (textos) => (key) => (textos || {})[key] || "",

    /** Llega otra lectura del coche: `{ clave: [estado, atributos] }`. */
    cambiar(estados) {
      const states = { ...banco.hass.states };
      for (const [key, value] of Object.entries(estados)) {
        const previous = states[id(key)] || { attributes: {} };
        const [next, attributes] = [].concat(value);
        states[id(key)] = { entity_id: id(key), state: String(next), attributes: attributes || previous.attributes };
      }
      banco.hass = { ...banco.hass, states };
      banco.card.hass = banco.hass;
    },

    /** Home Assistant cambia de idioma: primero el idioma y, un poco después, sus textos. */
    idioma(idioma, textos) {
      banco.hass = { ...banco.hass, locale: { language: idioma } };
      banco.card.hass = banco.hass;
      banco.hass = { ...banco.hass, localize: banco._localize(textos) };
      banco.card.hass = banco.hass;
    },

    /** El coche "obedece" a lo que se le pide, como haría de verdad. */
    _react(domain, service, data) {
      if (domain === "dec_deepal" || !data || !data.entity_id) return;
      const current = banco.hass.states[data.entity_id];
      if (!current) return;
      const next = { ...current };
      if (service === "unlock") next.state = "unlocked";
      if (service === "lock") next.state = "locked";
      if (service === "set_value") next.state = String(data.value);
      if (service === "toggle") next.state = current.state === "on" ? "off" : "on";
      if (domain === "climate" && service === "turn_on") next.state = "heat_cool";
      if (domain === "climate" && service === "turn_off") next.state = "off";
      if (service === "set_temperature") next.attributes = { ...current.attributes, temperature: data.temperature };
      banco.hass = { ...banco.hass, states: { ...banco.hass.states, [data.entity_id]: next } };
      banco.card.hass = banco.hass;
    },

    /** Ventanas abiertas (la última es la de encima). */
    ventanas: () => Array.from(document.querySelectorAll("body > div:not(#mount)")).filter((host) => host.shadowRoot),
    ventana: () => {
      const open = banco.ventanas();
      return open.length ? open[open.length - 1].shadowRoot : null;
    },

    /** Textos de los seis botones: `{ accion: [título, detalle, clases] }`. */
    botones: () =>
      Object.fromEntries(
        Array.from(banco.card.shadowRoot.querySelectorAll(".tile")).map((tile) => [
          tile.dataset.action,
          [tile.querySelector("b").textContent, tile.querySelector("small").textContent, tile.className.replace("tile", "").trim()],
        ])
      ),

    /** Iconos de la línea de estado (tic verde o testigos). */
    estado: () => Array.from(banco.card.shadowRoot.querySelectorAll(".status ha-icon")).map((icon) => icon.getAttribute("icon")),
  };

  window.banco = banco;
})();
