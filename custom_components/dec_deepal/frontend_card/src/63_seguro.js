  // ---------------------------------------------------------------------------
  // Ventana de Seguro
  // ---------------------------------------------------------------------------
  install(class {
    async _openInsurance() {
      const state = this._state(INSURANCE);
      if (!state || state.attributes.renovacion == null) return this._message(this._t("insurance"), this._t("no_insurance"));
      const data = state.attributes;
      // Póliza y teléfonos: no están en la entidad, se piden a la integración.
      let extra;
      try {
        extra = (await this._hass.callApi("GET", `dec_deepal/insurance_info/${this._deviceId()}`)) || {};
      } catch (_error) {
        extra = {};
      }
      const lastDay = data.dias_desistimiento === 0;
      const tone = lastDay ? RED : data.nivel === "soon" ? AMBER : "var(--secondary-text-color)";
      const kind = data.tipo ? this._t(`kind_${data.tipo}`) : "";
      const title = [data.compania, kind].filter(Boolean).join(" · ") || this._t("insurance");
      const cancel =
        data.dias_desistimiento >= 0
          ? `<div class="stat"><b>${data.dias_desistimiento}</b><small>${this._t("days_to_cancel")}</small></div>`
          : `<div class="stat"><b>—</b><small>${this._t("cancel_passed")}</small></div>`;
      // Botón de llamar. En la app del móvil un enlace "tel:" normal no hace
      // nada (la página va dentro de la app); con target="_blank" la app se lo
      // pasa al sistema, que abre el marcador. Además se enseña el número y, al
      // pulsar, se copia: así sirve aunque el dispositivo no pueda llamar.
      const phone = (number, icon, label) =>
        number
          ? `<a class="call" data-action="call" data-number="${escapeHtml(number)}" target="_blank" rel="noopener noreferrer"
               href="tel:${escapeHtml(String(number).replace(/[^0-9+]/g, ""))}"><ha-icon icon="${icon}"></ha-icon><span>${label}<small>${escapeHtml(number)}</small></span></a>`
          : "";
      const html = `
        <div class="head"><button class="icon-btn" data-action="close" aria-label="${this._t("close")}"><ha-icon icon="mdi:close"></ha-icon></button><h2>${this._t("insurance")}</h2></div>
        <div class="mt">
          <div class="next"><ha-icon icon="mdi:shield-car" style="color:${tone}"></ha-icon>${escapeHtml(title)}</div>
          <div class="two"><div class="stat"><b>${data.dias_renovacion}</b><small>${this._t("days_to_renewal")}</small></div>${cancel}</div>
          <p class="due">${this._t("renewal_text", { renewal: this._day(data.renovacion), deadline: this._day(data.limite_desistimiento), days: data.dias_aviso })}</p>
          <h3>${this._t("policy")}</h3>
          <dl><dt>${this._t("company")}</dt><dd>${escapeHtml(data.compania || "—")}</dd>
            <dt>${this._t("policy_number")}</dt><dd>${escapeHtml(extra.policy || "—")}</dd>
            <dt>${this._t("kind")}</dt><dd>${escapeHtml(kind || "—")}</dd></dl>
          <div class="calls">${phone(extra.phone_assistance, "mdi:tow-truck", this._t("assistance"))}${phone(extra.phone_company, "mdi:phone", this._t("company"))}</div>
        </div>
        <div class="btns"></div>`;
      openDialog(html, (action, target) => {
        if (action !== "call") return;
        const number = target.dataset.number;
        // El enlace abre el marcador por su cuenta; aquí solo se copia el número.
        if (navigator.clipboard && navigator.clipboard.writeText)
          navigator.clipboard.writeText(number).then(
            () => this._toast(this._t("number_copied", { number })),
            () => undefined
          );
      });
      return undefined;
    }
  });
