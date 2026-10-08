// =============================================================================
// DEC Deepal — Paquete de iconos "dec:" para el navegador
// =============================================================================
//
// Este script lo carga Home Assistant automáticamente en el navegador (lo
// registra frontend.py). Enseña al frontend a entender iconos "dec:<nombre>".
//
// Cómo consigue los dibujos (desde la 2.1.2):
//   1. Pide UNA sola vez /api/dec_deepal/icons_bundle, un JSON con todos los
//      SVG de icons/svg/ ({nombre: "<svg ...>"}).
//   2. Si esa petición falla (típico justo tras reiniciar Home Assistant: la
//      página carga antes de que la integración termine de arrancar), NO se da
//      por perdida: se reintenta durante un rato. Mientras tanto el icono
//      queda "pendiente" y aparece solo en cuanto llega, sin recargar.
//   3. Si un icono no está en el paquete (SVG añadido sin reiniciar), se pide
//      suelto a /dec_deepal/icons/<nombre>.svg. Un fallo ahí no se recuerda.
//
// Antes (hasta la 2.1.1) se pedía cada SVG por separado y un fallo se
// guardaba para siempre: tras un reinicio los iconos no salían hasta recargar.
//
// Desde la 2.1.3, además:
//   - puede llegar tarde, traído por el cargador temprano
//     (dec-icons-loader.js, ver frontend.py);
//   - al llegar, REPINTA los iconos "dec:" que la página dibujó antes de
//     que él existiera (ver repaintStuckIcons más abajo).
//
// Por eso NO hay que tocar este archivo para añadir iconos: basta con dejar el
// .svg en custom_components/dec_deepal/icons/svg/ (ver docs/iconos.md).
//
// Requisito de los SVG: solo trazados <path> rellenos de un color. Se unen
// todos los "d" de los <path> (menos los que tengan fill="none", que suelen
// ser un rectángulo invisible de relleno) y se usa el viewBox del <svg>.
//
// API usada (documentada por Home Assistant para iconos de terceros):
//   - window.customIcons[prefijo] = { getIcon, getIconList }   (actual)
//   - window.customIconsets[prefijo] = getIcon                  (antigua)
// =============================================================================

(() => {
  // Este script puede llegar por dos caminos (la página de Home Assistant y
  // el cargador temprano dec-icons-loader.js): solo se ejecuta una vez.
  if (window.__decDeepalIcons) return;
  window.__decDeepalIcons = true;

  const PREFIX = "dec";
  const SVG_BASE_URL = "/dec_deepal/icons";
  const BUNDLE_URL = "/api/dec_deepal/icons_bundle";

  // Esperas entre reintentos del paquete (segundos). En total, ~1 minuto:
  // de sobra para que la integración termine de arrancar tras un reinicio.
  const RETRY_DELAYS = [1, 2, 3, 5, 5, 5, 10, 10, 10, 10];

  // Iconos ya convertidos: nombre → {path, viewBox}.
  const icons = new Map();
  // Carga del paquete en curso (o terminada con éxito). null = hay que pedirlo.
  let bundlePromise = null;

  const sleep = (seconds) => new Promise((resolve) => setTimeout(resolve, seconds * 1000));

  // Convierte el texto de un SVG en el formato que espera Home Assistant.
  function parseSvg(text) {
    const doc = new DOMParser().parseFromString(text, "image/svg+xml");
    const svg = doc.querySelector("svg");
    if (!svg) return undefined;
    const viewBox = svg.getAttribute("viewBox") || "0 0 24 24";
    const path = Array.from(doc.querySelectorAll("path"))
      .filter((node) => (node.getAttribute("fill") || "").toLowerCase() !== "none")
      .map((node) => node.getAttribute("d"))
      .filter(Boolean)
      .join(" ");
    return path ? { path, viewBox } : undefined;
  }

  // Un intento de descargar el paquete. true = conseguido.
  async function fetchBundle() {
    try {
      const response = await fetch(BUNDLE_URL, { cache: "no-store" });
      if (!response.ok) return false;
      const bundle = await response.json();
      for (const [name, text] of Object.entries(bundle)) {
        const icon = parseSvg(text);
        if (icon) icons.set(name, icon);
      }
      return true;
    } catch (error) {
      return false;
    }
  }

  // Descarga el paquete, reintentando si falla. Devuelve true si se consiguió.
  async function loadBundleWithRetries() {
    if (await fetchBundle()) return true;
    for (const delay of RETRY_DELAYS) {
      await sleep(delay);
      if (await fetchBundle()) return true;
    }
    console.warn("[DEC Deepal] No se pudo cargar el paquete de iconos; se reintentará.");
    return false;
  }

  // Paquete cargado (una sola carga a la vez). Si acaba en fallo, la siguiente
  // petición de un icono vuelve a intentarlo: un fallo nunca se recuerda.
  function ensureBundle() {
    if (!bundlePromise) {
      bundlePromise = loadBundleWithRetries().then((ok) => {
        if (!ok) bundlePromise = null;
        return ok;
      });
    }
    return bundlePromise;
  }

  // Icono suelto (no estaba en el paquete). No se guarda si falla.
  async function fetchSingle(name) {
    try {
      const url = `${SVG_BASE_URL}/${encodeURIComponent(name)}.svg`;
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) return undefined;
      const icon = parseSvg(await response.text());
      if (icon) icons.set(name, icon);
      return icon;
    } catch (error) {
      return undefined;
    }
  }

  // Devuelve el icono pedido. La promesa queda pendiente mientras el paquete
  // se reintenta, así Home Assistant pinta el icono en cuanto está disponible.
  async function getIcon(name) {
    if (icons.has(name)) return icons.get(name);
    await ensureBundle();
    if (icons.has(name)) return icons.get(name);
    return fetchSingle(name);
  }

  // Lista de iconos disponibles, para el selector de iconos de HA.
  async function getIconList() {
    await ensureBundle();
    return Array.from(icons.keys())
      .sort()
      .map((name) => ({ name }));
  }

  // Repinta los iconos "dec:" que se pintaron ANTES de que este script
  // existiera. Pasa tras reiniciar Home Assistant: las entidades recuerdan su
  // icono "dec:..." y la página lo dibuja durante el arranque; como entonces
  // nadie conocía el prefijo "dec", el elemento <ha-icon> lo marca como
  // desconocido (_legacy) y no vuelve a intentarlo aunque el script llegue
  // después. Aquí se le quita la marca y se le hace recargar su icono.
  // Recorre también los "shadow DOM" (la interfaz de HA está hecha de ellos).
  function repaintStuckIcons() {
    const pending = [document];
    while (pending.length) {
      const root = pending.pop();
      for (const element of root.querySelectorAll("*")) {
        if (element.shadowRoot) pending.push(element.shadowRoot);
        if (element.localName !== "ha-icon") continue;
        const icon = element.icon;
        if (typeof icon !== "string" || !icon.startsWith(`${PREFIX}:`)) continue;
        if (element._path && !element._legacy) continue; // ya está pintado
        try {
          element._legacy = false;
          // Cambiar y restaurar la propiedad en el mismo instante hace que el
          // elemento vuelva a cargar su icono sin parpadeo.
          element.icon = "";
          element.icon = icon;
        } catch (error) {
          // Un elemento raro no debe impedir repintar los demás.
        }
      }
    }
  }

  window.customIcons = window.customIcons || {};
  window.customIcons[PREFIX] = { getIcon, getIconList };

  window.customIconsets = window.customIconsets || {};
  window.customIconsets[PREFIX] = getIcon;

  // Empieza a cargar ya, sin esperar a que alguien pida un icono.
  ensureBundle();

  // Si este script ha llegado tarde, arregla lo que ya estaba pintado: ahora,
  // y un par de veces más por si la página seguía dibujándose.
  repaintStuckIcons();
  for (const seconds of [1, 3, 8]) setTimeout(repaintStuckIcons, seconds * 1000);
})();
