  // ---------------------------------------------------------------------------
  // Engranajes de "Coches": configurar mantenimiento, ITV y seguro
  // ---------------------------------------------------------------------------
  // Cada formulario va por bloques y termina con un recuadro que dice qué va a
  // pasar ("Próxima revisión: ..."), recalculado según se escribe. Lo escrito
  // vive en un objeto `f`; al pulsar una opción se repinta la ventana entera,
  // y al teclear solo el recuadro (para no perder el cursor).
  install(class {
    _do_gear(data) {
      this[`_form_${data.kind}`](this._car(data.car));
    }

    /** Campo de texto, fecha o número. `more`: atributos; `unit`: unidad a la derecha. */
    _input(f, name, label, type, more, unit) {
      return `<label class="fld"><span>${this._t(label)}</span>
        <span class="fi"><input data-f="${name}" type="${type}" value="${escapeHtml(f[name] == null ? "" : f[name])}" ${more || ""}>${unit ? `<em>${unit}</em>` : ""}</span></label>`;
    }

    _section(icon, title, help, body) {
      return `<div class="fsec"><h4><ha-icon icon="${icon}"></ha-icon>${this._t(title)}</h4><div class="hp">${this._t(help)}</div>${body}</div>`;
    }

    /** Opción de un grupo (una está elegida): botón con título y, si la hay, una nota. */
    _choice(f, name, value, title, note) {
      const on = String(f[name]) === String(value);
      return `<button class="opt ${on ? "on" : ""}" data-action="set" data-f="${name}" data-v="${escapeHtml(value)}" aria-pressed="${on}">${escapeHtml(title)}${note ? `<small>${escapeHtml(note)}</small>` : ""}</button>`;
    }

    /**
     * Ventana de un apartado.
     *
     * @param parts
     *   sections(f)  bloques del formulario (HTML)
     *   preview(f)   `{ icon, title, detail }` del recuadro final, o `null` si aún faltan datos
     *   check(f)     texto del error que impide guardar ("" = todo bien)
     *   data(f)      lo que se manda a la integración
     */
    _formWindow(car, kind, icon, f, parts) {
      const preview = () => {
        const result = f.enabled ? parts.preview(f) : null;
        return result
          ? `<div class="preview"><ha-icon icon="${result.icon}"></ha-icon><div><b>${escapeHtml(result.title)}</b><small>${escapeHtml(result.detail)}</small></div></div>`
          : "";
      };
      const body = () => `
        <div class="thead"><div class="ic"><ha-icon icon="${icon}"></ha-icon></div>
          <h2>${this._t(`form_${kind}`)}<small>${escapeHtml(car.name)} · ${escapeHtml(car.model)}</small></h2>
          <span class="sw2">${this._t("enabled")}<button class="tog ${f.enabled ? "on" : ""}" data-action="set" data-f="enabled" data-v="${!f.enabled}" role="switch" aria-checked="${f.enabled}"></button></span></div>
        ${f.enabled ? `${parts.sections(f)}<div class="slot">${preview()}</div>` : `<p class="off">${this._t(`form_${kind}_off`)}</p>`}
        <div class="err"></div>
        <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("save")}</button></div>`;
      const dialog = openDialog(body(), (action, open, target) => {
        const data = target.dataset;
        if (action === "set") f[data.f] = data.v === "true" ? true : data.v === "false" ? false : data.v;
        else if (action === "step") f[data.f] = Math.max(0, Math.min(50, (Number(f[data.f]) || 0) + Number(data.d)));
        else if (action === "use") f[data.f] = data.v;
        else if (action === "ok") {
          const message = f.enabled ? parts.check(f) : "";
          if (message) return open.error(message);
          open.close();
          return this._run(`set_${kind}`, { vehicle_id: car.id, ...(f.enabled ? parts.data(f) : { enabled: false }) }, this._t("saved"));
        } else return undefined;
        open.root.querySelector(".dlg").innerHTML = body();
        return undefined;
      });
      dialog.root.querySelector(".dlg").classList.add("mid");
      dialog.root.addEventListener("input", (event) => {
        const name = event.target.dataset && event.target.dataset.f;
        if (!name) return;
        f[name] = event.target.value;
        const slot = dialog.root.querySelector(".slot");
        if (slot) slot.innerHTML = preview();
      });
    }

    // --- Mantenimiento -------------------------------------------------------------

    _form_maintenance(car) {
      const record = car.maintenance ? car.maintenance.record : null;
      const plan = car.plan;
      const f = {
        enabled: true,
        services_done: record ? record.services_done : 0,
        last_date: record ? record.last_date : "",
        last_km: record ? record.last_km : 0,
        interval_km: record ? record.interval_km : plan.interval_km,
        interval_months: record ? record.interval_months : plan.interval_months,
      };
      f.interval = Number(f.interval_km) === plan.interval_km && Number(f.interval_months) === plan.interval_months ? "manual" : "other";
      const odometer = car.odometer == null ? null : Math.round(car.odometer);
      /** Intervalo que cuenta: el del manual o el escrito. */
      const interval = () => (f.interval === "manual"
        ? { km: plan.interval_km, months: plan.interval_months }
        : { km: Number(f.interval_km), months: Number(f.interval_months) });
      this._formWindow(car, "maintenance", "mdi:wrench", f, {
        sections: () => `
          ${this._section("mdi:history", "mt_last", "mt_last_help", `
            <div class="inline"><label class="fld"><span>${this._t("mt_services_done")}</span>
                <span class="stepper"><button data-action="step" data-f="services_done" data-d="-1" aria-label="−">−</button><b>${Number(f.services_done) || 0}</b><button data-action="step" data-f="services_done" data-d="1" aria-label="+">+</button></span></label>
              <span class="note">${this._t("mt_next_is", { number: (Number(f.services_done) || 0) + 1 })}</span></div>
            <div class="fg">${this._input(f, "last_date", "date", "date")}
              <div>${this._input(f, "last_km", "mt_km_then", "number", 'min="0" max="2000000"', "km")}
                ${odometer == null ? "" : `<button class="hint" data-action="use" data-f="last_km" data-v="${odometer}"><ha-icon icon="mdi:car-arrow-left"></ha-icon>${this._t("mt_use_odometer", { km: this._number(odometer) })}</button>`}</div></div>`)}
          ${this._section("mdi:calendar-sync", "mt_every", "mt_every_help", `
            <div class="opts">${this._choice(f, "interval", "manual", this._t("mt_interval_manual"), this._t("mt_interval_value", { km: this._number(plan.interval_km), months: plan.interval_months }))}
              ${this._choice(f, "interval", "other", this._t("other"), this._t("mt_interval_other"))}</div>
            ${f.interval !== "other" ? "" : `<div class="fg">${this._input(f, "interval_km", "mt_interval_km", "number", 'min="1000" max="100000" step="500"', "km")}
              ${this._input(f, "interval_months", "mt_interval_months", "number", 'min="1" max="60"')}</div>`}`)}`,
        preview: () => {
          const last = parseDate(f.last_date);
          const every = interval();
          if (!last || !(every.km > 0) || !(every.months > 0)) return null;
          const due = addMonths(last, every.months);
          const dueKm = (Number(f.last_km) || 0) + every.km;
          const days = daysBetween(today(), due);
          const parts = [days >= 0 ? this._days(days) : ""];
          if (odometer != null && dueKm - odometer >= 0) parts.push(`${this._number(dueKm - odometer)} km`);
          const left = parts.filter(Boolean).join(this._t("or"));
          const overdue = days < 0 || (odometer != null && dueKm - odometer < 0);
          return {
            icon: "mdi:calendar-check",
            title: this._t("mt_preview", { date: this._date(isoDate(due)), km: this._number(dueKm) }),
            detail: overdue || !left ? this._t("overdue") : this._t("left", { parts: left }),
          };
        },
        check: () => {
          const every = interval();
          if (!parseDate(f.last_date) || !(every.km >= 1000) || !(every.months >= 1)) return this._t("error_required");
          return "";
        },
        data: () => {
          const every = interval();
          return {
            enabled: true,
            services_done: Number(f.services_done) || 0,
            last_date: f.last_date,
            last_km: Math.round(Number(f.last_km) || 0),
            interval_km: Math.round(every.km),
            interval_months: Math.round(every.months),
          };
        },
      });
    }

    // --- ITV -------------------------------------------------------------------------

    /** Próxima ITV según las normas del país (igual que `documents.itv_calculated`). */
    _itvCalculated(car, registration, last) {
      const rules = car.itv_rules;
      if (!last) return addMonths(registration, rules.first_months);
      const old = last >= addMonths(registration, rules.reduced_from_months);
      return addMonths(last, old ? rules.reduced_interval_months : rules.interval_months);
    }

    _form_itv(car) {
      const record = car.itv ? car.itv.record : null;
      const f = {
        enabled: true,
        registration_date: record ? record.registration_date : "",
        passed: Boolean(record && record.last_date),
        last_date: (record && record.last_date) || "",
        next: record && record.next_override ? "manual" : "auto",
        next_date: (record && record.next_override) || "",
      };
      const calculated = () => {
        const registration = parseDate(f.registration_date);
        const last = f.passed ? parseDate(f.last_date) : null;
        if (!registration || (f.passed && !last)) return null;
        return this._itvCalculated(car, registration, last);
      };
      const first = car.alerts.thresholds.itv_t1 || 60;
      this._formWindow(car, "itv", "mdi:clipboard-check-outline", f, {
        sections: () => {
          const auto = calculated();
          return `
          ${this._section("mdi:card-account-details-outline", "itv_registration_title", "itv_registration_help",
            `<div class="fg">${this._input(f, "registration_date", "itv_registration", "date")}<div></div></div>`)}
          ${this._section("mdi:clipboard-text-clock-outline", "itv_passed_title", "itv_passed_help", `
            <div class="inline"><button class="tog ${f.passed ? "on" : ""}" data-action="set" data-f="passed" data-v="${!f.passed}" role="switch" aria-checked="${f.passed}"></button><span>${this._t("itv_passed")}</span></div>
            ${f.passed ? `<div class="fg">${this._input(f, "last_date", "itv_last", "date")}<div></div></div>` : ""}`)}
          ${this._section("mdi:calendar-edit", "itv_next_title", "itv_next_rules", `
            <div class="opts">${this._choice(f, "next", "auto", this._t("itv_next_auto"), auto ? this._date(isoDate(auto)) : "")}
              ${this._choice(f, "next", "manual", this._t("itv_next_manual"), this._t("itv_next_manual_note"))}</div>
            ${f.next === "manual" ? `<div class="fg">${this._input(f, "next_date", "itv_next", "date")}<div></div></div>` : ""}`)}`;
        },
        preview: () => {
          const due = f.next === "manual" ? parseDate(f.next_date) : calculated();
          if (!due) return null;
          const days = daysBetween(today(), due);
          return {
            icon: "mdi:calendar-check",
            title: this._t("itv_preview", { date: this._date(isoDate(due)) }),
            detail: days < 0 ? this._t("overdue_since", { days: this._days(days) }) : `${this._t("left", { parts: this._days(days) })}. ${this._t("first_notice", { days: first })}`,
          };
        },
        check: () => {
          if (!parseDate(f.registration_date)) return this._t("error_required");
          if (f.passed && !parseDate(f.last_date)) return this._t("error_required");
          if (f.next === "manual" && !parseDate(f.next_date)) return this._t("error_required");
          return "";
        },
        data: () => ({
          enabled: true,
          registration_date: f.registration_date,
          last_date: f.passed ? f.last_date : null,
          next_date: f.next === "manual" ? f.next_date : null,
        }),
      });
    }

    // --- Seguro ----------------------------------------------------------------------

    _form_insurance(car) {
      const record = car.insurance ? car.insurance.record : null;
      const days = record ? record.notice_days : 30;
      const f = {
        enabled: true,
        company: record ? record.company : "",
        policy: record ? record.policy : "",
        kind: record ? record.kind : this._state.insurance_kinds[0],
        renewal_date: record ? record.renewal_date : "",
        notice: [15, 30, 60].includes(days) ? String(days) : "other",
        notice_days: days,
        phone_assistance: record ? record.phone_assistance : "",
        phone_company: record ? record.phone_company : "",
      };
      const notice = () => (f.notice === "other" ? Math.round(Number(f.notice_days)) : Number(f.notice));
      const KIND_ICONS = { third_party: "mdi:shield-outline", third_party_plus: "mdi:shield-half-full", comprehensive_excess: "mdi:shield-check", comprehensive: "mdi:shield-star" };
      const first = car.alerts.thresholds.insurance_c1 || 30;
      this._formWindow(car, "insurance", "mdi:shield-car", f, {
        sections: () => `
          ${this._section("mdi:domain", "ins_policy_title", "ins_policy_help", `
            <div class="fg">${this._input(f, "company", "ins_company", "text")}${this._input(f, "policy", "ins_policy", "text")}</div>
            <div class="fl">${this._t("ins_kind")}</div>
            <div class="kinds">${this._state.insurance_kinds.map((kind) =>
              `<button class="kind ${f.kind === kind ? "on" : ""}" data-action="set" data-f="kind" data-v="${kind}" aria-pressed="${f.kind === kind}"><ha-icon icon="${KIND_ICONS[kind] || "mdi:shield"}"></ha-icon>${this._t(`kind_${kind}`)}</button>`).join("")}</div>`)}
          ${this._section("mdi:calendar-refresh", "ins_renewal_title", "ins_renewal_help", `
            <div class="fg">${this._input(f, "renewal_date", "ins_renews_on", "date")}
              <div><div class="fl">${this._t("ins_notice")}</div><span class="seg">${["15", "30", "60"].map((value) =>
                `<button class="${f.notice === value ? "on" : ""}" data-action="set" data-f="notice" data-v="${value}">${this._days(Number(value))}</button>`).join("")}
                <button class="${f.notice === "other" ? "on" : ""}" data-action="set" data-f="notice" data-v="other">${this._t("other")}</button></span></div></div>
            ${f.notice === "other" ? `<div class="fg">${this._input(f, "notice_days", "ins_notice_days", "number", 'min="1" max="180"', this._t("unit_days"))}<div></div></div>` : ""}`)}
          ${this._section("mdi:phone", "ins_phones_title", "ins_phones_help",
            `<div class="fg">${this._input(f, "phone_assistance", "ins_phone_assistance", "tel")}${this._input(f, "phone_company", "ins_phone_company", "tel")}</div>`)}`,
        preview: () => {
          const renewal = parseDate(f.renewal_date);
          if (!renewal || !(notice() >= 1)) return null;
          const deadline = addDays(renewal, -notice());
          const left = daysBetween(today(), deadline);
          return {
            icon: "mdi:calendar-alert",
            title: this._t("ins_preview", { date: this._date(isoDate(deadline)) }),
            detail: left < 0 ? this._t("ins_preview_passed", { date: this._date(f.renewal_date) }) : `${this._t("left", { parts: this._days(left) })}. ${this._t("first_notice", { days: first })}`,
          };
        },
        check: () => (parseDate(f.renewal_date) && notice() >= 1 && notice() <= 180 ? "" : this._t("error_required")),
        data: () => ({
          enabled: true,
          renewal_date: f.renewal_date,
          company: f.company,
          policy: f.policy,
          kind: f.kind,
          notice_days: notice(),
          phone_assistance: f.phone_assistance,
          phone_company: f.phone_company,
        }),
      });
    }
  });
