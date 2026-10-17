  const TAG = "dec-deepal-panel";
  if (customElements.get(TAG)) return;

  const DOMAIN = "dec_deepal";
  /** Prefijo de las órdenes del panel (panel/). */
  const WS = "dec_deepal/panel/";

  /**
   * Pestañas: clave (su nombre es el texto "tab_<clave>"), icono y si es solo
   * para administradores. Quien no lo es ve las demás en solo lectura.
   */
  const TABS = [
    ["cars", "mdi:car-multiple", false],
    ["alerts", "mdi:bell-ring", false],
    ["data", "mdi:database", true],
    ["diagnostics", "mdi:stethoscope", true],
    ["settings", "mdi:cog", true],
  ];

  /** Pulsaciones que no cambian nada: las únicas que atiende el panel en solo lectura. */
  const READ_ONLY_ACTIONS = new Set(["tab", "reload", "fold", "info", "close", "call", "copy"]);

  /** Apartados de los avisos, en su orden, con su icono. */
  const SECTIONS = [
    ["charge", "mdi:battery-charging"],
    ["warnings", "mdi:car-brake-alert"],
    ["charger", "mdi:ev-station"],
    ["maintenance", "mdi:wrench"],
    ["itv", "mdi:clipboard-check-outline"],
    ["insurance", "mdi:shield-car"],
  ];

  /** Equipamiento que se enseña de la ficha del coche: función, icono y texto. */
  const FEATURES = [
    ["asientos_calefaccion", "mdi:car-seat-heater", "feature_seat_heat"],
    ["asientos_ventilacion", "mdi:car-seat-cooler", "feature_seat_vent"],
    ["volante_calefactado", "mdi:steering", "feature_wheel_heat"],
    ["porton_electrico", "mdi:car-back", "feature_power_tailgate"],
  ];

  /** Las 12 estrellas de la franja europea de la placa de matrícula (69_matricula.js). */
  const PLATE_STARS = '<svg width="9" height="9" viewBox="0 0 9 9" fill="#ffd400" aria-hidden="true"><circle cx="4.50" cy="1.26" r="0.9"/><circle cx="6.12" cy="1.69" r="0.9"/><circle cx="7.31" cy="2.88" r="0.9"/><circle cx="7.74" cy="4.50" r="0.9"/><circle cx="7.31" cy="6.12" r="0.9"/><circle cx="6.12" cy="7.31" r="0.9"/><circle cx="4.50" cy="7.74" r="0.9"/><circle cx="2.88" cy="7.31" r="0.9"/><circle cx="1.69" cy="6.12" r="0.9"/><circle cx="1.26" cy="4.50" r="0.9"/><circle cx="1.69" cy="2.88" r="0.9"/><circle cx="2.88" cy="1.69" r="0.9"/></svg>';

  /** Icono del destino de un aviso, según su tipo. */
  const TARGET_ICONS = { mobile: "mdi:cellphone", service: "mdi:send", panel: "mdi:bell" };

  /** Cuántos eventos del historial se enseñan como mucho. */
  const HISTORY_LIMIT = 80;

  /**
   * Fondo de estudio detrás de las fotos del coche, solo en tema oscuro: se
   * aclara a gris medio detrás del coche y se funde con la tarjeta en los
   * bordes. Sin él, las partes oscuras (techo, alerón, zaga) se pierden en el
   * fondo oscuro. Las fotos no cambian; en tema claro no se pinta nada.
   */
  const STUDIO_BG = "radial-gradient(closest-side at 50% 50%, rgba(150, 154, 162, .62) 0%, rgba(150, 154, 162, .42) 45%, rgba(150, 154, 162, .14) 80%, rgba(150, 154, 162, 0) 100%)";
