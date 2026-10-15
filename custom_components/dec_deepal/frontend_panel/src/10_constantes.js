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

  /** Icono del destino de un aviso, según su tipo. */
  const TARGET_ICONS = { mobile: "mdi:cellphone", service: "mdi:send", panel: "mdi:bell" };

  /** Cuántos eventos del historial se enseñan como mucho. */
  const HISTORY_LIMIT = 80;
