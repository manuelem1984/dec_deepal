  // ---------------------------------------------------------------------------
  // Ajustes → Cargadores: activarlos, quién los controla y cada cargador
  // ---------------------------------------------------------------------------
  // Los cargadores son de la casa, no de una cuenta: una sola tarjeta debajo
  // de las cuentas. Activar, desactivar y "quién controla" se guardan al
  // pulsar; cada cargador se edita en su ventana (chargers.py hace el resto).
  // DEC Deepal solo bloquea y desbloquea: nunca inicia ni pausa la carga.
  install(class {
    _chargersCard() {
      const config = this._state.chargers;
      if (!config) return "";
      const toggle = `<button class="tog ${config.enabled ? "on" : ""}" data-action="chargers-enabled" role="switch" aria-checked="${config.enabled}"></button>`;
      const control = `<span class="seg">${["people", "admins"].map((value) =>
        `<button class="${config.control === value ? "on" : ""}" data-action="chargers-control" data-value="${value}">${this._t(`control_${value}`)}</button>`).join("")}</span>`;
      const row = (icon, title, help, right) => `<div class="row"><div class="ic"><ha-icon icon="${icon}"></ha-icon></div>
        <div class="tx">${this._t(title)}<small>${this._t(help)}</small></div>${right}</div>`;
      const list = config.chargers.map((charger) => this._chargerRow(charger)).join("") ||
        `<div class="row"><div class="tx"><small>${this._t("charger_none")}</small></div></div>`;
      return `<div class="card" data-chargers>
          <h2>${this._t("chargers_title")}</h2><div class="sub">${this._t("chargers_help")}</div>
          ${row("mdi:ev-station", "chargers_enabled", "chargers_enabled_help", toggle)}
          ${config.enabled ? `${row("mdi:account-key", "chargers_control", "chargers_control_help", control)}${list}
          <div class="foot"><span></span><button class="btn" data-action="charger-edit" data-id=""><ha-icon icon="mdi:plus"></ha-icon>${this._t("charger_add")}</button></div>` : ""}
        </div>`;
    }

    _chargerRow(charger) {
      const chips = [];
      if (charger.plugged === true) chips.push(["mdi:power-plug", "st_plugged"]);
      else if (charger.plugged === false) chips.push(["mdi:power-plug-off-outline", "st_free"]);
      if (charger.entities.lock) chips.push(charger.locked ? ["mdi:lock", "st_locked"] : ["mdi:lock-open-variant", "st_unlocked"]);
      if (charger.unlock === "none") chips.push(["mdi:eye-outline", "unlock_none"]);
      chips.push([charger.coverage === "no" ? "mdi:signal-off" : "mdi:signal", `coverage_${charger.coverage}`]);
      const cars = charger.vehicles.map((id) => (this._car(id) || { name: id }).name).join(", ");
      return `<div class="row chg-row"><div class="ic"><ha-icon icon="mdi:ev-station"></ha-icon></div>
        <div class="tx">${escapeHtml(charger.name)}<small>${escapeHtml(cars || this._t("charger_no_cars"))}</small>
          <div class="chg-chips">${chips.map(([icon, text]) => `<span class="chip"><ha-icon icon="${icon}"></ha-icon>${this._t(text)}</span>`).join("")}</div></div>
        <button class="btn o" data-action="charger-edit" data-id="${escapeHtml(charger.id)}"><ha-icon icon="mdi:pencil"></ha-icon>${this._t("edit")}</button></div>`;
    }

    _do_chargers_enabled() {
      const config = this._state.chargers;
      this._run("set_chargers", { enabled: !config.enabled, control: config.control }, this._t("saved"));
    }

    _do_chargers_control(data) {
      this._run("set_chargers", { enabled: true, control: data.value }, this._t("saved"));
    }

    // --- Ventana de un cargador --------------------------------------------------

    /** Entidades que valen para un papel (por dominio y, en potencia y energía, por unidad). */
    _roleEntities(role) {
      const domains = this._state.chargers.roles[role];
      const units = { power: ["W", "kW"], energy: ["kWh", "Wh"] }[role];
      return Object.values(this._hass.states)
        .filter((state) => domains.includes(state.entity_id.split(".")[0]))
        .filter((state) => !units || units.includes(state.attributes.unit_of_measurement))
        .map((state) => ({ id: state.entity_id, name: state.attributes.friendly_name || state.entity_id, state }))
        .sort((a, b) => a.name.localeCompare(b.name));
    }

    _entityState(entityId) {
      const state = entityId && this._hass.states[entityId];
      if (!state) return "";
      const unit = state.attributes.unit_of_measurement;
      return `${state.state}${unit ? ` ${unit}` : ""}`;
    }

    _do_charger_edit(data) {
      const config = this._state.chargers;
      const saved = config.chargers.find((charger) => charger.id === data.id);
      const f = JSON.parse(JSON.stringify(saved || {
        id: "", name: this._t("charger_default_name"), entities: {}, lock_on_locked: true, vehicles: this._state.cars.map((car) => car.id),
        coverage: "unknown", unlock: "confirm", notify_confirm: true, remind_minutes: 15, relock: true, relock_minutes: 5,
        relock_notify: true, loss: config.default_loss, learn: true, price: null, price_entity: "",
      }));
      f.price_mode = f.price_entity ? "entity" : f.price != null ? "fixed" : "none";
      const opt = (name, value, label) => {
        const on = String(f[name]) === String(value);
        return `<button class="${on ? "on" : ""}" data-action="set" data-f="${name}" data-v="${escapeHtml(value)}" aria-pressed="${on}">${escapeHtml(label)}</button>`;
      };
      const tog = (name) => `<button class="tog ${f[name] ? "on" : ""}" data-action="set" data-f="${name}" data-v="${!f[name]}" role="switch" aria-checked="${Boolean(f[name])}"></button>`;
      const line = (title, help, control) => `<div class="cline"><div><b>${this._t(title)}</b>${help ? `<small>${this._t(help)}</small>` : ""}</div>${control}</div>`;
      const section = (number, title, help, content) =>
        `<div class="fsec"><h4><span class="num">${number}</span>${this._t(title)}</h4>${help ? `<div class="hp">${this._t(help)}</div>` : ""}${content}</div>`;
      const select = (role) => {
        const options = this._roleEntities(role).map((item) =>
          `<option value="${escapeHtml(item.id)}" ${item.id === f.entities[role] ? "selected" : ""}>${escapeHtml(item.name)} (${escapeHtml(item.id)})</option>`).join("");
        return `<label class="ent"><span>${this._t(`role_${role}`)}${role === "plugged" ? " *" : ""}<em>${escapeHtml(this._entityState(f.entities[role]))}</em></span>
          <select data-role="${role}"><option value="">${this._t("role_none")}</option>${options}</select></label>`;
      };
      const measured = () => {
        const value = saved && saved.measured;
        if (!value) return "";
        return `<div class="learned"><ha-icon icon="mdi:chart-bell-curve-cumulative"></ha-icon><span>${this._t("loss_measured", { value: String(value.value).replace(".", ","), count: value.count })}</span>
          <button class="tb" data-action="use-loss" data-v="${value.value}">${this._t("loss_use", { value: String(value.value).replace(".", ",") })}</button></div>`;
      };
      const body = () => {
        const lockDomain = (f.entities.lock || "").split(".")[0];
        const cars = this._state.cars.map((car) => {
          const on = f.vehicles.includes(car.id);
          const photo = this._photo(car);
          return `<button class="carpick ${on ? "on" : ""}" data-action="car" data-v="${escapeHtml(car.id)}" aria-pressed="${on}">${photo ? `<img src="${photo}" alt="">` : ""}<span>${escapeHtml(car.name)}</span></button>`;
        }).join("");
        const confirm = f.unlock === "confirm";
        return `
          <div class="thead"><div class="ic"><ha-icon icon="mdi:ev-station"></ha-icon></div>
            <h2><input class="cname" data-name value="${escapeHtml(f.name)}" maxlength="40" aria-label="${this._t("charger_name")}"><small>${this._t("charger_edit_help")}</small></h2></div>
          ${section(1, "entities_title", "entities_help", ["plugged", "charging", "power", "energy", "lock"].map(select).join(""))}
          ${f.entities.lock && lockDomain !== "lock" ? line("lock_on", "lock_on_help", `<span class="seg">${opt("lock_on_locked", true, this._t("lock_on_locked"))}${opt("lock_on_locked", false, this._t("lock_on_unlocked"))}</span>`) : ""}
          ${section(2, "cars_title", "cars_help", `<div class="carpicks">${cars}</div>`)}
          ${section(3, "coverage_title", "coverage_help", `<span class="seg wide">${["yes", "no", "unknown"].map((value) => opt("coverage", value, this._t(`coverage_${value}`))).join("")}</span>`)}
          ${section(4, "unlock_title", f.entities.lock ? "unlock_help" : "unlock_no_lock", f.entities.lock ? `<span class="seg wide">${opt("unlock", "none", this._t("unlock_none"))}${opt("unlock", "confirm", this._t("unlock_confirm"))}</span>
            ${confirm ? line("ask_title", "ask_help", tog("notify_confirm")) : ""}
            ${confirm && f.notify_confirm ? line("remind_title", "remind_help", `<span class="seg">${this._state.chargers.remind_choices.map((value) => opt("remind_minutes", value, value === 60 ? "1 h" : `${value} min`)).join("")}</span>`) : ""}` : "")}
          ${f.entities.lock ? section(5, "relock_title", "", `${line("relock_on", "relock_help", tog("relock"))}
            ${f.relock ? line("relock_after", "", `<span class="seg">${this._state.chargers.relock_choices.map((value) => opt("relock_minutes", value, `${value} min`)).join("")}</span>`) : ""}
            ${f.relock ? line("relock_notify", "relock_notify_help", tog("relock_notify")) : ""}`) : ""}
          ${section(f.entities.lock ? 6 : 5, "loss_title", "loss_help", `
            ${line("loss_value", "", `<span class="fi small"><input type="number" min="0" max="40" step="0.1" data-num="loss" value="${escapeHtml(f.loss)}"><em>%</em></span>`)}
            ${line("learn_title", "learn_help", tog("learn"))}
            ${measured()}
            ${line("price_title", "price_help", `<span class="seg">${opt("price_mode", "none", this._t("price_none"))}${opt("price_mode", "fixed", this._t("price_fixed"))}${opt("price_mode", "entity", this._t("price_entity"))}</span>`)}
            ${f.price_mode === "fixed" ? `<span class="fi small"><input type="number" min="0" step="0.001" data-num="price" value="${escapeHtml(f.price == null ? "" : f.price)}"><em>€/kWh</em></span>` : ""}
            ${f.price_mode === "entity" ? `<select data-price>${["", ...Object.keys(this._hass.states).filter((id) => /^(sensor|input_number|number)\./.test(id))].map((id) =>
              `<option value="${escapeHtml(id)}" ${id === f.price_entity ? "selected" : ""}>${escapeHtml(id ? `${(this._hass.states[id].attributes.friendly_name || id)} (${id})` : this._t("role_none"))}</option>`).join("")}</select>` : ""}`)}
          <div class="err"></div>
          <div class="btns">${saved ? `<button class="tb danger left" data-action="delete">${this._t("delete")}</button>` : ""}
            <button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("save")}</button></div>`;
      };
      const paint = (open) => {
        const box = open.root.querySelector(".dlg");
        const top = box.scrollTop;
        box.innerHTML = body();
        box.scrollTop = top;
      };
      const dialog = openDialog(body(), async (action, open, target) => {
        const value = target.dataset.v;
        if (action === "set") f[target.dataset.f] = value === "true" ? true : value === "false" ? false : /^\d+$/.test(value) ? Number(value) : value;
        else if (action === "car") f.vehicles = f.vehicles.includes(value) ? f.vehicles.filter((id) => id !== value) : [...f.vehicles, value];
        else if (action === "use-loss") f.loss = Number(value);
        else if (action === "delete") {
          if (await this._run("delete_charger", { charger_id: f.id }, this._t("charger_deleted"))) open.close();
          return;
        } else if (action === "ok") {
          if (!f.entities.plugged) return open.error(this._t("error_charger_plugged"));
          const charger = { ...f, price: f.price_mode === "fixed" ? f.price : null, price_entity: f.price_mode === "entity" ? f.price_entity : "" };
          delete charger.price_mode;
          delete charger.measured;
          delete charger.plugged;
          delete charger.locked;
          try {
            await this._ws("save_charger", { charger });
          } catch (error) {
            return open.error(this._errorText(error));
          }
          open.close();
          this._toast(this._t("saved"));
          this._load();
          return;
        }
        paint(open);
      });
      dialog.root.querySelector(".dlg").classList.add("mid");
      dialog.root.addEventListener("change", (event) => {
        const target = event.target;
        if (target.dataset.role) {
          if (target.value) f.entities[target.dataset.role] = target.value;
          else delete f.entities[target.dataset.role];
          paint(dialog);
        } else if (target.dataset.price !== undefined) f.price_entity = target.value;
      });
      dialog.root.addEventListener("input", (event) => {
        const target = event.target;
        if (target.dataset.name !== undefined) f.name = target.value;
        else if (target.dataset.num) f[target.dataset.num] = target.value === "" ? null : Number(target.value);
      });
    }
  });
