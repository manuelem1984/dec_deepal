// =============================================================================
// DEC Deepal — Tarjeta para los paneles de Home Assistant
// =============================================================================
//
//   type: custom:dec-deepal-card
//   device_id: <dispositivo del coche>     (opcional: si falta, el primero)
//
// Qué muestra (diseño cerrado con bocetos, 09-10-2026):
//   - Cabecera: nombre del coche, "Actualizado: ..." y botón de actualizar.
//   - Vista isométrica del coche (la entidad de imagen de la integración).
//     Tocarla no hace nada (a propósito).
//   - Batería: icono según el nivel (verde ≥ 50 %, amarillo < 50 %, rojo
//     < 15 %; con rayo si carga), autonomía y estado de carga, más la barra.
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
// Sin herramientas de compilación: JavaScript plano en un solo archivo, sin
// dependencias. Lo carga dec-icons.js (ver frontend.py).
// =============================================================================

(() => {
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
  // ---------------------------------------------------------------------------
  // Textos por idioma
  // ---------------------------------------------------------------------------
  // La tabla de abajo se GENERA a partir de idiomas/<idioma>.json (sección
  // "tarjeta") con tools/generar_idiomas.py. Para cambiar un texto o añadir un
  // idioma, editar esos ficheros y volver a generar. Guía: docs/idiomas.md
  //
  //   BASE_LANGUAGE       idioma que se usa si el del usuario no está traducido
  //   BORROWED_LANGUAGES  idiomas sin traducción propia que usan la de otro
  //   TEXTS               { idioma: { clave: texto } }, ya completa (a un
  //                       idioma a medias se le rellena con el idioma base)
  // >>> TEXTOS GENERADOS — no editar aquí: ver idiomas/ y tools/generar_idiomas.py >>>
  const BASE_LANGUAGE = "en";
  const BORROWED_LANGUAGES = {"ca": "es", "eu": "es", "gl": "es"};
  const TEXTS = {
    "es": {
      "card_description": "Tu Deepal de un vistazo: vista del coche, batería, confort y acciones rápidas.",
      "car": "Coche",
      "not_found": "No encuentro el coche. Elige uno en la configuración de la tarjeta.",
      "refresh": "Actualizar datos del vehículo",
      "updated": "Actualizado: {when}",
      "today": "hoy, {time}",
      "yesterday": "ayer, {time}",
      "comfort": "Confort",
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
      "no_pin": "Activa el control con PIN en Configurar (integración DEC Deepal) para usar este botón.",
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
      "no_maintenance": "El mantenimiento de este coche no está activado. Actívalo en Ajustes → Dispositivos y servicios → DEC Deepal → Configurar → Mantenimiento.",
      "no_itv": "La ITV de este coche no está activada. Actívala en Ajustes → Dispositivos y servicios → DEC Deepal → Configurar → ITV.",
      "no_insurance": "El seguro de este coche no está activado. Actívalo en Ajustes → Dispositivos y servicios → DEC Deepal → Configurar → Seguro.",
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
      "register_service_text": "Se anotará que {name} ha pasado la revisión hoy{odometer}, y se empezará a contar para la siguiente. Si la pasó otro día, regístrala desde Configurar → Mantenimiento.",
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
      "register_itv_text": "Se anotará que {name} ha pasado la ITV hoy y se calculará la siguiente. Si la pasó otro día, ponlo en Configurar → ITV.",
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
      "outside_air": "Aire exterior"
    },
    "en": {
      "card_description": "Your Deepal at a glance: car view, battery, comfort and quick actions.",
      "car": "Car",
      "not_found": "I cannot find the car. Choose one in the card settings.",
      "refresh": "Refresh vehicle data",
      "updated": "Updated: {when}",
      "today": "today, {time}",
      "yesterday": "yesterday, {time}",
      "comfort": "Comfort",
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
      "no_pin": "Enable PIN control in Configure (DEC Deepal integration) to use this button.",
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
      "no_maintenance": "Servicing is not enabled for this car. Enable it in Settings → Devices & services → DEC Deepal → Configure → Servicing.",
      "no_itv": "ITV is not enabled for this car. Enable it in Settings → Devices & services → DEC Deepal → Configure → ITV.",
      "no_insurance": "Insurance is not enabled for this car. Enable it in Settings → Devices & services → DEC Deepal → Configure → Insurance.",
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
      "register_service_text": "It will be recorded that {name} was serviced today{odometer}, and the count for the next one will start. If it was done on another day, register it from Configure → Servicing.",
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
      "register_itv_text": "It will be recorded that {name} passed the ITV today and the next one will be calculated. If it was on another day, set it in Configure → ITV.",
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
      "outside_air": "Outside air"
    },
    "pt": {
      "card_description": "O seu Deepal num relance: vista do carro, bateria, conforto e ações rápidas.",
      "car": "Carro",
      "not_found": "Não encontro o carro. Escolha um na configuração do cartão.",
      "refresh": "Atualizar dados do veículo",
      "updated": "Atualizado: {when}",
      "today": "hoje, {time}",
      "yesterday": "ontem, {time}",
      "comfort": "Conforto",
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
      "no_pin": "Ative o controlo com PIN em Configurar (integração DEC Deepal) para usar este botão.",
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
      "no_maintenance": "A manutenção deste carro não está ativada. Ative-a em Definições → Dispositivos e serviços → DEC Deepal → Configurar → Manutenção.",
      "no_itv": "A ITV deste carro não está ativada. Ative-a em Definições → Dispositivos e serviços → DEC Deepal → Configurar → ITV.",
      "no_insurance": "O seguro deste carro não está ativado. Ative-o em Definições → Dispositivos e serviços → DEC Deepal → Configurar → Seguro.",
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
      "register_service_text": "Ficará anotado que {name} fez a revisão hoje{odometer}, e começa a contagem para a seguinte. Se foi noutro dia, registe-a em Configurar → Manutenção.",
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
      "register_itv_text": "Ficará anotado que {name} passou na ITV hoje e será calculada a seguinte. Se foi noutro dia, indique-o em Configurar → ITV.",
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
      "outside_air": "Ar exterior"
    },
    "it": {
      "card_description": "La tua Deepal a colpo d'occhio: vista dell'auto, batteria, comfort e azioni rapide.",
      "car": "Auto",
      "not_found": "Non trovo l'auto. Scegline una nella configurazione della scheda.",
      "refresh": "Aggiorna dati del veicolo",
      "updated": "Aggiornato: {when}",
      "today": "oggi, {time}",
      "yesterday": "ieri, {time}",
      "comfort": "Comfort",
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
      "no_pin": "Attiva il controllo con PIN in Configura (integrazione DEC Deepal) per usare questo pulsante.",
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
      "no_maintenance": "La manutenzione di quest'auto non è attiva. Attivala in Impostazioni → Dispositivi e servizi → DEC Deepal → Configura → Manutenzione.",
      "no_itv": "L'ITV di quest'auto non è attiva. Attivala in Impostazioni → Dispositivi e servizi → DEC Deepal → Configura → ITV.",
      "no_insurance": "L'assicurazione di quest'auto non è attiva. Attivala in Impostazioni → Dispositivi e servizi → DEC Deepal → Configura → Assicurazione.",
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
      "register_service_text": "Verrà annotato che {name} ha fatto il tagliando oggi{odometer}, e inizierà il conteggio per il successivo. Se l'ha fatto un altro giorno, registralo da Configura → Manutenzione.",
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
      "register_itv_text": "Verrà annotato che {name} ha superato l'ITV oggi e verrà calcolata la successiva. Se è stato un altro giorno, indicalo in Configura → ITV.",
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
      "outside_air": "Aria esterna"
    },
    "pl": {
      "card_description": "Twój Deepal w jednym miejscu: widok samochodu, akumulator, komfort i szybkie akcje.",
      "car": "Samochód",
      "not_found": "Nie znajduję samochodu. Wybierz go w konfiguracji karty.",
      "refresh": "Odśwież dane pojazdu",
      "updated": "Zaktualizowano: {when}",
      "today": "dziś, {time}",
      "yesterday": "wczoraj, {time}",
      "comfort": "Komfort",
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
      "no_pin": "Włącz sterowanie z PIN-em w Konfiguruj (integracja DEC Deepal), aby używać tego przycisku.",
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
      "no_maintenance": "Serwis dla tego samochodu nie jest włączony. Włącz go w Ustawienia → Urządzenia i usługi → DEC Deepal → Konfiguruj → Serwis.",
      "no_itv": "ITV dla tego samochodu nie jest włączone. Włącz je w Ustawienia → Urządzenia i usługi → DEC Deepal → Konfiguruj → ITV.",
      "no_insurance": "Ubezpieczenie dla tego samochodu nie jest włączone. Włącz je w Ustawienia → Urządzenia i usługi → DEC Deepal → Konfiguruj → Ubezpieczenie.",
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
      "register_service_text": "Zostanie zapisane, że {name} przeszedł przegląd dzisiaj{odometer}, i zacznie się odliczanie do następnego. Jeśli było to innego dnia, zarejestruj go w Konfiguruj → Serwis.",
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
      "register_itv_text": "Zostanie zapisane, że {name} przeszedł ITV dzisiaj, i zostanie obliczony następny termin. Jeśli było to innego dnia, wpisz to w Konfiguruj → ITV.",
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
      "outside_air": "Powietrze z zewnątrz"
    }
  };
  // <<< TEXTOS GENERADOS <<<

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
    .car { position: absolute; max-width: none; display: block;
      width: ${(ISOMETRIC.width / ISOMETRIC.crop.w) * 100}%;
      left: ${(-ISOMETRIC.crop.x / ISOMETRIC.crop.w) * 100}%;
      top: ${(-ISOMETRIC.crop.y / ISOMETRIC.crop.h) * 100}%; }
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
      this._pendingTemp = null;
      this._tempTimer = null;
      this.shadowRoot.addEventListener("click", (event) => this._onClick(event));
    }

    // --- API de las tarjetas de Home Assistant --------------------------------

    static getStubConfig(hass) {
      const first = Object.values((hass && hass.entities) || {}).find((entry) => entry.platform === DOMAIN && entry.device_id);
      return { device_id: first ? first.device_id : "" };
    }

    static getConfigForm() {
      return {
        schema: [{ name: "device_id", selector: { device: { filter: [{ integration: DOMAIN }] } } }],
        computeLabel: () => translate(document.documentElement.lang, "car"),
      };
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
      return 8;
    }

    getGridOptions() {
      return { columns: 12, min_columns: 6, min_rows: 6 };
    }

    disconnectedCallback() {
      if (this._comfort) this._comfort.close();
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

    /** Pregunta a la integración (una vez por coche) el enlace del manual y si hay ITV. */
    async _checkManual(deviceId) {
      if (!deviceId || this._manualDevice === deviceId || !this._hass.callApi) return;
      this._manualDevice = deviceId;
      this._manualUrl = "";
      this._itvAvailable = true;
      try {
        const info = await this._hass.callApi("GET", `dec_deepal/manual_info/${deviceId}`);
        // La ITV solo existe en algunos países (hoy, España).
        if (this._manualDevice === deviceId) this._itvAvailable = !(info && info.itv === false);
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
      if (!this._built) this._build();
      else if (!changed && !this._dirty) return;
      this._seen = tracked;
      this._dirty = false;
      this._paint();
      if (this._comfort) this._paintComfort();
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
          <div class="range">
            <ha-icon class="batt"></ha-icon><span class="km"></span><span class="grow"></span>
            <span class="charge"><ha-icon></ha-icon><span></span></span>
          </div>
          <div class="bar"><i></i></div>
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

      // Imagen: vista isométrica (o, si no existe, la imagen DEC).
      const isometric = this._state("image.isometric_view");
      const image = isometric || this._state("image.dec_photo");
      const img = $(".car");
      const src = this._imageUrl(image);
      $(".carbox").hidden = !src;
      $(".carbox").classList.toggle("plain", !isometric); // la foto DEC va sin recortar
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
      const active = WARNINGS.filter((warning) => warning.keys.some((key) => this._value(key) === "on"));
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
        comfort: { icon: "mdi:sun-snowflake-variant", text: comfortText, primary: true },
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
        case "lock":
          if (tiles.lock.on) this._pinCommand("lock", this._t("lock_q"), this._t("lock_do"), "lock", "lock", "lock.doors");
          else this._pinCommand("lock", this._t("unlock_q"), this._t("unlock_do"), "lock", "unlock", "lock.doors");
          break;
        case "trunk":
          if (tiles.trunk.on) this._pinCommand("trunk", this._t("trunk_close_q"), this._t("close"), "cover", "close_cover", "cover.trunk_control");
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

    // --- Menú "Localizar vehículo" ------------------------------------------------

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

    // --- Menú "Otros" ---------------------------------------------------------------

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

    // --- Ventana de ITV ---------------------------------------------------------------

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

    // --- Ventana de Seguro ----------------------------------------------------------

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
      const phone = (number, icon, label) =>
        number ? `<a class="call" href="tel:${escapeHtml(String(number).replace(/[^0-9+]/g, ""))}"><ha-icon icon="${icon}"></ha-icon>${label}</a>` : "";
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
      openDialog(html, () => undefined);
      return undefined;
    }

    /** Ventana con un texto y un único botón. */
    _message(title, text) {
      const html = `
        <div class="confirm"><h2>${escapeHtml(title)}</h2><p>${escapeHtml(text)}</p></div>
        <div class="btns"><button class="tb fill" data-action="close">${this._t("understood")}</button></div>`;
      openDialog(html, () => undefined);
    }

    // --- Ventana de Mantenimiento ---------------------------------------------------

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

    // --- Ventana de Confort ----------------------------------------------------

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
        const min = Number(climate.attributes.min_temp) || 16;
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
  }

  customElements.define(TAG, DecDeepalCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: TAG,
    name: "DEC Deepal",
    description: translate(document.documentElement.lang || navigator.language, "card_description"),
    preview: true,
    documentationURL: "https://github.com/manuelem1984/dec_deepal",
  });
})();
