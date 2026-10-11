  // ---------------------------------------------------------------------------
  // Ventana "Apariencia" de un coche: modelo, versión, color y llanta
  // ---------------------------------------------------------------------------
  // Se abre con el botón "Apariencia" de la pestaña Coches. La foto de arriba
  // cambia con lo que se va eligiendo (son las fotos del catálogo); nada se
  // guarda hasta pulsar "Guardar".
  install(class {
    _do_appearance(data) {
      const car = this._car(data.car);
      const models = this._state.models;
      if (!models.length) return;
      const pick = { ...car.appearance };
      if (!models.some((model) => model.id === pick.model)) pick.model = models[0].id;

      /** Lo elegido, sin lo que el modelo no tiene (al cambiar de modelo, por ejemplo). */
      const current = () => {
        const model = models.find((item) => item.id === pick.model);
        if (!model.trims.some((trim) => trim.id === pick.trim)) pick.trim = null;
        if (!model.colors.some((color) => color.id === pick.color)) pick.color = null;
        const trim = model.trims.find((item) => item.id === pick.trim);
        // La llanta solo se elige si el modelo tiene varias y la versión no trae una fija.
        const choosable = model.wheels.length > 1 && !(trim && trim.wheel);
        if (!model.wheels.includes(pick.wheels)) pick.wheels = model.wheels[0] || null;
        return { model, trim, choosable };
      };

      const option = (field, value, name, note, on) =>
        `<button class="opt ${on ? "on" : ""}" data-action="pick" data-field="${field}" data-value="${escapeHtml(value)}" aria-pressed="${on}">${escapeHtml(name)}${note ? `<small>${escapeHtml(note)}</small>` : ""}</button>`;
      const trimNote = (trim) => {
        const parts = [];
        if (trim.equipped === 4) parts.push(this._t("trim_full"));
        if (trim.equipped === 0) parts.push(this._t("trim_basic"));
        if (trim.wheel) parts.push(this._maybe(`wheel_${trim.wheel}`) || trim.wheel);
        return parts.join(" · ");
      };
      const body = () => {
        const { model, choosable } = current();
        const photo = model.photos[`${pick.trim || ""}|${pick.color || ""}`] || model.photos["|"];
        return `<h2>${this._t("appearance_title", { name: escapeHtml(car.name) })}</h2><p>${this._t("appearance_help")}</p>
          ${photo ? `<div class="prev"><img src="${escapeHtml(photo)}" alt=""></div>` : ""}
          ${models.length > 1 ? `<div class="lbl">${this._t("model")}</div><div class="opts">${models.map((item) =>
            option("model", item.id, item.name, this._t(item.fuel ? "model_phev" : "model_ev"), item.id === pick.model)).join("")}</div>` : ""}
          ${model.trims.length ? `<div class="lbl">${this._t("trim")}</div><div class="opts">${model.trims.map((trim) =>
            option("trim", trim.id, trim.name, trimNote(trim), trim.id === pick.trim)).join("")}</div>` : ""}
          ${model.colors.length ? `<div class="lbl">${this._t("color")}</div><div class="sw">${model.colors.map((color) =>
            `<button class="${color.id === pick.color ? "on" : ""}" data-action="pick" data-field="color" data-value="${escapeHtml(color.id)}" aria-pressed="${color.id === pick.color}">
              <i style="background:${escapeHtml(color.swatch || "#9e9e9e")}"></i>${escapeHtml(color.name)}</button>`).join("")}</div>` : ""}
          ${choosable ? `<div class="lbl">${this._t("wheels")}</div><div class="opts">${model.wheels.map((wheel) =>
            option("wheels", wheel, this._maybe(`wheel_${wheel}`) || wheel, "", wheel === pick.wheels)).join("")}</div>` : ""}
          <div class="err"></div>
          <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("save")}</button></div>`;
      };

      const dialog = openDialog(body(), (action, open, target) => {
        if (action === "pick") {
          pick[target.dataset.field] = target.dataset.value;
          open.root.querySelector(".dlg").innerHTML = body();
          return undefined;
        }
        if (action !== "ok") return undefined;
        const { choosable } = current();
        open.close();
        return this._run(
          "set_appearance",
          { vehicle_id: car.id, model: pick.model, trim: pick.trim, color: pick.color, wheels: choosable ? pick.wheels : null },
          this._t("saved")
        );
      });
      dialog.root.querySelector(".dlg").classList.add("wide");
    }
  });
