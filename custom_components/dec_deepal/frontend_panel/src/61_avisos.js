  // ---------------------------------------------------------------------------
  // Pestaña "Avisos": una tabla por coche, con sus apartados plegables
  // ---------------------------------------------------------------------------
  // Lo que se toca se guarda en un borrador del coche (this._drafts) hasta que
  // se pulsa "Guardar": guardar recarga la integración, y no conviene hacerlo
  // con cada casilla.
  install(class {
    _view_alerts() {
      return this._state.cars.map((car) => this._alertsCard(car)).join("");
    }

    /** Avisos de un coche tal como se ven ahora: el borrador o lo guardado. */
    _alerts(car) {
      return this._drafts[car.id] || car.alerts;
    }

    /** Borrador del coche (se crea, copiando lo guardado, la primera vez). */
    _draft(car) {
      if (!this._drafts[car.id]) this._drafts[car.id] = JSON.parse(JSON.stringify(car.alerts));
      return this._drafts[car.id];
    }

    _threshold(car, notice) {
      const changed = this._alerts(car).thresholds[notice.id];
      return changed == null ? notice.threshold : changed;
    }

    /** Avisos de un apartado para un coche (la ITV solo donde existe). */
    _notices(car, section) {
      if (section === "itv" && !car.itv_available) return [];
      return this._state.notices.filter((notice) => notice.section === section);
    }

    _when(car, notice) {
      if (notice.threshold == null) return this._maybe(`when_${notice.id}`) || "";
      const value = this._number(this._threshold(car, notice));
      if (notice.unit === "km") return this._t("when_km", { value });
      return this._t(notice.id.startsWith("insurance_c") ? "when_days_deadline" : "when_days", { value });
    }

    _alertsCard(car) {
      const targets = this._state.targets;
      const alerts = this._alerts(car);
      const photo = this._photo(car);
      const admin = this._admin();
      const box = (state, action, extra) => {
        const icon = `<ha-icon icon="mdi:${state === "y" ? "checkbox-marked" : state === "some" ? "minus-box" : "checkbox-blank-outline"}"></ha-icon>`;
        // En solo lectura se ve lo marcado, pero no se puede tocar.
        if (!admin) return `<td><span class="box ${state} ro" role="checkbox" aria-checked="${state === "y"}" aria-readonly="true">${icon}</span></td>`;
        return `<td><button class="box ${state}" data-action="${action}" data-car="${escapeHtml(car.id)}" ${extra} aria-pressed="${state === "y"}">${icon}</button></td>`;
      };
      const rows = [];
      for (const [section, icon] of SECTIONS) {
        // El apartado "Cargador" solo con los cargadores activados (Ajustes).
        if (section === "charger" && !this._state.chargers_enabled) continue;
        const notices = this._notices(car, section);
        if (!notices.length) continue;
        const open = this._open.has(`${car.id}/${section}`);
        const configured = !["maintenance", "itv", "insurance"].includes(section) || car[section];
        const note = configured ? (open ? "" : this._t("n_notices", { count: notices.length })) : this._t("not_set");
        rows.push(`<tr class="grp"><td><button class="fold" data-action="fold" data-car="${escapeHtml(car.id)}" data-section="${section}" aria-expanded="${open}">
            <ha-icon icon="mdi:chevron-${open ? "down" : "right"}"></ha-icon><ha-icon class="sic" icon="${icon}"></ha-icon>${this._t(`section_${section}`)}<small>${note}</small></button></td>
          ${targets.map((target) => {
            const count = notices.filter((notice) => (alerts.notices[notice.id] || []).includes(target.id)).length;
            const state = count === notices.length ? "y" : count ? "some" : "";
            return box(state, "section-cell", `data-section="${section}" data-target="${escapeHtml(target.id)}"`);
          }).join("")}</tr>`);
        if (!open) continue;
        for (const notice of notices) {
          const editing = this._editing && this._editing.car === car.id && this._editing.notice === notice.id;
          const pen = notice.threshold == null || !admin
            ? ""
            : `<button class="pen" data-action="edit" data-car="${escapeHtml(car.id)}" data-notice="${notice.id}" aria-label="${this._t("edit_threshold")}"><ha-icon icon="mdi:pencil"></ha-icon></button>`;
          const label = editing
            ? `<div class="lab"><b>${this._t(`notice_${notice.id}`)}</b><small></small>
                <span class="inp"><input type="number" min="${notice.limits[0]}" max="${notice.limits[1]}" value="${this._threshold(car, notice)}"><span>${this._t(notice.unit === "km" ? "unit_km" : "unit_days")}</span></span>
                <button class="mini ok" data-action="edit-ok" aria-label="${this._t("accept")}"><ha-icon icon="mdi:check"></ha-icon></button>
                <button class="mini" data-action="edit-cancel" aria-label="${this._t("cancel")}"><ha-icon icon="mdi:close"></ha-icon></button></div>`
            : `<div class="lab"><b>${this._t(`notice_${notice.id}`)}</b><small>${escapeHtml(this._when(car, notice))}</small>${pen}</div>`;
          rows.push(`<tr class="it ${editing ? "ed" : ""}"><td>${label}</td>
            ${targets.map((target) => box((alerts.notices[notice.id] || []).includes(target.id) ? "y" : "", "cell",
              `data-notice="${notice.id}" data-target="${escapeHtml(target.id)}"`)).join("")}</tr>`);
        }
      }
      const dirty = Boolean(this._drafts[car.id]);
      const changedThresholds = Object.keys(alerts.thresholds).length > 0;
      const others = admin && this._state.cars.length > 1;
      return `<div class="card" data-car-card="${escapeHtml(car.id)}">
        <div class="chead">
          ${photo ? `<img src="${escapeHtml(photo)}" alt="">` : ""}
          <div class="n"><span class="nm">${escapeHtml(car.name)}${this._plateTag(car)}</span><small>${escapeHtml(car.model)}</small></div>
          ${others ? `<button class="btn o" data-action="copy-alerts" data-car="${escapeHtml(car.id)}"><ha-icon icon="mdi:content-copy"></ha-icon>${this._t("copy_from")}</button>` : ""}
        </div>
        <div class="wide"><table>
          <tr><th>${this._t("notify_to")}</th>${targets.map((target) =>
            `<th><div class="dev ${target.kind}"><u><ha-icon icon="${TARGET_ICONS[target.kind] || TARGET_ICONS.service}"></ha-icon></u>${escapeHtml(target.name)}</div></th>`).join("")}</tr>
          ${rows.join("")}
        </table></div>
        ${!admin ? "" : `<div class="foot ${dirty ? "dirty" : ""}">
          <span>${dirty ? this._t("unsaved") : this._t("alerts_help")}</span>
          ${changedThresholds ? `<button class="btn o" data-action="reset-thresholds" data-car="${escapeHtml(car.id)}"><ha-icon icon="mdi:restore"></ha-icon>${this._t("factory_thresholds")}</button>` : ""}
          ${dirty ? `<button class="btn o" data-action="discard-alerts" data-car="${escapeHtml(car.id)}">${this._t("discard")}</button>
                     <button class="btn" data-action="save-alerts" data-car="${escapeHtml(car.id)}">${this._t("save")}</button>` : ""}
        </div>`}
      </div>`;
    }

    _do_fold(data) {
      const key = `${data.car}/${data.section}`;
      if (!this._open.delete(key)) this._open.add(key);
      this._editing = null;
      this._render();
    }

    _toggle(list, target, on) {
      const without = (list || []).filter((item) => item !== target);
      return on ? [...without, target] : without;
    }

    _do_cell(data) {
      const draft = this._draft(this._car(data.car));
      const on = !(draft.notices[data.notice] || []).includes(data.target);
      draft.notices[data.notice] = this._toggle(draft.notices[data.notice], data.target, on);
      this._render();
    }

    /** Casilla del apartado: marca todos sus avisos (o los desmarca si ya lo estaban todos). */
    _do_section_cell(data) {
      const car = this._car(data.car);
      const draft = this._draft(car);
      const notices = this._notices(car, data.section);
      const all = notices.every((notice) => (draft.notices[notice.id] || []).includes(data.target));
      for (const notice of notices) draft.notices[notice.id] = this._toggle(draft.notices[notice.id], data.target, !all);
      this._render();
    }

    _do_edit(data) {
      this._editing = { car: data.car, notice: data.notice };
      this._render();
    }

    _do_edit_cancel() {
      this._editing = null;
      this._render();
    }

    _do_edit_ok() {
      const { car: carId, notice: noticeId } = this._editing;
      const car = this._car(carId);
      const notice = this._state.notices.find((item) => item.id === noticeId);
      const value = Math.round(Number(this.shadowRoot.querySelector(".inp input").value));
      const [low, high] = notice.limits;
      if (!Number.isFinite(value) || value < low || value > high) {
        this._toast(this._t("error_threshold_range_limits", { low: this._number(low), high: this._number(high) }));
        return;
      }
      const draft = this._draft(car);
      if (value === notice.threshold) delete draft.thresholds[noticeId];
      else draft.thresholds[noticeId] = value;
      this._editing = null;
      this._render();
    }

    _do_reset_thresholds(data) {
      this._draft(this._car(data.car)).thresholds = {};
      this._render();
    }

    _do_discard_alerts(data) {
      delete this._drafts[data.car];
      this._editing = null;
      this._render();
    }

    async _do_save_alerts(data) {
      const draft = this._drafts[data.car];
      if (!draft) return;
      const done = await this._run("set_alerts", { vehicle_id: data.car, notices: draft.notices, thresholds: draft.thresholds }, this._t("saved"));
      if (done) {
        delete this._drafts[data.car];
        this._render();
      }
    }

    /** Copia los avisos y los plazos de otro coche al borrador de este (falta guardar). */
    _do_copy_alerts(data) {
      const others = this._state.cars.filter((car) => car.id !== data.car);
      const copy = (fromId) => {
        const from = this._car(fromId);
        const mine = this._car(data.car);
        const source = JSON.parse(JSON.stringify(this._alerts(from)));
        // La ITV no se copia a un coche que no la tiene.
        if (!mine.itv_available) for (const notice of this._state.notices) if (notice.section === "itv") source.notices[notice.id] = [];
        this._drafts[data.car] = source;
        this._render();
      };
      if (others.length === 1) return copy(others[0].id);
      const options = others.map((car) => `<option value="${escapeHtml(car.id)}">${escapeHtml(car.name)}</option>`).join("");
      openDialog(
        `<h2>${this._t("copy_from")}</h2><label>${this._t("car")}<select name="from">${options}</select></label>
         <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("copy")}</button></div>`,
        (action, dialog) => {
          if (action !== "ok") return;
          copy(dialog.values().from);
          dialog.close();
        }
      );
      return undefined;
    }
  });
