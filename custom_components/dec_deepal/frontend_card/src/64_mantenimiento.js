  // ---------------------------------------------------------------------------
  // Ventana de Mantenimiento
  // ---------------------------------------------------------------------------
  install(class {
    _openMaintenance() {
      const state = this._state(MAINTENANCE);
      if (!state) return;
      const data = state.attributes;
      const overdue = data.nivel === "overdue";
      // Sin aviso todavía, la llave va en gris; ámbar si se acerca y roja si está vencida.
      const tone = overdue ? RED : data.nivel === "soon" ? AMBER : "var(--secondary-text-color)";
      const stat = (value, left, late) =>
        value == null
          ? `<div class="stat"><b>—</b><small>${this._t(left)}</small></div>`
          : `<div class="stat"><b>${this._thousands(value)}</b><small>${this._t(Number(value) < 0 ? late : left)}</small></div>`;
      const list = (title, items) => (items.length ? `<h3>${title}</h3><ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : "");
      const history = (data.historial || [])
        .slice()
        .reverse()
        .map((item) => this._t("history_item", { ordinal: this._ordinal(item.number), date: this._day(item.date), km: this._thousands(item.km) }));
      const html = `
        <div class="head"><button class="icon-btn" data-action="close" aria-label="${this._t("close")}"><ha-icon icon="mdi:close"></ha-icon></button><h2>${this._t("maintenance")}</h2></div>
        <div class="mt">
          <div class="next"><ha-icon icon="mdi:wrench" style="color:${tone}"></ha-icon>${this._t("nth_service", { ordinal: this._ordinal(data.revision) })}${overdue ? this._t("overdue_mark") : ""}</div>
          <div class="two">${stat(data.dias_restantes, "days_left", "days_late")}${stat(data.km_restantes, "km_left", "km_late")}</div>
          <p class="due">${this._t("service_planned", { date: this._day(data.fecha_prevista), km: this._thousands(data.km_previstos) })}</p>
          ${list(this._t("includes"), data.operaciones || [])}
          ${list(this._t("history"), history)}
        </div>
        <div class="btns"><button class="tb fill" data-action="register">${this._t("register_service")}</button></div>`;
      openDialog(html, (action, _target, dialog) => {
        if (action !== "register") return;
        dialog.close();
        this._confirmMaintenance(data.revision);
      });
    }

    /** Confirmación antes de anotar la revisión (hoy, con los km actuales). */
    _confirmMaintenance(revision) {
      const reading = this._format("sensor.odometer");
      const odometer = reading ? this._t("with_odometer", { value: escapeHtml(reading) }) : "";
      const html = `
        <div class="confirm"><h2>${this._t("register_service_q", { ordinal: this._ordinal(revision) })}</h2>
          <p>${this._t("register_service_text", { name: this._boldName(), odometer })}</p></div>
        <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("register")}</button></div>`;
      openDialog(html, async (action, _target, dialog) => {
        if (action !== "ok") return;
        dialog.close();
        try {
          await this._hass.callService(DOMAIN, "register_maintenance", { device_id: this._deviceId() });
          this._toast(this._t("service_registered"));
        } catch (error) {
          this._toast((error && error.message) || this._t("service_failed"));
        }
      });
    }
  });
