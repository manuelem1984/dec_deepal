  // ---------------------------------------------------------------------------
  // Pestaña "Ajustes": control con PIN y lectura de datos (de la cuenta)
  // ---------------------------------------------------------------------------
  // El PIN es de la cuenta de Deepal, no de un coche: vale para todos. El panel
  // nunca recibe el PIN guardado (solo si lo hay): el campo vacío = no cambiarlo.
  // Lo que se toca queda en un borrador (this._settings) hasta pulsar "Guardar".
  install(class {
    _view_settings() {
      const accounts = this._state.accounts;
      return accounts.map((account) => this._settingsCard(account, accounts.length > 1)).join("");
    }

    /** Ajustes de una cuenta tal como se ven ahora: el borrador o lo guardado. */
    _settingsOf(account) {
      return (this._settings && this._settings[account.entry_id]) || { ...account, pin: "", manual_url: account.manual ? account.manual.url : "" };
    }

    _settingsDraft(entryId) {
      const account = this._state.accounts.find((item) => item.entry_id === entryId);
      this._settings = this._settings || {};
      if (!this._settings[entryId]) this._settings[entryId] = this._settingsOf(account);
      return this._settings[entryId];
    }

    _settingsCard(account, several) {
      const now = this._settingsOf(account);
      const entry = escapeHtml(account.entry_id);
      const set = (field, value) => `data-action="setting" data-entry="${entry}" data-field="${field}" data-value="${value}"`;
      const toggle = (field) => `<button class="tog ${now[field] ? "on" : ""}" ${set(field, !now[field])} role="switch" aria-checked="${Boolean(now[field])}"></button>`;
      const row = (icon, title, help, control, grey) => `<div class="row"><div class="ic ${grey ? "grey" : ""}"><ha-icon icon="${icon}"></ha-icon></div>
        <div class="tx">${this._t(title)}<small>${this._t(help)}</small></div>${control}</div>`;
      const segment = (field, values, unit) => `<span class="seg">${values.map((value) =>
        `<button class="${Number(now[field]) === value ? "on" : ""}" ${set(field, value)}>${this._t(unit, { value })}</button>`).join("")}</span>`;
      const mode = (value, icon, extra) => `<button class="mode ${now.pin_mode === value ? "on" : ""}" ${set("pin_mode", value)} aria-pressed="${now.pin_mode === value}">
        <b><ha-icon icon="${icon}"></ha-icon>${this._t(`mode_${value}`)}</b><p>${this._t(`mode_${value}_help`)}</p></button>${extra || ""}`;
      const scan = [...new Set([2, 5, 10, 15, 30, Number(now.scan_minutes)])].sort((a, b) => a - b);
      const dirty = Boolean(this._settings && this._settings[account.entry_id]);

      const pin = !now.pin_enabled ? "" : `
        ${row("mdi:form-textbox-password", "pin", "pin_field_help",
          `<span class="pinbox"><input type="password" inputmode="numeric" autocomplete="off" data-input="pin" data-entry="${entry}" value="${escapeHtml(now.pin)}"
              placeholder="${account.pin_set ? "••••" : ""}" aria-label="${this._t("pin")}">
            <button data-action="reveal" aria-label="${this._t("show_pin")}"><ha-icon icon="mdi:eye-outline"></ha-icon></button></span>
           ${account.pin_set && !now.pin ? `<span class="badge ok"><ha-icon icon="mdi:check-circle"></ha-icon>${this._t("pin_checked")}</span>` : ""}`)}
        <div class="lbl">${this._t("pin_mode_title")}</div>
        <div class="modes">
          ${mode("direct", "mdi:flash")}
          ${mode("armed", "mdi:lock-clock")}
        </div>
        ${now.pin_mode !== "armed" ? "" : `
          ${row("mdi:timer-sand", "arm_seconds", "arm_seconds_help", segment("arm_seconds", account.arm_choices, "seconds"))}
          ${row("mdi:bell-outline", "arm_notify", "arm_notify_help", toggle("arm_notify"), true)}`}`;

      const manual = !account.manual ? "" : row("mdi:book-open-variant", `manual_${account.manual.kind}`, "manual_help",
        `<input class="url" type="url" data-input="manual_url" data-entry="${entry}" value="${escapeHtml(now.manual_url)}" placeholder="${escapeHtml(account.manual.official)}">`);

      return `${several ? `<div class="acct">${this._t("account", { name: escapeHtml(account.title) })}</div>` : ""}
        <div class="card" data-account="${entry}">
          <h2>${this._t("pin_title")}</h2><div class="sub">${this._t("pin_help")}</div>
          ${row("mdi:shield-key", "pin_enabled", "pin_enabled_help", toggle("pin_enabled"))}
          ${pin}
          <h2 class="next">${this._t("reading_title")}</h2><div class="sub">${this._t("reading_help")}</div>
          ${row("mdi:timer-outline", "scan_title", "scan_help", segment("scan_minutes", scan, "minutes"))}
          ${row("mdi:sleep-off", "wake_title", "wake_help", toggle("wake"))}
          ${row("mdi:scale-balance", "balance_title", "balance_help", toggle("charge_balance"))}
          ${manual}
          ${row("mdi:bug-outline", "debug_title", "debug_help", toggle("debug"), true)}
          <div class="foot ${dirty ? "dirty" : ""}">
            <span>${dirty ? this._t("unsaved_settings") : ""}</span>
            ${dirty ? `<button class="btn o" data-action="discard-settings" data-entry="${entry}">${this._t("discard")}</button>` : ""}
            <button class="btn" data-action="save-settings" data-entry="${entry}">${this._t("save_check")}</button>
          </div>
        </div>`;
    }

    _do_setting(data) {
      const draft = this._settingsDraft(data.entry);
      const value = data.value;
      draft[data.field] = value === "true" ? true : value === "false" ? false : /^\d+$/.test(value) ? Number(value) : value;
      this._render();
    }

    /** Lo que se escribe (PIN, enlace) se apunta sin repintar, para no perder el cursor. */
    _input_setting(target) {
      this._settingsDraft(target.dataset.entry)[target.dataset.input] = target.value;
    }

    _do_reveal(_data, target) {
      const input = target.parentNode.querySelector("input");
      input.type = input.type === "password" ? "text" : "password";
    }

    _do_discard_settings(data) {
      delete this._settings[data.entry];
      this._render();
    }

    async _do_save_settings(data) {
      const account = this._state.accounts.find((item) => item.entry_id === data.entry);
      const now = this._settingsOf(account);
      const message = {
        entry_id: account.entry_id,
        pin_enabled: Boolean(now.pin_enabled),
        pin: String(now.pin || ""),
        pin_mode: now.pin_mode,
        arm_seconds: Number(now.arm_seconds),
        arm_notify: Boolean(now.arm_notify),
        scan_minutes: Number(now.scan_minutes),
        wake: Boolean(now.wake),
        charge_balance: Boolean(now.charge_balance),
        debug: Boolean(now.debug),
      };
      if (account.manual) message.manual_url = String(now.manual_url || "");
      if (await this._run("set_settings", message, this._t("saved"))) {
        if (this._settings) delete this._settings[data.entry];
        this._render();
      }
    }
  });
