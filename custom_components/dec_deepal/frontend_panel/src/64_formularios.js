  // ---------------------------------------------------------------------------
  // Engranajes de "Coches": configurar mantenimiento, ITV y seguro
  // ---------------------------------------------------------------------------
  // Los mismos datos que piden los apartados de Configurar, en una ventana.
  install(class {
    _do_gear(data) {
      const car = this._car(data.car);
      this[`_form_${data.kind}`](car);
    }

    _today() {
      const now = new Date();
      const two = (value) => String(value).padStart(2, "0");
      return `${now.getFullYear()}-${two(now.getMonth() + 1)}-${two(now.getDate())}`;
    }

    /** Campo de formulario: etiqueta, control y, si la hay, una ayuda. */
    _field(name, label, attributes, help) {
      return `<label>${this._t(label)}<input name="${name}" ${attributes}>${help ? `<small>${this._t(help)}</small>` : ""}</label>`;
    }

    /**
     * Ventana de un apartado. Con "Activado" desmarcado se guarda como
     * desactivado (y se quitan sus entidades y avisos).
     */
    _form(car, kind, enabled, fields, extra, save) {
      const dialog = openDialog(
        `<h2>${this._t(`section_${kind}`)} — ${escapeHtml(car.name)}</h2>
         <label class="check"><input type="checkbox" name="enabled" ${enabled ? "checked" : ""}>${this._t("enabled")}</label>
         <div class="fields">${fields}</div>
         <div class="err"></div>
         <div class="btns">${extra || ""}<button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("save")}</button></div>`,
        async (action, current) => {
          if (action === "extra") {
            current.close();
            return this[`_register_${kind}`](car);
          }
          if (action !== "ok") return undefined;
          const values = current.values();
          const message = values.enabled ? save.check(values) : "";
          if (message) return current.error(message);
          current.close();
          return this._run(`set_${kind}`, { vehicle_id: car.id, ...(values.enabled ? save.data(values) : { enabled: false }) }, this._t("saved"));
        }
      );
      const toggle = () => {
        dialog.root.querySelector(".fields").hidden = !dialog.root.querySelector('[name="enabled"]').checked;
      };
      dialog.root.querySelector('[name="enabled"]').addEventListener("change", toggle);
      toggle();
    }

    _required(values, names) {
      return names.every((name) => String(values[name] || "").trim()) ? "" : this._t("error_required");
    }

    _form_maintenance(car) {
      const data = car.maintenance;
      const record = data ? data.record : { services_done: 0, last_date: "", last_km: 0, ...car.plan };
      const fields = `
        ${this._field("services_done", "mt_services_done", `type="number" min="0" max="50" value="${record.services_done}"`, "mt_services_done_help")}
        <div class="two">
          ${this._field("last_date", "mt_last_date", `type="date" value="${escapeHtml(record.last_date)}"`)}
          ${this._field("last_km", "mt_last_km", `type="number" min="0" max="2000000" value="${record.last_km}"`)}
          ${this._field("interval_km", "mt_interval_km", `type="number" min="1000" max="100000" step="500" value="${record.interval_km}"`)}
          ${this._field("interval_months", "mt_interval_months", `type="number" min="1" max="60" value="${record.interval_months}"`)}
        </div>`;
      const extra = data ? `<button class="tb left" data-action="extra">${this._t("mt_register")}</button>` : "";
      this._form(car, "maintenance", true, fields, extra, {
        check: (values) => this._required(values, ["last_date", "interval_km", "interval_months"]),
        data: (values) => ({
          enabled: true,
          services_done: Number(values.services_done) || 0,
          last_date: values.last_date,
          last_km: Number(values.last_km) || 0,
          interval_km: Number(values.interval_km),
          interval_months: Number(values.interval_months),
        }),
      });
    }

    /** Registrar una revisión hecha: fecha y kilómetros (por defecto, hoy y los del coche). */
    _register_maintenance(car) {
      openDialog(
        `<h2>${this._t("mt_register")}</h2><p>${this._t("mt_register_help", { name: escapeHtml(car.name), number: car.maintenance.number })}</p>
         <div class="two">${this._field("date", "date", `type="date" value="${this._today()}"`)}
           ${this._field("km", "mt_km", `type="number" min="0" max="2000000" value="${Math.round(car.odometer || 0)}"`)}</div>
         <div class="err"></div>
         <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("register")}</button></div>`,
        (action, dialog) => {
          if (action !== "ok") return undefined;
          const values = dialog.values();
          if (!values.date) return dialog.error(this._t("error_required"));
          dialog.close();
          return this._run("register_maintenance", { vehicle_id: car.id, date: values.date, km: Number(values.km) || 0 }, this._t("registered"));
        }
      );
    }

    _form_itv(car) {
      const data = car.itv;
      const record = data ? data.record : { registration_date: "", last_date: "", next_override: "" };
      const fields = `
        ${this._field("registration_date", "itv_registration", `type="date" value="${escapeHtml(record.registration_date || "")}"`)}
        ${this._field("last_date", "itv_last", `type="date" value="${escapeHtml(record.last_date || "")}"`, "itv_last_help")}
        ${this._field("next_date", "itv_next", `type="date" value="${escapeHtml(record.next_override || "")}"`, "itv_next_help")}`;
      const extra = data ? `<button class="tb left" data-action="extra">${this._t("itv_register")}</button>` : "";
      this._form(car, "itv", true, fields, extra, {
        check: (values) => this._required(values, ["registration_date"]),
        data: (values) => ({
          enabled: true,
          registration_date: values.registration_date,
          last_date: values.last_date || null,
          next_date: values.next_date || null,
        }),
      });
    }

    _register_itv(car) {
      openDialog(
        `<h2>${this._t("itv_register")}</h2><p>${this._t("itv_register_help", { name: escapeHtml(car.name) })}</p>
         ${this._field("date", "date", `type="date" value="${this._today()}"`)}
         <div class="err"></div>
         <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("register")}</button></div>`,
        (action, dialog) => {
          if (action !== "ok") return undefined;
          const values = dialog.values();
          if (!values.date) return dialog.error(this._t("error_required"));
          dialog.close();
          return this._run("register_itv", { vehicle_id: car.id, date: values.date }, this._t("registered"));
        }
      );
    }

    _form_insurance(car) {
      const data = car.insurance;
      const record = data ? data.record
        : { renewal_date: "", company: "", policy: "", kind: this._state.insurance_kinds[0], notice_days: 30, phone_assistance: "", phone_company: "" };
      const kinds = this._state.insurance_kinds
        .map((kind) => `<option value="${kind}" ${kind === record.kind ? "selected" : ""}>${this._t(`kind_${kind}`)}</option>`)
        .join("");
      const text = (name, label, value, type) => this._field(name, label, `type="${type || "text"}" value="${escapeHtml(value || "")}"`);
      const fields = `
        <div class="two">${text("company", "ins_company", record.company)}${text("policy", "ins_policy", record.policy)}</div>
        <label>${this._t("ins_kind")}<select name="kind">${kinds}</select></label>
        <div class="two">
          ${this._field("renewal_date", "ins_renewal", `type="date" value="${escapeHtml(record.renewal_date)}"`)}
          ${this._field("notice_days", "ins_notice", `type="number" min="1" max="180" value="${record.notice_days}"`)}
          ${text("phone_assistance", "ins_phone_assistance", record.phone_assistance, "tel")}
          ${text("phone_company", "ins_phone_company", record.phone_company, "tel")}
        </div>`;
      this._form(car, "insurance", true, fields, "", {
        check: (values) => this._required(values, ["renewal_date", "notice_days"]),
        data: (values) => ({
          enabled: true,
          renewal_date: values.renewal_date,
          company: values.company,
          policy: values.policy,
          kind: values.kind,
          notice_days: Number(values.notice_days),
          phone_assistance: values.phone_assistance,
          phone_company: values.phone_company,
        }),
      });
    }
  });
