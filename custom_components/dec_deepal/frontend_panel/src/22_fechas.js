  // ---------------------------------------------------------------------------
  // Fechas: lo justo para que los formularios enseñen el resultado antes de guardar
  // ---------------------------------------------------------------------------
  // Las cuentas "de verdad" las hace la integración (maintenance.py y
  // documents.py); estas son las mismas, para la vista previa.

  /** "2027-03-10" → Date (a medianoche, hora local); `null` si no es una fecha. */
  const parseDate = (iso) => {
    const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ""));
    if (!match) return null;
    const [year, month, day] = match.slice(1).map(Number);
    const date = new Date(year, month - 1, day);
    return date.getMonth() === month - 1 && date.getDate() === day ? date : null;
  };

  const isoDate = (date) => {
    const two = (value) => String(value).padStart(2, "0");
    return `${date.getFullYear()}-${two(date.getMonth() + 1)}-${two(date.getDate())}`;
  };

  /** Fecha + meses (el 31 pasa al último día si el mes es más corto), como `add_months`. */
  const addMonths = (date, months) => {
    const index = date.getMonth() + months;
    const year = date.getFullYear() + Math.floor(index / 12);
    const month = ((index % 12) + 12) % 12;
    return new Date(year, month, Math.min(date.getDate(), new Date(year, month + 1, 0).getDate()));
  };

  const addDays = (date, days) => new Date(date.getFullYear(), date.getMonth(), date.getDate() + days);

  /** Días de `from` a `to` (negativo si `to` ya pasó). */
  const daysBetween = (from, to) =>
    Math.round((Date.UTC(to.getFullYear(), to.getMonth(), to.getDate()) - Date.UTC(from.getFullYear(), from.getMonth(), from.getDate())) / 86400000);

  const today = () => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate());
  };
