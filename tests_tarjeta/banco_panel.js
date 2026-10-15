// =============================================================================
// Banco de pruebas del panel: un Home Assistant y una integración de mentira
// =============================================================================
// Uso (desde las pruebas o desde la consola del navegador):
//
//   banco.montar({ idioma: "es" })    // dos coches de ejemplo
//   banco.registro                     // órdenes que ha mandado el panel
//   banco.estado                       // lo que "guarda" la integración
//   banco.ventana()                    // la ventana abierta encima
//
// Responde a las mismas órdenes que panel/ ("dec_deepal/panel/...") y
// rechaza lo mismo que rechazaría la integración (p. ej. plazos desordenados).
// =============================================================================

(() => {
  const due = (section, step, threshold, unit) => ({
    id: `${section}_${step}`, section, unit: unit || null, threshold: threshold == null ? null : threshold,
    limits: unit === "days" ? [1, 365] : unit === "km" ? [100, 20000] : null,
  });
  const plain = (id, section) => ({ id, section, unit: null, threshold: null, limits: null });
  /** Los mismos avisos que alert_rules.NOTICES. */
  const NOTICES = [
    plain("charge_started", "charge"), plain("charge_interrupted", "charge"), plain("charge_finished", "charge"),
    plain("warnings", "warnings"), plain("tires", "warnings"), plain("key_battery", "warnings"),
    due("maintenance", "t1", 60, "days"), due("maintenance", "t2", 30, "days"), due("maintenance", "t3", 15, "days"),
    due("maintenance", "k1", 5000, "km"), due("maintenance", "k2", 2500, "km"), due("maintenance", "k3", 1000, "km"),
    due("maintenance", "overdue"),
    due("itv", "t1", 60, "days"), due("itv", "t2", 30, "days"), due("itv", "t3", 15, "days"), due("itv", "overdue"),
    due("insurance", "c1", 30, "days"), due("insurance", "c2", 15, "days"), due("insurance", "last_day"),
    due("insurance", "r1", 30, "days"), due("insurance", "r2", 15, "days"), due("insurance", "renewed"),
  ];
  const CHAINS = [
    ["maintenance_t1", "maintenance_t2", "maintenance_t3"], ["maintenance_k1", "maintenance_k2", "maintenance_k3"],
    ["itv_t1", "itv_t2", "itv_t3"], ["insurance_c1", "insurance_c2"], ["insurance_r1", "insurance_r2"],
  ];
  const ME = "mobile_app_iphone_de_manuel";
  const HER = "mobile_app_iphone_de_ella";
  const PANEL = "persistent_notification";
  const to = (targets, ids) => Object.fromEntries(NOTICES.map((notice) => [notice.id, ids.includes(notice.id) || ids.includes(notice.section) ? [...targets] : []]));
  const SHEET = {
    modelo: "s05_2024", version: "max", origen: "de su versión", copia_de: null, verificada: true,
    funciones: { asientos_calefaccion: true, asientos_ventilacion: true, volante_calefactado: true, porton_electrico: true },
    testigos_sin_aviso: ["warning_airbag"],
  };

  const COLORS = [
    { id: "andromeda_blue", name: "Andromeda Blue", swatch: "#2f4a6b" },
    { id: "ganymade_grey", name: "Ganymede Grey", swatch: "#5d6166" },
    { id: "moonlight_white", name: "Moonlight White", swatch: "" },
  ];
  /** Una foto por combinación, como hace panel/estado.py: "<versión>|<color>". */
  const photos = (trims) => Object.fromEntries(["", ...trims].flatMap((trim) => ["", ...COLORS.map((c) => c.id)].map((color) =>
    [`${trim}|${color}`, trim && color ? `coche.svg?${trim}_${color}` : "coche.svg?default"])));
  const ITV_RULES = { first_months: 48, interval_months: 24, reduced_from_months: 120, reduced_interval_months: 12 };
  const MODELS = [
    { id: "s05_2024", name: "Deepal S05 EV", fuel: false, colors: COLORS, wheels: ["cover", "open"], photos: photos(["pro", "max", "max_awd"]),
      trims: [{ id: "pro", name: "RWD Pro", wheel: "pro", equipped: 0 }, { id: "max", name: "RWD Max", wheel: "", equipped: 4 }, { id: "max_awd", name: "4WD Max", wheel: "", equipped: 4 }] },
    { id: "s05_phev", name: "Deepal S05 PHEV", fuel: true, colors: COLORS, wheels: ["cover", "open"], photos: photos(["pro", "limited_edition"]),
      trims: [{ id: "pro", name: "Pro", wheel: "pro", equipped: 0 }, { id: "limited_edition", name: "Limited Edition", wheel: "pro", equipped: 4 }] },
  ];

  const PEOPLE = [{ id: "person.ella", name: "Ella" }, { id: "person.manuel", name: "Manuel" }];

  const initial = () => ({
    version: "2.5.0b10",
    admin: true,
    people: PEOPLE,
    models: MODELS,
    accounts: [{
      entry_id: "entry1", title: "manuel@example.com", pin_enabled: true, pin_set: true, pin_mode: "armed", arm_seconds: 30, arm_notify: false,
      arm_choices: [10, 20, 30, 60], scan_minutes: 5, scan_limits: [2, 60], wake: true, debug: false,
      manual: { kind: "bev", url: "https://example.com/manual.pdf", official: "https://example.com/manual.pdf" },
    }],
    cars: [
      {
        id: "car1", entry_id: "entry1", device_id: "dev1", key: "LS5A3ABE0RA000001", name: "Changote",
        appearance: { model: "s05_2024", trim: "max", color: "ganymade_grey", wheels: "open" }, country: "es",
        people: [{ id: "person.manuel", name: "Manuel" }], mine: true, plate: { code: "E", parts: ["6545 NPD"] },
        model: "Deepal S05 EV RWD Max", color: "Ganymede Grey", wheel: "open", configured: true, sheet: SHEET,
        battery: 56, range: 276, odometer: 3498.8, itv_available: true, plan: { interval_km: 20000, interval_months: 12 },
        itv_rules: ITV_RULES, manual_url: "https://example.com/manual.pdf",
        maintenance: {
          record: { services_done: 0, last_date: "2026-07-29", last_km: 0, interval_km: 20000, interval_months: 12, history: [] },
          number: 1, due_date: "2027-07-29", due_km: 20000, days_left: 291, km_left: 16501, level: "ok",
          operations: ["Inspección general (propulsión, frenos y suspensión)", "Filtro del habitáculo"], next_extra: ["Líquido de frenos (sustitución)"],
        },
        itv: { record: { registration_date: "2026-07-29", last_date: null, next_override: null, history: [] },
          due_date: "2030-07-29", calculated: "2030-07-29", days_left: 1387, level: "ok" },
        insurance: {
          record: { renewal_date: "2027-07-29", company: "Mutua Ejemplo", policy: "0123 4567 89", kind: "comprehensive_excess",
            notice_days: 30, phone_assistance: "900 000 000", phone_company: "910 000 000" },
          cancel_deadline: "2027-06-29", days_to_renewal: 291, days_to_cancel: 261, level: "ok",
        },
        alerts: { notices: to([ME], ["charge", "warnings", "maintenance", "itv", "insurance_c1", "insurance_c2", "insurance_last_day", "insurance_renewed"]), thresholds: {} },
      },
      {
        id: "car2", entry_id: "entry1", device_id: "dev2", key: "LS5A3ABE0RA000002", name: "Changuito",
        appearance: { model: "s05_2024", trim: "pro", color: null, wheels: null }, country: "es",
        people: [], mine: false, plate: { code: "D", parts: ["M", "AB 1234"] },
        model: "Deepal S05 EV RWD Pro", color: "Deep Space Black", wheel: "pro", configured: true,
        sheet: { ...SHEET, version: "pro", verificada: false,
          funciones: { asientos_calefaccion: false, asientos_ventilacion: false, volante_calefactado: false, porton_electrico: false } },
        battery: 88, range: 430, odometer: 5862.9, itv_available: true, plan: { interval_km: 20000, interval_months: 12 },
        itv_rules: ITV_RULES, manual_url: null,
        maintenance: null, itv: null, insurance: null,
        alerts: { notices: to([HER], ["charge_finished", "warnings"]), thresholds: {} },
      },
    ],
    targets: [
      { id: ME, name: "iPhone de Manuel", kind: "mobile" },
      { id: HER, name: "iPhone de Ella", kind: "mobile" },
      { id: PANEL, name: "Notificaciones de Home Assistant", kind: "panel" },
    ],
    notices: NOTICES,
    insurance_kinds: ["third_party", "third_party_plus", "comprehensive_excess", "comprehensive"],
    stored: [
      { key: "LS5A3ABE0RA000001", label: "Changote", tail: "000001", in_account: true, has: ["maintenance", "itv", "insurance", "appearance"] },
      { key: "LS5A3ABE0RA774512", label: "Deepal …774512", tail: "774512", in_account: false, has: ["maintenance", "insurance"] },
    ],
    history: {
      cambios: [{ time: "2026-10-11T11:38:00+00:00", kind: "change", vehicle: "Changote", changes: ["charging: False → True"] }],
      ordenes: [
        { time: "2026-10-10T19:09:00+00:00", kind: "command", vehicle: "Changuito", name: "climate_on", stage: "rechazado", code: 1032, error: "Power is not off" },
        { time: "2026-10-10T18:47:00+00:00", kind: "command", vehicle: "Changote", name: "lock", stage: "SUCCESS", code: 0 },
      ],
      avisos: [{ time: "2026-10-11T11:38:05+00:00", kind: "alert", vehicle: "Changote", type: "charge_started", targets: 1, sent: 1 }],
      errores: [],
    },
  });

  const fail = (code, message) => Object.assign(new Error(message || code), { code });

  const banco = {
    ME, HER, PANEL,
    registro: [],
    avisos: [],
    estado: null,
    panel: null,

    /**
     * Crea el panel. `opciones`: idioma, fallo (mensaje con el que falla "state"),
     * sin_coches, lectura (usuario que no es administrador: lo que manda panel/estado.py).
     */
    montar(opciones = {}) {
      document.getElementById("mount").replaceChildren();
      for (const host of document.querySelectorAll("body > div:not(#mount)")) host.remove();
      banco.registro = [];
      banco.avisos = [];
      banco.estado = initial();
      if (opciones.sin_coches) banco.estado.cars = [];
      if (opciones.lectura) {
        banco.estado.admin = false;
        for (const key of ["models", "accounts", "people", "stored", "history"]) delete banco.estado[key];
      }
      banco.lectura = Boolean(opciones.lectura);
      const entities = {};
      const states = {};
      for (const [device, picture] of [["dev1", "coche.svg"], ["dev2", "coche.svg"]]) {
        const id = `image.${device}_dec_photo_x`;
        entities[id] = { entity_id: id, device_id: device, platform: "dec_deepal", translation_key: "dec_photo" };
        states[id] = { entity_id: id, state: "2026-10-09T12:00:00", attributes: { entity_picture: picture } };
      }
      const hass = {
        entities, states,
        locale: { language: opciones.idioma || "es" },
        callWS: async (message) => {
          banco.registro.push(JSON.parse(JSON.stringify(message)));
          if (message.type === "auth/sign_path") return { path: `${message.path}?authSig=abc` };
          if (opciones.fallo) throw fail("unknown", opciones.fallo);
          return banco._orden(message.type.replace("dec_deepal/panel/", ""), message);
        },
      };
      const panel = document.createElement("dec-deepal-panel");
      panel.addEventListener("hass-notification", (event) => banco.avisos.push(event.detail.message));
      panel.hass = hass;
      panel.narrow = false;
      document.getElementById("mount").append(panel);
      banco.panel = panel;
    },

    _coche(id) {
      const car = banco.estado.cars.find((item) => item.id === id);
      if (!car) throw fail("not_found");
      return car;
    },

    /** Lo que haría la integración con cada orden del panel. */
    _orden(type, message) {
      const state = banco.estado;
      if (type === "state") return JSON.parse(JSON.stringify(state));
      if (type === "export_url") return { url: "/api/dec_deepal/export?authSig=abc", absolute: "http://ha.local/api/dec_deepal/export?authSig=abc" };
      if (type === "send_backup") return null;
      if (type === "delete_data") {
        state.stored = state.stored.filter((item) => !message.keys.includes(item.key));
        return null;
      }
      if (type === "import_backup") {
        if (message.backup.formato !== "dec_deepal.datos") throw fail("invalid_file");
        return { cars: Object.keys(message.backup.coches || {}) };
      }
      if (type === "set_settings") {
        const account = state.accounts.find((item) => item.entry_id === message.entry_id);
        if (message.pin_enabled) {
          if (!message.pin && !account.pin_set) throw fail("pin_required");
          if (message.pin === "0000") throw fail("pin_invalid"); // el PIN "malo" del banco de pruebas
          if (message.manual_url && !/^https?:\/\//.test(message.manual_url)) throw fail("invalid_url");
        }
        Object.assign(account, { ...message, pin_set: message.pin_enabled && (Boolean(message.pin) || account.pin_set) });
        if (!message.pin_enabled) Object.assign(account, { pin_mode: "direct", arm_seconds: 30, arm_notify: false });
        if ("manual_url" in message) account.manual.url = message.manual_url || account.manual.official;
        for (const gone of ["type", "pin", "manual_url"]) delete account[gone];
        return null;
      }
      if (banco.lectura) throw fail("unauthorized");
      const car = banco._coche(message.vehicle_id);
      if (type === "set_people") {
        if (message.people.some((id) => !PEOPLE.some((person) => person.id === id))) throw fail("unknown_person");
        car.people = PEOPLE.filter((person) => message.people.includes(person.id));
        car.mine = message.people.includes("person.manuel");
        return null;
      }
      if (type === "set_appearance") {
        const model = MODELS.find((item) => item.id === message.model);
        if (!model) throw fail("unknown_model");
        const trim = model.trims.find((item) => item.id === message.trim);
        car.appearance = { model: message.model, trim: message.trim, color: message.color, wheels: message.wheels };
        car.model = [model.name, trim && trim.name].filter(Boolean).join(" ");
        car.wheel = (trim && trim.wheel) || message.wheels || model.wheels[0];
        car.configured = true;
        return null;
      }
      if (type === "set_alerts") {
        const values = Object.fromEntries(NOTICES.filter((notice) => notice.threshold != null).map((notice) => [notice.id, notice.threshold]));
        Object.assign(values, message.thresholds);
        for (const chain of CHAINS) for (let i = 0; i + 1 < chain.length; i += 1) if (values[chain[i]] <= values[chain[i + 1]]) throw fail("threshold_order", chain[i + 1]);
        car.alerts = { notices: message.notices, thresholds: message.thresholds };
      } else if (type === "set_maintenance") {
        car.maintenance = message.enabled
          ? { record: { ...message, history: [] }, number: message.services_done + 1, due_date: "2027-10-11", due_km: message.last_km + message.interval_km,
              days_left: 365, km_left: 14000, level: "ok", operations: [], next_extra: [] }
          : null;
      } else if (type === "register_maintenance") {
        car.maintenance.record.history.push({ number: car.maintenance.number, date: message.date, km: message.km });
        car.maintenance.number += 1;
      } else if (type === "set_itv") {
        car.itv = message.enabled
          ? { record: { registration_date: message.registration_date, last_date: message.last_date, next_override: message.next_date, history: [] },
              due_date: "2030-10-11", calculated: "2030-10-11", days_left: 1461, level: "ok" }
          : null;
      } else if (type === "set_insurance") {
        car.insurance = message.enabled
          ? { record: { ...message }, cancel_deadline: "2027-09-11", days_to_renewal: 365, days_to_cancel: 335, level: "ok" }
          : null;
      }
      return null;
    },

    raiz: () => banco.panel.shadowRoot,
    /** Órdenes mandadas a la integración (sin las lecturas de estado ni los enlaces). */
    ordenes: () => banco.registro.filter((message) => !["dec_deepal/panel/state", "dec_deepal/panel/export_url", "auth/sign_path"].includes(message.type)),
    ventanas: () => Array.from(document.querySelectorAll("body > div:not(#mount)")).filter((host) => host.shadowRoot),
    ventana: () => {
      const open = banco.ventanas();
      return open.length ? open[open.length - 1].shadowRoot : null;
    },
    /** Texto visible (espacios compactados) de un trozo del panel. */
    texto: (selector) => {
      const node = selector ? banco.raiz().querySelector(selector) : banco.raiz().querySelector(".view");
      return node ? node.textContent.replace(/\s+/g, " ").trim() : null;
    },
    pulsar: (selector, index = 0) => banco.raiz().querySelectorAll(selector)[index].click(),
    /** Tabla de avisos de un coche: `{ etiqueta de la fila: "x.." }` (una marca por destino). */
    tabla: (carId) => {
      const rows = banco.raiz().querySelectorAll(`[data-car-card="${carId}"] tr`);
      return Object.fromEntries(Array.from(rows).slice(1).map((row) => {
        const label = (row.querySelector(".lab b") || row.querySelector(".fold")).childNodes;
        const name = Array.from(label).filter((node) => node.nodeType === 3).map((node) => node.textContent.trim()).join("") || row.querySelector(".lab b").textContent;
        const marks = Array.from(row.querySelectorAll(".box")).map((box) => (box.classList.contains("y") ? "x" : box.classList.contains("some") ? "-" : ".")).join("");
        return [name, marks];
      }));
    },
  };

  window.banco = banco;
})();
