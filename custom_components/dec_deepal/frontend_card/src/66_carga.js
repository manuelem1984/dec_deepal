  // ---------------------------------------------------------------------------
  // Ventana de carga (se abre al pulsar la franja de la batería)
  // ---------------------------------------------------------------------------
  // Enseña la vista de carga y lo que se sabe de la carga: porcentaje,
  // autonomía, tiempo que queda, corriente, conector, lo que lleva esta carga
  // y la última. Estas dos las apunta la integración (charging.py) y llegan
  // como atributos del sensor "Cargando", con los minutos de equilibrado que
  // se suman al tiempo que da el coche (Panel → Ajustes, "Sumar el
  // equilibrado"). Se repinta sola mientras está abierta; el ⟳ de la cabecera
  // actualiza los datos.
  install(class {
    _openCharge() {
      if (this._charge) return;
      const html = `
        <div class="head"><button class="icon-btn" data-action="close" aria-label="${this._t("close")}"><ha-icon icon="mdi:close"></ha-icon></button>
          <h2>${this._t("charge_title")}</h2>
          <button class="icon-btn" data-action="refresh" aria-label="${this._t("refresh")}"><ha-icon icon="mdi:refresh"></ha-icon></button></div>
        <div class="chg">
          <div class="view" hidden><img alt=""></div>
          <div class="now"><ha-icon></ha-icon><span></span></div>
          <div class="pct"><b></b><span></span></div>
          <div class="lvl"><i></i></div>
          <div class="stats"></div>
        </div>
        <div class="btns"><button class="tb" data-action="close">${this._t("close")}</button></div>`;
      this._charge = openDialog(html, (action) => {
        if (action === "refresh") this._call("refresh", "button", "press", "button.refresh");
      });
      this._charge.onClose = () => {
        this._charge = null;
      };
      this._paintCharge();
    }

    /** "3 h 25 min" / "45 min". */
    _duration(minutes) {
      const total = Math.max(0, Math.round(minutes));
      const h = Math.floor(total / 60);
      const m = total % 60;
      return h ? this._t("duration_hm", { h, m }) : this._t("duration_m", { m });
    }

    _clock(date) {
      return date.toLocaleTimeString(this._language(), { hour: "numeric", minute: "2-digit" });
    }

    /** Minutos que le quedan a la carga, o `undefined` (el coche los da como "H:MM"). */
    _chargeMinutes() {
      const match = /^(\d+):(\d{2})$/.exec(this._value("sensor.remaining_charge_time_hhmm") || "");
      const minutes = match ? Number(match[1]) * 60 + Number(match[2]) : undefined;
      return minutes > 0 ? minutes : undefined;
    }

    /** Minutos de equilibrado que se suman al final (0 si está desactivado). */
    _balanceMinutes() {
      const attributes = (this._state("binary_sensor.charging") || { attributes: {} }).attributes;
      const minutes = Number(attributes.minutos_equilibrado);
      return minutes > 0 ? minutes : 0;
    }

    /** Autonomía sin decimales ("318 km"), sea cual sea la precisión de la entidad. */
    _rangeText() {
      const km = this._number("sensor.range");
      if (km === undefined) return this._format("sensor.range");
      const state = this._state("sensor.range");
      const unit = (state && state.attributes.unit_of_measurement) || "km";
      return `${Math.round(km).toLocaleString(this._language())} ${unit}`;
    }

    _chargeStat(icon, label, value, detail, wide, note) {
      return `<div class="st${wide ? " wide" : ""}"><div class="k"><ha-icon icon="${icon}"></ha-icon>${this._t(label)}</div>
        <div class="n">${escapeHtml(value)}</div><div class="d">${escapeHtml(detail || "")}</div>${
        note ? `<div class="bal"><ha-icon icon="mdi:scale-balance"></ha-icon>${escapeHtml(note)}</div>` : ""}</div>`;
    }

    _paintCharge() {
      const root = this._charge.root;
      const $ = (selector) => root.querySelector(selector);
      const themes = this._hass.themes || {};
      $(".chg").classList.toggle("dark", Boolean(themes.darkMode));

      const src = this._imageUrl(this._state("image.charging_view"));
      $(".view").hidden = !src;
      if (src && $(".view img").getAttribute("src") !== src) $(".view img").setAttribute("src", src);

      const status = this._value("sensor.charge_status") || "disconnected";
      const charging = this._value("binary_sensor.charging") === "on";
      const plugged = status !== "disconnected";
      const dc = status.endsWith("_dc");
      const balance = this._balanceMinutes();
      const car = charging ? this._chargeMinutes() : undefined;
      const minutes = car === undefined ? undefined : car + balance;
      const end = minutes === undefined ? null : new Date(Date.now() + minutes * 60000);
      $('.head [data-action="refresh"]').classList.toggle("spin", this._busy.has("refresh"));

      // Línea de estado.
      let now = this._t(plugged ? "charge_plugged" : "charge_unplugged");
      if (charging) {
        now = this._t("charging_status", { type: dc ? "DC" : "AC" });
        if (end) now += ` · ${this._t("charge_full_at", { time: this._clock(end) })}`;
      }
      $(".now").classList.toggle("on", charging);
      $(".now ha-icon").setAttribute("icon", charging ? "mdi:lightning-bolt" : plugged ? "mdi:power-plug" : "mdi:power-plug-off-outline");
      $(".now span").textContent = now;

      // Porcentaje, autonomía y barra (mismos colores que en la tarjeta).
      const level = this._number("sensor.battery_level");
      const range = this._rangeText();
      $(".pct b").textContent = level === undefined ? "—" : `${Math.round(level)} %`;
      $(".pct span").textContent = range ? this._t("range_left", { value: range }) : "";
      const color = level === undefined ? "var(--secondary-text-color)" : level < 15 ? "var(--error-color, #db4437)" : level < 50 ? "var(--warning-color, #f9a825)" : "var(--success-color, #43a047)";
      $(".lvl").classList.toggle("on", charging);
      $(".lvl i").style.width = `${level === undefined ? 0 : Math.max(0, Math.min(100, level))}%`;
      $(".lvl i").style.backgroundColor = color;

      // Recuadros de datos: solo los que tienen algo que decir.
      const stats = [];
      if (end) {
        const ends = this._t("ends_at", { time: this._clock(end) });
        stats.push(this._chargeStat("mdi:timer-sand", "time_left", this._duration(minutes), ends,
          false, balance ? this._t("balance_included", { minutes: balance }) : ""));
      }
      const current = this._format("sensor.charge_current");
      if (plugged && current) {
        stats.push(this._chargeStat(dc ? "mdi:current-dc" : "mdi:current-ac", "current", current, this._t(charging ? (dc ? "current_dc" : "current_ac") : "no_charge")));
      }
      if (plugged) stats.push(this._chargeStat(dc ? "mdi:ev-plug-ccs2" : "mdi:ev-plug-type2", "connector", dc ? "DC · CCS2" : this._t("connector_ac"), this._t("plugged")));

      const sessions = (this._state("binary_sensor.charging") || { attributes: {} }).attributes;
      const running = charging && sessions.carga_actual;
      if (running && running.inicio) {
        const start = new Date(running.inicio);
        const gained = [];
        if (level !== undefined && running.nivel_inicio != null) gained.push(`+${Math.max(0, Math.round(level - running.nivel_inicio))} %`);
        const km = this._number("sensor.range");
        if (km !== undefined && running.autonomia_inicio != null) gained.push(`+${Math.max(0, Math.round(km - running.autonomia_inicio))} km`);
        const since = this._t("since", { time: this._clock(start), duration: this._duration((Date.now() - start.getTime()) / 60000) });
        stats.push(this._chargeStat("mdi:chart-line", "this_charge", gained.join(" · ") || "—", since, stats.length % 2 === 0));
      }
      const last = !charging && sessions.ultima_carga;
      if (last && last.inicio && last.fin) {
        const start = new Date(last.inicio);
        const finish = new Date(last.fin);
        const levels = last.nivel_inicio != null && last.nivel_fin != null
          ? this._t("from_to", { from: Math.round(last.nivel_inicio), to: Math.round(last.nivel_fin) })
          : "—";
        const day = start.toLocaleDateString(this._dateLanguage(), { day: "numeric", month: "short" });
        const detail = `${day}, ${this._clock(start)} – ${this._clock(finish)} · ${this._duration((finish - start) / 60000)}`;
        stats.push(this._chargeStat("mdi:history", "last_charge", levels, detail, true));
      }
      const html = stats.join("");
      if (this._chargeHtml !== html || !$(".stats").childElementCount) $(".stats").innerHTML = html;
      this._chargeHtml = html;
    }
  });
