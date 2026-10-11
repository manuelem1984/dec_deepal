  // ---------------------------------------------------------------------------
  // Menú "Localizar vehículo"
  // ---------------------------------------------------------------------------
  install(class {
    _openLocate() {
      const option = (key, icon, label, text) =>
        this._ids[key]
          ? `<button class="tile" data-action="go" data-key="${key}"><ha-icon icon="${icon}"></ha-icon><b>${label}</b><small>${text}</small></button>`
          : "";
      const html = `
        <div class="head"><button class="icon-btn" data-action="close" aria-label="${this._t("close")}"><ha-icon icon="mdi:close"></ha-icon></button><h2>${this._t("locate")}</h2></div>
        <div class="three">
          ${option("button.flash_lights", "mdi:alarm-light-outline", this._t("lights"), this._t("flash"))}
          ${option("button.honk_horn", "mdi:bullhorn", this._t("horn"), this._t("honk"))}
          ${option("button.flash_and_honk", "mdi:alarm-light", this._t("lights_horn"), this._t("both"))}
        </div>`;
      openDialog(html, (action, target, dialog) => {
        if (action !== "go") return;
        dialog.close();
        this._call("locate", "button", "press", target.dataset.key);
      });
    }
  });
