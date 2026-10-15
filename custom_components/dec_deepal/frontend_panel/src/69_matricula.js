  // ---------------------------------------------------------------------------
  // Placa de matrícula (pestañas "Coches" y "Avisos")
  // ---------------------------------------------------------------------------
  // Placa genérica europea: franja azul con las estrellas y la letra del país
  // de la cuenta, y la matrícula con el formato de ese país (lo pone
  // plates.py: "parts" trae el texto; con dos partes, Alemania, entre ellas
  // van los dos sellos). Sin matrícula, no se pinta nada.
  install(class {
    _plateTag(car) {
      const plate = car.plate;
      if (!plate || !plate.parts || !plate.parts.length) return "";
      const seals = `<span class="seals" aria-hidden="true"><i></i><i></i></span>`;
      const text = plate.parts.map((part) => escapeHtml(part)).join(seals);
      const label = `${this._t("plate")} ${plate.parts.join(" ")}`;
      return `<span class="plate" role="img" aria-label="${escapeHtml(label)}">
        <span class="eu">${PLATE_STARS}<span>${escapeHtml(plate.code)}</span></span><span class="num">${text}</span></span>`;
    }
  });
