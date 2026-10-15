  // ---------------------------------------------------------------------------
  // Personas de cada coche: a quién pertenece (pestaña "Coches")
  // ---------------------------------------------------------------------------
  // Las personas son las de Home Assistant (Ajustes → Personas). De momento
  // solo se enseña de quién es cada coche ("Tuyo" si es de quien mira); más
  // adelante servirá para decidir quién puede hacer qué con él.
  install(class {
    /** Fila "Personas" de la tarjeta del coche (con su botón, si se puede cambiar). */
    _peopleRow(car) {
      const people = car.people || [];
      const names = people.length
        ? people.map((person) => `<span class="chip"><ha-icon icon="mdi:account"></ha-icon>${escapeHtml(person.name)}</span>`).join("")
        : `<span class="none">${this._t("people_none")}</span>`;
      const edit = this._admin() && (this._state.people || []).length
        ? `<button class="link" data-action="people" data-car="${escapeHtml(car.id)}">${this._t("people_edit")}</button>`
        : "";
      return `<div class="people"><span class="lbl"><ha-icon icon="mdi:account-multiple"></ha-icon>${this._t("people")}</span>${names}${edit}</div>`;
    }

    /** Ventana para elegir las personas de un coche. */
    _do_people(data) {
      const car = this._car(data.car);
      const chosen = new Set((car.people || []).map((person) => person.id));
      const boxes = (this._state.people || []).map((person) =>
        `<label class="check"><input type="checkbox" name="${escapeHtml(person.id)}" ${chosen.has(person.id) ? "checked" : ""}>${escapeHtml(person.name)}</label>`).join("");
      openDialog(
        `<h2>${this._t("people_title", { name: escapeHtml(car.name) })}</h2><p>${this._t("people_help")}</p>
         ${boxes}
         <div class="err"></div>
         <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("save")}</button></div>`,
        (action, dialog) => {
          if (action !== "ok") return undefined;
          const people = Object.entries(dialog.values()).filter(([, on]) => on).map(([id]) => id);
          dialog.close();
          return this._run("set_people", { vehicle_id: car.id, people }, this._t("saved"));
        }
      );
    }
  });
