  // ---------------------------------------------------------------------------
  // Ventana de ITV
  // ---------------------------------------------------------------------------
  install(class {
    _openItv() {
      const state = this._state(ITV);
      if (!state || state.attributes.fecha_limite == null) return this._message(this._t("itv"), this._t("no_itv"));
      const data = state.attributes;
      const overdue = data.dias_restantes < 0;
      const tone = overdue ? RED : data.nivel === "soon" ? AMBER : "var(--secondary-text-color)";
      const history = (data.historial || []).slice().reverse();
      const html = `
        <div class="head"><button class="icon-btn" data-action="close" aria-label="${this._t("close")}"><ha-icon icon="mdi:close"></ha-icon></button><h2>${this._t("itv")}</h2></div>
        <div class="mt">
          <div class="next"><ha-icon icon="mdi:clipboard-check-outline" style="color:${tone}"></ha-icon>${this._t("next_itv")}${overdue ? this._t("overdue_mark") : ""}</div>
          <div class="two">
            <div class="stat"><b>${Math.abs(data.dias_restantes)}</b><small>${this._t(overdue ? "days_late" : "days_left")}</small></div>
            <div class="stat"><b>${this._day(data.fecha_limite)}</b><small>${this._t("due_date")}</small></div>
          </div>
          <p class="due">${this._t("itv_rule")}</p>
          <h3>${this._t("details")}</h3>
          <dl><dt>${this._t("registration")}</dt><dd>${this._day(data.matriculacion)}</dd>
            <dt>${this._t("last_itv")}</dt><dd>${data.ultima_itv ? this._day(data.ultima_itv) : this._t("none_yet")}</dd></dl>
          ${history.length ? `<h3>${this._t("history")}</h3><ul>${history.map((item) => `<li>${this._day(item)}</li>`).join("")}</ul>` : ""}
        </div>
        <div class="btns"><button class="tb fill" data-action="register">${this._t("register_itv")}</button></div>`;
      openDialog(html, (action, _target, dialog) => {
        if (action !== "register") return;
        dialog.close();
        this._confirmItv();
      });
      return undefined;
    }

    _confirmItv() {
      const html = `
        <div class="confirm"><h2>${this._t("register_itv_q")}</h2>
          <p>${this._t("register_itv_text", { name: this._boldName() })}</p></div>
        <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("register")}</button></div>`;
      openDialog(html, async (action, _target, dialog) => {
        if (action !== "ok") return;
        dialog.close();
        try {
          await this._hass.callService(DOMAIN, "register_itv", { device_id: this._deviceId() });
          this._toast(this._t("itv_registered"));
        } catch (error) {
          this._toast((error && error.message) || this._t("itv_failed"));
        }
      });
    }
  });
