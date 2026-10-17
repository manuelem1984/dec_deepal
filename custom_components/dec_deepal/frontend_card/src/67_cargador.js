  // ---------------------------------------------------------------------------
  // Tarjeta "DEC Deepal · Cargador" (custom:dec-deepal-charger-card)
  // ---------------------------------------------------------------------------
  //   type: custom:dec-deepal-charger-card
  //   charger: <id del cargador>      (opcional: si falta, el primero)
  //
  // Un cargador de Panel → Ajustes → Cargadores (chargers.py). Recibe su estado
  // por la suscripción dec_deepal/chargers/subscribe, así que se pinta al
  // momento aunque lo que cambie no sea una entidad (el coche elegido, la
  // carga apuntada). Estados: libre, esperando confirmación (los coches son
  // botones), enchufado y cargando (con % y tiempo estimados sin cobertura).
  // El candado bloquea o desbloquea a mano. Solo pueden tocar quienes tienen
  // permiso (las personas de los coches y los administradores, o solo estos).
  const CHARGER_TAG = "dec-deepal-charger-card";
  const CHARGER_EDITOR_TAG = "dec-deepal-charger-card-editor";

  /** Cargador dibujado: anillo de color según el estado, rayo si carga, candado si no. */
  function wallboxSvg(state) {
    const ring = { charging: "#43a047", waiting: "#ffa000", locked: "#03a9f4", open: "#03a9f4", idle: "#9e9e9e" }[state];
    const center = state === "charging"
      ? '<path d="M2 -14 L-6 2 H0 L-2 14 L6 -2 H0 Z" fill="#43a047"/>'
      : `<path d="M-7 -1 h14 v11 h-14z M-4 -1 v-4 a4 4 0 0 1 8 0 ${state === "open" ? "" : "v4"}" fill="none" stroke="${ring}" stroke-width="2.4" stroke-linejoin="round"/>`;
    const cable = state === "idle" || state === "locked" || state === "open"
      ? '<path d="M46 118 C50 140 70 150 66 166" stroke="#37474f" stroke-width="7" fill="none" stroke-linecap="round"/><rect x="58" y="160" width="16" height="12" rx="3" fill="#263238"/>'
      : '<path d="M46 118 C46 150 30 160 10 168" stroke="#37474f" stroke-width="7" fill="none" stroke-linecap="round"/>';
    return `<svg class="wb" viewBox="0 0 92 175" aria-hidden="true"><rect x="6" y="4" width="80" height="112" rx="16" fill="#263238"/>
      <rect x="12" y="10" width="68" height="100" rx="12" fill="#37474f"/><circle cx="46" cy="52" r="24" fill="#263238" stroke="${ring}" stroke-width="5"/>
      <g transform="translate(46 52)">${center}</g>${cable}</svg>`;
  }

  const CHARGER_CSS = `
    :host { display: block; }
    ha-card { padding: 14px 16px 12px; }
    button { font: inherit; color: inherit; border: 0; background: none; margin: 0; padding: 0; cursor: pointer; }
    .hd { display: flex; align-items: flex-start; gap: 8px; }
    .hd .t { flex: 1; font-size: 20px; } .hd .t small { display: block; font-size: 12px; color: var(--secondary-text-color); }
    .body { display: flex; gap: 14px; align-items: center; margin: 6px 0 4px; }
    .wb { width: 74px; height: 140px; flex: none; }
    .side { flex: 1; min-width: 0; }
    .car { text-align: center; } .car img { width: 100%; max-height: 120px; object-fit: contain; }
    .car .who { font-size: 13px; color: var(--secondary-text-color); }
    .status { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 500; margin: 6px 0 2px; --mdc-icon-size: 20px; }
    .status.g { color: var(--success-color, #43a047); } .status.o { color: var(--warning-color, #ef6c00); }
    .status.b { color: var(--primary-color); } .status.n { color: var(--secondary-text-color); }
    .sub { font-size: 12.5px; color: var(--secondary-text-color); margin-bottom: 8px; }
    .est { font-size: 11px; color: var(--warning-color, #e65100); background: rgba(255, 152, 0, .15); border-radius: 8px; padding: 1px 6px; margin-left: 4px; }
    .lvl { height: 9px; border-radius: 5px; background: ${TILE_BG}; overflow: hidden; margin: 4px 0 10px; }
    .lvl i { display: block; height: 100%; border-radius: 5px; background: var(--success-color, #43a047);
      background-image: repeating-linear-gradient(110deg, rgba(255, 255, 255, .35) 0 8px, transparent 8px 16px); }
    .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
    .t3 { background: ${TILE_BG}; border-radius: 12px; padding: 8px 10px; min-width: 0; }
    .t3 .k { font-size: 11.5px; color: var(--secondary-text-color); display: flex; gap: 4px; align-items: center; --mdc-icon-size: 14px; }
    .t3 .v { font-size: 17px; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .pick { display: flex; gap: 8px; margin-top: 8px; }
    .pick button { flex: 1; border: 1px solid var(--divider-color, #e0e0e0); border-radius: 12px; text-align: center; padding: 4px; font-size: 12.5px; min-width: 0; }
    .pick button img { width: 100%; height: 44px; object-fit: contain; display: block; }
    .pick button[disabled] { cursor: default; opacity: .7; }
    .acts { display: flex; gap: 8px; margin-top: 10px; }
    .acts .b { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 3px; padding: 9px 4px; border-radius: 12px; background: ${TILE_BG};
      font-size: 12px; font-weight: 500; --mdc-icon-size: 22px; }
    .acts .b.on { color: var(--primary-color); background: rgba(var(--rgb-primary-color, 3, 169, 244), .14); }
    .acts .b.warn { color: var(--warning-color, #e65100); background: rgba(255, 152, 0, .15); }
    .acts .b[disabled] { cursor: default; }
    .last { font-size: 12px; color: var(--secondary-text-color); border-top: 1px solid var(--divider-color, #e0e0e0); margin-top: 10px; padding-top: 8px;
      display: flex; gap: 6px; align-items: center; --mdc-icon-size: 16px; }
    .empty { color: var(--secondary-text-color); padding: 8px 0; }
  `;

  class DecDeepalChargerCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._config = {};
      this._data = null;
      this.shadowRoot.addEventListener("click", (event) => this._onClick(event));
    }

    static getStubConfig() {
      return { charger: "" };
    }

    static getConfigElement() {
      return document.createElement(CHARGER_EDITOR_TAG);
    }

    setConfig(config) {
      this._config = config || {};
      this._render();
    }

    set hass(hass) {
      const first = !this._hass;
      this._hass = hass;
      if (first || !this._unsubscribe) this._subscribe();
      else this._render();
    }

    connectedCallback() {
      if (this._hass && !this._unsubscribe) this._subscribe();
    }

    disconnectedCallback() {
      if (this._unsubscribe) this._unsubscribe.then((unsubscribe) => unsubscribe()).catch(() => undefined);
      this._unsubscribe = null;
    }

    getCardSize() {
      return 5;
    }

    getGridOptions() {
      return { columns: 12, min_columns: 6, min_rows: 4 };
    }

    _subscribe() {
      if (!this._hass || !this._hass.connection || this._unsubscribe) return;
      this._unsubscribe = this._hass.connection.subscribeMessage((data) => {
        this._data = data;
        this._render();
      }, { type: "dec_deepal/chargers/subscribe" });
      this._unsubscribe.catch(() => {
        this._unsubscribe = null;
      });
    }

    _language() {
      const hass = this._hass || {};
      return (hass.locale && hass.locale.language) || hass.language || BASE_LANGUAGE;
    }

    _t(key, values) {
      return translate(this._language(), key, values);
    }

    _charger() {
      const chargers = (this._data && this._data.chargers) || [];
      return chargers.find((item) => item.id === this._config.charger) || (this._config.charger ? undefined : chargers[0]);
    }

    _decimal(value, digits) {
      return Number(value).toLocaleString(this._language(), { minimumFractionDigits: digits, maximumFractionDigits: digits });
    }

    _clock(iso) {
      return new Date(iso).toLocaleTimeString(this._language(), { hour: "numeric", minute: "2-digit" });
    }

    _duration(minutes) {
      const total = Math.max(0, Math.round(minutes));
      const h = Math.floor(total / 60);
      return h ? this._t("duration_hm", { h, m: total % 60 }) : this._t("duration_m", { m: total });
    }

    /** Foto del coche: su entidad de imagen (de lado; si no, la isométrica). */
    _photo(deviceId) {
      const hass = this._hass;
      if (!deviceId || !hass) return "";
      for (const key of ["dec_photo", "isometric_view"]) {
        for (const [entityId, entry] of Object.entries(hass.entities || {})) {
          if (entry.platform !== DOMAIN || entry.device_id !== deviceId || entry.translation_key !== key || !entityId.startsWith("image.")) continue;
          const state = hass.states[entityId];
          const picture = state && state.attributes.entity_picture;
          if (picture) return `${picture}${picture.includes("?") ? "&" : "?"}state=${encodeURIComponent(state.state)}`;
        }
      }
      return "";
    }

    _render() {
      if (!this._hass) return;
      const root = this.shadowRoot;
      const charger = this._charger();
      let html;
      if (!this._data) html = `<div class="empty">…</div>`;
      else if (!this._data.enabled) html = `<div class="empty">${this._t("charger_disabled")}</div>`;
      else if (!charger) html = `<div class="empty">${this._t("charger_missing")}</div>`;
      else html = this._chargerHtml(charger);
      root.innerHTML = `<style>${CHARGER_CSS}</style><ha-card>${html}</ha-card>`;
    }

    _chargerHtml(c) {
      const session = c.session;
      const control = c.can_control;
      const waiting = session && session.waiting;
      const charging = Boolean(c.charging);
      const state = charging ? "charging" : waiting ? "waiting" : c.plugged ? (c.locked ? "locked" : "open") : c.locked === false ? "open" : c.locked ? "locked" : "idle";
      const stat = (icon, label, value) => `<div class="t3"><div class="k"><ha-icon icon="${icon}"></ha-icon>${this._t(label)}</div><div class="v">${escapeHtml(value)}</div></div>`;
      let side;
      let grid = "";
      if (waiting) {
        side = `<div class="status o"><ha-icon icon="mdi:lock-clock"></ha-icon>${this._t("ch_waiting")}</div>
          <div class="sub">${this._t(control ? "ch_waiting_help" : "ch_waiting_ro")}</div>
          <div class="pick">${c.vehicles.map((car) => `<button data-action="pick" data-car="${escapeHtml(car.id)}" ${control ? "" : "disabled"}>${
            this._photo(car.device_id) ? `<img src="${this._photo(car.device_id)}" alt="">` : ""}${escapeHtml(car.name)}</button>`).join("")}</div>`;
      } else if (session) {
        const photo = this._photo(session.device_id);
        const status = charging
          ? `<div class="status g"><ha-icon icon="mdi:lightning-bolt"></ha-icon>${this._t("ch_charging")}${
            session.minutes_left != null ? ` · ${this._t("ch_full_at", { time: this._clock(Date.now() + (session.minutes_left + (session.balance || 0)) * 60000) })}` : ""}</div>`
          : `<div class="status ${session.finished_at ? "g" : "b"}"><ha-icon icon="mdi:power-plug"></ha-icon>${this._t(session.finished_at ? "ch_finished" : "ch_plugged")}</div>`;
        const level = session.level != null
          ? `<div class="sub">${session.estimated ? "≈ " : ""}${Math.round(session.level)} %${session.estimated ? `<span class="est">${this._t("ch_estimated")}</span>` : ""}${
            session.soc_start != null ? ` · ${this._t("ch_at_plug", { value: Math.round(session.soc_start) })}` : ""}</div>
            <div class="lvl"><i style="width:${Math.max(0, Math.min(100, session.level))}%"></i></div>`
          : "";
        side = `<div class="car">${photo ? `<img src="${photo}" alt="">` : ""}<div class="who">${escapeHtml(session.vehicle || this._t("ch_unknown_car"))}${
          session.estimated ? ` · ${this._t("ch_no_coverage")}` : ""}</div></div>`;
        grid = `${status}${level}<div class="grid">
          ${stat("mdi:flash", "ch_power", c.power != null ? `${this._decimal(c.power / 1000, 1)} kW` : "—")}
          ${stat("mdi:lightning-bolt-circle", "ch_energy", `+${this._decimal(session.energy, 1)} kWh`)}
          ${stat("mdi:currency-eur", "ch_cost", session.cost != null ? `${this._decimal(session.cost, 2)} €` : "—")}</div>`;
      } else {
        const month = c.month;
        side = `<div class="status n"><ha-icon icon="mdi:power-plug-off-outline"></ha-icon>${this._t("ch_free")}${c.has_lock ? ` · ${this._t(c.locked ? "ch_locked" : "ch_unlocked")}` : ""}</div>
          <div class="sub">${this._t(c.unlock === "confirm" ? "ch_free_help" : "ch_free_help_open")}</div>
          ${month.count ? `<div class="sub">${this._t("ch_month", { count: month.count, kwh: this._decimal(month.energy, 0), cost: month.cost != null ? ` · ${this._decimal(month.cost, 2)} €` : "" })}<br>${
            Object.entries(month.by_vehicle).map(([name, count]) => `${escapeHtml(name)} ${count}`).join(" · ")}</div>` : ""}`;
      }
      const lockButton = c.has_lock
        ? `<button class="b ${waiting ? "warn" : c.locked ? "" : "on"}" data-action="lock" ${control ? "" : "disabled"}><ha-icon icon="${c.locked ? "mdi:lock" : "mdi:lock-open-variant"}"></ha-icon>${this._t(c.locked ? "ch_locked" : "ch_unlocked")}</button>`
        : "";
      const middle = session && session.minutes_left != null && charging
        ? `<div class="b"><ha-icon icon="mdi:timer-sand"></ha-icon>${this._duration(session.minutes_left + (session.balance || 0))}</div>`
        : `<div class="b"><ha-icon icon="${charging ? "mdi:flash" : "mdi:flash-outline"}"></ha-icon>${c.power != null ? `${this._decimal(c.power / 1000, 1)} kW` : "—"}</div>`;
      const last = c.last
        ? `<div class="last"><ha-icon icon="mdi:history"></ha-icon>${escapeHtml(this._t("ch_last", { text: this._session(c.last) }))}</div>`
        : "";
      return `<div class="hd"><div class="t">${escapeHtml(c.name)}<small>${escapeHtml(this._t(`coverage_${c.coverage}`))}</small></div></div>
        <div class="body">${wallboxSvg(state)}<div class="side">${side}</div></div>${grid}
        <div class="acts">${lockButton}${middle}<button class="b" data-action="history"><ha-icon icon="mdi:history"></ha-icon>${this._t("ch_history")}</button></div>${last}`;
    }

    /** Una carga en una línea: "Changote · 12 oct, 22:12 – 6:05 · 65 % → 100 % · +22,1 kWh · 2,52 €". */
    _session(item) {
      const parts = [item.vehicle || this._t("ch_unknown_car")];
      if (item.start) {
        const day = new Date(item.start).toLocaleDateString(this._language(), { day: "numeric", month: "short" });
        parts.push(`${day}, ${this._clock(item.start)}${item.end ? ` – ${this._clock(item.end)}` : ""}`);
      }
      if (item.soc_start != null && item.soc_end != null) parts.push(`${Math.round(item.soc_start)} % → ${item.estimated ? "≈ " : ""}${Math.round(item.soc_end)} %`);
      if (item.energy) parts.push(`+${this._decimal(item.energy, 1)} kWh`);
      if (item.cost != null) parts.push(`${this._decimal(item.cost, 2)} €`);
      return parts.join(" · ");
    }

    async _ws(type, data) {
      try {
        await this._hass.callWS({ type: `dec_deepal/chargers/${type}`, ...data });
        return true;
      } catch (error) {
        this.dispatchEvent(new CustomEvent("hass-notification", { detail: { message: (error && error.message) || this._t("command_failed") }, bubbles: true, composed: true }));
        return false;
      }
    }

    /** Pregunta antes de tocar el cargador. */
    _ask(question, label, run) {
      const dialog = openDialog(`<div class="confirm"><p>${escapeHtml(question)}</p>
        <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${escapeHtml(label)}</button></div></div>`,
      (action) => {
        if (action !== "ok") return;
        dialog.close();
        run();
      });
    }

    _onClick(event) {
      const target = event.composedPath().find((node) => node.dataset && node.dataset.action);
      const c = this._charger();
      if (!target || !c) return;
      if (target.dataset.action === "pick" && c.can_control) {
        const car = c.vehicles.find((item) => item.id === target.dataset.car);
        this._ask(this._t("ch_confirm_q", { charger: c.name, car: car ? car.name : "" }), this._t("ch_unlock"),
          () => this._ws("confirm", { charger_id: c.id, vehicle_id: target.dataset.car }));
      } else if (target.dataset.action === "lock" && c.can_control) {
        const lock = !c.locked;
        this._ask(this._t(lock ? "ch_lock_q" : "ch_unlock_q", { charger: c.name }), this._t(lock ? "ch_lock" : "ch_unlock"),
          () => this._ws("lock", { charger_id: c.id, locked: lock }));
      } else if (target.dataset.action === "history") {
        const rows = c.history.map((item) => `<li>${escapeHtml(this._session(item))}</li>`).join("") || `<li>${this._t("ch_no_history")}</li>`;
        openDialog(`<div class="head"><button class="icon-btn" data-action="close" aria-label="${this._t("close")}"><ha-icon icon="mdi:close"></ha-icon></button>
          <h2>${escapeHtml(c.name)}</h2></div><ul class="hist">${rows}</ul>
          <div class="btns"><button class="tb" data-action="close">${this._t("close")}</button></div>`, () => undefined);
      }
    }
  }

  /** Editor de la tarjeta: elegir el cargador (sin YAML). */
  class DecDeepalChargerCardEditor extends HTMLElement {
    setConfig(config) {
      this._config = config || {};
      this._render();
    }

    set hass(hass) {
      const first = !this._hass;
      this._hass = hass;
      if (first) this._load();
    }

    async _load() {
      try {
        this._list = (await this._hass.callWS({ type: "dec_deepal/chargers/state" })).chargers || [];
      } catch (_error) {
        this._list = [];
      }
      this._render();
    }

    _render() {
      if (!this._hass) return;
      const language = (this._hass.locale && this._hass.locale.language) || this._hass.language;
      const text = (key) => translate(language, key);
      const options = (this._list || []).map((item) => `<option value="${escapeHtml(item.id)}" ${item.id === this._config.charger ? "selected" : ""}>${escapeHtml(item.name)}</option>`).join("");
      this.innerHTML = `<label style="display:block;font-size:13px;color:var(--secondary-text-color)">${text("charger_select")}
        <select style="display:block;width:100%;margin-top:4px;padding:8px;font:inherit;border-radius:8px;border:1px solid var(--divider-color,#ccc);background:var(--card-background-color,#fff);color:var(--primary-text-color)">
        <option value="">${text("charger_first")}</option>${options}</select></label>
        ${this._list && !this._list.length ? `<p style="font-size:13px;color:var(--secondary-text-color)">${text("charger_missing")}</p>` : ""}`;
      this.querySelector("select").addEventListener("change", (event) => {
        this._config = { ...this._config, charger: event.target.value };
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
      });
    }
  }
