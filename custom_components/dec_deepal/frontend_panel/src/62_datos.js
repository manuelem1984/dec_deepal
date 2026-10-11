  // ---------------------------------------------------------------------------
  // Pestaña "Datos": copia de seguridad y datos guardados
  // ---------------------------------------------------------------------------
  install(class {
    _view_data() {
      const mobiles = this._state.targets.filter((target) => target.kind === "mobile");
      const link = this._links.backup;
      const stored = this._state.stored.map((item) => {
        const has = item.has.map((section) => this._t(`section_${section}`)).join(" · ");
        return `<div class="row">
          <div class="ic ${item.in_account ? "" : "grey"}"><ha-icon icon="mdi:${item.in_account ? "car" : "car-off"}"></ha-icon></div>
          <div class="tx">${escapeHtml(item.label)} <span style="color:var(--secondary-text-color)">(…${escapeHtml(item.tail)})</span>
            <small>${escapeHtml(has)}${item.in_account ? "" : `. ${this._t("no_account_note")}`}</small></div>
          <span class="badge ${item.in_account ? "info" : "warn"}">${this._t(item.in_account ? "in_account" : "no_account")}</span>
          <button class="btn r" data-action="delete-data" data-key="${escapeHtml(item.key)}" data-label="${escapeHtml(item.label)}"><ha-icon icon="mdi:delete-outline"></ha-icon>${this._t("delete")}</button>
        </div>`;
      });
      return `<div class="card">
          <h2>${this._t("backup_title")}</h2><div class="sub">${this._t("backup_help")}</div>
          <div class="row"><div class="ic"><ha-icon icon="mdi:download"></ha-icon></div>
            <div class="tx">${this._t("download_title")}<small>${this._t("download_help")}</small></div>
            <a class="btn" ${link ? `href="${escapeHtml(link)}"` : "disabled"} target="_blank" rel="noopener noreferrer" data-action="downloaded"><ha-icon icon="mdi:download"></ha-icon>${this._t("download")}</a></div>
          ${mobiles.length ? `<div class="row"><div class="ic"><ha-icon icon="mdi:cellphone-arrow-down"></ha-icon></div>
            <div class="tx">${this._t("send_title")}<small>${this._t("send_help")}</small></div>
            <select data-field="mobile">${mobiles.map((target) => `<option value="${escapeHtml(target.id)}">${escapeHtml(target.name)}</option>`).join("")}</select>
            <button class="btn o" data-action="send-backup"><ha-icon icon="mdi:send"></ha-icon>${this._t("send")}</button></div>` : ""}
          <div class="row"><div class="ic"><ha-icon icon="mdi:upload"></ha-icon></div>
            <div class="tx">${this._t("upload_title")}<small>${this._t("upload_help")}</small></div>
            <label class="btn o"><ha-icon icon="mdi:upload"></ha-icon>${this._t("choose_file")}<input type="file" accept=".json,application/json" data-change="backup" hidden></label></div>
        </div>
        <div class="card">
          <h2>${this._t("stored_title")}</h2><div class="sub">${this._t("stored_help")}</div>
          ${stored.length ? stored.join("") : `<div class="row"><div class="tx" style="color:var(--secondary-text-color)">${this._t("stored_none")}</div></div>`}
        </div>`;
    }

    /**
     * Enlaces firmados (caducan en minutos): se piden al abrir la pestaña para
     * que el botón sea un enlace de verdad, que se abre en el navegador también
     * desde la app del móvil.
     */
    async _prepareLinks() {
      try {
        const backup = await this._ws("export_url");
        this._links.backup = backup.url;
        for (const entryId of new Set(this._state.cars.map((car) => car.entry_id))) {
          const signed = await this._hass.callWS({ type: "auth/sign_path", path: `/api/diagnostics/config_entry/${entryId}` });
          this._links[`diagnostics_${entryId}`] = signed.path;
        }
      } catch (_error) {
        // Sin enlace: el botón queda desactivado.
      }
      if (this._tab === "data" || this._tab === "diagnostics") this._render();
    }

    /** El enlace sirve una vez con garantías: se pide otro para la próxima. */
    _do_downloaded() {
      setTimeout(() => this._prepareLinks(), 1500);
    }

    async _do_send_backup() {
      const select = this.shadowRoot.querySelector('select[data-field="mobile"]');
      const name = select.options[select.selectedIndex].textContent;
      await this._run("send_backup", { target: select.value }, this._t("sent_to", { device: name }));
    }

    async _change_backup(input) {
      const file = input.files && input.files[0];
      input.value = "";
      if (!file) return;
      let backup;
      try {
        backup = JSON.parse(await file.text());
      } catch (_error) {
        backup = null;
      }
      if (!backup || typeof backup !== "object" || Array.isArray(backup)) {
        this._toast(this._t("error_invalid_file"));
        return;
      }
      const result = await this._run("import_backup", { backup });
      if (result) this._toast(this._t("imported", { cars: (result.cars || []).join(", ") }));
    }

    _do_delete_data(data) {
      openDialog(
        `<h2>${this._t("delete_title")}</h2><p>${this._t("delete_confirm", { name: `<b>${escapeHtml(data.label)}</b>` })}</p>
         <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb danger" data-action="ok">${this._t("delete")}</button></div>`,
        async (action, dialog) => {
          if (action !== "ok") return;
          dialog.close();
          await this._run("delete_data", { keys: [data.key] }, this._t("deleted"));
        }
      );
    }
  });
