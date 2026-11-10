  // ---------------------------------------------------------------------------
  // Tarjeta «DEC Deepal · A medida» (custom:dec-deepal-flex-card, 2.6.0b16)
  // ---------------------------------------------------------------------------
  // La misma tarjeta del coche, pero configurable desde el editor visual (sin
  // YAML): estilo, imagen, qué datos se ven, qué botones y en qué orden,
  // columnas, color de acento, nombre e idioma. Hereda de DecDeepalCard: las
  // ventanas (confort, carga, localizar, otros, ITV, seguro...) son las mismas.
  // Las dos tarjetas de siempre no cambian.
  //
  //   type: custom:dec-deepal-flex-card
  //   device_id: <dispositivo del coche>
  //   style: full | compact | mini | data         (de fábrica: full)
  //   image: isometric | side | top | photo | none (de fábrica: según el estilo)
  //   orientation: horizontal | vertical          (con image: top)
  //   charging_view: true    vista de carga mientras la manguera está puesta
  //   studio: true           fondo de estudio en tema oscuro
  //   main_value: range | battery | both
  //   show_status / show_limit / show_updated / show_extra: true | false
  //   buttons: [comfort, lock, trunk, vent, locate, others, climate, seat,
  //             wheel, flash, refresh, charger]   (de fábrica: según el estilo)
  //   columns: 2 | 3 | 4
  //   accent: blue | green | purple | orange | red | grey   (vacío: el del tema)
  //   name: <nombre en la tarjeta>     language: es | en | ...  (vacío: el de HA)
  const FLEX_TAG = "dec-deepal-flex-card";
  const FLEX_STYLES = ["full", "compact", "mini", "data"];
  const FLEX_IMAGES = ["isometric", "side", "top", "photo", "none"];
  // Los seis botones de siempre y seis más, directos (una pulsación, sin ventana).
  const FLEX_STANDARD = ["comfort", "lock", "trunk", "vent", "locate", "others"];
  const FLEX_DIRECT = ["climate", "seat", "wheel", "flash", "refresh", "charger"];
  const FLEX_BUTTONS = [...FLEX_STANDARD, ...FLEX_DIRECT];
  // Lo que pone cada estilo si no se elige otra cosa.
  const FLEX_PRESETS = {
    full: { image: "isometric", buttons: FLEX_STANDARD, columns: 3, show_extra: false },
    compact: { image: "isometric", buttons: ["comfort", "lock", "locate"], columns: 3, show_extra: false },
    mini: { image: "side", buttons: ["lock", "climate"], columns: 4, show_extra: false, show_status: false, show_limit: false, show_updated: false },
    data: { image: "none", buttons: ["comfort", "lock", "trunk"], columns: 3, show_extra: true },
  };
  const FLEX_ACCENTS = { blue: "#03a9f4", green: "#43a047", purple: "#7e57c2", orange: "#ef6c00", red: "#e53935", grey: "#607d8b" };
  // Idiomas de la tarjeta, con su nombre en ese idioma (no se traducen).
  const FLEX_LANGUAGES = {
    es: "Español", en: "English", pt: "Português", it: "Italiano", pl: "Polski", de: "Deutsch",
    fr: "Français", nl: "Nederlands", nb: "Norsk", da: "Dansk", el: "Ελληνικά", sl: "Slovenščina",
  };
  const FLEX_IMAGE_KEYS = { isometric: "image.isometric_view", side: "image.dec_photo", top: "image.top_view", photo: "image.official_image" };
  const FLEX_TIRES = ["front_left", "front_right", "rear_left", "rear_right"].map((position) => `sensor.tire_pressure_${position}`);
  /** Nombre de un botón: los de siempre, con su texto de la tarjeta base; los directos, con el suyo. */
  const flexButtonName = (text, key) => text(FLEX_DIRECT.includes(key) ? `flex_btn_${key}` : key);

  class DecDeepalFlexCard extends DecDeepalCard {
    static get VIEW() {
      return "flex";
    }

    /** Al añadirla desde el selector: lo de fábrica, explícito (así el editor lo enseña). */
    static getStubConfig(hass) {
      return { ...DecDeepalCard.getStubConfig(hass), style: "full", charging_view: true, studio: true, show_status: true, show_limit: true, show_updated: true };
    }

    static getConfigForm() {
      const text = (key, values) => translate(document.documentElement.lang, key, values);
      const select = (name, values, label, mode = "dropdown") => ({
        name,
        selector: { select: { mode, options: values.map((value) => ({ value, label: label(value) })) } },
      });
      const toggle = (name) => ({ name, selector: { boolean: {} } });
      const section = (title, icon, schema) => ({ type: "expandable", name: "", title: text(title), icon, flatten: true, schema });
      const schema = [
        { name: "device_id", selector: { device: { filter: [{ integration: DOMAIN }] } } },
        select("style", FLEX_STYLES, (value) => text(`flex_style_${value}`), "list"),
        section("flex_sec_image", "mdi:image-outline", [
          select("image", FLEX_IMAGES, (value) => text(`flex_image_${value}`)),
          select("orientation", ["horizontal", "vertical"], (value) => text(`orientation_${value}`)),
          toggle("charging_view"),
          toggle("studio"),
        ]),
        section("flex_sec_data", "mdi:battery-high", [
          select("main_value", MAIN_VALUES, (value) => text(`main_value_${value}`), "list"),
          toggle("show_status"),
          toggle("show_limit"),
          toggle("show_updated"),
          toggle("show_extra"),
        ]),
        section("flex_sec_buttons", "mdi:gesture-tap-button", [
          {
            name: "buttons",
            selector: { select: { multiple: true, reorder: true, mode: "list", options: FLEX_BUTTONS.map((value) => ({ value, label: flexButtonName(text, value) })) } },
          },
          select("columns", ["2", "3", "4"], (value) => value, "list"),
        ]),
        section("flex_sec_look", "mdi:palette-outline", [
          select("accent", ["", ...Object.keys(FLEX_ACCENTS)], (value) => text(value ? `flex_accent_${value}` : "flex_accent_theme")),
          { name: "name", selector: { text: {} } },
          select("language", ["", ...Object.keys(FLEX_LANGUAGES)], (value) => (value ? FLEX_LANGUAGES[value] : text("flex_language_auto"))),
        ]),
      ];
      const labels = {
        device_id: "car", style: "flex_style", image: "flex_image", orientation: "orientation", charging_view: "flex_charging_view",
        studio: "flex_studio", main_value: "main_value", show_status: "flex_show_status", show_limit: "flex_show_limit",
        show_updated: "flex_show_updated", show_extra: "flex_show_extra", buttons: "flex_buttons", columns: "flex_columns",
        accent: "flex_accent", name: "flex_name", language: "flex_language",
      };
      const helpers = {
        charging_view: "flex_charging_view_help", studio: "flex_studio_help", show_extra: "flex_show_extra_help",
        buttons: "flex_buttons_help", name: "flex_name_help", image: "flex_image_help",
      };
      return {
        schema,
        computeLabel: (field) => text(labels[field.name] || "car"),
        computeHelper: (field) => (helpers[field.name] ? text(helpers[field.name]) : undefined),
      };
    }

    // --- Configuración efectiva (lo elegido o, si no, lo del estilo) ------------

    _style() {
      return FLEX_STYLES.includes(this._config.style) ? this._config.style : "full";
    }

    _opt(name, fallback) {
      const value = this._config[name];
      if (value !== undefined && value !== null && value !== "") return value;
      const preset = FLEX_PRESETS[this._style()];
      return name in preset ? preset[name] : fallback;
    }

    _buttons() {
      const chosen = Array.isArray(this._config.buttons) && this._config.buttons.length ? this._config.buttons : FLEX_PRESETS[this._style()].buttons;
      return chosen.filter((key, index) => FLEX_BUTTONS.includes(key) && chosen.indexOf(key) === index).filter((key) => this._hasButton(key));
    }

    /** ¿Tiene el coche lo que necesita ese botón? (p. ej. el Pro no tiene asientos calefactados). */
    _hasButton(key) {
      const needs = { climate: "climate.cabin_climate", seat: "number.seat_heat_driver", wheel: "switch.steering_wheel_heat", flash: "button.flash_lights", refresh: "button.refresh" }[key];
      return !needs || !this._ids || !Object.keys(this._ids).length || Boolean(this._ids[needs]);
    }

    _columns() {
      const value = Number(this._opt("columns", 3));
      return [2, 3, 4].includes(value) ? value : 3;
    }

    _vertical() {
      return this._opt("image", "isometric") === "top" && this._config.orientation === "vertical";
    }

    _language() {
      return FLEX_LANGUAGES[this._config.language] ? this._config.language : super._language();
    }

    _name() {
      return (this._config.name || "").trim() || super._name();
    }

    getCardSize() {
      return { full: 8, compact: 5, mini: 2, data: 5 }[this._style()];
    }

    getGridOptions() {
      return this._style() === "mini" ? { columns: 12, min_columns: 6, rows: 2, min_rows: 2 } : { columns: 12, min_columns: 6, min_rows: 4 };
    }

    // --- Pintado --------------------------------------------------------------

    _build() {
      // La estructura de la tarjeta de siempre (la pinta su _paint) y, encima,
      // lo de esta: estilo, columnas, datos extra y botones elegidos.
      super._build();
      const card = this.shadowRoot.querySelector("ha-card");
      card.classList.add("flex", `st-${this._style()}`);
      // Todo dentro de un contenedor propio: la rejilla de los estilos va en él
      // (el estilo de ha-card lo pone Home Assistant).
      const box = document.createElement("div");
      box.className = "fx";
      box.append(...card.childNodes);
      card.append(box);
      this._flexKey = this._configKey();
      const accent = FLEX_ACCENTS[this._config.accent];
      // En el propio elemento (no en ha-card, cuyo estilo pone Home Assistant): lo heredan los de dentro.
      if (accent) this.style.setProperty("--dec-accent", `var(--${this._config.accent}-color, ${accent})`);
      else this.style.removeProperty("--dec-accent");
      card.classList.toggle("accent", Boolean(accent));
      const extra = document.createElement("div");
      extra.className = "extra";
      extra.innerHTML = ["inside", "odometer", "tires"].map((key) => `<div data-x="${key}"><span>${this._t(`flex_extra_${key}`)}</span><b>—</b></div>`).join("");
      this.shadowRoot.querySelector(".energy").after(extra);
      const tiles = this.shadowRoot.querySelector(".tiles");
      tiles.className = `tiles c${this._columns()}`;
      tiles.innerHTML = this._buttons()
        .map((key) => `<button class="tile${FLEX_DIRECT.includes(key) ? " dir" : ""}" data-action="${key}" aria-label="${escapeHtml(flexButtonName((k) => this._t(k), key))}"><ha-icon></ha-icon><b>${escapeHtml(flexButtonName((k) => this._t(k), key))}</b><small></small></button>`)
        .join("");
      this.shadowRoot.querySelector("style").textContent += FLEX_CSS;
    }

    /** Si cambia la configuración, se vuelve a construir (el editor la cambia en vivo). */
    _configKey() {
      return JSON.stringify([this._config, this._buttons()]);
    }

    _update() {
      if (this._built && this._flexKey !== this._configKey()) this._built = false;
      super._update();
    }

    _paint() {
      super._paint();
      const $ = (selector) => this.shadowRoot.querySelector(selector);
      const card = $("ha-card");
      const show = (name) => this._opt(name, true) !== false;
      $(".upd").hidden = !show("show_updated");
      $(".status").hidden = !show("show_status");
      if (!show("show_limit")) {
        $(".limits").hidden = true;
        $(".lhint").hidden = true;
        $(".bar .tgt").hidden = true;
      }
      $(".extra").hidden = !show("show_extra");
      if (show("show_extra")) this._paintExtra($);
      this._paintImage($);
      // Con color de acento, la barra lo lleva (salvo la batería baja, que avisa en ámbar o rojo).
      const level = this._number("sensor.battery_level");
      if (card.classList.contains("accent") && (level === undefined || level >= 50)) $(".bar i").style.background = "var(--dec-accent)";
    }

    /** La imagen elegida; con la manguera puesta, la vista de carga (si se quiere). */
    _paintImage($) {
      const box = $(".carbox");
      const img = $(".car");
      const choice = this._opt("image", "isometric");
      const estimate = this._estimate();
      const plugged = estimate ? estimate.state !== "unplugged" : (this._value("sensor.charge_status") || "disconnected") !== "disconnected";
      let key = FLEX_IMAGE_KEYS[choice];
      let charging = false;
      if (choice !== "none" && this._opt("charging_view", true) !== false && plugged && this._state("image.charging_view")) {
        key = "image.charging_view";
        charging = true;
      }
      const state = key ? this._state(key) || (choice === "photo" ? this._state("image.dec_photo") : undefined) : undefined;
      const src = this._imageUrl(state);
      box.hidden = !src;
      box.classList.toggle("plain", ["side", "photo"].includes(choice) && !charging);
      box.classList.toggle("top", choice === "top" && !charging);
      box.classList.toggle("vertical", choice === "top" && !charging && this._vertical());
      box.classList.toggle("charging", charging);
      box.classList.toggle("nostudio", this._opt("studio", true) === false);
      if (src && img.getAttribute("src") !== src) img.setAttribute("src", src);
    }

    /** Datos extra: temperatura interior, kilómetros totales y la presión más baja de las ruedas. */
    _paintExtra($) {
      const set = (key, value) => {
        $(`.extra [data-x="${key}"] b`).textContent = value || "—";
      };
      set("inside", this._format("sensor.inside_temperature"));
      const odometer = this._number("sensor.odometer");
      set("odometer", odometer === undefined ? "" : `${this._thousands(Math.round(odometer))} km`);
      const tires = FLEX_TIRES.map((key) => ({ key, value: this._number(key) })).filter((item) => item.value !== undefined);
      if (!tires.length) set("tires", "");
      else {
        const lowest = tires.reduce((a, b) => (b.value < a.value ? b : a));
        const unit = this._state(lowest.key).attributes.unit_of_measurement || "";
        set("tires", `${lowest.value.toLocaleString(this._language(), { maximumFractionDigits: 1 })} ${unit}`.trim());
      }
    }

    /** Los botones elegidos: los de siempre (de la tarjeta base) y los directos. */
    _tiles() {
      const base = super._tiles();
      const chosen = this._buttons();
      const result = {};
      for (const key of chosen) result[key] = base[key] || this._directTile(key);
      return result;
    }

    _directTile(key) {
      if (key === "climate") {
        const climate = this._state("climate.cabin_climate");
        const on = (this._value("climate.cabin_climate") || "off") !== "off";
        const target = climate && climate.attributes.temperature;
        return { icon: "mdi:fan", text: on ? `${this._t("on")}${target != null ? ` · ${this._temp(target)} °C` : ""}` : this._t("off"), primary: on };
      }
      if (key === "seat") {
        const level = this._number("number.seat_heat_driver") || 0;
        return { icon: "mdi:car-seat-heater", text: level ? this._t("flex_seat_level", { level }) : this._t("off"), primary: level > 0 };
      }
      if (key === "wheel") {
        const on = this._value("switch.steering_wheel_heat") === "on";
        return { icon: "mdi:steering", text: this._t(on ? "on" : "off"), primary: on };
      }
      if (key === "flash") return { icon: "mdi:car-light-high", text: this._t("flash") };
      if (key === "refresh") return { icon: "mdi:refresh", text: this._updatedText() };
      if (key === "charger") {
        const station = this._station();
        return { icon: "mdi:ev-station", text: station ? station.name : "—", primary: Boolean(station && station.charging) };
      }
      return { icon: "mdi:help", text: "" };
    }

    _onClick(event) {
      const target = event.composedPath().find((node) => node.dataset && node.dataset.action);
      if (target && this._hass && FLEX_DIRECT.includes(target.dataset.action)) {
        this._direct(target.dataset.action);
        return;
      }
      super._onClick(event);
    }

    /** Botones directos: una pulsación, sin ventana (y un aviso breve de que se mandó). */
    async _direct(key) {
      let done = false;
      if (key === "climate") {
        const on = (this._value("climate.cabin_climate") || "off") !== "off";
        done = await this._call(key, "climate", on ? "turn_off" : "turn_on", "climate.cabin_climate");
      } else if (key === "seat") {
        done = await this._call(key, "number", "set_value", "number.seat_heat_driver", { value: ((this._number("number.seat_heat_driver") || 0) + 1) % 4 });
      } else if (key === "wheel") {
        done = await this._call(key, "switch", "toggle", "switch.steering_wheel_heat");
      } else if (key === "flash") {
        done = await this._call(key, "button", "press", "button.flash_lights");
      } else if (key === "refresh") {
        done = await this._call(key, "button", "press", "button.refresh");
      } else if (key === "charger") {
        this._openCharge();
        return;
      }
      if (done) this._toast(this._t("flex_sent", { name: this._t(`flex_btn_${key}`) }));
    }
  }
