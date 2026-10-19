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
      this._charge = null; // ventana de carga abierta
      this._pendingTemp = null;
      this._tempTimer = null;
      this.shadowRoot.addEventListener("click", (event) => this._onClick(event));
      // La franja de la batería hace de botón: también con Intro o Espacio.
      this.shadowRoot.addEventListener("keydown", (event) => {
        if ((event.key !== "Enter" && event.key !== " ") || !event.target.matches || !event.target.matches(".energy")) return;
        event.preventDefault();
        event.target.click();
      });
    }

    /** Qué vista del coche enseña: "isometric" (esta) o "top" (la de planta). */
    static get VIEW() {
      return "isometric";
    }

    // --- API de las tarjetas de Home Assistant --------------------------------

    static getStubConfig(hass) {
      const first = Object.values((hass && hass.entities) || {}).find((entry) => entry.platform === DOMAIN && entry.device_id);
      return { device_id: first ? first.device_id : "" };
    }

    static getConfigForm() {
      const text = (key) => translate(document.documentElement.lang, key);
      const schema = [{ name: "device_id", selector: { device: { filter: [{ integration: DOMAIN }] } } }];
      if (this.VIEW === "top") {
        const options = ["horizontal", "vertical"].map((value) => ({ value, label: text(`orientation_${value}`) }));
        schema.push({ name: "orientation", selector: { select: { mode: "dropdown", options } } });
      }
      return { schema, computeLabel: (field) => text(field.name === "orientation" ? "orientation" : "car") };
    }

    setConfig(config) {
      this._config = config || {};
      this._ids = {};
      this._built = false;
      if (this._hass) this._update();
    }

    set hass(hass) {
      if (!this._hass) this._subscribeChargers(hass);
      this._hass = hass;
      // Tema oscuro: fondo de estudio detrás de la foto (STUDIO_BG).
      this.toggleAttribute("dark", Boolean((hass.themes || {}).darkMode));
      this._update();
    }

    getCardSize() {
      return this._vertical() ? 11 : 8;
    }

    /** ¿Vista planta de pie? (solo la tarjeta de planta, y si se pide). */
    _vertical() {
      return this.constructor.VIEW === "top" && this._config.orientation === "vertical";
    }

    getGridOptions() {
      return { columns: 12, min_columns: 6, min_rows: 6 };
    }

    disconnectedCallback() {
      if (this._comfort) this._comfort.close();
      if (this._charge) this._charge.close();
      if (this._chargers) this._chargers.then((unsubscribe) => unsubscribe()).catch(() => undefined);
      this._chargers = null;
    }

    connectedCallback() {
      if (this._hass && !this._chargers) this._subscribeChargers(this._hass);
    }

    /** Cargadores (chargers.py): la ventana de carga enseña el que carga este coche. */
    _subscribeChargers(hass) {
      if (!hass || !hass.connection || !hass.connection.subscribeMessage || this._chargers) return;
      this._chargers = hass.connection.subscribeMessage((data) => {
        this._chargerData = data;
        this._repaint();
        if (this._charge) this._paintCharge();
      }, { type: "dec_deepal/chargers/subscribe" });
      this._chargers.catch(() => {
        this._chargers = null;
      });
    }

    /** % estimado de este coche por un cargador (sin cobertura), si está activado; o `undefined`. */
    _estimate() {
      const data = this._chargerData;
      if (!data || !data.enabled || !data.show_estimate || !data.estimates) return undefined;
      return data.estimates[this._deviceId()];
    }

    /** Cargador en el que está enchufado este coche, o `undefined`. */
    _station() {
      const data = this._chargerData;
      if (!data || !data.enabled) return undefined;
      const deviceId = this._deviceId();
      return data.chargers.find((charger) => charger.session && charger.session.device_id && charger.session.device_id === deviceId);
    }

    /** Límite de carga de este coche (activado y con cargador), o `undefined`. */
    _limitCar() {
      const data = this._chargerData;
      if (!data || !data.enabled || !data.limit || !data.limit.enabled || !data.cars) return undefined;
      return data.cars[this._deviceId()];
    }

    /** Debajo de la barra: 70 · 80 · 90 · 100 %, la marca del límite y qué va a pasar. */
    _paintLimit($) {
      const car = this._limitCar();
      const row = $(".limits");
      const hint = $(".lhint");
      const marker = $(".bar .tgt");
      row.hidden = !car;
      marker.hidden = !car || car.limit >= 100;
      if (!car) {
        hint.hidden = true;
        return;
      }
      for (const button of row.querySelectorAll("button")) {
        const on = Number(button.dataset.v) === car.limit;
        button.classList.toggle("on", on);
        button.setAttribute("aria-pressed", String(on));
        button.disabled = !car.can_control;
      }
      marker.style.left = `calc(${car.limit}% - 1px)`;
      const station = this._station();
      const session = station && station.session;
      let text = "";
      let icon = "mdi:information-outline";
      let warn = false;
      if (session && session.limit_hit && session.target) {
        text = this._t("limit_stopped", { limit: session.target });
        icon = "mdi:battery-lock";
      } else if (car.once_full) {
        text = this._t("limit_once_on");
        icon = "mdi:battery-charging-100";
      } else if (session && session.target && session.minutes_to_target != null && station.charging) {
        text = this._t("limit_stops_in", { limit: session.target, time: this._duration(session.minutes_to_target) });
        icon = "mdi:lock-clock";
        warn = true;
      } else if (car.limit < 100) {
        text = this._t("limit_stops", { limit: car.limit });
      }
      const once = car.limit < 100 || car.once_full;
      hint.hidden = !text && !once;
      hint.classList.toggle("warn", warn);
      hint.querySelector("ha-icon").setAttribute("icon", icon);
      hint.querySelector(".tx").textContent = text;
      const button = hint.querySelector(".once");
      button.hidden = !once;
      button.textContent = this._t("limit_once");
      button.classList.toggle("on", Boolean(car.once_full));
      button.setAttribute("aria-pressed", String(Boolean(car.once_full)));
      button.disabled = !car.can_control;
    }

    /** Cambia el límite o «Solo esta: 100 %» (se ve al momento; la suscripción lo confirma). */
    async _setLimit(change) {
      const car = this._limitCar();
      if (!car || !car.can_control || !this._hass.callWS) return;
      Object.assign(car, change);
      this._repaint();
      try {
        await this._hass.callWS({ type: "dec_deepal/chargers/car_limit", device_id: this._deviceId(), ...change });
      } catch (error) {
        this._toast((error && error.message) || this._t("command_failed"));
      }
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

    /** Pregunta a la integración (una vez por coche): manual, ITV y testigos que no se enseñan. */
    async _checkManual(deviceId) {
      if (!deviceId || this._manualDevice === deviceId || !this._hass.callApi) return;
      this._manualDevice = deviceId;
      this._manualUrl = "";
      this._itvAvailable = true;
      try {
        const info = await this._hass.callApi("GET", `dec_deepal/manual_info/${deviceId}`);
        // La ITV solo existe en algunos países (hoy, España).
        if (this._manualDevice === deviceId) this._itvAvailable = !(info && info.itv === false);
        if (this._manualDevice === deviceId && info && Array.isArray(info.silent_warnings)) {
          this._silent = new Set(info.silent_warnings);
          this._repaint();
        }
        // Equipamiento de la versión del coche (su ficha): { porton_electrico: false, ... }.
        if (this._manualDevice === deviceId) this._features = (info && info.features) || {};
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
      // Estados con texto ("Desconectado"): se traducen aquí. La función de
      // Home Assistant se queda con el idioma anterior al cambiar de idioma.
      const [domain, translationKey] = key.split(".");
      const text =
        this._hass.localize &&
        this._hass.localize(`component.${DOMAIN}.entity.${domain}.${translationKey}.state.${state.state}`);
      if (text) return text;
      return this._hass.formatEntityState ? this._hass.formatEntityState(state) : state.state;
    }

    _language() {
      return (this._hass && this._hass.locale && this._hass.locale.language) || "en";
    }

    /**
     * Idioma para escribir fechas con nombre de mes: el del usuario si la
     * tarjeta está traducida a él; si no, el del texto que se enseña (así no
     * sale "Renueva el 14 de març" con el texto en español).
     */
    _dateLanguage() {
      const language = this._language();
      const shown = textLanguage(language);
      return language.toLowerCase().split("-")[0] === shown ? language : shown;
    }

    /** Texto traducido. Las claves están en la tabla TEXTS. */
    _t(key, values) {
      return translate(this._language(), key, values);
    }

    _ordinal(number) {
      return this._t("ordinal", { number });
    }

    /** Nombre del coche en negrita, para meterlo en una frase. */
    _boldName() {
      return `<b style="font-weight:500;color:var(--primary-text-color)">${escapeHtml(this._name())}</b>`;
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
      if (this._builtLanguage !== this._language()) this._built = false; // cambió el idioma
      // Al cambiar de idioma, los textos de Home Assistant llegan un poco
      // después que el idioma: hay que repintar cuando llegan.
      if (this._localize !== this._hass.localize) this._dirty = true;
      this._localize = this._hass.localize;
      if (!this._built) this._build();
      else if (!changed && !this._dirty) return;
      this._seen = tracked;
      this._dirty = false;
      this._paint();
      if (this._comfort) this._paintComfort();
      if (this._charge) this._paintCharge();
    }

    _build() {
      this._built = true;
      this._statusSignature = undefined;
      this._builtLanguage = this._language();
      const tile = (action) =>
        `<button class="tile" data-action="${action}"><ha-icon></ha-icon><b>${this._t(action)}</b><small></small></button>`;
      this.shadowRoot.innerHTML = `
        <style>${CARD_CSS}</style>
        <ha-card>
          <div class="hdr">
            <div class="grow"><div class="name"></div><div class="upd"></div></div>
            <button class="icon-btn" data-action="refresh" aria-label="${this._t("refresh")}"><ha-icon icon="mdi:refresh"></ha-icon></button>
          </div>
          <div class="carbox" hidden><img class="car" alt=""></div>
          <div class="msg" hidden></div>
          <div class="status"></div>
          <div class="energy" data-action="charge" role="button" tabindex="0" aria-label="${this._t("charge_open")}">
            <div class="range">
              <ha-icon class="batt"></ha-icon><span class="km"></span><span class="estb" hidden></span><span class="grow"></span>
              <span class="charge"><ha-icon></ha-icon><span></span></span>
            </div>
            <div class="bar"><i></i><b class="tgt" hidden></b></div>
          </div>
          <div class="limits" hidden><span class="lbl"><ha-icon icon="mdi:battery-lock"></ha-icon>${this._t("limit")}</span>
            <span class="lseg">${[70, 80, 90, 100].map((value) => `<button data-action="limit" data-v="${value}">${value} %</button>`).join("")}</span></div>
          <div class="lhint" hidden><ha-icon></ha-icon><span class="tx"></span><button class="once" data-action="limit-once" hidden></button></div>
          <div class="tiles">
            ${tile("comfort")}${tile("lock")}${tile("trunk")}
            ${tile("vent")}${tile("locate")}${tile("others")}
          </div>
        </ha-card>`;
    }

    _paint() {
      const $ = (selector) => this.shadowRoot.querySelector(selector);
      const found = Object.keys(this._ids).length > 0;
      $(".msg").hidden = found;
      $(".msg").textContent = found ? "" : this._t("not_found");
      $(".name").textContent = this._name();
      // Sin cobertura, con un cargador vinculado: % estimado por el cargador (chargers.py).
      const estimate = this._estimate();
      $(".upd").textContent = this._t("updated", { when: this._updatedText() }) + (estimate ? ` · ${this._t("est_by", { charger: estimate.charger })}` : "");
      $(".upd").classList.toggle("est", Boolean(estimate));
      $('[data-action="refresh"]').classList.toggle("spin", this._busy.has("refresh"));

      // Imagen: la vista de esta tarjeta (isométrica o de planta) o, si el
      // coche no la tiene, la imagen DEC.
      const top = this.constructor.VIEW === "top";
      const view = this._state(top ? "image.top_view" : "image.isometric_view");
      const image = view || this._state("image.dec_photo");
      const img = $(".car");
      const src = this._imageUrl(image);
      const box = $(".carbox");
      box.hidden = !src;
      box.classList.toggle("plain", !view); // la foto DEC va sin recortar
      box.classList.toggle("top", top && Boolean(view));
      box.classList.toggle("vertical", Boolean(view) && this._vertical());
      if (src && img.getAttribute("src") !== src) img.setAttribute("src", src);

      // Batería y autonomía.
      const level = estimate ? estimate.level : this._number("sensor.battery_level");
      const charging = estimate ? estimate.state === "charging" : this._value("binary_sensor.charging") === "on";
      const color = level === undefined ? "var(--secondary-text-color)" : level < 15 ? "var(--error-color, #db4437)" : level < 50 ? "var(--warning-color, #f9a825)" : "var(--success-color, #43a047)";
      $(".batt").setAttribute("icon", this._batteryIcon(level, charging));
      $(".batt").style.color = color;
      $(".km").textContent = estimate ? `≈ ${Math.round(level)} %` : this._format("sensor.range") || "—";
      $(".estb").hidden = !estimate;
      $(".estb").textContent = estimate ? this._t("ch_estimated") : "";
      $(".bar i").style.width = `${level === undefined ? 0 : Math.max(0, Math.min(100, level))}%`;
      $(".bar i").style.background = color;
      const plugged = estimate ? estimate.state !== "unplugged" : (this._value("sensor.charge_status") || "disconnected") !== "disconnected";
      let chargeText = estimate ? this._t(`est_${estimate.state}`) : this._format("sensor.charge_status") || "";
      const remaining = this._value("sensor.remaining_charge_time_hhmm");
      if (!estimate && charging && remaining) chargeText += ` · ${remaining} h`;
      $(".charge ha-icon").setAttribute("icon", estimate ? "mdi:ev-station" : plugged ? "mdi:power-plug" : "mdi:power-plug-off-outline");
      $(".charge").classList.toggle("est", Boolean(estimate) && estimate.state !== "unplugged");
      $(".charge span").textContent = chargeText;
      $(".charge").hidden = !chargeText;
      this._paintLimit($);

      // Línea de estado: tic verde, o el icono de cada testigo encendido.
      // Los de vencimiento (mantenimiento, ITV, seguro) van al final y se pueden pulsar.
      // Un testigo cuenta si está encendido y la ficha del coche no lo silencia.
      const silent = this._silent || new Set(SILENT_BY_DEFAULT);
      const active = WARNINGS.filter((warning) =>
        warning.keys.some((key) => !silent.has(key.split(".")[1]) && this._value(key) === "on")
      );
      const due = DUE.map((item) => ({ ...item, level: this._dueLevel(item.key) })).filter((item) => item.level);
      const signature = `${active.map((warning) => warning.icon).join("|")}#${due.map((item) => item.action + item.level).join("|")}`;
      if (this._statusSignature !== signature) {
        this._statusSignature = signature;
        const icons = active.map((warning) => `<ha-icon icon="${warning.icon}" style="color:${warning.color}"></ha-icon>`);
        for (const item of due)
          icons.push(
            `<button data-action="${item.action}" aria-label="${this._t(item.label)}"><ha-icon icon="${item.icon}" style="color:${item.level === "overdue" ? RED : AMBER}"></ha-icon></button>`
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
        ? `${this._t("on")}${target != null ? ` · ${this._temp(target)} °C` : ""}`
        : `${this._t(comfortOn ? "seats" : "off")}${inside ? ` · ${inside}` : ""}`;

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
        // En azul solo si hay algo encendido (clima, asientos o volante).
        comfort: { icon: "mdi:sun-snowflake-variant", text: comfortText, primary: comfortOn },
        lock: {
          icon: unlocked ? "mdi:lock-open-variant" : "mdi:lock",
          text: lockKnown ? this._t(unlocked ? "unlocked" : "locked") : "—",
          on: lockKnown && unlocked,
        },
        trunk: { icon: trunkOpen ? "dec:trunk_open" : "dec:trunk_closed", text: this._t(trunkOpen ? "trunk_open" : "trunk_closed"), on: trunkOpen },
        vent: { icon: "mdi:weather-windy", text: this._t(venting ? "venting" : anyWindow ? "windows_open" : "windows_closed"), on: venting || anyWindow },
        locate: { icon: "mdi:car-search", text: this._t("lights_horn") },
        others: { icon: "mdi:dots-horizontal", text: this._othersShort() || this._t("others_default") },
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
      return Math.abs(count) === 1 ? this._t("day") : this._t("days", { count: Math.abs(count) });
    }

    /** ITV en una línea. Con ``named`` lleva delante "ITV" (para el botón "Otros"). */
    _itvShort(named = true) {
      const data = (this._state(ITV) || { attributes: {} }).attributes;
      if (data.dias_restantes == null) return "";
      if (data.dias_restantes < 0) return this._t(named ? "itv_overdue" : "overdue");
      if (data.dias_restantes === 0) return this._t(named ? "itv_last_day" : "last_day");
      return this._t(named ? "itv_in" : "left", { days: this._days(data.dias_restantes) });
    }

    /** Seguro en una línea. Con ``named`` lleva delante "Seguro". */
    _insuranceShort(named = true) {
      const data = (this._state(INSURANCE) || { attributes: {} }).attributes;
      if (data.dias_desistimiento == null) return "";
      if (data.dias_desistimiento === 0) return this._t(named ? "insurance_last_day" : "last_day");
      if (data.dias_desistimiento > 0 && data.nivel !== "ok")
        return this._t(named ? "insurance_cancel" : "to_cancel", { days: this._days(data.dias_desistimiento) });
      return this._t("renews_on", { date: this._day(data.renovacion) });
    }

    /** Fecha ISO ("2027-03-14") como "14 mar 2027". */
    _day(iso) {
      if (!iso) return "—";
      return new Date(`${iso}T00:00:00`).toLocaleDateString(this._dateLanguage(), { day: "numeric", month: "short", year: "numeric" });
    }

    /** Número entero con separador de miles, según el idioma. */
    _thousands(value) {
      return Math.abs(Number(value)).toLocaleString(this._language(), { useGrouping: "always" });
    }

    /** Resumen corto del mantenimiento, solo si la revisión está próxima o vencida. */
    _maintenanceShort() {
      if (this._value(MAINTENANCE) !== "on") return "";
      const data = this._state(MAINTENANCE).attributes;
      if (data.nivel === "overdue") return this._t("service_overdue");
      const days = Number(data.dias_restantes);
      const km = data.km_restantes;
      // Se enseña lo que antes llegue a los escalones de aviso.
      if (km != null && Number(km) <= 3000 && days > 60) return this._t("service_in", { value: `${this._thousands(km)} km` });
      return this._t("service_in", { value: this._days(days) });
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
      return Number(value).toLocaleString(this._language(), { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    }

    _updatedText() {
      const raw = this._value("sensor.last_update");
      const date = raw ? new Date(raw) : undefined;
      if (!date || Number.isNaN(date.getTime())) return "—";
      const language = this._dateLanguage();
      const time = date.toLocaleTimeString(language, { hour: "numeric", minute: "2-digit" });
      const startOfDay = (value) => new Date(value.getFullYear(), value.getMonth(), value.getDate()).getTime();
      const days = Math.round((startOfDay(new Date()) - startOfDay(date)) / 86400000);
      if (days === 0) return this._t("today", { time });
      if (days === 1) return this._t("yesterday", { time });
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
        this._toast((error && error.message) || this._t("command_failed"));
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
      if (!this._ids[key]) return this._toast(this._t("no_pin"));
      const html = `
        <div class="confirm"><h2>${escapeHtml(title)}</h2>
          <p>${this._t("pin_confirm", { name: this._boldName() })}</p></div>
        <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${escapeHtml(button)}</button></div>`;
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
        case "charge":
          this._openCharge();
          break;
        case "limit":
          this._setLimit({ limit: Number(target.dataset.v) });
          break;
        case "limit-once": {
          const car = this._limitCar();
          if (car) this._setLimit({ once_full: !car.once_full });
          break;
        }
        case "lock":
          if (tiles.lock.on) this._pinCommand("lock", this._t("lock_q"), this._t("lock_do"), "lock", "lock", "lock.doors");
          else this._pinCommand("lock", this._t("unlock_q"), this._t("unlock_do"), "lock", "unlock", "lock.doors");
          break;
        case "trunk":
          // Sin portón eléctrico (p. ej. el Pro) no hay nada que mandar: se dice.
          if ((this._features || {}).porton_electrico === false) this._toast(this._t("trunk_manual"));
          else if (tiles.trunk.on) this._pinCommand("trunk", this._t("trunk_close_q"), this._t("close"), "cover", "close_cover", "cover.trunk_control");
          else this._pinCommand("trunk", this._t("trunk_open_q"), this._t("open_do"), "cover", "open_cover", "cover.trunk_control");
          break;
        case "vent":
          // Persiana invertida: open_cover SUBE los cristales; close_cover los entreabre.
          if (tiles.vent.on) this._pinCommand("vent", this._t("windows_close_q"), this._t("close"), "cover", "open_cover", "cover.windows");
          else this._pinCommand("vent", this._t("vent_q"), this._t("vent"), "cover", "close_cover", "cover.windows");
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

    /** Ventana con un texto y un único botón. */
    _message(title, text) {
      const html = `
        <div class="confirm"><h2>${escapeHtml(title)}</h2><p>${escapeHtml(text)}</p></div>
        <div class="btns"><button class="tb fill" data-action="close">${this._t("understood")}</button></div>`;
      openDialog(html, () => undefined);
    }
  }

  /**
   * Añade a la tarjeta los métodos de una clase. Cada ventana (ITV, seguro,
   * confort...) está en su fichero y se engancha así: dentro, `this` es la
   * tarjeta, igual que en los métodos de arriba.
   */
  const install = (source) => {
    for (const name of Object.getOwnPropertyNames(source.prototype)) {
      if (name === "constructor") continue;
      Object.defineProperty(DecDeepalCard.prototype, name, Object.getOwnPropertyDescriptor(source.prototype, name));
    }
  };
