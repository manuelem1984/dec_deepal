  // ---------------------------------------------------------------------------
  // Fichas de "Coches": la ventana que se abre al pulsar un recuadro
  // ---------------------------------------------------------------------------
  // Pulsar el recuadro (no su engranaje) enseña la información: qué toca en
  // la revisión, las fechas de la ITV, los datos del seguro. El engranaje de
  // dentro lleva al formulario. Sin configurar, se abre el formulario directamente.
  install(class {
    _do_info(data) {
      const car = this._car(data.car);
      if (!car[data.kind]) return this._do_gear(data);
      return this[`_info_${data.kind}`](car);
    }

    /**
     * Ventana de ficha: cabecera, cuerpo y pie con el engranaje.
     * `actions(action, dialog)` atiende los botones propios de la ficha.
     */
    _infoWindow(car, kind, icon, body, buttons, actions) {
      const dialog = openDialog(
        `<div class="thead"><div class="ic"><ha-icon icon="${icon}"></ha-icon></div>
           <h2>${this._t(`section_${kind}`)}<small>${escapeHtml(car.name)} · ${escapeHtml(car.model)}</small></h2>
           <button class="x" data-action="close" aria-label="${this._t("close")}"><ha-icon icon="mdi:close"></ha-icon></button></div>
         ${body}
         <div class="ifoot">${this._admin() ? `<button class="gearb" data-action="configure" aria-label="${this._t("configure")}"><ha-icon icon="mdi:cog"></ha-icon></button>` : ""}<span></span>${buttons || ""}
           <button class="tb" data-action="close">${this._t("close")}</button></div>`,
        (action, open, target) => {
          if (action === "configure" && this._admin()) {
            open.close();
            return this._do_gear({ car: car.id, kind });
          }
          return actions ? actions(action, open, target) : undefined;
        }
      );
      dialog.root.querySelector(".dlg").classList.add("mid");
      return dialog;
    }

    _stat(icon, label, value, detail, fraction) {
      return `<div class="stat"><div class="k"><ha-icon icon="${icon}"></ha-icon>${this._t(label)}</div><div class="n">${escapeHtml(value)}</div><div class="d">${escapeHtml(detail)}</div>
        ${fraction == null ? "" : `<div class="meter"><i style="width:${Math.round(Math.max(0, Math.min(1, fraction)) * 100)}%"></i></div>`}</div>`;
    }

    /** "Inspección general (propulsión, frenos)" → título y, debajo, lo del paréntesis. */
    _operation(name) {
      const match = /^(.*?)\s*\((.*)\)\s*$/.exec(name);
      const title = match ? match[1] : name;
      const note = match ? match[2].charAt(0).toUpperCase() + match[2].slice(1) : "";
      return `<li><ha-icon icon="mdi:check-circle-outline"></ha-icon><div>${escapeHtml(title)}${note ? `<small>${escapeHtml(note)}</small>` : ""}</div></li>`;
    }

    // --- Mantenimiento -------------------------------------------------------------

    _info_maintenance(car) {
      const data = car.maintenance;
      const record = data.record;
      const odometer = car.odometer == null ? null : Math.round(car.odometer);
      const overdueDays = data.days_left < 0;
      const overdueKm = data.km_left != null && data.km_left < 0;
      const history = (record.history || []).slice().reverse();
      const body = `
        <div class="big">${this._t("service_number", { number: data.number })}</div>
        <div class="bigsub">${this._t("mt_whichever", { date: this._date(data.due_date), km: this._number(data.due_km) })}</div>
        <div class="dual">
          ${this._stat("mdi:calendar", "by_time", overdueDays ? this._t("overdue") : this._days(data.days_left), this._date(data.due_date),
            1 - data.days_left / (record.interval_months * 30.4))}
          ${data.km_left == null ? "" : this._stat("mdi:counter", "by_km", overdueKm ? this._t("overdue") : `${this._number(data.km_left)} km`,
            this._t("mt_km_detail", { now: this._number(odometer == null ? 0 : odometer), due: this._number(data.due_km) }), 1 - data.km_left / record.interval_km)}
        </div>
        <div class="h3">${this._t("mt_this_service")}${data.operations.length ? `<span>· ${this._t("n_operations", { count: data.operations.length })}</span>` : ""}</div>
        ${data.operations.length ? `<ul class="ops">${data.operations.map((name) => this._operation(name)).join("")}</ul>` : `<div class="hist">${this._t("mt_no_plan")}</div>`}
        ${data.next_extra && data.next_extra.length ? `<div class="h3">${this._t("mt_next_adds", { number: data.number + 1 })}</div>
          <div>${data.next_extra.map((name) => `<span class="chip">${escapeHtml(name.replace(/\s*\(.*\)\s*$/, ""))}</span>`).join("")}</div>` : ""}
        <div class="h3">${this._t("history")}</div>
        ${history.length ? history.map((item) => `<div class="hist"><ha-icon icon="mdi:check"></ha-icon>${this._t("mt_history_item", {
            number: item.number, date: this._date(item.date), km: this._number(item.km) })}</div>`).join("")
          : `<div class="hist"><ha-icon icon="mdi:history"></ha-icon>${this._t("mt_no_history")}</div>`}`;
      const buttons = `${car.manual_url ? `<a class="tb" href="${escapeHtml(car.manual_url)}" target="_blank" rel="noopener noreferrer">${this._t("manual")}</a>` : ""}
        ${this._admin() ? `<button class="tb fill" data-action="register">${this._t("mt_register")}</button>` : ""}`;
      this._infoWindow(car, "maintenance", "mdi:wrench", body, buttons, (action, open) => {
        if (action !== "register") return;
        open.close();
        this._register_maintenance(car);
      });
    }

    /** Registrar una revisión hecha: fecha y kilómetros (por defecto, hoy y los del coche). */
    _register_maintenance(car) {
      openDialog(
        `<h2>${this._t("mt_register")}</h2><p>${this._t("mt_register_help", { name: escapeHtml(car.name), number: car.maintenance.number })}</p>
         <div class="two"><label>${this._t("date")}<input name="date" type="date" value="${isoDate(today())}"></label>
           <label>${this._t("mt_km")}<input name="km" type="number" min="0" max="2000000" value="${Math.round(car.odometer || 0)}"></label></div>
         <div class="err"></div>
         <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("register")}</button></div>`,
        (action, dialog) => {
          if (action !== "ok") return undefined;
          const values = dialog.values();
          if (!parseDate(values.date)) return dialog.error(this._t("error_required"));
          dialog.close();
          return this._run("register_maintenance", { vehicle_id: car.id, date: values.date, km: Number(values.km) || 0 }, this._t("registered"));
        }
      );
    }

    // --- ITV -------------------------------------------------------------------------

    _info_itv(car) {
      const data = car.itv;
      const record = data.record;
      const overdue = data.days_left < 0;
      const history = (record.history || []).slice().reverse();
      const rules = car.itv_rules;
      // Edad del coche: solo se dice cuando ya son años en plural.
      const years = Math.floor(daysBetween(parseDate(record.registration_date), today()) / 365.25);
      const body = `
        <div class="big">${this._date(data.due_date)}</div>
        <div class="bigsub">${overdue ? this._t("overdue_since", { days: this._days(data.days_left) }) : this._t("left", { parts: this._days(data.days_left) })}${
          record.next_override ? ` · ${this._t("itv_manual_date")}` : ""}</div>
        <div class="dual">
          ${this._stat("mdi:card-account-details-outline", "itv_registration", this._date(record.registration_date), years >= 2 ? this._t("itv_age", { years }) : "")}
          ${this._stat("mdi:clipboard-check-outline", "itv_last", record.last_date ? this._date(record.last_date) : this._t("itv_none_yet"),
            record.last_date ? "" : this._t("itv_first_at", { years: Math.round(rules.first_months / 12) }))}
        </div>
        <div class="h3">${this._t("itv_rules_title")}</div>
        <div class="hist"><ha-icon icon="mdi:information-outline"></ha-icon>${this._t("itv_rules", {
          first: Math.round(rules.first_months / 12), interval: Math.round(rules.interval_months / 12), reduced: Math.round(rules.reduced_from_months / 12) })}</div>
        <div class="h3">${this._t("history")}</div>
        ${history.length ? history.map((date) => `<div class="hist"><ha-icon icon="mdi:check"></ha-icon>${this._t("itv_history_item", { date: this._date(date) })}</div>`).join("")
          : `<div class="hist"><ha-icon icon="mdi:history"></ha-icon>${this._t("itv_no_history")}</div>`}`;
      this._infoWindow(car, "itv", "mdi:clipboard-check-outline", body,
        this._admin() ? `<button class="tb fill" data-action="register">${this._t("itv_register")}</button>` : "", (action, open) => {
          if (action !== "register") return;
          open.close();
          this._register_itv(car);
        });
    }

    _register_itv(car) {
      openDialog(
        `<h2>${this._t("itv_register")}</h2><p>${this._t("itv_register_help", { name: escapeHtml(car.name) })}</p>
         <label>${this._t("date")}<input name="date" type="date" value="${isoDate(today())}"></label>
         <div class="err"></div>
         <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("register")}</button></div>`,
        (action, dialog) => {
          if (action !== "ok") return undefined;
          const values = dialog.values();
          if (!parseDate(values.date)) return dialog.error(this._t("error_required"));
          dialog.close();
          return this._run("register_itv", { vehicle_id: car.id, date: values.date }, this._t("registered"));
        }
      );
    }

    // --- Seguro ----------------------------------------------------------------------

    _info_insurance(car) {
      const data = car.insurance;
      const record = data.record;
      // Línea del año: de la renovación anterior a la próxima.
      const at = (days) => Math.max(0, Math.min(100, (1 - days / 365) * 100));
      const now = at(data.days_to_renewal);
      const deadline = at(record.notice_days);
      const first = car.alerts.thresholds.insurance_c1 || 30;
      const amber = at(record.notice_days + first);
      const passed = data.days_to_cancel < 0;
      const call = (number, icon, label) => !number ? "" :
        `<a class="callb" data-action="call" data-number="${escapeHtml(number)}" target="_blank" rel="noopener noreferrer" href="tel:${escapeHtml(String(number).replace(/[^0-9+]/g, ""))}">
           <ha-icon icon="${icon}"></ha-icon><span><b>${this._t(label)}</b><small>${escapeHtml(number)}</small></span></a>`;
      const calls = call(record.phone_assistance, "mdi:tow-truck", "ins_assistance") + call(record.phone_company, "mdi:phone", "ins_company");
      const body = `
        <div class="big">${escapeHtml(record.company || this._t("section_insurance"))}</div>
        <div class="bigsub"><span class="badge info">${this._t(`kind_${record.kind}`)}</span></div>
        ${record.policy ? `<div class="pol"><span>${this._t("ins_policy")}</span><b>${escapeHtml(record.policy)}</b>
          <button class="x" data-action="copy" data-text="${escapeHtml(record.policy)}" aria-label="${this._t("copy")}"><ha-icon icon="mdi:content-copy"></ha-icon></button></div>` : ""}
        <div class="h3">${this._t("ins_dates")}</div>
        <div class="line"><div class="track"></div><div class="fill" style="width:${now}%"></div>
          <div class="amber" style="left:${amber}%;width:${Math.max(0, deadline - amber)}%"></div>
          <div class="pt now" style="left:${now}%"></div><div class="pt" style="left:${deadline}%"></div><div class="pt" style="left:100%"></div></div>
        <div class="dual">
          ${this._stat("mdi:calendar-alert", "ins_to_cancel", passed ? this._t("ins_deadline_passed") : this._days(data.days_to_cancel),
            this._t("ins_deadline_on", { date: this._date(data.cancel_deadline) }))}
          ${this._stat("mdi:autorenew", "ins_to_renewal", this._days(data.days_to_renewal), this._t("ins_renews_itself", { date: this._date(record.renewal_date) }))}
        </div>
        ${calls ? `<div class="h3">${this._t("ins_phones_title")}</div><div class="calls">${calls}</div>` : ""}`;
      this._infoWindow(car, "insurance", "mdi:shield-car", body, "", (action, _open, target) => {
        // El enlace "tel:" abre el marcador por su cuenta; aquí solo se copia.
        const text = action === "call" ? target.dataset.number : action === "copy" ? target.dataset.text : "";
        if (text && navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(() => this._toast(this._t("copied", { text })), () => undefined);
        }
      });
    }
  });
