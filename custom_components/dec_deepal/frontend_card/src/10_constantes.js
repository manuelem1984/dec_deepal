  const TAG = "dec-deepal-card";
  if (customElements.get(TAG)) return;

  const DOMAIN = "dec_deepal";

  // (En HOTSPOTS y DUE, "label" es la clave del texto en TEXTS.)
  // Recorte de la vista interior (1125×1500) que se enseña en "Confort" y
  // posición de cada botón sobre ese recorte, en % (Deepal S05).
  const INTERIOR = { width: 1125, height: 1500, crop: { x: 190, y: 300, w: 745, h: 560 } };
  // Recorte de la vista isométrica (750×500): se quita el aire de los lados y
  // de abajo, dejando sitio arriba para el capó y el portón abiertos.
  const ISOMETRIC = { width: 750, height: 500, crop: { x: 10, y: 40, w: 730, h: 405 } };
  // Recorte de la vista de planta (750×750, el coche con el morro hacia
  // arriba): lo justo para que quepan las cuatro puertas, el capó y el portón
  // abiertos. En horizontal la imagen se gira un cuarto de vuelta (morro a la
  // izquierda); al ser cuadrada, girada ocupa lo mismo y el recorte es el
  // mismo con los ejes cambiados.
  const TOP = { size: 750, crop: { x: 120, y: 22, w: 510, h: 720 } };
  const TOP_TAG = "dec-deepal-top-card";
  const HOTSPOTS = [
    { key: "switch.steering_wheel_heat", icon: "mdi:steering", x: 27.4, y: 16, label: "wheel_heat" },
    { key: "number.seat_vent_driver", icon: "mdi:fan", x: 21.3, y: 57.5, label: "seat_vent_driver" },
    { key: "number.seat_heat_driver", icon: "mdi:heat-wave", x: 30.8, y: 57.5, label: "seat_heat_driver" },
    { key: "number.seat_vent_passenger", icon: "mdi:fan", x: 67, y: 57.5, label: "seat_vent_passenger" },
    { key: "number.seat_heat_passenger", icon: "mdi:heat-wave", x: 76.5, y: 57.5, label: "seat_heat_passenger" },
  ];

  // Testigos de la línea de estado. "red" = grave; el resto, ámbar.
  const AMBER = "var(--warning-color, #f9a825)";
  const RED = "var(--error-color, #db4437)";
  // Algunos coches encienden un testigo sin motivo (el S05, el del airbag al
  // despertar): la ficha del coche dice cuáles no se enseñan y la tarjeta se
  // lo pregunta a la integración (SILENT_BY_DEFAULT vale hasta que responde).
  const SILENT_BY_DEFAULT = ["warning_airbag"];
  const WARNINGS = [
    { keys: ["binary_sensor.warning_brake"], icon: "mdi:car-brake-alert", color: RED },
    { keys: ["binary_sensor.warning_brake_fluid"], icon: "mdi:car-brake-fluid-level", color: RED },
    { keys: ["binary_sensor.warning_airbag"], icon: "mdi:airbag", color: RED },
    { keys: ["binary_sensor.warning_12v_battery"], icon: "mdi:car-battery", color: RED },
    { keys: ["binary_sensor.warning_coolant_temperature"], icon: "mdi:coolant-temperature", color: RED },
    { keys: ["binary_sensor.warning_power_system"], icon: "mdi:engine", color: RED },
    { keys: ["binary_sensor.warning_abs"], icon: "mdi:car-brake-abs", color: AMBER },
    { keys: ["binary_sensor.warning_eps"], icon: "mdi:steering", color: AMBER },
    {
      keys: [
        "binary_sensor.warning_tpms",
        "binary_sensor.tire_alarm_front_left",
        "binary_sensor.tire_alarm_front_right",
        "binary_sensor.tire_alarm_rear_left",
        "binary_sensor.tire_alarm_rear_right",
      ],
      icon: "mdi:car-tire-alert",
      color: AMBER,
    },
    { keys: ["binary_sensor.warning_power_limit"], icon: "mdi:speedometer-slow", color: AMBER },
    { keys: ["binary_sensor.warning_traction_battery_low"], icon: "mdi:battery-alert", color: AMBER },
    { keys: ["binary_sensor.key_battery_low"], icon: "dec:key_battery_low_on", color: AMBER },
  ];

  // Testigo de mantenimiento (solo existe si el usuario lo activó en Configurar).
  const MAINTENANCE = "binary_sensor.maintenance_due";
  const ITV = "binary_sensor.itv_due";
  const INSURANCE = "binary_sensor.insurance_due";
  // Testigos de vencimiento, en el orden en que salen. Todos se pueden pulsar.
  const DUE = [
    { key: MAINTENANCE, action: "maintenance", icon: "mdi:wrench", label: "maintenance" },
    { key: ITV, action: "itv", icon: "mdi:clipboard-check-outline", label: "itv" },
    { key: INSURANCE, action: "insurance", icon: "mdi:shield-car", label: "insurance" },
  ];
