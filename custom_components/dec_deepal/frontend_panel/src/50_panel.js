  // ---------------------------------------------------------------------------
  // El panel: carga de datos, pestañas y reparto de las pulsaciones
  // ---------------------------------------------------------------------------
  class DecDeepalPanel extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._tab = "cars";
      this._state = null; // lo que devuelve "state" (panel.py)
      this._error = "";
      this._open = new Set(); // apartados de avisos desplegados: "<coche>/<apartado>"
      this._drafts = {}; // avisos cambiados y sin guardar, por coche
      this._editing = null; // plazo que se está editando: { car, notice }
      this._filter = "all"; // filtro del historial
      this._links = {}; // enlaces firmados (copia, diagnósticos)
      this.shadowRoot.addEventListener("click", (event) => this._onClick(event));
      this.shadowRoot.addEventListener("change", (event) => this._onChange(event));
      this.shadowRoot.addEventListener("keydown", (event) => this._onKey(event));
    }

    // --- Lo que Home Assistant le pasa a un panel --------------------------------

    set hass(hass) {
      const first = !this._hass;
      const language = first ? "" : this._language();
      this._hass = hass;
      if (first) this._load();
      else if (language !== this._language()) this._render();
      this._syncMenu();
    }

    set narrow(narrow) {
      this._narrow = narrow;
      this._syncMenu();
    }

    // --- Idioma y textos ---------------------------------------------------------

    _language() {
      const hass = this._hass || {};
      return (hass.locale && hass.locale.language) || hass.language || BASE_LANGUAGE;
    }

    _t(key, values) {
      return translate(this._language(), key, values);
    }

    /** Texto si existe; si no, `undefined` (para claves opcionales). */
    _maybe(key, values) {
      return key in TEXTS[textLanguage(this._language())] ? this._t(key, values) : undefined;
    }

    /** Número con separador de miles siempre ("5.000": el español no lo pone con cuatro cifras). */
    _number(value) {
      try {
        return new Intl.NumberFormat(this._language(), { useGrouping: "always" }).format(Number(value));
      } catch (_error) {
        return Number(value).toLocaleString(this._language());
      }
    }

    _date(iso) {
      if (!iso) return "—";
      const [year, month, day] = String(iso).slice(0, 10).split("-").map(Number);
      return new Date(year, month - 1, day).toLocaleDateString(this._language(), { day: "numeric", month: "short", year: "numeric" });
    }

    _days(count) {
      return this._t(Math.abs(count) === 1 ? "day" : "days", { value: this._number(Math.abs(count)) });
    }

    // --- Datos ---------------------------------------------------------------------

    _ws(type, data) {
      return this._hass.callWS({ type: WS + type, ...(data || {}) });
    }

    async _load() {
      try {
        this._state = await this._ws("state");
        this._error = "";
      } catch (error) {
        this._error = (error && error.message) || this._t("error_generic");
      }
      this._render();
    }

    /**
     * Ejecuta una orden y vuelve a pedir el estado. Algunos cambios recargan
     * la integración: por eso se pide otra vez pasados unos segundos.
     */
    async _run(type, data, done) {
      try {
        const result = await this._ws(type, data);
        if (done) this._toast(done);
        await this._load();
        clearTimeout(this._again);
        this._again = setTimeout(() => this._load(), 3500);
        return result === undefined || result === null ? true : result;
      } catch (error) {
        this._toast(this._errorText(error));
        return false;
      }
    }

    _errorText(error) {
      const code = error && error.code;
      return this._maybe(`error_${code}`) || (error && error.message) || this._t("error_generic");
    }

    _toast(message) {
      this.dispatchEvent(new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }));
    }

    _car(id) {
      return this._state.cars.find((car) => car.id === id);
    }

    /** Foto del coche: la entidad de imagen de la integración (de lado; si no, la isométrica). */
    _photo(car) {
      const hass = this._hass;
      for (const key of ["dec_photo", "isometric_view"]) {
        for (const [entityId, entry] of Object.entries(hass.entities || {})) {
          if (entry.platform !== DOMAIN || entry.device_id !== car.device_id || entry.translation_key !== key) continue;
          if (!entityId.startsWith("image.")) continue;
          const state = hass.states[entityId];
          const picture = state && state.attributes.entity_picture;
          if (picture) return `${picture}${picture.includes("?") ? "&" : "?"}state=${encodeURIComponent(state.state)}`;
        }
      }
      return "";
    }

    // --- Pintado ---------------------------------------------------------------------

    _render() {
      const root = this.shadowRoot;
      const scroller = root.querySelector(".scroll");
      const top = scroller ? scroller.scrollTop : 0;
      const tabs = TABS.map(
        ([key, icon]) =>
          `<button class="${key === this._tab ? "on" : ""}" data-action="tab" data-tab="${key}"><ha-icon icon="${icon}"></ha-icon>${this._t(`tab_${key}`)}</button>`
      ).join("");
      let view;
      if (this._error) view = `<div class="empty">${escapeHtml(this._error)}<br><br><button class="btn o" data-action="reload">${this._t("retry")}</button></div>`;
      else if (!this._state) view = `<div class="empty">${this._t("loading")}</div>`;
      else if (!this._state.cars.length) view = `<div class="empty">${this._t("no_cars")}</div>`;
      else view = this[`_view_${this._tab}`]();
      root.innerHTML = `<style>${PANEL_CSS}</style>
        <div class="page">
          <div class="bar">
            <div class="top"><ha-menu-button></ha-menu-button><span>DEC Deepal</span><small>${this._state ? `v${escapeHtml(this._state.version)}` : ""}</small></div>
            <div class="tabs">${tabs}</div>
          </div>
          <div class="scroll"><div class="view">${view}</div></div>
        </div>`;
      this._syncMenu();
      root.querySelector(".scroll").scrollTop = top;
      const input = root.querySelector(".inp input");
      if (input) {
        input.focus();
        input.select();
      }
    }

    /** El botón del menú lateral es de Home Assistant: hay que pasarle sus datos. */
    _syncMenu() {
      const button = this.shadowRoot.querySelector("ha-menu-button");
      if (!button) return;
      button.hass = this._hass;
      button.narrow = this._narrow;
    }

    // --- Pulsaciones -------------------------------------------------------------------

    _onClick(event) {
      const target = event.composedPath().find((node) => node.dataset && node.dataset.action);
      if (!target) return;
      const handler = this[`_do_${target.dataset.action.replace(/-/g, "_")}`];
      if (handler) handler.call(this, target.dataset, target, event);
    }

    _onChange(event) {
      const target = event.target;
      if (target && target.dataset && target.dataset.change) this[`_change_${target.dataset.change}`](target);
    }

    _onKey(event) {
      if (!this._editing || !event.target.matches || !event.target.matches(".inp input")) return;
      if (event.key === "Enter") this._do_edit_ok();
      if (event.key === "Escape") this._do_edit_cancel();
    }

    _do_tab(data) {
      this._tab = data.tab;
      this._editing = null;
      this._render();
      if (data.tab === "data" || data.tab === "diagnostics") this._prepareLinks();
    }

    _do_reload() {
      this._load();
    }

    /** Va a otra página de Home Assistant sin recargar. */
    _navigate(path) {
      window.history.pushState(null, "", path);
      window.dispatchEvent(new CustomEvent("location-changed", { bubbles: true, composed: true }));
    }
  }

  /**
   * Añade al panel los métodos de una clase. Cada pestaña está en su fichero
   * y se engancha así: dentro, `this` es el panel, igual que arriba.
   */
  const install = (source) => {
    for (const name of Object.getOwnPropertyNames(source.prototype)) {
      if (name === "constructor") continue;
      Object.defineProperty(DecDeepalPanel.prototype, name, Object.getOwnPropertyDescriptor(source.prototype, name));
    }
  };
