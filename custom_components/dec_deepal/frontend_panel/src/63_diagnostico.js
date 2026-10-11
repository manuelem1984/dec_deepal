  // ---------------------------------------------------------------------------
  // Pestaña "Diagnóstico": qué ha pasado y la ficha de cada coche
  // ---------------------------------------------------------------------------
  install(class {
    _view_diagnostics() {
      const history = this._state.history;
      const events = [...history.cambios, ...history.ordenes, ...history.avisos]
        .map((event) => this._event(event))
        .filter((item) => this._matches(item))
        .sort((a, b) => (a.time < b.time ? 1 : -1))
        .slice(0, HISTORY_LIMIT);
      const names = [...new Set(this._state.cars.map((car) => car.name))];
      const filters = [["all", this._t("filter_all")], ...names.map((name) => [`car:${name}`, name]),
        ["orders", this._t("filter_orders")], ["alerts", this._t("filter_alerts")], ["errors", this._t("filter_errors")]];
      const sheets = this._state.cars.map((car) => {
        const sheet = car.sheet || {};
        const link = this._links[`diagnostics_${car.entry_id}`];
        return `<div class="row"><div class="ic"><ha-icon icon="mdi:car-info"></ha-icon></div>
          <div class="tx">${escapeHtml(car.name)} · ${escapeHtml(car.model)}<small>${escapeHtml(sheet.origen || "")}</small></div>
          <span class="badge ${sheet.verificada ? "ok" : "info"}">${this._t(sheet.verificada ? "sheet_verified" : "sheet_catalogue")}</span>
          <a class="btn o" ${link ? `href="${escapeHtml(link)}"` : "disabled"} target="_blank" rel="noopener noreferrer" data-action="downloaded"><ha-icon icon="mdi:download"></ha-icon>${this._t("diagnostics_file")}</a>
        </div>`;
      });
      return `<div class="card">
          <h2>${this._t("history_title")}</h2><div class="sub">${this._t("history_help")}</div>
          <div class="filt">${filters.map(([key, name]) => `<button class="${key === this._filter ? "on" : ""}" data-action="filter" data-filter="${escapeHtml(key)}">${escapeHtml(name)}</button>`).join("")}</div>
          ${events.length ? events.map((item) => `<div class="log"><time>${escapeHtml(this._time(item.time))}</time>
              <div class="dot ${item.tone}"><ha-icon icon="${item.icon}"></ha-icon></div>
              <div class="what">${escapeHtml(item.title)}<small>${escapeHtml(item.detail)}</small></div></div>`).join("")
            : `<div class="row"><div class="tx" style="color:var(--secondary-text-color)">${this._t("history_none")}</div></div>`}
        </div>
        <div class="card">
          <h2>${this._t("sheets_title")}</h2><div class="sub">${this._t("sheets_help")}</div>
          ${sheets.join("")}
        </div>`;
    }

    /** Un evento del historial, listo para pintar. */
    _event(event) {
      const car = event.vehicle || "";
      const failed = Boolean(event.error) || event.ok === false || ["rechazado", "error_envio"].includes(event.stage);
      if (event.kind === "alert") {
        return { time: event.time, car, group: "alerts", tone: "blue", icon: "mdi:bell-ring",
          title: this._t("ev_alert", { name: this._maybe(`notice_${event.type}`) || this._maybe(`section_${event.type}`) || event.type }),
          detail: [car, this._t("ev_targets", { count: event.sent == null ? event.targets : event.sent })].filter(Boolean).join(" · ") };
      }
      if (event.kind === "change") {
        const changes = event.changes || [];
        return { time: event.time, car, group: "changes", tone: "green", icon: "mdi:swap-horizontal",
          title: changes.slice(0, 3).join(" · ") + (changes.length > 3 ? ` (+${changes.length - 3})` : ""), detail: car };
      }
      if (event.kind === "wake") {
        return { time: event.time, car, group: "orders", tone: failed ? "red" : "", icon: "mdi:sleep-off", failed,
          title: this._t("ev_wake"), detail: [car, event.error || event.stage || ""].filter(Boolean).join(" · ") };
      }
      return { time: event.time, car, group: "orders", tone: failed ? "red" : "", icon: "mdi:remote", failed,
        title: this._t("ev_command", { name: event.name || "" }),
        detail: [car, event.stage, event.code == null ? "" : `${this._t("ev_code")} ${event.code}`, event.error].filter(Boolean).join(" · ") };
    }

    _matches(item) {
      const filter = this._filter;
      if (filter === "all") return true;
      if (filter === "errors") return Boolean(item.failed);
      if (filter.startsWith("car:")) return item.car === filter.slice(4);
      return item.group === filter;
    }

    /** "Hoy 13:38", "Ayer 21:09" o "9 oct 20:47". */
    _time(iso) {
      const date = new Date(iso);
      if (Number.isNaN(date.getTime())) return "";
      const language = this._language();
      const time = date.toLocaleTimeString(language, { hour: "2-digit", minute: "2-digit" });
      const day = (value) => new Date(value.getFullYear(), value.getMonth(), value.getDate()).getTime();
      const days = Math.round((day(new Date()) - day(date)) / 86400000);
      if (days === 0) return `${this._t("today")} ${time}`;
      if (days === 1) return `${this._t("yesterday")} ${time}`;
      return `${date.toLocaleDateString(language, { day: "numeric", month: "short" })} ${time}`;
    }

    _do_filter(data) {
      this._filter = data.filter;
      this._render();
    }
  });
