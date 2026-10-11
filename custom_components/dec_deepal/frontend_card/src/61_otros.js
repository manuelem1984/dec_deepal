  // ---------------------------------------------------------------------------
  // Menú "Otros"
  // ---------------------------------------------------------------------------
  install(class {
    _openOthers() {
      const maintenance = this._state(MAINTENANCE);
      const known = maintenance && maintenance.attributes.revision != null;
      const itv = this._state(ITV);
      const insurance = this._state(INSURANCE);
      const tone = (key) => {
        const level = this._dueLevel(key);
        return level ? ` style="color:${level === "overdue" ? RED : AMBER}"` : "";
      };
      // Un enlace de verdad (no un botón): así el navegador y la app del móvil
      // lo abren fuera, en una pestaña nueva, sin bloquearlo como ventana emergente.
      const manual = this._manualUrl
        ? `<a class="tile" data-action="manual" href="${escapeHtml(this._manualUrl)}" target="_blank" rel="noopener noreferrer"><ha-icon icon="mdi:book-open-variant"></ha-icon><b>${this._t("manual")}</b><small>${this._t("open_pdf")}</small></a>`
        : "";
      const off = this._t("not_enabled");
      const option = (action, key, icon, label, text) =>
        `<button class="tile" data-action="${action}"><ha-icon icon="${icon}"${tone(key)}></ha-icon><b>${label}</b><small>${escapeHtml(text)}</small></button>`;
      const html = `
        <div class="head"><button class="icon-btn" data-action="close" aria-label="${this._t("close")}"><ha-icon icon="mdi:close"></ha-icon></button><h2>${this._t("others")}</h2></div>
        <div class="three pairs">
          ${manual}
          ${option("maintenance", MAINTENANCE, "mdi:wrench", this._t("maintenance"), known ? this._t("nth_service", { ordinal: this._ordinal(maintenance.attributes.revision) }) : off)}
          ${this._itvAvailable === false ? "" : option("itv", ITV, "mdi:clipboard-check-outline", this._t("itv"), itv ? this._itvShort(false) || "—" : off)}
          ${option("insurance", INSURANCE, "mdi:shield-car", this._t("insurance"), insurance ? this._insuranceShort(false) || "—" : off)}
        </div>`;
      openDialog(html, (action, _target, dialog) => {
        if (action === "manual") {
          // El enlace se abre solo; el menú se cierra un instante después.
          setTimeout(() => dialog.close(), 300);
          return;
        }
        if (!["maintenance", "itv", "insurance"].includes(action)) return;
        dialog.close();
        if (action === "maintenance") known ? this._openMaintenance() : this._message(this._t("maintenance"), this._t("no_maintenance"));
        else if (action === "itv") this._openItv();
        else this._openInsurance();
      });
    }
  });
