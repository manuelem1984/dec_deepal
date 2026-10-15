// FICHERO GENERADO — no editar. El código está en frontend_card/src/;
// tras cambiarlo, ejecutar: python tools/construir_tarjeta.py
// =============================================================================
// DEC Deepal — Tarjeta para los paneles de Home Assistant
// =============================================================================
//
//   type: custom:dec-deepal-card
//   device_id: <dispositivo del coche>     (opcional: si falta, el primero)
//
// Y la misma tarjeta con el coche visto desde arriba (2.5.0b5):
//
//   type: custom:dec-deepal-top-card
//   device_id: <dispositivo del coche>
//   orientation: horizontal | vertical     (opcional: horizontal)
//
// Qué muestra (diseño cerrado con bocetos, 09-10-2026):
//   - Cabecera: nombre del coche, "Actualizado: ..." y botón de actualizar.
//   - Vista isométrica del coche (la entidad de imagen de la integración).
//     Tocarla no hace nada (a propósito).
//   - Batería: icono según el nivel (verde ≥ 50 %, amarillo < 50 %, rojo
//     < 15 %; con rayo si carga), autonomía y estado de carga, más la barra.
//   - Pulsar la franja de la batería (icono, autonomía, estado de carga y
//     barra) abre la ventana de carga: la vista de carga, el porcentaje, el
//     tiempo que queda, la corriente, el conector, lo que lleva esta carga y
//     la última carga (2.5.0b6).
//   - Línea de estado (encima de la batería, a la derecha): un tic verde si
//     no hay avisos; si los hay, el icono de cada testigo encendido.
//   - Testigo de mantenimiento (una llave inglesa en la línea de estado):
//     ámbar cuando se acerca la revisión, rojo si está vencida. Es el único
//     testigo que se puede pulsar: abre una ventana con los días y kilómetros
//     que quedan, lo que incluye la revisión, el historial y el botón para
//     registrarla (con confirmación). La misma ventana se abre siempre desde
//     "Otros → Mantenimiento".
//   - Testigos de ITV (portapapeles) y de seguro (escudo), con las mismas
//     reglas: ámbar si se acerca la fecha, rojo si vence; al pulsarlos abren su
//     ventana, que también está en "Otros". El número de póliza y los
//     teléfonos del seguro no están en ninguna entidad: la tarjeta se los pide
//     a la integración al abrir la ventana.
//   - Seis botones: Confort, Bloqueo, Maletero, Ventilar, Localizar vehículo
//     (abre un menú con luces, claxon y las dos cosas) y Otros (abre un menú
//     con el manual del coche y el mantenimiento).
//   - "Otros → Manual" abre el PDF del manual en el navegador (pestaña
//     nueva). El enlace lo da la integración (manual.py).
//   - "Confort" abre una ventana con la vista interior y, encima de la foto,
//     los botones de volante y asientos (sin color: blanco = encendido,
//     atenuado = apagado, con el nivel 1-3), la temperatura y el climatizador.
//   - Bloqueo, Maletero y Ventilar usan el PIN: piden confirmación y, si el
//     usuario tiene el modo "desbloqueo previo", la tarjeta lo hace sola.
//
// Cómo encuentra las entidades
// ----------------------------
// No hay que configurarlas. Cada entidad de la integración lleva una clave
// interna (translation_key: "battery_level", "doors"...) que no cambia aunque
// el usuario renombre la entidad. La tarjeta busca, entre las entidades del
// dispositivo elegido, la de cada clave (hass.entities).
//
// Idiomas: se usa el del usuario en Home Assistant. La tabla de textos se
// genera a partir de idiomas/ (ver docs/idiomas.md); ahí se decide también
// qué idiomas usan los textos de otro y cuál es el idioma por defecto.
//
// Sin dependencias y sin Node: JavaScript plano. El código está repartido en
// frontend_card/src/ y se une en un solo archivo (dec-deepal-card.js) con
// tools/construir_tarjeta.py. Lo carga dec-icons.js (ver frontend.py).
// Guía para tocarla: docs/tarjeta.md
// =============================================================================

(() => {
  // ── src/10_constantes.js ──────────────────────────────────────────────────
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
  // Recorte de la vista de carga (750×500): el coche de lado con su cable.
  const CHARGING = { width: 750, height: 500, crop: { x: 40, y: 96, w: 680, h: 290 } };
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

  // ── src/20_textos.js ──────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Textos por idioma
  // ---------------------------------------------------------------------------
  // FICHERO GENERADO a partir de idiomas/<idioma>.json (sección "tarjeta") con
  // tools/generar_idiomas.py. Para cambiar un texto o añadir un idioma, editar
  // esos ficheros y volver a generar. Guía: docs/idiomas.md
  //
  //   BASE_LANGUAGE       idioma que se usa si el del usuario no está traducido
  //   BORROWED_LANGUAGES  idiomas sin traducción propia que usan la de otro
  //   TEXTS               { idioma: { clave: texto } }, ya completa (a un
  //                       idioma a medias se le rellena con el idioma base)
  const BASE_LANGUAGE = "en";
  const BORROWED_LANGUAGES = {"ca": "es", "eu": "es", "gl": "es", "lb": "fr", "nn": "nb"};
  const TEXTS = {
    "es": {
      "card_description": "Tu Deepal de un vistazo: vista del coche, batería, confort y acciones rápidas.",
      "top_view": "Vista planta",
      "top_card_description": "Tu Deepal visto desde arriba: puertas, capó y maletero de un vistazo, con la batería, el confort y las acciones rápidas.",
      "orientation": "Orientación del coche",
      "orientation_horizontal": "Horizontal (tumbado)",
      "orientation_vertical": "Vertical (de pie)",
      "car": "Coche",
      "not_found": "No encuentro el coche. Elige uno en la configuración de la tarjeta.",
      "refresh": "Actualizar datos del vehículo",
      "updated": "Actualizado: {when}",
      "today": "hoy, {time}",
      "yesterday": "ayer, {time}",
      "comfort": "Confort",
      "charge_title": "Carga",
      "charge_open": "Ver la carga",
      "refresh_short": "Actualizar",
      "charging_status": "Cargando · {type}",
      "charge_full_at": "lleno a las {time}",
      "charge_plugged": "Enchufado · no carga",
      "charge_unplugged": "Sin enchufar",
      "range_left": "{value} de autonomía",
      "time_left": "Tiempo restante",
      "ends_at": "Termina hacia las {time}",
      "current": "Corriente",
      "current_ac": "Corriente alterna",
      "current_dc": "Corriente continua",
      "no_charge": "Sin carga en curso",
      "connector": "Conector",
      "connector_ac": "AC · Tipo 2",
      "plugged": "Enchufado",
      "this_charge": "Esta carga",
      "since": "Desde las {time} · {duration}",
      "last_charge": "Última carga",
      "from_to": "Del {from} % al {to} %",
      "duration_hm": "{h} h {m} min",
      "duration_m": "{m} min",
      "lock": "Bloqueo",
      "trunk": "Maletero",
      "vent": "Ventilar",
      "locate": "Localizar vehículo",
      "others": "Otros",
      "on": "Encendido",
      "off": "Apagado",
      "seats": "Asientos",
      "unlocked": "Desbloqueado",
      "locked": "Bloqueado",
      "trunk_open": "Abierto",
      "trunk_closed": "Cerrado",
      "venting": "Ventilando",
      "windows_open": "Abiertas",
      "windows_closed": "Cerradas",
      "lights_horn": "Luces y claxon",
      "others_default": "Manual y documentos",
      "day": "1 día",
      "days": "{count} días",
      "close": "Cerrar",
      "cancel": "Cancelar",
      "understood": "Entendido",
      "command_failed": "No se pudo enviar la orden al coche.",
      "no_pin": "Activa el control con PIN en el panel DEC Deepal (pestaña Ajustes) para usar este botón.",
      "pin_confirm": "Se enviará la orden a {name} con tu PIN guardado. El coche puede tardar unos segundos en responder.",
      "lock_q": "¿Bloquear las puertas?",
      "lock_do": "Bloquear",
      "unlock_q": "¿Desbloquear las puertas?",
      "unlock_do": "Desbloquear",
      "trunk_close_q": "¿Cerrar el maletero?",
      "trunk_open_q": "¿Abrir el maletero?",
      "open_do": "Abrir",
      "windows_close_q": "¿Cerrar las ventanillas?",
      "vent_q": "¿Entreabrir las ventanillas para ventilar?",
      "lights": "Luces",
      "flash": "Parpadear",
      "horn": "Claxon",
      "honk": "Tocar",
      "both": "Las dos cosas",
      "manual": "Manual",
      "open_pdf": "Abrir PDF",
      "not_enabled": "Sin activar",
      "maintenance": "Mantenimiento",
      "itv": "ITV",
      "insurance": "Seguro",
      "no_maintenance": "El mantenimiento de este coche no está activado. Actívalo en el panel DEC Deepal → Coches.",
      "no_itv": "La ITV de este coche no está activada. Actívala en el panel DEC Deepal → Coches.",
      "no_insurance": "El seguro de este coche no está activado. Actívalo en el panel DEC Deepal → Coches.",
      "ordinal": "{number}ª",
      "nth_service": "{ordinal} revisión",
      "overdue_mark": " · vencida",
      "service_overdue": "Revisión vencida",
      "service_in": "Revisión en {value}",
      "days_left": "días restantes",
      "days_late": "días de retraso",
      "km_left": "km restantes",
      "km_late": "km de retraso",
      "service_planned": "Prevista el {date} o a los {km} km, lo que llegue antes.",
      "includes": "Qué incluye",
      "history": "Historial",
      "history_item": "{ordinal} revisión · {date} · {km} km",
      "register_service": "Registrar mantenimiento",
      "register_service_q": "¿Registrar la {ordinal} revisión?",
      "register_service_text": "Se anotará que {name} ha pasado la revisión hoy{odometer}, y se empezará a contar para la siguiente. Si la pasó otro día, regístrala desde el panel DEC Deepal.",
      "with_odometer": ", con {value}",
      "register": "Registrar",
      "service_registered": "Mantenimiento registrado.",
      "service_failed": "No se pudo registrar el mantenimiento.",
      "itv_overdue": "ITV vencida",
      "itv_last_day": "ITV: último día",
      "itv_in": "ITV en {days}",
      "left": "Quedan {days}",
      "overdue": "Vencida",
      "last_day": "Último día",
      "next_itv": "Próxima ITV",
      "due_date": "fecha límite",
      "itv_rule": "Primera ITV a los 4 años de la matriculación. Después, cada 2 años hasta los 10 y cada año a partir de entonces.",
      "details": "Datos",
      "registration": "Matriculación",
      "last_itv": "Última ITV",
      "none_yet": "Aún no ha pasado ninguna",
      "register_itv": "Registrar ITV pasada",
      "register_itv_q": "¿Registrar la ITV?",
      "register_itv_text": "Se anotará que {name} ha pasado la ITV hoy y se calculará la siguiente. Si la pasó otro día, regístrala desde el panel DEC Deepal.",
      "itv_registered": "ITV registrada.",
      "itv_failed": "No se pudo registrar la ITV.",
      "insurance_last_day": "Seguro: último día",
      "insurance_cancel": "Seguro: {days} para desistir",
      "to_cancel": "{days} para desistir",
      "renews_on": "Renueva el {date}",
      "days_to_renewal": "días para la renovación",
      "days_to_cancel": "días para desistir",
      "cancel_passed": "plazo para desistir pasado",
      "renewal_text": "Renovación el {renewal}. Para no renovar hay que avisar antes del {deadline} ({days} días antes).",
      "policy": "Póliza",
      "company": "Compañía",
      "policy_number": "Nº de póliza",
      "kind": "Tipo",
      "assistance": "Asistencia",
      "kind_third_party": "Terceros",
      "kind_third_party_plus": "Terceros ampliado",
      "kind_comprehensive_excess": "Todo riesgo con franquicia",
      "kind_comprehensive": "Todo riesgo sin franquicia",
      "wheel_heat": "Volante calefactado",
      "seat_vent_driver": "Ventilación asiento conductor",
      "seat_heat_driver": "Calefacción asiento conductor",
      "seat_vent_passenger": "Ventilación asiento acompañante",
      "seat_heat_passenger": "Calefacción asiento acompañante",
      "temp_down": "Bajar temperatura",
      "temp_up": "Subir temperatura",
      "climate_on": "Climatizador encendido",
      "climate_off": "Climatizador apagado",
      "inside": "Interior {value}",
      "humidity": "Humedad {value}",
      "fan": "Ventilador {value}",
      "recirculating": "Recirculando",
      "outside_air": "Aire exterior",
      "number_copied": "Número copiado: {number}",
      "trunk_manual": "Este coche no tiene portón eléctrico: el maletero se abre y se cierra a mano."
    },
    "en": {
      "card_description": "Your Deepal at a glance: car view, battery, comfort and quick actions.",
      "top_view": "Top view",
      "top_card_description": "Your Deepal seen from above: doors, bonnet and boot at a glance, with battery, comfort and quick actions.",
      "orientation": "Vehicle orientation",
      "orientation_horizontal": "Horizontal (lying down)",
      "orientation_vertical": "Vertical (upright)",
      "car": "Car",
      "not_found": "I cannot find the car. Choose one in the card settings.",
      "refresh": "Refresh vehicle data",
      "updated": "Updated: {when}",
      "today": "today, {time}",
      "yesterday": "yesterday, {time}",
      "comfort": "Comfort",
      "charge_title": "Charging",
      "charge_open": "Show charging details",
      "refresh_short": "Refresh",
      "charging_status": "Charging · {type}",
      "charge_full_at": "full at {time}",
      "charge_plugged": "Plugged in · not charging",
      "charge_unplugged": "Not plugged in",
      "range_left": "{value} of range",
      "time_left": "Time remaining",
      "ends_at": "Finishes around {time}",
      "current": "Current",
      "current_ac": "Alternating current",
      "current_dc": "Direct current",
      "no_charge": "No charge in progress",
      "connector": "Connector",
      "connector_ac": "AC · Type 2",
      "plugged": "Plugged in",
      "this_charge": "This charge",
      "since": "Since {time} · {duration}",
      "last_charge": "Last charge",
      "from_to": "From {from}% to {to}%",
      "duration_hm": "{h} h {m} min",
      "duration_m": "{m} min",
      "lock": "Lock",
      "trunk": "Boot",
      "vent": "Vent",
      "locate": "Find vehicle",
      "others": "More",
      "on": "On",
      "off": "Off",
      "seats": "Seats",
      "unlocked": "Unlocked",
      "locked": "Locked",
      "trunk_open": "Open",
      "trunk_closed": "Closed",
      "venting": "Venting",
      "windows_open": "Open",
      "windows_closed": "Closed",
      "lights_horn": "Lights and horn",
      "others_default": "Manual and documents",
      "day": "1 day",
      "days": "{count} days",
      "close": "Close",
      "cancel": "Cancel",
      "understood": "Got it",
      "command_failed": "The command could not be sent to the car.",
      "no_pin": "Enable PIN control in the DEC Deepal panel (Settings tab) to use this button.",
      "pin_confirm": "The command will be sent to {name} with your saved PIN. The car may take a few seconds to respond.",
      "lock_q": "Lock the doors?",
      "lock_do": "Lock",
      "unlock_q": "Unlock the doors?",
      "unlock_do": "Unlock",
      "trunk_close_q": "Close the boot?",
      "trunk_open_q": "Open the boot?",
      "open_do": "Open",
      "windows_close_q": "Close the windows?",
      "vent_q": "Open the windows slightly to vent?",
      "lights": "Lights",
      "flash": "Flash",
      "horn": "Horn",
      "honk": "Sound",
      "both": "Both",
      "manual": "Manual",
      "open_pdf": "Open PDF",
      "not_enabled": "Not enabled",
      "maintenance": "Servicing",
      "itv": "ITV",
      "insurance": "Insurance",
      "no_maintenance": "Servicing is not enabled for this car. Enable it in the DEC Deepal panel → Vehicles.",
      "no_itv": "ITV is not enabled for this car. Enable it in the DEC Deepal panel → Vehicles.",
      "no_insurance": "Insurance is not enabled for this car. Enable it in the DEC Deepal panel → Vehicles.",
      "ordinal": "No. {number}",
      "nth_service": "Service {ordinal}",
      "overdue_mark": " · overdue",
      "service_overdue": "Service overdue",
      "service_in": "Service in {value}",
      "days_left": "days left",
      "days_late": "days overdue",
      "km_left": "km left",
      "km_late": "km overdue",
      "service_planned": "Due on {date} or at {km} km, whichever comes first.",
      "includes": "What it includes",
      "history": "History",
      "history_item": "Service {ordinal} · {date} · {km} km",
      "register_service": "Register service",
      "register_service_q": "Register service {ordinal}?",
      "register_service_text": "It will be recorded that {name} was serviced today{odometer}, and the count for the next one will start. If it was done on another day, register it from the DEC Deepal panel.",
      "with_odometer": ", at {value}",
      "register": "Register",
      "service_registered": "Service registered.",
      "service_failed": "The service could not be registered.",
      "itv_overdue": "ITV overdue",
      "itv_last_day": "ITV: last day",
      "itv_in": "ITV in {days}",
      "left": "{days} left",
      "overdue": "Overdue",
      "last_day": "Last day",
      "next_itv": "Next ITV",
      "due_date": "due date",
      "itv_rule": "First ITV (roadworthiness test) 4 years after registration. Then every 2 years until the car is 10, and every year from then on.",
      "details": "Details",
      "registration": "Registration",
      "last_itv": "Last ITV",
      "none_yet": "None yet",
      "register_itv": "Register ITV passed",
      "register_itv_q": "Register the ITV?",
      "register_itv_text": "It will be recorded that {name} passed the ITV today and the next one will be calculated. If it was on another day, register it from the DEC Deepal panel.",
      "itv_registered": "ITV registered.",
      "itv_failed": "The ITV could not be registered.",
      "insurance_last_day": "Insurance: last day",
      "insurance_cancel": "Insurance: {days} to cancel",
      "to_cancel": "{days} to cancel",
      "renews_on": "Renews on {date}",
      "days_to_renewal": "days until renewal",
      "days_to_cancel": "days to cancel",
      "cancel_passed": "cancellation deadline passed",
      "renewal_text": "Renewal on {renewal}. To not renew, you must give notice before {deadline} ({days} days earlier).",
      "policy": "Policy",
      "company": "Company",
      "policy_number": "Policy number",
      "kind": "Type",
      "assistance": "Assistance",
      "kind_third_party": "Third party",
      "kind_third_party_plus": "Third party, fire and theft",
      "kind_comprehensive_excess": "Comprehensive with excess",
      "kind_comprehensive": "Comprehensive without excess",
      "wheel_heat": "Heated steering wheel",
      "seat_vent_driver": "Driver seat ventilation",
      "seat_heat_driver": "Driver seat heating",
      "seat_vent_passenger": "Passenger seat ventilation",
      "seat_heat_passenger": "Passenger seat heating",
      "temp_down": "Lower temperature",
      "temp_up": "Raise temperature",
      "climate_on": "Climate control on",
      "climate_off": "Climate control off",
      "inside": "Inside {value}",
      "humidity": "Humidity {value}",
      "fan": "Fan {value}",
      "recirculating": "Recirculating",
      "outside_air": "Outside air",
      "number_copied": "Number copied: {number}",
      "trunk_manual": "This vehicle has no power tailgate: the boot is opened and closed by hand."
    },
    "pt": {
      "card_description": "O seu Deepal num relance: vista do carro, bateria, conforto e ações rápidas.",
      "top_view": "Vista de cima",
      "top_card_description": "O seu Deepal visto de cima: portas, capô e mala num relance, com a bateria, o conforto e as ações rápidas.",
      "orientation": "Orientação do carro",
      "orientation_horizontal": "Horizontal (deitado)",
      "orientation_vertical": "Vertical (de pé)",
      "car": "Carro",
      "not_found": "Não encontro o carro. Escolha um na configuração do cartão.",
      "refresh": "Atualizar dados do veículo",
      "updated": "Atualizado: {when}",
      "today": "hoje, {time}",
      "yesterday": "ontem, {time}",
      "comfort": "Conforto",
      "charge_title": "Carregamento",
      "charge_open": "Ver o carregamento",
      "refresh_short": "Atualizar",
      "charging_status": "A carregar · {type}",
      "charge_full_at": "cheio às {time}",
      "charge_plugged": "Ligado · não carrega",
      "charge_unplugged": "Desligado da tomada",
      "range_left": "{value} de autonomia",
      "time_left": "Tempo restante",
      "ends_at": "Termina por volta das {time}",
      "current": "Corrente",
      "current_ac": "Corrente alternada",
      "current_dc": "Corrente contínua",
      "no_charge": "Sem carregamento em curso",
      "connector": "Conector",
      "connector_ac": "AC · Tipo 2",
      "plugged": "Ligado",
      "this_charge": "Este carregamento",
      "since": "Desde as {time} · {duration}",
      "last_charge": "Último carregamento",
      "from_to": "De {from} % a {to} %",
      "duration_hm": "{h} h {m} min",
      "duration_m": "{m} min",
      "lock": "Bloqueio",
      "trunk": "Mala",
      "vent": "Ventilar",
      "locate": "Localizar veículo",
      "others": "Outros",
      "on": "Ligado",
      "off": "Desligado",
      "seats": "Bancos",
      "unlocked": "Desbloqueado",
      "locked": "Bloqueado",
      "trunk_open": "Aberta",
      "trunk_closed": "Fechada",
      "venting": "A ventilar",
      "windows_open": "Abertas",
      "windows_closed": "Fechadas",
      "lights_horn": "Luzes e buzina",
      "others_default": "Manual e documentos",
      "day": "1 dia",
      "days": "{count} dias",
      "close": "Fechar",
      "cancel": "Cancelar",
      "understood": "Entendido",
      "command_failed": "Não foi possível enviar o comando para o carro.",
      "no_pin": "Ative o controlo com PIN no painel DEC Deepal (separador Definições) para usar este botão.",
      "pin_confirm": "O comando será enviado para {name} com o seu PIN guardado. O carro pode demorar alguns segundos a responder.",
      "lock_q": "Bloquear as portas?",
      "lock_do": "Bloquear",
      "unlock_q": "Desbloquear as portas?",
      "unlock_do": "Desbloquear",
      "trunk_close_q": "Fechar a mala?",
      "trunk_open_q": "Abrir a mala?",
      "open_do": "Abrir",
      "windows_close_q": "Fechar as janelas?",
      "vent_q": "Entreabrir as janelas para ventilar?",
      "lights": "Luzes",
      "flash": "Piscar",
      "horn": "Buzina",
      "honk": "Tocar",
      "both": "As duas coisas",
      "manual": "Manual",
      "open_pdf": "Abrir PDF",
      "not_enabled": "Não ativado",
      "maintenance": "Manutenção",
      "itv": "ITV",
      "insurance": "Seguro",
      "no_maintenance": "A manutenção deste carro não está ativada. Ative-a no painel DEC Deepal → Veículos.",
      "no_itv": "A ITV deste carro não está ativada. Ative-a no painel DEC Deepal → Veículos.",
      "no_insurance": "O seguro deste carro não está ativado. Ative-o no painel DEC Deepal → Veículos.",
      "ordinal": "{number}.ª",
      "nth_service": "{ordinal} revisão",
      "overdue_mark": " · vencida",
      "service_overdue": "Revisão vencida",
      "service_in": "Revisão em {value}",
      "days_left": "dias restantes",
      "days_late": "dias de atraso",
      "km_left": "km restantes",
      "km_late": "km de atraso",
      "service_planned": "Prevista para {date} ou aos {km} km, o que ocorrer primeiro.",
      "includes": "O que inclui",
      "history": "Histórico",
      "history_item": "{ordinal} revisão · {date} · {km} km",
      "register_service": "Registar manutenção",
      "register_service_q": "Registar a {ordinal} revisão?",
      "register_service_text": "Ficará anotado que {name} fez a revisão hoje{odometer}, e começa a contagem para a seguinte. Se foi noutro dia, registe-a no painel DEC Deepal.",
      "with_odometer": ", com {value}",
      "register": "Registar",
      "service_registered": "Manutenção registada.",
      "service_failed": "Não foi possível registar a manutenção.",
      "itv_overdue": "ITV vencida",
      "itv_last_day": "ITV: último dia",
      "itv_in": "ITV em {days}",
      "left": "Faltam {days}",
      "overdue": "Vencida",
      "last_day": "Último dia",
      "next_itv": "Próxima ITV",
      "due_date": "data limite",
      "itv_rule": "Primeira ITV (inspeção periódica) 4 anos após a matrícula. Depois, de 2 em 2 anos até aos 10 e todos os anos a partir daí.",
      "details": "Dados",
      "registration": "Matrícula",
      "last_itv": "Última ITV",
      "none_yet": "Ainda não fez nenhuma",
      "register_itv": "Registar ITV feita",
      "register_itv_q": "Registar a ITV?",
      "register_itv_text": "Ficará anotado que {name} passou na ITV hoje e será calculada a seguinte. Se foi noutro dia, registe-a no painel DEC Deepal.",
      "itv_registered": "ITV registada.",
      "itv_failed": "Não foi possível registar a ITV.",
      "insurance_last_day": "Seguro: último dia",
      "insurance_cancel": "Seguro: {days} para cancelar",
      "to_cancel": "{days} para cancelar",
      "renews_on": "Renova a {date}",
      "days_to_renewal": "dias até à renovação",
      "days_to_cancel": "dias para cancelar",
      "cancel_passed": "prazo para cancelar ultrapassado",
      "renewal_text": "Renovação a {renewal}. Para não renovar é preciso avisar antes de {deadline} ({days} dias antes).",
      "policy": "Apólice",
      "company": "Seguradora",
      "policy_number": "N.º da apólice",
      "kind": "Tipo",
      "assistance": "Assistência",
      "kind_third_party": "Terceiros",
      "kind_third_party_plus": "Terceiros alargado",
      "kind_comprehensive_excess": "Danos próprios com franquia",
      "kind_comprehensive": "Danos próprios sem franquia",
      "wheel_heat": "Volante aquecido",
      "seat_vent_driver": "Ventilação do banco do condutor",
      "seat_heat_driver": "Aquecimento do banco do condutor",
      "seat_vent_passenger": "Ventilação do banco do passageiro",
      "seat_heat_passenger": "Aquecimento do banco do passageiro",
      "temp_down": "Baixar a temperatura",
      "temp_up": "Subir a temperatura",
      "climate_on": "Climatização ligada",
      "climate_off": "Climatização desligada",
      "inside": "Interior {value}",
      "humidity": "Humidade {value}",
      "fan": "Ventilador {value}",
      "recirculating": "A recircular",
      "outside_air": "Ar exterior",
      "number_copied": "Número copiado: {number}",
      "trunk_manual": "Este veículo não tem portão elétrico: a mala abre-se e fecha-se à mão."
    },
    "it": {
      "card_description": "La tua Deepal a colpo d'occhio: vista dell'auto, batteria, comfort e azioni rapide.",
      "top_view": "Vista dall'alto",
      "top_card_description": "La tua Deepal vista dall'alto: porte, cofano e bagagliaio a colpo d'occhio, con batteria, comfort e azioni rapide.",
      "orientation": "Orientamento dell'auto",
      "orientation_horizontal": "Orizzontale (sdraiata)",
      "orientation_vertical": "Verticale (in piedi)",
      "car": "Auto",
      "not_found": "Non trovo l'auto. Scegline una nella configurazione della scheda.",
      "refresh": "Aggiorna dati del veicolo",
      "updated": "Aggiornato: {when}",
      "today": "oggi, {time}",
      "yesterday": "ieri, {time}",
      "comfort": "Comfort",
      "charge_title": "Ricarica",
      "charge_open": "Mostra la ricarica",
      "refresh_short": "Aggiorna",
      "charging_status": "In ricarica · {type}",
      "charge_full_at": "piena alle {time}",
      "charge_plugged": "Collegata · non carica",
      "charge_unplugged": "Non collegata",
      "range_left": "{value} di autonomia",
      "time_left": "Tempo rimanente",
      "ends_at": "Termina verso le {time}",
      "current": "Corrente",
      "current_ac": "Corrente alternata",
      "current_dc": "Corrente continua",
      "no_charge": "Nessuna ricarica in corso",
      "connector": "Connettore",
      "connector_ac": "AC · Tipo 2",
      "plugged": "Collegato",
      "this_charge": "Questa ricarica",
      "since": "Dalle {time} · {duration}",
      "last_charge": "Ultima ricarica",
      "from_to": "Dal {from} % al {to} %",
      "duration_hm": "{h} h {m} min",
      "duration_m": "{m} min",
      "lock": "Chiusura",
      "trunk": "Bagagliaio",
      "vent": "Ventila",
      "locate": "Trova veicolo",
      "others": "Altro",
      "on": "Acceso",
      "off": "Spento",
      "seats": "Sedili",
      "unlocked": "Sbloccato",
      "locked": "Bloccato",
      "trunk_open": "Aperto",
      "trunk_closed": "Chiuso",
      "venting": "In ventilazione",
      "windows_open": "Aperti",
      "windows_closed": "Chiusi",
      "lights_horn": "Luci e clacson",
      "others_default": "Manuale e documenti",
      "day": "1 giorno",
      "days": "{count} giorni",
      "close": "Chiudi",
      "cancel": "Annulla",
      "understood": "Ho capito",
      "command_failed": "Impossibile inviare il comando all'auto.",
      "no_pin": "Attiva il controllo con PIN nel pannello DEC Deepal (scheda Impostazioni) per usare questo pulsante.",
      "pin_confirm": "Il comando verrà inviato a {name} con il tuo PIN salvato. L'auto può impiegare qualche secondo a rispondere.",
      "lock_q": "Bloccare le porte?",
      "lock_do": "Blocca",
      "unlock_q": "Sbloccare le porte?",
      "unlock_do": "Sblocca",
      "trunk_close_q": "Chiudere il bagagliaio?",
      "trunk_open_q": "Aprire il bagagliaio?",
      "open_do": "Apri",
      "windows_close_q": "Chiudere i finestrini?",
      "vent_q": "Socchiudere i finestrini per ventilare?",
      "lights": "Luci",
      "flash": "Lampeggia",
      "horn": "Clacson",
      "honk": "Suona",
      "both": "Entrambi",
      "manual": "Manuale",
      "open_pdf": "Apri PDF",
      "not_enabled": "Non attivo",
      "maintenance": "Manutenzione",
      "itv": "ITV",
      "insurance": "Assicurazione",
      "no_maintenance": "La manutenzione di quest'auto non è attiva. Attivala nel pannello DEC Deepal → Veicoli.",
      "no_itv": "L'ITV di quest'auto non è attiva. Attivala nel pannello DEC Deepal → Veicoli.",
      "no_insurance": "L'assicurazione di quest'auto non è attiva. Attivala nel pannello DEC Deepal → Veicoli.",
      "ordinal": "{number}º",
      "nth_service": "{ordinal} tagliando",
      "overdue_mark": " · scaduto",
      "service_overdue": "Tagliando scaduto",
      "service_in": "Tagliando tra {value}",
      "days_left": "giorni rimanenti",
      "days_late": "giorni di ritardo",
      "km_left": "km rimanenti",
      "km_late": "km di ritardo",
      "service_planned": "Previsto per il {date} o a {km} km, a seconda di cosa arriva prima.",
      "includes": "Cosa include",
      "history": "Storico",
      "history_item": "{ordinal} tagliando · {date} · {km} km",
      "register_service": "Registra manutenzione",
      "register_service_q": "Registrare il {ordinal} tagliando?",
      "register_service_text": "Verrà annotato che {name} ha fatto il tagliando oggi{odometer}, e inizierà il conteggio per il successivo. Se l'ha fatto un altro giorno, registralo dal pannello DEC Deepal.",
      "with_odometer": ", con {value}",
      "register": "Registra",
      "service_registered": "Manutenzione registrata.",
      "service_failed": "Impossibile registrare la manutenzione.",
      "itv_overdue": "ITV scaduta",
      "itv_last_day": "ITV: ultimo giorno",
      "itv_in": "ITV tra {days}",
      "left": "Mancano {days}",
      "overdue": "Scaduta",
      "last_day": "Ultimo giorno",
      "next_itv": "Prossima ITV",
      "due_date": "data limite",
      "itv_rule": "Prima ITV (revisione spagnola) a 4 anni dall'immatricolazione. Poi ogni 2 anni fino ai 10 e ogni anno da allora in poi.",
      "details": "Dati",
      "registration": "Immatricolazione",
      "last_itv": "Ultima ITV",
      "none_yet": "Non ne ha ancora fatta nessuna",
      "register_itv": "Registra ITV superata",
      "register_itv_q": "Registrare l'ITV?",
      "register_itv_text": "Verrà annotato che {name} ha superato l'ITV oggi e verrà calcolata la successiva. Se è stato un altro giorno, registrala dal pannello DEC Deepal.",
      "itv_registered": "ITV registrata.",
      "itv_failed": "Impossibile registrare l'ITV.",
      "insurance_last_day": "Assicurazione: ultimo giorno",
      "insurance_cancel": "Assicurazione: {days} per disdire",
      "to_cancel": "{days} per disdire",
      "renews_on": "Si rinnova il {date}",
      "days_to_renewal": "giorni al rinnovo",
      "days_to_cancel": "giorni per disdire",
      "cancel_passed": "termine per disdire scaduto",
      "renewal_text": "Rinnovo il {renewal}. Per non rinnovare bisogna avvisare entro il {deadline} ({days} giorni prima).",
      "policy": "Polizza",
      "company": "Compagnia",
      "policy_number": "N. di polizza",
      "kind": "Tipo",
      "assistance": "Assistenza",
      "kind_third_party": "RC auto",
      "kind_third_party_plus": "RC auto con garanzie aggiuntive",
      "kind_comprehensive_excess": "Kasko con franchigia",
      "kind_comprehensive": "Kasko senza franchigia",
      "wheel_heat": "Volante riscaldato",
      "seat_vent_driver": "Ventilazione sedile conducente",
      "seat_heat_driver": "Riscaldamento sedile conducente",
      "seat_vent_passenger": "Ventilazione sedile passeggero",
      "seat_heat_passenger": "Riscaldamento sedile passeggero",
      "temp_down": "Abbassa la temperatura",
      "temp_up": "Alza la temperatura",
      "climate_on": "Climatizzatore acceso",
      "climate_off": "Climatizzatore spento",
      "inside": "Interno {value}",
      "humidity": "Umidità {value}",
      "fan": "Ventola {value}",
      "recirculating": "Ricircolo",
      "outside_air": "Aria esterna",
      "number_copied": "Numero copiato: {number}",
      "trunk_manual": "Questo veicolo non ha il portellone elettrico: il bagagliaio si apre e si chiude a mano."
    },
    "pl": {
      "card_description": "Twój Deepal w jednym miejscu: widok samochodu, akumulator, komfort i szybkie akcje.",
      "top_view": "Widok z góry",
      "top_card_description": "Twój Deepal widziany z góry: drzwi, maska i bagażnik na pierwszy rzut oka, z baterią, komfortem i szybkimi akcjami.",
      "orientation": "Orientacja samochodu",
      "orientation_horizontal": "Poziomo (na leżąco)",
      "orientation_vertical": "Pionowo (na stojąco)",
      "car": "Samochód",
      "not_found": "Nie znajduję samochodu. Wybierz go w konfiguracji karty.",
      "refresh": "Odśwież dane pojazdu",
      "updated": "Zaktualizowano: {when}",
      "today": "dziś, {time}",
      "yesterday": "wczoraj, {time}",
      "comfort": "Komfort",
      "charge_title": "Ładowanie",
      "charge_open": "Pokaż ładowanie",
      "refresh_short": "Odśwież",
      "charging_status": "Ładowanie · {type}",
      "charge_full_at": "pełna o {time}",
      "charge_plugged": "Podłączony · nie ładuje",
      "charge_unplugged": "Niepodłączony",
      "range_left": "{value} zasięgu",
      "time_left": "Pozostały czas",
      "ends_at": "Koniec około {time}",
      "current": "Prąd",
      "current_ac": "Prąd przemienny",
      "current_dc": "Prąd stały",
      "no_charge": "Brak ładowania",
      "connector": "Złącze",
      "connector_ac": "AC · Typ 2",
      "plugged": "Podłączone",
      "this_charge": "To ładowanie",
      "since": "Od {time} · {duration}",
      "last_charge": "Ostatnie ładowanie",
      "from_to": "Od {from}% do {to}%",
      "duration_hm": "{h} godz. {m} min",
      "duration_m": "{m} min",
      "lock": "Zamek",
      "trunk": "Bagażnik",
      "vent": "Przewietrz",
      "locate": "Znajdź pojazd",
      "others": "Więcej",
      "on": "Włączone",
      "off": "Wyłączone",
      "seats": "Fotele",
      "unlocked": "Odblokowany",
      "locked": "Zablokowany",
      "trunk_open": "Otwarty",
      "trunk_closed": "Zamknięty",
      "venting": "Wietrzenie",
      "windows_open": "Otwarte",
      "windows_closed": "Zamknięte",
      "lights_horn": "Światła i klakson",
      "others_default": "Instrukcja i dokumenty",
      "day": "1 dzień",
      "days": "{count} dni",
      "close": "Zamknij",
      "cancel": "Anuluj",
      "understood": "Rozumiem",
      "command_failed": "Nie udało się wysłać polecenia do samochodu.",
      "no_pin": "Włącz sterowanie z PIN-em w panelu DEC Deepal (karta Ustawienia), aby używać tego przycisku.",
      "pin_confirm": "Polecenie zostanie wysłane do: {name}, z użyciem zapisanego PIN-u. Samochód może odpowiedzieć po kilku sekundach.",
      "lock_q": "Zablokować drzwi?",
      "lock_do": "Zablokuj",
      "unlock_q": "Odblokować drzwi?",
      "unlock_do": "Odblokuj",
      "trunk_close_q": "Zamknąć bagażnik?",
      "trunk_open_q": "Otworzyć bagażnik?",
      "open_do": "Otwórz",
      "windows_close_q": "Zamknąć szyby?",
      "vent_q": "Uchylić szyby, aby przewietrzyć?",
      "lights": "Światła",
      "flash": "Mignij",
      "horn": "Klakson",
      "honk": "Zatrąb",
      "both": "Jedno i drugie",
      "manual": "Instrukcja",
      "open_pdf": "Otwórz PDF",
      "not_enabled": "Nie włączono",
      "maintenance": "Serwis",
      "itv": "ITV",
      "insurance": "Ubezpieczenie",
      "no_maintenance": "Serwis dla tego samochodu nie jest włączony. Włącz go w panelu DEC Deepal → Pojazdy.",
      "no_itv": "ITV dla tego samochodu nie jest włączone. Włącz je w panelu DEC Deepal → Pojazdy.",
      "no_insurance": "Ubezpieczenie dla tego samochodu nie jest włączone. Włącz je w panelu DEC Deepal → Pojazdy.",
      "ordinal": "{number}.",
      "nth_service": "{ordinal} przegląd",
      "overdue_mark": " · po terminie",
      "service_overdue": "Przegląd po terminie",
      "service_in": "Przegląd za {value}",
      "days_left": "dni pozostało",
      "days_late": "dni po terminie",
      "km_left": "km pozostało",
      "km_late": "km po terminie",
      "service_planned": "Planowany na {date} lub przy {km} km, zależnie od tego, co nastąpi wcześniej.",
      "includes": "Co obejmuje",
      "history": "Historia",
      "history_item": "{ordinal} przegląd · {date} · {km} km",
      "register_service": "Zarejestruj serwis",
      "register_service_q": "Zarejestrować {ordinal} przegląd?",
      "register_service_text": "Zostanie zapisane, że {name} przeszedł przegląd dzisiaj{odometer}, i zacznie się odliczanie do następnego. Jeśli było to innego dnia, zarejestruj go w panelu DEC Deepal.",
      "with_odometer": ", przy {value}",
      "register": "Zarejestruj",
      "service_registered": "Serwis zarejestrowany.",
      "service_failed": "Nie udało się zarejestrować serwisu.",
      "itv_overdue": "ITV po terminie",
      "itv_last_day": "ITV: ostatni dzień",
      "itv_in": "ITV za {days}",
      "left": "Pozostało: {days}",
      "overdue": "Po terminie",
      "last_day": "Ostatni dzień",
      "next_itv": "Następne ITV",
      "due_date": "termin",
      "itv_rule": "Pierwsze ITV (hiszpański przegląd techniczny) po 4 latach od rejestracji. Potem co 2 lata do 10. roku, a następnie co roku.",
      "details": "Dane",
      "registration": "Rejestracja",
      "last_itv": "Ostatnie ITV",
      "none_yet": "Jeszcze żadnego",
      "register_itv": "Zarejestruj zaliczone ITV",
      "register_itv_q": "Zarejestrować ITV?",
      "register_itv_text": "Zostanie zapisane, że {name} przeszedł ITV dzisiaj, i zostanie obliczony następny termin. Jeśli było to innego dnia, zarejestruj je w panelu DEC Deepal.",
      "itv_registered": "ITV zarejestrowane.",
      "itv_failed": "Nie udało się zarejestrować ITV.",
      "insurance_last_day": "Ubezpieczenie: ostatni dzień",
      "insurance_cancel": "Ubezpieczenie: {days} na wypowiedzenie",
      "to_cancel": "{days} na wypowiedzenie",
      "renews_on": "Odnowienie: {date}",
      "days_to_renewal": "dni do odnowienia",
      "days_to_cancel": "dni na wypowiedzenie",
      "cancel_passed": "termin wypowiedzenia minął",
      "renewal_text": "Odnowienie: {renewal}. Aby nie przedłużać, trzeba to zgłosić przed {deadline} ({days} dni wcześniej).",
      "policy": "Polisa",
      "company": "Ubezpieczyciel",
      "policy_number": "Nr polisy",
      "kind": "Rodzaj",
      "assistance": "Pomoc drogowa",
      "kind_third_party": "OC",
      "kind_third_party_plus": "OC rozszerzone",
      "kind_comprehensive_excess": "AC z udziałem własnym",
      "kind_comprehensive": "AC bez udziału własnego",
      "wheel_heat": "Podgrzewana kierownica",
      "seat_vent_driver": "Wentylacja fotela kierowcy",
      "seat_heat_driver": "Ogrzewanie fotela kierowcy",
      "seat_vent_passenger": "Wentylacja fotela pasażera",
      "seat_heat_passenger": "Ogrzewanie fotela pasażera",
      "temp_down": "Obniż temperaturę",
      "temp_up": "Podnieś temperaturę",
      "climate_on": "Klimatyzacja włączona",
      "climate_off": "Klimatyzacja wyłączona",
      "inside": "Wewnątrz {value}",
      "humidity": "Wilgotność {value}",
      "fan": "Wentylator {value}",
      "recirculating": "Obieg wewnętrzny",
      "outside_air": "Powietrze z zewnątrz",
      "number_copied": "Skopiowano numer: {number}",
      "trunk_manual": "Ten pojazd nie ma elektrycznej klapy bagażnika: bagażnik otwiera się i zamyka ręcznie."
    },
    "de": {
      "card_description": "Dein Deepal auf einen Blick: Fahrzeugansicht, Batterie, Komfort und Schnellaktionen.",
      "top_view": "Draufsicht",
      "top_card_description": "Dein Deepal von oben: Türen, Motorhaube und Kofferraum auf einen Blick, mit Batterie, Komfort und Schnellaktionen.",
      "orientation": "Ausrichtung des Autos",
      "orientation_horizontal": "Waagerecht (liegend)",
      "orientation_vertical": "Senkrecht (stehend)",
      "car": "Auto",
      "not_found": "Ich finde das Auto nicht. Wähle eines in den Karteneinstellungen.",
      "refresh": "Fahrzeugdaten aktualisieren",
      "updated": "Aktualisiert: {when}",
      "today": "heute, {time}",
      "yesterday": "gestern, {time}",
      "comfort": "Komfort",
      "charge_title": "Laden",
      "charge_open": "Ladedetails anzeigen",
      "refresh_short": "Aktualisieren",
      "charging_status": "Lädt · {type}",
      "charge_full_at": "voll um {time}",
      "charge_plugged": "Angeschlossen · lädt nicht",
      "charge_unplugged": "Nicht angeschlossen",
      "range_left": "{value} Reichweite",
      "time_left": "Restzeit",
      "ends_at": "Endet gegen {time}",
      "current": "Strom",
      "current_ac": "Wechselstrom",
      "current_dc": "Gleichstrom",
      "no_charge": "Kein Ladevorgang",
      "connector": "Stecker",
      "connector_ac": "AC · Typ 2",
      "plugged": "Angeschlossen",
      "this_charge": "Dieser Ladevorgang",
      "since": "Seit {time} · {duration}",
      "last_charge": "Letzter Ladevorgang",
      "from_to": "Von {from} % auf {to} %",
      "duration_hm": "{h} h {m} min",
      "duration_m": "{m} min",
      "lock": "Schloss",
      "trunk": "Kofferraum",
      "vent": "Lüften",
      "locate": "Fahrzeug finden",
      "others": "Mehr",
      "on": "An",
      "off": "Aus",
      "seats": "Sitze",
      "unlocked": "Entriegelt",
      "locked": "Verriegelt",
      "trunk_open": "Offen",
      "trunk_closed": "Geschlossen",
      "venting": "Lüftet",
      "windows_open": "Offen",
      "windows_closed": "Geschlossen",
      "lights_horn": "Licht und Hupe",
      "others_default": "Handbuch und Dokumente",
      "day": "1 Tag",
      "days": "{count} Tage",
      "close": "Schließen",
      "cancel": "Abbrechen",
      "understood": "Verstanden",
      "command_failed": "Der Befehl konnte nicht an das Auto gesendet werden.",
      "no_pin": "Aktiviere die PIN-Steuerung im DEC-Deepal-Panel (Tab Einstellungen), um diese Taste zu nutzen.",
      "pin_confirm": "Der Befehl wird mit deiner gespeicherten PIN an {name} gesendet. Das Auto kann ein paar Sekunden brauchen.",
      "lock_q": "Türen verriegeln?",
      "lock_do": "Verriegeln",
      "unlock_q": "Türen entriegeln?",
      "unlock_do": "Entriegeln",
      "trunk_close_q": "Kofferraum schließen?",
      "trunk_open_q": "Kofferraum öffnen?",
      "open_do": "Öffnen",
      "windows_close_q": "Fenster schließen?",
      "vent_q": "Fenster zum Lüften einen Spalt öffnen?",
      "lights": "Licht",
      "flash": "Blinken",
      "horn": "Hupe",
      "honk": "Hupen",
      "both": "Beides",
      "manual": "Handbuch",
      "open_pdf": "PDF öffnen",
      "not_enabled": "Nicht aktiviert",
      "maintenance": "Wartung",
      "itv": "ITV",
      "insurance": "Versicherung",
      "no_maintenance": "Die Wartung ist für dieses Auto nicht aktiviert. Aktiviere sie im DEC-Deepal-Panel → Fahrzeuge.",
      "no_itv": "Die ITV ist für dieses Auto nicht aktiviert. Aktiviere sie im DEC-Deepal-Panel → Fahrzeuge.",
      "no_insurance": "Die Versicherung ist für dieses Auto nicht aktiviert. Aktiviere sie im DEC-Deepal-Panel → Fahrzeuge.",
      "ordinal": "{number}.",
      "nth_service": "{ordinal} Wartung",
      "overdue_mark": " · überfällig",
      "service_overdue": "Wartung überfällig",
      "service_in": "Wartung in {value}",
      "days_left": "Tage übrig",
      "days_late": "Tage überfällig",
      "km_left": "km übrig",
      "km_late": "km überfällig",
      "service_planned": "Fällig am {date} oder bei {km} km, je nachdem, was zuerst eintritt.",
      "includes": "Was dazugehört",
      "history": "Verlauf",
      "history_item": "{ordinal} Wartung · {date} · {km} km",
      "register_service": "Wartung erfassen",
      "register_service_q": "{ordinal} Wartung erfassen?",
      "register_service_text": "Es wird vermerkt, dass {name} heute gewartet wurde{odometer}, und die Zählung bis zur nächsten beginnt. War es an einem anderen Tag, erfasse sie im DEC-Deepal-Panel.",
      "with_odometer": ", bei {value}",
      "register": "Erfassen",
      "service_registered": "Wartung erfasst.",
      "service_failed": "Die Wartung konnte nicht erfasst werden.",
      "itv_overdue": "ITV überfällig",
      "itv_last_day": "ITV: letzter Tag",
      "itv_in": "ITV in {days}",
      "left": "Noch {days}",
      "overdue": "Überfällig",
      "last_day": "Letzter Tag",
      "next_itv": "Nächste ITV",
      "due_date": "Fälligkeitsdatum",
      "itv_rule": "Erste ITV (Hauptuntersuchung) 4 Jahre nach der Zulassung. Danach alle 2 Jahre, bis das Auto 10 Jahre alt ist, und dann jedes Jahr.",
      "details": "Details",
      "registration": "Zulassung",
      "last_itv": "Letzte ITV",
      "none_yet": "Noch keine",
      "register_itv": "Bestandene ITV erfassen",
      "register_itv_q": "ITV erfassen?",
      "register_itv_text": "Es wird vermerkt, dass {name} heute die ITV bestanden hat, und die nächste wird berechnet. War es an einem anderen Tag, trage es im DEC-Deepal-Panel ein.",
      "itv_registered": "ITV erfasst.",
      "itv_failed": "Die ITV konnte nicht erfasst werden.",
      "insurance_last_day": "Versicherung: letzter Tag",
      "insurance_cancel": "Versicherung: {days} zum Kündigen",
      "to_cancel": "{days} zum Kündigen",
      "renews_on": "Verlängert sich am {date}",
      "days_to_renewal": "Tage bis zur Verlängerung",
      "days_to_cancel": "Tage zum Kündigen",
      "cancel_passed": "Kündigungsfrist abgelaufen",
      "renewal_text": "Verlängerung am {renewal}. Um nicht zu verlängern, musst du vor dem {deadline} kündigen ({days} Tage vorher).",
      "policy": "Police",
      "company": "Gesellschaft",
      "policy_number": "Policennummer",
      "kind": "Art",
      "assistance": "Pannenhilfe",
      "kind_third_party": "Haftpflicht",
      "kind_third_party_plus": "Teilkasko",
      "kind_comprehensive_excess": "Vollkasko mit Selbstbeteiligung",
      "kind_comprehensive": "Vollkasko ohne Selbstbeteiligung",
      "wheel_heat": "Lenkradheizung",
      "seat_vent_driver": "Sitzbelüftung Fahrer",
      "seat_heat_driver": "Sitzheizung Fahrer",
      "seat_vent_passenger": "Sitzbelüftung Beifahrer",
      "seat_heat_passenger": "Sitzheizung Beifahrer",
      "temp_down": "Temperatur senken",
      "temp_up": "Temperatur erhöhen",
      "climate_on": "Klimaanlage an",
      "climate_off": "Klimaanlage aus",
      "inside": "Innen {value}",
      "humidity": "Luftfeuchte {value}",
      "fan": "Gebläse {value}",
      "recirculating": "Umluft",
      "outside_air": "Außenluft",
      "number_copied": "Nummer kopiert: {number}",
      "trunk_manual": "Dieses Fahrzeug hat keine elektrische Heckklappe: Der Kofferraum wird von Hand geöffnet und geschlossen."
    },
    "fr": {
      "card_description": "Votre Deepal en un coup d'œil : vue de la voiture, batterie, confort et actions rapides.",
      "top_view": "Vue de dessus",
      "top_card_description": "Votre Deepal vue de dessus : portes, capot et coffre en un coup d'œil, avec la batterie, le confort et les actions rapides.",
      "orientation": "Orientation de la voiture",
      "orientation_horizontal": "Horizontale (couchée)",
      "orientation_vertical": "Verticale (debout)",
      "car": "Voiture",
      "not_found": "Je ne trouve pas la voiture. Choisissez-en une dans les réglages de la carte.",
      "refresh": "Actualiser les données du véhicule",
      "updated": "Mis à jour : {when}",
      "today": "aujourd'hui, {time}",
      "yesterday": "hier, {time}",
      "comfort": "Confort",
      "charge_title": "Recharge",
      "charge_open": "Afficher la recharge",
      "refresh_short": "Actualiser",
      "charging_status": "En recharge · {type}",
      "charge_full_at": "pleine à {time}",
      "charge_plugged": "Branchée · ne charge pas",
      "charge_unplugged": "Non branchée",
      "range_left": "{value} d'autonomie",
      "time_left": "Temps restant",
      "ends_at": "Se termine vers {time}",
      "current": "Courant",
      "current_ac": "Courant alternatif",
      "current_dc": "Courant continu",
      "no_charge": "Aucune recharge en cours",
      "connector": "Connecteur",
      "connector_ac": "AC · Type 2",
      "plugged": "Branché",
      "this_charge": "Cette recharge",
      "since": "Depuis {time} · {duration}",
      "last_charge": "Dernière recharge",
      "from_to": "De {from} % à {to} %",
      "duration_hm": "{h} h {m} min",
      "duration_m": "{m} min",
      "lock": "Verrou",
      "trunk": "Coffre",
      "vent": "Aérer",
      "locate": "Localiser le véhicule",
      "others": "Plus",
      "on": "Allumé",
      "off": "Éteint",
      "seats": "Sièges",
      "unlocked": "Déverrouillée",
      "locked": "Verrouillée",
      "trunk_open": "Ouvert",
      "trunk_closed": "Fermé",
      "venting": "Aération",
      "windows_open": "Ouvertes",
      "windows_closed": "Fermées",
      "lights_horn": "Phares et klaxon",
      "others_default": "Manuel et documents",
      "day": "1 jour",
      "days": "{count} jours",
      "close": "Fermer",
      "cancel": "Annuler",
      "understood": "Compris",
      "command_failed": "La commande n'a pas pu être envoyée à la voiture.",
      "no_pin": "Activez le contrôle par code PIN dans le panneau DEC Deepal (onglet Réglages) pour utiliser ce bouton.",
      "pin_confirm": "La commande sera envoyée à {name} avec votre code PIN enregistré. La voiture peut mettre quelques secondes à répondre.",
      "lock_q": "Verrouiller les portes ?",
      "lock_do": "Verrouiller",
      "unlock_q": "Déverrouiller les portes ?",
      "unlock_do": "Déverrouiller",
      "trunk_close_q": "Fermer le coffre ?",
      "trunk_open_q": "Ouvrir le coffre ?",
      "open_do": "Ouvrir",
      "windows_close_q": "Fermer les vitres ?",
      "vent_q": "Entrouvrir les vitres pour aérer ?",
      "lights": "Phares",
      "flash": "Appel",
      "horn": "Klaxon",
      "honk": "Klaxonner",
      "both": "Les deux",
      "manual": "Manuel",
      "open_pdf": "Ouvrir le PDF",
      "not_enabled": "Non activé",
      "maintenance": "Entretien",
      "itv": "ITV",
      "insurance": "Assurance",
      "no_maintenance": "L'entretien n'est pas activé pour cette voiture. Activez-le dans le panneau DEC Deepal → Véhicules.",
      "no_itv": "L'ITV n'est pas activée pour cette voiture. Activez-la dans le panneau DEC Deepal → Véhicules.",
      "no_insurance": "L'assurance n'est pas activée pour cette voiture. Activez-la dans le panneau DEC Deepal → Véhicules.",
      "ordinal": "n° {number}",
      "nth_service": "Entretien {ordinal}",
      "overdue_mark": " · en retard",
      "service_overdue": "Entretien en retard",
      "service_in": "Entretien dans {value}",
      "days_left": "jours restants",
      "days_late": "jours de retard",
      "km_left": "km restants",
      "km_late": "km de retard",
      "service_planned": "Prévu le {date} ou à {km} km, au premier des deux termes atteint.",
      "includes": "Ce qu'il comprend",
      "history": "Historique",
      "history_item": "Entretien {ordinal} · {date} · {km} km",
      "register_service": "Enregistrer l'entretien",
      "register_service_q": "Enregistrer l'entretien {ordinal} ?",
      "register_service_text": "Il sera noté que {name} a été entretenue aujourd'hui{odometer}, et le décompte du suivant commencera. Si c'était un autre jour, enregistrez-le depuis le panneau DEC Deepal.",
      "with_odometer": ", à {value}",
      "register": "Enregistrer",
      "service_registered": "Entretien enregistré.",
      "service_failed": "L'entretien n'a pas pu être enregistré.",
      "itv_overdue": "ITV dépassée",
      "itv_last_day": "ITV : dernier jour",
      "itv_in": "ITV dans {days}",
      "left": "Il reste {days}",
      "overdue": "Dépassée",
      "last_day": "Dernier jour",
      "next_itv": "Prochaine ITV",
      "due_date": "date limite",
      "itv_rule": "Première ITV (contrôle technique) 4 ans après l'immatriculation. Ensuite tous les 2 ans jusqu'aux 10 ans de la voiture, puis tous les ans.",
      "details": "Détails",
      "registration": "Immatriculation",
      "last_itv": "Dernière ITV",
      "none_yet": "Aucune pour l'instant",
      "register_itv": "Enregistrer l'ITV passée",
      "register_itv_q": "Enregistrer l'ITV ?",
      "register_itv_text": "Il sera noté que {name} a passé l'ITV aujourd'hui et la suivante sera calculée. Si c'était un autre jour, indiquez-le dans le panneau DEC Deepal.",
      "itv_registered": "ITV enregistrée.",
      "itv_failed": "L'ITV n'a pas pu être enregistrée.",
      "insurance_last_day": "Assurance : dernier jour",
      "insurance_cancel": "Assurance : {days} pour résilier",
      "to_cancel": "{days} pour résilier",
      "renews_on": "Se renouvelle le {date}",
      "days_to_renewal": "jours avant le renouvellement",
      "days_to_cancel": "jours pour résilier",
      "cancel_passed": "délai de résiliation dépassé",
      "renewal_text": "Renouvellement le {renewal}. Pour ne pas renouveler, il faut prévenir avant le {deadline} ({days} jours plus tôt).",
      "policy": "Contrat",
      "company": "Compagnie",
      "policy_number": "Numéro de contrat",
      "kind": "Type",
      "assistance": "Assistance",
      "kind_third_party": "Au tiers",
      "kind_third_party_plus": "Tiers étendu",
      "kind_comprehensive_excess": "Tous risques avec franchise",
      "kind_comprehensive": "Tous risques sans franchise",
      "wheel_heat": "Volant chauffant",
      "seat_vent_driver": "Ventilation siège conducteur",
      "seat_heat_driver": "Chauffage siège conducteur",
      "seat_vent_passenger": "Ventilation siège passager",
      "seat_heat_passenger": "Chauffage siège passager",
      "temp_down": "Baisser la température",
      "temp_up": "Augmenter la température",
      "climate_on": "Climatisation allumée",
      "climate_off": "Climatisation éteinte",
      "inside": "Intérieur {value}",
      "humidity": "Humidité {value}",
      "fan": "Ventilateur {value}",
      "recirculating": "Recyclage",
      "outside_air": "Air extérieur",
      "number_copied": "Numéro copié : {number}",
      "trunk_manual": "Ce véhicule n'a pas de hayon électrique : le coffre s'ouvre et se ferme à la main."
    },
    "nl": {
      "card_description": "Je Deepal in één oogopslag: aanzicht van de auto, batterij, comfort en snelle acties.",
      "top_view": "Bovenaanzicht",
      "top_card_description": "Je Deepal van bovenaf: portieren, motorkap en kofferbak in één oogopslag, met batterij, comfort en snelle acties.",
      "orientation": "Oriëntatie van de auto",
      "orientation_horizontal": "Horizontaal (liggend)",
      "orientation_vertical": "Verticaal (staand)",
      "car": "Auto",
      "not_found": "Ik kan de auto niet vinden. Kies er een in de kaartinstellingen.",
      "refresh": "Voertuiggegevens vernieuwen",
      "updated": "Bijgewerkt: {when}",
      "today": "vandaag, {time}",
      "yesterday": "gisteren, {time}",
      "comfort": "Comfort",
      "charge_title": "Laden",
      "charge_open": "Laadgegevens tonen",
      "refresh_short": "Vernieuwen",
      "charging_status": "Laadt · {type}",
      "charge_full_at": "vol om {time}",
      "charge_plugged": "Aangesloten · laadt niet",
      "charge_unplugged": "Niet aangesloten",
      "range_left": "{value} actieradius",
      "time_left": "Resterende tijd",
      "ends_at": "Klaar rond {time}",
      "current": "Stroom",
      "current_ac": "Wisselstroom",
      "current_dc": "Gelijkstroom",
      "no_charge": "Geen laadsessie bezig",
      "connector": "Stekker",
      "connector_ac": "AC · Type 2",
      "plugged": "Aangesloten",
      "this_charge": "Deze laadsessie",
      "since": "Sinds {time} · {duration}",
      "last_charge": "Laatste laadsessie",
      "from_to": "Van {from}% naar {to}%",
      "duration_hm": "{h} u {m} min",
      "duration_m": "{m} min",
      "lock": "Slot",
      "trunk": "Kofferbak",
      "vent": "Ventileren",
      "locate": "Voertuig zoeken",
      "others": "Meer",
      "on": "Aan",
      "off": "Uit",
      "seats": "Stoelen",
      "unlocked": "Ontgrendeld",
      "locked": "Vergrendeld",
      "trunk_open": "Open",
      "trunk_closed": "Dicht",
      "venting": "Ventileert",
      "windows_open": "Open",
      "windows_closed": "Dicht",
      "lights_horn": "Lichten en claxon",
      "others_default": "Handleiding en documenten",
      "day": "1 dag",
      "days": "{count} dagen",
      "close": "Sluiten",
      "cancel": "Annuleren",
      "understood": "Begrepen",
      "command_failed": "De opdracht kon niet naar de auto worden verstuurd.",
      "no_pin": "Schakel pincodebediening in via het DEC Deepal-paneel (tabblad Instellingen) om deze knop te gebruiken.",
      "pin_confirm": "De opdracht wordt met je opgeslagen pincode naar {name} verstuurd. De auto kan er een paar seconden over doen.",
      "lock_q": "Portieren vergrendelen?",
      "lock_do": "Vergrendelen",
      "unlock_q": "Portieren ontgrendelen?",
      "unlock_do": "Ontgrendelen",
      "trunk_close_q": "Kofferbak sluiten?",
      "trunk_open_q": "Kofferbak openen?",
      "open_do": "Openen",
      "windows_close_q": "Ramen sluiten?",
      "vent_q": "Ramen op een kier zetten om te ventileren?",
      "lights": "Lichten",
      "flash": "Knipperen",
      "horn": "Claxon",
      "honk": "Claxonneren",
      "both": "Beide",
      "manual": "Handleiding",
      "open_pdf": "Pdf openen",
      "not_enabled": "Niet ingeschakeld",
      "maintenance": "Onderhoud",
      "itv": "ITV",
      "insurance": "Verzekering",
      "no_maintenance": "Onderhoud is voor deze auto niet ingeschakeld. Schakel het in via het DEC Deepal-paneel → Voertuigen.",
      "no_itv": "De ITV is voor deze auto niet ingeschakeld. Schakel hem in via het DEC Deepal-paneel → Voertuigen.",
      "no_insurance": "De verzekering is voor deze auto niet ingeschakeld. Schakel ze in via het DEC Deepal-paneel → Voertuigen.",
      "ordinal": "{number}e",
      "nth_service": "{ordinal} beurt",
      "overdue_mark": " · verlopen",
      "service_overdue": "Onderhoud verlopen",
      "service_in": "Onderhoud over {value}",
      "days_left": "dagen te gaan",
      "days_late": "dagen te laat",
      "km_left": "km te gaan",
      "km_late": "km te laat",
      "service_planned": "Gepland op {date} of bij {km} km, wat het eerst komt.",
      "includes": "Wat erbij hoort",
      "history": "Geschiedenis",
      "history_item": "{ordinal} beurt · {date} · {km} km",
      "register_service": "Onderhoud registreren",
      "register_service_q": "{ordinal} beurt registreren?",
      "register_service_text": "Er wordt genoteerd dat {name} vandaag een beurt heeft gehad{odometer}, en het tellen voor de volgende begint. Was het op een andere dag, registreer het dan via het DEC Deepal-paneel.",
      "with_odometer": ", bij {value}",
      "register": "Registreren",
      "service_registered": "Onderhoud geregistreerd.",
      "service_failed": "Het onderhoud kon niet worden geregistreerd.",
      "itv_overdue": "ITV verlopen",
      "itv_last_day": "ITV: laatste dag",
      "itv_in": "ITV over {days}",
      "left": "Nog {days}",
      "overdue": "Verlopen",
      "last_day": "Laatste dag",
      "next_itv": "Volgende ITV",
      "due_date": "uiterste datum",
      "itv_rule": "Eerste ITV (periodieke keuring) 4 jaar na de registratie. Daarna om de 2 jaar tot de auto 10 jaar is, en vanaf dan elk jaar.",
      "details": "Details",
      "registration": "Registratie",
      "last_itv": "Laatste ITV",
      "none_yet": "Nog geen",
      "register_itv": "Doorstane ITV registreren",
      "register_itv_q": "ITV registreren?",
      "register_itv_text": "Er wordt genoteerd dat {name} vandaag de ITV heeft doorstaan en de volgende wordt berekend. Was het op een andere dag, vul het dan in via het DEC Deepal-paneel.",
      "itv_registered": "ITV geregistreerd.",
      "itv_failed": "De ITV kon niet worden geregistreerd.",
      "insurance_last_day": "Verzekering: laatste dag",
      "insurance_cancel": "Verzekering: {days} om op te zeggen",
      "to_cancel": "{days} om op te zeggen",
      "renews_on": "Wordt verlengd op {date}",
      "days_to_renewal": "dagen tot verlenging",
      "days_to_cancel": "dagen om op te zeggen",
      "cancel_passed": "opzegtermijn verstreken",
      "renewal_text": "Verlenging op {renewal}. Om niet te verlengen moet je vóór {deadline} opzeggen ({days} dagen eerder).",
      "policy": "Polis",
      "company": "Maatschappij",
      "policy_number": "Polisnummer",
      "kind": "Soort",
      "assistance": "Pechhulp",
      "kind_third_party": "WA",
      "kind_third_party_plus": "WA beperkt casco",
      "kind_comprehensive_excess": "Allrisk met eigen risico",
      "kind_comprehensive": "Allrisk zonder eigen risico",
      "wheel_heat": "Stuurverwarming",
      "seat_vent_driver": "Stoelventilatie bestuurder",
      "seat_heat_driver": "Stoelverwarming bestuurder",
      "seat_vent_passenger": "Stoelventilatie passagier",
      "seat_heat_passenger": "Stoelverwarming passagier",
      "temp_down": "Temperatuur lager",
      "temp_up": "Temperatuur hoger",
      "climate_on": "Klimaatregeling aan",
      "climate_off": "Klimaatregeling uit",
      "inside": "Binnen {value}",
      "humidity": "Vochtigheid {value}",
      "fan": "Ventilator {value}",
      "recirculating": "Recirculatie",
      "outside_air": "Buitenlucht",
      "number_copied": "Nummer gekopieerd: {number}",
      "trunk_manual": "Dit voertuig heeft geen elektrische achterklep: de kofferbak gaat met de hand open en dicht."
    },
    "nb": {
      "card_description": "Din Deepal på et øyeblikk: bilvisning, batteri, komfort og hurtighandlinger.",
      "top_view": "Sett ovenfra",
      "top_card_description": "Din Deepal sett ovenfra: dører, panser og bagasjerom på et øyeblikk, med batteri, komfort og hurtighandlinger.",
      "orientation": "Bilens retning",
      "orientation_horizontal": "Vannrett (liggende)",
      "orientation_vertical": "Loddrett (stående)",
      "car": "Bil",
      "not_found": "Jeg finner ikke bilen. Velg en i kortinnstillingene.",
      "refresh": "Oppdater kjøretøydata",
      "updated": "Oppdatert: {when}",
      "today": "i dag, {time}",
      "yesterday": "i går, {time}",
      "comfort": "Komfort",
      "charge_title": "Lading",
      "charge_open": "Vis ladedetaljer",
      "refresh_short": "Oppdater",
      "charging_status": "Lader · {type}",
      "charge_full_at": "full kl. {time}",
      "charge_plugged": "Tilkoblet · lader ikke",
      "charge_unplugged": "Ikke tilkoblet",
      "range_left": "{value} rekkevidde",
      "time_left": "Gjenstående tid",
      "ends_at": "Ferdig rundt kl. {time}",
      "current": "Strøm",
      "current_ac": "Vekselstrøm",
      "current_dc": "Likestrøm",
      "no_charge": "Ingen lading pågår",
      "connector": "Kontakt",
      "connector_ac": "AC · Type 2",
      "plugged": "Tilkoblet",
      "this_charge": "Denne ladingen",
      "since": "Siden kl. {time} · {duration}",
      "last_charge": "Siste lading",
      "from_to": "Fra {from} % til {to} %",
      "duration_hm": "{h} t {m} min",
      "duration_m": "{m} min",
      "lock": "Lås",
      "trunk": "Bagasjerom",
      "vent": "Luft",
      "locate": "Finn kjøretøyet",
      "others": "Mer",
      "on": "På",
      "off": "Av",
      "seats": "Seter",
      "unlocked": "Ulåst",
      "locked": "Låst",
      "trunk_open": "Åpent",
      "trunk_closed": "Lukket",
      "venting": "Lufter",
      "windows_open": "Åpne",
      "windows_closed": "Lukket",
      "lights_horn": "Lys og horn",
      "others_default": "Håndbok og dokumenter",
      "day": "1 dag",
      "days": "{count} dager",
      "close": "Lukk",
      "cancel": "Avbryt",
      "understood": "Forstått",
      "command_failed": "Kommandoen kunne ikke sendes til bilen.",
      "no_pin": "Aktiver PIN-styring i DEC Deepal-panelet (fanen Innstillinger) for å bruke denne knappen.",
      "pin_confirm": "Kommandoen sendes til {name} med den lagrede PIN-koden din. Bilen kan bruke noen sekunder på å svare.",
      "lock_q": "Låse dørene?",
      "lock_do": "Lås",
      "unlock_q": "Låse opp dørene?",
      "unlock_do": "Lås opp",
      "trunk_close_q": "Lukke bagasjerommet?",
      "trunk_open_q": "Åpne bagasjerommet?",
      "open_do": "Åpne",
      "windows_close_q": "Lukke vinduene?",
      "vent_q": "Åpne vinduene på gløtt for å lufte?",
      "lights": "Lys",
      "flash": "Blink",
      "horn": "Horn",
      "honk": "Tut",
      "both": "Begge",
      "manual": "Håndbok",
      "open_pdf": "Åpne PDF",
      "not_enabled": "Ikke aktivert",
      "maintenance": "Service",
      "itv": "ITV",
      "insurance": "Forsikring",
      "no_maintenance": "Service er ikke aktivert for denne bilen. Aktiver det i DEC Deepal-panelet → Kjøretøy.",
      "no_itv": "ITV er ikke aktivert for denne bilen. Aktiver det i DEC Deepal-panelet → Kjøretøy.",
      "no_insurance": "Forsikring er ikke aktivert for denne bilen. Aktiver det i DEC Deepal-panelet → Kjøretøy.",
      "ordinal": "{number}.",
      "nth_service": "{ordinal} service",
      "overdue_mark": " · forfalt",
      "service_overdue": "Service forfalt",
      "service_in": "Service om {value}",
      "days_left": "dager igjen",
      "days_late": "dager på overtid",
      "km_left": "km igjen",
      "km_late": "km på overtid",
      "service_planned": "Forfaller {date} eller ved {km} km, det som kommer først.",
      "includes": "Hva den omfatter",
      "history": "Historikk",
      "history_item": "{ordinal} service · {date} · {km} km",
      "register_service": "Registrer service",
      "register_service_q": "Registrere {ordinal} service?",
      "register_service_text": "Det blir notert at {name} var på service i dag{odometer}, og tellingen mot den neste starter. Var det en annen dag, registrer det fra DEC Deepal-panelet.",
      "with_odometer": ", ved {value}",
      "register": "Registrer",
      "service_registered": "Service registrert.",
      "service_failed": "Servicen kunne ikke registreres.",
      "itv_overdue": "ITV forfalt",
      "itv_last_day": "ITV: siste dag",
      "itv_in": "ITV om {days}",
      "left": "{days} igjen",
      "overdue": "Forfalt",
      "last_day": "Siste dag",
      "next_itv": "Neste ITV",
      "due_date": "frist",
      "itv_rule": "Første ITV (periodisk kjøretøykontroll) 4 år etter registrering. Deretter hvert 2. år til bilen er 10 år, og hvert år etter det.",
      "details": "Detaljer",
      "registration": "Registrering",
      "last_itv": "Siste ITV",
      "none_yet": "Ingen ennå",
      "register_itv": "Registrer bestått ITV",
      "register_itv_q": "Registrere ITV?",
      "register_itv_text": "Det blir notert at {name} besto ITV i dag, og den neste beregnes. Var det en annen dag, legg det inn i DEC Deepal-panelet.",
      "itv_registered": "ITV registrert.",
      "itv_failed": "ITV kunne ikke registreres.",
      "insurance_last_day": "Forsikring: siste dag",
      "insurance_cancel": "Forsikring: {days} til å si opp",
      "to_cancel": "{days} til å si opp",
      "renews_on": "Fornyes {date}",
      "days_to_renewal": "dager til fornyelse",
      "days_to_cancel": "dager til å si opp",
      "cancel_passed": "oppsigelsesfristen er ute",
      "renewal_text": "Fornyelse {renewal}. For ikke å fornye må du gi beskjed før {deadline} ({days} dager før).",
      "policy": "Polise",
      "company": "Selskap",
      "policy_number": "Polisenummer",
      "kind": "Type",
      "assistance": "Veihjelp",
      "kind_third_party": "Ansvar",
      "kind_third_party_plus": "Delkasko",
      "kind_comprehensive_excess": "Kasko med egenandel",
      "kind_comprehensive": "Kasko uten egenandel",
      "wheel_heat": "Rattvarme",
      "seat_vent_driver": "Seteventilasjon fører",
      "seat_heat_driver": "Setevarme fører",
      "seat_vent_passenger": "Seteventilasjon passasjer",
      "seat_heat_passenger": "Setevarme passasjer",
      "temp_down": "Senk temperaturen",
      "temp_up": "Øk temperaturen",
      "climate_on": "Klimaanlegg på",
      "climate_off": "Klimaanlegg av",
      "inside": "Inne {value}",
      "humidity": "Fuktighet {value}",
      "fan": "Vifte {value}",
      "recirculating": "Resirkulering",
      "outside_air": "Uteluft",
      "number_copied": "Nummer kopiert: {number}",
      "trunk_manual": "Dette kjøretøyet har ikke elektrisk bakluke: bagasjerommet åpnes og lukkes for hånd."
    },
    "da": {
      "card_description": "Din Deepal med et enkelt blik: bilvisning, batteri, komfort og hurtige handlinger.",
      "top_view": "Set ovenfra",
      "top_card_description": "Din Deepal set ovenfra: døre, motorhjelm og bagagerum med et enkelt blik, med batteri, komfort og hurtige handlinger.",
      "orientation": "Bilens retning",
      "orientation_horizontal": "Vandret (liggende)",
      "orientation_vertical": "Lodret (stående)",
      "car": "Bil",
      "not_found": "Jeg kan ikke finde bilen. Vælg en i kortets indstillinger.",
      "refresh": "Opdater køretøjsdata",
      "updated": "Opdateret: {when}",
      "today": "i dag, {time}",
      "yesterday": "i går, {time}",
      "comfort": "Komfort",
      "charge_title": "Opladning",
      "charge_open": "Vis opladningsdetaljer",
      "refresh_short": "Opdater",
      "charging_status": "Oplader · {type}",
      "charge_full_at": "fuld kl. {time}",
      "charge_plugged": "Tilsluttet · oplader ikke",
      "charge_unplugged": "Ikke tilsluttet",
      "range_left": "{value} rækkevidde",
      "time_left": "Resterende tid",
      "ends_at": "Færdig omkring kl. {time}",
      "current": "Strøm",
      "current_ac": "Vekselstrøm",
      "current_dc": "Jævnstrøm",
      "no_charge": "Ingen opladning i gang",
      "connector": "Stik",
      "connector_ac": "AC · Type 2",
      "plugged": "Tilsluttet",
      "this_charge": "Denne opladning",
      "since": "Siden kl. {time} · {duration}",
      "last_charge": "Seneste opladning",
      "from_to": "Fra {from} % til {to} %",
      "duration_hm": "{h} t {m} min",
      "duration_m": "{m} min",
      "lock": "Lås",
      "trunk": "Bagagerum",
      "vent": "Luft ud",
      "locate": "Find køretøjet",
      "others": "Mere",
      "on": "Til",
      "off": "Fra",
      "seats": "Sæder",
      "unlocked": "Ulåst",
      "locked": "Låst",
      "trunk_open": "Åbent",
      "trunk_closed": "Lukket",
      "venting": "Lufter ud",
      "windows_open": "Åbne",
      "windows_closed": "Lukket",
      "lights_horn": "Lygter og horn",
      "others_default": "Instruktionsbog og dokumenter",
      "day": "1 dag",
      "days": "{count} dage",
      "close": "Luk",
      "cancel": "Annuller",
      "understood": "Forstået",
      "command_failed": "Kommandoen kunne ikke sendes til bilen.",
      "no_pin": "Aktivér pinkodestyring i DEC Deepal-panelet (fanen Indstillinger) for at bruge denne knap.",
      "pin_confirm": "Kommandoen sendes til {name} med din gemte pinkode. Bilen kan være et par sekunder om at svare.",
      "lock_q": "Lås dørene?",
      "lock_do": "Lås",
      "unlock_q": "Lås dørene op?",
      "unlock_do": "Lås op",
      "trunk_close_q": "Luk bagagerummet?",
      "trunk_open_q": "Åbn bagagerummet?",
      "open_do": "Åbn",
      "windows_close_q": "Luk ruderne?",
      "vent_q": "Åbn ruderne på klem for at lufte ud?",
      "lights": "Lygter",
      "flash": "Blink",
      "horn": "Horn",
      "honk": "Dyt",
      "both": "Begge",
      "manual": "Instruktionsbog",
      "open_pdf": "Åbn PDF",
      "not_enabled": "Ikke aktiveret",
      "maintenance": "Service",
      "itv": "ITV",
      "insurance": "Forsikring",
      "no_maintenance": "Service er ikke aktiveret for denne bil. Aktivér det i DEC Deepal-panelet → Køretøjer.",
      "no_itv": "ITV er ikke aktiveret for denne bil. Aktivér det i DEC Deepal-panelet → Køretøjer.",
      "no_insurance": "Forsikring er ikke aktiveret for denne bil. Aktivér det i DEC Deepal-panelet → Køretøjer.",
      "ordinal": "{number}.",
      "nth_service": "{ordinal} service",
      "overdue_mark": " · overskredet",
      "service_overdue": "Service overskredet",
      "service_in": "Service om {value}",
      "days_left": "dage tilbage",
      "days_late": "dage over tid",
      "km_left": "km tilbage",
      "km_late": "km over",
      "service_planned": "Forfalder {date} eller ved {km} km, alt efter hvad der kommer først.",
      "includes": "Hvad den omfatter",
      "history": "Historik",
      "history_item": "{ordinal} service · {date} · {km} km",
      "register_service": "Registrér service",
      "register_service_q": "Registrér {ordinal} service?",
      "register_service_text": "Det bliver noteret, at {name} var til service i dag{odometer}, og tællingen mod den næste starter. Var det en anden dag, så registrér det fra DEC Deepal-panelet.",
      "with_odometer": ", ved {value}",
      "register": "Registrér",
      "service_registered": "Service registreret.",
      "service_failed": "Servicen kunne ikke registreres.",
      "itv_overdue": "ITV overskredet",
      "itv_last_day": "ITV: sidste dag",
      "itv_in": "ITV om {days}",
      "left": "{days} tilbage",
      "overdue": "Overskredet",
      "last_day": "Sidste dag",
      "next_itv": "Næste ITV",
      "due_date": "frist",
      "itv_rule": "Første ITV (periodisk syn) 4 år efter registreringen. Derefter hvert 2. år, til bilen er 10 år, og derefter hvert år.",
      "details": "Detaljer",
      "registration": "Registrering",
      "last_itv": "Seneste ITV",
      "none_yet": "Ingen endnu",
      "register_itv": "Registrér bestået ITV",
      "register_itv_q": "Registrér ITV?",
      "register_itv_text": "Det bliver noteret, at {name} bestod ITV i dag, og det næste beregnes. Var det en anden dag, så angiv det i DEC Deepal-panelet.",
      "itv_registered": "ITV registreret.",
      "itv_failed": "ITV kunne ikke registreres.",
      "insurance_last_day": "Forsikring: sidste dag",
      "insurance_cancel": "Forsikring: {days} til at opsige",
      "to_cancel": "{days} til at opsige",
      "renews_on": "Fornyes {date}",
      "days_to_renewal": "dage til fornyelse",
      "days_to_cancel": "dage til at opsige",
      "cancel_passed": "opsigelsesfristen er overskredet",
      "renewal_text": "Fornyelse {renewal}. For ikke at forny skal du give besked inden {deadline} ({days} dage før).",
      "policy": "Police",
      "company": "Selskab",
      "policy_number": "Policenummer",
      "kind": "Type",
      "assistance": "Vejhjælp",
      "kind_third_party": "Ansvar",
      "kind_third_party_plus": "Udvidet ansvar",
      "kind_comprehensive_excess": "Kasko med selvrisiko",
      "kind_comprehensive": "Kasko uden selvrisiko",
      "wheel_heat": "Ratvarme",
      "seat_vent_driver": "Sædeventilation fører",
      "seat_heat_driver": "Sædevarme fører",
      "seat_vent_passenger": "Sædeventilation passager",
      "seat_heat_passenger": "Sædevarme passager",
      "temp_down": "Sænk temperaturen",
      "temp_up": "Hæv temperaturen",
      "climate_on": "Klimaanlæg tændt",
      "climate_off": "Klimaanlæg slukket",
      "inside": "Inde {value}",
      "humidity": "Fugtighed {value}",
      "fan": "Blæser {value}",
      "recirculating": "Recirkulation",
      "outside_air": "Udeluft",
      "number_copied": "Nummer kopieret: {number}",
      "trunk_manual": "Dette køretøj har ikke elektrisk bagklap: bagagerummet åbnes og lukkes med hånden."
    },
    "el": {
      "card_description": "Το Deepal σας με μια ματιά: όψη αυτοκινήτου, μπαταρία, άνεση και γρήγορες ενέργειες.",
      "top_view": "Κάτοψη",
      "top_card_description": "Το Deepal σας από ψηλά: πόρτες, καπό και πορτμπαγκάζ με μια ματιά, με μπαταρία, άνεση και γρήγορες ενέργειες.",
      "orientation": "Προσανατολισμός αυτοκινήτου",
      "orientation_horizontal": "Οριζόντια (ξαπλωτό)",
      "orientation_vertical": "Κάθετα (όρθιο)",
      "car": "Αυτοκίνητο",
      "not_found": "Δεν βρίσκω το αυτοκίνητο. Επιλέξτε ένα στις ρυθμίσεις της κάρτας.",
      "refresh": "Ανανέωση δεδομένων οχήματος",
      "updated": "Ενημερώθηκε: {when}",
      "today": "σήμερα, {time}",
      "yesterday": "χθες, {time}",
      "comfort": "Άνεση",
      "charge_title": "Φόρτιση",
      "charge_open": "Προβολή της φόρτισης",
      "refresh_short": "Ανανέωση",
      "charging_status": "Φορτίζει · {type}",
      "charge_full_at": "γεμάτη στις {time}",
      "charge_plugged": "Συνδεδεμένο · δεν φορτίζει",
      "charge_unplugged": "Χωρίς σύνδεση",
      "range_left": "{value} αυτονομία",
      "time_left": "Υπολειπόμενος χρόνος",
      "ends_at": "Τελειώνει γύρω στις {time}",
      "current": "Ρεύμα",
      "current_ac": "Εναλλασσόμενο ρεύμα",
      "current_dc": "Συνεχές ρεύμα",
      "no_charge": "Καμία φόρτιση σε εξέλιξη",
      "connector": "Φις",
      "connector_ac": "AC · Τύπου 2",
      "plugged": "Συνδεδεμένο",
      "this_charge": "Αυτή η φόρτιση",
      "since": "Από τις {time} · {duration}",
      "last_charge": "Τελευταία φόρτιση",
      "from_to": "Από {from}% σε {to}%",
      "duration_hm": "{h} ώ {m} λ",
      "duration_m": "{m} λ",
      "lock": "Κλειδαριά",
      "trunk": "Πορτμπαγκάζ",
      "vent": "Αερισμός",
      "locate": "Εντοπισμός οχήματος",
      "others": "Περισσότερα",
      "on": "Ανοιχτό",
      "off": "Κλειστό",
      "seats": "Καθίσματα",
      "unlocked": "Ξεκλείδωτο",
      "locked": "Κλειδωμένο",
      "trunk_open": "Ανοιχτό",
      "trunk_closed": "Κλειστό",
      "venting": "Αερισμός",
      "windows_open": "Ανοιχτά",
      "windows_closed": "Κλειστά",
      "lights_horn": "Φώτα και κόρνα",
      "others_default": "Εγχειρίδιο και έγγραφα",
      "day": "1 ημέρα",
      "days": "{count} ημέρες",
      "close": "Κλείσιμο",
      "cancel": "Ακύρωση",
      "understood": "Κατάλαβα",
      "command_failed": "Η εντολή δεν μπόρεσε να σταλεί στο αυτοκίνητο.",
      "no_pin": "Ενεργοποιήστε τον έλεγχο με PIN στον πίνακα DEC Deepal (καρτέλα Ρυθμίσεις) για να χρησιμοποιήσετε αυτό το κουμπί.",
      "pin_confirm": "Η εντολή θα σταλεί στο {name} με το αποθηκευμένο PIN σας. Το αυτοκίνητο μπορεί να χρειαστεί λίγα δευτερόλεπτα για να απαντήσει.",
      "lock_q": "Κλείδωμα των θυρών;",
      "lock_do": "Κλείδωμα",
      "unlock_q": "Ξεκλείδωμα των θυρών;",
      "unlock_do": "Ξεκλείδωμα",
      "trunk_close_q": "Κλείσιμο του πορτμπαγκάζ;",
      "trunk_open_q": "Άνοιγμα του πορτμπαγκάζ;",
      "open_do": "Άνοιγμα",
      "windows_close_q": "Κλείσιμο των παραθύρων;",
      "vent_q": "Να ανοίξουν λίγο τα παράθυρα για αερισμό;",
      "lights": "Φώτα",
      "flash": "Αναβόσβημα",
      "horn": "Κόρνα",
      "honk": "Κορνάρισμα",
      "both": "Και τα δύο",
      "manual": "Εγχειρίδιο",
      "open_pdf": "Άνοιγμα PDF",
      "not_enabled": "Μη ενεργοποιημένο",
      "maintenance": "Σέρβις",
      "itv": "ITV",
      "insurance": "Ασφάλεια",
      "no_maintenance": "Το σέρβις δεν είναι ενεργοποιημένο για αυτό το αυτοκίνητο. Ενεργοποιήστε το στον πίνακα DEC Deepal → Οχήματα.",
      "no_itv": "Το ITV δεν είναι ενεργοποιημένο για αυτό το αυτοκίνητο. Ενεργοποιήστε το στον πίνακα DEC Deepal → Οχήματα.",
      "no_insurance": "Η ασφάλεια δεν είναι ενεργοποιημένη για αυτό το αυτοκίνητο. Ενεργοποιήστε τη στον πίνακα DEC Deepal → Οχήματα.",
      "ordinal": "{number}ο",
      "nth_service": "{ordinal} σέρβις",
      "overdue_mark": " · σε καθυστέρηση",
      "service_overdue": "Σέρβις σε καθυστέρηση",
      "service_in": "Σέρβις σε {value}",
      "days_left": "ημέρες απομένουν",
      "days_late": "ημέρες καθυστέρησης",
      "km_left": "km απομένουν",
      "km_late": "km καθυστέρησης",
      "service_planned": "Προγραμματισμένο για {date} ή στα {km} km, όποιο έρθει πρώτο.",
      "includes": "Τι περιλαμβάνει",
      "history": "Ιστορικό",
      "history_item": "{ordinal} σέρβις · {date} · {km} km",
      "register_service": "Καταχώριση σέρβις",
      "register_service_q": "Καταχώριση του {ordinal} σέρβις;",
      "register_service_text": "Θα σημειωθεί ότι το {name} έκανε σέρβις σήμερα{odometer} και θα αρχίσει η μέτρηση για το επόμενο. Αν έγινε άλλη ημέρα, καταχωρίστε το από τον πίνακα DEC Deepal.",
      "with_odometer": ", στα {value}",
      "register": "Καταχώριση",
      "service_registered": "Το σέρβις καταχωρίστηκε.",
      "service_failed": "Το σέρβις δεν μπόρεσε να καταχωριστεί.",
      "itv_overdue": "Το ITV έχει λήξει",
      "itv_last_day": "ITV: τελευταία ημέρα",
      "itv_in": "ITV σε {days}",
      "left": "Απομένουν {days}",
      "overdue": "Έχει λήξει",
      "last_day": "Τελευταία ημέρα",
      "next_itv": "Επόμενο ITV",
      "due_date": "προθεσμία",
      "itv_rule": "Πρώτο ITV (τεχνικός έλεγχος) 4 χρόνια μετά την ταξινόμηση. Έπειτα κάθε 2 χρόνια μέχρι το αυτοκίνητο να γίνει 10 ετών, και από εκεί και πέρα κάθε χρόνο.",
      "details": "Λεπτομέρειες",
      "registration": "Ταξινόμηση",
      "last_itv": "Τελευταίο ITV",
      "none_yet": "Κανένα ακόμη",
      "register_itv": "Καταχώριση ITV που πέρασε",
      "register_itv_q": "Καταχώριση του ITV;",
      "register_itv_text": "Θα σημειωθεί ότι το {name} πέρασε το ITV σήμερα και θα υπολογιστεί το επόμενο. Αν ήταν άλλη ημέρα, ορίστε το στον πίνακα DEC Deepal.",
      "itv_registered": "Το ITV καταχωρίστηκε.",
      "itv_failed": "Το ITV δεν μπόρεσε να καταχωριστεί.",
      "insurance_last_day": "Ασφάλεια: τελευταία ημέρα",
      "insurance_cancel": "Ασφάλεια: {days} για ακύρωση",
      "to_cancel": "{days} για ακύρωση",
      "renews_on": "Ανανεώνεται στις {date}",
      "days_to_renewal": "ημέρες μέχρι την ανανέωση",
      "days_to_cancel": "ημέρες για ακύρωση",
      "cancel_passed": "η προθεσμία ακύρωσης πέρασε",
      "renewal_text": "Ανανέωση στις {renewal}. Για να μην ανανεωθεί, πρέπει να ειδοποιήσετε πριν από τις {deadline} ({days} ημέρες νωρίτερα).",
      "policy": "Συμβόλαιο",
      "company": "Εταιρεία",
      "policy_number": "Αριθμός συμβολαίου",
      "kind": "Τύπος",
      "assistance": "Οδική βοήθεια",
      "kind_third_party": "Αστική ευθύνη",
      "kind_third_party_plus": "Αστική ευθύνη με επιπλέον καλύψεις",
      "kind_comprehensive_excess": "Μικτή με απαλλαγή",
      "kind_comprehensive": "Μικτή χωρίς απαλλαγή",
      "wheel_heat": "Θερμαινόμενο τιμόνι",
      "seat_vent_driver": "Αερισμός καθίσματος οδηγού",
      "seat_heat_driver": "Θέρμανση καθίσματος οδηγού",
      "seat_vent_passenger": "Αερισμός καθίσματος συνοδηγού",
      "seat_heat_passenger": "Θέρμανση καθίσματος συνοδηγού",
      "temp_down": "Μείωση θερμοκρασίας",
      "temp_up": "Αύξηση θερμοκρασίας",
      "climate_on": "Κλιματισμός ανοιχτός",
      "climate_off": "Κλιματισμός κλειστός",
      "inside": "Μέσα {value}",
      "humidity": "Υγρασία {value}",
      "fan": "Ανεμιστήρας {value}",
      "recirculating": "Ανακυκλοφορία",
      "outside_air": "Εξωτερικός αέρας",
      "number_copied": "Ο αριθμός αντιγράφηκε: {number}",
      "trunk_manual": "Αυτό το όχημα δεν έχει ηλεκτρική πόρτα χώρου αποσκευών: το πορτμπαγκάζ ανοίγει και κλείνει με το χέρι."
    },
    "sl": {
      "card_description": "Vaš Deepal na prvi pogled: pogled avtomobila, baterija, udobje in hitra dejanja.",
      "top_view": "Pogled od zgoraj",
      "top_card_description": "Vaš Deepal od zgoraj: vrata, pokrov motorja in prtljažnik na prvi pogled, z baterijo, udobjem in hitrimi dejanji.",
      "orientation": "Usmerjenost avtomobila",
      "orientation_horizontal": "Vodoravno (leže)",
      "orientation_vertical": "Navpično (pokonci)",
      "car": "Avto",
      "not_found": "Avta ne najdem. Izberite ga v nastavitvah kartice.",
      "refresh": "Osveži podatke vozila",
      "updated": "Posodobljeno: {when}",
      "today": "danes, {time}",
      "yesterday": "včeraj, {time}",
      "comfort": "Udobje",
      "charge_title": "Polnjenje",
      "charge_open": "Prikaži polnjenje",
      "refresh_short": "Osveži",
      "charging_status": "Polnjenje · {type}",
      "charge_full_at": "polna ob {time}",
      "charge_plugged": "Priklopljeno · ne polni",
      "charge_unplugged": "Ni priklopljeno",
      "range_left": "Doseg: {value}",
      "time_left": "Preostali čas",
      "ends_at": "Konec okoli {time}",
      "current": "Tok",
      "current_ac": "Izmenični tok",
      "current_dc": "Enosmerni tok",
      "no_charge": "Polnjenje ne poteka",
      "connector": "Priključek",
      "connector_ac": "AC · tip 2",
      "plugged": "Priklopljeno",
      "this_charge": "To polnjenje",
      "since": "Od {time} · {duration}",
      "last_charge": "Zadnje polnjenje",
      "from_to": "Od {from} % do {to} %",
      "duration_hm": "{h} h {m} min",
      "duration_m": "{m} min",
      "lock": "Ključavnica",
      "trunk": "Prtljažnik",
      "vent": "Prezrači",
      "locate": "Poišči vozilo",
      "others": "Več",
      "on": "Vklopljeno",
      "off": "Izklopljeno",
      "seats": "Sedeži",
      "unlocked": "Odklenjeno",
      "locked": "Zaklenjeno",
      "trunk_open": "Odprt",
      "trunk_closed": "Zaprt",
      "venting": "Prezračevanje",
      "windows_open": "Odprta",
      "windows_closed": "Zaprta",
      "lights_horn": "Luči in hupa",
      "others_default": "Priročnik in dokumenti",
      "day": "1 dan",
      "days": "{count} dni",
      "close": "Zapri",
      "cancel": "Prekliči",
      "understood": "Razumem",
      "command_failed": "Ukaza ni bilo mogoče poslati avtomobilu.",
      "no_pin": "Za uporabo tega gumba omogočite upravljanje s PIN-om na plošči DEC Deepal (zavihek Nastavitve).",
      "pin_confirm": "Ukaz bo poslan vozilu {name} z vašim shranjenim PIN-om. Avto lahko za odziv potrebuje nekaj sekund.",
      "lock_q": "Zaklenem vrata?",
      "lock_do": "Zakleni",
      "unlock_q": "Odklenem vrata?",
      "unlock_do": "Odkleni",
      "trunk_close_q": "Zaprem prtljažnik?",
      "trunk_open_q": "Odprem prtljažnik?",
      "open_do": "Odpri",
      "windows_close_q": "Zaprem okna?",
      "vent_q": "Odprem okna na režo za prezračevanje?",
      "lights": "Luči",
      "flash": "Utripni",
      "horn": "Hupa",
      "honk": "Zatrobi",
      "both": "Oboje",
      "manual": "Priročnik",
      "open_pdf": "Odpri PDF",
      "not_enabled": "Ni omogočeno",
      "maintenance": "Servis",
      "itv": "ITV",
      "insurance": "Zavarovanje",
      "no_maintenance": "Servis za ta avto ni omogočen. Omogočite ga na plošči DEC Deepal → Vozila.",
      "no_itv": "ITV za ta avto ni omogočen. Omogočite ga na plošči DEC Deepal → Vozila.",
      "no_insurance": "Zavarovanje za ta avto ni omogočeno. Omogočite ga na plošči DEC Deepal → Vozila.",
      "ordinal": "{number}.",
      "nth_service": "{ordinal} servis",
      "overdue_mark": " · zamujeno",
      "service_overdue": "Servis je zamujen",
      "service_in": "Servis čez {value}",
      "days_left": "dni še",
      "days_late": "dni zamude",
      "km_left": "km še",
      "km_late": "km čez",
      "service_planned": "Predviden {date} ali pri {km} km, kar nastopi prej.",
      "includes": "Kaj vključuje",
      "history": "Zgodovina",
      "history_item": "{ordinal} servis · {date} · {km} km",
      "register_service": "Zabeleži servis",
      "register_service_q": "Zabeležim {ordinal} servis?",
      "register_service_text": "Zabeleženo bo, da je bilo vozilo {name} danes servisirano{odometer}, in začelo se bo štetje do naslednjega. Če je bilo to drug dan, ga zabeležite na plošči DEC Deepal.",
      "with_odometer": ", pri {value}",
      "register": "Zabeleži",
      "service_registered": "Servis zabeležen.",
      "service_failed": "Servisa ni bilo mogoče zabeležiti.",
      "itv_overdue": "ITV je zamujen",
      "itv_last_day": "ITV: zadnji dan",
      "itv_in": "ITV čez {days}",
      "left": "Še {days}",
      "overdue": "Zamujeno",
      "last_day": "Zadnji dan",
      "next_itv": "Naslednji ITV",
      "due_date": "rok",
      "itv_rule": "Prvi ITV (tehnični pregled) 4 leta po registraciji. Nato vsaki 2 leti, dokler avto ni star 10 let, potem pa vsako leto.",
      "details": "Podrobnosti",
      "registration": "Registracija",
      "last_itv": "Zadnji ITV",
      "none_yet": "Še nobenega",
      "register_itv": "Zabeleži opravljen ITV",
      "register_itv_q": "Zabeležim ITV?",
      "register_itv_text": "Zabeleženo bo, da je vozilo {name} danes opravilo ITV, in izračunan bo naslednji. Če je bilo to drug dan, to vnesite na plošči DEC Deepal.",
      "itv_registered": "ITV zabeležen.",
      "itv_failed": "ITV ni bilo mogoče zabeležiti.",
      "insurance_last_day": "Zavarovanje: zadnji dan",
      "insurance_cancel": "Zavarovanje: {days} za odpoved",
      "to_cancel": "{days} za odpoved",
      "renews_on": "Podaljša se {date}",
      "days_to_renewal": "dni do podaljšanja",
      "days_to_cancel": "dni za odpoved",
      "cancel_passed": "rok za odpoved je minil",
      "renewal_text": "Podaljšanje {renewal}. Če ne želite podaljšati, morate to sporočiti pred {deadline} ({days} dni prej).",
      "policy": "Polica",
      "company": "Zavarovalnica",
      "policy_number": "Številka police",
      "kind": "Vrsta",
      "assistance": "Pomoč na cesti",
      "kind_third_party": "Avtomobilska odgovornost",
      "kind_third_party_plus": "Delni kasko",
      "kind_comprehensive_excess": "Polni kasko z odbitno franšizo",
      "kind_comprehensive": "Polni kasko brez odbitne franšize",
      "wheel_heat": "Ogrevan volan",
      "seat_vent_driver": "Prezračevanje voznikovega sedeža",
      "seat_heat_driver": "Ogrevanje voznikovega sedeža",
      "seat_vent_passenger": "Prezračevanje sovoznikovega sedeža",
      "seat_heat_passenger": "Ogrevanje sovoznikovega sedeža",
      "temp_down": "Znižaj temperaturo",
      "temp_up": "Zvišaj temperaturo",
      "climate_on": "Klima vklopljena",
      "climate_off": "Klima izklopljena",
      "inside": "Znotraj {value}",
      "humidity": "Vlažnost {value}",
      "fan": "Ventilator {value}",
      "recirculating": "Kroženje",
      "outside_air": "Zunanji zrak",
      "number_copied": "Številka kopirana: {number}",
      "trunk_manual": "To vozilo nima električnih prtljažnih vrat: prtljažnik se odpira in zapira ročno."
    }
  };

  // ── src/21_idioma.js ──────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Idioma: qué textos toca y cómo se rellenan
  // ---------------------------------------------------------------------------
  /** "pt-BR" → "pt"; un idioma prestado → el que le presta; uno sin traducir → el base. */
  const textLanguage = (language) => {
    const base = String(language || BASE_LANGUAGE).toLowerCase().split("-")[0];
    const resolved = BORROWED_LANGUAGES[base] || base;
    return TEXTS[resolved] ? resolved : BASE_LANGUAGE;
  };

  /** Texto de una clave en el idioma pedido. */
  const translate = (language, key, values) => {
    const table = TEXTS[textLanguage(language)];
    let text = key in table ? table[key] : key;
    for (const [name, value] of Object.entries(values || {})) text = text.split(`{${name}}`).join(String(value));
    return text;
  };

  const escapeHtml = (text) =>
    String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  // ── src/30_estilos.js ─────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Estilos
  // ---------------------------------------------------------------------------
  const TILE_BG = "rgba(var(--rgb-primary-text-color, 33, 33, 33), 0.05)";
  const CARD_CSS = `
    :host { display: block; }
    ha-card { overflow: hidden; }
    .hdr { display: flex; align-items: center; gap: 8px; padding: 14px 8px 4px 16px; }
    .grow { flex: 1; min-width: 0; }
    .name { font-size: 20px; line-height: 1.2; color: var(--primary-text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .upd { font-size: 12px; color: var(--secondary-text-color); margin-top: 2px; }
    button { font: inherit; color: inherit; border: 0; background: none; margin: 0; cursor: pointer; -webkit-tap-highlight-color: transparent; }
    .icon-btn { width: 40px; height: 40px; border-radius: 50%; color: var(--secondary-text-color); display: flex; align-items: center; justify-content: center; }
    .icon-btn:hover { background: ${TILE_BG}; }
    .spin ha-icon { animation: dec-spin 1s linear infinite; }
    @keyframes dec-spin { to { transform: rotate(360deg); } }
    .carbox { position: relative; overflow: hidden; aspect-ratio: ${ISOMETRIC.crop.w} / ${ISOMETRIC.crop.h}; }
    .carbox[hidden] { display: none; }
    .carbox.plain { aspect-ratio: auto; }
    .carbox.plain .car { position: static; width: 100%; }
    /* Vista planta: tumbada (morro a la izquierda) o de pie. */
    .carbox.top { aspect-ratio: ${TOP.crop.h} / ${TOP.crop.w}; }
    .carbox.top .car { transform: rotate(-90deg);
      width: ${(TOP.size / TOP.crop.h) * 100}%;
      left: ${(-TOP.crop.y / TOP.crop.h) * 100}%;
      top: ${(-TOP.crop.x / TOP.crop.w) * 100}%; }
    .carbox.top.vertical { aspect-ratio: ${TOP.crop.w} / ${TOP.crop.h}; max-width: 320px; margin: 0 auto; }
    .carbox.top.vertical .car { transform: none;
      width: ${(TOP.size / TOP.crop.w) * 100}%;
      left: ${(-TOP.crop.x / TOP.crop.w) * 100}%;
      top: ${(-TOP.crop.y / TOP.crop.h) * 100}%; }
    .car { position: absolute; max-width: none; display: block;
      width: ${(ISOMETRIC.width / ISOMETRIC.crop.w) * 100}%;
      left: ${(-ISOMETRIC.crop.x / ISOMETRIC.crop.w) * 100}%;
      top: ${(-ISOMETRIC.crop.y / ISOMETRIC.crop.h) * 100}%; }
    .energy { cursor: pointer; border-radius: 12px; outline-offset: -2px; }
    .energy:active { opacity: .7; }
    .range { display: flex; align-items: center; gap: 8px; padding: 0 16px; }
    .range .batt { --mdc-icon-size: 26px; }
    .range .km { font-size: 24px; color: var(--primary-text-color); }
    .range .charge { font-size: 14px; color: var(--secondary-text-color); display: flex; align-items: center; gap: 4px; --mdc-icon-size: 18px; }
    .bar { height: 8px; border-radius: 4px; background: ${TILE_BG}; margin: 6px 16px 14px; overflow: hidden; }
    .bar i { display: block; height: 100%; border-radius: 4px; transition: width .4s; }
    .status { display: flex; justify-content: flex-end; align-items: center; gap: 10px; padding: 0 16px 10px; min-height: 22px; --mdc-icon-size: 22px; }
    .status .ok { color: var(--success-color, #43a047); }
    .status button { padding: 0; display: flex; }
    /* 6 botones en dos filas de 3. */
    .tiles { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; padding: 0 12px 12px; }
    .tile { background: ${TILE_BG}; border-radius: 12px; padding: 10px 6px; display: flex; flex-direction: column; align-items: center; gap: 4px; text-align: center; min-height: 84px; color: var(--secondary-text-color); transition: opacity .2s, transform .1s; }
    .tile:active { transform: scale(.97); }
    .tile.on { color: var(--state-active-color, #ffc107); }
    .tile.pri { color: var(--primary-color); }
    .tile.busy { opacity: .45; pointer-events: none; }
    .tile b { font-size: 12px; font-weight: 500; color: var(--primary-text-color); }
    .tile small { font-size: 11px; color: var(--secondary-text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
    .msg { padding: 16px; color: var(--secondary-text-color); font-size: 14px; }
  `;
  const DIALOG_CSS = `
    :host { position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center; padding: 16px; box-sizing: border-box;
      background: rgba(0, 0, 0, .32); font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif); color: var(--primary-text-color); }
    .dlg { width: 100%; max-width: 440px; max-height: 100%; overflow: auto; background: var(--ha-card-background, var(--card-background-color, #fff));
      border-radius: 28px; box-shadow: 0 8px 24px rgba(0, 0, 0, .3); }
    button { font: inherit; color: inherit; border: 0; background: none; margin: 0; cursor: pointer; -webkit-tap-highlight-color: transparent; }
    .head { display: flex; align-items: center; gap: 4px; padding: 8px 8px 4px; }
    .head h2 { margin: 0; font-size: 20px; font-weight: 400; flex: 1; }
    .icon-btn { width: 40px; height: 40px; border-radius: 50%; color: var(--secondary-text-color); display: flex; align-items: center; justify-content: center; }
    .stage { position: relative; margin: 4px 12px 0; border-radius: 16px; overflow: hidden; background: ${TILE_BG};
      aspect-ratio: ${INTERIOR.crop.w} / ${INTERIOR.crop.h}; }
    .stage img { position: absolute; max-width: none;
      width: ${(INTERIOR.width / INTERIOR.crop.w) * 100}%;
      left: ${(-INTERIOR.crop.x / INTERIOR.crop.w) * 100}%;
      top: ${(-INTERIOR.crop.y / INTERIOR.crop.h) * 100}%; }
    .hot { position: absolute; transform: translate(-50%, -50%); width: 44px; height: 44px; display: flex; align-items: center; justify-content: center;
      color: #fff; --mdc-icon-size: 34px; filter: drop-shadow(0 1px 2px rgba(0, 0, 0, .65)); opacity: .38; transition: opacity .2s; }
    .hot.on { opacity: 1; }
    .hot.busy { animation: dec-pulse .8s ease-in-out infinite; pointer-events: none; }
    @keyframes dec-pulse { 50% { opacity: .25; } }
    .hot u { position: absolute; left: 82%; top: -2px; font-size: 15px; font-weight: 500; text-decoration: none; }
    .temp { display: flex; align-items: center; justify-content: center; gap: 18px; padding: 16px 12px 14px; }
    .temp b { font-size: 40px; font-weight: 400; min-width: 3.2ch; text-align: center; }
    .temp sup { font-size: 16px; color: var(--secondary-text-color); }
    .round { width: 48px; height: 48px; border-radius: 50%; background: ${TILE_BG}; display: flex; align-items: center; justify-content: center; color: var(--secondary-text-color); }
    .power { display: flex; align-items: center; justify-content: center; gap: 8px; margin: 0 12px; width: calc(100% - 24px); padding: 12px; border-radius: 12px;
      background: ${TILE_BG}; font-size: 14px; font-weight: 500; --mdc-icon-size: 20px; }
    .power ha-icon { color: var(--secondary-text-color); }
    .power.on { background: rgba(var(--rgb-primary-color, 3, 169, 244), .15); }
    .power.on ha-icon { color: var(--primary-color); }
    .power.busy { opacity: .5; pointer-events: none; }
    .info { font-size: 12px; color: var(--secondary-text-color); text-align: center; margin: 12px 12px 16px; }
    /* Ventana de carga. La vista de carga es un coche translúcido y claro:
       sobre fondo claro se oscurece para que se vea; en tema oscuro va tal cual. */
    .chg { padding: 4px 16px 6px; }
    .chg .view { position: relative; overflow: hidden; aspect-ratio: ${CHARGING.crop.w} / ${CHARGING.crop.h}; }
    .chg .view[hidden] { display: none; }
    .chg .view img { position: absolute; max-width: none;
      width: ${(CHARGING.width / CHARGING.crop.w) * 100}%;
      left: ${(-CHARGING.crop.x / CHARGING.crop.w) * 100}%;
      top: ${(-CHARGING.crop.y / CHARGING.crop.h) * 100}%;
      filter: brightness(.62) contrast(1.25); }
    .chg.dark .view img { filter: none; }
    .chg .now { font-size: 13px; font-weight: 500; display: flex; gap: 6px; align-items: center; color: var(--secondary-text-color); --mdc-icon-size: 18px; }
    .chg .now.on { color: var(--success-color, #43a047); }
    .chg .pct { display: flex; align-items: baseline; gap: 10px; margin: 6px 0; }
    .chg .pct b { font-size: 34px; font-weight: 400; }
    .chg .pct span { font-size: 14px; color: var(--secondary-text-color); }
    .chg .lvl { height: 10px; border-radius: 5px; background: ${TILE_BG}; overflow: hidden; }
    .chg .lvl i { display: block; height: 100%; border-radius: 5px; transition: width .4s; }
    .chg .lvl.on i { background-image: repeating-linear-gradient(110deg, rgba(255, 255, 255, .35) 0 8px, transparent 8px 16px); }
    .chg .stats { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 14px; }
    .chg .stats:empty { display: none; }
    .chg .st { background: ${TILE_BG}; border-radius: 12px; padding: 10px 12px; min-width: 0; }
    .chg .st.wide { grid-column: 1 / 3; }
    .chg .st .k { font-size: 12px; color: var(--secondary-text-color); display: flex; gap: 6px; align-items: center; --mdc-icon-size: 16px; }
    .chg .st .n { font-size: 19px; margin-top: 3px; }
    .chg .st .d { font-size: 12px; color: var(--secondary-text-color); min-height: 14px; }
    .three { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; padding: 8px 12px 16px; }
    /* Menú con menos de tres opciones: centradas, con el mismo ancho que en una fila de tres. */
    .three.center { display: flex; justify-content: center; }
    .three.center .tile { flex: 0 1 calc((100% - 16px) / 3); }
    /* Menú "Otros": de dos en dos, centrado si sobra uno. */
    .three.pairs { display: flex; flex-wrap: wrap; justify-content: center; }
    .three.pairs .tile { flex: 0 1 calc((100% - 8px) / 2); box-sizing: border-box; }
    .mt dl { display: grid; grid-template-columns: auto 1fr; gap: 6px 14px; margin: 0; font-size: 13px; }
    .mt dt { color: var(--secondary-text-color); }
    .mt dd { margin: 0; text-align: right; }
    .calls { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 14px; }
    .calls:empty { display: none; }
    .call span { display: flex; flex-direction: column; align-items: flex-start; line-height: 1.25; }
    .call small { font-size: 11px; font-weight: 400; opacity: .85; }
    .call { display: flex; align-items: center; justify-content: center; gap: 6px; padding: 10px; border-radius: 12px; font-size: 13px; font-weight: 500;
      text-decoration: none; color: var(--primary-color); background: rgba(var(--rgb-primary-color, 3, 169, 244), .12); --mdc-icon-size: 18px; }
    .tile { background: ${TILE_BG}; border-radius: 12px; padding: 10px 6px; display: flex; flex-direction: column; align-items: center; gap: 4px;
      text-align: center; min-height: 84px; color: var(--secondary-text-color); }
    .tile:active { transform: scale(.97); }
    .tile b { font-size: 12px; font-weight: 500; color: var(--primary-text-color); }
    .tile small { font-size: 11px; color: var(--secondary-text-color); }
    .confirm { padding: 20px 24px 8px; }
    .confirm h2 { margin: 0 0 10px; font-size: 22px; font-weight: 400; }
    .confirm p { margin: 0; font-size: 14px; color: var(--secondary-text-color); line-height: 1.5; }
    .btns { display: flex; justify-content: flex-end; gap: 8px; padding: 14px 16px 16px; }
    .tb { font-size: 14px; font-weight: 500; color: var(--primary-color); padding: 10px 14px; border-radius: 20px; }
    .tb.fill { background: var(--primary-color); color: var(--text-primary-color, #fff); }
    a.tile { text-decoration: none; box-sizing: border-box; }
    .mt { padding: 0 20px 4px; }
    .mt .next { font-size: 15px; font-weight: 500; margin: 4px 0 10px; display: flex; align-items: center; gap: 8px; --mdc-icon-size: 22px; }
    .mt .two { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
    .mt .stat { background: ${TILE_BG}; border-radius: 12px; padding: 10px 12px; }
    .mt .stat b { display: block; font-size: 24px; font-weight: 400; }
    .mt .stat small, .mt .due { font-size: 12px; color: var(--secondary-text-color); }
    .mt .due { margin: 8px 0 0; }
    .mt h3 { font-size: 13px; font-weight: 500; margin: 16px 0 6px; }
    .mt ul { margin: 0; padding-left: 18px; font-size: 13px; line-height: 1.5; color: var(--secondary-text-color); }
  `;

  // ── src/40_dialogo.js ─────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Ventana emergente mínima (se cuelga de <body> para quedar por encima)
  // ---------------------------------------------------------------------------
  function openDialog(html, onAction) {
    const host = document.createElement("div");
    const root = host.attachShadow({ mode: "open" });
    root.innerHTML = `<style>${DIALOG_CSS}</style><div class="dlg" role="dialog" aria-modal="true">${html}</div>`;
    const close = () => {
      document.removeEventListener("keydown", onKey);
      host.remove();
      if (dialog.onClose) dialog.onClose();
    };
    const onKey = (event) => event.key === "Escape" && close();
    document.addEventListener("keydown", onKey);
    host.addEventListener("click", (event) => {
      const path = event.composedPath();
      if (path[0] === host) return close(); // toque en el fondo oscuro
      const target = path.find((node) => node.dataset && node.dataset.action);
      if (!target) return undefined;
      if (target.dataset.action === "close") return close();
      return onAction(target.dataset.action, target, dialog);
    });
    const dialog = { root, close, onClose: null };
    document.body.append(host);
    return dialog;
  }

  // ── src/50_tarjeta.js ─────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // La tarjeta
  // ---------------------------------------------------------------------------
  class DecDeepalCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._config = {};
      this._ids = {}; // "dominio.clave" → entity_id
      this._seen = []; // estados usados en el último pintado
      this._busy = new Set();
      this._comfort = null; // ventana de Confort abierta
      this._charge = null; // ventana de carga abierta
      this._pendingTemp = null;
      this._tempTimer = null;
      this.shadowRoot.addEventListener("click", (event) => this._onClick(event));
      // La franja de la batería hace de botón: también con Intro o Espacio.
      this.shadowRoot.addEventListener("keydown", (event) => {
        if ((event.key !== "Enter" && event.key !== " ") || !event.target.matches || !event.target.matches(".energy")) return;
        event.preventDefault();
        event.target.click();
      });
    }

    /** Qué vista del coche enseña: "isometric" (esta) o "top" (la de planta). */
    static get VIEW() {
      return "isometric";
    }

    // --- API de las tarjetas de Home Assistant --------------------------------

    static getStubConfig(hass) {
      const first = Object.values((hass && hass.entities) || {}).find((entry) => entry.platform === DOMAIN && entry.device_id);
      return { device_id: first ? first.device_id : "" };
    }

    static getConfigForm() {
      const text = (key) => translate(document.documentElement.lang, key);
      const schema = [{ name: "device_id", selector: { device: { filter: [{ integration: DOMAIN }] } } }];
      if (this.VIEW === "top") {
        const options = ["horizontal", "vertical"].map((value) => ({ value, label: text(`orientation_${value}`) }));
        schema.push({ name: "orientation", selector: { select: { mode: "dropdown", options } } });
      }
      return { schema, computeLabel: (field) => text(field.name === "orientation" ? "orientation" : "car") };
    }

    setConfig(config) {
      this._config = config || {};
      this._ids = {};
      this._built = false;
      if (this._hass) this._update();
    }

    set hass(hass) {
      this._hass = hass;
      this._update();
    }

    getCardSize() {
      return this._vertical() ? 11 : 8;
    }

    /** ¿Vista planta de pie? (solo la tarjeta de planta, y si se pide). */
    _vertical() {
      return this.constructor.VIEW === "top" && this._config.orientation === "vertical";
    }

    getGridOptions() {
      return { columns: 12, min_columns: 6, min_rows: 6 };
    }

    disconnectedCallback() {
      if (this._comfort) this._comfort.close();
      if (this._charge) this._charge.close();
    }

    // --- Entidades -------------------------------------------------------------

    _deviceId() {
      return this._config.device_id || DecDeepalCard.getStubConfig(this._hass).device_id;
    }

    _discover() {
      const deviceId = this._deviceId();
      const ids = {};
      for (const [entityId, entry] of Object.entries(this._hass.entities || {})) {
        if (entry.platform !== DOMAIN || entry.device_id !== deviceId || !entry.translation_key) continue;
        ids[`${entityId.split(".")[0]}.${entry.translation_key}`] = entityId;
      }
      this._ids = ids;
      this._registry = this._hass.entities;
      this._checkManual(deviceId);
    }

    /** Pregunta a la integración (una vez por coche): manual, ITV y testigos que no se enseñan. */
    async _checkManual(deviceId) {
      if (!deviceId || this._manualDevice === deviceId || !this._hass.callApi) return;
      this._manualDevice = deviceId;
      this._manualUrl = "";
      this._itvAvailable = true;
      try {
        const info = await this._hass.callApi("GET", `dec_deepal/manual_info/${deviceId}`);
        // La ITV solo existe en algunos países (hoy, España).
        if (this._manualDevice === deviceId) this._itvAvailable = !(info && info.itv === false);
        if (this._manualDevice === deviceId && info && Array.isArray(info.silent_warnings)) {
          this._silent = new Set(info.silent_warnings);
          this._repaint();
        }
        // Equipamiento de la versión del coche (su ficha): { porton_electrico: false, ... }.
        if (this._manualDevice === deviceId) this._features = (info && info.features) || {};
        const url = (info && info.url) || "";
        if (this._manualDevice === deviceId && /^https?:\/\//.test(url)) this._manualUrl = url;
      } catch (_error) {
        this._manualDevice = undefined; // se volverá a intentar
      }
    }

    _state(key) {
      const entityId = this._ids[key];
      return entityId ? this._hass.states[entityId] : undefined;
    }

    _value(key) {
      const state = this._state(key);
      return state && !["unknown", "unavailable"].includes(state.state) ? state.state : undefined;
    }

    _number(key) {
      const value = Number(this._value(key));
      return Number.isFinite(value) ? value : undefined;
    }

    _format(key) {
      const state = this._state(key);
      if (!state || ["unknown", "unavailable"].includes(state.state)) return undefined;
      // Estados con texto ("Desconectado"): se traducen aquí. La función de
      // Home Assistant se queda con el idioma anterior al cambiar de idioma.
      const [domain, translationKey] = key.split(".");
      const text =
        this._hass.localize &&
        this._hass.localize(`component.${DOMAIN}.entity.${domain}.${translationKey}.state.${state.state}`);
      if (text) return text;
      return this._hass.formatEntityState ? this._hass.formatEntityState(state) : state.state;
    }

    _language() {
      return (this._hass && this._hass.locale && this._hass.locale.language) || "en";
    }

    /**
     * Idioma para escribir fechas con nombre de mes: el del usuario si la
     * tarjeta está traducida a él; si no, el del texto que se enseña (así no
     * sale "Renueva el 14 de març" con el texto en español).
     */
    _dateLanguage() {
      const language = this._language();
      const shown = textLanguage(language);
      return language.toLowerCase().split("-")[0] === shown ? language : shown;
    }

    /** Texto traducido. Las claves están en la tabla TEXTS. */
    _t(key, values) {
      return translate(this._language(), key, values);
    }

    _ordinal(number) {
      return this._t("ordinal", { number });
    }

    /** Nombre del coche en negrita, para meterlo en una frase. */
    _boldName() {
      return `<b style="font-weight:500;color:var(--primary-text-color)">${escapeHtml(this._name())}</b>`;
    }

    _name() {
      const device = (this._hass.devices || {})[this._deviceId()];
      return (device && (device.name_by_user || device.name)) || "Deepal";
    }

    // --- Pintado ---------------------------------------------------------------

    _update() {
      if (!this._hass) return;
      if (this._registry !== this._hass.entities) this._discover();
      const tracked = Object.values(this._ids).map((entityId) => this._hass.states[entityId]);
      const changed = tracked.length !== this._seen.length || tracked.some((state, index) => state !== this._seen[index]);
      if (this._builtLanguage !== this._language()) this._built = false; // cambió el idioma
      // Al cambiar de idioma, los textos de Home Assistant llegan un poco
      // después que el idioma: hay que repintar cuando llegan.
      if (this._localize !== this._hass.localize) this._dirty = true;
      this._localize = this._hass.localize;
      if (!this._built) this._build();
      else if (!changed && !this._dirty) return;
      this._seen = tracked;
      this._dirty = false;
      this._paint();
      if (this._comfort) this._paintComfort();
      if (this._charge) this._paintCharge();
    }

    _build() {
      this._built = true;
      this._statusSignature = undefined;
      this._builtLanguage = this._language();
      const tile = (action) =>
        `<button class="tile" data-action="${action}"><ha-icon></ha-icon><b>${this._t(action)}</b><small></small></button>`;
      this.shadowRoot.innerHTML = `
        <style>${CARD_CSS}</style>
        <ha-card>
          <div class="hdr">
            <div class="grow"><div class="name"></div><div class="upd"></div></div>
            <button class="icon-btn" data-action="refresh" aria-label="${this._t("refresh")}"><ha-icon icon="mdi:refresh"></ha-icon></button>
          </div>
          <div class="carbox" hidden><img class="car" alt=""></div>
          <div class="msg" hidden></div>
          <div class="status"></div>
          <div class="energy" data-action="charge" role="button" tabindex="0" aria-label="${this._t("charge_open")}">
            <div class="range">
              <ha-icon class="batt"></ha-icon><span class="km"></span><span class="grow"></span>
              <span class="charge"><ha-icon></ha-icon><span></span></span>
            </div>
            <div class="bar"><i></i></div>
          </div>
          <div class="tiles">
            ${tile("comfort")}${tile("lock")}${tile("trunk")}
            ${tile("vent")}${tile("locate")}${tile("others")}
          </div>
        </ha-card>`;
    }

    _paint() {
      const $ = (selector) => this.shadowRoot.querySelector(selector);
      const found = Object.keys(this._ids).length > 0;
      $(".msg").hidden = found;
      $(".msg").textContent = found ? "" : this._t("not_found");
      $(".name").textContent = this._name();
      $(".upd").textContent = this._t("updated", { when: this._updatedText() });
      $('[data-action="refresh"]').classList.toggle("spin", this._busy.has("refresh"));

      // Imagen: la vista de esta tarjeta (isométrica o de planta) o, si el
      // coche no la tiene, la imagen DEC.
      const top = this.constructor.VIEW === "top";
      const view = this._state(top ? "image.top_view" : "image.isometric_view");
      const image = view || this._state("image.dec_photo");
      const img = $(".car");
      const src = this._imageUrl(image);
      const box = $(".carbox");
      box.hidden = !src;
      box.classList.toggle("plain", !view); // la foto DEC va sin recortar
      box.classList.toggle("top", top && Boolean(view));
      box.classList.toggle("vertical", Boolean(view) && this._vertical());
      if (src && img.getAttribute("src") !== src) img.setAttribute("src", src);

      // Batería y autonomía.
      const level = this._number("sensor.battery_level");
      const charging = this._value("binary_sensor.charging") === "on";
      const color = level === undefined ? "var(--secondary-text-color)" : level < 15 ? "var(--error-color, #db4437)" : level < 50 ? "var(--warning-color, #f9a825)" : "var(--success-color, #43a047)";
      $(".batt").setAttribute("icon", this._batteryIcon(level, charging));
      $(".batt").style.color = color;
      $(".km").textContent = this._format("sensor.range") || "—";
      $(".bar i").style.width = `${level === undefined ? 0 : Math.max(0, Math.min(100, level))}%`;
      $(".bar i").style.background = color;
      const plugged = (this._value("sensor.charge_status") || "disconnected") !== "disconnected";
      let chargeText = this._format("sensor.charge_status") || "";
      const remaining = this._value("sensor.remaining_charge_time_hhmm");
      if (charging && remaining) chargeText += ` · ${remaining} h`;
      $(".charge ha-icon").setAttribute("icon", plugged ? "mdi:power-plug" : "mdi:power-plug-off-outline");
      $(".charge span").textContent = chargeText;
      $(".charge").hidden = !chargeText;

      // Línea de estado: tic verde, o el icono de cada testigo encendido.
      // Los de vencimiento (mantenimiento, ITV, seguro) van al final y se pueden pulsar.
      // Un testigo cuenta si está encendido y la ficha del coche no lo silencia.
      const silent = this._silent || new Set(SILENT_BY_DEFAULT);
      const active = WARNINGS.filter((warning) =>
        warning.keys.some((key) => !silent.has(key.split(".")[1]) && this._value(key) === "on")
      );
      const due = DUE.map((item) => ({ ...item, level: this._dueLevel(item.key) })).filter((item) => item.level);
      const signature = `${active.map((warning) => warning.icon).join("|")}#${due.map((item) => item.action + item.level).join("|")}`;
      if (this._statusSignature !== signature) {
        this._statusSignature = signature;
        const icons = active.map((warning) => `<ha-icon icon="${warning.icon}" style="color:${warning.color}"></ha-icon>`);
        for (const item of due)
          icons.push(
            `<button data-action="${item.action}" aria-label="${this._t(item.label)}"><ha-icon icon="${item.icon}" style="color:${item.level === "overdue" ? RED : AMBER}"></ha-icon></button>`
          );
        $(".status").innerHTML = icons.length ? icons.join("") : '<ha-icon class="ok" icon="mdi:check-circle"></ha-icon>';
      }

      // Los seis botones.
      const tiles = this._tiles();
      for (const [action, data] of Object.entries(tiles)) {
        const element = $(`.tile[data-action="${action}"]`);
        element.querySelector("ha-icon").setAttribute("icon", data.icon);
        element.querySelector("small").textContent = data.text;
        element.classList.toggle("on", Boolean(data.on));
        element.classList.toggle("pri", Boolean(data.primary));
        element.classList.toggle("busy", this._busy.has(action));
      }
    }

    _tiles() {
      const climateOn = (this._value("climate.cabin_climate") || "off") !== "off";
      const comfortOn = climateOn || HOTSPOTS.some((spot) => this._spotLevel(spot) > 0);
      const climate = this._state("climate.cabin_climate");
      const target = climate && climate.attributes.temperature;
      const inside = this._format("sensor.inside_temperature");
      const comfortText = climateOn
        ? `${this._t("on")}${target != null ? ` · ${this._temp(target)} °C` : ""}`
        : `${this._t(comfortOn ? "seats" : "off")}${inside ? ` · ${inside}` : ""}`;

      const lock = this._value("lock.doors");
      const central = this._value("binary_sensor.central_locking"); // on = desbloqueado
      const unlocked = lock ? lock === "unlocked" : central === "on";
      const lockKnown = Boolean(lock || central);

      const trunkOpen = this._value("binary_sensor.trunk") === "on";
      // La persiana de ventanillas va invertida: "closed" = entreabiertas.
      const venting = this._value("cover.windows") === "closed";
      const anyWindow = ["front_left", "front_right", "rear_left", "rear_right"].some(
        (position) => this._value(`binary_sensor.window_${position}`) === "on"
      );

      return {
        // En azul solo si hay algo encendido (clima, asientos o volante).
        comfort: { icon: "mdi:sun-snowflake-variant", text: comfortText, primary: comfortOn },
        lock: {
          icon: unlocked ? "mdi:lock-open-variant" : "mdi:lock",
          text: lockKnown ? this._t(unlocked ? "unlocked" : "locked") : "—",
          on: lockKnown && unlocked,
        },
        trunk: { icon: trunkOpen ? "dec:trunk_open" : "dec:trunk_closed", text: this._t(trunkOpen ? "trunk_open" : "trunk_closed"), on: trunkOpen },
        vent: { icon: "mdi:weather-windy", text: this._t(venting ? "venting" : anyWindow ? "windows_open" : "windows_closed"), on: venting || anyWindow },
        locate: { icon: "mdi:car-search", text: this._t("lights_horn") },
        others: { icon: "mdi:dots-horizontal", text: this._othersShort() || this._t("others_default") },
      };
    }

    /** Nivel de un testigo de vencimiento: "", "soon" u "overdue". */
    _dueLevel(key) {
      return this._value(key) === "on" ? this._state(key).attributes.nivel || "soon" : "";
    }

    /** Lo más urgente de mantenimiento, ITV y seguro (primero lo vencido). */
    _othersShort() {
      const items = [
        [this._dueLevel(MAINTENANCE), this._maintenanceShort()],
        [this._dueLevel(ITV), this._itvShort()],
        [this._dueLevel(INSURANCE), this._insuranceShort()],
      ].filter(([level]) => level);
      const urgent = items.find(([level]) => level === "overdue") || items[0];
      return urgent ? urgent[1] : "";
    }

    _days(count) {
      return Math.abs(count) === 1 ? this._t("day") : this._t("days", { count: Math.abs(count) });
    }

    /** ITV en una línea. Con ``named`` lleva delante "ITV" (para el botón "Otros"). */
    _itvShort(named = true) {
      const data = (this._state(ITV) || { attributes: {} }).attributes;
      if (data.dias_restantes == null) return "";
      if (data.dias_restantes < 0) return this._t(named ? "itv_overdue" : "overdue");
      if (data.dias_restantes === 0) return this._t(named ? "itv_last_day" : "last_day");
      return this._t(named ? "itv_in" : "left", { days: this._days(data.dias_restantes) });
    }

    /** Seguro en una línea. Con ``named`` lleva delante "Seguro". */
    _insuranceShort(named = true) {
      const data = (this._state(INSURANCE) || { attributes: {} }).attributes;
      if (data.dias_desistimiento == null) return "";
      if (data.dias_desistimiento === 0) return this._t(named ? "insurance_last_day" : "last_day");
      if (data.dias_desistimiento > 0 && data.nivel !== "ok")
        return this._t(named ? "insurance_cancel" : "to_cancel", { days: this._days(data.dias_desistimiento) });
      return this._t("renews_on", { date: this._day(data.renovacion) });
    }

    /** Fecha ISO ("2027-03-14") como "14 mar 2027". */
    _day(iso) {
      if (!iso) return "—";
      return new Date(`${iso}T00:00:00`).toLocaleDateString(this._dateLanguage(), { day: "numeric", month: "short", year: "numeric" });
    }

    /** Número entero con separador de miles, según el idioma. */
    _thousands(value) {
      return Math.abs(Number(value)).toLocaleString(this._language(), { useGrouping: "always" });
    }

    /** Resumen corto del mantenimiento, solo si la revisión está próxima o vencida. */
    _maintenanceShort() {
      if (this._value(MAINTENANCE) !== "on") return "";
      const data = this._state(MAINTENANCE).attributes;
      if (data.nivel === "overdue") return this._t("service_overdue");
      const days = Number(data.dias_restantes);
      const km = data.km_restantes;
      // Se enseña lo que antes llegue a los escalones de aviso.
      if (km != null && Number(km) <= 3000 && days > 60) return this._t("service_in", { value: `${this._thousands(km)} km` });
      return this._t("service_in", { value: this._days(days) });
    }

    _batteryIcon(level, charging) {
      if (level === undefined) return "mdi:battery-unknown";
      const step = Math.round(level / 10) * 10;
      if (charging) return step >= 100 ? "mdi:battery-charging-100" : `mdi:battery-charging-${Math.max(10, step)}`;
      if (step >= 100) return "mdi:battery";
      return step <= 0 ? "mdi:battery-outline" : `mdi:battery-${step}`;
    }

    _imageUrl(state) {
      if (!state || !state.attributes.entity_picture) return undefined;
      const picture = state.attributes.entity_picture;
      return `${picture}${picture.includes("?") ? "&" : "?"}state=${encodeURIComponent(state.state)}`;
    }

    _temp(value) {
      return Number(value).toLocaleString(this._language(), { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    }

    _updatedText() {
      const raw = this._value("sensor.last_update");
      const date = raw ? new Date(raw) : undefined;
      if (!date || Number.isNaN(date.getTime())) return "—";
      const language = this._dateLanguage();
      const time = date.toLocaleTimeString(language, { hour: "numeric", minute: "2-digit" });
      const startOfDay = (value) => new Date(value.getFullYear(), value.getMonth(), value.getDate()).getTime();
      const days = Math.round((startOfDay(new Date()) - startOfDay(date)) / 86400000);
      if (days === 0) return this._t("today", { time });
      if (days === 1) return this._t("yesterday", { time });
      return `${date.toLocaleDateString(language, { day: "numeric", month: "short" })}, ${time}`;
    }

    // --- Acciones ----------------------------------------------------------------

    _toast(message) {
      this.dispatchEvent(new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }));
    }

    async _call(busyKey, domain, service, key, data) {
      const entityId = this._ids[key];
      if (!entityId) return false;
      this._busy.add(busyKey);
      this._repaint();
      try {
        await this._hass.callService(domain, service, { entity_id: entityId, ...(data || {}) });
        return true;
      } catch (error) {
        this._toast((error && error.message) || this._t("command_failed"));
        return false;
      } finally {
        this._busy.delete(busyKey);
        this._repaint();
      }
    }

    _repaint() {
      this._dirty = true;
      this._update();
    }

    /** Orden con PIN: confirmación y, si hace falta, el desbloqueo previo. */
    _pinCommand(busyKey, title, button, domain, service, key) {
      if (!this._ids[key]) return this._toast(this._t("no_pin"));
      const html = `
        <div class="confirm"><h2>${escapeHtml(title)}</h2>
          <p>${this._t("pin_confirm", { name: this._boldName() })}</p></div>
        <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${escapeHtml(button)}</button></div>`;
      openDialog(html, async (action, _target, dialog) => {
        if (action !== "ok") return;
        dialog.close();
        // Modo "desbloqueo previo": la entidad pin_arm bloqueada = no armado.
        if (this._value("lock.pin_arm") === "locked" && !(await this._call(busyKey, "lock", "unlock", "lock.pin_arm"))) return;
        await this._call(busyKey, domain, service, key);
      });
      return undefined;
    }

    _onClick(event) {
      const target = event.composedPath().find((node) => node.dataset && node.dataset.action);
      if (!target || !this._hass) return;
      const tiles = this._tiles();
      switch (target.dataset.action) {
        case "refresh":
          this._call("refresh", "button", "press", "button.refresh");
          break;
        case "comfort":
          this._openComfort();
          break;
        case "charge":
          this._openCharge();
          break;
        case "lock":
          if (tiles.lock.on) this._pinCommand("lock", this._t("lock_q"), this._t("lock_do"), "lock", "lock", "lock.doors");
          else this._pinCommand("lock", this._t("unlock_q"), this._t("unlock_do"), "lock", "unlock", "lock.doors");
          break;
        case "trunk":
          // Sin portón eléctrico (p. ej. el Pro) no hay nada que mandar: se dice.
          if ((this._features || {}).porton_electrico === false) this._toast(this._t("trunk_manual"));
          else if (tiles.trunk.on) this._pinCommand("trunk", this._t("trunk_close_q"), this._t("close"), "cover", "close_cover", "cover.trunk_control");
          else this._pinCommand("trunk", this._t("trunk_open_q"), this._t("open_do"), "cover", "open_cover", "cover.trunk_control");
          break;
        case "vent":
          // Persiana invertida: open_cover SUBE los cristales; close_cover los entreabre.
          if (tiles.vent.on) this._pinCommand("vent", this._t("windows_close_q"), this._t("close"), "cover", "open_cover", "cover.windows");
          else this._pinCommand("vent", this._t("vent_q"), this._t("vent"), "cover", "close_cover", "cover.windows");
          break;
        case "locate":
          this._openLocate();
          break;
        case "maintenance":
          this._openMaintenance();
          break;
        case "itv":
          this._openItv();
          break;
        case "insurance":
          this._openInsurance();
          break;
        case "others":
          this._openOthers();
          break;
        default:
      }
    }

    /** Ventana con un texto y un único botón. */
    _message(title, text) {
      const html = `
        <div class="confirm"><h2>${escapeHtml(title)}</h2><p>${escapeHtml(text)}</p></div>
        <div class="btns"><button class="tb fill" data-action="close">${this._t("understood")}</button></div>`;
      openDialog(html, () => undefined);
    }
  }

  /**
   * Añade a la tarjeta los métodos de una clase. Cada ventana (ITV, seguro,
   * confort...) está en su fichero y se engancha así: dentro, `this` es la
   * tarjeta, igual que en los métodos de arriba.
   */
  const install = (source) => {
    for (const name of Object.getOwnPropertyNames(source.prototype)) {
      if (name === "constructor") continue;
      Object.defineProperty(DecDeepalCard.prototype, name, Object.getOwnPropertyDescriptor(source.prototype, name));
    }
  };

  // ── src/60_localizar.js ───────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Menú "Localizar vehículo"
  // ---------------------------------------------------------------------------
  install(class {
    _openLocate() {
      const option = (key, icon, label, text) =>
        this._ids[key]
          ? `<button class="tile" data-action="go" data-key="${key}"><ha-icon icon="${icon}"></ha-icon><b>${label}</b><small>${text}</small></button>`
          : "";
      const html = `
        <div class="head"><button class="icon-btn" data-action="close" aria-label="${this._t("close")}"><ha-icon icon="mdi:close"></ha-icon></button><h2>${this._t("locate")}</h2></div>
        <div class="three">
          ${option("button.flash_lights", "mdi:alarm-light-outline", this._t("lights"), this._t("flash"))}
          ${option("button.honk_horn", "mdi:bullhorn", this._t("horn"), this._t("honk"))}
          ${option("button.flash_and_honk", "mdi:alarm-light", this._t("lights_horn"), this._t("both"))}
        </div>`;
      openDialog(html, (action, target, dialog) => {
        if (action !== "go") return;
        dialog.close();
        this._call("locate", "button", "press", target.dataset.key);
      });
    }
  });

  // ── src/61_otros.js ───────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Menú "Otros"
  // ---------------------------------------------------------------------------
  install(class {
    _openOthers() {
      const maintenance = this._state(MAINTENANCE);
      const known = maintenance && maintenance.attributes.revision != null;
      const itv = this._state(ITV);
      const insurance = this._state(INSURANCE);
      const tone = (key) => {
        const level = this._dueLevel(key);
        return level ? ` style="color:${level === "overdue" ? RED : AMBER}"` : "";
      };
      // Un enlace de verdad (no un botón): así el navegador y la app del móvil
      // lo abren fuera, en una pestaña nueva, sin bloquearlo como ventana emergente.
      const manual = this._manualUrl
        ? `<a class="tile" data-action="manual" href="${escapeHtml(this._manualUrl)}" target="_blank" rel="noopener noreferrer"><ha-icon icon="mdi:book-open-variant"></ha-icon><b>${this._t("manual")}</b><small>${this._t("open_pdf")}</small></a>`
        : "";
      const off = this._t("not_enabled");
      const option = (action, key, icon, label, text) =>
        `<button class="tile" data-action="${action}"><ha-icon icon="${icon}"${tone(key)}></ha-icon><b>${label}</b><small>${escapeHtml(text)}</small></button>`;
      const html = `
        <div class="head"><button class="icon-btn" data-action="close" aria-label="${this._t("close")}"><ha-icon icon="mdi:close"></ha-icon></button><h2>${this._t("others")}</h2></div>
        <div class="three pairs">
          ${manual}
          ${option("maintenance", MAINTENANCE, "mdi:wrench", this._t("maintenance"), known ? this._t("nth_service", { ordinal: this._ordinal(maintenance.attributes.revision) }) : off)}
          ${this._itvAvailable === false ? "" : option("itv", ITV, "mdi:clipboard-check-outline", this._t("itv"), itv ? this._itvShort(false) || "—" : off)}
          ${option("insurance", INSURANCE, "mdi:shield-car", this._t("insurance"), insurance ? this._insuranceShort(false) || "—" : off)}
        </div>`;
      openDialog(html, (action, _target, dialog) => {
        if (action === "manual") {
          // El enlace se abre solo; el menú se cierra un instante después.
          setTimeout(() => dialog.close(), 300);
          return;
        }
        if (!["maintenance", "itv", "insurance"].includes(action)) return;
        dialog.close();
        if (action === "maintenance") known ? this._openMaintenance() : this._message(this._t("maintenance"), this._t("no_maintenance"));
        else if (action === "itv") this._openItv();
        else this._openInsurance();
      });
    }
  });

  // ── src/62_itv.js ─────────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Ventana de ITV
  // ---------------------------------------------------------------------------
  install(class {
    _openItv() {
      const state = this._state(ITV);
      if (!state || state.attributes.fecha_limite == null) return this._message(this._t("itv"), this._t("no_itv"));
      const data = state.attributes;
      const overdue = data.dias_restantes < 0;
      const tone = overdue ? RED : data.nivel === "soon" ? AMBER : "var(--secondary-text-color)";
      const history = (data.historial || []).slice().reverse();
      const html = `
        <div class="head"><button class="icon-btn" data-action="close" aria-label="${this._t("close")}"><ha-icon icon="mdi:close"></ha-icon></button><h2>${this._t("itv")}</h2></div>
        <div class="mt">
          <div class="next"><ha-icon icon="mdi:clipboard-check-outline" style="color:${tone}"></ha-icon>${this._t("next_itv")}${overdue ? this._t("overdue_mark") : ""}</div>
          <div class="two">
            <div class="stat"><b>${Math.abs(data.dias_restantes)}</b><small>${this._t(overdue ? "days_late" : "days_left")}</small></div>
            <div class="stat"><b>${this._day(data.fecha_limite)}</b><small>${this._t("due_date")}</small></div>
          </div>
          <p class="due">${this._t("itv_rule")}</p>
          <h3>${this._t("details")}</h3>
          <dl><dt>${this._t("registration")}</dt><dd>${this._day(data.matriculacion)}</dd>
            <dt>${this._t("last_itv")}</dt><dd>${data.ultima_itv ? this._day(data.ultima_itv) : this._t("none_yet")}</dd></dl>
          ${history.length ? `<h3>${this._t("history")}</h3><ul>${history.map((item) => `<li>${this._day(item)}</li>`).join("")}</ul>` : ""}
        </div>
        <div class="btns"><button class="tb fill" data-action="register">${this._t("register_itv")}</button></div>`;
      openDialog(html, (action, _target, dialog) => {
        if (action !== "register") return;
        dialog.close();
        this._confirmItv();
      });
      return undefined;
    }

    _confirmItv() {
      const html = `
        <div class="confirm"><h2>${this._t("register_itv_q")}</h2>
          <p>${this._t("register_itv_text", { name: this._boldName() })}</p></div>
        <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("register")}</button></div>`;
      openDialog(html, async (action, _target, dialog) => {
        if (action !== "ok") return;
        dialog.close();
        try {
          await this._hass.callService(DOMAIN, "register_itv", { device_id: this._deviceId() });
          this._toast(this._t("itv_registered"));
        } catch (error) {
          this._toast((error && error.message) || this._t("itv_failed"));
        }
      });
    }
  });

  // ── src/63_seguro.js ──────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Ventana de Seguro
  // ---------------------------------------------------------------------------
  install(class {
    async _openInsurance() {
      const state = this._state(INSURANCE);
      if (!state || state.attributes.renovacion == null) return this._message(this._t("insurance"), this._t("no_insurance"));
      const data = state.attributes;
      // Póliza y teléfonos: no están en la entidad, se piden a la integración.
      let extra = {};
      try {
        extra = (await this._hass.callApi("GET", `dec_deepal/insurance_info/${this._deviceId()}`)) || {};
      } catch (_error) {
        extra = {};
      }
      const lastDay = data.dias_desistimiento === 0;
      const tone = lastDay ? RED : data.nivel === "soon" ? AMBER : "var(--secondary-text-color)";
      const kind = data.tipo ? this._t(`kind_${data.tipo}`) : "";
      const title = [data.compania, kind].filter(Boolean).join(" · ") || this._t("insurance");
      const cancel =
        data.dias_desistimiento >= 0
          ? `<div class="stat"><b>${data.dias_desistimiento}</b><small>${this._t("days_to_cancel")}</small></div>`
          : `<div class="stat"><b>—</b><small>${this._t("cancel_passed")}</small></div>`;
      // Botón de llamar. En la app del móvil un enlace "tel:" normal no hace
      // nada (la página va dentro de la app); con target="_blank" la app se lo
      // pasa al sistema, que abre el marcador. Además se enseña el número y, al
      // pulsar, se copia: así sirve aunque el dispositivo no pueda llamar.
      const phone = (number, icon, label) =>
        number
          ? `<a class="call" data-action="call" data-number="${escapeHtml(number)}" target="_blank" rel="noopener noreferrer"
               href="tel:${escapeHtml(String(number).replace(/[^0-9+]/g, ""))}"><ha-icon icon="${icon}"></ha-icon><span>${label}<small>${escapeHtml(number)}</small></span></a>`
          : "";
      const html = `
        <div class="head"><button class="icon-btn" data-action="close" aria-label="${this._t("close")}"><ha-icon icon="mdi:close"></ha-icon></button><h2>${this._t("insurance")}</h2></div>
        <div class="mt">
          <div class="next"><ha-icon icon="mdi:shield-car" style="color:${tone}"></ha-icon>${escapeHtml(title)}</div>
          <div class="two"><div class="stat"><b>${data.dias_renovacion}</b><small>${this._t("days_to_renewal")}</small></div>${cancel}</div>
          <p class="due">${this._t("renewal_text", { renewal: this._day(data.renovacion), deadline: this._day(data.limite_desistimiento), days: data.dias_aviso })}</p>
          <h3>${this._t("policy")}</h3>
          <dl><dt>${this._t("company")}</dt><dd>${escapeHtml(data.compania || "—")}</dd>
            <dt>${this._t("policy_number")}</dt><dd>${escapeHtml(extra.policy || "—")}</dd>
            <dt>${this._t("kind")}</dt><dd>${escapeHtml(kind || "—")}</dd></dl>
          <div class="calls">${phone(extra.phone_assistance, "mdi:tow-truck", this._t("assistance"))}${phone(extra.phone_company, "mdi:phone", this._t("company"))}</div>
        </div>
        <div class="btns"></div>`;
      openDialog(html, (action, target) => {
        if (action !== "call") return;
        const number = target.dataset.number;
        // El enlace abre el marcador por su cuenta; aquí solo se copia el número.
        if (navigator.clipboard && navigator.clipboard.writeText)
          navigator.clipboard.writeText(number).then(
            () => this._toast(this._t("number_copied", { number })),
            () => undefined
          );
      });
      return undefined;
    }
  });

  // ── src/64_mantenimiento.js ───────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Ventana de Mantenimiento
  // ---------------------------------------------------------------------------
  install(class {
    _openMaintenance() {
      const state = this._state(MAINTENANCE);
      if (!state) return;
      const data = state.attributes;
      const overdue = data.nivel === "overdue";
      // Sin aviso todavía, la llave va en gris; ámbar si se acerca y roja si está vencida.
      const tone = overdue ? RED : data.nivel === "soon" ? AMBER : "var(--secondary-text-color)";
      const stat = (value, left, late) =>
        value == null
          ? `<div class="stat"><b>—</b><small>${this._t(left)}</small></div>`
          : `<div class="stat"><b>${this._thousands(value)}</b><small>${this._t(Number(value) < 0 ? late : left)}</small></div>`;
      const list = (title, items) => (items.length ? `<h3>${title}</h3><ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : "");
      const history = (data.historial || [])
        .slice()
        .reverse()
        .map((item) => this._t("history_item", { ordinal: this._ordinal(item.number), date: this._day(item.date), km: this._thousands(item.km) }));
      const html = `
        <div class="head"><button class="icon-btn" data-action="close" aria-label="${this._t("close")}"><ha-icon icon="mdi:close"></ha-icon></button><h2>${this._t("maintenance")}</h2></div>
        <div class="mt">
          <div class="next"><ha-icon icon="mdi:wrench" style="color:${tone}"></ha-icon>${this._t("nth_service", { ordinal: this._ordinal(data.revision) })}${overdue ? this._t("overdue_mark") : ""}</div>
          <div class="two">${stat(data.dias_restantes, "days_left", "days_late")}${stat(data.km_restantes, "km_left", "km_late")}</div>
          <p class="due">${this._t("service_planned", { date: this._day(data.fecha_prevista), km: this._thousands(data.km_previstos) })}</p>
          ${list(this._t("includes"), data.operaciones || [])}
          ${list(this._t("history"), history)}
        </div>
        <div class="btns"><button class="tb fill" data-action="register">${this._t("register_service")}</button></div>`;
      openDialog(html, (action, _target, dialog) => {
        if (action !== "register") return;
        dialog.close();
        this._confirmMaintenance(data.revision);
      });
    }

    /** Confirmación antes de anotar la revisión (hoy, con los km actuales). */
    _confirmMaintenance(revision) {
      const reading = this._format("sensor.odometer");
      const odometer = reading ? this._t("with_odometer", { value: escapeHtml(reading) }) : "";
      const html = `
        <div class="confirm"><h2>${this._t("register_service_q", { ordinal: this._ordinal(revision) })}</h2>
          <p>${this._t("register_service_text", { name: this._boldName(), odometer })}</p></div>
        <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("register")}</button></div>`;
      openDialog(html, async (action, _target, dialog) => {
        if (action !== "ok") return;
        dialog.close();
        try {
          await this._hass.callService(DOMAIN, "register_maintenance", { device_id: this._deviceId() });
          this._toast(this._t("service_registered"));
        } catch (error) {
          this._toast((error && error.message) || this._t("service_failed"));
        }
      });
    }
  });

  // ── src/65_confort.js ─────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Ventana de Confort
  // ---------------------------------------------------------------------------
  install(class {
    _spotLevel(spot) {
      if (spot.key.startsWith("switch.")) return this._value(spot.key) === "on" ? 1 : 0;
      return this._number(spot.key) || 0;
    }

    _openComfort() {
      if (this._comfort) return;
      const spots = HOTSPOTS.filter((spot) => this._ids[spot.key])
        .map(
          (spot) =>
            `<button class="hot" data-action="spot" data-key="${spot.key}" aria-label="${escapeHtml(this._t(spot.label))}"
               style="left:${spot.x}%;top:${spot.y}%"><ha-icon icon="${spot.icon}"></ha-icon><u></u></button>`
        )
        .join("");
      const html = `
        <div class="head"><button class="icon-btn" data-action="close" aria-label="${this._t("close")}"><ha-icon icon="mdi:close"></ha-icon></button><h2>${this._t("comfort")}</h2></div>
        <div class="stage"><img alt="">${spots}</div>
        <div class="temp">
          <button class="round" data-action="temp" data-step="-0.5" aria-label="${this._t("temp_down")}"><ha-icon icon="mdi:minus"></ha-icon></button>
          <b><span class="target"></span><sup> °C</sup></b>
          <button class="round" data-action="temp" data-step="0.5" aria-label="${this._t("temp_up")}"><ha-icon icon="mdi:plus"></ha-icon></button>
        </div>
        <button class="power" data-action="power"><ha-icon icon="mdi:power"></ha-icon><span></span></button>
        <p class="info"></p>`;
      this._comfort = openDialog(html, (action, target) => this._onComfort(action, target));
      this._comfort.onClose = () => {
        this._comfort = null;
      };
      this._paintComfort();
    }

    _paintComfort() {
      const root = this._comfort.root;
      const image = this._state("image.interior_view");
      const img = root.querySelector(".stage img");
      const src = this._imageUrl(image);
      if (src && img.getAttribute("src") !== src) img.setAttribute("src", src);

      for (const element of root.querySelectorAll(".hot")) {
        const spot = HOTSPOTS.find((item) => item.key === element.dataset.key);
        const level = this._spotLevel(spot);
        element.classList.toggle("on", level > 0);
        element.classList.toggle("busy", this._busy.has(spot.key));
        element.querySelector("u").textContent = spot.key.startsWith("number.") && level > 0 ? String(level) : "";
      }

      const climate = this._state("climate.cabin_climate");
      const climateOn = (this._value("climate.cabin_climate") || "off") !== "off";
      const target = this._pendingTemp != null ? this._pendingTemp : climate && climate.attributes.temperature;
      root.querySelector(".target").textContent = target != null ? this._temp(target) : "—";
      root.querySelector(".temp").hidden = !climate;
      const power = root.querySelector(".power");
      power.hidden = !climate;
      power.classList.toggle("on", climateOn);
      power.classList.toggle("busy", this._busy.has("power"));
      power.querySelector("span").textContent = this._t(climateOn ? "climate_on" : "climate_off");

      const parts = [];
      const inside = this._format("sensor.inside_temperature");
      const humidity = this._format("sensor.cabin_humidity");
      const fan = this._value("sensor.fan_level");
      const recirculation = this._value("binary_sensor.air_recirculation");
      if (inside) parts.push(this._t("inside", { value: inside }));
      if (humidity) parts.push(this._t("humidity", { value: humidity }));
      if (climateOn && fan) parts.push(this._t("fan", { value: fan }));
      if (climateOn && recirculation) parts.push(this._t(recirculation === "on" ? "recirculating" : "outside_air"));
      root.querySelector(".info").textContent = parts.join(" · ");
    }

    _onComfort(action, target) {
      if (action === "spot") {
        const key = target.dataset.key;
        if (key.startsWith("switch.")) this._call(key, "switch", "toggle", key);
        else this._call(key, "number", "set_value", key, { value: ((this._number(key) || 0) + 1) % 4 });
      } else if (action === "power") {
        const climateOn = (this._value("climate.cabin_climate") || "off") !== "off";
        this._call("power", "climate", climateOn ? "turn_off" : "turn_on", "climate.cabin_climate");
      } else if (action === "temp") {
        const climate = this._state("climate.cabin_climate");
        if (!climate) return;
        const current = this._pendingTemp != null ? this._pendingTemp : Number(climate.attributes.temperature);
        if (!Number.isFinite(current)) return;
        const min = Number(climate.attributes.min_temp) || 18;
        const max = Number(climate.attributes.max_temp) || 32;
        this._pendingTemp = Math.max(min, Math.min(max, current + Number(target.dataset.step)));
        this._paintComfort();
        // Se espera a que el usuario termine de pulsar antes de enviar la orden.
        clearTimeout(this._tempTimer);
        this._tempTimer = setTimeout(async () => {
          const temperature = this._pendingTemp;
          await this._call("temp", "climate", "set_temperature", "climate.cabin_climate", { temperature });
          if (this._pendingTemp === temperature) this._pendingTemp = null;
          if (this._comfort) this._paintComfort();
        }, 900);
      }
    }
  });

  // ── src/66_carga.js ───────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Ventana de carga (se abre al pulsar la franja de la batería)
  // ---------------------------------------------------------------------------
  // Enseña la vista de carga y lo que se sabe de la carga: porcentaje,
  // autonomía, tiempo que queda, corriente, conector, lo que lleva esta carga
  // y la última. Estas dos las apunta la integración (charging.py) y llegan
  // como atributos del sensor "Cargando". Se repinta sola mientras está abierta.
  install(class {
    _openCharge() {
      if (this._charge) return;
      const html = `
        <div class="head"><button class="icon-btn" data-action="close" aria-label="${this._t("close")}"><ha-icon icon="mdi:close"></ha-icon></button>
          <h2>${this._t("charge_title")}</h2></div>
        <div class="chg">
          <div class="view" hidden><img alt=""></div>
          <div class="now"><ha-icon></ha-icon><span></span></div>
          <div class="pct"><b></b><span></span></div>
          <div class="lvl"><i></i></div>
          <div class="stats"></div>
        </div>
        <div class="btns"><button class="tb" data-action="refresh">${this._t("refresh_short")}</button><button class="tb" data-action="close">${this._t("close")}</button></div>`;
      this._charge = openDialog(html, (action) => {
        if (action === "refresh") this._call("refresh", "button", "press", "button.refresh");
      });
      this._charge.onClose = () => {
        this._charge = null;
      };
      this._paintCharge();
    }

    /** "3 h 25 min" / "45 min". */
    _duration(minutes) {
      const total = Math.max(0, Math.round(minutes));
      const h = Math.floor(total / 60);
      const m = total % 60;
      return h ? this._t("duration_hm", { h, m }) : this._t("duration_m", { m });
    }

    _clock(date) {
      return date.toLocaleTimeString(this._language(), { hour: "numeric", minute: "2-digit" });
    }

    /** Minutos que le quedan a la carga, o `undefined` (el coche los da como "H:MM"). */
    _chargeMinutes() {
      const match = /^(\d+):(\d{2})$/.exec(this._value("sensor.remaining_charge_time_hhmm") || "");
      const minutes = match ? Number(match[1]) * 60 + Number(match[2]) : undefined;
      return minutes > 0 ? minutes : undefined;
    }

    _chargeStat(icon, label, value, detail, wide) {
      return `<div class="st${wide ? " wide" : ""}"><div class="k"><ha-icon icon="${icon}"></ha-icon>${this._t(label)}</div>
        <div class="n">${escapeHtml(value)}</div><div class="d">${escapeHtml(detail || "")}</div></div>`;
    }

    _paintCharge() {
      const root = this._charge.root;
      const $ = (selector) => root.querySelector(selector);
      const themes = this._hass.themes || {};
      $(".chg").classList.toggle("dark", Boolean(themes.darkMode));

      const src = this._imageUrl(this._state("image.charging_view"));
      $(".view").hidden = !src;
      if (src && $(".view img").getAttribute("src") !== src) $(".view img").setAttribute("src", src);

      const status = this._value("sensor.charge_status") || "disconnected";
      const charging = this._value("binary_sensor.charging") === "on";
      const plugged = status !== "disconnected";
      const dc = status.endsWith("_dc");
      const minutes = charging ? this._chargeMinutes() : undefined;
      const end = minutes === undefined ? null : new Date(Date.now() + minutes * 60000);

      // Línea de estado.
      let now = this._t(plugged ? "charge_plugged" : "charge_unplugged");
      if (charging) {
        now = this._t("charging_status", { type: dc ? "DC" : "AC" });
        if (end) now += ` · ${this._t("charge_full_at", { time: this._clock(end) })}`;
      }
      $(".now").classList.toggle("on", charging);
      $(".now ha-icon").setAttribute("icon", charging ? "mdi:lightning-bolt" : plugged ? "mdi:power-plug" : "mdi:power-plug-off-outline");
      $(".now span").textContent = now;

      // Porcentaje, autonomía y barra (mismos colores que en la tarjeta).
      const level = this._number("sensor.battery_level");
      const range = this._format("sensor.range");
      $(".pct b").textContent = level === undefined ? "—" : `${Math.round(level)} %`;
      $(".pct span").textContent = range ? this._t("range_left", { value: range }) : "";
      const color = level === undefined ? "var(--secondary-text-color)" : level < 15 ? "var(--error-color, #db4437)" : level < 50 ? "var(--warning-color, #f9a825)" : "var(--success-color, #43a047)";
      $(".lvl").classList.toggle("on", charging);
      $(".lvl i").style.width = `${level === undefined ? 0 : Math.max(0, Math.min(100, level))}%`;
      $(".lvl i").style.backgroundColor = color;

      // Recuadros de datos: solo los que tienen algo que decir.
      const stats = [];
      if (end) stats.push(this._chargeStat("mdi:timer-sand", "time_left", this._duration(minutes), this._t("ends_at", { time: this._clock(end) })));
      const current = this._format("sensor.charge_current");
      if (plugged && current) {
        stats.push(this._chargeStat(dc ? "mdi:current-dc" : "mdi:current-ac", "current", current, this._t(charging ? (dc ? "current_dc" : "current_ac") : "no_charge")));
      }
      if (plugged) stats.push(this._chargeStat(dc ? "mdi:ev-plug-ccs2" : "mdi:ev-plug-type2", "connector", dc ? "DC · CCS2" : this._t("connector_ac"), this._t("plugged")));

      const sessions = (this._state("binary_sensor.charging") || { attributes: {} }).attributes;
      const running = charging && sessions.carga_actual;
      if (running && running.inicio) {
        const start = new Date(running.inicio);
        const gained = [];
        if (level !== undefined && running.nivel_inicio != null) gained.push(`+${Math.max(0, Math.round(level - running.nivel_inicio))} %`);
        const km = this._number("sensor.range");
        if (km !== undefined && running.autonomia_inicio != null) gained.push(`+${Math.max(0, Math.round(km - running.autonomia_inicio))} km`);
        const since = this._t("since", { time: this._clock(start), duration: this._duration((Date.now() - start.getTime()) / 60000) });
        stats.push(this._chargeStat("mdi:chart-line", "this_charge", gained.join(" · ") || "—", since, stats.length % 2 === 0));
      }
      const last = !charging && sessions.ultima_carga;
      if (last && last.inicio && last.fin) {
        const start = new Date(last.inicio);
        const finish = new Date(last.fin);
        const levels = last.nivel_inicio != null && last.nivel_fin != null
          ? this._t("from_to", { from: Math.round(last.nivel_inicio), to: Math.round(last.nivel_fin) })
          : "—";
        const day = start.toLocaleDateString(this._dateLanguage(), { day: "numeric", month: "short" });
        const detail = `${day}, ${this._clock(start)} – ${this._clock(finish)} · ${this._duration((finish - start) / 60000)}`;
        stats.push(this._chargeStat("mdi:history", "last_charge", levels, detail, true));
      }
      const html = stats.join("");
      if (this._chargeHtml !== html || !$(".stats").childElementCount) $(".stats").innerHTML = html;
      this._chargeHtml = html;
    }
  });

  // ── src/90_registro.js ────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Alta de la tarjeta en Home Assistant
  // ---------------------------------------------------------------------------
  /** La misma tarjeta, con el coche visto desde arriba. */
  class DecDeepalTopCard extends DecDeepalCard {
    static get VIEW() {
      return "top";
    }
  }

  customElements.define(TAG, DecDeepalCard);
  customElements.define(TOP_TAG, DecDeepalTopCard);
  const cardText = (key) => translate(document.documentElement.lang || navigator.language, key);
  const documentationURL = "https://github.com/manuelem1984/dec_deepal";
  window.customCards = window.customCards || [];
  window.customCards.push(
    { type: TAG, name: "DEC Deepal", description: cardText("card_description"), preview: true, documentationURL },
    { type: TOP_TAG, name: `DEC Deepal · ${cardText("top_view")}`, description: cardText("top_card_description"), preview: true, documentationURL }
  );
})();
