// =============================================================================
// DEC Deepal — Paquete de iconos "dec:" para el navegador
// =============================================================================
//
// Este script lo carga Home Assistant automáticamente en el navegador (lo
// registra frontend.py). Enseña al frontend a entender iconos "dec:<nombre>":
// cuando una entidad pide "dec:windows_open", este script descarga
// /dec_deepal/icons/windows_open.svg, extrae su dibujo y se lo entrega a HA.
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
  const PREFIX = "dec";
  const SVG_BASE_URL = "/dec_deepal/icons";
  const LIST_URL = "/api/dec_deepal/icons";

  // Caché en memoria: nombre → Promise<{path, viewBox} | undefined>.
  const cache = new Map();
  let listPromise = null;

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

  // Descarga (una sola vez) y devuelve el icono pedido.
  function getIcon(name) {
    if (!cache.has(name)) {
      const url = `${SVG_BASE_URL}/${encodeURIComponent(name)}.svg`;
      cache.set(
        name,
        fetch(url)
          .then((response) => (response.ok ? response.text() : undefined))
          .then((text) => (text ? parseSvg(text) : undefined))
          .catch((error) => {
            console.warn(`[DEC Deepal] No se pudo cargar el icono ${name}:`, error);
            return undefined;
          })
      );
    }
    return cache.get(name);
  }

  // Lista de iconos disponibles, para el selector de iconos de HA.
  function getIconList() {
    if (!listPromise) {
      listPromise = fetch(LIST_URL)
        .then((response) => (response.ok ? response.json() : []))
        .then((names) => names.map((name) => ({ name })))
        .catch(() => []);
    }
    return listPromise;
  }

  window.customIcons = window.customIcons || {};
  window.customIcons[PREFIX] = { getIcon, getIconList };

  window.customIconsets = window.customIconsets || {};
  window.customIconsets[PREFIX] = getIcon;
})();
