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
      // En el móvil no cabe a la derecha: el selector va debajo, a todo lo ancho.
      const control = `<div class="under"><span class="seg wide">${["people", "admins"].map((value) =>
        `<button class="${config.control === value ? "on" : ""}" data-action="chargers-control" data-value="${value}">${this._t(`control_${value}`)}</button>`).join("")}</span></div>`;
      const row = (icon, title, help, right) => `<div class="row"><div class="ic"><ha-icon icon="${icon}"></ha-icon></div>
        <div class="tx">${this._t(title)}<small>${this._t(help)}</small></div>${right}</div>`;
      const list = config.chargers.map((charger) => this._chargerRow(charger)).join("") ||
        `<div class="row"><div class="tx"><small>${this._t("charger_none")}</small></div></div>`;
      return `<div class="card" data-chargers>
          <h2>${this._t("chargers_title")}</h2><div class="sub">${this._t("chargers_help")}</div>
          ${row("mdi:ev-station", "chargers_enabled", "chargers_enabled_help", toggle)}
          ${config.enabled ? `${row("mdi:account-key", "chargers_control", "chargers_control_help", "")}${control}
          ${row("mdi:battery-sync", "chargers_estimate", "chargers_estimate_help",
            `<button class="tog ${config.show_estimate ? "on" : ""}" data-action="chargers-estimate" role="switch" aria-checked="${Boolean(config.show_estimate)}"></button>`)}${list}
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

    _do_chargers_estimate() {
      const config = this._state.chargers;
      this._run("set_chargers", { enabled: true, control: config.control, show_estimate: !config.show_estimate }, this._t("saved"));
    }

    /**
     * Ventana "elegir el coche" de un cargador. Se abre al tocar la notificación
     * de confirmación (?elegir=<cargador> en la dirección del panel): en el iPhone,
     * los botones de la notificación solo salen al mantenerla pulsada.
     */
    async _pickFromLink() {
      const params = new URLSearchParams(window.location.search);
      const chargerId = params.get("elegir");
      if (!chargerId || this._picked === chargerId) return;
      this._picked = chargerId;
      let data;
      try {
        data = await this._hass.callWS({ type: "dec_deepal/chargers/state" });
      } catch (_error) {
        return;
      }
      const charger = (data.chargers || []).find((item) => item.id === chargerId);
      if (!charger) return;
      const session = charger.session;
      const cars = charger.vehicles.map((car) => {
        const photo = this._photo(car);
        return `<button class="carpick" data-action="pick" data-v="${escapeHtml(car.id)}">${photo ? `<img src="${photo}" alt="">` : ""}<span>${escapeHtml(car.name)}</span></button>`;
      }).join("");
      const waiting = session && session.waiting;
      const body = `<div class="thead"><div class="ic"><ha-icon icon="mdi:ev-station"></ha-icon></div>
          <h2>${escapeHtml(charger.name)}<small>${this._t(waiting ? "pick_title" : "pick_done")}</small></h2></div>
        ${waiting ? `<p>${this._t(charger.can_control ? "pick_help" : "pick_no_permission")}</p><div class="carpicks">${cars}</div>` : ""}
        <div class="err"></div><div class="btns"><button class="tb" data-action="close">${this._t("close")}</button></div>`;
      openDialog(body, async (action, open, target) => {
        if (action !== "pick" || !charger.can_control) return;
        try {
          await this._hass.callWS({ type: "dec_deepal/chargers/confirm", charger_id: chargerId, vehicle_id: target.dataset.v });
        } catch (error) {
          open.error(this._errorText(error));
          return;
        }
        open.close();
        this._toast(this._t("pick_unlocked", { charger: charger.name }));
      });
      // Que no se vuelva a abrir al recargar el panel.
      params.delete("elegir");
      const query = params.toString();
      window.history.replaceState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
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

    /** Estado de la entidad de un papel, en palabras: "Sí", "Desbloqueado", "3,9 kW"... */
    _entityState(role, entityId, lockOnLocked) {
      const state = entityId && this._hass.states[entityId];
      if (!state || ["unknown", "unavailable"].includes(state.state)) return state ? this._t("state_unknown") : "";
      if (role === "power" || role === "energy") {
        const number = Number(state.state);
        const unit = state.attributes.unit_of_measurement || "";
        return Number.isFinite(number) ? `${number.toLocaleString(this._language(), { maximumFractionDigits: 2 })} ${unit}`.trim() : state.state;
      }
      const on = ["on", "true", "locked", "plugged", "connected", "charging"].includes(state.state) || Number(state.state) > 0;
      if (role === "lock") {
        const locked = state.entity_id.startsWith("lock.") ? state.state === "locked" : on === lockOnLocked;
        return this._t(locked ? "st_locked" : "st_unlocked");
      }
      return this._t(on ? "state_yes" : "state_no");
    }

    _do_charger_edit(data) {
      const config = this._state.chargers;
      const saved = config.chargers.find((charger) => charger.id === data.id);
      const f = JSON.parse(JSON.stringify(saved || {
        id: "", name: this._t("charger_default_name"), entities: {}, lock_on_locked: true, vehicles: this._state.cars.map((car) => car.id),
        coverage: "unknown", unlock: "confirm", notify_confirm: true, remind_minutes: 15, relock: true, relock_minutes: 5,
        relock_notify: true, lock_full: true, lock_full_minutes: 30, loss: config.default_loss, learn: true, price: null, price_entity: "",
      }));
      f.price_mode = f.price_entity ? "entity" : f.price != null ? "fixed" : "none";
      const opt = (name, value, label) => {
        const on = String(f[name]) === String(value);
        return `<button class="${on ? "on" : ""}" data-action="set" data-f="${name}" data-v="${escapeHtml(value)}" aria-pressed="${on}">${escapeHtml(label)}</button>`;
      };
      const tog = (name) => `<button class="tog ${f[name] ? "on" : ""}" data-action="set" data-f="${name}" data-v="${!f[name]}" role="switch" aria-checked="${Boolean(f[name])}"></button>`;
      const line = (title, help, control) => `<div class="cline"><div><b>${this._t(title)}</b>${help ? `<small>${this._t(help)}</small>` : ""}</div>${control}</div>`;
      // Selector debajo del texto, a todo lo ancho y en una línea (en el móvil no cabe al lado).
      const stack = (title, help, control) =>
        `<div class="cstack">${title ? `<b>${this._t(title)}</b>` : ""}${help ? `<small>${this._t(help)}</small>` : ""}${control}</div>`;
      const choices = (...options) => `<span class="seg wide">${options.join("")}</span>`;
      const section = (number, title, help, content) =>
        `<div class="fsec"><h4><span class="num">${number}</span>${this._t(title)}</h4>${help ? `<div class="hp">${this._t(help)}</div>` : ""}${content}</div>`;
      const select = (role) => {
        const options = this._roleEntities(role).map((item) =>
          `<option value="${escapeHtml(item.id)}" ${item.id === f.entities[role] ? "selected" : ""}>${escapeHtml(item.name)}</option>`).join("");
        // El nombre en la lista y el identificador debajo, en pequeño (en el móvil no cabe todo).
        return `<label class="ent"><span>${this._t(`role_${role}`)}${role === "plugged" ? " *" : ""}<em>${escapeHtml(this._entityState(role, f.entities[role], f.lock_on_locked))}</em></span>
          <select data-role="${role}"><option value="">${this._t("role_none")}</option>${options}</select>
          ${f.entities[role] ? `<small class="eid">${escapeHtml(f.entities[role])}</small>` : ""}</label>`;
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
        // Cabecera y pie fijos (no se pierden al desplazarse); en medio, el contenido.
        return `
          <div class="dhead"><button class="x" data-action="close" aria-label="${this._t("cancel")}"><ha-icon icon="mdi:close"></ha-icon></button>
            <h2>${this._t("charger_window")}<small>${escapeHtml(f.name || "")}</small></h2>
            <button class="tb fill" data-action="ok">${this._t("save")}</button></div>
          <div class="dbody">
          <label class="cname"><span>${this._t("charger_name")}</span>
            <span class="cn"><input data-name value="${escapeHtml(f.name)}" maxlength="40"><ha-icon icon="mdi:pencil"></ha-icon></span></label>
          <div class="hp cname-help">${this._t("charger_name_help")}</div>
          ${section(1, "entities_title", "entities_help", ["plugged", "charging", "power", "energy", "lock"].map(select).join(""))}
          ${f.entities.lock && lockDomain !== "lock" ? stack("lock_on", "lock_on_help", choices(opt("lock_on_locked", true, this._t("lock_on_locked")), opt("lock_on_locked", false, this._t("lock_on_unlocked")))) : ""}
          ${section(2, "cars_title", "cars_help", `<div class="carpicks">${cars}</div>`)}
          ${section(3, "coverage_title", "coverage_help", `<span class="seg wide">${["yes", "no", "unknown"].map((value) => opt("coverage", value, this._t(`coverage_${value}`))).join("")}</span>`)}
          ${section(4, "unlock_title", f.entities.lock ? "unlock_help" : "unlock_no_lock", f.entities.lock ? `<span class="seg wide">${opt("unlock", "none", this._t("unlock_none"))}${opt("unlock", "confirm", this._t("unlock_confirm"))}</span>
            ${confirm ? line("ask_title", "ask_help", tog("notify_confirm")) : ""}
            ${confirm && f.notify_confirm ? stack("remind_title", "remind_help", choices(...this._state.chargers.remind_choices.map((value) => opt("remind_minutes", value, value === 60 ? "1 h" : `${value} min`)))) : ""}` : "")}
          ${f.entities.lock ? section(5, "relock_title", "", `${line("relock_on", "relock_help", tog("relock"))}
            ${f.relock ? stack("relock_after", "", choices(...this._state.chargers.relock_choices.map((value) => opt("relock_minutes", value, `${value} min`)))) : ""}
            ${line("lock_full", "lock_full_help", tog("lock_full"))}
            ${f.lock_full ? stack("", "", choices(...this._state.chargers.lock_full_choices.map((value) => opt("lock_full_minutes", value, `${value} min`)))) : ""}
            ${f.relock || f.lock_full ? line("relock_notify", "relock_notify_help", tog("relock_notify")) : ""}`) : ""}
          ${section(f.entities.lock ? 6 : 5, "loss_title", "loss_help", `
            ${line("loss_value", "", `<span class="fi small"><input type="number" min="0" max="40" step="0.1" data-num="loss" value="${escapeHtml(f.loss)}"><em>%</em></span>`)}
            ${line("learn_title", "learn_help", tog("learn"))}
            ${measured()}
            ${stack("price_title", "price_help", choices(opt("price_mode", "none", this._t("price_none")), opt("price_mode", "fixed", this._t("price_fixed")), opt("price_mode", "entity", this._t("price_entity"))))}
            ${f.price_mode === "fixed" ? `<span class="fi wide"><input type="number" min="0" step="0.001" data-num="price" value="${escapeHtml(f.price == null ? "" : f.price)}"><em>€/kWh</em></span>` : ""}
            ${f.price_mode === "entity" ? `<select data-price>${["", ...Object.keys(this._hass.states).filter((id) => /^(sensor|input_number|number)\./.test(id))].map((id) =>
              `<option value="${escapeHtml(id)}" ${id === f.price_entity ? "selected" : ""}>${escapeHtml(id ? `${(this._hass.states[id].attributes.friendly_name || id)} (${id})` : this._t("role_none"))}</option>`).join("")}</select>` : ""}`)}
          </div>
          <div class="dfoot"><div class="err"></div>
            <div class="btns">${saved ? `<button class="tb danger left" data-action="delete">${this._t("delete")}</button>` : ""}
              <button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("save")}</button></div></div>`;
      };
      const paint = (open) => {
        const box = open.root.querySelector(".dlg");
        const top = box.querySelector(".dbody").scrollTop;
        box.innerHTML = body();
        box.querySelector(".dbody").scrollTop = top;
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
      dialog.root.querySelector(".dlg").classList.add("mid", "sheet");
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
        if (target.dataset.name !== undefined) {
          f.name = target.value;
          dialog.root.querySelector(".dhead small").textContent = target.value;
        }
        else if (target.dataset.num) f[target.dataset.num] = target.value === "" ? null : Number(target.value);
      });
    }
  });
