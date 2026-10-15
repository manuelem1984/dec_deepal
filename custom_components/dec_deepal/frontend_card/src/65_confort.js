  // ---------------------------------------------------------------------------
  // Ventana de Confort
  // ---------------------------------------------------------------------------
  install(class {
    _spotLevel(spot) {
      if (spot.key.startsWith("switch.")) return this._value(spot.key) === "on" ? 1 : 0;
      return this._number(spot.key) || 0;
    }

    _openComfort() {
      if (this._comfort) return;
      const spots = HOTSPOTS.filter((spot) => this._ids[spot.key])
        .map(
          (spot) =>
            `<button class="hot" data-action="spot" data-key="${spot.key}" aria-label="${escapeHtml(this._t(spot.label))}"
               style="left:${spot.x}%;top:${spot.y}%"><ha-icon icon="${spot.icon}"></ha-icon><u></u></button>`
        )
        .join("");
      const html = `
        <div class="head"><button class="icon-btn" data-action="close" aria-label="${this._t("close")}"><ha-icon icon="mdi:close"></ha-icon></button><h2>${this._t("comfort")}</h2></div>
        <div class="stage"><img alt="">${spots}</div>
        <div class="temp">
          <button class="round" data-action="temp" data-step="-0.5" aria-label="${this._t("temp_down")}"><ha-icon icon="mdi:minus"></ha-icon></button>
          <b><span class="target"></span><sup> °C</sup></b>
          <button class="round" data-action="temp" data-step="0.5" aria-label="${this._t("temp_up")}"><ha-icon icon="mdi:plus"></ha-icon></button>
        </div>
        <button class="power" data-action="power"><ha-icon icon="mdi:power"></ha-icon><span></span></button>
        <p class="info"></p>`;
      this._comfort = openDialog(html, (action, target) => this._onComfort(action, target));
      this._comfort.onClose = () => {
        this._comfort = null;
      };
      this._paintComfort();
    }

    _paintComfort() {
      const root = this._comfort.root;
      const image = this._state("image.interior_view");
      const img = root.querySelector(".stage img");
      const src = this._imageUrl(image);
      if (src && img.getAttribute("src") !== src) img.setAttribute("src", src);

      for (const element of root.querySelectorAll(".hot")) {
        const spot = HOTSPOTS.find((item) => item.key === element.dataset.key);
        const level = this._spotLevel(spot);
        element.classList.toggle("on", level > 0);
        element.classList.toggle("busy", this._busy.has(spot.key));
        element.querySelector("u").textContent = spot.key.startsWith("number.") && level > 0 ? String(level) : "";
      }

      const climate = this._state("climate.cabin_climate");
      const climateOn = (this._value("climate.cabin_climate") || "off") !== "off";
      const target = this._pendingTemp != null ? this._pendingTemp : climate && climate.attributes.temperature;
      root.querySelector(".target").textContent = target != null ? this._temp(target) : "—";
      root.querySelector(".temp").hidden = !climate;
      const power = root.querySelector(".power");
      power.hidden = !climate;
      power.classList.toggle("on", climateOn);
      power.classList.toggle("busy", this._busy.has("power"));
      power.querySelector("span").textContent = this._t(climateOn ? "climate_on" : "climate_off");

      const parts = [];
      const inside = this._format("sensor.inside_temperature");
      const humidity = this._format("sensor.cabin_humidity");
      const fan = this._value("sensor.fan_level");
      const recirculation = this._value("binary_sensor.air_recirculation");
      if (inside) parts.push(this._t("inside", { value: inside }));
      if (humidity) parts.push(this._t("humidity", { value: humidity }));
      if (climateOn && fan) parts.push(this._t("fan", { value: fan }));
      if (climateOn && recirculation) parts.push(this._t(recirculation === "on" ? "recirculating" : "outside_air"));
      root.querySelector(".info").textContent = parts.join(" · ");
    }

    _onComfort(action, target) {
      if (action === "spot") {
        const key = target.dataset.key;
        if (key.startsWith("switch.")) this._call(key, "switch", "toggle", key);
        else this._call(key, "number", "set_value", key, { value: ((this._number(key) || 0) + 1) % 4 });
      } else if (action === "power") {
        const climateOn = (this._value("climate.cabin_climate") || "off") !== "off";
        this._call("power", "climate", climateOn ? "turn_off" : "turn_on", "climate.cabin_climate");
      } else if (action === "temp") {
        const climate = this._state("climate.cabin_climate");
        if (!climate) return;
        const current = this._pendingTemp != null ? this._pendingTemp : Number(climate.attributes.temperature);
        if (!Number.isFinite(current)) return;
        const min = Number(climate.attributes.min_temp) || 18;
        const max = Number(climate.attributes.max_temp) || 32;
        this._pendingTemp = Math.max(min, Math.min(max, current + Number(target.dataset.step)));
        this._paintComfort();
        // Se espera a que el usuario termine de pulsar antes de enviar la orden.
        clearTimeout(this._tempTimer);
        this._tempTimer = setTimeout(async () => {
          const temperature = this._pendingTemp;
          await this._call("temp", "climate", "set_temperature", "climate.cabin_climate", { temperature });
          if (this._pendingTemp === temperature) this._pendingTemp = null;
          if (this._comfort) this._paintComfort();
        }, 900);
      }
    }
  });
