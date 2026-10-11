  // ---------------------------------------------------------------------------
  // Pestaña "Coches"
  // ---------------------------------------------------------------------------
  install(class {
    _view_cars() {
      return this._state.cars.map((car) => this._carCard(car)).join("");
    }

    _carCard(car) {
      const photo = this._photo(car);
      const sheet = car.sheet || {};
      const features = sheet.funciones || {};
      const chips = car.configured
        ? FEATURES.filter(([key]) => features[key]).map(([, icon, text]) => `<span class="chip"><ha-icon icon="${icon}"></ha-icon>${this._t(text)}</span>`)
        : [];
      if (car.wheel) chips.push(`<span class="chip"><ha-icon icon="mdi:tire"></ha-icon>${this._maybe(`wheel_${car.wheel}`) || escapeHtml(car.wheel)}</span>`);
      const badge = !car.configured
        ? `<span class="badge warn"><ha-icon icon="mdi:alert-circle-outline"></ha-icon>${this._t("not_configured")}</span>`
        : sheet.verificada
          ? `<span class="badge ok"><ha-icon icon="mdi:check-decagram"></ha-icon>${this._t("sheet_verified")}</span>`
          : `<span class="badge info"><ha-icon icon="mdi:book-open-variant"></ha-icon>${this._t("sheet_catalogue")}</span>`;
      const fact = (value, label) => `<div><b>${value}</b>${this._t(label)}</div>`;
      return `<div class="card">
        <div class="hero">
          ${photo ? `<img src="${escapeHtml(photo)}" alt="">` : ""}
          <div class="who">
            <div class="n">${escapeHtml(car.name)}</div>
            <div class="m">${escapeHtml([car.model, car.color].filter(Boolean).join(" · "))}</div>
            ${badge}
            <div class="kv">
              ${car.battery == null ? "" : fact(`${this._number(car.battery)} %`, "battery")}
              ${car.range == null ? "" : fact(`${this._number(Math.round(car.range))} km`, "range")}
              ${car.odometer == null ? "" : fact(`${this._number(Math.round(car.odometer))} km`, "odometer")}
            </div>
          </div>
          <button class="btn o" data-action="appearance" data-car="${escapeHtml(car.id)}"><ha-icon icon="mdi:pencil"></ha-icon>${this._t("appearance")}</button>
        </div>
        ${chips.length ? `<div class="chips">${chips.join("")}</div>` : ""}
        <div class="grid3">
          ${this._maintenanceTile(car)}
          ${car.itv_available ? this._itvTile(car) : ""}
          ${this._insuranceTile(car)}
        </div>
      </div>`;
    }

    /** Recuadro con engranaje; `body` va vacío si el apartado está sin configurar. */
    _tile(car, kind, icon, level, body) {
      const gear = `<button class="gear" data-action="gear" data-kind="${kind}" data-car="${escapeHtml(car.id)}" aria-label="${this._t("configure")}"><ha-icon icon="mdi:cog"></ha-icon></button>`;
      const head = `<div class="h"><ha-icon icon="${icon}"></ha-icon><span>${this._t(`section_${kind}`)}</span>${gear}</div>`;
      if (!body) {
        return `<div class="tile off">${head}<div class="v">${this._t("not_set")}</div>
          <button class="link" data-action="gear" data-kind="${kind}" data-car="${escapeHtml(car.id)}">${this._t(`add_${kind}`)}</button></div>`;
      }
      return `<div class="tile ${level}">${head}${body}</div>`;
    }

    _meter(fraction) {
      return `<div class="meter"><i style="width:${Math.round(Math.max(0, Math.min(1, fraction)) * 100)}%"></i></div>`;
    }

    _maintenanceTile(car) {
      const data = car.maintenance;
      if (!data) return this._tile(car, "maintenance", "mdi:wrench", "", "");
      const left = [];
      if (data.days_left >= 0) left.push(this._days(data.days_left));
      if (data.km_left != null && data.km_left >= 0) left.push(`${this._number(data.km_left)} km`);
      const overdue = data.level === "overdue";
      // Lo recorrido del intervalo: lo que más avance, tiempo o kilómetros.
      const months = data.record.interval_months * 30.4;
      const byDays = 1 - data.days_left / months;
      const byKm = data.km_left == null ? 0 : 1 - data.km_left / data.record.interval_km;
      return this._tile(car, "maintenance", "mdi:wrench", data.level,
        `<div class="v">${this._t("service_number", { number: data.number })}</div>
         <div class="d">${overdue ? this._t("overdue") : this._t("left", { parts: left.join(this._t("or")) })}</div>
         ${this._meter(Math.max(byDays, byKm))}`);
    }

    _itvTile(car) {
      const data = car.itv;
      if (!data) return this._tile(car, "itv", "mdi:clipboard-check-outline", "", "");
      const overdue = data.days_left < 0;
      return this._tile(car, "itv", "mdi:clipboard-check-outline", data.level,
        `<div class="v">${this._date(data.due_date)}</div>
         <div class="d">${overdue ? this._t("overdue_since", { days: this._days(data.days_left) }) : this._t("left", { parts: this._days(data.days_left) })}</div>
         ${this._meter(1 - data.days_left / 730)}`);
    }

    _insuranceTile(car) {
      const data = car.insurance;
      if (!data) return this._tile(car, "insurance", "mdi:shield-car", "", "");
      const detail = data.days_to_cancel >= 0
        ? this._t("cancel_until", { date: this._date(data.cancel_deadline) })
        : this._t("renews_in", { days: this._days(data.days_to_renewal) });
      return this._tile(car, "insurance", "mdi:shield-car", data.level,
        `<div class="v">${this._date(data.record.renewal_date)}</div>
         <div class="d">${escapeHtml(detail)}</div>
         ${this._meter(1 - data.days_to_renewal / 365)}`);
    }
  });
