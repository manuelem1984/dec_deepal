// =============================================================================
// DEC Deepal — Cargador temprano de los iconos "dec:"
// =============================================================================
//
// NO EDITAR ni borrar: la integración lo sirve desde su propia ruta
// (/dec_deepal/frontend/dec-icons-loader.js) y lo registra como recurso de los
// paneles (Ajustes → Paneles → Recursos). Si se desinstala DEC Deepal, el
// recurso se quita solo.
//
// Para qué sirve
// --------------
// Tras reiniciar Home Assistant, la app vuelve a cargar la página ANTES de que
// la integración termine de arrancar. En ese momento Home Assistant todavía no
// sabe que existe el script de iconos (dec-icons.js), así que la página se
// queda sin él y los iconos "dec:" no se ven hasta recargar.
//
// Los recursos de los paneles se cargan con cada panel. Este cargador solo hace
// una cosa: intentar cargar el script de verdad hasta que la integración lo
// publica.
//
// Su contenido no cambia entre versiones (toda la lógica está en
// dec-icons.js), así que el recurso se registra una sola vez.
// =============================================================================

(() => {
  if (window.__decDeepalIconsLoader) return;
  window.__decDeepalIconsLoader = true;

  const SCRIPT_URL = "/dec_deepal/frontend/dec-icons.js";
  // Esperas entre intentos (segundos): unos 2 minutos en total.
  const DELAYS = [0, 1, 1, 2, 2, 3, 5, 5, 5, 10, 10, 10, 15, 15, 30];

  const sleep = (seconds) => new Promise((resolve) => setTimeout(resolve, seconds * 1000));
  const ready = () => Boolean(window.__decDeepalIcons);

  (async () => {
    for (const delay of DELAYS) {
      if (ready()) return;
      if (delay) await sleep(delay);
      if (ready()) return;
      try {
        // El parámetro cambia en cada intento: el navegador recuerda los
        // "import" fallidos de una misma dirección.
        await import(`${SCRIPT_URL}?loader=${Date.now()}`);
        return;
      } catch (error) {
        // La integración aún no ha arrancado: se reintenta.
      }
    }
  })();
})();
