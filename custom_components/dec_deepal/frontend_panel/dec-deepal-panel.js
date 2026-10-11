// FICHERO GENERADO — no editar. El código está en frontend_panel/src/;
// tras cambiarlo, ejecutar: python tools/construir_tarjeta.py
// =============================================================================
// DEC Deepal — Panel de la barra lateral de Home Assistant
// =============================================================================
// Una página propia (como la de Alarmo) donde se ve y se configura todo lo de
// los coches. El botón "Configurar" de la integración lleva aquí.
//
// Pestañas:
//   - Coches: una tarjeta por coche con su foto, versión, equipamiento (el de
//     su ficha del catálogo) y tres recuadros —mantenimiento, ITV y seguro—,
//     que al pulsarlos abren su ficha (qué toca en la revisión, fechas del
//     seguro...) y con un engranaje que abre su configuración. El botón
//     "Apariencia" elige modelo, versión, color y llanta, con la foto delante.
//   - Avisos: una tabla por coche. Un apartado plegable por cada cosa (carga,
//     testigos, mantenimiento, ITV, seguro), una fila por aviso y una casilla
//     por destino. Los avisos con plazo llevan un lápiz para cambiar los días
//     o los kilómetros. Los cambios se guardan con el botón del coche.
//   - Datos: descargar la copia, enviarla a un móvil, cargarla y borrar.
//   - Diagnóstico: lo que ha pasado (cambios, órdenes, avisos) y la ficha que
//     se le aplica a cada coche.
//   - Ajustes: control con PIN y lectura de datos (son de la cuenta).
//
// Cómo habla con la integración
// -----------------------------
// Por WebSocket, con órdenes "dec_deepal/panel/..." (ver panel.py). Al abrir
// pide el estado completo ("state") y lo vuelve a pedir tras cada cambio. No
// guarda nada en el navegador.
//
// Idiomas: el del usuario en Home Assistant. La tabla de textos se genera a
// partir de idiomas/ (sección "panel"; ver docs/idiomas.md).
//
// Sin dependencias y sin Node: JavaScript plano. El código está repartido en
// frontend_panel/src/ y se une en un solo archivo (dec-deepal-panel.js) con
// tools/construir_tarjeta.py. Guía para tocarlo: docs/panel.md
// =============================================================================

(() => {
  // ── src/10_constantes.js ──────────────────────────────────────────────────
  const TAG = "dec-deepal-panel";
  if (customElements.get(TAG)) return;

  const DOMAIN = "dec_deepal";
  /** Prefijo de las órdenes del panel (panel.py). */
  const WS = "dec_deepal/panel/";

  /** Pestañas: clave (su nombre es el texto "tab_<clave>") e icono. */
  const TABS = [
    ["cars", "mdi:car-multiple"],
    ["alerts", "mdi:bell-ring"],
    ["data", "mdi:database"],
    ["diagnostics", "mdi:stethoscope"],
    ["settings", "mdi:cog"],
  ];

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

  // ── src/20_textos.js ──────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Textos por idioma
  // ---------------------------------------------------------------------------
  // FICHERO GENERADO a partir de idiomas/<idioma>.json (sección "panel") con
  // tools/generar_idiomas.py. Para cambiar un texto o añadir un idioma, editar
  // esos ficheros y volver a generar. Guía: docs/idiomas.md
  //
  //   BASE_LANGUAGE       idioma que se usa si el del usuario no está traducido
  //   BORROWED_LANGUAGES  idiomas sin traducción propia que usan la de otro
  //   TEXTS               { idioma: { clave: texto } }, ya completa (a un
  //                       idioma a medias se le rellena con el idioma base)
  const BASE_LANGUAGE = "en";
  const BORROWED_LANGUAGES = {"ca": "es", "eu": "es", "gl": "es"};
  const TEXTS = {
    "es": {
      "tab_cars": "Coches",
      "tab_alerts": "Avisos",
      "tab_data": "Datos",
      "tab_diagnostics": "Diagnóstico",
      "loading": "Cargando…",
      "retry": "Reintentar",
      "no_cars": "No hay ningún coche. Añade tu cuenta de Deepal en Ajustes → Dispositivos y servicios.",
      "error_generic": "No se ha podido completar. Inténtalo otra vez.",
      "day": "{value} día",
      "days": "{value} días",
      "or": " o ",
      "not_configured": "Sin modelo elegido",
      "sheet_verified": "Ficha verificada",
      "sheet_catalogue": "Ficha de catálogo",
      "battery": "Batería",
      "range": "Autonomía",
      "odometer": "Cuentakilómetros",
      "appearance": "Apariencia",
      "configure": "Configurar",
      "section_charge": "Carga",
      "section_warnings": "Testigos",
      "section_maintenance": "Mantenimiento",
      "section_itv": "ITV",
      "section_insurance": "Seguro",
      "section_appearance": "Apariencia",
      "not_set": "Sin configurar",
      "add_maintenance": "Activar el mantenimiento",
      "add_itv": "Añadir la ITV",
      "add_insurance": "Añadir el seguro",
      "feature_seat_heat": "Asientos calefactados",
      "feature_seat_vent": "Asientos ventilados",
      "feature_wheel_heat": "Volante calefactado",
      "feature_power_tailgate": "Portón eléctrico",
      "wheel_pro": "Llanta 18\"",
      "wheel_cover": "Llanta 20\" con tapacubos",
      "wheel_open": "Llanta 20\" sin tapacubos",
      "service_number": "{number}ª revisión",
      "overdue": "Vencido",
      "left": "Quedan {parts}",
      "overdue_since": "Vencida hace {days}",
      "cancel_until": "Límite para desistir: {date}",
      "renews_in": "Se renueva en {days}",
      "notify_to": "Avisar a",
      "n_notices": "{count} avisos",
      "edit_threshold": "Cambiar el plazo",
      "accept": "Aceptar",
      "cancel": "Cancelar",
      "unit_km": "km",
      "unit_days": "días",
      "when_km": "quedan {value} km",
      "when_days": "quedan {value} días",
      "when_days_deadline": "quedan {value} días para el límite",
      "when_maintenance_overdue": "el mismo día o al llegar a los km",
      "when_itv_overdue": "el mismo día",
      "when_insurance_last_day": "último día para desistir",
      "when_insurance_renewed": "el mismo día",
      "notice_charge_started": "Carga iniciada",
      "notice_charge_interrupted": "Carga interrumpida",
      "notice_charge_finished": "Carga terminada",
      "notice_warnings": "Testigos del cuadro",
      "notice_tires": "Neumáticos",
      "notice_key_battery": "Pila del mando baja",
      "notice_maintenance_t1": "Aviso tiempo 1",
      "notice_maintenance_t2": "Aviso tiempo 2",
      "notice_maintenance_t3": "Aviso tiempo 3",
      "notice_maintenance_k1": "Aviso kilometraje 1",
      "notice_maintenance_k2": "Aviso kilometraje 2",
      "notice_maintenance_k3": "Aviso kilometraje 3",
      "notice_maintenance_overdue": "Mantenimiento cumplido",
      "notice_itv_t1": "Aviso 1",
      "notice_itv_t2": "Aviso 2",
      "notice_itv_t3": "Aviso 3",
      "notice_itv_overdue": "ITV cumplida",
      "notice_insurance_c1": "Aviso desistimiento 1",
      "notice_insurance_c2": "Aviso desistimiento 2",
      "notice_insurance_last_day": "Desistimiento cumplido",
      "notice_insurance_r1": "Aviso renovación 1",
      "notice_insurance_r2": "Aviso renovación 2",
      "notice_insurance_renewed": "Seguro renovado",
      "unsaved": "Hay cambios sin guardar en este coche.",
      "alerts_help": "Marca a quién llega cada aviso. El lápiz cambia los días o los kilómetros de ese aviso; los plazos son de este coche.",
      "factory_thresholds": "Plazos de fábrica",
      "discard": "Descartar",
      "save": "Guardar",
      "saved": "Guardado",
      "copy_from": "Copiar de otro coche",
      "car": "Coche",
      "copy": "Copiar",
      "error_threshold_range_limits": "El plazo tiene que estar entre {low} y {high}.",
      "error_threshold_range": "Hay un plazo fuera de sus límites.",
      "error_threshold_order": "Los plazos tienen que ir de mayor a menor: el aviso 1 antes que el 2, y el 2 antes que el 3.",
      "error_not_found": "Ese coche ya no está en la cuenta.",
      "error_invalid": "Hay algún dato que no vale.",
      "error_invalid_file": "El fichero no es una copia de DEC Deepal o está dañado.",
      "error_newer_file": "La copia es de una versión más nueva de la integración. Actualiza DEC Deepal y vuelve a intentarlo.",
      "error_empty_file": "La copia no trae datos de ningún coche.",
      "error_required": "Faltan datos por rellenar.",
      "backup_title": "Copia de seguridad",
      "backup_help": "Mantenimiento, ITV, seguro y apariencia de tus coches. Los datos son del coche: no se pierden al quitar la cuenta.",
      "download_title": "Descargar una copia",
      "download_help": "Un fichero con los datos de todos los coches. Lleva la póliza y los teléfonos del seguro: guárdalo en un sitio seguro.",
      "download": "Descargar",
      "send_title": "Enviar la copia a un móvil",
      "send_help": "Llega una notificación; al tocarla se abre el navegador y se descarga. El enlace caduca en 10 minutos.",
      "send": "Enviar",
      "sent_to": "Notificación enviada a {device}.",
      "upload_title": "Cargar una copia",
      "upload_help": "Deja los coches del fichero como estaban en él. Los demás no se tocan.",
      "choose_file": "Elegir fichero",
      "imported": "Copia cargada: {cars}.",
      "stored_title": "Datos guardados",
      "stored_help": "Por coche, identificado por su bastidor.",
      "stored_none": "No hay datos guardados de ningún coche.",
      "in_account": "En la cuenta",
      "no_account": "Sin cuenta",
      "no_account_note": "Ya no está en ninguna cuenta",
      "delete": "Borrar",
      "delete_title": "Borrar datos guardados",
      "delete_confirm": "Se borran el mantenimiento, la ITV y el seguro de {name}. No se puede deshacer: descarga antes una copia si los quieres conservar.",
      "deleted": "Datos borrados.",
      "history_title": "Qué ha pasado",
      "history_help": "Cambios, órdenes y avisos desde el último reinicio. Es lo mismo que va en el fichero de diagnóstico.",
      "history_none": "Todavía no hay nada que enseñar.",
      "filter_all": "Todo",
      "filter_orders": "Órdenes",
      "filter_alerts": "Avisos",
      "filter_errors": "Errores",
      "sheets_title": "Ficha de cada coche",
      "sheets_help": "Qué equipamiento da por bueno la integración y de dónde lo saca.",
      "diagnostics_file": "Diagnóstico",
      "ev_alert": "Aviso enviado: {name}",
      "ev_targets": "{count} destinos",
      "ev_wake": "Despertar del coche",
      "ev_command": "Orden: {name}",
      "ev_code": "código",
      "today": "Hoy",
      "yesterday": "Ayer",
      "enabled": "Activado",
      "mt_services_done": "Revisiones ya pasadas",
      "mt_interval_km": "Intervalo (km)",
      "mt_interval_months": "Intervalo (meses)",
      "mt_register": "Registrar revisión hecha",
      "mt_register_help": "Anota la {number}ª revisión de {name} y empieza a contar la siguiente.",
      "date": "Fecha",
      "mt_km": "Kilómetros",
      "register": "Registrar",
      "registered": "Registrado",
      "itv_registration": "Fecha de matriculación",
      "itv_last": "Última ITV pasada",
      "itv_next": "Próxima ITV (a mano)",
      "itv_register": "Registrar ITV pasada",
      "itv_register_help": "Anota que {name} ha pasado la ITV y calcula la siguiente.",
      "ins_company": "Compañía",
      "ins_policy": "Número de póliza",
      "ins_kind": "Tipo de seguro",
      "ins_renewal": "Fecha de renovación",
      "ins_notice": "Días de preaviso para desistir",
      "ins_phone_assistance": "Teléfono de asistencia",
      "ins_phone_company": "Teléfono de la compañía",
      "kind_third_party": "Terceros",
      "kind_third_party_plus": "Terceros ampliado",
      "kind_comprehensive_excess": "Todo riesgo con franquicia",
      "kind_comprehensive": "Todo riesgo sin franquicia",
      "tab_settings": "Ajustes",
      "appearance_title": "Apariencia de {name}",
      "appearance_help": "Decide la foto, la vista del coche y qué equipamiento se da por bueno.",
      "model": "Modelo",
      "trim": "Versión",
      "color": "Color",
      "wheels": "Llanta",
      "model_ev": "Eléctrico",
      "model_phev": "Híbrido enchufable",
      "trim_full": "Asientos y volante calefactados, portón eléctrico",
      "trim_basic": "Sin asientos ni volante calefactados",
      "account": "Cuenta: {name}",
      "pin_title": "Control remoto con PIN",
      "pin_help": "Para bloquear y desbloquear, ventanillas y maletero. Es el PIN de la app oficial de Deepal, con la misma cuenta. Vale para todos los coches de la cuenta.",
      "pin_enabled": "Órdenes con PIN",
      "pin_enabled_help": "Sin esto, la tarjeta solo enseña el estado de puertas, ventanillas y maletero.",
      "pin": "PIN",
      "pin_field_help": "Se comprueba con Deepal al guardar. Déjalo vacío para no cambiarlo.",
      "pin_checked": "Comprobado",
      "show_pin": "Ver el PIN",
      "pin_mode_title": "Cómo se usan las órdenes",
      "mode_direct": "Directo",
      "mode_direct_help": "La orden se envía al pulsar, tras confirmar. Lo más cómodo.",
      "mode_armed": "Desbloquear antes",
      "mode_armed_help": "Hay que activar primero «Desbloqueo de acciones» y solo vale durante un rato. Lo más seguro.",
      "arm_seconds": "Cuánto dura el desbloqueo",
      "arm_seconds_help": "Pasado ese tiempo, las órdenes con PIN se vuelven a bloquear solas.",
      "seconds": "{value} s",
      "arm_notify": "Avisar al desbloquear",
      "arm_notify_help": "Una notificación en Home Assistant cada vez que se permiten las órdenes.",
      "reading_title": "Lectura de datos",
      "reading_help": "Cómo y cada cuánto se pregunta al coche.",
      "scan_title": "Intervalo de lectura",
      "scan_help": "Cada cuánto se leen los datos del coche. Muy bajo puede hacer que Deepal limite la cuenta.",
      "minutes": "{value} min",
      "wake_title": "Despertar el coche cuando haga falta",
      "wake_help": "Al pulsar Actualizar y antes de una orden con PIN. Nunca en las lecturas automáticas, para cuidar la batería de 12 V.",
      "manual_bev": "Manual BEV",
      "manual_phev": "Manual PHEV",
      "manual_help": "El enlace que abre la tarjeta en Otros → Manual. Vacío para usar el oficial.",
      "debug_title": "Modo depuración",
      "debug_help": "Guarda peticiones y respuestas completas (sin datos personales) en los diagnósticos.",
      "save_check": "Guardar",
      "unsaved_settings": "Hay cambios sin guardar.",
      "error_pin_required": "Escribe el PIN.",
      "error_pin_invalid": "El PIN no es correcto. Es el de la app oficial de Deepal, con esta misma cuenta.",
      "error_pin_rate_limited": "Demasiados intentos con el PIN. Espera unos minutos antes de volver a probar.",
      "error_cannot_connect": "No se ha podido conectar con Deepal. Inténtalo más tarde.",
      "error_invalid_url": "El enlace del manual no es válido: tiene que empezar por http:// o https://.",
      "error_unknown_model": "Ese modelo no está en el catálogo.",
      "close": "Cerrar",
      "other": "Otro",
      "history": "Historial",
      "manual": "Manual",
      "copied": "Copiado: {text}",
      "form_maintenance": "Configurar el mantenimiento",
      "form_itv": "Configurar la ITV",
      "form_insurance": "Configurar el seguro",
      "form_maintenance_off": "Desactivado: se quitan sus entidades, su testigo en la tarjeta y sus avisos. El historial se pierde.",
      "form_itv_off": "Desactivada: se quitan sus entidades, su testigo en la tarjeta y sus avisos.",
      "form_insurance_off": "Desactivado: se quitan sus entidades, su testigo en la tarjeta y sus avisos.",
      "first_notice": "El primer aviso, {days} días antes",
      "mt_last": "Última revisión",
      "mt_last_help": "Si el coche aún no ha pasado ninguna, pon la fecha de matriculación y 0 km.",
      "mt_next_is": "La próxima será la {number}ª revisión.",
      "mt_km_then": "Kilómetros entonces",
      "mt_use_odometer": "Usar los del coche ahora ({km} km)",
      "mt_every": "Cada cuánto",
      "mt_every_help": "El manual pide acortarlo con trayectos cortos repetidos, polvo, barro, frío extremo o sal.",
      "mt_interval_manual": "El del manual",
      "mt_interval_value": "{km} km o {months} meses",
      "mt_interval_other": "Lo eliges tú",
      "mt_preview": "Próxima revisión: {date} o a los {km} km",
      "mt_whichever": "Lo que llegue antes: el {date} o a los {km} km.",
      "by_time": "Por tiempo",
      "by_km": "Por kilómetros",
      "mt_km_detail": "Ahora {now} km · toca a los {due}",
      "mt_this_service": "Qué toca en esta revisión",
      "n_operations": "{count} operaciones",
      "mt_no_plan": "Este modelo no tiene plan de mantenimiento en el catálogo.",
      "mt_next_adds": "En la siguiente ({number}ª) se añade",
      "mt_history_item": "{number}ª revisión · {date} · {km} km",
      "mt_no_history": "Todavía no hay revisiones registradas.",
      "itv_registration_title": "Matriculación",
      "itv_registration_help": "Viene en el permiso de circulación. Con ella se calcula sola la primera ITV.",
      "itv_passed_title": "ITV ya pasadas",
      "itv_passed_help": "Solo si el coche ya ha pasado alguna.",
      "itv_passed": "Ya ha pasado alguna ITV",
      "itv_next_title": "Próxima ITV",
      "itv_next_rules": "Se calcula con las normas del país de la cuenta.",
      "itv_next_auto": "Calcularla sola",
      "itv_next_manual": "Poner otra fecha",
      "itv_next_manual_note": "Si la estación te dio una distinta",
      "itv_preview": "Próxima ITV: {date}",
      "itv_manual_date": "fecha puesta a mano",
      "itv_age": "{years} años",
      "itv_none_yet": "Ninguna todavía",
      "itv_first_at": "La primera, a los {years} años",
      "itv_rules_title": "Cada cuánto",
      "itv_rules": "La primera a los {first} años; después cada {interval} y, desde los {reduced} años, cada año.",
      "itv_history_item": "ITV pasada el {date}",
      "itv_no_history": "Todavía no hay ninguna ITV registrada.",
      "ins_policy_title": "La póliza",
      "ins_policy_help": "El número de póliza y los teléfonos solo se ven en la tarjeta y en el panel; no salen en los diagnósticos.",
      "ins_renewal_title": "Renovación",
      "ins_renewal_help": "El seguro se renueva solo cada año. Para no renovar hay que avisar antes.",
      "ins_renews_on": "Se renueva el",
      "ins_notice_days": "Días de preaviso",
      "ins_phones_title": "Teléfonos",
      "ins_phones_help": "Para llamar con un toque desde la tarjeta y desde aquí.",
      "ins_preview": "Último día para desistir: {date}",
      "ins_preview_passed": "Ese plazo ya pasó. Se renueva el {date}.",
      "ins_dates": "Fechas",
      "ins_to_cancel": "Para desistir",
      "ins_to_renewal": "Para la renovación",
      "ins_deadline_passed": "Plazo pasado",
      "ins_deadline_on": "Último día: {date}",
      "ins_renews_itself": "Se renueva solo el {date}",
      "ins_assistance": "Asistencia"
    },
    "en": {
      "tab_cars": "Vehicles",
      "tab_alerts": "Notifications",
      "tab_data": "Data",
      "tab_diagnostics": "Diagnostics",
      "loading": "Loading…",
      "retry": "Retry",
      "no_cars": "There are no vehicles. Add your Deepal account under Settings → Devices and services.",
      "error_generic": "That could not be completed. Try again.",
      "day": "{value} day",
      "days": "{value} days",
      "or": " or ",
      "not_configured": "No model chosen",
      "sheet_verified": "Verified sheet",
      "sheet_catalogue": "Catalogue sheet",
      "battery": "Battery",
      "range": "Range",
      "odometer": "Odometer",
      "appearance": "Appearance",
      "configure": "Configure",
      "section_charge": "Charging",
      "section_warnings": "Warnings",
      "section_maintenance": "Servicing",
      "section_itv": "ITV",
      "section_insurance": "Insurance",
      "section_appearance": "Appearance",
      "not_set": "Not set up",
      "add_maintenance": "Enable servicing",
      "add_itv": "Add the ITV",
      "add_insurance": "Add the insurance",
      "feature_seat_heat": "Heated seats",
      "feature_seat_vent": "Ventilated seats",
      "feature_wheel_heat": "Heated steering wheel",
      "feature_power_tailgate": "Power tailgate",
      "wheel_pro": "18\" wheels",
      "wheel_cover": "20\" wheels with aero covers",
      "wheel_open": "20\" wheels without covers",
      "service_number": "Service no. {number}",
      "overdue": "Overdue",
      "left": "{parts} left",
      "overdue_since": "Overdue by {days}",
      "cancel_until": "Cancellation deadline: {date}",
      "renews_in": "Renews in {days}",
      "notify_to": "Notify",
      "n_notices": "{count} notifications",
      "edit_threshold": "Change the lead time",
      "accept": "Accept",
      "cancel": "Cancel",
      "unit_km": "km",
      "unit_days": "days",
      "when_km": "{value} km left",
      "when_days": "{value} days left",
      "when_days_deadline": "{value} days before the deadline",
      "when_maintenance_overdue": "on the day or when the km are reached",
      "when_itv_overdue": "on the day",
      "when_insurance_last_day": "last day to cancel",
      "when_insurance_renewed": "on the day",
      "notice_charge_started": "Charging started",
      "notice_charge_interrupted": "Charging interrupted",
      "notice_charge_finished": "Charging finished",
      "notice_warnings": "Warning lights",
      "notice_tires": "Tyres",
      "notice_key_battery": "Key fob battery low",
      "notice_maintenance_t1": "Time notice 1",
      "notice_maintenance_t2": "Time notice 2",
      "notice_maintenance_t3": "Time notice 3",
      "notice_maintenance_k1": "Distance notice 1",
      "notice_maintenance_k2": "Distance notice 2",
      "notice_maintenance_k3": "Distance notice 3",
      "notice_maintenance_overdue": "Service due",
      "notice_itv_t1": "Notice 1",
      "notice_itv_t2": "Notice 2",
      "notice_itv_t3": "Notice 3",
      "notice_itv_overdue": "ITV due",
      "notice_insurance_c1": "Cancellation notice 1",
      "notice_insurance_c2": "Cancellation notice 2",
      "notice_insurance_last_day": "Cancellation deadline",
      "notice_insurance_r1": "Renewal notice 1",
      "notice_insurance_r2": "Renewal notice 2",
      "notice_insurance_renewed": "Insurance renewed",
      "unsaved": "This vehicle has unsaved changes.",
      "alerts_help": "Tick who gets each notification. The pencil changes the days or kilometres of that notification; lead times belong to this vehicle.",
      "factory_thresholds": "Default lead times",
      "discard": "Discard",
      "save": "Save",
      "saved": "Saved",
      "copy_from": "Copy from another vehicle",
      "car": "Vehicle",
      "copy": "Copy",
      "error_threshold_range_limits": "The lead time must be between {low} and {high}.",
      "error_threshold_range": "A lead time is out of range.",
      "error_threshold_order": "Lead times must go from longest to shortest: notice 1 before 2, and 2 before 3.",
      "error_not_found": "That vehicle is no longer in the account.",
      "error_invalid": "Some of the data is not valid.",
      "error_invalid_file": "The file is not a DEC Deepal backup, or it is damaged.",
      "error_newer_file": "The backup comes from a newer version of the integration. Update DEC Deepal and try again.",
      "error_empty_file": "The backup has no data for any vehicle.",
      "error_required": "Some fields are missing.",
      "backup_title": "Backup",
      "backup_help": "Servicing, ITV, insurance and appearance of your vehicles. The data belongs to the vehicle: it is not lost when the account is removed.",
      "download_title": "Download a backup",
      "download_help": "A file with the data of every vehicle. It contains the policy number and the insurance phone numbers: keep it somewhere safe.",
      "download": "Download",
      "send_title": "Send the backup to a phone",
      "send_help": "A notification arrives; tapping it opens the browser and downloads the file. The link expires in 10 minutes.",
      "send": "Send",
      "sent_to": "Notification sent to {device}.",
      "upload_title": "Load a backup",
      "upload_help": "Leaves the vehicles in the file as they were in it. Other vehicles are left untouched.",
      "choose_file": "Choose file",
      "imported": "Backup loaded: {cars}.",
      "stored_title": "Stored data",
      "stored_help": "Per vehicle, identified by its VIN.",
      "stored_none": "There is no stored data for any vehicle.",
      "in_account": "In the account",
      "no_account": "No account",
      "no_account_note": "No longer in any account",
      "delete": "Delete",
      "delete_title": "Delete stored data",
      "delete_confirm": "The servicing, ITV and insurance of {name} will be deleted. This cannot be undone: download a backup first if you want to keep them.",
      "deleted": "Data deleted.",
      "history_title": "What has happened",
      "history_help": "Changes, commands and notifications since the last restart. The same goes into the diagnostics file.",
      "history_none": "Nothing to show yet.",
      "filter_all": "All",
      "filter_orders": "Commands",
      "filter_alerts": "Notifications",
      "filter_errors": "Errors",
      "sheets_title": "Sheet of each vehicle",
      "sheets_help": "Which equipment the integration assumes, and where it gets it from.",
      "diagnostics_file": "Diagnostics",
      "ev_alert": "Notification sent: {name}",
      "ev_targets": "{count} recipients",
      "ev_wake": "Vehicle wake-up",
      "ev_command": "Command: {name}",
      "ev_code": "code",
      "today": "Today",
      "yesterday": "Yesterday",
      "enabled": "Enabled",
      "mt_services_done": "Services already done",
      "mt_interval_km": "Interval (km)",
      "mt_interval_months": "Interval (months)",
      "mt_register": "Register a completed service",
      "mt_register_help": "Records service no. {number} of {name} and starts counting towards the next one.",
      "date": "Date",
      "mt_km": "Kilometres",
      "register": "Register",
      "registered": "Registered",
      "itv_registration": "Registration date",
      "itv_last": "Last ITV passed",
      "itv_next": "Next ITV (manual)",
      "itv_register": "Register a passed ITV",
      "itv_register_help": "Records that {name} has passed the ITV and calculates the next one.",
      "ins_company": "Company",
      "ins_policy": "Policy number",
      "ins_kind": "Type of insurance",
      "ins_renewal": "Renewal date",
      "ins_notice": "Notice days to cancel",
      "ins_phone_assistance": "Assistance phone",
      "ins_phone_company": "Company phone",
      "kind_third_party": "Third party",
      "kind_third_party_plus": "Third party plus",
      "kind_comprehensive_excess": "Comprehensive with excess",
      "kind_comprehensive": "Comprehensive without excess",
      "tab_settings": "Settings",
      "appearance_title": "Appearance of {name}",
      "appearance_help": "Decides the photo, the view of the vehicle and which equipment is assumed.",
      "model": "Model",
      "trim": "Version",
      "color": "Colour",
      "wheels": "Wheels",
      "model_ev": "Electric",
      "model_phev": "Plug-in hybrid",
      "trim_full": "Heated seats and steering wheel, power tailgate",
      "trim_basic": "No heated seats or steering wheel",
      "account": "Account: {name}",
      "pin_title": "Remote control with PIN",
      "pin_help": "To lock and unlock, windows and boot. It is the PIN of the official Deepal app, with the same account. It applies to every vehicle in the account.",
      "pin_enabled": "PIN commands",
      "pin_enabled_help": "Without this, the card only shows the state of doors, windows and boot.",
      "pin": "PIN",
      "pin_field_help": "It is checked with Deepal on saving. Leave it empty to keep the current one.",
      "pin_checked": "Checked",
      "show_pin": "Show the PIN",
      "pin_mode_title": "How commands are used",
      "mode_direct": "Direct",
      "mode_direct_help": "The command is sent when you tap, after confirming. The most convenient.",
      "mode_armed": "Unlock first",
      "mode_armed_help": "You first have to enable \"Unlock PIN actions\", and it only lasts for a while. The safest.",
      "arm_seconds": "How long the unlock lasts",
      "arm_seconds_help": "After that time, PIN commands lock again on their own.",
      "seconds": "{value} s",
      "arm_notify": "Notify on unlock",
      "arm_notify_help": "A notification in Home Assistant every time commands are allowed.",
      "reading_title": "Data reading",
      "reading_help": "How and how often the vehicle is asked.",
      "scan_title": "Reading interval",
      "scan_help": "How often the vehicle data is read. Very low values may make Deepal throttle the account.",
      "minutes": "{value} min",
      "wake_title": "Wake the vehicle when needed",
      "wake_help": "When you tap Refresh and before a PIN command. Never on automatic readings, to protect the 12 V battery.",
      "manual_bev": "BEV manual",
      "manual_phev": "PHEV manual",
      "manual_help": "The link the card opens under More → Manual. Empty to use the official one.",
      "debug_title": "Debug mode",
      "debug_help": "Stores full requests and responses (without personal data) in the diagnostics.",
      "save_check": "Save",
      "unsaved_settings": "There are unsaved changes.",
      "error_pin_required": "Enter the PIN.",
      "error_pin_invalid": "The PIN is not correct. It is the one from the official Deepal app, with this same account.",
      "error_pin_rate_limited": "Too many PIN attempts. Wait a few minutes before trying again.",
      "error_cannot_connect": "Could not connect to Deepal. Try again later.",
      "error_invalid_url": "The manual link is not valid: it must start with http:// or https://.",
      "error_unknown_model": "That model is not in the catalogue.",
      "close": "Close",
      "other": "Other",
      "history": "History",
      "manual": "Manual",
      "copied": "Copied: {text}",
      "form_maintenance": "Set up servicing",
      "form_itv": "Set up the ITV",
      "form_insurance": "Set up the insurance",
      "form_maintenance_off": "Disabled: its entities, its indicator on the card and its notifications are removed. The history is lost.",
      "form_itv_off": "Disabled: its entities, its indicator on the card and its notifications are removed.",
      "form_insurance_off": "Disabled: its entities, its indicator on the card and its notifications are removed.",
      "first_notice": "First notification {days} days before",
      "mt_last": "Last service",
      "mt_last_help": "If the vehicle has not had any yet, enter the registration date and 0 km.",
      "mt_next_is": "The next one will be service no. {number}.",
      "mt_km_then": "Kilometres then",
      "mt_use_odometer": "Use the vehicle's current reading ({km} km)",
      "mt_every": "How often",
      "mt_every_help": "The manual asks for a shorter interval with repeated short trips, dust, mud, extreme cold or salt.",
      "mt_interval_manual": "From the manual",
      "mt_interval_value": "{km} km or {months} months",
      "mt_interval_other": "You choose",
      "mt_preview": "Next service: {date} or at {km} km",
      "mt_whichever": "Whichever comes first: {date} or at {km} km.",
      "by_time": "By time",
      "by_km": "By distance",
      "mt_km_detail": "Now {now} km · due at {due}",
      "mt_this_service": "What this service includes",
      "n_operations": "{count} operations",
      "mt_no_plan": "This model has no servicing plan in the catalogue.",
      "mt_next_adds": "The next one (no. {number}) adds",
      "mt_history_item": "Service no. {number} · {date} · {km} km",
      "mt_no_history": "No services have been registered yet.",
      "itv_registration_title": "Registration",
      "itv_registration_help": "It is on the registration certificate. The first ITV is calculated from it.",
      "itv_passed_title": "ITVs already passed",
      "itv_passed_help": "Only if the vehicle has already passed one.",
      "itv_passed": "It has already passed an ITV",
      "itv_next_title": "Next ITV",
      "itv_next_rules": "It is calculated with the rules of the account's country.",
      "itv_next_auto": "Calculate it",
      "itv_next_manual": "Set another date",
      "itv_next_manual_note": "If the station gave you a different one",
      "itv_preview": "Next ITV: {date}",
      "itv_manual_date": "date set by hand",
      "itv_age": "{years} years",
      "itv_none_yet": "None yet",
      "itv_first_at": "The first one, at {years} years",
      "itv_rules_title": "How often",
      "itv_rules": "The first at {first} years; then every {interval} and, from {reduced} years on, every year.",
      "itv_history_item": "ITV passed on {date}",
      "itv_no_history": "No ITV has been registered yet.",
      "ins_policy_title": "The policy",
      "ins_policy_help": "The policy number and the phone numbers are only shown on the card and in the panel; they never appear in the diagnostics.",
      "ins_renewal_title": "Renewal",
      "ins_renewal_help": "The insurance renews itself every year. To cancel, you have to give notice beforehand.",
      "ins_renews_on": "It renews on",
      "ins_notice_days": "Notice days",
      "ins_phones_title": "Phone numbers",
      "ins_phones_help": "To call with one tap from the card and from here.",
      "ins_preview": "Last day to cancel: {date}",
      "ins_preview_passed": "That deadline has passed. It renews on {date}.",
      "ins_dates": "Dates",
      "ins_to_cancel": "To cancel",
      "ins_to_renewal": "To renewal",
      "ins_deadline_passed": "Deadline passed",
      "ins_deadline_on": "Last day: {date}",
      "ins_renews_itself": "It renews itself on {date}",
      "ins_assistance": "Assistance"
    },
    "pt": {
      "tab_cars": "Vehicles",
      "tab_alerts": "Notifications",
      "tab_data": "Data",
      "tab_diagnostics": "Diagnostics",
      "loading": "Loading…",
      "retry": "Retry",
      "no_cars": "There are no vehicles. Add your Deepal account under Settings → Devices and services.",
      "error_generic": "That could not be completed. Try again.",
      "day": "{value} day",
      "days": "{value} days",
      "or": " or ",
      "not_configured": "No model chosen",
      "sheet_verified": "Verified sheet",
      "sheet_catalogue": "Catalogue sheet",
      "battery": "Battery",
      "range": "Range",
      "odometer": "Odometer",
      "appearance": "Appearance",
      "configure": "Configure",
      "section_charge": "Charging",
      "section_warnings": "Warnings",
      "section_maintenance": "Servicing",
      "section_itv": "ITV",
      "section_insurance": "Insurance",
      "section_appearance": "Appearance",
      "not_set": "Not set up",
      "add_maintenance": "Enable servicing",
      "add_itv": "Add the ITV",
      "add_insurance": "Add the insurance",
      "feature_seat_heat": "Heated seats",
      "feature_seat_vent": "Ventilated seats",
      "feature_wheel_heat": "Heated steering wheel",
      "feature_power_tailgate": "Power tailgate",
      "wheel_pro": "18\" wheels",
      "wheel_cover": "20\" wheels with aero covers",
      "wheel_open": "20\" wheels without covers",
      "service_number": "Service no. {number}",
      "overdue": "Overdue",
      "left": "{parts} left",
      "overdue_since": "Overdue by {days}",
      "cancel_until": "Cancellation deadline: {date}",
      "renews_in": "Renews in {days}",
      "notify_to": "Notify",
      "n_notices": "{count} notifications",
      "edit_threshold": "Change the lead time",
      "accept": "Accept",
      "cancel": "Cancel",
      "unit_km": "km",
      "unit_days": "days",
      "when_km": "{value} km left",
      "when_days": "{value} days left",
      "when_days_deadline": "{value} days before the deadline",
      "when_maintenance_overdue": "on the day or when the km are reached",
      "when_itv_overdue": "on the day",
      "when_insurance_last_day": "last day to cancel",
      "when_insurance_renewed": "on the day",
      "notice_charge_started": "Charging started",
      "notice_charge_interrupted": "Charging interrupted",
      "notice_charge_finished": "Charging finished",
      "notice_warnings": "Warning lights",
      "notice_tires": "Tyres",
      "notice_key_battery": "Key fob battery low",
      "notice_maintenance_t1": "Time notice 1",
      "notice_maintenance_t2": "Time notice 2",
      "notice_maintenance_t3": "Time notice 3",
      "notice_maintenance_k1": "Distance notice 1",
      "notice_maintenance_k2": "Distance notice 2",
      "notice_maintenance_k3": "Distance notice 3",
      "notice_maintenance_overdue": "Service due",
      "notice_itv_t1": "Notice 1",
      "notice_itv_t2": "Notice 2",
      "notice_itv_t3": "Notice 3",
      "notice_itv_overdue": "ITV due",
      "notice_insurance_c1": "Cancellation notice 1",
      "notice_insurance_c2": "Cancellation notice 2",
      "notice_insurance_last_day": "Cancellation deadline",
      "notice_insurance_r1": "Renewal notice 1",
      "notice_insurance_r2": "Renewal notice 2",
      "notice_insurance_renewed": "Insurance renewed",
      "unsaved": "This vehicle has unsaved changes.",
      "alerts_help": "Tick who gets each notification. The pencil changes the days or kilometres of that notification; lead times belong to this vehicle.",
      "factory_thresholds": "Default lead times",
      "discard": "Discard",
      "save": "Save",
      "saved": "Saved",
      "copy_from": "Copy from another vehicle",
      "car": "Vehicle",
      "copy": "Copy",
      "error_threshold_range_limits": "The lead time must be between {low} and {high}.",
      "error_threshold_range": "A lead time is out of range.",
      "error_threshold_order": "Lead times must go from longest to shortest: notice 1 before 2, and 2 before 3.",
      "error_not_found": "That vehicle is no longer in the account.",
      "error_invalid": "Some of the data is not valid.",
      "error_invalid_file": "The file is not a DEC Deepal backup, or it is damaged.",
      "error_newer_file": "The backup comes from a newer version of the integration. Update DEC Deepal and try again.",
      "error_empty_file": "The backup has no data for any vehicle.",
      "error_required": "Some fields are missing.",
      "backup_title": "Backup",
      "backup_help": "Servicing, ITV, insurance and appearance of your vehicles. The data belongs to the vehicle: it is not lost when the account is removed.",
      "download_title": "Download a backup",
      "download_help": "A file with the data of every vehicle. It contains the policy number and the insurance phone numbers: keep it somewhere safe.",
      "download": "Download",
      "send_title": "Send the backup to a phone",
      "send_help": "A notification arrives; tapping it opens the browser and downloads the file. The link expires in 10 minutes.",
      "send": "Send",
      "sent_to": "Notification sent to {device}.",
      "upload_title": "Load a backup",
      "upload_help": "Leaves the vehicles in the file as they were in it. Other vehicles are left untouched.",
      "choose_file": "Choose file",
      "imported": "Backup loaded: {cars}.",
      "stored_title": "Stored data",
      "stored_help": "Per vehicle, identified by its VIN.",
      "stored_none": "There is no stored data for any vehicle.",
      "in_account": "In the account",
      "no_account": "No account",
      "no_account_note": "No longer in any account",
      "delete": "Delete",
      "delete_title": "Delete stored data",
      "delete_confirm": "The servicing, ITV and insurance of {name} will be deleted. This cannot be undone: download a backup first if you want to keep them.",
      "deleted": "Data deleted.",
      "history_title": "What has happened",
      "history_help": "Changes, commands and notifications since the last restart. The same goes into the diagnostics file.",
      "history_none": "Nothing to show yet.",
      "filter_all": "All",
      "filter_orders": "Commands",
      "filter_alerts": "Notifications",
      "filter_errors": "Errors",
      "sheets_title": "Sheet of each vehicle",
      "sheets_help": "Which equipment the integration assumes, and where it gets it from.",
      "diagnostics_file": "Diagnostics",
      "ev_alert": "Notification sent: {name}",
      "ev_targets": "{count} recipients",
      "ev_wake": "Vehicle wake-up",
      "ev_command": "Command: {name}",
      "ev_code": "code",
      "today": "Today",
      "yesterday": "Yesterday",
      "enabled": "Enabled",
      "mt_services_done": "Services already done",
      "mt_interval_km": "Interval (km)",
      "mt_interval_months": "Interval (months)",
      "mt_register": "Register a completed service",
      "mt_register_help": "Records service no. {number} of {name} and starts counting towards the next one.",
      "date": "Date",
      "mt_km": "Kilometres",
      "register": "Register",
      "registered": "Registered",
      "itv_registration": "Registration date",
      "itv_last": "Last ITV passed",
      "itv_next": "Next ITV (manual)",
      "itv_register": "Register a passed ITV",
      "itv_register_help": "Records that {name} has passed the ITV and calculates the next one.",
      "ins_company": "Company",
      "ins_policy": "Policy number",
      "ins_kind": "Type of insurance",
      "ins_renewal": "Renewal date",
      "ins_notice": "Notice days to cancel",
      "ins_phone_assistance": "Assistance phone",
      "ins_phone_company": "Company phone",
      "kind_third_party": "Third party",
      "kind_third_party_plus": "Third party plus",
      "kind_comprehensive_excess": "Comprehensive with excess",
      "kind_comprehensive": "Comprehensive without excess",
      "tab_settings": "Settings",
      "appearance_title": "Appearance of {name}",
      "appearance_help": "Decides the photo, the view of the vehicle and which equipment is assumed.",
      "model": "Model",
      "trim": "Version",
      "color": "Colour",
      "wheels": "Wheels",
      "model_ev": "Electric",
      "model_phev": "Plug-in hybrid",
      "trim_full": "Heated seats and steering wheel, power tailgate",
      "trim_basic": "No heated seats or steering wheel",
      "account": "Account: {name}",
      "pin_title": "Remote control with PIN",
      "pin_help": "To lock and unlock, windows and boot. It is the PIN of the official Deepal app, with the same account. It applies to every vehicle in the account.",
      "pin_enabled": "PIN commands",
      "pin_enabled_help": "Without this, the card only shows the state of doors, windows and boot.",
      "pin": "PIN",
      "pin_field_help": "It is checked with Deepal on saving. Leave it empty to keep the current one.",
      "pin_checked": "Checked",
      "show_pin": "Show the PIN",
      "pin_mode_title": "How commands are used",
      "mode_direct": "Direct",
      "mode_direct_help": "The command is sent when you tap, after confirming. The most convenient.",
      "mode_armed": "Unlock first",
      "mode_armed_help": "You first have to enable \"Unlock PIN actions\", and it only lasts for a while. The safest.",
      "arm_seconds": "How long the unlock lasts",
      "arm_seconds_help": "After that time, PIN commands lock again on their own.",
      "seconds": "{value} s",
      "arm_notify": "Notify on unlock",
      "arm_notify_help": "A notification in Home Assistant every time commands are allowed.",
      "reading_title": "Data reading",
      "reading_help": "How and how often the vehicle is asked.",
      "scan_title": "Reading interval",
      "scan_help": "How often the vehicle data is read. Very low values may make Deepal throttle the account.",
      "minutes": "{value} min",
      "wake_title": "Wake the vehicle when needed",
      "wake_help": "When you tap Refresh and before a PIN command. Never on automatic readings, to protect the 12 V battery.",
      "manual_bev": "BEV manual",
      "manual_phev": "PHEV manual",
      "manual_help": "The link the card opens under More → Manual. Empty to use the official one.",
      "debug_title": "Debug mode",
      "debug_help": "Stores full requests and responses (without personal data) in the diagnostics.",
      "save_check": "Save",
      "unsaved_settings": "There are unsaved changes.",
      "error_pin_required": "Enter the PIN.",
      "error_pin_invalid": "The PIN is not correct. It is the one from the official Deepal app, with this same account.",
      "error_pin_rate_limited": "Too many PIN attempts. Wait a few minutes before trying again.",
      "error_cannot_connect": "Could not connect to Deepal. Try again later.",
      "error_invalid_url": "The manual link is not valid: it must start with http:// or https://.",
      "error_unknown_model": "That model is not in the catalogue.",
      "close": "Close",
      "other": "Other",
      "history": "History",
      "manual": "Manual",
      "copied": "Copied: {text}",
      "form_maintenance": "Set up servicing",
      "form_itv": "Set up the ITV",
      "form_insurance": "Set up the insurance",
      "form_maintenance_off": "Disabled: its entities, its indicator on the card and its notifications are removed. The history is lost.",
      "form_itv_off": "Disabled: its entities, its indicator on the card and its notifications are removed.",
      "form_insurance_off": "Disabled: its entities, its indicator on the card and its notifications are removed.",
      "first_notice": "First notification {days} days before",
      "mt_last": "Last service",
      "mt_last_help": "If the vehicle has not had any yet, enter the registration date and 0 km.",
      "mt_next_is": "The next one will be service no. {number}.",
      "mt_km_then": "Kilometres then",
      "mt_use_odometer": "Use the vehicle's current reading ({km} km)",
      "mt_every": "How often",
      "mt_every_help": "The manual asks for a shorter interval with repeated short trips, dust, mud, extreme cold or salt.",
      "mt_interval_manual": "From the manual",
      "mt_interval_value": "{km} km or {months} months",
      "mt_interval_other": "You choose",
      "mt_preview": "Next service: {date} or at {km} km",
      "mt_whichever": "Whichever comes first: {date} or at {km} km.",
      "by_time": "By time",
      "by_km": "By distance",
      "mt_km_detail": "Now {now} km · due at {due}",
      "mt_this_service": "What this service includes",
      "n_operations": "{count} operations",
      "mt_no_plan": "This model has no servicing plan in the catalogue.",
      "mt_next_adds": "The next one (no. {number}) adds",
      "mt_history_item": "Service no. {number} · {date} · {km} km",
      "mt_no_history": "No services have been registered yet.",
      "itv_registration_title": "Registration",
      "itv_registration_help": "It is on the registration certificate. The first ITV is calculated from it.",
      "itv_passed_title": "ITVs already passed",
      "itv_passed_help": "Only if the vehicle has already passed one.",
      "itv_passed": "It has already passed an ITV",
      "itv_next_title": "Next ITV",
      "itv_next_rules": "It is calculated with the rules of the account's country.",
      "itv_next_auto": "Calculate it",
      "itv_next_manual": "Set another date",
      "itv_next_manual_note": "If the station gave you a different one",
      "itv_preview": "Next ITV: {date}",
      "itv_manual_date": "date set by hand",
      "itv_age": "{years} years",
      "itv_none_yet": "None yet",
      "itv_first_at": "The first one, at {years} years",
      "itv_rules_title": "How often",
      "itv_rules": "The first at {first} years; then every {interval} and, from {reduced} years on, every year.",
      "itv_history_item": "ITV passed on {date}",
      "itv_no_history": "No ITV has been registered yet.",
      "ins_policy_title": "The policy",
      "ins_policy_help": "The policy number and the phone numbers are only shown on the card and in the panel; they never appear in the diagnostics.",
      "ins_renewal_title": "Renewal",
      "ins_renewal_help": "The insurance renews itself every year. To cancel, you have to give notice beforehand.",
      "ins_renews_on": "It renews on",
      "ins_notice_days": "Notice days",
      "ins_phones_title": "Phone numbers",
      "ins_phones_help": "To call with one tap from the card and from here.",
      "ins_preview": "Last day to cancel: {date}",
      "ins_preview_passed": "That deadline has passed. It renews on {date}.",
      "ins_dates": "Dates",
      "ins_to_cancel": "To cancel",
      "ins_to_renewal": "To renewal",
      "ins_deadline_passed": "Deadline passed",
      "ins_deadline_on": "Last day: {date}",
      "ins_renews_itself": "It renews itself on {date}",
      "ins_assistance": "Assistance"
    },
    "it": {
      "tab_cars": "Vehicles",
      "tab_alerts": "Notifications",
      "tab_data": "Data",
      "tab_diagnostics": "Diagnostics",
      "loading": "Loading…",
      "retry": "Retry",
      "no_cars": "There are no vehicles. Add your Deepal account under Settings → Devices and services.",
      "error_generic": "That could not be completed. Try again.",
      "day": "{value} day",
      "days": "{value} days",
      "or": " or ",
      "not_configured": "No model chosen",
      "sheet_verified": "Verified sheet",
      "sheet_catalogue": "Catalogue sheet",
      "battery": "Battery",
      "range": "Range",
      "odometer": "Odometer",
      "appearance": "Appearance",
      "configure": "Configure",
      "section_charge": "Charging",
      "section_warnings": "Warnings",
      "section_maintenance": "Servicing",
      "section_itv": "ITV",
      "section_insurance": "Insurance",
      "section_appearance": "Appearance",
      "not_set": "Not set up",
      "add_maintenance": "Enable servicing",
      "add_itv": "Add the ITV",
      "add_insurance": "Add the insurance",
      "feature_seat_heat": "Heated seats",
      "feature_seat_vent": "Ventilated seats",
      "feature_wheel_heat": "Heated steering wheel",
      "feature_power_tailgate": "Power tailgate",
      "wheel_pro": "18\" wheels",
      "wheel_cover": "20\" wheels with aero covers",
      "wheel_open": "20\" wheels without covers",
      "service_number": "Service no. {number}",
      "overdue": "Overdue",
      "left": "{parts} left",
      "overdue_since": "Overdue by {days}",
      "cancel_until": "Cancellation deadline: {date}",
      "renews_in": "Renews in {days}",
      "notify_to": "Notify",
      "n_notices": "{count} notifications",
      "edit_threshold": "Change the lead time",
      "accept": "Accept",
      "cancel": "Cancel",
      "unit_km": "km",
      "unit_days": "days",
      "when_km": "{value} km left",
      "when_days": "{value} days left",
      "when_days_deadline": "{value} days before the deadline",
      "when_maintenance_overdue": "on the day or when the km are reached",
      "when_itv_overdue": "on the day",
      "when_insurance_last_day": "last day to cancel",
      "when_insurance_renewed": "on the day",
      "notice_charge_started": "Charging started",
      "notice_charge_interrupted": "Charging interrupted",
      "notice_charge_finished": "Charging finished",
      "notice_warnings": "Warning lights",
      "notice_tires": "Tyres",
      "notice_key_battery": "Key fob battery low",
      "notice_maintenance_t1": "Time notice 1",
      "notice_maintenance_t2": "Time notice 2",
      "notice_maintenance_t3": "Time notice 3",
      "notice_maintenance_k1": "Distance notice 1",
      "notice_maintenance_k2": "Distance notice 2",
      "notice_maintenance_k3": "Distance notice 3",
      "notice_maintenance_overdue": "Service due",
      "notice_itv_t1": "Notice 1",
      "notice_itv_t2": "Notice 2",
      "notice_itv_t3": "Notice 3",
      "notice_itv_overdue": "ITV due",
      "notice_insurance_c1": "Cancellation notice 1",
      "notice_insurance_c2": "Cancellation notice 2",
      "notice_insurance_last_day": "Cancellation deadline",
      "notice_insurance_r1": "Renewal notice 1",
      "notice_insurance_r2": "Renewal notice 2",
      "notice_insurance_renewed": "Insurance renewed",
      "unsaved": "This vehicle has unsaved changes.",
      "alerts_help": "Tick who gets each notification. The pencil changes the days or kilometres of that notification; lead times belong to this vehicle.",
      "factory_thresholds": "Default lead times",
      "discard": "Discard",
      "save": "Save",
      "saved": "Saved",
      "copy_from": "Copy from another vehicle",
      "car": "Vehicle",
      "copy": "Copy",
      "error_threshold_range_limits": "The lead time must be between {low} and {high}.",
      "error_threshold_range": "A lead time is out of range.",
      "error_threshold_order": "Lead times must go from longest to shortest: notice 1 before 2, and 2 before 3.",
      "error_not_found": "That vehicle is no longer in the account.",
      "error_invalid": "Some of the data is not valid.",
      "error_invalid_file": "The file is not a DEC Deepal backup, or it is damaged.",
      "error_newer_file": "The backup comes from a newer version of the integration. Update DEC Deepal and try again.",
      "error_empty_file": "The backup has no data for any vehicle.",
      "error_required": "Some fields are missing.",
      "backup_title": "Backup",
      "backup_help": "Servicing, ITV, insurance and appearance of your vehicles. The data belongs to the vehicle: it is not lost when the account is removed.",
      "download_title": "Download a backup",
      "download_help": "A file with the data of every vehicle. It contains the policy number and the insurance phone numbers: keep it somewhere safe.",
      "download": "Download",
      "send_title": "Send the backup to a phone",
      "send_help": "A notification arrives; tapping it opens the browser and downloads the file. The link expires in 10 minutes.",
      "send": "Send",
      "sent_to": "Notification sent to {device}.",
      "upload_title": "Load a backup",
      "upload_help": "Leaves the vehicles in the file as they were in it. Other vehicles are left untouched.",
      "choose_file": "Choose file",
      "imported": "Backup loaded: {cars}.",
      "stored_title": "Stored data",
      "stored_help": "Per vehicle, identified by its VIN.",
      "stored_none": "There is no stored data for any vehicle.",
      "in_account": "In the account",
      "no_account": "No account",
      "no_account_note": "No longer in any account",
      "delete": "Delete",
      "delete_title": "Delete stored data",
      "delete_confirm": "The servicing, ITV and insurance of {name} will be deleted. This cannot be undone: download a backup first if you want to keep them.",
      "deleted": "Data deleted.",
      "history_title": "What has happened",
      "history_help": "Changes, commands and notifications since the last restart. The same goes into the diagnostics file.",
      "history_none": "Nothing to show yet.",
      "filter_all": "All",
      "filter_orders": "Commands",
      "filter_alerts": "Notifications",
      "filter_errors": "Errors",
      "sheets_title": "Sheet of each vehicle",
      "sheets_help": "Which equipment the integration assumes, and where it gets it from.",
      "diagnostics_file": "Diagnostics",
      "ev_alert": "Notification sent: {name}",
      "ev_targets": "{count} recipients",
      "ev_wake": "Vehicle wake-up",
      "ev_command": "Command: {name}",
      "ev_code": "code",
      "today": "Today",
      "yesterday": "Yesterday",
      "enabled": "Enabled",
      "mt_services_done": "Services already done",
      "mt_interval_km": "Interval (km)",
      "mt_interval_months": "Interval (months)",
      "mt_register": "Register a completed service",
      "mt_register_help": "Records service no. {number} of {name} and starts counting towards the next one.",
      "date": "Date",
      "mt_km": "Kilometres",
      "register": "Register",
      "registered": "Registered",
      "itv_registration": "Registration date",
      "itv_last": "Last ITV passed",
      "itv_next": "Next ITV (manual)",
      "itv_register": "Register a passed ITV",
      "itv_register_help": "Records that {name} has passed the ITV and calculates the next one.",
      "ins_company": "Company",
      "ins_policy": "Policy number",
      "ins_kind": "Type of insurance",
      "ins_renewal": "Renewal date",
      "ins_notice": "Notice days to cancel",
      "ins_phone_assistance": "Assistance phone",
      "ins_phone_company": "Company phone",
      "kind_third_party": "Third party",
      "kind_third_party_plus": "Third party plus",
      "kind_comprehensive_excess": "Comprehensive with excess",
      "kind_comprehensive": "Comprehensive without excess",
      "tab_settings": "Settings",
      "appearance_title": "Appearance of {name}",
      "appearance_help": "Decides the photo, the view of the vehicle and which equipment is assumed.",
      "model": "Model",
      "trim": "Version",
      "color": "Colour",
      "wheels": "Wheels",
      "model_ev": "Electric",
      "model_phev": "Plug-in hybrid",
      "trim_full": "Heated seats and steering wheel, power tailgate",
      "trim_basic": "No heated seats or steering wheel",
      "account": "Account: {name}",
      "pin_title": "Remote control with PIN",
      "pin_help": "To lock and unlock, windows and boot. It is the PIN of the official Deepal app, with the same account. It applies to every vehicle in the account.",
      "pin_enabled": "PIN commands",
      "pin_enabled_help": "Without this, the card only shows the state of doors, windows and boot.",
      "pin": "PIN",
      "pin_field_help": "It is checked with Deepal on saving. Leave it empty to keep the current one.",
      "pin_checked": "Checked",
      "show_pin": "Show the PIN",
      "pin_mode_title": "How commands are used",
      "mode_direct": "Direct",
      "mode_direct_help": "The command is sent when you tap, after confirming. The most convenient.",
      "mode_armed": "Unlock first",
      "mode_armed_help": "You first have to enable \"Unlock PIN actions\", and it only lasts for a while. The safest.",
      "arm_seconds": "How long the unlock lasts",
      "arm_seconds_help": "After that time, PIN commands lock again on their own.",
      "seconds": "{value} s",
      "arm_notify": "Notify on unlock",
      "arm_notify_help": "A notification in Home Assistant every time commands are allowed.",
      "reading_title": "Data reading",
      "reading_help": "How and how often the vehicle is asked.",
      "scan_title": "Reading interval",
      "scan_help": "How often the vehicle data is read. Very low values may make Deepal throttle the account.",
      "minutes": "{value} min",
      "wake_title": "Wake the vehicle when needed",
      "wake_help": "When you tap Refresh and before a PIN command. Never on automatic readings, to protect the 12 V battery.",
      "manual_bev": "BEV manual",
      "manual_phev": "PHEV manual",
      "manual_help": "The link the card opens under More → Manual. Empty to use the official one.",
      "debug_title": "Debug mode",
      "debug_help": "Stores full requests and responses (without personal data) in the diagnostics.",
      "save_check": "Save",
      "unsaved_settings": "There are unsaved changes.",
      "error_pin_required": "Enter the PIN.",
      "error_pin_invalid": "The PIN is not correct. It is the one from the official Deepal app, with this same account.",
      "error_pin_rate_limited": "Too many PIN attempts. Wait a few minutes before trying again.",
      "error_cannot_connect": "Could not connect to Deepal. Try again later.",
      "error_invalid_url": "The manual link is not valid: it must start with http:// or https://.",
      "error_unknown_model": "That model is not in the catalogue.",
      "close": "Close",
      "other": "Other",
      "history": "History",
      "manual": "Manual",
      "copied": "Copied: {text}",
      "form_maintenance": "Set up servicing",
      "form_itv": "Set up the ITV",
      "form_insurance": "Set up the insurance",
      "form_maintenance_off": "Disabled: its entities, its indicator on the card and its notifications are removed. The history is lost.",
      "form_itv_off": "Disabled: its entities, its indicator on the card and its notifications are removed.",
      "form_insurance_off": "Disabled: its entities, its indicator on the card and its notifications are removed.",
      "first_notice": "First notification {days} days before",
      "mt_last": "Last service",
      "mt_last_help": "If the vehicle has not had any yet, enter the registration date and 0 km.",
      "mt_next_is": "The next one will be service no. {number}.",
      "mt_km_then": "Kilometres then",
      "mt_use_odometer": "Use the vehicle's current reading ({km} km)",
      "mt_every": "How often",
      "mt_every_help": "The manual asks for a shorter interval with repeated short trips, dust, mud, extreme cold or salt.",
      "mt_interval_manual": "From the manual",
      "mt_interval_value": "{km} km or {months} months",
      "mt_interval_other": "You choose",
      "mt_preview": "Next service: {date} or at {km} km",
      "mt_whichever": "Whichever comes first: {date} or at {km} km.",
      "by_time": "By time",
      "by_km": "By distance",
      "mt_km_detail": "Now {now} km · due at {due}",
      "mt_this_service": "What this service includes",
      "n_operations": "{count} operations",
      "mt_no_plan": "This model has no servicing plan in the catalogue.",
      "mt_next_adds": "The next one (no. {number}) adds",
      "mt_history_item": "Service no. {number} · {date} · {km} km",
      "mt_no_history": "No services have been registered yet.",
      "itv_registration_title": "Registration",
      "itv_registration_help": "It is on the registration certificate. The first ITV is calculated from it.",
      "itv_passed_title": "ITVs already passed",
      "itv_passed_help": "Only if the vehicle has already passed one.",
      "itv_passed": "It has already passed an ITV",
      "itv_next_title": "Next ITV",
      "itv_next_rules": "It is calculated with the rules of the account's country.",
      "itv_next_auto": "Calculate it",
      "itv_next_manual": "Set another date",
      "itv_next_manual_note": "If the station gave you a different one",
      "itv_preview": "Next ITV: {date}",
      "itv_manual_date": "date set by hand",
      "itv_age": "{years} years",
      "itv_none_yet": "None yet",
      "itv_first_at": "The first one, at {years} years",
      "itv_rules_title": "How often",
      "itv_rules": "The first at {first} years; then every {interval} and, from {reduced} years on, every year.",
      "itv_history_item": "ITV passed on {date}",
      "itv_no_history": "No ITV has been registered yet.",
      "ins_policy_title": "The policy",
      "ins_policy_help": "The policy number and the phone numbers are only shown on the card and in the panel; they never appear in the diagnostics.",
      "ins_renewal_title": "Renewal",
      "ins_renewal_help": "The insurance renews itself every year. To cancel, you have to give notice beforehand.",
      "ins_renews_on": "It renews on",
      "ins_notice_days": "Notice days",
      "ins_phones_title": "Phone numbers",
      "ins_phones_help": "To call with one tap from the card and from here.",
      "ins_preview": "Last day to cancel: {date}",
      "ins_preview_passed": "That deadline has passed. It renews on {date}.",
      "ins_dates": "Dates",
      "ins_to_cancel": "To cancel",
      "ins_to_renewal": "To renewal",
      "ins_deadline_passed": "Deadline passed",
      "ins_deadline_on": "Last day: {date}",
      "ins_renews_itself": "It renews itself on {date}",
      "ins_assistance": "Assistance"
    },
    "pl": {
      "tab_cars": "Vehicles",
      "tab_alerts": "Notifications",
      "tab_data": "Data",
      "tab_diagnostics": "Diagnostics",
      "loading": "Loading…",
      "retry": "Retry",
      "no_cars": "There are no vehicles. Add your Deepal account under Settings → Devices and services.",
      "error_generic": "That could not be completed. Try again.",
      "day": "{value} day",
      "days": "{value} days",
      "or": " or ",
      "not_configured": "No model chosen",
      "sheet_verified": "Verified sheet",
      "sheet_catalogue": "Catalogue sheet",
      "battery": "Battery",
      "range": "Range",
      "odometer": "Odometer",
      "appearance": "Appearance",
      "configure": "Configure",
      "section_charge": "Charging",
      "section_warnings": "Warnings",
      "section_maintenance": "Servicing",
      "section_itv": "ITV",
      "section_insurance": "Insurance",
      "section_appearance": "Appearance",
      "not_set": "Not set up",
      "add_maintenance": "Enable servicing",
      "add_itv": "Add the ITV",
      "add_insurance": "Add the insurance",
      "feature_seat_heat": "Heated seats",
      "feature_seat_vent": "Ventilated seats",
      "feature_wheel_heat": "Heated steering wheel",
      "feature_power_tailgate": "Power tailgate",
      "wheel_pro": "18\" wheels",
      "wheel_cover": "20\" wheels with aero covers",
      "wheel_open": "20\" wheels without covers",
      "service_number": "Service no. {number}",
      "overdue": "Overdue",
      "left": "{parts} left",
      "overdue_since": "Overdue by {days}",
      "cancel_until": "Cancellation deadline: {date}",
      "renews_in": "Renews in {days}",
      "notify_to": "Notify",
      "n_notices": "{count} notifications",
      "edit_threshold": "Change the lead time",
      "accept": "Accept",
      "cancel": "Cancel",
      "unit_km": "km",
      "unit_days": "days",
      "when_km": "{value} km left",
      "when_days": "{value} days left",
      "when_days_deadline": "{value} days before the deadline",
      "when_maintenance_overdue": "on the day or when the km are reached",
      "when_itv_overdue": "on the day",
      "when_insurance_last_day": "last day to cancel",
      "when_insurance_renewed": "on the day",
      "notice_charge_started": "Charging started",
      "notice_charge_interrupted": "Charging interrupted",
      "notice_charge_finished": "Charging finished",
      "notice_warnings": "Warning lights",
      "notice_tires": "Tyres",
      "notice_key_battery": "Key fob battery low",
      "notice_maintenance_t1": "Time notice 1",
      "notice_maintenance_t2": "Time notice 2",
      "notice_maintenance_t3": "Time notice 3",
      "notice_maintenance_k1": "Distance notice 1",
      "notice_maintenance_k2": "Distance notice 2",
      "notice_maintenance_k3": "Distance notice 3",
      "notice_maintenance_overdue": "Service due",
      "notice_itv_t1": "Notice 1",
      "notice_itv_t2": "Notice 2",
      "notice_itv_t3": "Notice 3",
      "notice_itv_overdue": "ITV due",
      "notice_insurance_c1": "Cancellation notice 1",
      "notice_insurance_c2": "Cancellation notice 2",
      "notice_insurance_last_day": "Cancellation deadline",
      "notice_insurance_r1": "Renewal notice 1",
      "notice_insurance_r2": "Renewal notice 2",
      "notice_insurance_renewed": "Insurance renewed",
      "unsaved": "This vehicle has unsaved changes.",
      "alerts_help": "Tick who gets each notification. The pencil changes the days or kilometres of that notification; lead times belong to this vehicle.",
      "factory_thresholds": "Default lead times",
      "discard": "Discard",
      "save": "Save",
      "saved": "Saved",
      "copy_from": "Copy from another vehicle",
      "car": "Vehicle",
      "copy": "Copy",
      "error_threshold_range_limits": "The lead time must be between {low} and {high}.",
      "error_threshold_range": "A lead time is out of range.",
      "error_threshold_order": "Lead times must go from longest to shortest: notice 1 before 2, and 2 before 3.",
      "error_not_found": "That vehicle is no longer in the account.",
      "error_invalid": "Some of the data is not valid.",
      "error_invalid_file": "The file is not a DEC Deepal backup, or it is damaged.",
      "error_newer_file": "The backup comes from a newer version of the integration. Update DEC Deepal and try again.",
      "error_empty_file": "The backup has no data for any vehicle.",
      "error_required": "Some fields are missing.",
      "backup_title": "Backup",
      "backup_help": "Servicing, ITV, insurance and appearance of your vehicles. The data belongs to the vehicle: it is not lost when the account is removed.",
      "download_title": "Download a backup",
      "download_help": "A file with the data of every vehicle. It contains the policy number and the insurance phone numbers: keep it somewhere safe.",
      "download": "Download",
      "send_title": "Send the backup to a phone",
      "send_help": "A notification arrives; tapping it opens the browser and downloads the file. The link expires in 10 minutes.",
      "send": "Send",
      "sent_to": "Notification sent to {device}.",
      "upload_title": "Load a backup",
      "upload_help": "Leaves the vehicles in the file as they were in it. Other vehicles are left untouched.",
      "choose_file": "Choose file",
      "imported": "Backup loaded: {cars}.",
      "stored_title": "Stored data",
      "stored_help": "Per vehicle, identified by its VIN.",
      "stored_none": "There is no stored data for any vehicle.",
      "in_account": "In the account",
      "no_account": "No account",
      "no_account_note": "No longer in any account",
      "delete": "Delete",
      "delete_title": "Delete stored data",
      "delete_confirm": "The servicing, ITV and insurance of {name} will be deleted. This cannot be undone: download a backup first if you want to keep them.",
      "deleted": "Data deleted.",
      "history_title": "What has happened",
      "history_help": "Changes, commands and notifications since the last restart. The same goes into the diagnostics file.",
      "history_none": "Nothing to show yet.",
      "filter_all": "All",
      "filter_orders": "Commands",
      "filter_alerts": "Notifications",
      "filter_errors": "Errors",
      "sheets_title": "Sheet of each vehicle",
      "sheets_help": "Which equipment the integration assumes, and where it gets it from.",
      "diagnostics_file": "Diagnostics",
      "ev_alert": "Notification sent: {name}",
      "ev_targets": "{count} recipients",
      "ev_wake": "Vehicle wake-up",
      "ev_command": "Command: {name}",
      "ev_code": "code",
      "today": "Today",
      "yesterday": "Yesterday",
      "enabled": "Enabled",
      "mt_services_done": "Services already done",
      "mt_interval_km": "Interval (km)",
      "mt_interval_months": "Interval (months)",
      "mt_register": "Register a completed service",
      "mt_register_help": "Records service no. {number} of {name} and starts counting towards the next one.",
      "date": "Date",
      "mt_km": "Kilometres",
      "register": "Register",
      "registered": "Registered",
      "itv_registration": "Registration date",
      "itv_last": "Last ITV passed",
      "itv_next": "Next ITV (manual)",
      "itv_register": "Register a passed ITV",
      "itv_register_help": "Records that {name} has passed the ITV and calculates the next one.",
      "ins_company": "Company",
      "ins_policy": "Policy number",
      "ins_kind": "Type of insurance",
      "ins_renewal": "Renewal date",
      "ins_notice": "Notice days to cancel",
      "ins_phone_assistance": "Assistance phone",
      "ins_phone_company": "Company phone",
      "kind_third_party": "Third party",
      "kind_third_party_plus": "Third party plus",
      "kind_comprehensive_excess": "Comprehensive with excess",
      "kind_comprehensive": "Comprehensive without excess",
      "tab_settings": "Settings",
      "appearance_title": "Appearance of {name}",
      "appearance_help": "Decides the photo, the view of the vehicle and which equipment is assumed.",
      "model": "Model",
      "trim": "Version",
      "color": "Colour",
      "wheels": "Wheels",
      "model_ev": "Electric",
      "model_phev": "Plug-in hybrid",
      "trim_full": "Heated seats and steering wheel, power tailgate",
      "trim_basic": "No heated seats or steering wheel",
      "account": "Account: {name}",
      "pin_title": "Remote control with PIN",
      "pin_help": "To lock and unlock, windows and boot. It is the PIN of the official Deepal app, with the same account. It applies to every vehicle in the account.",
      "pin_enabled": "PIN commands",
      "pin_enabled_help": "Without this, the card only shows the state of doors, windows and boot.",
      "pin": "PIN",
      "pin_field_help": "It is checked with Deepal on saving. Leave it empty to keep the current one.",
      "pin_checked": "Checked",
      "show_pin": "Show the PIN",
      "pin_mode_title": "How commands are used",
      "mode_direct": "Direct",
      "mode_direct_help": "The command is sent when you tap, after confirming. The most convenient.",
      "mode_armed": "Unlock first",
      "mode_armed_help": "You first have to enable \"Unlock PIN actions\", and it only lasts for a while. The safest.",
      "arm_seconds": "How long the unlock lasts",
      "arm_seconds_help": "After that time, PIN commands lock again on their own.",
      "seconds": "{value} s",
      "arm_notify": "Notify on unlock",
      "arm_notify_help": "A notification in Home Assistant every time commands are allowed.",
      "reading_title": "Data reading",
      "reading_help": "How and how often the vehicle is asked.",
      "scan_title": "Reading interval",
      "scan_help": "How often the vehicle data is read. Very low values may make Deepal throttle the account.",
      "minutes": "{value} min",
      "wake_title": "Wake the vehicle when needed",
      "wake_help": "When you tap Refresh and before a PIN command. Never on automatic readings, to protect the 12 V battery.",
      "manual_bev": "BEV manual",
      "manual_phev": "PHEV manual",
      "manual_help": "The link the card opens under More → Manual. Empty to use the official one.",
      "debug_title": "Debug mode",
      "debug_help": "Stores full requests and responses (without personal data) in the diagnostics.",
      "save_check": "Save",
      "unsaved_settings": "There are unsaved changes.",
      "error_pin_required": "Enter the PIN.",
      "error_pin_invalid": "The PIN is not correct. It is the one from the official Deepal app, with this same account.",
      "error_pin_rate_limited": "Too many PIN attempts. Wait a few minutes before trying again.",
      "error_cannot_connect": "Could not connect to Deepal. Try again later.",
      "error_invalid_url": "The manual link is not valid: it must start with http:// or https://.",
      "error_unknown_model": "That model is not in the catalogue.",
      "close": "Close",
      "other": "Other",
      "history": "History",
      "manual": "Manual",
      "copied": "Copied: {text}",
      "form_maintenance": "Set up servicing",
      "form_itv": "Set up the ITV",
      "form_insurance": "Set up the insurance",
      "form_maintenance_off": "Disabled: its entities, its indicator on the card and its notifications are removed. The history is lost.",
      "form_itv_off": "Disabled: its entities, its indicator on the card and its notifications are removed.",
      "form_insurance_off": "Disabled: its entities, its indicator on the card and its notifications are removed.",
      "first_notice": "First notification {days} days before",
      "mt_last": "Last service",
      "mt_last_help": "If the vehicle has not had any yet, enter the registration date and 0 km.",
      "mt_next_is": "The next one will be service no. {number}.",
      "mt_km_then": "Kilometres then",
      "mt_use_odometer": "Use the vehicle's current reading ({km} km)",
      "mt_every": "How often",
      "mt_every_help": "The manual asks for a shorter interval with repeated short trips, dust, mud, extreme cold or salt.",
      "mt_interval_manual": "From the manual",
      "mt_interval_value": "{km} km or {months} months",
      "mt_interval_other": "You choose",
      "mt_preview": "Next service: {date} or at {km} km",
      "mt_whichever": "Whichever comes first: {date} or at {km} km.",
      "by_time": "By time",
      "by_km": "By distance",
      "mt_km_detail": "Now {now} km · due at {due}",
      "mt_this_service": "What this service includes",
      "n_operations": "{count} operations",
      "mt_no_plan": "This model has no servicing plan in the catalogue.",
      "mt_next_adds": "The next one (no. {number}) adds",
      "mt_history_item": "Service no. {number} · {date} · {km} km",
      "mt_no_history": "No services have been registered yet.",
      "itv_registration_title": "Registration",
      "itv_registration_help": "It is on the registration certificate. The first ITV is calculated from it.",
      "itv_passed_title": "ITVs already passed",
      "itv_passed_help": "Only if the vehicle has already passed one.",
      "itv_passed": "It has already passed an ITV",
      "itv_next_title": "Next ITV",
      "itv_next_rules": "It is calculated with the rules of the account's country.",
      "itv_next_auto": "Calculate it",
      "itv_next_manual": "Set another date",
      "itv_next_manual_note": "If the station gave you a different one",
      "itv_preview": "Next ITV: {date}",
      "itv_manual_date": "date set by hand",
      "itv_age": "{years} years",
      "itv_none_yet": "None yet",
      "itv_first_at": "The first one, at {years} years",
      "itv_rules_title": "How often",
      "itv_rules": "The first at {first} years; then every {interval} and, from {reduced} years on, every year.",
      "itv_history_item": "ITV passed on {date}",
      "itv_no_history": "No ITV has been registered yet.",
      "ins_policy_title": "The policy",
      "ins_policy_help": "The policy number and the phone numbers are only shown on the card and in the panel; they never appear in the diagnostics.",
      "ins_renewal_title": "Renewal",
      "ins_renewal_help": "The insurance renews itself every year. To cancel, you have to give notice beforehand.",
      "ins_renews_on": "It renews on",
      "ins_notice_days": "Notice days",
      "ins_phones_title": "Phone numbers",
      "ins_phones_help": "To call with one tap from the card and from here.",
      "ins_preview": "Last day to cancel: {date}",
      "ins_preview_passed": "That deadline has passed. It renews on {date}.",
      "ins_dates": "Dates",
      "ins_to_cancel": "To cancel",
      "ins_to_renewal": "To renewal",
      "ins_deadline_passed": "Deadline passed",
      "ins_deadline_on": "Last day: {date}",
      "ins_renews_itself": "It renews itself on {date}",
      "ins_assistance": "Assistance"
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

  // ── src/22_fechas.js ──────────────────────────────────────────────────────
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

  // ── src/30_estilos.js ─────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Estilos (con las variables del tema de Home Assistant: claro y oscuro)
  // ---------------------------------------------------------------------------
  const SOFT = "rgba(var(--rgb-primary-text-color, 33, 33, 33), 0.06)";
  const PANEL_CSS = `
    :host { display: block; height: 100%; color: var(--primary-text-color); background: var(--primary-background-color, #fafafa);
      font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif); font-size: 14px; }
    * { box-sizing: border-box; }
    button { font: inherit; color: inherit; border: 0; background: none; margin: 0; cursor: pointer; -webkit-tap-highlight-color: transparent; }
    .page { display: flex; flex-direction: column; height: 100%; }
    .bar { background: var(--app-header-background-color, var(--primary-color)); color: var(--app-header-text-color, #fff); flex: none; }
    .top { display: flex; align-items: center; height: var(--header-height, 56px); padding: 0 12px; gap: 8px; font-size: 20px; }
    .top span { flex: 1; } .top small { font-size: 13px; opacity: .85; }
    .tabs { display: flex; padding: 0 12px; gap: 4px; overflow-x: auto; }
    .tabs button { font-weight: 500; font-size: 13px; letter-spacing: .6px; text-transform: uppercase; padding: 13px 16px; opacity: .75;
      border-bottom: 3px solid transparent; display: flex; gap: 8px; align-items: center; white-space: nowrap; --mdc-icon-size: 18px; }
    .tabs button.on { opacity: 1; border-color: currentColor; }
    .scroll { flex: 1; overflow: auto; }
    .view { padding: 20px; max-width: 1040px; margin: 0 auto; }
    .card { background: var(--ha-card-background, var(--card-background-color, #fff)); border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 12px; margin-bottom: 20px; overflow: hidden; }
    .card h2 { font-size: 18px; font-weight: 400; margin: 0; padding: 16px 20px 4px; }
    .sub { color: var(--secondary-text-color); padding: 0 20px 12px; font-size: 13px; }
    .pad { padding: 14px 20px; }
    .empty { padding: 40px 20px; text-align: center; color: var(--secondary-text-color); }

    .btn { display: inline-flex; gap: 8px; align-items: center; border-radius: 18px; padding: 8px 16px; font-weight: 500; white-space: nowrap;
      background: var(--primary-color); color: var(--text-primary-color, #fff); text-decoration: none; --mdc-icon-size: 18px; }
    .btn.o { background: transparent; color: var(--primary-color); border: 1px solid var(--divider-color, #e0e0e0); }
    .btn.r { background: transparent; color: var(--error-color, #db4437); border: 1px solid var(--divider-color, #e0e0e0); }
    .btn[disabled] { opacity: .5; pointer-events: none; }
    .badge { font-size: 12px; padding: 4px 10px; border-radius: 12px; font-weight: 500; display: inline-flex; gap: 4px; align-items: center; --mdc-icon-size: 14px; }
    .badge.ok { background: rgba(67, 160, 71, .15); color: var(--success-color, #2e7d32); }
    .badge.warn { background: rgba(249, 168, 37, .18); color: var(--warning-color, #f57f17); }
    .badge.info { background: rgba(var(--rgb-primary-color, 3, 169, 244), .15); color: var(--primary-color); }

    /* --- Coches --- */
    .hero { display: flex; align-items: center; gap: 16px; padding: 12px 20px 0; flex-wrap: wrap; }
    .hero img { width: 380px; max-width: 100%; margin: -4px 0 -8px -16px; }
    .hero .who { flex: 1; min-width: 200px; }
    .hero .n { font-size: 26px; } .hero .m { color: var(--secondary-text-color); margin: 2px 0 10px; }
    .kv { display: flex; gap: 26px; margin-top: 8px; flex-wrap: wrap; }
    .kv div { font-size: 13px; color: var(--secondary-text-color); } .kv b { display: block; font-size: 18px; font-weight: 400; color: var(--primary-text-color); }
    .chips { padding: 14px 20px 2px; }
    .chip { display: inline-flex; gap: 6px; align-items: center; padding: 5px 12px; border-radius: 16px; background: ${SOFT}; font-size: 13px;
      margin: 0 6px 6px 0; --mdc-icon-size: 16px; }
    .chip ha-icon { color: var(--primary-color); }
    .grid3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; padding: 10px 20px 18px; }
    .tile { border: 1px solid var(--divider-color, #e0e0e0); border-radius: 10px; padding: 12px 14px; min-width: 0; }
    .tile[data-action] { cursor: pointer; }
    .tile .h { display: flex; gap: 8px; align-items: center; color: var(--secondary-text-color); font-size: 13px; --mdc-icon-size: 20px; }
    .tile .h span { flex: 1; }
    .gear { width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: -4px -6px -4px 0;
      color: var(--secondary-text-color); background: ${SOFT}; --mdc-icon-size: 20px; }
    .tile .v { font-size: 20px; margin: 6px 0 2px; } .tile .d { color: var(--secondary-text-color); font-size: 13px; }
    .tile.off .v { color: var(--secondary-text-color); }
    .tile.ok .h > ha-icon { color: var(--success-color, #43a047); }
    .tile.soon .h > ha-icon { color: var(--warning-color, #f9a825); }
    .tile.overdue .h > ha-icon { color: var(--error-color, #db4437); }
    .link { color: var(--primary-color); font-size: 13px; padding: 0; }
    .meter { height: 6px; border-radius: 3px; background: ${SOFT}; margin-top: 10px; overflow: hidden; }
    .meter i { display: block; height: 100%; background: var(--success-color, #43a047); }
    .tile.soon .meter i { background: var(--warning-color, #f9a825); } .tile.overdue .meter i { background: var(--error-color, #db4437); }

    /* --- Avisos --- */
    .chead { display: flex; align-items: center; gap: 10px; padding: 8px 20px 0; flex-wrap: wrap; }
    .chead img { width: 170px; margin: -6px 0 -10px -18px; }
    .chead .n { font-size: 20px; flex: 1; min-width: 140px; } .chead .n small { display: block; font-size: 13px; color: var(--secondary-text-color); }
    .wide { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; }
    th { font-weight: 400; font-size: 12px; color: var(--secondary-text-color); padding: 10px 6px; text-align: center; border-bottom: 1px solid var(--divider-color, #e0e0e0); }
    th:first-child { text-align: left; padding-left: 20px; font-size: 13px; }
    .dev { display: flex; flex-direction: column; align-items: center; gap: 4px; max-width: 96px; margin: 0 auto; }
    .dev u { text-decoration: none; width: 30px; height: 30px; border-radius: 50%; background: var(--primary-color); color: var(--text-primary-color, #fff);
      display: flex; align-items: center; justify-content: center; --mdc-icon-size: 17px; }
    .dev.panel u { background: var(--secondary-text-color); }
    td { padding: 6px; text-align: center; border-bottom: 1px solid var(--divider-color, #e0e0e0); }
    td:first-child { text-align: left; padding-left: 20px; }
    tr:last-child td { border-bottom: 0; }
    .box { width: 36px; height: 36px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
      color: var(--secondary-text-color); --mdc-icon-size: 22px; }
    .box.y, .box.some { color: var(--primary-color); }
    tr.grp td { background: ${SOFT}; }
    tr.grp td:first-child { padding: 0; }
    .fold { display: flex; align-items: center; gap: 8px; width: 100%; padding: 12px 14px; font-weight: 500; font-size: 15px; text-align: left; --mdc-icon-size: 22px; }
    .fold .sic { color: var(--primary-color); } .fold small { font-weight: 400; font-size: 12px; color: var(--secondary-text-color); margin-left: 6px; }
    tr.it td:first-child { padding-left: 52px; }
    .lab { display: flex; align-items: center; gap: 8px; min-height: 36px; }
    .lab b { font-weight: 400; } .lab small { color: var(--secondary-text-color); font-size: 12px; flex: 1; }
    .pen { width: 32px; height: 32px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
      color: var(--secondary-text-color); --mdc-icon-size: 18px; flex: none; }
    tr.ed td { background: rgba(var(--rgb-primary-color, 3, 169, 244), .1); }
    .inp { display: inline-flex; align-items: center; border: 1px solid var(--primary-color); border-radius: 6px; overflow: hidden;
      background: var(--card-background-color, #fff); }
    .inp input { width: 78px; border: 0; padding: 6px 8px; font: inherit; text-align: right; background: transparent; color: inherit; outline: none; }
    .inp span { padding: 6px 10px; color: var(--secondary-text-color); font-size: 13px; border-left: 1px solid var(--divider-color, #e0e0e0); }
    .mini { width: 32px; height: 32px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; --mdc-icon-size: 18px; flex: none; }
    .mini.ok { background: var(--primary-color); color: var(--text-primary-color, #fff); }
    .foot { display: flex; align-items: center; gap: 10px; padding: 12px 20px; border-top: 1px solid var(--divider-color, #e0e0e0); flex-wrap: wrap; }
    .foot span { flex: 1; color: var(--secondary-text-color); font-size: 13px; min-width: 160px; }
    .foot.dirty { background: rgba(var(--rgb-primary-color, 3, 169, 244), .08); }

    /* --- Datos y diagnóstico --- */
    .row { display: flex; gap: 14px; align-items: center; padding: 14px 20px; border-top: 1px solid var(--divider-color, #e0e0e0); flex-wrap: wrap; }
    .row .ic { width: 40px; height: 40px; border-radius: 50%; background: rgba(var(--rgb-primary-color, 3, 169, 244), .15); color: var(--primary-color);
      display: flex; align-items: center; justify-content: center; flex: none; }
    .row .ic.grey { background: ${SOFT}; color: var(--secondary-text-color); }
    .row .tx { flex: 1; min-width: 180px; } .row .tx small { display: block; color: var(--secondary-text-color); font-size: 13px; }
    select { font: inherit; color: inherit; padding: 7px 8px; border-radius: 8px; border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff); max-width: 100%; }
    .filt { display: flex; gap: 8px; padding: 0 20px 14px; flex-wrap: wrap; }
    .filt button { padding: 5px 12px; border-radius: 16px; border: 1px solid var(--divider-color, #e0e0e0); font-size: 13px; }
    .filt button.on { background: rgba(var(--rgb-primary-color, 3, 169, 244), .15); border-color: var(--primary-color); color: var(--primary-color); }
    .log { display: flex; gap: 12px; padding: 10px 20px; border-top: 1px solid var(--divider-color, #e0e0e0); align-items: flex-start; }
    .log time { color: var(--secondary-text-color); font-size: 12px; width: 86px; flex: none; padding-top: 6px; }
    .log .dot { width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex: none; --mdc-icon-size: 17px;
      background: ${SOFT}; color: var(--secondary-text-color); }
    .log .dot.blue { background: rgba(var(--rgb-primary-color, 3, 169, 244), .15); color: var(--primary-color); }
    .log .dot.red { background: rgba(219, 68, 55, .15); color: var(--error-color, #db4437); }
    .log .dot.green { background: rgba(67, 160, 71, .15); color: var(--success-color, #43a047); }
    .log .what { min-width: 0; overflow-wrap: anywhere; } .log .what small { display: block; color: var(--secondary-text-color); font-size: 12px; }

    /* --- Ajustes --- */
    .acct { font-size: 13px; color: var(--secondary-text-color); margin: 0 4px 8px; }
    h2.next { border-top: 1px solid var(--divider-color, #e0e0e0); padding-top: 18px; margin-top: 6px; }
    .lbl { font-size: 13px; color: var(--secondary-text-color); padding: 14px 20px 8px; border-top: 1px solid var(--divider-color, #e0e0e0); }
    .tog { width: 40px; height: 22px; border-radius: 11px; background: var(--disabled-text-color, #bdbdbd); position: relative; flex: none; }
    .tog::after { content: ""; position: absolute; top: 3px; left: 3px; width: 16px; height: 16px; border-radius: 50%; background: #fff; transition: left .15s; }
    .tog.on { background: var(--primary-color); } .tog.on::after { left: 21px; }
    .seg { display: inline-flex; border: 1px solid var(--divider-color, #e0e0e0); border-radius: 18px; overflow: hidden; flex-wrap: wrap; }
    .seg button { padding: 7px 13px; font-size: 13px; border-right: 1px solid var(--divider-color, #e0e0e0); }
    .seg button:last-child { border: 0; } .seg button.on { background: var(--primary-color); color: var(--text-primary-color, #fff); }
    .modes { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; padding: 0 20px 16px; }
    .mode { border: 1px solid var(--divider-color, #e0e0e0); border-radius: 12px; padding: 14px 16px; text-align: left; }
    .mode.on { border: 2px solid var(--primary-color); padding: 13px 15px; background: rgba(var(--rgb-primary-color, 3, 169, 244), .08); }
    .mode b { font-weight: 500; display: flex; gap: 8px; align-items: center; --mdc-icon-size: 20px; } .mode b ha-icon { color: var(--primary-color); }
    .mode p { margin: 6px 0 0; color: var(--secondary-text-color); font-size: 13px; line-height: 1.45; }
    .pinbox { display: inline-flex; align-items: center; border: 1px solid var(--divider-color, #e0e0e0); border-radius: 8px; overflow: hidden;
      background: var(--card-background-color, #fff); }
    .pinbox input { width: 110px; border: 0; padding: 9px 10px; font: inherit; font-size: 16px; letter-spacing: 4px; background: transparent; color: inherit; outline: none; }
    .pinbox button { padding: 6px 8px; color: var(--secondary-text-color); --mdc-icon-size: 20px; display: flex; }
    input.url { font: inherit; color: inherit; padding: 8px 10px; border-radius: 8px; border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff); width: 320px; max-width: 100%; }

    @media (max-width: 700px) {
      .view { padding: 12px; }
      .modes { grid-template-columns: 1fr; }
      .grid3 { grid-template-columns: 1fr; }
      .hero img { width: 100%; margin: 0; }
      .tabs button { padding: 12px 10px; } .tabs button ha-icon { display: none; }
      tr.it td:first-child { padding-left: 20px; }
    }
  `;

  const DIALOG_CSS = `
    :host { position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center; padding: 16px; box-sizing: border-box;
      background: rgba(0, 0, 0, .32); font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif); color: var(--primary-text-color); font-size: 14px; }
    * { box-sizing: border-box; }
    .dlg { width: 100%; max-width: 460px; max-height: 100%; overflow: auto; background: var(--ha-card-background, var(--card-background-color, #fff));
      border-radius: 24px; box-shadow: 0 8px 24px rgba(0, 0, 0, .3); padding: 20px 22px 16px; }
    button { font: inherit; color: inherit; border: 0; background: none; margin: 0; cursor: pointer; }
    h2 { margin: 0 0 4px; font-size: 20px; font-weight: 400; }
    p { margin: 6px 0 12px; color: var(--secondary-text-color); line-height: 1.45; }
    label { display: block; margin: 12px 0 0; font-size: 13px; color: var(--secondary-text-color); }
    label small { display: block; font-size: 12px; margin-top: 3px; }
    input:not([type=checkbox]), select { display: block; width: 100%; margin-top: 4px; font: inherit; color: var(--primary-text-color); padding: 9px 10px;
      border-radius: 8px; border: 1px solid var(--divider-color, #e0e0e0); background: var(--card-background-color, #fff); }
    label.check { display: flex; align-items: center; gap: 10px; font-size: 15px; color: var(--primary-text-color); }
    label.check input { width: 18px; height: 18px; margin: 0; }
    .two { display: grid; grid-template-columns: 1fr 1fr; gap: 0 12px; }
    .err { color: var(--error-color, #db4437); font-size: 13px; margin-top: 10px; min-height: 18px; }
    .btns { display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px; flex-wrap: wrap; }
    .tb { font-weight: 500; color: var(--primary-color); padding: 9px 14px; border-radius: 18px; }
    .tb.fill { background: var(--primary-color); color: var(--text-primary-color, #fff); }
    .tb.danger { background: var(--error-color, #db4437); color: #fff; }
    .tb.left { margin-right: auto; }
    /* Ventana de Apariencia */
    .dlg.wide { max-width: 640px; }
    /* Fichas y formularios de Coches */
    .dlg.mid { max-width: 580px; }
    a.tb { text-decoration: none; display: inline-block; }
    .thead { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
    .thead .ic { width: 44px; height: 44px; border-radius: 50%; background: rgba(var(--rgb-primary-color, 3, 169, 244), .15); color: var(--primary-color);
      display: flex; align-items: center; justify-content: center; flex: none; }
    .thead h2 { flex: 1; margin: 0; } .thead h2 small { display: block; font-size: 13px; color: var(--secondary-text-color); margin-top: 2px; }
    .sw2 { display: flex; gap: 8px; align-items: center; font-size: 13px; }
    .x { width: 36px; height: 36px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; color: var(--secondary-text-color); --mdc-icon-size: 20px; flex: none; }
    .tog { width: 40px; height: 22px; border-radius: 11px; background: var(--disabled-text-color, #bdbdbd); position: relative; flex: none; }
    .tog::after { content: ""; position: absolute; top: 3px; left: 3px; width: 16px; height: 16px; border-radius: 50%; background: #fff; transition: left .15s; }
    .tog.on { background: var(--primary-color); } .tog.on::after { left: 21px; }
    .off { padding: 8px 0 4px; }
    .fsec { border-top: 1px solid var(--divider-color, #e0e0e0); padding: 14px 0 4px; }
    .fsec h4 { font-size: 13px; font-weight: 500; margin: 0 0 2px; display: flex; gap: 8px; align-items: center; --mdc-icon-size: 18px; }
    .fsec h4 ha-icon { color: var(--primary-color); }
    .hp { font-size: 12px; color: var(--secondary-text-color); margin-bottom: 10px; line-height: 1.4; }
    .fl, .fld > span:first-child { display: block; font-size: 12px; color: var(--secondary-text-color); margin-bottom: 4px; }
    label.fld { margin: 0; }
    .fi { display: flex; align-items: center; border: 1px solid var(--divider-color, #e0e0e0); border-radius: 8px; background: var(--card-background-color, #fff); overflow: hidden; }
    .fi input:not([type=checkbox]) { border: 0; margin: 0; border-radius: 0; background: transparent; min-width: 0; flex: 1; outline: none; }
    .fi em { font-style: normal; color: var(--secondary-text-color); font-size: 13px; padding: 0 10px; }
    .fg { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 10px; align-items: start; }
    .inline { display: flex; align-items: center; gap: 14px; margin-bottom: 12px; flex-wrap: wrap; }
    .note { font-size: 13px; color: var(--secondary-text-color); padding-top: 16px; }
    .stepper { display: inline-flex; align-items: center; border: 1px solid var(--divider-color, #e0e0e0); border-radius: 20px; overflow: hidden; }
    .stepper button { width: 40px; height: 38px; font-size: 20px; color: var(--primary-color); }
    .stepper b { min-width: 40px; text-align: center; font-size: 17px; font-weight: 400; }
    .hint { display: inline-flex; gap: 6px; align-items: center; font-size: 12px; color: var(--primary-color); margin-top: 5px; --mdc-icon-size: 15px; }
    .opts { margin-bottom: 10px; }
    .kinds { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px; }
    .kind { border: 1px solid var(--divider-color, #e0e0e0); border-radius: 10px; padding: 9px 12px; display: flex; gap: 8px; align-items: center; text-align: left; --mdc-icon-size: 18px; }
    .kind ha-icon { color: var(--secondary-text-color); }
    .kind.on { border: 2px solid var(--primary-color); padding: 8px 11px; background: rgba(var(--rgb-primary-color, 3, 169, 244), .1); } .kind.on ha-icon { color: var(--primary-color); }
    .seg { display: inline-flex; border: 1px solid var(--divider-color, #e0e0e0); border-radius: 18px; overflow: hidden; flex-wrap: wrap; }
    .seg button { padding: 8px 12px; font-size: 13px; border-right: 1px solid var(--divider-color, #e0e0e0); }
    .seg button:last-child { border: 0; } .seg button.on { background: var(--primary-color); color: var(--text-primary-color, #fff); }
    .preview { border-radius: 12px; background: rgba(67, 160, 71, .14); padding: 12px 14px; display: flex; gap: 12px; align-items: center; margin-top: 6px; }
    .preview ha-icon { color: var(--success-color, #43a047); flex: none; } .preview b { font-weight: 500; display: block; } .preview small { font-size: 13px; }
    .big { font-size: 28px; margin: 2px 0; overflow-wrap: anywhere; } .bigsub { color: var(--secondary-text-color); font-size: 13px; margin-bottom: 12px; }
    .dual { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 6px; }
    .stat { background: rgba(var(--rgb-primary-text-color, 33, 33, 33), .05); border-radius: 12px; padding: 12px 14px; min-width: 0; }
    .stat .k { font-size: 12px; color: var(--secondary-text-color); display: flex; gap: 6px; align-items: center; --mdc-icon-size: 16px; }
    .stat .n { font-size: 20px; margin: 4px 0 1px; } .stat .d { font-size: 12px; color: var(--secondary-text-color); min-height: 15px; }
    .meter { height: 6px; border-radius: 3px; background: rgba(var(--rgb-primary-text-color, 33, 33, 33), .1); margin-top: 8px; overflow: hidden; }
    .meter i { display: block; height: 100%; background: var(--success-color, #43a047); }
    .h3 { font-size: 13px; font-weight: 500; margin: 16px 0 6px; display: flex; gap: 8px; align-items: center; } .h3 span { font-weight: 400; color: var(--secondary-text-color); }
    .ops { margin: 0; padding: 0; list-style: none; }
    .ops li { display: flex; gap: 10px; align-items: flex-start; padding: 7px 0; border-bottom: 1px solid var(--divider-color, #e0e0e0); --mdc-icon-size: 20px; }
    .ops li:last-child { border: 0; } .ops ha-icon { color: var(--success-color, #43a047); flex: none; }
    .ops small { display: block; color: var(--secondary-text-color); font-size: 12px; }
    .hist { display: flex; gap: 10px; align-items: center; padding: 5px 0; font-size: 13px; --mdc-icon-size: 18px; } .hist ha-icon { color: var(--secondary-text-color); flex: none; }
    .chip { display: inline-block; padding: 5px 12px; border-radius: 16px; background: rgba(var(--rgb-primary-text-color, 33, 33, 33), .06); font-size: 13px; margin: 0 6px 6px 0; }
    .badge { font-size: 12px; padding: 4px 10px; border-radius: 12px; font-weight: 500; }
    .badge.info { background: rgba(var(--rgb-primary-color, 3, 169, 244), .15); color: var(--primary-color); }
    .pol { display: flex; align-items: center; gap: 12px; } .pol span { font-size: 13px; color: var(--secondary-text-color); } .pol b { font-weight: 400; flex: 1; }
    .line { position: relative; height: 34px; margin: 6px 10px 4px; }
    .line .track, .line .fill, .line .amber { position: absolute; top: 14px; height: 6px; border-radius: 3px; }
    .line .track { left: 0; right: 0; background: rgba(var(--rgb-primary-text-color, 33, 33, 33), .1); }
    .line .fill { left: 0; background: var(--success-color, #43a047); } .line .amber { background: var(--warning-color, #f9a825); border-radius: 0; }
    .line .pt { position: absolute; top: 7px; width: 20px; height: 20px; border-radius: 50%; background: var(--card-background-color, #fff); border: 3px solid var(--primary-color); transform: translateX(-50%); }
    .line .pt.now { border-color: var(--success-color, #43a047); background: var(--success-color, #43a047); }
    .calls { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .callb { display: flex; gap: 12px; align-items: center; border-radius: 14px; padding: 12px 14px; text-decoration: none;
      background: rgba(var(--rgb-primary-color, 3, 169, 244), .12); color: var(--primary-color); }
    .callb b { font-weight: 500; display: block; } .callb small { font-size: 13px; }
    .ifoot { display: flex; align-items: center; gap: 8px; margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--divider-color, #e0e0e0); flex-wrap: wrap; }
    .ifoot span { flex: 1; }
    .gearb { width: 40px; height: 40px; border-radius: 50%; background: rgba(var(--rgb-primary-text-color, 33, 33, 33), .06); color: var(--secondary-text-color);
      display: flex; align-items: center; justify-content: center; --mdc-icon-size: 22px; }
    @media (max-width: 520px) { .fg, .dual, .kinds, .calls { grid-template-columns: 1fr; } }
    .prev { background: rgba(var(--rgb-primary-text-color, 33, 33, 33), .05); border-radius: 16px; text-align: center; padding-top: 4px; margin-bottom: 4px; overflow: hidden; }
    .prev img { width: 88%; display: block; margin: 0 auto -4px; }
    .lbl { font-size: 13px; color: var(--secondary-text-color); margin: 14px 0 6px; }
    .opts { display: flex; gap: 8px; flex-wrap: wrap; }
    .opt { border: 1px solid var(--divider-color, #e0e0e0); border-radius: 12px; padding: 9px 14px; text-align: left; }
    .opt small { display: block; color: var(--secondary-text-color); font-size: 12px; margin-top: 2px; }
    .opt.on { border: 2px solid var(--primary-color); padding: 8px 13px; background: rgba(var(--rgb-primary-color, 3, 169, 244), .1); }
    .sw { display: flex; gap: 8px; flex-wrap: wrap; }
    .sw button { display: flex; flex-direction: column; align-items: center; gap: 6px; font-size: 12px; width: 92px; padding: 4px 0; }
    .sw i { display: block; width: 44px; height: 44px; border-radius: 50%; border: 1px solid var(--divider-color, #cfd8dc); }
    .sw .on i { outline: 3px solid var(--primary-color); outline-offset: 2px; }
    [hidden] { display: none !important; }
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
    };
    const onKey = (event) => event.key === "Escape" && close();
    document.addEventListener("keydown", onKey);
    host.addEventListener("click", (event) => {
      const path = event.composedPath();
      if (path[0] === host) return close(); // toque en el fondo oscuro
      const target = path.find((node) => node.dataset && node.dataset.action);
      if (!target) return undefined;
      if (target.dataset.action === "close") return close();
      return onAction(target.dataset.action, dialog, target);
    });
    const dialog = {
      root,
      close,
      /** Valores del formulario: `{ nombre: valor }` (casillas → true/false). */
      values() {
        const values = {};
        for (const field of root.querySelectorAll("[name]")) {
          values[field.name] = field.type === "checkbox" ? field.checked : field.value;
        }
        return values;
      },
      error(text) {
        const box = root.querySelector(".err");
        if (box) box.textContent = text || "";
      },
    };
    document.body.append(host);
    return dialog;
  }

  // ── src/50_panel.js ───────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // El panel: carga de datos, pestañas y reparto de las pulsaciones
  // ---------------------------------------------------------------------------
  class DecDeepalPanel extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._tab = "cars";
      this._state = null; // lo que devuelve "state" (panel.py)
      this._error = "";
      this._open = new Set(); // apartados de avisos desplegados: "<coche>/<apartado>"
      this._drafts = {}; // avisos cambiados y sin guardar, por coche
      this._editing = null; // plazo que se está editando: { car, notice }
      this._filter = "all"; // filtro del historial
      this._links = {}; // enlaces firmados (copia, diagnósticos)
      this._settings = {}; // ajustes cambiados y sin guardar, por cuenta
      this.shadowRoot.addEventListener("click", (event) => this._onClick(event));
      this.shadowRoot.addEventListener("change", (event) => this._onChange(event));
      this.shadowRoot.addEventListener("input", (event) => this._onInput(event));
      this.shadowRoot.addEventListener("keydown", (event) => this._onKey(event));
    }

    // --- Lo que Home Assistant le pasa a un panel --------------------------------

    set hass(hass) {
      const first = !this._hass;
      const language = first ? "" : this._language();
      this._hass = hass;
      if (first) this._load();
      else if (language !== this._language()) this._render();
      this._syncMenu();
    }

    set narrow(narrow) {
      this._narrow = narrow;
      this._syncMenu();
    }

    // --- Idioma y textos ---------------------------------------------------------

    _language() {
      const hass = this._hass || {};
      return (hass.locale && hass.locale.language) || hass.language || BASE_LANGUAGE;
    }

    _t(key, values) {
      return translate(this._language(), key, values);
    }

    /** Texto si existe; si no, `undefined` (para claves opcionales). */
    _maybe(key, values) {
      return key in TEXTS[textLanguage(this._language())] ? this._t(key, values) : undefined;
    }

    /** Número con separador de miles siempre ("5.000": el español no lo pone con cuatro cifras). */
    _number(value) {
      try {
        return new Intl.NumberFormat(this._language(), { useGrouping: "always" }).format(Number(value));
      } catch (_error) {
        return Number(value).toLocaleString(this._language());
      }
    }

    _date(iso) {
      if (!iso) return "—";
      const [year, month, day] = String(iso).slice(0, 10).split("-").map(Number);
      return new Date(year, month - 1, day).toLocaleDateString(this._language(), { day: "numeric", month: "short", year: "numeric" });
    }

    _days(count) {
      return this._t(Math.abs(count) === 1 ? "day" : "days", { value: this._number(Math.abs(count)) });
    }

    // --- Datos ---------------------------------------------------------------------

    _ws(type, data) {
      return this._hass.callWS({ type: WS + type, ...(data || {}) });
    }

    async _load() {
      try {
        this._state = await this._ws("state");
        this._error = "";
      } catch (error) {
        this._error = (error && error.message) || this._t("error_generic");
      }
      this._render();
    }

    /**
     * Ejecuta una orden y vuelve a pedir el estado. Algunos cambios recargan
     * la integración: por eso se pide otra vez pasados unos segundos.
     */
    async _run(type, data, done) {
      try {
        const result = await this._ws(type, data);
        if (done) this._toast(done);
        await this._load();
        clearTimeout(this._again);
        this._again = setTimeout(() => this._load(), 3500);
        return result === undefined || result === null ? true : result;
      } catch (error) {
        this._toast(this._errorText(error));
        return false;
      }
    }

    _errorText(error) {
      const code = error && error.code;
      return this._maybe(`error_${code}`) || (error && error.message) || this._t("error_generic");
    }

    _toast(message) {
      this.dispatchEvent(new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }));
    }

    _car(id) {
      return this._state.cars.find((car) => car.id === id);
    }

    /** Foto del coche: la entidad de imagen de la integración (de lado; si no, la isométrica). */
    _photo(car) {
      const hass = this._hass;
      for (const key of ["dec_photo", "isometric_view"]) {
        for (const [entityId, entry] of Object.entries(hass.entities || {})) {
          if (entry.platform !== DOMAIN || entry.device_id !== car.device_id || entry.translation_key !== key) continue;
          if (!entityId.startsWith("image.")) continue;
          const state = hass.states[entityId];
          const picture = state && state.attributes.entity_picture;
          if (picture) return `${picture}${picture.includes("?") ? "&" : "?"}state=${encodeURIComponent(state.state)}`;
        }
      }
      return "";
    }

    // --- Pintado ---------------------------------------------------------------------

    _render() {
      const root = this.shadowRoot;
      const scroller = root.querySelector(".scroll");
      const top = scroller ? scroller.scrollTop : 0;
      const tabs = TABS.map(
        ([key, icon]) =>
          `<button class="${key === this._tab ? "on" : ""}" data-action="tab" data-tab="${key}"><ha-icon icon="${icon}"></ha-icon>${this._t(`tab_${key}`)}</button>`
      ).join("");
      let view;
      if (this._error) view = `<div class="empty">${escapeHtml(this._error)}<br><br><button class="btn o" data-action="reload">${this._t("retry")}</button></div>`;
      else if (!this._state) view = `<div class="empty">${this._t("loading")}</div>`;
      else if (!this._state.cars.length) view = `<div class="empty">${this._t("no_cars")}</div>`;
      else view = this[`_view_${this._tab}`]();
      root.innerHTML = `<style>${PANEL_CSS}</style>
        <div class="page">
          <div class="bar">
            <div class="top"><ha-menu-button></ha-menu-button><span>DEC Deepal</span><small>${this._state ? `v${escapeHtml(this._state.version)}` : ""}</small></div>
            <div class="tabs">${tabs}</div>
          </div>
          <div class="scroll"><div class="view">${view}</div></div>
        </div>`;
      this._syncMenu();
      root.querySelector(".scroll").scrollTop = top;
      const input = root.querySelector(".inp input");
      if (input) {
        input.focus();
        input.select();
      }
    }

    /** El botón del menú lateral es de Home Assistant: hay que pasarle sus datos. */
    _syncMenu() {
      const button = this.shadowRoot.querySelector("ha-menu-button");
      if (!button) return;
      button.hass = this._hass;
      button.narrow = this._narrow;
    }

    // --- Pulsaciones -------------------------------------------------------------------

    _onClick(event) {
      const target = event.composedPath().find((node) => node.dataset && node.dataset.action);
      if (!target) return;
      const handler = this[`_do_${target.dataset.action.replace(/-/g, "_")}`];
      if (handler) handler.call(this, target.dataset, target, event);
    }

    _onChange(event) {
      const target = event.target;
      if (target && target.dataset && target.dataset.change) this[`_change_${target.dataset.change}`](target);
    }

    _onInput(event) {
      const target = event.target;
      if (target && target.dataset && target.dataset.input) this._input_setting(target);
    }

    _onKey(event) {
      // Los recuadros que hacen de botón se abren también con Intro o Espacio.
      if ((event.key === "Enter" || event.key === " ") && event.target.matches && event.target.matches("[role=button][data-action]")) {
        event.preventDefault();
        event.target.click();
        return;
      }
      if (!this._editing || !event.target.matches || !event.target.matches(".inp input")) return;
      if (event.key === "Enter") this._do_edit_ok();
      if (event.key === "Escape") this._do_edit_cancel();
    }

    _do_tab(data) {
      this._tab = data.tab;
      this._editing = null;
      this._render();
      if (data.tab === "data" || data.tab === "diagnostics") this._prepareLinks();
    }

    _do_reload() {
      this._load();
    }
  }

  /**
   * Añade al panel los métodos de una clase. Cada pestaña está en su fichero
   * y se engancha así: dentro, `this` es el panel, igual que arriba.
   */
  const install = (source) => {
    for (const name of Object.getOwnPropertyNames(source.prototype)) {
      if (name === "constructor") continue;
      Object.defineProperty(DecDeepalPanel.prototype, name, Object.getOwnPropertyDescriptor(source.prototype, name));
    }
  };

  // ── src/60_coches.js ──────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Pestaña "Coches"
  // ---------------------------------------------------------------------------
  install(class {
    _view_cars() {
      return this._state.cars.map((car) => this._carCard(car)).join("");
    }

    _carCard(car) {
      const photo = this._photo(car);
      const sheet = car.sheet || {};
      const features = sheet.funciones || {};
      const chips = car.configured
        ? FEATURES.filter(([key]) => features[key]).map(([, icon, text]) => `<span class="chip"><ha-icon icon="${icon}"></ha-icon>${this._t(text)}</span>`)
        : [];
      if (car.wheel) chips.push(`<span class="chip"><ha-icon icon="mdi:tire"></ha-icon>${this._maybe(`wheel_${car.wheel}`) || escapeHtml(car.wheel)}</span>`);
      const badge = !car.configured
        ? `<span class="badge warn"><ha-icon icon="mdi:alert-circle-outline"></ha-icon>${this._t("not_configured")}</span>`
        : sheet.verificada
          ? `<span class="badge ok"><ha-icon icon="mdi:check-decagram"></ha-icon>${this._t("sheet_verified")}</span>`
          : `<span class="badge info"><ha-icon icon="mdi:book-open-variant"></ha-icon>${this._t("sheet_catalogue")}</span>`;
      const fact = (value, label) => `<div><b>${value}</b>${this._t(label)}</div>`;
      return `<div class="card">
        <div class="hero">
          ${photo ? `<img src="${escapeHtml(photo)}" alt="">` : ""}
          <div class="who">
            <div class="n">${escapeHtml(car.name)}</div>
            <div class="m">${escapeHtml([car.model, car.color].filter(Boolean).join(" · "))}</div>
            ${badge}
            <div class="kv">
              ${car.battery == null ? "" : fact(`${this._number(car.battery)} %`, "battery")}
              ${car.range == null ? "" : fact(`${this._number(Math.round(car.range))} km`, "range")}
              ${car.odometer == null ? "" : fact(`${this._number(Math.round(car.odometer))} km`, "odometer")}
            </div>
          </div>
          <button class="btn o" data-action="appearance" data-car="${escapeHtml(car.id)}"><ha-icon icon="mdi:pencil"></ha-icon>${this._t("appearance")}</button>
        </div>
        ${chips.length ? `<div class="chips">${chips.join("")}</div>` : ""}
        <div class="grid3">
          ${this._maintenanceTile(car)}
          ${car.itv_available ? this._itvTile(car) : ""}
          ${this._insuranceTile(car)}
        </div>
      </div>`;
    }

    /** Recuadro con engranaje; `body` va vacío si el apartado está sin configurar. */
    _tile(car, kind, icon, level, body) {
      const gear = `<button class="gear" data-action="gear" data-kind="${kind}" data-car="${escapeHtml(car.id)}" aria-label="${this._t("configure")}"><ha-icon icon="mdi:cog"></ha-icon></button>`;
      const head = `<div class="h"><ha-icon icon="${icon}"></ha-icon><span>${this._t(`section_${kind}`)}</span>${gear}</div>`;
      if (!body) {
        return `<div class="tile off" data-action="info" data-kind="${kind}" data-car="${escapeHtml(car.id)}">${head}<div class="v">${this._t("not_set")}</div>
          <button class="link" data-action="gear" data-kind="${kind}" data-car="${escapeHtml(car.id)}">${this._t(`add_${kind}`)}</button></div>`;
      }
      return `<div class="tile ${level}" data-action="info" data-kind="${kind}" data-car="${escapeHtml(car.id)}" role="button" tabindex="0">${head}${body}</div>`;
    }

    _meter(fraction) {
      return `<div class="meter"><i style="width:${Math.round(Math.max(0, Math.min(1, fraction)) * 100)}%"></i></div>`;
    }

    _maintenanceTile(car) {
      const data = car.maintenance;
      if (!data) return this._tile(car, "maintenance", "mdi:wrench", "", "");
      const left = [];
      if (data.days_left >= 0) left.push(this._days(data.days_left));
      if (data.km_left != null && data.km_left >= 0) left.push(`${this._number(data.km_left)} km`);
      const overdue = data.level === "overdue";
      // Lo recorrido del intervalo: lo que más avance, tiempo o kilómetros.
      const months = data.record.interval_months * 30.4;
      const byDays = 1 - data.days_left / months;
      const byKm = data.km_left == null ? 0 : 1 - data.km_left / data.record.interval_km;
      return this._tile(car, "maintenance", "mdi:wrench", data.level,
        `<div class="v">${this._t("service_number", { number: data.number })}</div>
         <div class="d">${overdue ? this._t("overdue") : this._t("left", { parts: left.join(this._t("or")) })}</div>
         ${this._meter(Math.max(byDays, byKm))}`);
    }

    _itvTile(car) {
      const data = car.itv;
      if (!data) return this._tile(car, "itv", "mdi:clipboard-check-outline", "", "");
      const overdue = data.days_left < 0;
      return this._tile(car, "itv", "mdi:clipboard-check-outline", data.level,
        `<div class="v">${this._date(data.due_date)}</div>
         <div class="d">${overdue ? this._t("overdue_since", { days: this._days(data.days_left) }) : this._t("left", { parts: this._days(data.days_left) })}</div>
         ${this._meter(1 - data.days_left / 730)}`);
    }

    _insuranceTile(car) {
      const data = car.insurance;
      if (!data) return this._tile(car, "insurance", "mdi:shield-car", "", "");
      const detail = data.days_to_cancel >= 0
        ? this._t("cancel_until", { date: this._date(data.cancel_deadline) })
        : this._t("renews_in", { days: this._days(data.days_to_renewal) });
      return this._tile(car, "insurance", "mdi:shield-car", data.level,
        `<div class="v">${this._date(data.record.renewal_date)}</div>
         <div class="d">${escapeHtml(detail)}</div>
         ${this._meter(1 - data.days_to_renewal / 365)}`);
    }
  });

  // ── src/61_avisos.js ──────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Pestaña "Avisos": una tabla por coche, con sus apartados plegables
  // ---------------------------------------------------------------------------
  // Lo que se toca se guarda en un borrador del coche (this._drafts) hasta que
  // se pulsa "Guardar": guardar recarga la integración, y no conviene hacerlo
  // con cada casilla.
  install(class {
    _view_alerts() {
      return this._state.cars.map((car) => this._alertsCard(car)).join("");
    }

    /** Avisos de un coche tal como se ven ahora: el borrador o lo guardado. */
    _alerts(car) {
      return this._drafts[car.id] || car.alerts;
    }

    /** Borrador del coche (se crea, copiando lo guardado, la primera vez). */
    _draft(car) {
      if (!this._drafts[car.id]) this._drafts[car.id] = JSON.parse(JSON.stringify(car.alerts));
      return this._drafts[car.id];
    }

    _threshold(car, notice) {
      const changed = this._alerts(car).thresholds[notice.id];
      return changed == null ? notice.threshold : changed;
    }

    /** Avisos de un apartado para un coche (la ITV solo donde existe). */
    _notices(car, section) {
      if (section === "itv" && !car.itv_available) return [];
      return this._state.notices.filter((notice) => notice.section === section);
    }

    _when(car, notice) {
      if (notice.threshold == null) return this._maybe(`when_${notice.id}`) || "";
      const value = this._number(this._threshold(car, notice));
      if (notice.unit === "km") return this._t("when_km", { value });
      return this._t(notice.id.startsWith("insurance_c") ? "when_days_deadline" : "when_days", { value });
    }

    _alertsCard(car) {
      const targets = this._state.targets;
      const alerts = this._alerts(car);
      const photo = this._photo(car);
      const box = (state, action, extra) =>
        `<td><button class="box ${state}" data-action="${action}" data-car="${escapeHtml(car.id)}" ${extra} aria-pressed="${state === "y"}">
          <ha-icon icon="mdi:${state === "y" ? "checkbox-marked" : state === "some" ? "minus-box" : "checkbox-blank-outline"}"></ha-icon></button></td>`;
      const rows = [];
      for (const [section, icon] of SECTIONS) {
        const notices = this._notices(car, section);
        if (!notices.length) continue;
        const open = this._open.has(`${car.id}/${section}`);
        const configured = !["maintenance", "itv", "insurance"].includes(section) || car[section];
        const note = configured ? (open ? "" : this._t("n_notices", { count: notices.length })) : this._t("not_set");
        rows.push(`<tr class="grp"><td><button class="fold" data-action="fold" data-car="${escapeHtml(car.id)}" data-section="${section}" aria-expanded="${open}">
            <ha-icon icon="mdi:chevron-${open ? "down" : "right"}"></ha-icon><ha-icon class="sic" icon="${icon}"></ha-icon>${this._t(`section_${section}`)}<small>${note}</small></button></td>
          ${targets.map((target) => {
            const count = notices.filter((notice) => (alerts.notices[notice.id] || []).includes(target.id)).length;
            const state = count === notices.length ? "y" : count ? "some" : "";
            return box(state, "section-cell", `data-section="${section}" data-target="${escapeHtml(target.id)}"`);
          }).join("")}</tr>`);
        if (!open) continue;
        for (const notice of notices) {
          const editing = this._editing && this._editing.car === car.id && this._editing.notice === notice.id;
          const pen = notice.threshold == null
            ? ""
            : `<button class="pen" data-action="edit" data-car="${escapeHtml(car.id)}" data-notice="${notice.id}" aria-label="${this._t("edit_threshold")}"><ha-icon icon="mdi:pencil"></ha-icon></button>`;
          const label = editing
            ? `<div class="lab"><b>${this._t(`notice_${notice.id}`)}</b><small></small>
                <span class="inp"><input type="number" min="${notice.limits[0]}" max="${notice.limits[1]}" value="${this._threshold(car, notice)}"><span>${this._t(notice.unit === "km" ? "unit_km" : "unit_days")}</span></span>
                <button class="mini ok" data-action="edit-ok" aria-label="${this._t("accept")}"><ha-icon icon="mdi:check"></ha-icon></button>
                <button class="mini" data-action="edit-cancel" aria-label="${this._t("cancel")}"><ha-icon icon="mdi:close"></ha-icon></button></div>`
            : `<div class="lab"><b>${this._t(`notice_${notice.id}`)}</b><small>${escapeHtml(this._when(car, notice))}</small>${pen}</div>`;
          rows.push(`<tr class="it ${editing ? "ed" : ""}"><td>${label}</td>
            ${targets.map((target) => box((alerts.notices[notice.id] || []).includes(target.id) ? "y" : "", "cell",
              `data-notice="${notice.id}" data-target="${escapeHtml(target.id)}"`)).join("")}</tr>`);
        }
      }
      const dirty = Boolean(this._drafts[car.id]);
      const changedThresholds = Object.keys(alerts.thresholds).length > 0;
      const others = this._state.cars.length > 1;
      return `<div class="card" data-car-card="${escapeHtml(car.id)}">
        <div class="chead">
          ${photo ? `<img src="${escapeHtml(photo)}" alt="">` : ""}
          <div class="n">${escapeHtml(car.name)}<small>${escapeHtml(car.model)}</small></div>
          ${others ? `<button class="btn o" data-action="copy-alerts" data-car="${escapeHtml(car.id)}"><ha-icon icon="mdi:content-copy"></ha-icon>${this._t("copy_from")}</button>` : ""}
        </div>
        <div class="wide"><table>
          <tr><th>${this._t("notify_to")}</th>${targets.map((target) =>
            `<th><div class="dev ${target.kind}"><u><ha-icon icon="${TARGET_ICONS[target.kind] || TARGET_ICONS.service}"></ha-icon></u>${escapeHtml(target.name)}</div></th>`).join("")}</tr>
          ${rows.join("")}
        </table></div>
        <div class="foot ${dirty ? "dirty" : ""}">
          <span>${dirty ? this._t("unsaved") : this._t("alerts_help")}</span>
          ${changedThresholds ? `<button class="btn o" data-action="reset-thresholds" data-car="${escapeHtml(car.id)}"><ha-icon icon="mdi:restore"></ha-icon>${this._t("factory_thresholds")}</button>` : ""}
          ${dirty ? `<button class="btn o" data-action="discard-alerts" data-car="${escapeHtml(car.id)}">${this._t("discard")}</button>
                     <button class="btn" data-action="save-alerts" data-car="${escapeHtml(car.id)}">${this._t("save")}</button>` : ""}
        </div>
      </div>`;
    }

    _do_fold(data) {
      const key = `${data.car}/${data.section}`;
      if (!this._open.delete(key)) this._open.add(key);
      this._editing = null;
      this._render();
    }

    _toggle(list, target, on) {
      const without = (list || []).filter((item) => item !== target);
      return on ? [...without, target] : without;
    }

    _do_cell(data) {
      const draft = this._draft(this._car(data.car));
      const on = !(draft.notices[data.notice] || []).includes(data.target);
      draft.notices[data.notice] = this._toggle(draft.notices[data.notice], data.target, on);
      this._render();
    }

    /** Casilla del apartado: marca todos sus avisos (o los desmarca si ya lo estaban todos). */
    _do_section_cell(data) {
      const car = this._car(data.car);
      const draft = this._draft(car);
      const notices = this._notices(car, data.section);
      const all = notices.every((notice) => (draft.notices[notice.id] || []).includes(data.target));
      for (const notice of notices) draft.notices[notice.id] = this._toggle(draft.notices[notice.id], data.target, !all);
      this._render();
    }

    _do_edit(data) {
      this._editing = { car: data.car, notice: data.notice };
      this._render();
    }

    _do_edit_cancel() {
      this._editing = null;
      this._render();
    }

    _do_edit_ok() {
      const { car: carId, notice: noticeId } = this._editing;
      const car = this._car(carId);
      const notice = this._state.notices.find((item) => item.id === noticeId);
      const value = Math.round(Number(this.shadowRoot.querySelector(".inp input").value));
      const [low, high] = notice.limits;
      if (!Number.isFinite(value) || value < low || value > high) {
        this._toast(this._t("error_threshold_range_limits", { low: this._number(low), high: this._number(high) }));
        return;
      }
      const draft = this._draft(car);
      if (value === notice.threshold) delete draft.thresholds[noticeId];
      else draft.thresholds[noticeId] = value;
      this._editing = null;
      this._render();
    }

    _do_reset_thresholds(data) {
      this._draft(this._car(data.car)).thresholds = {};
      this._render();
    }

    _do_discard_alerts(data) {
      delete this._drafts[data.car];
      this._editing = null;
      this._render();
    }

    async _do_save_alerts(data) {
      const draft = this._drafts[data.car];
      if (!draft) return;
      const done = await this._run("set_alerts", { vehicle_id: data.car, notices: draft.notices, thresholds: draft.thresholds }, this._t("saved"));
      if (done) {
        delete this._drafts[data.car];
        this._render();
      }
    }

    /** Copia los avisos y los plazos de otro coche al borrador de este (falta guardar). */
    _do_copy_alerts(data) {
      const others = this._state.cars.filter((car) => car.id !== data.car);
      const copy = (fromId) => {
        const from = this._car(fromId);
        const mine = this._car(data.car);
        const source = JSON.parse(JSON.stringify(this._alerts(from)));
        // La ITV no se copia a un coche que no la tiene.
        if (!mine.itv_available) for (const notice of this._state.notices) if (notice.section === "itv") source.notices[notice.id] = [];
        this._drafts[data.car] = source;
        this._render();
      };
      if (others.length === 1) return copy(others[0].id);
      const options = others.map((car) => `<option value="${escapeHtml(car.id)}">${escapeHtml(car.name)}</option>`).join("");
      openDialog(
        `<h2>${this._t("copy_from")}</h2><label>${this._t("car")}<select name="from">${options}</select></label>
         <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("copy")}</button></div>`,
        (action, dialog) => {
          if (action !== "ok") return;
          copy(dialog.values().from);
          dialog.close();
        }
      );
      return undefined;
    }
  });

  // ── src/62_datos.js ───────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Pestaña "Datos": copia de seguridad y datos guardados
  // ---------------------------------------------------------------------------
  install(class {
    _view_data() {
      const mobiles = this._state.targets.filter((target) => target.kind === "mobile");
      const link = this._links.backup;
      const stored = this._state.stored.map((item) => {
        const has = item.has.map((section) => this._t(`section_${section}`)).join(" · ");
        return `<div class="row">
          <div class="ic ${item.in_account ? "" : "grey"}"><ha-icon icon="mdi:${item.in_account ? "car" : "car-off"}"></ha-icon></div>
          <div class="tx">${escapeHtml(item.label)} <span style="color:var(--secondary-text-color)">(…${escapeHtml(item.tail)})</span>
            <small>${escapeHtml(has)}${item.in_account ? "" : `. ${this._t("no_account_note")}`}</small></div>
          <span class="badge ${item.in_account ? "info" : "warn"}">${this._t(item.in_account ? "in_account" : "no_account")}</span>
          <button class="btn r" data-action="delete-data" data-key="${escapeHtml(item.key)}" data-label="${escapeHtml(item.label)}"><ha-icon icon="mdi:delete-outline"></ha-icon>${this._t("delete")}</button>
        </div>`;
      });
      return `<div class="card">
          <h2>${this._t("backup_title")}</h2><div class="sub">${this._t("backup_help")}</div>
          <div class="row"><div class="ic"><ha-icon icon="mdi:download"></ha-icon></div>
            <div class="tx">${this._t("download_title")}<small>${this._t("download_help")}</small></div>
            <a class="btn" ${link ? `href="${escapeHtml(link)}"` : "disabled"} target="_blank" rel="noopener noreferrer" data-action="downloaded"><ha-icon icon="mdi:download"></ha-icon>${this._t("download")}</a></div>
          ${mobiles.length ? `<div class="row"><div class="ic"><ha-icon icon="mdi:cellphone-arrow-down"></ha-icon></div>
            <div class="tx">${this._t("send_title")}<small>${this._t("send_help")}</small></div>
            <select data-field="mobile">${mobiles.map((target) => `<option value="${escapeHtml(target.id)}">${escapeHtml(target.name)}</option>`).join("")}</select>
            <button class="btn o" data-action="send-backup"><ha-icon icon="mdi:send"></ha-icon>${this._t("send")}</button></div>` : ""}
          <div class="row"><div class="ic"><ha-icon icon="mdi:upload"></ha-icon></div>
            <div class="tx">${this._t("upload_title")}<small>${this._t("upload_help")}</small></div>
            <label class="btn o"><ha-icon icon="mdi:upload"></ha-icon>${this._t("choose_file")}<input type="file" accept=".json,application/json" data-change="backup" hidden></label></div>
        </div>
        <div class="card">
          <h2>${this._t("stored_title")}</h2><div class="sub">${this._t("stored_help")}</div>
          ${stored.length ? stored.join("") : `<div class="row"><div class="tx" style="color:var(--secondary-text-color)">${this._t("stored_none")}</div></div>`}
        </div>`;
    }

    /**
     * Enlaces firmados (caducan en minutos): se piden al abrir la pestaña para
     * que el botón sea un enlace de verdad, que se abre en el navegador también
     * desde la app del móvil.
     */
    async _prepareLinks() {
      try {
        const backup = await this._ws("export_url");
        this._links.backup = backup.url;
        for (const entryId of new Set(this._state.cars.map((car) => car.entry_id))) {
          const signed = await this._hass.callWS({ type: "auth/sign_path", path: `/api/diagnostics/config_entry/${entryId}` });
          this._links[`diagnostics_${entryId}`] = signed.path;
        }
      } catch (_error) {
        // Sin enlace: el botón queda desactivado.
      }
      if (this._tab === "data" || this._tab === "diagnostics") this._render();
    }

    /** El enlace sirve una vez con garantías: se pide otro para la próxima. */
    _do_downloaded() {
      setTimeout(() => this._prepareLinks(), 1500);
    }

    async _do_send_backup() {
      const select = this.shadowRoot.querySelector('select[data-field="mobile"]');
      const name = select.options[select.selectedIndex].textContent;
      await this._run("send_backup", { target: select.value }, this._t("sent_to", { device: name }));
    }

    async _change_backup(input) {
      const file = input.files && input.files[0];
      input.value = "";
      if (!file) return;
      let backup;
      try {
        backup = JSON.parse(await file.text());
      } catch (_error) {
        backup = null;
      }
      if (!backup || typeof backup !== "object" || Array.isArray(backup)) {
        this._toast(this._t("error_invalid_file"));
        return;
      }
      const result = await this._run("import_backup", { backup });
      if (result) this._toast(this._t("imported", { cars: (result.cars || []).join(", ") }));
    }

    _do_delete_data(data) {
      openDialog(
        `<h2>${this._t("delete_title")}</h2><p>${this._t("delete_confirm", { name: `<b>${escapeHtml(data.label)}</b>` })}</p>
         <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb danger" data-action="ok">${this._t("delete")}</button></div>`,
        async (action, dialog) => {
          if (action !== "ok") return;
          dialog.close();
          await this._run("delete_data", { keys: [data.key] }, this._t("deleted"));
        }
      );
    }
  });

  // ── src/63_diagnostico.js ─────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Pestaña "Diagnóstico": qué ha pasado y la ficha de cada coche
  // ---------------------------------------------------------------------------
  install(class {
    _view_diagnostics() {
      const history = this._state.history;
      const events = [...history.cambios, ...history.ordenes, ...history.avisos]
        .map((event) => this._event(event))
        .filter((item) => this._matches(item))
        .sort((a, b) => (a.time < b.time ? 1 : -1))
        .slice(0, HISTORY_LIMIT);
      const names = [...new Set(this._state.cars.map((car) => car.name))];
      const filters = [["all", this._t("filter_all")], ...names.map((name) => [`car:${name}`, name]),
        ["orders", this._t("filter_orders")], ["alerts", this._t("filter_alerts")], ["errors", this._t("filter_errors")]];
      const sheets = this._state.cars.map((car) => {
        const sheet = car.sheet || {};
        const link = this._links[`diagnostics_${car.entry_id}`];
        return `<div class="row"><div class="ic"><ha-icon icon="mdi:car-info"></ha-icon></div>
          <div class="tx">${escapeHtml(car.name)} · ${escapeHtml(car.model)}<small>${escapeHtml(sheet.origen || "")}</small></div>
          <span class="badge ${sheet.verificada ? "ok" : "info"}">${this._t(sheet.verificada ? "sheet_verified" : "sheet_catalogue")}</span>
          <a class="btn o" ${link ? `href="${escapeHtml(link)}"` : "disabled"} target="_blank" rel="noopener noreferrer" data-action="downloaded"><ha-icon icon="mdi:download"></ha-icon>${this._t("diagnostics_file")}</a>
        </div>`;
      });
      return `<div class="card">
          <h2>${this._t("history_title")}</h2><div class="sub">${this._t("history_help")}</div>
          <div class="filt">${filters.map(([key, name]) => `<button class="${key === this._filter ? "on" : ""}" data-action="filter" data-filter="${escapeHtml(key)}">${escapeHtml(name)}</button>`).join("")}</div>
          ${events.length ? events.map((item) => `<div class="log"><time>${escapeHtml(this._time(item.time))}</time>
              <div class="dot ${item.tone}"><ha-icon icon="${item.icon}"></ha-icon></div>
              <div class="what">${escapeHtml(item.title)}<small>${escapeHtml(item.detail)}</small></div></div>`).join("")
            : `<div class="row"><div class="tx" style="color:var(--secondary-text-color)">${this._t("history_none")}</div></div>`}
        </div>
        <div class="card">
          <h2>${this._t("sheets_title")}</h2><div class="sub">${this._t("sheets_help")}</div>
          ${sheets.join("")}
        </div>`;
    }

    /** Un evento del historial, listo para pintar. */
    _event(event) {
      const car = event.vehicle || "";
      const failed = Boolean(event.error) || event.ok === false || ["rechazado", "error_envio"].includes(event.stage);
      if (event.kind === "alert") {
        return { time: event.time, car, group: "alerts", tone: "blue", icon: "mdi:bell-ring",
          title: this._t("ev_alert", { name: this._maybe(`notice_${event.type}`) || this._maybe(`section_${event.type}`) || event.type }),
          detail: [car, this._t("ev_targets", { count: event.sent == null ? event.targets : event.sent })].filter(Boolean).join(" · ") };
      }
      if (event.kind === "change") {
        const changes = event.changes || [];
        return { time: event.time, car, group: "changes", tone: "green", icon: "mdi:swap-horizontal",
          title: changes.slice(0, 3).join(" · ") + (changes.length > 3 ? ` (+${changes.length - 3})` : ""), detail: car };
      }
      if (event.kind === "wake") {
        return { time: event.time, car, group: "orders", tone: failed ? "red" : "", icon: "mdi:sleep-off", failed,
          title: this._t("ev_wake"), detail: [car, event.error || event.stage || ""].filter(Boolean).join(" · ") };
      }
      return { time: event.time, car, group: "orders", tone: failed ? "red" : "", icon: "mdi:remote", failed,
        title: this._t("ev_command", { name: event.name || "" }),
        detail: [car, event.stage, event.code == null ? "" : `${this._t("ev_code")} ${event.code}`, event.error].filter(Boolean).join(" · ") };
    }

    _matches(item) {
      const filter = this._filter;
      if (filter === "all") return true;
      if (filter === "errors") return Boolean(item.failed);
      if (filter.startsWith("car:")) return item.car === filter.slice(4);
      return item.group === filter;
    }

    /** "Hoy 13:38", "Ayer 21:09" o "9 oct 20:47". */
    _time(iso) {
      const date = new Date(iso);
      if (Number.isNaN(date.getTime())) return "";
      const language = this._language();
      const time = date.toLocaleTimeString(language, { hour: "2-digit", minute: "2-digit" });
      const day = (value) => new Date(value.getFullYear(), value.getMonth(), value.getDate()).getTime();
      const days = Math.round((day(new Date()) - day(date)) / 86400000);
      if (days === 0) return `${this._t("today")} ${time}`;
      if (days === 1) return `${this._t("yesterday")} ${time}`;
      return `${date.toLocaleDateString(language, { day: "numeric", month: "short" })} ${time}`;
    }

    _do_filter(data) {
      this._filter = data.filter;
      this._render();
    }
  });

  // ── src/64_formularios.js ─────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Engranajes de "Coches": configurar mantenimiento, ITV y seguro
  // ---------------------------------------------------------------------------
  // Cada formulario va por bloques y termina con un recuadro que dice qué va a
  // pasar ("Próxima revisión: ..."), recalculado según se escribe. Lo escrito
  // vive en un objeto `f`; al pulsar una opción se repinta la ventana entera,
  // y al teclear solo el recuadro (para no perder el cursor).
  install(class {
    _do_gear(data) {
      this[`_form_${data.kind}`](this._car(data.car));
    }

    /** Campo de texto, fecha o número. `more`: atributos; `unit`: unidad a la derecha. */
    _input(f, name, label, type, more, unit) {
      return `<label class="fld"><span>${this._t(label)}</span>
        <span class="fi"><input data-f="${name}" type="${type}" value="${escapeHtml(f[name] == null ? "" : f[name])}" ${more || ""}>${unit ? `<em>${unit}</em>` : ""}</span></label>`;
    }

    _section(icon, title, help, body) {
      return `<div class="fsec"><h4><ha-icon icon="${icon}"></ha-icon>${this._t(title)}</h4><div class="hp">${this._t(help)}</div>${body}</div>`;
    }

    /** Opción de un grupo (una está elegida): botón con título y, si la hay, una nota. */
    _choice(f, name, value, title, note) {
      const on = String(f[name]) === String(value);
      return `<button class="opt ${on ? "on" : ""}" data-action="set" data-f="${name}" data-v="${escapeHtml(value)}" aria-pressed="${on}">${escapeHtml(title)}${note ? `<small>${escapeHtml(note)}</small>` : ""}</button>`;
    }

    /**
     * Ventana de un apartado.
     *
     * @param parts
     *   sections(f)  bloques del formulario (HTML)
     *   preview(f)   `{ icon, title, detail }` del recuadro final, o `null` si aún faltan datos
     *   check(f)     texto del error que impide guardar ("" = todo bien)
     *   data(f)      lo que se manda a la integración
     */
    _formWindow(car, kind, icon, f, parts) {
      const preview = () => {
        const result = f.enabled ? parts.preview(f) : null;
        return result
          ? `<div class="preview"><ha-icon icon="${result.icon}"></ha-icon><div><b>${escapeHtml(result.title)}</b><small>${escapeHtml(result.detail)}</small></div></div>`
          : "";
      };
      const body = () => `
        <div class="thead"><div class="ic"><ha-icon icon="${icon}"></ha-icon></div>
          <h2>${this._t(`form_${kind}`)}<small>${escapeHtml(car.name)} · ${escapeHtml(car.model)}</small></h2>
          <span class="sw2">${this._t("enabled")}<button class="tog ${f.enabled ? "on" : ""}" data-action="set" data-f="enabled" data-v="${!f.enabled}" role="switch" aria-checked="${f.enabled}"></button></span></div>
        ${f.enabled ? `${parts.sections(f)}<div class="slot">${preview()}</div>` : `<p class="off">${this._t(`form_${kind}_off`)}</p>`}
        <div class="err"></div>
        <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("save")}</button></div>`;
      const dialog = openDialog(body(), (action, open, target) => {
        const data = target.dataset;
        if (action === "set") f[data.f] = data.v === "true" ? true : data.v === "false" ? false : data.v;
        else if (action === "step") f[data.f] = Math.max(0, Math.min(50, (Number(f[data.f]) || 0) + Number(data.d)));
        else if (action === "use") f[data.f] = data.v;
        else if (action === "ok") {
          const message = f.enabled ? parts.check(f) : "";
          if (message) return open.error(message);
          open.close();
          return this._run(`set_${kind}`, { vehicle_id: car.id, ...(f.enabled ? parts.data(f) : { enabled: false }) }, this._t("saved"));
        } else return undefined;
        open.root.querySelector(".dlg").innerHTML = body();
        return undefined;
      });
      dialog.root.querySelector(".dlg").classList.add("mid");
      dialog.root.addEventListener("input", (event) => {
        const name = event.target.dataset && event.target.dataset.f;
        if (!name) return;
        f[name] = event.target.value;
        const slot = dialog.root.querySelector(".slot");
        if (slot) slot.innerHTML = preview();
      });
    }

    // --- Mantenimiento -------------------------------------------------------------

    _form_maintenance(car) {
      const record = car.maintenance ? car.maintenance.record : null;
      const plan = car.plan;
      const f = {
        enabled: true,
        services_done: record ? record.services_done : 0,
        last_date: record ? record.last_date : "",
        last_km: record ? record.last_km : 0,
        interval_km: record ? record.interval_km : plan.interval_km,
        interval_months: record ? record.interval_months : plan.interval_months,
      };
      f.interval = Number(f.interval_km) === plan.interval_km && Number(f.interval_months) === plan.interval_months ? "manual" : "other";
      const odometer = car.odometer == null ? null : Math.round(car.odometer);
      /** Intervalo que cuenta: el del manual o el escrito. */
      const interval = () => (f.interval === "manual"
        ? { km: plan.interval_km, months: plan.interval_months }
        : { km: Number(f.interval_km), months: Number(f.interval_months) });
      this._formWindow(car, "maintenance", "mdi:wrench", f, {
        sections: () => `
          ${this._section("mdi:history", "mt_last", "mt_last_help", `
            <div class="inline"><label class="fld"><span>${this._t("mt_services_done")}</span>
                <span class="stepper"><button data-action="step" data-f="services_done" data-d="-1" aria-label="−">−</button><b>${Number(f.services_done) || 0}</b><button data-action="step" data-f="services_done" data-d="1" aria-label="+">+</button></span></label>
              <span class="note">${this._t("mt_next_is", { number: (Number(f.services_done) || 0) + 1 })}</span></div>
            <div class="fg">${this._input(f, "last_date", "date", "date")}
              <div>${this._input(f, "last_km", "mt_km_then", "number", 'min="0" max="2000000"', "km")}
                ${odometer == null ? "" : `<button class="hint" data-action="use" data-f="last_km" data-v="${odometer}"><ha-icon icon="mdi:car-arrow-left"></ha-icon>${this._t("mt_use_odometer", { km: this._number(odometer) })}</button>`}</div></div>`)}
          ${this._section("mdi:calendar-sync", "mt_every", "mt_every_help", `
            <div class="opts">${this._choice(f, "interval", "manual", this._t("mt_interval_manual"), this._t("mt_interval_value", { km: this._number(plan.interval_km), months: plan.interval_months }))}
              ${this._choice(f, "interval", "other", this._t("other"), this._t("mt_interval_other"))}</div>
            ${f.interval !== "other" ? "" : `<div class="fg">${this._input(f, "interval_km", "mt_interval_km", "number", 'min="1000" max="100000" step="500"', "km")}
              ${this._input(f, "interval_months", "mt_interval_months", "number", 'min="1" max="60"')}</div>`}`)}`,
        preview: () => {
          const last = parseDate(f.last_date);
          const every = interval();
          if (!last || !(every.km > 0) || !(every.months > 0)) return null;
          const due = addMonths(last, every.months);
          const dueKm = (Number(f.last_km) || 0) + every.km;
          const days = daysBetween(today(), due);
          const parts = [days >= 0 ? this._days(days) : ""];
          if (odometer != null && dueKm - odometer >= 0) parts.push(`${this._number(dueKm - odometer)} km`);
          const left = parts.filter(Boolean).join(this._t("or"));
          const overdue = days < 0 || (odometer != null && dueKm - odometer < 0);
          return {
            icon: "mdi:calendar-check",
            title: this._t("mt_preview", { date: this._date(isoDate(due)), km: this._number(dueKm) }),
            detail: overdue || !left ? this._t("overdue") : this._t("left", { parts: left }),
          };
        },
        check: () => {
          const every = interval();
          if (!parseDate(f.last_date) || !(every.km >= 1000) || !(every.months >= 1)) return this._t("error_required");
          return "";
        },
        data: () => {
          const every = interval();
          return {
            enabled: true,
            services_done: Number(f.services_done) || 0,
            last_date: f.last_date,
            last_km: Math.round(Number(f.last_km) || 0),
            interval_km: Math.round(every.km),
            interval_months: Math.round(every.months),
          };
        },
      });
    }

    // --- ITV -------------------------------------------------------------------------

    /** Próxima ITV según las normas del país (igual que `documents.itv_calculated`). */
    _itvCalculated(car, registration, last) {
      const rules = car.itv_rules;
      if (!last) return addMonths(registration, rules.first_months);
      const old = last >= addMonths(registration, rules.reduced_from_months);
      return addMonths(last, old ? rules.reduced_interval_months : rules.interval_months);
    }

    _form_itv(car) {
      const record = car.itv ? car.itv.record : null;
      const f = {
        enabled: true,
        registration_date: record ? record.registration_date : "",
        passed: Boolean(record && record.last_date),
        last_date: (record && record.last_date) || "",
        next: record && record.next_override ? "manual" : "auto",
        next_date: (record && record.next_override) || "",
      };
      const calculated = () => {
        const registration = parseDate(f.registration_date);
        const last = f.passed ? parseDate(f.last_date) : null;
        if (!registration || (f.passed && !last)) return null;
        return this._itvCalculated(car, registration, last);
      };
      const first = car.alerts.thresholds.itv_t1 || 60;
      this._formWindow(car, "itv", "mdi:clipboard-check-outline", f, {
        sections: () => {
          const auto = calculated();
          return `
          ${this._section("mdi:card-account-details-outline", "itv_registration_title", "itv_registration_help",
            `<div class="fg">${this._input(f, "registration_date", "itv_registration", "date")}<div></div></div>`)}
          ${this._section("mdi:clipboard-text-clock-outline", "itv_passed_title", "itv_passed_help", `
            <div class="inline"><button class="tog ${f.passed ? "on" : ""}" data-action="set" data-f="passed" data-v="${!f.passed}" role="switch" aria-checked="${f.passed}"></button><span>${this._t("itv_passed")}</span></div>
            ${f.passed ? `<div class="fg">${this._input(f, "last_date", "itv_last", "date")}<div></div></div>` : ""}`)}
          ${this._section("mdi:calendar-edit", "itv_next_title", "itv_next_rules", `
            <div class="opts">${this._choice(f, "next", "auto", this._t("itv_next_auto"), auto ? this._date(isoDate(auto)) : "")}
              ${this._choice(f, "next", "manual", this._t("itv_next_manual"), this._t("itv_next_manual_note"))}</div>
            ${f.next === "manual" ? `<div class="fg">${this._input(f, "next_date", "itv_next", "date")}<div></div></div>` : ""}`)}`;
        },
        preview: () => {
          const due = f.next === "manual" ? parseDate(f.next_date) : calculated();
          if (!due) return null;
          const days = daysBetween(today(), due);
          return {
            icon: "mdi:calendar-check",
            title: this._t("itv_preview", { date: this._date(isoDate(due)) }),
            detail: days < 0 ? this._t("overdue_since", { days: this._days(days) }) : `${this._t("left", { parts: this._days(days) })}. ${this._t("first_notice", { days: first })}`,
          };
        },
        check: () => {
          if (!parseDate(f.registration_date)) return this._t("error_required");
          if (f.passed && !parseDate(f.last_date)) return this._t("error_required");
          if (f.next === "manual" && !parseDate(f.next_date)) return this._t("error_required");
          return "";
        },
        data: () => ({
          enabled: true,
          registration_date: f.registration_date,
          last_date: f.passed ? f.last_date : null,
          next_date: f.next === "manual" ? f.next_date : null,
        }),
      });
    }

    // --- Seguro ----------------------------------------------------------------------

    _form_insurance(car) {
      const record = car.insurance ? car.insurance.record : null;
      const days = record ? record.notice_days : 30;
      const f = {
        enabled: true,
        company: record ? record.company : "",
        policy: record ? record.policy : "",
        kind: record ? record.kind : this._state.insurance_kinds[0],
        renewal_date: record ? record.renewal_date : "",
        notice: [15, 30, 60].includes(days) ? String(days) : "other",
        notice_days: days,
        phone_assistance: record ? record.phone_assistance : "",
        phone_company: record ? record.phone_company : "",
      };
      const notice = () => (f.notice === "other" ? Math.round(Number(f.notice_days)) : Number(f.notice));
      const KIND_ICONS = { third_party: "mdi:shield-outline", third_party_plus: "mdi:shield-half-full", comprehensive_excess: "mdi:shield-check", comprehensive: "mdi:shield-star" };
      const first = car.alerts.thresholds.insurance_c1 || 30;
      this._formWindow(car, "insurance", "mdi:shield-car", f, {
        sections: () => `
          ${this._section("mdi:domain", "ins_policy_title", "ins_policy_help", `
            <div class="fg">${this._input(f, "company", "ins_company", "text")}${this._input(f, "policy", "ins_policy", "text")}</div>
            <div class="fl">${this._t("ins_kind")}</div>
            <div class="kinds">${this._state.insurance_kinds.map((kind) =>
              `<button class="kind ${f.kind === kind ? "on" : ""}" data-action="set" data-f="kind" data-v="${kind}" aria-pressed="${f.kind === kind}"><ha-icon icon="${KIND_ICONS[kind] || "mdi:shield"}"></ha-icon>${this._t(`kind_${kind}`)}</button>`).join("")}</div>`)}
          ${this._section("mdi:calendar-refresh", "ins_renewal_title", "ins_renewal_help", `
            <div class="fg">${this._input(f, "renewal_date", "ins_renews_on", "date")}
              <div><div class="fl">${this._t("ins_notice")}</div><span class="seg">${["15", "30", "60"].map((value) =>
                `<button class="${f.notice === value ? "on" : ""}" data-action="set" data-f="notice" data-v="${value}">${this._days(Number(value))}</button>`).join("")}
                <button class="${f.notice === "other" ? "on" : ""}" data-action="set" data-f="notice" data-v="other">${this._t("other")}</button></span></div></div>
            ${f.notice === "other" ? `<div class="fg">${this._input(f, "notice_days", "ins_notice_days", "number", 'min="1" max="180"', this._t("unit_days"))}<div></div></div>` : ""}`)}
          ${this._section("mdi:phone", "ins_phones_title", "ins_phones_help",
            `<div class="fg">${this._input(f, "phone_assistance", "ins_phone_assistance", "tel")}${this._input(f, "phone_company", "ins_phone_company", "tel")}</div>`)}`,
        preview: () => {
          const renewal = parseDate(f.renewal_date);
          if (!renewal || !(notice() >= 1)) return null;
          const deadline = addDays(renewal, -notice());
          const left = daysBetween(today(), deadline);
          return {
            icon: "mdi:calendar-alert",
            title: this._t("ins_preview", { date: this._date(isoDate(deadline)) }),
            detail: left < 0 ? this._t("ins_preview_passed", { date: this._date(f.renewal_date) }) : `${this._t("left", { parts: this._days(left) })}. ${this._t("first_notice", { days: first })}`,
          };
        },
        check: () => (parseDate(f.renewal_date) && notice() >= 1 && notice() <= 180 ? "" : this._t("error_required")),
        data: () => ({
          enabled: true,
          renewal_date: f.renewal_date,
          company: f.company,
          policy: f.policy,
          kind: f.kind,
          notice_days: notice(),
          phone_assistance: f.phone_assistance,
          phone_company: f.phone_company,
        }),
      });
    }
  });

  // ── src/65_apariencia.js ──────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Ventana "Apariencia" de un coche: modelo, versión, color y llanta
  // ---------------------------------------------------------------------------
  // Se abre con el botón "Apariencia" de la pestaña Coches. La foto de arriba
  // cambia con lo que se va eligiendo (son las fotos del catálogo); nada se
  // guarda hasta pulsar "Guardar".
  install(class {
    _do_appearance(data) {
      const car = this._car(data.car);
      const models = this._state.models;
      if (!models.length) return;
      const pick = { ...car.appearance };
      if (!models.some((model) => model.id === pick.model)) pick.model = models[0].id;

      /** Lo elegido, sin lo que el modelo no tiene (al cambiar de modelo, por ejemplo). */
      const current = () => {
        const model = models.find((item) => item.id === pick.model);
        if (!model.trims.some((trim) => trim.id === pick.trim)) pick.trim = null;
        if (!model.colors.some((color) => color.id === pick.color)) pick.color = null;
        const trim = model.trims.find((item) => item.id === pick.trim);
        // La llanta solo se elige si el modelo tiene varias y la versión no trae una fija.
        const choosable = model.wheels.length > 1 && !(trim && trim.wheel);
        if (!model.wheels.includes(pick.wheels)) pick.wheels = model.wheels[0] || null;
        return { model, trim, choosable };
      };

      const option = (field, value, name, note, on) =>
        `<button class="opt ${on ? "on" : ""}" data-action="pick" data-field="${field}" data-value="${escapeHtml(value)}" aria-pressed="${on}">${escapeHtml(name)}${note ? `<small>${escapeHtml(note)}</small>` : ""}</button>`;
      const trimNote = (trim) => {
        const parts = [];
        if (trim.equipped === 4) parts.push(this._t("trim_full"));
        if (trim.equipped === 0) parts.push(this._t("trim_basic"));
        if (trim.wheel) parts.push(this._maybe(`wheel_${trim.wheel}`) || trim.wheel);
        return parts.join(" · ");
      };
      const body = () => {
        const { model, choosable } = current();
        const photo = model.photos[`${pick.trim || ""}|${pick.color || ""}`] || model.photos["|"];
        return `<h2>${this._t("appearance_title", { name: escapeHtml(car.name) })}</h2><p>${this._t("appearance_help")}</p>
          ${photo ? `<div class="prev"><img src="${escapeHtml(photo)}" alt=""></div>` : ""}
          ${models.length > 1 ? `<div class="lbl">${this._t("model")}</div><div class="opts">${models.map((item) =>
            option("model", item.id, item.name, this._t(item.fuel ? "model_phev" : "model_ev"), item.id === pick.model)).join("")}</div>` : ""}
          ${model.trims.length ? `<div class="lbl">${this._t("trim")}</div><div class="opts">${model.trims.map((trim) =>
            option("trim", trim.id, trim.name, trimNote(trim), trim.id === pick.trim)).join("")}</div>` : ""}
          ${model.colors.length ? `<div class="lbl">${this._t("color")}</div><div class="sw">${model.colors.map((color) =>
            `<button class="${color.id === pick.color ? "on" : ""}" data-action="pick" data-field="color" data-value="${escapeHtml(color.id)}" aria-pressed="${color.id === pick.color}">
              <i style="background:${escapeHtml(color.swatch || "#9e9e9e")}"></i>${escapeHtml(color.name)}</button>`).join("")}</div>` : ""}
          ${choosable ? `<div class="lbl">${this._t("wheels")}</div><div class="opts">${model.wheels.map((wheel) =>
            option("wheels", wheel, this._maybe(`wheel_${wheel}`) || wheel, "", wheel === pick.wheels)).join("")}</div>` : ""}
          <div class="err"></div>
          <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("save")}</button></div>`;
      };

      const dialog = openDialog(body(), (action, open, target) => {
        if (action === "pick") {
          pick[target.dataset.field] = target.dataset.value;
          open.root.querySelector(".dlg").innerHTML = body();
          return undefined;
        }
        if (action !== "ok") return undefined;
        const { choosable } = current();
        open.close();
        return this._run(
          "set_appearance",
          { vehicle_id: car.id, model: pick.model, trim: pick.trim, color: pick.color, wheels: choosable ? pick.wheels : null },
          this._t("saved")
        );
      });
      dialog.root.querySelector(".dlg").classList.add("wide");
    }
  });

  // ── src/66_ajustes.js ─────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Pestaña "Ajustes": control con PIN y lectura de datos (de la cuenta)
  // ---------------------------------------------------------------------------
  // El PIN es de la cuenta de Deepal, no de un coche: vale para todos. El panel
  // nunca recibe el PIN guardado (solo si lo hay): el campo vacío = no cambiarlo.
  // Lo que se toca queda en un borrador (this._settings) hasta pulsar "Guardar".
  install(class {
    _view_settings() {
      const accounts = this._state.accounts;
      return accounts.map((account) => this._settingsCard(account, accounts.length > 1)).join("");
    }

    /** Ajustes de una cuenta tal como se ven ahora: el borrador o lo guardado. */
    _settingsOf(account) {
      return (this._settings && this._settings[account.entry_id]) || { ...account, pin: "", manual_url: account.manual ? account.manual.url : "" };
    }

    _settingsDraft(entryId) {
      const account = this._state.accounts.find((item) => item.entry_id === entryId);
      this._settings = this._settings || {};
      if (!this._settings[entryId]) this._settings[entryId] = this._settingsOf(account);
      return this._settings[entryId];
    }

    _settingsCard(account, several) {
      const now = this._settingsOf(account);
      const entry = escapeHtml(account.entry_id);
      const set = (field, value) => `data-action="setting" data-entry="${entry}" data-field="${field}" data-value="${value}"`;
      const toggle = (field) => `<button class="tog ${now[field] ? "on" : ""}" ${set(field, !now[field])} role="switch" aria-checked="${Boolean(now[field])}"></button>`;
      const row = (icon, title, help, control, grey) => `<div class="row"><div class="ic ${grey ? "grey" : ""}"><ha-icon icon="${icon}"></ha-icon></div>
        <div class="tx">${this._t(title)}<small>${this._t(help)}</small></div>${control}</div>`;
      const segment = (field, values, unit) => `<span class="seg">${values.map((value) =>
        `<button class="${Number(now[field]) === value ? "on" : ""}" ${set(field, value)}>${this._t(unit, { value })}</button>`).join("")}</span>`;
      const mode = (value, icon, extra) => `<button class="mode ${now.pin_mode === value ? "on" : ""}" ${set("pin_mode", value)} aria-pressed="${now.pin_mode === value}">
        <b><ha-icon icon="${icon}"></ha-icon>${this._t(`mode_${value}`)}</b><p>${this._t(`mode_${value}_help`)}</p></button>${extra || ""}`;
      const scan = [...new Set([2, 5, 10, 15, 30, Number(now.scan_minutes)])].sort((a, b) => a - b);
      const dirty = Boolean(this._settings && this._settings[account.entry_id]);

      const pin = !now.pin_enabled ? "" : `
        ${row("mdi:form-textbox-password", "pin", "pin_field_help",
          `<span class="pinbox"><input type="password" inputmode="numeric" autocomplete="off" data-input="pin" data-entry="${entry}" value="${escapeHtml(now.pin)}"
              placeholder="${account.pin_set ? "••••" : ""}" aria-label="${this._t("pin")}">
            <button data-action="reveal" aria-label="${this._t("show_pin")}"><ha-icon icon="mdi:eye-outline"></ha-icon></button></span>
           ${account.pin_set && !now.pin ? `<span class="badge ok"><ha-icon icon="mdi:check-circle"></ha-icon>${this._t("pin_checked")}</span>` : ""}`)}
        <div class="lbl">${this._t("pin_mode_title")}</div>
        <div class="modes">
          ${mode("direct", "mdi:flash")}
          ${mode("armed", "mdi:lock-clock")}
        </div>
        ${now.pin_mode !== "armed" ? "" : `
          ${row("mdi:timer-sand", "arm_seconds", "arm_seconds_help", segment("arm_seconds", account.arm_choices, "seconds"))}
          ${row("mdi:bell-outline", "arm_notify", "arm_notify_help", toggle("arm_notify"), true)}`}`;

      const manual = !account.manual ? "" : row("mdi:book-open-variant", `manual_${account.manual.kind}`, "manual_help",
        `<input class="url" type="url" data-input="manual_url" data-entry="${entry}" value="${escapeHtml(now.manual_url)}" placeholder="${escapeHtml(account.manual.official)}">`);

      return `${several ? `<div class="acct">${this._t("account", { name: escapeHtml(account.title) })}</div>` : ""}
        <div class="card" data-account="${entry}">
          <h2>${this._t("pin_title")}</h2><div class="sub">${this._t("pin_help")}</div>
          ${row("mdi:shield-key", "pin_enabled", "pin_enabled_help", toggle("pin_enabled"))}
          ${pin}
          <h2 class="next">${this._t("reading_title")}</h2><div class="sub">${this._t("reading_help")}</div>
          ${row("mdi:timer-outline", "scan_title", "scan_help", segment("scan_minutes", scan, "minutes"))}
          ${row("mdi:sleep-off", "wake_title", "wake_help", toggle("wake"))}
          ${manual}
          ${row("mdi:bug-outline", "debug_title", "debug_help", toggle("debug"), true)}
          <div class="foot ${dirty ? "dirty" : ""}">
            <span>${dirty ? this._t("unsaved_settings") : ""}</span>
            ${dirty ? `<button class="btn o" data-action="discard-settings" data-entry="${entry}">${this._t("discard")}</button>` : ""}
            <button class="btn" data-action="save-settings" data-entry="${entry}">${this._t("save_check")}</button>
          </div>
        </div>`;
    }

    _do_setting(data) {
      const draft = this._settingsDraft(data.entry);
      const value = data.value;
      draft[data.field] = value === "true" ? true : value === "false" ? false : /^\d+$/.test(value) ? Number(value) : value;
      this._render();
    }

    /** Lo que se escribe (PIN, enlace) se apunta sin repintar, para no perder el cursor. */
    _input_setting(target) {
      this._settingsDraft(target.dataset.entry)[target.dataset.input] = target.value;
    }

    _do_reveal(_data, target) {
      const input = target.parentNode.querySelector("input");
      input.type = input.type === "password" ? "text" : "password";
    }

    _do_discard_settings(data) {
      delete this._settings[data.entry];
      this._render();
    }

    async _do_save_settings(data) {
      const account = this._state.accounts.find((item) => item.entry_id === data.entry);
      const now = this._settingsOf(account);
      const message = {
        entry_id: account.entry_id,
        pin_enabled: Boolean(now.pin_enabled),
        pin: String(now.pin || ""),
        pin_mode: now.pin_mode,
        arm_seconds: Number(now.arm_seconds),
        arm_notify: Boolean(now.arm_notify),
        scan_minutes: Number(now.scan_minutes),
        wake: Boolean(now.wake),
        debug: Boolean(now.debug),
      };
      if (account.manual) message.manual_url = String(now.manual_url || "");
      if (await this._run("set_settings", message, this._t("saved"))) {
        if (this._settings) delete this._settings[data.entry];
        this._render();
      }
    }
  });

  // ── src/67_fichas.js ──────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Fichas de "Coches": la ventana que se abre al pulsar un recuadro
  // ---------------------------------------------------------------------------
  // Pulsar el recuadro (no su engranaje) enseña la información: qué toca en
  // la revisión, las fechas de la ITV, los datos del seguro. El engranaje de
  // dentro lleva al formulario. Sin configurar, se abre el formulario directamente.
  install(class {
    _do_info(data) {
      const car = this._car(data.car);
      if (!car[data.kind]) return this._do_gear(data);
      return this[`_info_${data.kind}`](car);
    }

    /**
     * Ventana de ficha: cabecera, cuerpo y pie con el engranaje.
     * `actions(action, dialog)` atiende los botones propios de la ficha.
     */
    _infoWindow(car, kind, icon, body, buttons, actions) {
      const dialog = openDialog(
        `<div class="thead"><div class="ic"><ha-icon icon="${icon}"></ha-icon></div>
           <h2>${this._t(`section_${kind}`)}<small>${escapeHtml(car.name)} · ${escapeHtml(car.model)}</small></h2>
           <button class="x" data-action="close" aria-label="${this._t("close")}"><ha-icon icon="mdi:close"></ha-icon></button></div>
         ${body}
         <div class="ifoot"><button class="gearb" data-action="configure" aria-label="${this._t("configure")}"><ha-icon icon="mdi:cog"></ha-icon></button><span></span>${buttons || ""}
           <button class="tb" data-action="close">${this._t("close")}</button></div>`,
        (action, open, target) => {
          if (action === "configure") {
            open.close();
            return this._do_gear({ car: car.id, kind });
          }
          return actions ? actions(action, open, target) : undefined;
        }
      );
      dialog.root.querySelector(".dlg").classList.add("mid");
      return dialog;
    }

    _stat(icon, label, value, detail, fraction) {
      return `<div class="stat"><div class="k"><ha-icon icon="${icon}"></ha-icon>${this._t(label)}</div><div class="n">${escapeHtml(value)}</div><div class="d">${escapeHtml(detail)}</div>
        ${fraction == null ? "" : `<div class="meter"><i style="width:${Math.round(Math.max(0, Math.min(1, fraction)) * 100)}%"></i></div>`}</div>`;
    }

    /** "Inspección general (propulsión, frenos)" → título y, debajo, lo del paréntesis. */
    _operation(name) {
      const match = /^(.*?)\s*\((.*)\)\s*$/.exec(name);
      const title = match ? match[1] : name;
      const note = match ? match[2].charAt(0).toUpperCase() + match[2].slice(1) : "";
      return `<li><ha-icon icon="mdi:check-circle-outline"></ha-icon><div>${escapeHtml(title)}${note ? `<small>${escapeHtml(note)}</small>` : ""}</div></li>`;
    }

    // --- Mantenimiento -------------------------------------------------------------

    _info_maintenance(car) {
      const data = car.maintenance;
      const record = data.record;
      const odometer = car.odometer == null ? null : Math.round(car.odometer);
      const overdueDays = data.days_left < 0;
      const overdueKm = data.km_left != null && data.km_left < 0;
      const history = (record.history || []).slice().reverse();
      const body = `
        <div class="big">${this._t("service_number", { number: data.number })}</div>
        <div class="bigsub">${this._t("mt_whichever", { date: this._date(data.due_date), km: this._number(data.due_km) })}</div>
        <div class="dual">
          ${this._stat("mdi:calendar", "by_time", overdueDays ? this._t("overdue") : this._days(data.days_left), this._date(data.due_date),
            1 - data.days_left / (record.interval_months * 30.4))}
          ${data.km_left == null ? "" : this._stat("mdi:counter", "by_km", overdueKm ? this._t("overdue") : `${this._number(data.km_left)} km`,
            this._t("mt_km_detail", { now: this._number(odometer == null ? 0 : odometer), due: this._number(data.due_km) }), 1 - data.km_left / record.interval_km)}
        </div>
        <div class="h3">${this._t("mt_this_service")}${data.operations.length ? `<span>· ${this._t("n_operations", { count: data.operations.length })}</span>` : ""}</div>
        ${data.operations.length ? `<ul class="ops">${data.operations.map((name) => this._operation(name)).join("")}</ul>` : `<div class="hist">${this._t("mt_no_plan")}</div>`}
        ${data.next_extra && data.next_extra.length ? `<div class="h3">${this._t("mt_next_adds", { number: data.number + 1 })}</div>
          <div>${data.next_extra.map((name) => `<span class="chip">${escapeHtml(name.replace(/\s*\(.*\)\s*$/, ""))}</span>`).join("")}</div>` : ""}
        <div class="h3">${this._t("history")}</div>
        ${history.length ? history.map((item) => `<div class="hist"><ha-icon icon="mdi:check"></ha-icon>${this._t("mt_history_item", {
            number: item.number, date: this._date(item.date), km: this._number(item.km) })}</div>`).join("")
          : `<div class="hist"><ha-icon icon="mdi:history"></ha-icon>${this._t("mt_no_history")}</div>`}`;
      const buttons = `${car.manual_url ? `<a class="tb" href="${escapeHtml(car.manual_url)}" target="_blank" rel="noopener noreferrer">${this._t("manual")}</a>` : ""}
        <button class="tb fill" data-action="register">${this._t("mt_register")}</button>`;
      this._infoWindow(car, "maintenance", "mdi:wrench", body, buttons, (action, open) => {
        if (action !== "register") return;
        open.close();
        this._register_maintenance(car);
      });
    }

    /** Registrar una revisión hecha: fecha y kilómetros (por defecto, hoy y los del coche). */
    _register_maintenance(car) {
      openDialog(
        `<h2>${this._t("mt_register")}</h2><p>${this._t("mt_register_help", { name: escapeHtml(car.name), number: car.maintenance.number })}</p>
         <div class="two"><label>${this._t("date")}<input name="date" type="date" value="${isoDate(today())}"></label>
           <label>${this._t("mt_km")}<input name="km" type="number" min="0" max="2000000" value="${Math.round(car.odometer || 0)}"></label></div>
         <div class="err"></div>
         <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("register")}</button></div>`,
        (action, dialog) => {
          if (action !== "ok") return undefined;
          const values = dialog.values();
          if (!parseDate(values.date)) return dialog.error(this._t("error_required"));
          dialog.close();
          return this._run("register_maintenance", { vehicle_id: car.id, date: values.date, km: Number(values.km) || 0 }, this._t("registered"));
        }
      );
    }

    // --- ITV -------------------------------------------------------------------------

    _info_itv(car) {
      const data = car.itv;
      const record = data.record;
      const overdue = data.days_left < 0;
      const history = (record.history || []).slice().reverse();
      const rules = car.itv_rules;
      // Edad del coche: solo se dice cuando ya son años en plural.
      const years = Math.floor(daysBetween(parseDate(record.registration_date), today()) / 365.25);
      const body = `
        <div class="big">${this._date(data.due_date)}</div>
        <div class="bigsub">${overdue ? this._t("overdue_since", { days: this._days(data.days_left) }) : this._t("left", { parts: this._days(data.days_left) })}${
          record.next_override ? ` · ${this._t("itv_manual_date")}` : ""}</div>
        <div class="dual">
          ${this._stat("mdi:card-account-details-outline", "itv_registration", this._date(record.registration_date), years >= 2 ? this._t("itv_age", { years }) : "")}
          ${this._stat("mdi:clipboard-check-outline", "itv_last", record.last_date ? this._date(record.last_date) : this._t("itv_none_yet"),
            record.last_date ? "" : this._t("itv_first_at", { years: Math.round(rules.first_months / 12) }))}
        </div>
        <div class="h3">${this._t("itv_rules_title")}</div>
        <div class="hist"><ha-icon icon="mdi:information-outline"></ha-icon>${this._t("itv_rules", {
          first: Math.round(rules.first_months / 12), interval: Math.round(rules.interval_months / 12), reduced: Math.round(rules.reduced_from_months / 12) })}</div>
        <div class="h3">${this._t("history")}</div>
        ${history.length ? history.map((date) => `<div class="hist"><ha-icon icon="mdi:check"></ha-icon>${this._t("itv_history_item", { date: this._date(date) })}</div>`).join("")
          : `<div class="hist"><ha-icon icon="mdi:history"></ha-icon>${this._t("itv_no_history")}</div>`}`;
      this._infoWindow(car, "itv", "mdi:clipboard-check-outline", body,
        `<button class="tb fill" data-action="register">${this._t("itv_register")}</button>`, (action, open) => {
          if (action !== "register") return;
          open.close();
          this._register_itv(car);
        });
    }

    _register_itv(car) {
      openDialog(
        `<h2>${this._t("itv_register")}</h2><p>${this._t("itv_register_help", { name: escapeHtml(car.name) })}</p>
         <label>${this._t("date")}<input name="date" type="date" value="${isoDate(today())}"></label>
         <div class="err"></div>
         <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("register")}</button></div>`,
        (action, dialog) => {
          if (action !== "ok") return undefined;
          const values = dialog.values();
          if (!parseDate(values.date)) return dialog.error(this._t("error_required"));
          dialog.close();
          return this._run("register_itv", { vehicle_id: car.id, date: values.date }, this._t("registered"));
        }
      );
    }

    // --- Seguro ----------------------------------------------------------------------

    _info_insurance(car) {
      const data = car.insurance;
      const record = data.record;
      // Línea del año: de la renovación anterior a la próxima.
      const at = (days) => Math.max(0, Math.min(100, (1 - days / 365) * 100));
      const now = at(data.days_to_renewal);
      const deadline = at(record.notice_days);
      const first = car.alerts.thresholds.insurance_c1 || 30;
      const amber = at(record.notice_days + first);
      const passed = data.days_to_cancel < 0;
      const call = (number, icon, label) => !number ? "" :
        `<a class="callb" data-action="call" data-number="${escapeHtml(number)}" target="_blank" rel="noopener noreferrer" href="tel:${escapeHtml(String(number).replace(/[^0-9+]/g, ""))}">
           <ha-icon icon="${icon}"></ha-icon><span><b>${this._t(label)}</b><small>${escapeHtml(number)}</small></span></a>`;
      const calls = call(record.phone_assistance, "mdi:tow-truck", "ins_assistance") + call(record.phone_company, "mdi:phone", "ins_company");
      const body = `
        <div class="big">${escapeHtml(record.company || this._t("section_insurance"))}</div>
        <div class="bigsub"><span class="badge info">${this._t(`kind_${record.kind}`)}</span></div>
        ${record.policy ? `<div class="pol"><span>${this._t("ins_policy")}</span><b>${escapeHtml(record.policy)}</b>
          <button class="x" data-action="copy" data-text="${escapeHtml(record.policy)}" aria-label="${this._t("copy")}"><ha-icon icon="mdi:content-copy"></ha-icon></button></div>` : ""}
        <div class="h3">${this._t("ins_dates")}</div>
        <div class="line"><div class="track"></div><div class="fill" style="width:${now}%"></div>
          <div class="amber" style="left:${amber}%;width:${Math.max(0, deadline - amber)}%"></div>
          <div class="pt now" style="left:${now}%"></div><div class="pt" style="left:${deadline}%"></div><div class="pt" style="left:100%"></div></div>
        <div class="dual">
          ${this._stat("mdi:calendar-alert", "ins_to_cancel", passed ? this._t("ins_deadline_passed") : this._days(data.days_to_cancel),
            this._t("ins_deadline_on", { date: this._date(data.cancel_deadline) }))}
          ${this._stat("mdi:autorenew", "ins_to_renewal", this._days(data.days_to_renewal), this._t("ins_renews_itself", { date: this._date(record.renewal_date) }))}
        </div>
        ${calls ? `<div class="h3">${this._t("ins_phones_title")}</div><div class="calls">${calls}</div>` : ""}`;
      this._infoWindow(car, "insurance", "mdi:shield-car", body, "", (action, _open, target) => {
        // El enlace "tel:" abre el marcador por su cuenta; aquí solo se copia.
        const text = action === "call" ? target.dataset.number : action === "copy" ? target.dataset.text : "";
        if (text && navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(() => this._toast(this._t("copied", { text })), () => undefined);
        }
      });
    }
  });

  // ── src/90_registro.js ────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Alta del panel en Home Assistant
  // ---------------------------------------------------------------------------
  customElements.define(TAG, DecDeepalPanel);
})();
