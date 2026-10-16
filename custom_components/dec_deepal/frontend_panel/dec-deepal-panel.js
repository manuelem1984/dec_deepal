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
// Por WebSocket, con órdenes "dec_deepal/panel/..." (ver panel/). Al abrir
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
  const BORROWED_LANGUAGES = {"ca": "es", "eu": "es", "gl": "es", "lb": "fr", "nn": "nb"};
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
      "section_people": "Personas",
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
      "mode_armed_help": "Hay que activar primero «Desbloqueo acciones con PIN» y solo vale durante un rato. Lo más seguro.",
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
      "ins_assistance": "Asistencia",
      "read_only": "Solo lectura: los cambios los hace un administrador de Home Assistant.",
      "people": "Personas",
      "people_none": "Sin asignar",
      "people_edit": "Elegir",
      "people_title": "Personas de {name}",
      "people_help": "Elige a quién pertenece este coche. Son las personas de Ajustes → Personas.",
      "mine": "Tuyo",
      "error_unknown_person": "Esa persona ya no existe en Home Assistant.",
      "error_unauthorized": "Solo un administrador puede hacer este cambio.",
      "plate": "Matrícula"
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
      "section_people": "People",
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
      "ins_notice": "Notice days to cancel",
      "ins_phone_assistance": "Assistance phone",
      "ins_phone_company": "Company phone",
      "kind_third_party": "Third party",
      "kind_third_party_plus": "Third party, fire and theft",
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
      "ins_assistance": "Assistance",
      "read_only": "Read only: changes are made by a Home Assistant administrator.",
      "people": "People",
      "people_none": "Not assigned",
      "people_edit": "Choose",
      "people_title": "People of {name}",
      "people_help": "Choose who this car belongs to. These are the people in Settings → People.",
      "mine": "Yours",
      "error_unknown_person": "That person no longer exists in Home Assistant.",
      "error_unauthorized": "Only an administrator can make this change.",
      "plate": "Number plate"
    },
    "pt": {
      "tab_cars": "Veículos",
      "tab_alerts": "Avisos",
      "tab_data": "Dados",
      "tab_diagnostics": "Diagnóstico",
      "loading": "A carregar…",
      "retry": "Tentar de novo",
      "no_cars": "Não há veículos. Adicione a sua conta Deepal em Definições → Dispositivos e serviços.",
      "error_generic": "Não foi possível concluir. Tente de novo.",
      "day": "{value} dia",
      "days": "{value} dias",
      "or": " ou ",
      "not_configured": "Sem modelo escolhido",
      "sheet_verified": "Ficha verificada",
      "sheet_catalogue": "Ficha de catálogo",
      "battery": "Bateria",
      "range": "Autonomia",
      "odometer": "Quilometragem",
      "appearance": "Aparência",
      "configure": "Configurar",
      "section_charge": "Carregamento",
      "section_warnings": "Avisos do painel",
      "section_maintenance": "Manutenção",
      "section_itv": "ITV",
      "section_insurance": "Seguro",
      "section_appearance": "Aparência",
      "section_people": "Pessoas",
      "not_set": "Por configurar",
      "add_maintenance": "Ativar a manutenção",
      "add_itv": "Adicionar a ITV",
      "add_insurance": "Adicionar o seguro",
      "feature_seat_heat": "Bancos aquecidos",
      "feature_seat_vent": "Bancos ventilados",
      "feature_wheel_heat": "Volante aquecido",
      "feature_power_tailgate": "Porta da mala elétrica",
      "wheel_pro": "Jantes de 18\"",
      "wheel_cover": "Jantes de 20\" com tampões aerodinâmicos",
      "wheel_open": "Jantes de 20\" sem tampões",
      "service_number": "{number}.ª revisão",
      "overdue": "Em atraso",
      "left": "Faltam {parts}",
      "overdue_since": "Em atraso há {days}",
      "cancel_until": "Limite para cancelar: {date}",
      "renews_in": "Renova dentro de {days}",
      "notify_to": "Avisar",
      "n_notices": "{count} avisos",
      "edit_threshold": "Alterar a antecedência",
      "accept": "Aceitar",
      "cancel": "Cancelar",
      "unit_km": "km",
      "unit_days": "dias",
      "when_km": "quando faltarem {value} km",
      "when_days": "quando faltarem {value} dias",
      "when_days_deadline": "{value} dias antes do limite",
      "when_maintenance_overdue": "no próprio dia ou ao atingir os km",
      "when_itv_overdue": "no próprio dia",
      "when_insurance_last_day": "último dia para cancelar",
      "when_insurance_renewed": "no próprio dia",
      "notice_charge_started": "Carregamento iniciado",
      "notice_charge_interrupted": "Carregamento interrompido",
      "notice_charge_finished": "Carregamento concluído",
      "notice_warnings": "Luzes de aviso",
      "notice_tires": "Pneus",
      "notice_key_battery": "Pilha da chave fraca",
      "notice_maintenance_t1": "Aviso por tempo 1",
      "notice_maintenance_t2": "Aviso por tempo 2",
      "notice_maintenance_t3": "Aviso por tempo 3",
      "notice_maintenance_k1": "Aviso por quilómetros 1",
      "notice_maintenance_k2": "Aviso por quilómetros 2",
      "notice_maintenance_k3": "Aviso por quilómetros 3",
      "notice_maintenance_overdue": "Revisão vencida",
      "notice_itv_t1": "Aviso 1",
      "notice_itv_t2": "Aviso 2",
      "notice_itv_t3": "Aviso 3",
      "notice_itv_overdue": "ITV vencida",
      "notice_insurance_c1": "Aviso de cancelamento 1",
      "notice_insurance_c2": "Aviso de cancelamento 2",
      "notice_insurance_last_day": "Limite para cancelar",
      "notice_insurance_r1": "Aviso de renovação 1",
      "notice_insurance_r2": "Aviso de renovação 2",
      "notice_insurance_renewed": "Seguro renovado",
      "unsaved": "Este veículo tem alterações por guardar.",
      "alerts_help": "Marque quem recebe cada aviso. O lápis altera os dias ou os quilómetros desse aviso; as antecedências são deste veículo.",
      "factory_thresholds": "Antecedências de origem",
      "discard": "Descartar",
      "save": "Guardar",
      "saved": "Guardado",
      "copy_from": "Copiar de outro veículo",
      "car": "Veículo",
      "copy": "Copiar",
      "error_threshold_range_limits": "A antecedência tem de estar entre {low} e {high}.",
      "error_threshold_range": "Uma antecedência está fora dos limites.",
      "error_threshold_order": "As antecedências têm de ir da maior para a menor: o aviso 1 antes do 2, e o 2 antes do 3.",
      "error_not_found": "Esse veículo já não está na conta.",
      "error_invalid": "Alguns dados não são válidos.",
      "error_invalid_file": "O ficheiro não é uma cópia do DEC Deepal ou está danificado.",
      "error_newer_file": "A cópia vem de uma versão mais recente da integração. Atualize o DEC Deepal e tente de novo.",
      "error_empty_file": "A cópia não tem dados de nenhum veículo.",
      "error_required": "Faltam dados por preencher.",
      "backup_title": "Cópia de segurança",
      "backup_help": "Manutenção, ITV, seguro e aparência dos seus veículos. Os dados são do veículo: não se perdem ao remover a conta.",
      "download_title": "Descarregar uma cópia",
      "download_help": "Um ficheiro com os dados de todos os veículos. Contém o número da apólice e os telefones do seguro: guarde-o em local seguro.",
      "download": "Descarregar",
      "send_title": "Enviar a cópia para um telemóvel",
      "send_help": "Chega uma notificação; ao tocar nela, abre o navegador e descarrega o ficheiro. A ligação expira em 10 minutos.",
      "send": "Enviar",
      "sent_to": "Notificação enviada para {device}.",
      "upload_title": "Carregar uma cópia",
      "upload_help": "Repõe os veículos do ficheiro tal como estavam nele. Os outros veículos não são alterados.",
      "choose_file": "Escolher ficheiro",
      "imported": "Cópia carregada: {cars}.",
      "stored_title": "Dados guardados",
      "stored_help": "Por veículo, identificado pelo seu VIN.",
      "stored_none": "Não há dados guardados de nenhum veículo.",
      "in_account": "Na conta",
      "no_account": "Sem conta",
      "no_account_note": "Já não está em nenhuma conta",
      "delete": "Apagar",
      "delete_title": "Apagar dados guardados",
      "delete_confirm": "A manutenção, a ITV e o seguro de {name} serão apagados. Não é possível desfazer: descarregue primeiro uma cópia se quiser conservá-los.",
      "deleted": "Dados apagados.",
      "history_title": "O que aconteceu",
      "history_help": "Alterações, comandos e avisos desde o último reinício. O mesmo vai para o ficheiro de diagnóstico.",
      "history_none": "Ainda não há nada para mostrar.",
      "filter_all": "Tudo",
      "filter_orders": "Comandos",
      "filter_alerts": "Avisos",
      "filter_errors": "Erros",
      "sheets_title": "Ficha de cada veículo",
      "sheets_help": "Que equipamento a integração assume e de onde o tira.",
      "diagnostics_file": "Diagnóstico",
      "ev_alert": "Aviso enviado: {name}",
      "ev_targets": "{count} destinatários",
      "ev_wake": "Despertar do veículo",
      "ev_command": "Comando: {name}",
      "ev_code": "código",
      "today": "Hoje",
      "yesterday": "Ontem",
      "enabled": "Ativado",
      "mt_services_done": "Revisões já feitas",
      "mt_interval_km": "Intervalo (km)",
      "mt_interval_months": "Intervalo (meses)",
      "mt_register": "Registar revisão feita",
      "mt_register_help": "Regista a {number}.ª revisão de {name} e começa a contar para a seguinte.",
      "date": "Data",
      "mt_km": "Quilómetros",
      "register": "Registar",
      "registered": "Registado",
      "itv_registration": "Data de matrícula",
      "itv_last": "Última ITV feita",
      "itv_next": "Próxima ITV (manual)",
      "itv_register": "Registar ITV feita",
      "itv_register_help": "Regista que {name} passou na ITV e calcula a seguinte.",
      "ins_company": "Seguradora",
      "ins_policy": "N.º da apólice",
      "ins_kind": "Tipo de seguro",
      "ins_notice": "Dias de pré-aviso para cancelar",
      "ins_phone_assistance": "Telefone de assistência",
      "ins_phone_company": "Telefone da seguradora",
      "kind_third_party": "Terceiros",
      "kind_third_party_plus": "Terceiros alargado",
      "kind_comprehensive_excess": "Danos próprios com franquia",
      "kind_comprehensive": "Danos próprios sem franquia",
      "tab_settings": "Definições",
      "appearance_title": "Aparência de {name}",
      "appearance_help": "Decide a fotografia, a vista do veículo e que equipamento se assume.",
      "model": "Modelo",
      "trim": "Versão",
      "color": "Cor",
      "wheels": "Jantes",
      "model_ev": "Elétrico",
      "model_phev": "Híbrido plug-in",
      "trim_full": "Bancos e volante aquecidos, porta da mala elétrica",
      "trim_basic": "Sem bancos nem volante aquecidos",
      "account": "Conta: {name}",
      "pin_title": "Controlo remoto com PIN",
      "pin_help": "Para trancar e destrancar, vidros e mala. É o PIN da aplicação oficial Deepal, com a mesma conta. Vale para todos os veículos da conta.",
      "pin_enabled": "Comandos com PIN",
      "pin_enabled_help": "Sem isto, o cartão só mostra o estado das portas, dos vidros e da mala.",
      "pin": "PIN",
      "pin_field_help": "É verificado junto da Deepal ao guardar. Deixe vazio para manter o atual.",
      "pin_checked": "Verificado",
      "show_pin": "Mostrar o PIN",
      "pin_mode_title": "Como se usam os comandos",
      "mode_direct": "Direto",
      "mode_direct_help": "O comando é enviado ao tocar, depois de confirmar. O mais cómodo.",
      "mode_armed": "Desbloquear primeiro",
      "mode_armed_help": "É preciso ativar primeiro «Desbloqueio de ações com PIN», e dura só algum tempo. O mais seguro.",
      "arm_seconds": "Quanto dura o desbloqueio",
      "arm_seconds_help": "Passado esse tempo, os comandos com PIN voltam a bloquear-se sozinhos.",
      "seconds": "{value} s",
      "arm_notify": "Avisar ao desbloquear",
      "arm_notify_help": "Uma notificação no Home Assistant sempre que os comandos são permitidos.",
      "reading_title": "Leitura de dados",
      "reading_help": "Como e com que frequência se consulta o veículo.",
      "scan_title": "Intervalo de leitura",
      "scan_help": "Com que frequência se leem os dados do veículo. Valores muito baixos podem levar a Deepal a limitar a conta.",
      "minutes": "{value} min",
      "wake_title": "Despertar o veículo quando for preciso",
      "wake_help": "Ao tocar em Atualizar e antes de um comando com PIN. Nunca nas leituras automáticas, para proteger a bateria de 12 V.",
      "manual_bev": "Manual BEV",
      "manual_phev": "Manual PHEV",
      "manual_help": "A ligação que o cartão abre em Outros → Manual. Vazio para usar o oficial.",
      "debug_title": "Modo de depuração",
      "debug_help": "Guarda pedidos e respostas completos (sem dados pessoais) no diagnóstico.",
      "save_check": "Guardar",
      "unsaved_settings": "Há alterações por guardar.",
      "error_pin_required": "Introduza o PIN.",
      "error_pin_invalid": "O PIN não está correto. É o da aplicação oficial Deepal, com esta mesma conta.",
      "error_pin_rate_limited": "Demasiadas tentativas de PIN. Aguarde uns minutos antes de tentar de novo.",
      "error_cannot_connect": "Não foi possível ligar à Deepal. Tente mais tarde.",
      "error_invalid_url": "A ligação do manual não é válida: tem de começar por http:// ou https://.",
      "error_unknown_model": "Esse modelo não está no catálogo.",
      "close": "Fechar",
      "other": "Outro",
      "history": "Histórico",
      "manual": "Manual",
      "copied": "Copiado: {text}",
      "form_maintenance": "Configurar a manutenção",
      "form_itv": "Configurar a ITV",
      "form_insurance": "Configurar o seguro",
      "form_maintenance_off": "Desativada: são removidas as suas entidades, o seu indicador no cartão e os seus avisos. O histórico perde-se.",
      "form_itv_off": "Desativada: são removidas as suas entidades, o seu indicador no cartão e os seus avisos.",
      "form_insurance_off": "Desativado: são removidas as suas entidades, o seu indicador no cartão e os seus avisos.",
      "first_notice": "O primeiro aviso, {days} dias antes",
      "mt_last": "Última revisão",
      "mt_last_help": "Se o veículo ainda não fez nenhuma, indique a data de matrícula e 0 km.",
      "mt_next_is": "A próxima será a {number}.ª revisão.",
      "mt_km_then": "Quilómetros nessa altura",
      "mt_use_odometer": "Usar os do veículo agora ({km} km)",
      "mt_every": "De quanto em quanto",
      "mt_every_help": "O manual pede um intervalo mais curto com trajetos curtos repetidos, pó, lama, frio extremo ou sal.",
      "mt_interval_manual": "O do manual",
      "mt_interval_value": "{km} km ou {months} meses",
      "mt_interval_other": "Escolhe você",
      "mt_preview": "Próxima revisão: {date} ou aos {km} km",
      "mt_whichever": "O que chegar primeiro: {date} ou aos {km} km.",
      "by_time": "Por tempo",
      "by_km": "Por quilómetros",
      "mt_km_detail": "Agora {now} km · revisão aos {due}",
      "mt_this_service": "O que inclui esta revisão",
      "n_operations": "{count} operações",
      "mt_no_plan": "Este modelo não tem plano de manutenção no catálogo.",
      "mt_next_adds": "Na seguinte ({number}.ª) acrescenta-se",
      "mt_history_item": "{number}.ª revisão · {date} · {km} km",
      "mt_no_history": "Ainda não há revisões registadas.",
      "itv_registration_title": "Matrícula",
      "itv_registration_help": "Vem no certificado de matrícula. Com ela calcula-se sozinha a primeira ITV.",
      "itv_passed_title": "ITV já feitas",
      "itv_passed_help": "Só se o veículo já fez alguma.",
      "itv_passed": "Já fez alguma ITV",
      "itv_next_title": "Próxima ITV",
      "itv_next_rules": "É calculada com as regras do país da conta.",
      "itv_next_auto": "Calcular sozinha",
      "itv_next_manual": "Indicar outra data",
      "itv_next_manual_note": "Se o centro de inspeção lhe deu uma diferente",
      "itv_preview": "Próxima ITV: {date}",
      "itv_manual_date": "data indicada à mão",
      "itv_age": "{years} anos",
      "itv_none_yet": "Nenhuma ainda",
      "itv_first_at": "A primeira, aos {years} anos",
      "itv_rules_title": "De quanto em quanto",
      "itv_rules": "A primeira aos {first} anos; depois a cada {interval} anos e, a partir dos {reduced} anos, todos os anos.",
      "itv_history_item": "ITV feita a {date}",
      "itv_no_history": "Ainda não há nenhuma ITV registada.",
      "ins_policy_title": "A apólice",
      "ins_policy_help": "O número da apólice e os telefones só se veem no cartão e no painel; nunca aparecem no diagnóstico.",
      "ins_renewal_title": "Renovação",
      "ins_renewal_help": "O seguro renova-se sozinho todos os anos. Para não renovar é preciso avisar antes.",
      "ins_renews_on": "Renova a",
      "ins_notice_days": "Dias de pré-aviso",
      "ins_phones_title": "Telefones",
      "ins_phones_help": "Para ligar com um toque a partir do cartão e daqui.",
      "ins_preview": "Último dia para cancelar: {date}",
      "ins_preview_passed": "Esse prazo já passou. Renova a {date}.",
      "ins_dates": "Datas",
      "ins_to_cancel": "Para cancelar",
      "ins_to_renewal": "Para a renovação",
      "ins_deadline_passed": "Prazo passado",
      "ins_deadline_on": "Último dia: {date}",
      "ins_renews_itself": "Renova-se sozinho a {date}",
      "ins_assistance": "Assistência",
      "read_only": "Só de leitura: as alterações são feitas por um administrador do Home Assistant.",
      "people": "Pessoas",
      "people_none": "Sem atribuir",
      "people_edit": "Escolher",
      "people_title": "Pessoas de {name}",
      "people_help": "Escolhe a quem pertence este carro. São as pessoas de Definições → Pessoas.",
      "mine": "Teu",
      "error_unknown_person": "Essa pessoa já não existe no Home Assistant.",
      "error_unauthorized": "Só um administrador pode fazer esta alteração.",
      "plate": "Matrícula"
    },
    "it": {
      "tab_cars": "Veicoli",
      "tab_alerts": "Avvisi",
      "tab_data": "Dati",
      "tab_diagnostics": "Diagnostica",
      "loading": "Caricamento…",
      "retry": "Riprova",
      "no_cars": "Non ci sono veicoli. Aggiungi il tuo account Deepal in Impostazioni → Dispositivi e servizi.",
      "error_generic": "Non è stato possibile completare l'operazione. Riprova.",
      "day": "{value} giorno",
      "days": "{value} giorni",
      "or": " o ",
      "not_configured": "Nessun modello scelto",
      "sheet_verified": "Scheda verificata",
      "sheet_catalogue": "Scheda da catalogo",
      "battery": "Batteria",
      "range": "Autonomia",
      "odometer": "Chilometraggio",
      "appearance": "Aspetto",
      "configure": "Configura",
      "section_charge": "Ricarica",
      "section_warnings": "Spie",
      "section_maintenance": "Manutenzione",
      "section_itv": "ITV",
      "section_insurance": "Assicurazione",
      "section_appearance": "Aspetto",
      "section_people": "Persone",
      "not_set": "Non configurato",
      "add_maintenance": "Attiva la manutenzione",
      "add_itv": "Aggiungi l'ITV",
      "add_insurance": "Aggiungi l'assicurazione",
      "feature_seat_heat": "Sedili riscaldati",
      "feature_seat_vent": "Sedili ventilati",
      "feature_wheel_heat": "Volante riscaldato",
      "feature_power_tailgate": "Portellone elettrico",
      "wheel_pro": "Cerchi da 18\"",
      "wheel_cover": "Cerchi da 20\" con copricerchi aerodinamici",
      "wheel_open": "Cerchi da 20\" senza copricerchi",
      "service_number": "{number}º tagliando",
      "overdue": "Scaduto",
      "left": "Mancano {parts}",
      "overdue_since": "Scaduto da {days}",
      "cancel_until": "Termine per disdire: {date}",
      "renews_in": "Si rinnova tra {days}",
      "notify_to": "Avvisa",
      "n_notices": "{count} avvisi",
      "edit_threshold": "Cambia l'anticipo",
      "accept": "Conferma",
      "cancel": "Annulla",
      "unit_km": "km",
      "unit_days": "giorni",
      "when_km": "quando mancano {value} km",
      "when_days": "quando mancano {value} giorni",
      "when_days_deadline": "{value} giorni prima del termine",
      "when_maintenance_overdue": "il giorno stesso o al raggiungimento dei km",
      "when_itv_overdue": "il giorno stesso",
      "when_insurance_last_day": "ultimo giorno per disdire",
      "when_insurance_renewed": "il giorno stesso",
      "notice_charge_started": "Ricarica avviata",
      "notice_charge_interrupted": "Ricarica interrotta",
      "notice_charge_finished": "Ricarica terminata",
      "notice_warnings": "Spie",
      "notice_tires": "Pneumatici",
      "notice_key_battery": "Batteria della chiave scarica",
      "notice_maintenance_t1": "Avviso per tempo 1",
      "notice_maintenance_t2": "Avviso per tempo 2",
      "notice_maintenance_t3": "Avviso per tempo 3",
      "notice_maintenance_k1": "Avviso per chilometri 1",
      "notice_maintenance_k2": "Avviso per chilometri 2",
      "notice_maintenance_k3": "Avviso per chilometri 3",
      "notice_maintenance_overdue": "Tagliando in scadenza",
      "notice_itv_t1": "Avviso 1",
      "notice_itv_t2": "Avviso 2",
      "notice_itv_t3": "Avviso 3",
      "notice_itv_overdue": "ITV in scadenza",
      "notice_insurance_c1": "Avviso di disdetta 1",
      "notice_insurance_c2": "Avviso di disdetta 2",
      "notice_insurance_last_day": "Termine per disdire",
      "notice_insurance_r1": "Avviso di rinnovo 1",
      "notice_insurance_r2": "Avviso di rinnovo 2",
      "notice_insurance_renewed": "Assicurazione rinnovata",
      "unsaved": "Questo veicolo ha modifiche non salvate.",
      "alerts_help": "Spunta chi riceve ogni avviso. La matita cambia i giorni o i chilometri di quell'avviso; gli anticipi valgono per questo veicolo.",
      "factory_thresholds": "Anticipi predefiniti",
      "discard": "Scarta",
      "save": "Salva",
      "saved": "Salvato",
      "copy_from": "Copia da un altro veicolo",
      "car": "Veicolo",
      "copy": "Copia",
      "error_threshold_range_limits": "L'anticipo deve essere compreso tra {low} e {high}.",
      "error_threshold_range": "Un anticipo è fuori dai limiti.",
      "error_threshold_order": "Gli anticipi devono andare dal più lungo al più corto: l'avviso 1 prima del 2, e il 2 prima del 3.",
      "error_not_found": "Quel veicolo non è più nell'account.",
      "error_invalid": "Alcuni dati non sono validi.",
      "error_invalid_file": "Il file non è una copia di DEC Deepal oppure è danneggiato.",
      "error_newer_file": "La copia proviene da una versione più recente dell'integrazione. Aggiorna DEC Deepal e riprova.",
      "error_empty_file": "La copia non contiene dati di alcun veicolo.",
      "error_required": "Mancano dei dati.",
      "backup_title": "Copia di sicurezza",
      "backup_help": "Manutenzione, ITV, assicurazione e aspetto dei tuoi veicoli. I dati appartengono al veicolo: non si perdono quando l'account viene rimosso.",
      "download_title": "Scarica una copia",
      "download_help": "Un file con i dati di tutti i veicoli. Contiene il numero di polizza e i telefoni dell'assicurazione: conservalo in un luogo sicuro.",
      "download": "Scarica",
      "send_title": "Invia la copia a un telefono",
      "send_help": "Arriva una notifica; toccandola si apre il browser e si scarica il file. Il link scade dopo 10 minuti.",
      "send": "Invia",
      "sent_to": "Notifica inviata a {device}.",
      "upload_title": "Carica una copia",
      "upload_help": "Riporta i veicoli del file a com'erano al suo interno. Gli altri veicoli non vengono toccati.",
      "choose_file": "Scegli file",
      "imported": "Copia caricata: {cars}.",
      "stored_title": "Dati salvati",
      "stored_help": "Per veicolo, identificato dal suo VIN.",
      "stored_none": "Non ci sono dati salvati per alcun veicolo.",
      "in_account": "Nell'account",
      "no_account": "Senza account",
      "no_account_note": "Non è più in nessun account",
      "delete": "Elimina",
      "delete_title": "Elimina i dati salvati",
      "delete_confirm": "La manutenzione, l'ITV e l'assicurazione di {name} verranno eliminate. Non si può annullare: scarica prima una copia se vuoi conservarle.",
      "deleted": "Dati eliminati.",
      "history_title": "Cosa è successo",
      "history_help": "Modifiche, comandi e avvisi dall'ultimo riavvio. Lo stesso finisce nel file di diagnostica.",
      "history_none": "Ancora niente da mostrare.",
      "filter_all": "Tutto",
      "filter_orders": "Comandi",
      "filter_alerts": "Avvisi",
      "filter_errors": "Errori",
      "sheets_title": "Scheda di ogni veicolo",
      "sheets_help": "Quale equipaggiamento presume l'integrazione, e da dove lo ricava.",
      "diagnostics_file": "Diagnostica",
      "ev_alert": "Avviso inviato: {name}",
      "ev_targets": "{count} destinatari",
      "ev_wake": "Risveglio del veicolo",
      "ev_command": "Comando: {name}",
      "ev_code": "codice",
      "today": "Oggi",
      "yesterday": "Ieri",
      "enabled": "Attivo",
      "mt_services_done": "Tagliandi già fatti",
      "mt_interval_km": "Intervallo (km)",
      "mt_interval_months": "Intervallo (mesi)",
      "mt_register": "Registra tagliando fatto",
      "mt_register_help": "Registra il {number}º tagliando di {name} e inizia a contare per il successivo.",
      "date": "Data",
      "mt_km": "Chilometri",
      "register": "Registra",
      "registered": "Registrato",
      "itv_registration": "Data di immatricolazione",
      "itv_last": "Ultima ITV superata",
      "itv_next": "Prossima ITV (manuale)",
      "itv_register": "Registra ITV superata",
      "itv_register_help": "Registra che {name} ha superato l'ITV e calcola la successiva.",
      "ins_company": "Compagnia",
      "ins_policy": "N. di polizza",
      "ins_kind": "Tipo di assicurazione",
      "ins_notice": "Giorni di preavviso per disdire",
      "ins_phone_assistance": "Telefono assistenza",
      "ins_phone_company": "Telefono compagnia",
      "kind_third_party": "RC auto",
      "kind_third_party_plus": "RC auto con garanzie aggiuntive",
      "kind_comprehensive_excess": "Kasko con franchigia",
      "kind_comprehensive": "Kasko senza franchigia",
      "tab_settings": "Impostazioni",
      "appearance_title": "Aspetto di {name}",
      "appearance_help": "Decide la foto, la vista del veicolo e quale equipaggiamento si presume.",
      "model": "Modello",
      "trim": "Versione",
      "color": "Colore",
      "wheels": "Cerchi",
      "model_ev": "Elettrico",
      "model_phev": "Ibrido plug-in",
      "trim_full": "Sedili e volante riscaldati, portellone elettrico",
      "trim_basic": "Senza sedili né volante riscaldati",
      "account": "Account: {name}",
      "pin_title": "Controllo remoto con PIN",
      "pin_help": "Per bloccare e sbloccare, finestrini e bagagliaio. È il PIN dell'app ufficiale Deepal, con lo stesso account. Vale per tutti i veicoli dell'account.",
      "pin_enabled": "Comandi con PIN",
      "pin_enabled_help": "Senza questo, la scheda mostra solo lo stato di porte, finestrini e bagagliaio.",
      "pin": "PIN",
      "pin_field_help": "Viene verificato con Deepal al salvataggio. Lascia vuoto per mantenere quello attuale.",
      "pin_checked": "Verificato",
      "show_pin": "Mostra il PIN",
      "pin_mode_title": "Come si usano i comandi",
      "mode_direct": "Diretto",
      "mode_direct_help": "Il comando viene inviato al tocco, dopo la conferma. Il più comodo.",
      "mode_armed": "Prima sblocca",
      "mode_armed_help": "Bisogna prima attivare «Sblocco azioni con PIN», e dura solo per un po'. Il più sicuro.",
      "arm_seconds": "Quanto dura lo sblocco",
      "arm_seconds_help": "Trascorso quel tempo, i comandi con PIN si bloccano di nuovo da soli.",
      "seconds": "{value} s",
      "arm_notify": "Avvisa allo sblocco",
      "arm_notify_help": "Una notifica in Home Assistant ogni volta che i comandi vengono consentiti.",
      "reading_title": "Lettura dei dati",
      "reading_help": "Come e ogni quanto viene interrogato il veicolo.",
      "scan_title": "Intervallo di lettura",
      "scan_help": "Ogni quanto vengono letti i dati del veicolo. Valori molto bassi possono portare Deepal a limitare l'account.",
      "minutes": "{value} min",
      "wake_title": "Risveglia il veicolo quando serve",
      "wake_help": "Quando tocchi Aggiorna e prima di un comando con PIN. Mai nelle letture automatiche, per proteggere la batteria a 12 V.",
      "manual_bev": "Manuale BEV",
      "manual_phev": "Manuale PHEV",
      "manual_help": "Il link che la scheda apre in Altro → Manuale. Vuoto per usare quello ufficiale.",
      "debug_title": "Modalità debug",
      "debug_help": "Conserva richieste e risposte complete (senza dati personali) nella diagnostica.",
      "save_check": "Salva",
      "unsaved_settings": "Ci sono modifiche non salvate.",
      "error_pin_required": "Inserisci il PIN.",
      "error_pin_invalid": "Il PIN non è corretto. È quello dell'app ufficiale Deepal, con questo stesso account.",
      "error_pin_rate_limited": "Troppi tentativi di PIN. Attendi qualche minuto prima di riprovare.",
      "error_cannot_connect": "Impossibile connettersi a Deepal. Riprova più tardi.",
      "error_invalid_url": "Il link del manuale non è valido: deve iniziare con http:// o https://.",
      "error_unknown_model": "Quel modello non è nel catalogo.",
      "close": "Chiudi",
      "other": "Altro",
      "history": "Storico",
      "manual": "Manuale",
      "copied": "Copiato: {text}",
      "form_maintenance": "Configura la manutenzione",
      "form_itv": "Configura l'ITV",
      "form_insurance": "Configura l'assicurazione",
      "form_maintenance_off": "Disattivata: vengono rimosse le sue entità, la sua spia sulla scheda e i suoi avvisi. Lo storico va perso.",
      "form_itv_off": "Disattivata: vengono rimosse le sue entità, la sua spia sulla scheda e i suoi avvisi.",
      "form_insurance_off": "Disattivata: vengono rimosse le sue entità, la sua spia sulla scheda e i suoi avvisi.",
      "first_notice": "Il primo avviso, {days} giorni prima",
      "mt_last": "Ultimo tagliando",
      "mt_last_help": "Se il veicolo non ne ha ancora fatto nessuno, inserisci la data di immatricolazione e 0 km.",
      "mt_next_is": "Il prossimo sarà il {number}º tagliando.",
      "mt_km_then": "Chilometri in quel momento",
      "mt_use_odometer": "Usa quelli attuali del veicolo ({km} km)",
      "mt_every": "Ogni quanto",
      "mt_every_help": "Il manuale chiede un intervallo più breve con tragitti brevi ripetuti, polvere, fango, freddo estremo o sale.",
      "mt_interval_manual": "Quello del manuale",
      "mt_interval_value": "{km} km o {months} mesi",
      "mt_interval_other": "Lo scegli tu",
      "mt_preview": "Prossimo tagliando: {date} o a {km} km",
      "mt_whichever": "Quello che arriva prima: il {date} o a {km} km.",
      "by_time": "Per tempo",
      "by_km": "Per chilometri",
      "mt_km_detail": "Ora {now} km · tagliando a {due}",
      "mt_this_service": "Cosa include questo tagliando",
      "n_operations": "{count} operazioni",
      "mt_no_plan": "Questo modello non ha un piano di manutenzione nel catalogo.",
      "mt_next_adds": "Nel successivo ({number}º) si aggiunge",
      "mt_history_item": "{number}º tagliando · {date} · {km} km",
      "mt_no_history": "Non ci sono ancora tagliandi registrati.",
      "itv_registration_title": "Immatricolazione",
      "itv_registration_help": "Si trova sulla carta di circolazione. Con questa si calcola da sola la prima ITV.",
      "itv_passed_title": "ITV già superate",
      "itv_passed_help": "Solo se il veicolo ne ha già superata una.",
      "itv_passed": "Ha già superato un'ITV",
      "itv_next_title": "Prossima ITV",
      "itv_next_rules": "Viene calcolata con le regole del paese dell'account.",
      "itv_next_auto": "Calcolala da sola",
      "itv_next_manual": "Indica un'altra data",
      "itv_next_manual_note": "Se il centro te ne ha data una diversa",
      "itv_preview": "Prossima ITV: {date}",
      "itv_manual_date": "data inserita a mano",
      "itv_age": "{years} anni",
      "itv_none_yet": "Ancora nessuna",
      "itv_first_at": "La prima, a {years} anni",
      "itv_rules_title": "Ogni quanto",
      "itv_rules": "La prima a {first} anni; poi ogni {interval} anni e, dai {reduced} anni in poi, ogni anno.",
      "itv_history_item": "ITV superata il {date}",
      "itv_no_history": "Non c'è ancora nessuna ITV registrata.",
      "ins_policy_title": "La polizza",
      "ins_policy_help": "Il numero di polizza e i telefoni si vedono solo sulla scheda e nel pannello; non compaiono mai nella diagnostica.",
      "ins_renewal_title": "Rinnovo",
      "ins_renewal_help": "L'assicurazione si rinnova da sola ogni anno. Per non rinnovare bisogna avvisare prima.",
      "ins_renews_on": "Si rinnova il",
      "ins_notice_days": "Giorni di preavviso",
      "ins_phones_title": "Telefoni",
      "ins_phones_help": "Per chiamare con un tocco dalla scheda e da qui.",
      "ins_preview": "Ultimo giorno per disdire: {date}",
      "ins_preview_passed": "Quel termine è già passato. Si rinnova il {date}.",
      "ins_dates": "Date",
      "ins_to_cancel": "Per disdire",
      "ins_to_renewal": "Al rinnovo",
      "ins_deadline_passed": "Termine passato",
      "ins_deadline_on": "Ultimo giorno: {date}",
      "ins_renews_itself": "Si rinnova da sola il {date}",
      "ins_assistance": "Assistenza",
      "read_only": "Sola lettura: le modifiche le fa un amministratore di Home Assistant.",
      "people": "Persone",
      "people_none": "Non assegnato",
      "people_edit": "Scegli",
      "people_title": "Persone di {name}",
      "people_help": "Scegli a chi appartiene questa auto. Sono le persone di Impostazioni → Persone.",
      "mine": "Tua",
      "error_unknown_person": "Quella persona non esiste più in Home Assistant.",
      "error_unauthorized": "Solo un amministratore può fare questa modifica.",
      "plate": "Targa"
    },
    "pl": {
      "tab_cars": "Pojazdy",
      "tab_alerts": "Powiadomienia",
      "tab_data": "Dane",
      "tab_diagnostics": "Diagnostyka",
      "loading": "Ładowanie…",
      "retry": "Spróbuj ponownie",
      "no_cars": "Brak pojazdów. Dodaj swoje konto Deepal w Ustawienia → Urządzenia i usługi.",
      "error_generic": "Nie udało się tego dokończyć. Spróbuj ponownie.",
      "day": "{value} dzień",
      "days": "{value} dni",
      "or": " lub ",
      "not_configured": "Nie wybrano modelu",
      "sheet_verified": "Karta zweryfikowana",
      "sheet_catalogue": "Karta z katalogu",
      "battery": "Bateria",
      "range": "Zasięg",
      "odometer": "Przebieg",
      "appearance": "Wygląd",
      "configure": "Konfiguruj",
      "section_charge": "Ładowanie",
      "section_warnings": "Kontrolki",
      "section_maintenance": "Serwis",
      "section_itv": "ITV",
      "section_insurance": "Ubezpieczenie",
      "section_appearance": "Wygląd",
      "section_people": "Osoby",
      "not_set": "Nie skonfigurowano",
      "add_maintenance": "Włącz serwis",
      "add_itv": "Dodaj ITV",
      "add_insurance": "Dodaj ubezpieczenie",
      "feature_seat_heat": "Podgrzewane fotele",
      "feature_seat_vent": "Wentylowane fotele",
      "feature_wheel_heat": "Podgrzewana kierownica",
      "feature_power_tailgate": "Elektryczna klapa bagażnika",
      "wheel_pro": "Felgi 18\"",
      "wheel_cover": "Felgi 20\" z nakładkami aero",
      "wheel_open": "Felgi 20\" bez nakładek",
      "service_number": "{number}. przegląd",
      "overdue": "Po terminie",
      "left": "Pozostało: {parts}",
      "overdue_since": "Po terminie od: {days}",
      "cancel_until": "Termin wypowiedzenia: {date}",
      "renews_in": "Odnowienie za {days}",
      "notify_to": "Powiadom",
      "n_notices": "Powiadomienia: {count}",
      "edit_threshold": "Zmień wyprzedzenie",
      "accept": "Zatwierdź",
      "cancel": "Anuluj",
      "unit_km": "km",
      "unit_days": "dni",
      "when_km": "gdy zostanie {value} km",
      "when_days": "gdy zostanie {value} dni",
      "when_days_deadline": "{value} dni przed terminem",
      "when_maintenance_overdue": "w dniu terminu lub po osiągnięciu km",
      "when_itv_overdue": "w dniu terminu",
      "when_insurance_last_day": "ostatni dzień na wypowiedzenie",
      "when_insurance_renewed": "w dniu odnowienia",
      "notice_charge_started": "Ładowanie rozpoczęte",
      "notice_charge_interrupted": "Ładowanie przerwane",
      "notice_charge_finished": "Ładowanie zakończone",
      "notice_warnings": "Kontrolki ostrzegawcze",
      "notice_tires": "Opony",
      "notice_key_battery": "Słaba bateria w kluczyku",
      "notice_maintenance_t1": "Powiadomienie czasowe 1",
      "notice_maintenance_t2": "Powiadomienie czasowe 2",
      "notice_maintenance_t3": "Powiadomienie czasowe 3",
      "notice_maintenance_k1": "Powiadomienie o przebiegu 1",
      "notice_maintenance_k2": "Powiadomienie o przebiegu 2",
      "notice_maintenance_k3": "Powiadomienie o przebiegu 3",
      "notice_maintenance_overdue": "Termin przeglądu",
      "notice_itv_t1": "Powiadomienie 1",
      "notice_itv_t2": "Powiadomienie 2",
      "notice_itv_t3": "Powiadomienie 3",
      "notice_itv_overdue": "Termin ITV",
      "notice_insurance_c1": "Powiadomienie o wypowiedzeniu 1",
      "notice_insurance_c2": "Powiadomienie o wypowiedzeniu 2",
      "notice_insurance_last_day": "Termin wypowiedzenia",
      "notice_insurance_r1": "Powiadomienie o odnowieniu 1",
      "notice_insurance_r2": "Powiadomienie o odnowieniu 2",
      "notice_insurance_renewed": "Ubezpieczenie odnowione",
      "unsaved": "Ten pojazd ma niezapisane zmiany.",
      "alerts_help": "Zaznacz, kto dostaje każde powiadomienie. Ołówek zmienia dni lub kilometry danego powiadomienia; wyprzedzenia dotyczą tego pojazdu.",
      "factory_thresholds": "Domyślne wyprzedzenia",
      "discard": "Odrzuć",
      "save": "Zapisz",
      "saved": "Zapisano",
      "copy_from": "Skopiuj z innego pojazdu",
      "car": "Pojazd",
      "copy": "Kopiuj",
      "error_threshold_range_limits": "Wyprzedzenie musi mieścić się między {low} a {high}.",
      "error_threshold_range": "Jedno z wyprzedzeń jest poza zakresem.",
      "error_threshold_order": "Wyprzedzenia muszą iść od najdłuższego do najkrótszego: powiadomienie 1 przed 2, a 2 przed 3.",
      "error_not_found": "Tego pojazdu nie ma już na koncie.",
      "error_invalid": "Niektóre dane są nieprawidłowe.",
      "error_invalid_file": "Plik nie jest kopią DEC Deepal albo jest uszkodzony.",
      "error_newer_file": "Kopia pochodzi z nowszej wersji integracji. Zaktualizuj DEC Deepal i spróbuj ponownie.",
      "error_empty_file": "Kopia nie zawiera danych żadnego pojazdu.",
      "error_required": "Brakuje danych.",
      "backup_title": "Kopia zapasowa",
      "backup_help": "Serwis, ITV, ubezpieczenie i wygląd Twoich pojazdów. Dane należą do pojazdu: nie giną po usunięciu konta.",
      "download_title": "Pobierz kopię",
      "download_help": "Plik z danymi wszystkich pojazdów. Zawiera numer polisy i telefony ubezpieczyciela: przechowuj go w bezpiecznym miejscu.",
      "download": "Pobierz",
      "send_title": "Wyślij kopię na telefon",
      "send_help": "Przychodzi powiadomienie; po jego dotknięciu otwiera się przeglądarka i pobiera plik. Link wygasa po 10 minutach.",
      "send": "Wyślij",
      "sent_to": "Powiadomienie wysłane do {device}.",
      "upload_title": "Wczytaj kopię",
      "upload_help": "Przywraca pojazdy z pliku do stanu, w jakim są w nim zapisane. Pozostałe pojazdy pozostają bez zmian.",
      "choose_file": "Wybierz plik",
      "imported": "Kopia wczytana: {cars}.",
      "stored_title": "Zapisane dane",
      "stored_help": "Dla każdego pojazdu, rozpoznawanego po numerze VIN.",
      "stored_none": "Nie ma zapisanych danych żadnego pojazdu.",
      "in_account": "Na koncie",
      "no_account": "Bez konta",
      "no_account_note": "Nie ma go już na żadnym koncie",
      "delete": "Usuń",
      "delete_title": "Usuń zapisane dane",
      "delete_confirm": "Serwis, ITV i ubezpieczenie pojazdu {name} zostaną usunięte. Tego nie da się cofnąć: jeśli chcesz je zachować, najpierw pobierz kopię.",
      "deleted": "Dane usunięte.",
      "history_title": "Co się wydarzyło",
      "history_help": "Zmiany, polecenia i powiadomienia od ostatniego restartu. To samo trafia do pliku diagnostycznego.",
      "history_none": "Na razie nie ma nic do pokazania.",
      "filter_all": "Wszystko",
      "filter_orders": "Polecenia",
      "filter_alerts": "Powiadomienia",
      "filter_errors": "Błędy",
      "sheets_title": "Karta każdego pojazdu",
      "sheets_help": "Jakie wyposażenie zakłada integracja i skąd to wie.",
      "diagnostics_file": "Diagnostyka",
      "ev_alert": "Wysłano powiadomienie: {name}",
      "ev_targets": "Odbiorcy: {count}",
      "ev_wake": "Wybudzenie pojazdu",
      "ev_command": "Polecenie: {name}",
      "ev_code": "kod",
      "today": "Dzisiaj",
      "yesterday": "Wczoraj",
      "enabled": "Włączone",
      "mt_services_done": "Wykonane już przeglądy",
      "mt_interval_km": "Interwał (km)",
      "mt_interval_months": "Interwał (miesiące)",
      "mt_register": "Zarejestruj wykonany przegląd",
      "mt_register_help": "Zapisuje {number}. przegląd pojazdu {name} i zaczyna odliczać do następnego.",
      "date": "Data",
      "mt_km": "Kilometry",
      "register": "Zarejestruj",
      "registered": "Zarejestrowano",
      "itv_registration": "Data rejestracji",
      "itv_last": "Ostatnie zaliczone ITV",
      "itv_next": "Następne ITV (ręcznie)",
      "itv_register": "Zarejestruj zaliczone ITV",
      "itv_register_help": "Zapisuje, że {name} zaliczył ITV, i oblicza następne.",
      "ins_company": "Ubezpieczyciel",
      "ins_policy": "Nr polisy",
      "ins_kind": "Rodzaj ubezpieczenia",
      "ins_notice": "Dni wypowiedzenia",
      "ins_phone_assistance": "Telefon pomocy drogowej",
      "ins_phone_company": "Telefon ubezpieczyciela",
      "kind_third_party": "OC",
      "kind_third_party_plus": "OC rozszerzone",
      "kind_comprehensive_excess": "AC z udziałem własnym",
      "kind_comprehensive": "AC bez udziału własnego",
      "tab_settings": "Ustawienia",
      "appearance_title": "Wygląd: {name}",
      "appearance_help": "Decyduje o zdjęciu, widoku pojazdu i o tym, jakie wyposażenie jest zakładane.",
      "model": "Model",
      "trim": "Wersja",
      "color": "Kolor",
      "wheels": "Felgi",
      "model_ev": "Elektryczny",
      "model_phev": "Hybryda plug-in",
      "trim_full": "Podgrzewane fotele i kierownica, elektryczna klapa bagażnika",
      "trim_basic": "Bez podgrzewanych foteli i kierownicy",
      "account": "Konto: {name}",
      "pin_title": "Zdalne sterowanie z PIN-em",
      "pin_help": "Do zamykania i otwierania zamków, szyb i bagażnika. To PIN z oficjalnej aplikacji Deepal, z tym samym kontem. Obowiązuje dla wszystkich pojazdów na koncie.",
      "pin_enabled": "Polecenia z PIN-em",
      "pin_enabled_help": "Bez tego karta pokazuje tylko stan drzwi, szyb i bagażnika.",
      "pin": "PIN",
      "pin_field_help": "Jest sprawdzany w Deepal przy zapisie. Zostaw puste, aby zachować obecny.",
      "pin_checked": "Sprawdzono",
      "show_pin": "Pokaż PIN",
      "pin_mode_title": "Jak używane są polecenia",
      "mode_direct": "Bezpośrednio",
      "mode_direct_help": "Polecenie jest wysyłane po dotknięciu i potwierdzeniu. Najwygodniejsze.",
      "mode_armed": "Najpierw odblokuj",
      "mode_armed_help": "Najpierw trzeba włączyć „Odblokowanie akcji z PIN-em”, a to trwa tylko chwilę. Najbezpieczniejsze.",
      "arm_seconds": "Jak długo trwa odblokowanie",
      "arm_seconds_help": "Po tym czasie polecenia z PIN-em same się ponownie blokują.",
      "seconds": "{value} s",
      "arm_notify": "Powiadom przy odblokowaniu",
      "arm_notify_help": "Powiadomienie w Home Assistant za każdym razem, gdy polecenia zostają dozwolone.",
      "reading_title": "Odczyt danych",
      "reading_help": "Jak i jak często pojazd jest odpytywany.",
      "scan_title": "Interwał odczytu",
      "scan_help": "Jak często odczytywane są dane pojazdu. Bardzo niskie wartości mogą sprawić, że Deepal ograniczy konto.",
      "minutes": "{value} min",
      "wake_title": "Wybudzaj pojazd, gdy to potrzebne",
      "wake_help": "Gdy dotkniesz Odśwież i przed poleceniem z PIN-em. Nigdy przy automatycznych odczytach, aby chronić akumulator 12 V.",
      "manual_bev": "Instrukcja BEV",
      "manual_phev": "Instrukcja PHEV",
      "manual_help": "Link, który karta otwiera w Więcej → Instrukcja. Puste = oficjalna.",
      "debug_title": "Tryb debugowania",
      "debug_help": "Zapisuje pełne żądania i odpowiedzi (bez danych osobowych) w diagnostyce.",
      "save_check": "Zapisz",
      "unsaved_settings": "Są niezapisane zmiany.",
      "error_pin_required": "Wpisz PIN.",
      "error_pin_invalid": "PIN jest nieprawidłowy. To ten z oficjalnej aplikacji Deepal, z tym samym kontem.",
      "error_pin_rate_limited": "Zbyt wiele prób PIN-u. Odczekaj kilka minut przed kolejną próbą.",
      "error_cannot_connect": "Nie udało się połączyć z Deepal. Spróbuj później.",
      "error_invalid_url": "Link do instrukcji jest nieprawidłowy: musi zaczynać się od http:// lub https://.",
      "error_unknown_model": "Tego modelu nie ma w katalogu.",
      "close": "Zamknij",
      "other": "Inne",
      "history": "Historia",
      "manual": "Instrukcja",
      "copied": "Skopiowano: {text}",
      "form_maintenance": "Skonfiguruj serwis",
      "form_itv": "Skonfiguruj ITV",
      "form_insurance": "Skonfiguruj ubezpieczenie",
      "form_maintenance_off": "Wyłączone: usuwane są encje, kontrolka na karcie i powiadomienia. Historia przepada.",
      "form_itv_off": "Wyłączone: usuwane są encje, kontrolka na karcie i powiadomienia.",
      "form_insurance_off": "Wyłączone: usuwane są encje, kontrolka na karcie i powiadomienia.",
      "first_notice": "Pierwsze powiadomienie {days} dni wcześniej",
      "mt_last": "Ostatni przegląd",
      "mt_last_help": "Jeśli pojazd nie miał jeszcze żadnego, wpisz datę rejestracji i 0 km.",
      "mt_next_is": "Następny będzie {number}. przegląd.",
      "mt_km_then": "Kilometry w tamtym dniu",
      "mt_use_odometer": "Użyj obecnego przebiegu pojazdu ({km} km)",
      "mt_every": "Jak często",
      "mt_every_help": "Instrukcja wymaga krótszego interwału przy częstych krótkich trasach, kurzu, błocie, skrajnym mrozie lub soli.",
      "mt_interval_manual": "Według instrukcji",
      "mt_interval_value": "{km} km lub {months} mies.",
      "mt_interval_other": "Wybierasz samodzielnie",
      "mt_preview": "Następny przegląd: {date} lub przy {km} km",
      "mt_whichever": "Co nastąpi wcześniej: {date} lub przy {km} km.",
      "by_time": "Według czasu",
      "by_km": "Według przebiegu",
      "mt_km_detail": "Teraz {now} km · przegląd przy {due}",
      "mt_this_service": "Co obejmuje ten przegląd",
      "n_operations": "Czynności: {count}",
      "mt_no_plan": "Ten model nie ma planu serwisowego w katalogu.",
      "mt_next_adds": "W następnym ({number}.) dochodzi",
      "mt_history_item": "{number}. przegląd · {date} · {km} km",
      "mt_no_history": "Nie zarejestrowano jeszcze żadnego przeglądu.",
      "itv_registration_title": "Rejestracja",
      "itv_registration_help": "Jest w dowodzie rejestracyjnym. Na jej podstawie obliczane jest pierwsze ITV.",
      "itv_passed_title": "Zaliczone już ITV",
      "itv_passed_help": "Tylko jeśli pojazd zaliczył już jakieś.",
      "itv_passed": "Zaliczył już ITV",
      "itv_next_title": "Następne ITV",
      "itv_next_rules": "Jest obliczane według przepisów kraju konta.",
      "itv_next_auto": "Oblicz automatycznie",
      "itv_next_manual": "Podaj inną datę",
      "itv_next_manual_note": "Jeśli stacja podała Ci inną",
      "itv_preview": "Następne ITV: {date}",
      "itv_manual_date": "data wpisana ręcznie",
      "itv_age": "Wiek w latach: {years}",
      "itv_none_yet": "Jeszcze żadnego",
      "itv_first_at": "Pierwsze po {years} latach",
      "itv_rules_title": "Jak często",
      "itv_rules": "Pierwsze po {first} latach; potem co {interval} lata, a od {reduced} lat co roku.",
      "itv_history_item": "ITV zaliczone {date}",
      "itv_no_history": "Nie zarejestrowano jeszcze żadnego ITV.",
      "ins_policy_title": "Polisa",
      "ins_policy_help": "Numer polisy i telefony widać tylko na karcie i w panelu; nigdy nie trafiają do diagnostyki.",
      "ins_renewal_title": "Odnowienie",
      "ins_renewal_help": "Ubezpieczenie odnawia się samo co roku. Aby zrezygnować, trzeba powiadomić wcześniej.",
      "ins_renews_on": "Odnawia się",
      "ins_notice_days": "Dni wypowiedzenia",
      "ins_phones_title": "Telefony",
      "ins_phones_help": "Aby zadzwonić jednym dotknięciem z karty i stąd.",
      "ins_preview": "Ostatni dzień na wypowiedzenie: {date}",
      "ins_preview_passed": "Ten termin już minął. Odnowienie: {date}.",
      "ins_dates": "Daty",
      "ins_to_cancel": "Do wypowiedzenia",
      "ins_to_renewal": "Do odnowienia",
      "ins_deadline_passed": "Termin minął",
      "ins_deadline_on": "Ostatni dzień: {date}",
      "ins_renews_itself": "Odnawia się samo {date}",
      "ins_assistance": "Pomoc drogowa",
      "read_only": "Tylko do odczytu: zmiany wprowadza administrator Home Assistant.",
      "people": "Osoby",
      "people_none": "Nieprzypisany",
      "people_edit": "Wybierz",
      "people_title": "Osoby: {name}",
      "people_help": "Wybierz, do kogo należy ten samochód. To osoby z Ustawienia → Osoby.",
      "mine": "Twój",
      "error_unknown_person": "Ta osoba już nie istnieje w Home Assistant.",
      "error_unauthorized": "Tę zmianę może wprowadzić tylko administrator.",
      "plate": "Tablica rejestracyjna"
    },
    "de": {
      "tab_cars": "Fahrzeuge",
      "tab_alerts": "Benachrichtigungen",
      "tab_data": "Daten",
      "tab_diagnostics": "Diagnose",
      "loading": "Wird geladen…",
      "retry": "Erneut versuchen",
      "no_cars": "Es gibt keine Fahrzeuge. Füge dein Deepal-Konto unter Einstellungen → Geräte & Dienste hinzu.",
      "error_generic": "Das konnte nicht abgeschlossen werden. Versuche es erneut.",
      "day": "{value} Tag",
      "days": "{value} Tage",
      "or": " oder ",
      "not_configured": "Kein Modell gewählt",
      "sheet_verified": "Geprüftes Datenblatt",
      "sheet_catalogue": "Katalog-Datenblatt",
      "battery": "Batterie",
      "range": "Reichweite",
      "odometer": "Kilometerstand",
      "appearance": "Aussehen",
      "configure": "Konfigurieren",
      "section_charge": "Laden",
      "section_warnings": "Warnungen",
      "section_maintenance": "Wartung",
      "section_itv": "ITV",
      "section_insurance": "Versicherung",
      "section_appearance": "Aussehen",
      "section_people": "Personen",
      "not_set": "Nicht eingerichtet",
      "add_maintenance": "Wartung aktivieren",
      "add_itv": "ITV hinzufügen",
      "add_insurance": "Versicherung hinzufügen",
      "feature_seat_heat": "Sitzheizung",
      "feature_seat_vent": "Sitzbelüftung",
      "feature_wheel_heat": "Lenkradheizung",
      "feature_power_tailgate": "Elektrische Heckklappe",
      "wheel_pro": "18\"-Felgen",
      "wheel_cover": "20\"-Felgen mit Aero-Abdeckung",
      "wheel_open": "20\"-Felgen ohne Abdeckung",
      "service_number": "{number}. Wartung",
      "overdue": "Überfällig",
      "left": "Noch {parts}",
      "overdue_since": "Seit {days} überfällig",
      "cancel_until": "Kündigungsfrist: {date}",
      "renews_in": "Verlängert sich in {days}",
      "notify_to": "Benachrichtigen",
      "n_notices": "{count} Benachrichtigungen",
      "edit_threshold": "Vorlaufzeit ändern",
      "accept": "Übernehmen",
      "cancel": "Abbrechen",
      "unit_km": "km",
      "unit_days": "Tage",
      "when_km": "noch {value} km",
      "when_days": "noch {value} Tage",
      "when_days_deadline": "{value} Tage vor der Frist",
      "when_maintenance_overdue": "am Tag selbst oder beim Erreichen der km",
      "when_itv_overdue": "am Tag selbst",
      "when_insurance_last_day": "letzter Tag zum Kündigen",
      "when_insurance_renewed": "am Tag selbst",
      "notice_charge_started": "Laden gestartet",
      "notice_charge_interrupted": "Laden unterbrochen",
      "notice_charge_finished": "Laden beendet",
      "notice_warnings": "Warnleuchten",
      "notice_tires": "Reifen",
      "notice_key_battery": "Schlüsselbatterie schwach",
      "notice_maintenance_t1": "Hinweis nach Zeit 1",
      "notice_maintenance_t2": "Hinweis nach Zeit 2",
      "notice_maintenance_t3": "Hinweis nach Zeit 3",
      "notice_maintenance_k1": "Hinweis nach Kilometern 1",
      "notice_maintenance_k2": "Hinweis nach Kilometern 2",
      "notice_maintenance_k3": "Hinweis nach Kilometern 3",
      "notice_maintenance_overdue": "Wartung fällig",
      "notice_itv_t1": "Hinweis 1",
      "notice_itv_t2": "Hinweis 2",
      "notice_itv_t3": "Hinweis 3",
      "notice_itv_overdue": "ITV fällig",
      "notice_insurance_c1": "Kündigungshinweis 1",
      "notice_insurance_c2": "Kündigungshinweis 2",
      "notice_insurance_last_day": "Kündigungsfrist",
      "notice_insurance_r1": "Verlängerungshinweis 1",
      "notice_insurance_r2": "Verlängerungshinweis 2",
      "notice_insurance_renewed": "Versicherung verlängert",
      "unsaved": "Dieses Fahrzeug hat ungespeicherte Änderungen.",
      "alerts_help": "Markiere, wer welche Benachrichtigung erhält. Der Stift ändert die Tage oder Kilometer dieser Benachrichtigung; die Vorlaufzeiten gelten für dieses Fahrzeug.",
      "factory_thresholds": "Standard-Vorlaufzeiten",
      "discard": "Verwerfen",
      "save": "Speichern",
      "saved": "Gespeichert",
      "copy_from": "Von anderem Fahrzeug kopieren",
      "car": "Fahrzeug",
      "copy": "Kopieren",
      "error_threshold_range_limits": "Die Vorlaufzeit muss zwischen {low} und {high} liegen.",
      "error_threshold_range": "Eine Vorlaufzeit liegt außerhalb des Bereichs.",
      "error_threshold_order": "Die Vorlaufzeiten müssen von der längsten zur kürzesten gehen: Hinweis 1 vor 2 und 2 vor 3.",
      "error_not_found": "Dieses Fahrzeug ist nicht mehr im Konto.",
      "error_invalid": "Einige Daten sind ungültig.",
      "error_invalid_file": "Die Datei ist keine DEC-Deepal-Sicherung oder sie ist beschädigt.",
      "error_newer_file": "Die Sicherung stammt aus einer neueren Version der Integration. Aktualisiere DEC Deepal und versuche es erneut.",
      "error_empty_file": "Die Sicherung enthält keine Fahrzeugdaten.",
      "error_required": "Es fehlen Angaben.",
      "backup_title": "Sicherung",
      "backup_help": "Wartung, ITV, Versicherung und Aussehen deiner Fahrzeuge. Die Daten gehören zum Fahrzeug: Sie gehen nicht verloren, wenn das Konto entfernt wird.",
      "download_title": "Sicherung herunterladen",
      "download_help": "Eine Datei mit den Daten aller Fahrzeuge. Sie enthält die Policennummer und die Telefonnummern der Versicherung: Bewahre sie sicher auf.",
      "download": "Herunterladen",
      "send_title": "Sicherung an ein Handy senden",
      "send_help": "Es kommt eine Benachrichtigung; beim Antippen öffnet sich der Browser und lädt die Datei herunter. Der Link läuft in 10 Minuten ab.",
      "send": "Senden",
      "sent_to": "Benachrichtigung an {device} gesendet.",
      "upload_title": "Sicherung laden",
      "upload_help": "Stellt die Fahrzeuge aus der Datei so wieder her, wie sie darin stehen. Andere Fahrzeuge bleiben unberührt.",
      "choose_file": "Datei wählen",
      "imported": "Sicherung geladen: {cars}.",
      "stored_title": "Gespeicherte Daten",
      "stored_help": "Pro Fahrzeug, erkannt an seiner FIN.",
      "stored_none": "Es sind keine Fahrzeugdaten gespeichert.",
      "in_account": "Im Konto",
      "no_account": "Kein Konto",
      "no_account_note": "In keinem Konto mehr",
      "delete": "Löschen",
      "delete_title": "Gespeicherte Daten löschen",
      "delete_confirm": "Wartung, ITV und Versicherung von {name} werden gelöscht. Das lässt sich nicht rückgängig machen: Lade vorher eine Sicherung herunter, wenn du sie behalten möchtest.",
      "deleted": "Daten gelöscht.",
      "history_title": "Was passiert ist",
      "history_help": "Änderungen, Befehle und Benachrichtigungen seit dem letzten Neustart. Dasselbe steht in der Diagnosedatei.",
      "history_none": "Noch nichts anzuzeigen.",
      "filter_all": "Alle",
      "filter_orders": "Befehle",
      "filter_alerts": "Benachrichtigungen",
      "filter_errors": "Fehler",
      "sheets_title": "Datenblatt jedes Fahrzeugs",
      "sheets_help": "Welche Ausstattung die Integration annimmt und woher sie das hat.",
      "diagnostics_file": "Diagnose",
      "ev_alert": "Benachrichtigung gesendet: {name}",
      "ev_targets": "{count} Empfänger",
      "ev_wake": "Fahrzeug geweckt",
      "ev_command": "Befehl: {name}",
      "ev_code": "Code",
      "today": "Heute",
      "yesterday": "Gestern",
      "enabled": "Aktiviert",
      "mt_services_done": "Bereits erfolgte Wartungen",
      "mt_interval_km": "Intervall (km)",
      "mt_interval_months": "Intervall (Monate)",
      "mt_register": "Erledigte Wartung erfassen",
      "mt_register_help": "Vermerkt die {number}. Wartung von {name} und beginnt die Zählung bis zur nächsten.",
      "date": "Datum",
      "mt_km": "Kilometer",
      "register": "Erfassen",
      "registered": "Erfasst",
      "itv_registration": "Zulassungsdatum",
      "itv_last": "Letzte bestandene ITV",
      "itv_next": "Nächste ITV (manuell)",
      "itv_register": "Bestandene ITV erfassen",
      "itv_register_help": "Vermerkt, dass {name} die ITV bestanden hat, und berechnet die nächste.",
      "ins_company": "Gesellschaft",
      "ins_policy": "Policennummer",
      "ins_kind": "Versicherungsart",
      "ins_notice": "Kündigungsfrist in Tagen",
      "ins_phone_assistance": "Telefon Pannenhilfe",
      "ins_phone_company": "Telefon Gesellschaft",
      "kind_third_party": "Haftpflicht",
      "kind_third_party_plus": "Teilkasko",
      "kind_comprehensive_excess": "Vollkasko mit Selbstbeteiligung",
      "kind_comprehensive": "Vollkasko ohne Selbstbeteiligung",
      "tab_settings": "Einstellungen",
      "appearance_title": "Aussehen von {name}",
      "appearance_help": "Bestimmt das Foto, die Fahrzeugansicht und welche Ausstattung angenommen wird.",
      "model": "Modell",
      "trim": "Version",
      "color": "Farbe",
      "wheels": "Felgen",
      "model_ev": "Elektrisch",
      "model_phev": "Plug-in-Hybrid",
      "trim_full": "Sitz- und Lenkradheizung, elektrische Heckklappe",
      "trim_basic": "Ohne Sitz- und Lenkradheizung",
      "account": "Konto: {name}",
      "pin_title": "Fernsteuerung mit PIN",
      "pin_help": "Zum Ver- und Entriegeln, für Fenster und Kofferraum. Es ist die PIN der offiziellen Deepal-App, mit demselben Konto. Sie gilt für alle Fahrzeuge des Kontos.",
      "pin_enabled": "PIN-Befehle",
      "pin_enabled_help": "Ohne dies zeigt die Karte nur den Zustand von Türen, Fenstern und Kofferraum.",
      "pin": "PIN",
      "pin_field_help": "Sie wird beim Speichern bei Deepal geprüft. Leer lassen, um die aktuelle zu behalten.",
      "pin_checked": "Geprüft",
      "show_pin": "PIN anzeigen",
      "pin_mode_title": "Wie Befehle verwendet werden",
      "mode_direct": "Direkt",
      "mode_direct_help": "Der Befehl wird beim Antippen nach einer Bestätigung gesendet. Am bequemsten.",
      "mode_armed": "Erst entsperren",
      "mode_armed_help": "Du musst zuerst „PIN-Aktionen entsperren“ aktivieren, und das gilt nur eine Weile. Am sichersten.",
      "arm_seconds": "Wie lange die Entsperrung gilt",
      "arm_seconds_help": "Nach dieser Zeit sperren sich die PIN-Befehle von selbst wieder.",
      "seconds": "{value} s",
      "arm_notify": "Beim Entsperren benachrichtigen",
      "arm_notify_help": "Eine Benachrichtigung in Home Assistant, jedes Mal wenn Befehle erlaubt werden.",
      "reading_title": "Datenabfrage",
      "reading_help": "Wie und wie oft das Fahrzeug abgefragt wird.",
      "scan_title": "Abfrageintervall",
      "scan_help": "Wie oft die Fahrzeugdaten gelesen werden. Sehr niedrige Werte können dazu führen, dass Deepal das Konto drosselt.",
      "minutes": "{value} min",
      "wake_title": "Fahrzeug bei Bedarf wecken",
      "wake_help": "Wenn du Aktualisieren antippst und vor einem PIN-Befehl. Nie bei automatischen Abfragen, um die 12-V-Batterie zu schonen.",
      "manual_bev": "BEV-Handbuch",
      "manual_phev": "PHEV-Handbuch",
      "manual_help": "Der Link, den die Karte unter Mehr → Handbuch öffnet. Leer = das offizielle.",
      "debug_title": "Debug-Modus",
      "debug_help": "Speichert vollständige Anfragen und Antworten (ohne persönliche Daten) in der Diagnose.",
      "save_check": "Speichern",
      "unsaved_settings": "Es gibt ungespeicherte Änderungen.",
      "error_pin_required": "Gib die PIN ein.",
      "error_pin_invalid": "Die PIN ist nicht korrekt. Es ist die der offiziellen Deepal-App, mit demselben Konto.",
      "error_pin_rate_limited": "Zu viele PIN-Versuche. Warte ein paar Minuten, bevor du es erneut versuchst.",
      "error_cannot_connect": "Keine Verbindung zu Deepal. Versuche es später erneut.",
      "error_invalid_url": "Der Handbuch-Link ist ungültig: Er muss mit http:// oder https:// beginnen.",
      "error_unknown_model": "Dieses Modell ist nicht im Katalog.",
      "close": "Schließen",
      "other": "Andere",
      "history": "Verlauf",
      "manual": "Handbuch",
      "copied": "Kopiert: {text}",
      "form_maintenance": "Wartung einrichten",
      "form_itv": "ITV einrichten",
      "form_insurance": "Versicherung einrichten",
      "form_maintenance_off": "Deaktiviert: Ihre Entitäten, ihre Anzeige auf der Karte und ihre Benachrichtigungen werden entfernt. Der Verlauf geht verloren.",
      "form_itv_off": "Deaktiviert: Ihre Entitäten, ihre Anzeige auf der Karte und ihre Benachrichtigungen werden entfernt.",
      "form_insurance_off": "Deaktiviert: Ihre Entitäten, ihre Anzeige auf der Karte und ihre Benachrichtigungen werden entfernt.",
      "first_notice": "Erste Benachrichtigung {days} Tage vorher",
      "mt_last": "Letzte Wartung",
      "mt_last_help": "Wenn das Fahrzeug noch keine hatte, gib das Zulassungsdatum und 0 km ein.",
      "mt_next_is": "Die nächste ist die {number}. Wartung.",
      "mt_km_then": "Kilometer damals",
      "mt_use_odometer": "Aktuellen Stand des Fahrzeugs verwenden ({km} km)",
      "mt_every": "Wie oft",
      "mt_every_help": "Das Handbuch verlangt ein kürzeres Intervall bei häufigen Kurzstrecken, Staub, Schlamm, extremer Kälte oder Salz.",
      "mt_interval_manual": "Laut Handbuch",
      "mt_interval_value": "{km} km oder {months} Monate",
      "mt_interval_other": "Du wählst",
      "mt_preview": "Nächste Wartung: {date} oder bei {km} km",
      "mt_whichever": "Je nachdem, was zuerst eintritt: am {date} oder bei {km} km.",
      "by_time": "Nach Zeit",
      "by_km": "Nach Kilometern",
      "mt_km_detail": "Jetzt {now} km · fällig bei {due}",
      "mt_this_service": "Was zu dieser Wartung gehört",
      "n_operations": "{count} Arbeiten",
      "mt_no_plan": "Für dieses Modell gibt es keinen Wartungsplan im Katalog.",
      "mt_next_adds": "Bei der nächsten ({number}.) kommt hinzu",
      "mt_history_item": "{number}. Wartung · {date} · {km} km",
      "mt_no_history": "Es wurden noch keine Wartungen erfasst.",
      "itv_registration_title": "Zulassung",
      "itv_registration_help": "Sie steht im Fahrzeugschein. Daraus wird die erste ITV berechnet.",
      "itv_passed_title": "Bereits bestandene ITV",
      "itv_passed_help": "Nur wenn das Fahrzeug schon eine bestanden hat.",
      "itv_passed": "Es hat schon eine ITV bestanden",
      "itv_next_title": "Nächste ITV",
      "itv_next_rules": "Sie wird nach den Regeln des Landes des Kontos berechnet.",
      "itv_next_auto": "Berechnen lassen",
      "itv_next_manual": "Anderes Datum eintragen",
      "itv_next_manual_note": "Falls die Prüfstelle dir ein anderes genannt hat",
      "itv_preview": "Nächste ITV: {date}",
      "itv_manual_date": "Datum von Hand eingetragen",
      "itv_age": "{years} Jahre",
      "itv_none_yet": "Noch keine",
      "itv_first_at": "Die erste nach {years} Jahren",
      "itv_rules_title": "Wie oft",
      "itv_rules": "Die erste nach {first} Jahren; danach alle {interval} Jahre und ab {reduced} Jahren jedes Jahr.",
      "itv_history_item": "ITV bestanden am {date}",
      "itv_no_history": "Es wurde noch keine ITV erfasst.",
      "ins_policy_title": "Die Police",
      "ins_policy_help": "Die Policennummer und die Telefonnummern sind nur auf der Karte und im Panel zu sehen; sie erscheinen nie in der Diagnose.",
      "ins_renewal_title": "Verlängerung",
      "ins_renewal_help": "Die Versicherung verlängert sich jedes Jahr von selbst. Um zu kündigen, musst du vorher Bescheid geben.",
      "ins_renews_on": "Verlängert sich am",
      "ins_notice_days": "Tage Kündigungsfrist",
      "ins_phones_title": "Telefonnummern",
      "ins_phones_help": "Zum Anrufen mit einem Tipp, von der Karte und von hier aus.",
      "ins_preview": "Letzter Tag zum Kündigen: {date}",
      "ins_preview_passed": "Diese Frist ist abgelaufen. Sie verlängert sich am {date}.",
      "ins_dates": "Termine",
      "ins_to_cancel": "Zum Kündigen",
      "ins_to_renewal": "Bis zur Verlängerung",
      "ins_deadline_passed": "Frist abgelaufen",
      "ins_deadline_on": "Letzter Tag: {date}",
      "ins_renews_itself": "Verlängert sich von selbst am {date}",
      "ins_assistance": "Pannenhilfe",
      "read_only": "Nur Lesen: Änderungen nimmt ein Home-Assistant-Administrator vor.",
      "people": "Personen",
      "people_none": "Nicht zugewiesen",
      "people_edit": "Auswählen",
      "people_title": "Personen von {name}",
      "people_help": "Wähle, wem dieses Auto gehört. Das sind die Personen unter Einstellungen → Personen.",
      "mine": "Deins",
      "error_unknown_person": "Diese Person gibt es in Home Assistant nicht mehr.",
      "error_unauthorized": "Nur ein Administrator kann diese Änderung vornehmen.",
      "plate": "Kennzeichen"
    },
    "fr": {
      "tab_cars": "Véhicules",
      "tab_alerts": "Notifications",
      "tab_data": "Données",
      "tab_diagnostics": "Diagnostic",
      "loading": "Chargement…",
      "retry": "Réessayer",
      "no_cars": "Il n'y a aucun véhicule. Ajoutez votre compte Deepal dans Paramètres → Appareils et services.",
      "error_generic": "L'opération n'a pas abouti. Réessayez.",
      "day": "{value} jour",
      "days": "{value} jours",
      "or": " ou ",
      "not_configured": "Aucun modèle choisi",
      "sheet_verified": "Fiche vérifiée",
      "sheet_catalogue": "Fiche de catalogue",
      "battery": "Batterie",
      "range": "Autonomie",
      "odometer": "Compteur",
      "appearance": "Apparence",
      "configure": "Configurer",
      "section_charge": "Recharge",
      "section_warnings": "Témoins",
      "section_maintenance": "Entretien",
      "section_itv": "ITV",
      "section_insurance": "Assurance",
      "section_appearance": "Apparence",
      "section_people": "Personnes",
      "not_set": "Non configuré",
      "add_maintenance": "Activer l'entretien",
      "add_itv": "Ajouter l'ITV",
      "add_insurance": "Ajouter l'assurance",
      "feature_seat_heat": "Sièges chauffants",
      "feature_seat_vent": "Sièges ventilés",
      "feature_wheel_heat": "Volant chauffant",
      "feature_power_tailgate": "Hayon électrique",
      "wheel_pro": "Jantes 18\"",
      "wheel_cover": "Jantes 20\" avec enjoliveurs aéro",
      "wheel_open": "Jantes 20\" sans enjoliveurs",
      "service_number": "Entretien n° {number}",
      "overdue": "En retard",
      "left": "Il reste {parts}",
      "overdue_since": "En retard de {days}",
      "cancel_until": "Limite pour résilier : {date}",
      "renews_in": "Se renouvelle dans {days}",
      "notify_to": "Prévenir",
      "n_notices": "{count} notifications",
      "edit_threshold": "Modifier le délai",
      "accept": "Valider",
      "cancel": "Annuler",
      "unit_km": "km",
      "unit_days": "jours",
      "when_km": "à {value} km du terme",
      "when_days": "à {value} jours du terme",
      "when_days_deadline": "{value} jours avant la date limite",
      "when_maintenance_overdue": "le jour même ou quand les km sont atteints",
      "when_itv_overdue": "le jour même",
      "when_insurance_last_day": "dernier jour pour résilier",
      "when_insurance_renewed": "le jour même",
      "notice_charge_started": "Recharge démarrée",
      "notice_charge_interrupted": "Recharge interrompue",
      "notice_charge_finished": "Recharge terminée",
      "notice_warnings": "Témoins",
      "notice_tires": "Pneus",
      "notice_key_battery": "Pile de la clé faible",
      "notice_maintenance_t1": "Rappel par durée 1",
      "notice_maintenance_t2": "Rappel par durée 2",
      "notice_maintenance_t3": "Rappel par durée 3",
      "notice_maintenance_k1": "Rappel par kilométrage 1",
      "notice_maintenance_k2": "Rappel par kilométrage 2",
      "notice_maintenance_k3": "Rappel par kilométrage 3",
      "notice_maintenance_overdue": "Entretien à échéance",
      "notice_itv_t1": "Rappel 1",
      "notice_itv_t2": "Rappel 2",
      "notice_itv_t3": "Rappel 3",
      "notice_itv_overdue": "ITV à échéance",
      "notice_insurance_c1": "Rappel de résiliation 1",
      "notice_insurance_c2": "Rappel de résiliation 2",
      "notice_insurance_last_day": "Date limite de résiliation",
      "notice_insurance_r1": "Rappel de renouvellement 1",
      "notice_insurance_r2": "Rappel de renouvellement 2",
      "notice_insurance_renewed": "Assurance renouvelée",
      "unsaved": "Ce véhicule a des modifications non enregistrées.",
      "alerts_help": "Cochez qui reçoit chaque notification. Le crayon change les jours ou les kilomètres de cette notification ; les délais sont propres à ce véhicule.",
      "factory_thresholds": "Délais par défaut",
      "discard": "Abandonner",
      "save": "Enregistrer",
      "saved": "Enregistré",
      "copy_from": "Copier depuis un autre véhicule",
      "car": "Véhicule",
      "copy": "Copier",
      "error_threshold_range_limits": "Le délai doit être compris entre {low} et {high}.",
      "error_threshold_range": "Un délai est hors limites.",
      "error_threshold_order": "Les délais doivent aller du plus long au plus court : le rappel 1 avant le 2, et le 2 avant le 3.",
      "error_not_found": "Ce véhicule n'est plus dans le compte.",
      "error_invalid": "Certaines données ne sont pas valides.",
      "error_invalid_file": "Le fichier n'est pas une sauvegarde DEC Deepal, ou il est endommagé.",
      "error_newer_file": "La sauvegarde vient d'une version plus récente de l'intégration. Mettez à jour DEC Deepal et réessayez.",
      "error_empty_file": "La sauvegarde ne contient les données d'aucun véhicule.",
      "error_required": "Il manque des données.",
      "backup_title": "Sauvegarde",
      "backup_help": "Entretien, ITV, assurance et apparence de vos véhicules. Les données appartiennent au véhicule : elles ne sont pas perdues quand le compte est supprimé.",
      "download_title": "Télécharger une sauvegarde",
      "download_help": "Un fichier avec les données de tous les véhicules. Il contient le numéro de contrat et les téléphones de l'assurance : gardez-le en lieu sûr.",
      "download": "Télécharger",
      "send_title": "Envoyer la sauvegarde à un téléphone",
      "send_help": "Une notification arrive ; en la touchant, le navigateur s'ouvre et télécharge le fichier. Le lien expire dans 10 minutes.",
      "send": "Envoyer",
      "sent_to": "Notification envoyée à {device}.",
      "upload_title": "Charger une sauvegarde",
      "upload_help": "Remet les véhicules du fichier tels qu'ils y figurent. Les autres véhicules ne sont pas touchés.",
      "choose_file": "Choisir un fichier",
      "imported": "Sauvegarde chargée : {cars}.",
      "stored_title": "Données enregistrées",
      "stored_help": "Par véhicule, identifié par son VIN.",
      "stored_none": "Aucune donnée de véhicule n'est enregistrée.",
      "in_account": "Dans le compte",
      "no_account": "Sans compte",
      "no_account_note": "N'est plus dans aucun compte",
      "delete": "Supprimer",
      "delete_title": "Supprimer les données enregistrées",
      "delete_confirm": "L'entretien, l'ITV et l'assurance de {name} seront supprimés. C'est irréversible : téléchargez d'abord une sauvegarde si vous voulez les conserver.",
      "deleted": "Données supprimées.",
      "history_title": "Ce qui s'est passé",
      "history_help": "Changements, commandes et notifications depuis le dernier redémarrage. La même chose figure dans le fichier de diagnostic.",
      "history_none": "Rien à afficher pour l'instant.",
      "filter_all": "Tout",
      "filter_orders": "Commandes",
      "filter_alerts": "Notifications",
      "filter_errors": "Erreurs",
      "sheets_title": "Fiche de chaque véhicule",
      "sheets_help": "Quel équipement l'intégration suppose, et d'où elle le tient.",
      "diagnostics_file": "Diagnostic",
      "ev_alert": "Notification envoyée : {name}",
      "ev_targets": "{count} destinataires",
      "ev_wake": "Réveil du véhicule",
      "ev_command": "Commande : {name}",
      "ev_code": "code",
      "today": "Aujourd'hui",
      "yesterday": "Hier",
      "enabled": "Activé",
      "mt_services_done": "Entretiens déjà faits",
      "mt_interval_km": "Intervalle (km)",
      "mt_interval_months": "Intervalle (mois)",
      "mt_register": "Enregistrer un entretien fait",
      "mt_register_help": "Note l'entretien n° {number} de {name} et commence le décompte du suivant.",
      "date": "Date",
      "mt_km": "Kilomètres",
      "register": "Enregistrer",
      "registered": "Enregistré",
      "itv_registration": "Date d'immatriculation",
      "itv_last": "Dernière ITV passée",
      "itv_next": "Prochaine ITV (manuelle)",
      "itv_register": "Enregistrer une ITV passée",
      "itv_register_help": "Note que {name} a passé l'ITV et calcule la suivante.",
      "ins_company": "Compagnie",
      "ins_policy": "Numéro de contrat",
      "ins_kind": "Type d'assurance",
      "ins_notice": "Jours de préavis pour résilier",
      "ins_phone_assistance": "Téléphone d'assistance",
      "ins_phone_company": "Téléphone de la compagnie",
      "kind_third_party": "Au tiers",
      "kind_third_party_plus": "Tiers étendu",
      "kind_comprehensive_excess": "Tous risques avec franchise",
      "kind_comprehensive": "Tous risques sans franchise",
      "tab_settings": "Réglages",
      "appearance_title": "Apparence de {name}",
      "appearance_help": "Décide de la photo, de la vue du véhicule et de l'équipement supposé.",
      "model": "Modèle",
      "trim": "Version",
      "color": "Couleur",
      "wheels": "Jantes",
      "model_ev": "Électrique",
      "model_phev": "Hybride rechargeable",
      "trim_full": "Sièges et volant chauffants, hayon électrique",
      "trim_basic": "Sans sièges ni volant chauffants",
      "account": "Compte : {name}",
      "pin_title": "Contrôle à distance avec code PIN",
      "pin_help": "Pour verrouiller et déverrouiller, les vitres et le coffre. C'est le code PIN de l'application officielle Deepal, avec le même compte. Il vaut pour tous les véhicules du compte.",
      "pin_enabled": "Commandes avec PIN",
      "pin_enabled_help": "Sans cela, la carte montre seulement l'état des portes, des vitres et du coffre.",
      "pin": "Code PIN",
      "pin_field_help": "Il est vérifié auprès de Deepal à l'enregistrement. Laissez vide pour garder l'actuel.",
      "pin_checked": "Vérifié",
      "show_pin": "Afficher le code PIN",
      "pin_mode_title": "Comment les commandes sont utilisées",
      "mode_direct": "Direct",
      "mode_direct_help": "La commande est envoyée quand vous touchez, après confirmation. Le plus pratique.",
      "mode_armed": "Déverrouiller d'abord",
      "mode_armed_help": "Il faut d'abord activer « Déverrouiller les actions avec PIN », et cela ne dure qu'un moment. Le plus sûr.",
      "arm_seconds": "Durée du déverrouillage",
      "arm_seconds_help": "Passé ce délai, les commandes avec PIN se reverrouillent toutes seules.",
      "seconds": "{value} s",
      "arm_notify": "Prévenir au déverrouillage",
      "arm_notify_help": "Une notification dans Home Assistant chaque fois que les commandes sont autorisées.",
      "reading_title": "Lecture des données",
      "reading_help": "Comment et à quelle fréquence le véhicule est interrogé.",
      "scan_title": "Intervalle de lecture",
      "scan_help": "À quelle fréquence les données du véhicule sont lues. Des valeurs très basses peuvent amener Deepal à brider le compte.",
      "minutes": "{value} min",
      "wake_title": "Réveiller le véhicule si nécessaire",
      "wake_help": "Quand vous touchez Actualiser et avant une commande avec PIN. Jamais lors des lectures automatiques, pour protéger la batterie 12 V.",
      "manual_bev": "Manuel BEV",
      "manual_phev": "Manuel PHEV",
      "manual_help": "Le lien que la carte ouvre dans Plus → Manuel. Vide = l'officiel.",
      "debug_title": "Mode débogage",
      "debug_help": "Conserve les requêtes et réponses complètes (sans données personnelles) dans le diagnostic.",
      "save_check": "Enregistrer",
      "unsaved_settings": "Il y a des modifications non enregistrées.",
      "error_pin_required": "Saisissez le code PIN.",
      "error_pin_invalid": "Le code PIN n'est pas correct. C'est celui de l'application officielle Deepal, avec ce même compte.",
      "error_pin_rate_limited": "Trop de tentatives de code PIN. Attendez quelques minutes avant de réessayer.",
      "error_cannot_connect": "Impossible de se connecter à Deepal. Réessayez plus tard.",
      "error_invalid_url": "Le lien du manuel n'est pas valide : il doit commencer par http:// ou https://.",
      "error_unknown_model": "Ce modèle n'est pas dans le catalogue.",
      "close": "Fermer",
      "other": "Autre",
      "history": "Historique",
      "manual": "Manuel",
      "copied": "Copié : {text}",
      "form_maintenance": "Configurer l'entretien",
      "form_itv": "Configurer l'ITV",
      "form_insurance": "Configurer l'assurance",
      "form_maintenance_off": "Désactivé : ses entités, son témoin sur la carte et ses notifications sont retirés. L'historique est perdu.",
      "form_itv_off": "Désactivée : ses entités, son témoin sur la carte et ses notifications sont retirés.",
      "form_insurance_off": "Désactivée : ses entités, son témoin sur la carte et ses notifications sont retirés.",
      "first_notice": "Première notification {days} jours avant",
      "mt_last": "Dernier entretien",
      "mt_last_help": "Si le véhicule n'en a encore eu aucun, indiquez la date d'immatriculation et 0 km.",
      "mt_next_is": "Le prochain sera l'entretien n° {number}.",
      "mt_km_then": "Kilomètres à ce moment-là",
      "mt_use_odometer": "Utiliser le kilométrage actuel du véhicule ({km} km)",
      "mt_every": "À quelle fréquence",
      "mt_every_help": "Le manuel demande un intervalle plus court en cas de petits trajets répétés, de poussière, de boue, de froid extrême ou de sel.",
      "mt_interval_manual": "Celui du manuel",
      "mt_interval_value": "{km} km ou {months} mois",
      "mt_interval_other": "Vous choisissez",
      "mt_preview": "Prochain entretien : {date} ou à {km} km",
      "mt_whichever": "Au premier des deux termes atteint : le {date} ou à {km} km.",
      "by_time": "Par durée",
      "by_km": "Par kilométrage",
      "mt_km_detail": "Actuellement {now} km · prévu à {due}",
      "mt_this_service": "Ce que comprend cet entretien",
      "n_operations": "{count} opérations",
      "mt_no_plan": "Ce modèle n'a pas de plan d'entretien dans le catalogue.",
      "mt_next_adds": "Le suivant (n° {number}) ajoute",
      "mt_history_item": "Entretien n° {number} · {date} · {km} km",
      "mt_no_history": "Aucun entretien n'a encore été enregistré.",
      "itv_registration_title": "Immatriculation",
      "itv_registration_help": "Elle figure sur le certificat d'immatriculation. La première ITV est calculée à partir d'elle.",
      "itv_passed_title": "ITV déjà passées",
      "itv_passed_help": "Seulement si le véhicule en a déjà passé une.",
      "itv_passed": "Il a déjà passé une ITV",
      "itv_next_title": "Prochaine ITV",
      "itv_next_rules": "Elle est calculée avec les règles du pays du compte.",
      "itv_next_auto": "La calculer",
      "itv_next_manual": "Indiquer une autre date",
      "itv_next_manual_note": "Si le centre vous en a donné une différente",
      "itv_preview": "Prochaine ITV : {date}",
      "itv_manual_date": "date saisie à la main",
      "itv_age": "{years} ans",
      "itv_none_yet": "Aucune pour l'instant",
      "itv_first_at": "La première, à {years} ans",
      "itv_rules_title": "À quelle fréquence",
      "itv_rules": "La première à {first} ans ; ensuite tous les {interval} ans et, à partir de {reduced} ans, tous les ans.",
      "itv_history_item": "ITV passée le {date}",
      "itv_no_history": "Aucune ITV n'a encore été enregistrée.",
      "ins_policy_title": "Le contrat",
      "ins_policy_help": "Le numéro de contrat et les téléphones ne sont visibles que sur la carte et dans le panneau ; ils n'apparaissent jamais dans le diagnostic.",
      "ins_renewal_title": "Renouvellement",
      "ins_renewal_help": "L'assurance se renouvelle toute seule chaque année. Pour résilier, il faut prévenir à l'avance.",
      "ins_renews_on": "Se renouvelle le",
      "ins_notice_days": "Jours de préavis",
      "ins_phones_title": "Téléphones",
      "ins_phones_help": "Pour appeler d'un seul geste depuis la carte et depuis ici.",
      "ins_preview": "Dernier jour pour résilier : {date}",
      "ins_preview_passed": "Ce délai est dépassé. Elle se renouvelle le {date}.",
      "ins_dates": "Dates",
      "ins_to_cancel": "Pour résilier",
      "ins_to_renewal": "Avant le renouvellement",
      "ins_deadline_passed": "Délai dépassé",
      "ins_deadline_on": "Dernier jour : {date}",
      "ins_renews_itself": "Se renouvelle toute seule le {date}",
      "ins_assistance": "Assistance",
      "read_only": "Lecture seule : les modifications sont faites par un administrateur de Home Assistant.",
      "people": "Personnes",
      "people_none": "Non attribué",
      "people_edit": "Choisir",
      "people_title": "Personnes de {name}",
      "people_help": "Choisissez à qui appartient cette voiture. Ce sont les personnes de Paramètres → Personnes.",
      "mine": "À vous",
      "error_unknown_person": "Cette personne n'existe plus dans Home Assistant.",
      "error_unauthorized": "Seul un administrateur peut faire cette modification.",
      "plate": "Plaque d'immatriculation"
    },
    "nl": {
      "tab_cars": "Voertuigen",
      "tab_alerts": "Meldingen",
      "tab_data": "Gegevens",
      "tab_diagnostics": "Diagnose",
      "loading": "Laden…",
      "retry": "Opnieuw proberen",
      "no_cars": "Er zijn geen voertuigen. Voeg je Deepal-account toe via Instellingen → Apparaten en diensten.",
      "error_generic": "Dat kon niet worden voltooid. Probeer het opnieuw.",
      "day": "{value} dag",
      "days": "{value} dagen",
      "or": " of ",
      "not_configured": "Geen model gekozen",
      "sheet_verified": "Geverifieerde fiche",
      "sheet_catalogue": "Catalogusfiche",
      "battery": "Batterij",
      "range": "Actieradius",
      "odometer": "Kilometerstand",
      "appearance": "Uiterlijk",
      "configure": "Instellen",
      "section_charge": "Laden",
      "section_warnings": "Waarschuwingen",
      "section_maintenance": "Onderhoud",
      "section_itv": "ITV",
      "section_insurance": "Verzekering",
      "section_appearance": "Uiterlijk",
      "section_people": "Personen",
      "not_set": "Niet ingesteld",
      "add_maintenance": "Onderhoud inschakelen",
      "add_itv": "ITV toevoegen",
      "add_insurance": "Verzekering toevoegen",
      "feature_seat_heat": "Stoelverwarming",
      "feature_seat_vent": "Stoelventilatie",
      "feature_wheel_heat": "Stuurverwarming",
      "feature_power_tailgate": "Elektrische achterklep",
      "wheel_pro": "18\"-velgen",
      "wheel_cover": "20\"-velgen met aerokappen",
      "wheel_open": "20\"-velgen zonder kappen",
      "service_number": "{number}e beurt",
      "overdue": "Verlopen",
      "left": "Nog {parts}",
      "overdue_since": "{days} te laat",
      "cancel_until": "Opzeggen tot: {date}",
      "renews_in": "Wordt verlengd over {days}",
      "notify_to": "Melden aan",
      "n_notices": "{count} meldingen",
      "edit_threshold": "Termijn wijzigen",
      "accept": "Toepassen",
      "cancel": "Annuleren",
      "unit_km": "km",
      "unit_days": "dagen",
      "when_km": "nog {value} km",
      "when_days": "nog {value} dagen",
      "when_days_deadline": "{value} dagen vóór de uiterste datum",
      "when_maintenance_overdue": "op de dag zelf of wanneer de km bereikt zijn",
      "when_itv_overdue": "op de dag zelf",
      "when_insurance_last_day": "laatste dag om op te zeggen",
      "when_insurance_renewed": "op de dag zelf",
      "notice_charge_started": "Laden gestart",
      "notice_charge_interrupted": "Laden onderbroken",
      "notice_charge_finished": "Laden voltooid",
      "notice_warnings": "Waarschuwingslampjes",
      "notice_tires": "Banden",
      "notice_key_battery": "Batterij van de sleutel bijna leeg",
      "notice_maintenance_t1": "Melding op tijd 1",
      "notice_maintenance_t2": "Melding op tijd 2",
      "notice_maintenance_t3": "Melding op tijd 3",
      "notice_maintenance_k1": "Melding op afstand 1",
      "notice_maintenance_k2": "Melding op afstand 2",
      "notice_maintenance_k3": "Melding op afstand 3",
      "notice_maintenance_overdue": "Onderhoud bereikt",
      "notice_itv_t1": "Melding 1",
      "notice_itv_t2": "Melding 2",
      "notice_itv_t3": "Melding 3",
      "notice_itv_overdue": "ITV bereikt",
      "notice_insurance_c1": "Opzegmelding 1",
      "notice_insurance_c2": "Opzegmelding 2",
      "notice_insurance_last_day": "Uiterste opzegdatum",
      "notice_insurance_r1": "Verlengingsmelding 1",
      "notice_insurance_r2": "Verlengingsmelding 2",
      "notice_insurance_renewed": "Verzekering verlengd",
      "unsaved": "Dit voertuig heeft niet-opgeslagen wijzigingen.",
      "alerts_help": "Vink aan wie welke melding krijgt. Het potlood wijzigt de dagen of kilometers van die melding; de termijnen horen bij dit voertuig.",
      "factory_thresholds": "Standaardtermijnen",
      "discard": "Verwerpen",
      "save": "Opslaan",
      "saved": "Opgeslagen",
      "copy_from": "Kopiëren van een ander voertuig",
      "car": "Voertuig",
      "copy": "Kopiëren",
      "error_threshold_range_limits": "De termijn moet tussen {low} en {high} liggen.",
      "error_threshold_range": "Een termijn valt buiten het bereik.",
      "error_threshold_order": "De termijnen moeten van lang naar kort gaan: melding 1 vóór 2, en 2 vóór 3.",
      "error_not_found": "Dat voertuig zit niet meer in het account.",
      "error_invalid": "Sommige gegevens zijn niet geldig.",
      "error_invalid_file": "Het bestand is geen DEC Deepal-back-up, of het is beschadigd.",
      "error_newer_file": "De back-up komt uit een nieuwere versie van de integratie. Werk DEC Deepal bij en probeer het opnieuw.",
      "error_empty_file": "De back-up bevat van geen enkel voertuig gegevens.",
      "error_required": "Er ontbreken gegevens.",
      "backup_title": "Back-up",
      "backup_help": "Onderhoud, ITV, verzekering en uiterlijk van je voertuigen. De gegevens horen bij het voertuig: ze gaan niet verloren als het account wordt verwijderd.",
      "download_title": "Een back-up downloaden",
      "download_help": "Een bestand met de gegevens van alle voertuigen. Het bevat het polisnummer en de telefoonnummers van de verzekering: bewaar het op een veilige plek.",
      "download": "Downloaden",
      "send_title": "De back-up naar een telefoon sturen",
      "send_help": "Er komt een melding; als je erop tikt, opent de browser en wordt het bestand gedownload. De link verloopt over 10 minuten.",
      "send": "Versturen",
      "sent_to": "Melding verstuurd naar {device}.",
      "upload_title": "Een back-up laden",
      "upload_help": "Zet de voertuigen uit het bestand terug zoals ze erin staan. Andere voertuigen blijven ongemoeid.",
      "choose_file": "Bestand kiezen",
      "imported": "Back-up geladen: {cars}.",
      "stored_title": "Opgeslagen gegevens",
      "stored_help": "Per voertuig, herkend aan zijn VIN.",
      "stored_none": "Er zijn van geen enkel voertuig gegevens opgeslagen.",
      "in_account": "In het account",
      "no_account": "Geen account",
      "no_account_note": "Zit in geen enkel account meer",
      "delete": "Verwijderen",
      "delete_title": "Opgeslagen gegevens verwijderen",
      "delete_confirm": "Het onderhoud, de ITV en de verzekering van {name} worden verwijderd. Dit kan niet ongedaan worden gemaakt: download eerst een back-up als je ze wilt bewaren.",
      "deleted": "Gegevens verwijderd.",
      "history_title": "Wat er is gebeurd",
      "history_help": "Wijzigingen, opdrachten en meldingen sinds de laatste herstart. Hetzelfde staat in het diagnosebestand.",
      "history_none": "Nog niets om te tonen.",
      "filter_all": "Alles",
      "filter_orders": "Opdrachten",
      "filter_alerts": "Meldingen",
      "filter_errors": "Fouten",
      "sheets_title": "Fiche van elk voertuig",
      "sheets_help": "Welke uitrusting de integratie aanneemt, en waar ze dat vandaan haalt.",
      "diagnostics_file": "Diagnose",
      "ev_alert": "Melding verstuurd: {name}",
      "ev_targets": "{count} ontvangers",
      "ev_wake": "Voertuig gewekt",
      "ev_command": "Opdracht: {name}",
      "ev_code": "code",
      "today": "Vandaag",
      "yesterday": "Gisteren",
      "enabled": "Ingeschakeld",
      "mt_services_done": "Reeds uitgevoerde beurten",
      "mt_interval_km": "Interval (km)",
      "mt_interval_months": "Interval (maanden)",
      "mt_register": "Uitgevoerde beurt registreren",
      "mt_register_help": "Noteert de {number}e beurt van {name} en begint te tellen voor de volgende.",
      "date": "Datum",
      "mt_km": "Kilometers",
      "register": "Registreren",
      "registered": "Geregistreerd",
      "itv_registration": "Registratiedatum",
      "itv_last": "Laatste doorstane ITV",
      "itv_next": "Volgende ITV (handmatig)",
      "itv_register": "Doorstane ITV registreren",
      "itv_register_help": "Noteert dat {name} de ITV heeft doorstaan en berekent de volgende.",
      "ins_company": "Maatschappij",
      "ins_policy": "Polisnummer",
      "ins_kind": "Soort verzekering",
      "ins_notice": "Opzegtermijn in dagen",
      "ins_phone_assistance": "Telefoon pechhulp",
      "ins_phone_company": "Telefoon maatschappij",
      "kind_third_party": "WA",
      "kind_third_party_plus": "WA beperkt casco",
      "kind_comprehensive_excess": "Allrisk met eigen risico",
      "kind_comprehensive": "Allrisk zonder eigen risico",
      "tab_settings": "Instellingen",
      "appearance_title": "Uiterlijk van {name}",
      "appearance_help": "Bepaalt de foto, het aanzicht van het voertuig en welke uitrusting wordt aangenomen.",
      "model": "Model",
      "trim": "Uitvoering",
      "color": "Kleur",
      "wheels": "Velgen",
      "model_ev": "Elektrisch",
      "model_phev": "Plug-in hybride",
      "trim_full": "Stoel- en stuurverwarming, elektrische achterklep",
      "trim_basic": "Zonder stoel- en stuurverwarming",
      "account": "Account: {name}",
      "pin_title": "Afstandsbediening met pincode",
      "pin_help": "Voor vergrendelen en ontgrendelen, ramen en kofferbak. Het is de pincode van de officiële Deepal-app, met hetzelfde account. Hij geldt voor alle voertuigen van het account.",
      "pin_enabled": "Pincode-opdrachten",
      "pin_enabled_help": "Zonder dit toont de kaart alleen de toestand van portieren, ramen en kofferbak.",
      "pin": "Pincode",
      "pin_field_help": "Hij wordt bij het opslaan bij Deepal gecontroleerd. Laat leeg om de huidige te behouden.",
      "pin_checked": "Gecontroleerd",
      "show_pin": "Pincode tonen",
      "pin_mode_title": "Hoe opdrachten worden gebruikt",
      "mode_direct": "Direct",
      "mode_direct_help": "De opdracht wordt verstuurd als je tikt, na een bevestiging. Het handigst.",
      "mode_armed": "Eerst ontgrendelen",
      "mode_armed_help": "Je moet eerst ‘Pincode-acties ontgrendelen’ inschakelen, en dat duurt maar even. Het veiligst.",
      "arm_seconds": "Hoe lang de ontgrendeling duurt",
      "arm_seconds_help": "Na die tijd vergrendelen de pincode-opdrachten vanzelf weer.",
      "seconds": "{value} s",
      "arm_notify": "Melden bij ontgrendelen",
      "arm_notify_help": "Een melding in Home Assistant telkens wanneer opdrachten worden toegestaan.",
      "reading_title": "Gegevens uitlezen",
      "reading_help": "Hoe en hoe vaak het voertuig wordt bevraagd.",
      "scan_title": "Uitleesinterval",
      "scan_help": "Hoe vaak de voertuiggegevens worden gelezen. Bij heel lage waarden kan Deepal het account afknijpen.",
      "minutes": "{value} min",
      "wake_title": "Voertuig wekken als dat nodig is",
      "wake_help": "Wanneer je op Vernieuwen tikt en vóór een pincode-opdracht. Nooit bij automatische uitlezingen, om de 12V-accu te sparen.",
      "manual_bev": "BEV-handleiding",
      "manual_phev": "PHEV-handleiding",
      "manual_help": "De link die de kaart opent onder Meer → Handleiding. Leeg = de officiële.",
      "debug_title": "Debugmodus",
      "debug_help": "Bewaart volledige verzoeken en antwoorden (zonder persoonsgegevens) in de diagnose.",
      "save_check": "Opslaan",
      "unsaved_settings": "Er zijn niet-opgeslagen wijzigingen.",
      "error_pin_required": "Voer de pincode in.",
      "error_pin_invalid": "De pincode is niet juist. Het is die van de officiële Deepal-app, met ditzelfde account.",
      "error_pin_rate_limited": "Te veel pincodepogingen. Wacht een paar minuten voordat je het opnieuw probeert.",
      "error_cannot_connect": "Kan geen verbinding maken met Deepal. Probeer het later opnieuw.",
      "error_invalid_url": "De link naar de handleiding is niet geldig: hij moet beginnen met http:// of https://.",
      "error_unknown_model": "Dat model staat niet in de catalogus.",
      "close": "Sluiten",
      "other": "Anders",
      "history": "Geschiedenis",
      "manual": "Handleiding",
      "copied": "Gekopieerd: {text}",
      "form_maintenance": "Onderhoud instellen",
      "form_itv": "ITV instellen",
      "form_insurance": "Verzekering instellen",
      "form_maintenance_off": "Uitgeschakeld: de entiteiten, het lampje op de kaart en de meldingen worden verwijderd. De geschiedenis gaat verloren.",
      "form_itv_off": "Uitgeschakeld: de entiteiten, het lampje op de kaart en de meldingen worden verwijderd.",
      "form_insurance_off": "Uitgeschakeld: de entiteiten, het lampje op de kaart en de meldingen worden verwijderd.",
      "first_notice": "Eerste melding {days} dagen ervoor",
      "mt_last": "Laatste beurt",
      "mt_last_help": "Heeft het voertuig er nog geen gehad, vul dan de registratiedatum en 0 km in.",
      "mt_next_is": "De volgende wordt de {number}e beurt.",
      "mt_km_then": "Kilometers toen",
      "mt_use_odometer": "De huidige stand van het voertuig gebruiken ({km} km)",
      "mt_every": "Hoe vaak",
      "mt_every_help": "De handleiding vraagt een korter interval bij veel korte ritten, stof, modder, extreme kou of zout.",
      "mt_interval_manual": "Volgens de handleiding",
      "mt_interval_value": "{km} km of {months} maanden",
      "mt_interval_other": "Kies je zelf",
      "mt_preview": "Volgende beurt: {date} of bij {km} km",
      "mt_whichever": "Wat het eerst komt: op {date} of bij {km} km.",
      "by_time": "Op tijd",
      "by_km": "Op afstand",
      "mt_km_detail": "Nu {now} km · beurt bij {due}",
      "mt_this_service": "Wat bij deze beurt hoort",
      "n_operations": "{count} werkzaamheden",
      "mt_no_plan": "Dit model heeft geen onderhoudsplan in de catalogus.",
      "mt_next_adds": "Bij de volgende ({number}e) komt erbij",
      "mt_history_item": "{number}e beurt · {date} · {km} km",
      "mt_no_history": "Er zijn nog geen beurten geregistreerd.",
      "itv_registration_title": "Registratie",
      "itv_registration_help": "Ze staat op het kentekenbewijs. Daarmee wordt de eerste ITV berekend.",
      "itv_passed_title": "Reeds doorstane ITV's",
      "itv_passed_help": "Alleen als het voertuig er al een heeft doorstaan.",
      "itv_passed": "Het heeft al een ITV doorstaan",
      "itv_next_title": "Volgende ITV",
      "itv_next_rules": "Ze wordt berekend volgens de regels van het land van het account.",
      "itv_next_auto": "Laten berekenen",
      "itv_next_manual": "Een andere datum invullen",
      "itv_next_manual_note": "Als het keuringsstation je een andere gaf",
      "itv_preview": "Volgende ITV: {date}",
      "itv_manual_date": "datum met de hand ingevuld",
      "itv_age": "{years} jaar",
      "itv_none_yet": "Nog geen",
      "itv_first_at": "De eerste na {years} jaar",
      "itv_rules_title": "Hoe vaak",
      "itv_rules": "De eerste na {first} jaar; daarna om de {interval} jaar en vanaf {reduced} jaar elk jaar.",
      "itv_history_item": "ITV doorstaan op {date}",
      "itv_no_history": "Er is nog geen ITV geregistreerd.",
      "ins_policy_title": "De polis",
      "ins_policy_help": "Het polisnummer en de telefoonnummers zijn alleen te zien op de kaart en in het paneel; ze komen nooit in de diagnose.",
      "ins_renewal_title": "Verlenging",
      "ins_renewal_help": "De verzekering wordt elk jaar vanzelf verlengd. Om op te zeggen moet je dat vooraf melden.",
      "ins_renews_on": "Wordt verlengd op",
      "ins_notice_days": "Dagen opzegtermijn",
      "ins_phones_title": "Telefoonnummers",
      "ins_phones_help": "Om met één tik te bellen, vanaf de kaart en vanaf hier.",
      "ins_preview": "Laatste dag om op te zeggen: {date}",
      "ins_preview_passed": "Die termijn is verstreken. Ze wordt verlengd op {date}.",
      "ins_dates": "Datums",
      "ins_to_cancel": "Om op te zeggen",
      "ins_to_renewal": "Tot de verlenging",
      "ins_deadline_passed": "Termijn verstreken",
      "ins_deadline_on": "Laatste dag: {date}",
      "ins_renews_itself": "Wordt vanzelf verlengd op {date}",
      "ins_assistance": "Pechhulp",
      "read_only": "Alleen lezen: wijzigingen worden gedaan door een beheerder van Home Assistant.",
      "people": "Personen",
      "people_none": "Niet toegewezen",
      "people_edit": "Kiezen",
      "people_title": "Personen van {name}",
      "people_help": "Kies van wie deze auto is. Dit zijn de personen in Instellingen → Personen.",
      "mine": "Van jou",
      "error_unknown_person": "Die persoon bestaat niet meer in Home Assistant.",
      "error_unauthorized": "Alleen een beheerder kan deze wijziging doen.",
      "plate": "Kenteken"
    },
    "nb": {
      "tab_cars": "Kjøretøy",
      "tab_alerts": "Varsler",
      "tab_data": "Data",
      "tab_diagnostics": "Diagnostikk",
      "loading": "Laster…",
      "retry": "Prøv igjen",
      "no_cars": "Det er ingen kjøretøy. Legg til Deepal-kontoen din under Innstillinger → Enheter og tjenester.",
      "error_generic": "Det kunne ikke fullføres. Prøv igjen.",
      "day": "{value} dag",
      "days": "{value} dager",
      "or": " eller ",
      "not_configured": "Ingen modell valgt",
      "sheet_verified": "Verifisert datablad",
      "sheet_catalogue": "Datablad fra katalogen",
      "battery": "Batteri",
      "range": "Rekkevidde",
      "odometer": "Kilometerstand",
      "appearance": "Utseende",
      "configure": "Konfigurer",
      "section_charge": "Lading",
      "section_warnings": "Varsellamper",
      "section_maintenance": "Service",
      "section_itv": "ITV",
      "section_insurance": "Forsikring",
      "section_appearance": "Utseende",
      "section_people": "Personer",
      "not_set": "Ikke satt opp",
      "add_maintenance": "Aktiver service",
      "add_itv": "Legg til ITV",
      "add_insurance": "Legg til forsikring",
      "feature_seat_heat": "Setevarme",
      "feature_seat_vent": "Seteventilasjon",
      "feature_wheel_heat": "Rattvarme",
      "feature_power_tailgate": "Elektrisk bakluke",
      "wheel_pro": "18\"-felger",
      "wheel_cover": "20\"-felger med aerodeksler",
      "wheel_open": "20\"-felger uten deksler",
      "service_number": "{number}. service",
      "overdue": "Forfalt",
      "left": "{parts} igjen",
      "overdue_since": "Forfalt for {days} siden",
      "cancel_until": "Frist for oppsigelse: {date}",
      "renews_in": "Fornyes om {days}",
      "notify_to": "Varsle",
      "n_notices": "{count} varsler",
      "edit_threshold": "Endre fristen",
      "accept": "Godta",
      "cancel": "Avbryt",
      "unit_km": "km",
      "unit_days": "dager",
      "when_km": "{value} km igjen",
      "when_days": "{value} dager igjen",
      "when_days_deadline": "{value} dager før fristen",
      "when_maintenance_overdue": "på dagen eller når km er nådd",
      "when_itv_overdue": "på dagen",
      "when_insurance_last_day": "siste dag for å si opp",
      "when_insurance_renewed": "på dagen",
      "notice_charge_started": "Lading startet",
      "notice_charge_interrupted": "Lading avbrutt",
      "notice_charge_finished": "Lading ferdig",
      "notice_warnings": "Varsellamper",
      "notice_tires": "Dekk",
      "notice_key_battery": "Lavt batteri i nøkkelen",
      "notice_maintenance_t1": "Tidsvarsel 1",
      "notice_maintenance_t2": "Tidsvarsel 2",
      "notice_maintenance_t3": "Tidsvarsel 3",
      "notice_maintenance_k1": "Kilometervarsel 1",
      "notice_maintenance_k2": "Kilometervarsel 2",
      "notice_maintenance_k3": "Kilometervarsel 3",
      "notice_maintenance_overdue": "Service forfalt",
      "notice_itv_t1": "Varsel 1",
      "notice_itv_t2": "Varsel 2",
      "notice_itv_t3": "Varsel 3",
      "notice_itv_overdue": "ITV forfalt",
      "notice_insurance_c1": "Oppsigelsesvarsel 1",
      "notice_insurance_c2": "Oppsigelsesvarsel 2",
      "notice_insurance_last_day": "Oppsigelsesfrist",
      "notice_insurance_r1": "Fornyelsesvarsel 1",
      "notice_insurance_r2": "Fornyelsesvarsel 2",
      "notice_insurance_renewed": "Forsikring fornyet",
      "unsaved": "Dette kjøretøyet har endringer som ikke er lagret.",
      "alerts_help": "Kryss av for hvem som får hvert varsel. Blyanten endrer dagene eller kilometerne for det varselet; fristene gjelder dette kjøretøyet.",
      "factory_thresholds": "Standardfrister",
      "discard": "Forkast",
      "save": "Lagre",
      "saved": "Lagret",
      "copy_from": "Kopier fra et annet kjøretøy",
      "car": "Kjøretøy",
      "copy": "Kopier",
      "error_threshold_range_limits": "Fristen må være mellom {low} og {high}.",
      "error_threshold_range": "En frist er utenfor området.",
      "error_threshold_order": "Fristene må gå fra lengst til kortest: varsel 1 før 2, og 2 før 3.",
      "error_not_found": "Det kjøretøyet er ikke lenger i kontoen.",
      "error_invalid": "Noen av opplysningene er ikke gyldige.",
      "error_invalid_file": "Filen er ikke en DEC Deepal-sikkerhetskopi, eller den er skadet.",
      "error_newer_file": "Sikkerhetskopien kommer fra en nyere versjon av integrasjonen. Oppdater DEC Deepal og prøv igjen.",
      "error_empty_file": "Sikkerhetskopien har ikke data for noe kjøretøy.",
      "error_required": "Det mangler opplysninger.",
      "backup_title": "Sikkerhetskopi",
      "backup_help": "Service, ITV, forsikring og utseende for kjøretøyene dine. Dataene tilhører kjøretøyet: de går ikke tapt når kontoen fjernes.",
      "download_title": "Last ned en sikkerhetskopi",
      "download_help": "En fil med dataene for alle kjøretøy. Den inneholder polisenummeret og telefonnumrene til forsikringen: oppbevar den trygt.",
      "download": "Last ned",
      "send_title": "Send sikkerhetskopien til en telefon",
      "send_help": "Det kommer et varsel; når du trykker på det, åpnes nettleseren og filen lastes ned. Lenken utløper om 10 minutter.",
      "send": "Send",
      "sent_to": "Varsel sendt til {device}.",
      "upload_title": "Last inn en sikkerhetskopi",
      "upload_help": "Setter kjøretøyene i filen tilbake slik de står der. Andre kjøretøy røres ikke.",
      "choose_file": "Velg fil",
      "imported": "Sikkerhetskopi lastet: {cars}.",
      "stored_title": "Lagrede data",
      "stored_help": "Per kjøretøy, identifisert med VIN.",
      "stored_none": "Det er ikke lagret data for noe kjøretøy.",
      "in_account": "I kontoen",
      "no_account": "Ingen konto",
      "no_account_note": "Ikke lenger i noen konto",
      "delete": "Slett",
      "delete_title": "Slett lagrede data",
      "delete_confirm": "Service, ITV og forsikring for {name} blir slettet. Dette kan ikke angres: last ned en sikkerhetskopi først hvis du vil beholde dem.",
      "deleted": "Data slettet.",
      "history_title": "Hva som har skjedd",
      "history_help": "Endringer, kommandoer og varsler siden siste omstart. Det samme havner i diagnostikkfilen.",
      "history_none": "Ingenting å vise ennå.",
      "filter_all": "Alle",
      "filter_orders": "Kommandoer",
      "filter_alerts": "Varsler",
      "filter_errors": "Feil",
      "sheets_title": "Datablad for hvert kjøretøy",
      "sheets_help": "Hvilket utstyr integrasjonen antar, og hvor den har det fra.",
      "diagnostics_file": "Diagnostikk",
      "ev_alert": "Varsel sendt: {name}",
      "ev_targets": "{count} mottakere",
      "ev_wake": "Kjøretøyet vekket",
      "ev_command": "Kommando: {name}",
      "ev_code": "kode",
      "today": "I dag",
      "yesterday": "I går",
      "enabled": "Aktivert",
      "mt_services_done": "Servicer som allerede er tatt",
      "mt_interval_km": "Intervall (km)",
      "mt_interval_months": "Intervall (måneder)",
      "mt_register": "Registrer utført service",
      "mt_register_help": "Noterer {number}. service for {name} og begynner å telle mot den neste.",
      "date": "Dato",
      "mt_km": "Kilometer",
      "register": "Registrer",
      "registered": "Registrert",
      "itv_registration": "Registreringsdato",
      "itv_last": "Siste beståtte ITV",
      "itv_next": "Neste ITV (manuell)",
      "itv_register": "Registrer bestått ITV",
      "itv_register_help": "Noterer at {name} har bestått ITV, og beregner den neste.",
      "ins_company": "Selskap",
      "ins_policy": "Polisenummer",
      "ins_kind": "Type forsikring",
      "ins_notice": "Dagers varsel for oppsigelse",
      "ins_phone_assistance": "Telefon veihjelp",
      "ins_phone_company": "Telefon selskap",
      "kind_third_party": "Ansvar",
      "kind_third_party_plus": "Delkasko",
      "kind_comprehensive_excess": "Kasko med egenandel",
      "kind_comprehensive": "Kasko uten egenandel",
      "tab_settings": "Innstillinger",
      "appearance_title": "Utseende for {name}",
      "appearance_help": "Bestemmer bildet, visningen av kjøretøyet og hvilket utstyr som antas.",
      "model": "Modell",
      "trim": "Versjon",
      "color": "Farge",
      "wheels": "Felger",
      "model_ev": "Elektrisk",
      "model_phev": "Ladbar hybrid",
      "trim_full": "Sete- og rattvarme, elektrisk bakluke",
      "trim_basic": "Uten sete- og rattvarme",
      "account": "Konto: {name}",
      "pin_title": "Fjernstyring med PIN",
      "pin_help": "For å låse og låse opp, vinduer og bagasjerom. Det er PIN-koden fra den offisielle Deepal-appen, med samme konto. Den gjelder alle kjøretøy i kontoen.",
      "pin_enabled": "PIN-kommandoer",
      "pin_enabled_help": "Uten dette viser kortet bare tilstanden til dører, vinduer og bagasjerom.",
      "pin": "PIN",
      "pin_field_help": "Den sjekkes mot Deepal ved lagring. La stå tomt for å beholde den nåværende.",
      "pin_checked": "Sjekket",
      "show_pin": "Vis PIN-koden",
      "pin_mode_title": "Hvordan kommandoer brukes",
      "mode_direct": "Direkte",
      "mode_direct_help": "Kommandoen sendes når du trykker, etter bekreftelse. Det mest praktiske.",
      "mode_armed": "Lås opp først",
      "mode_armed_help": "Du må først aktivere «Lås opp PIN-handlinger», og det varer bare en stund. Det tryggeste.",
      "arm_seconds": "Hvor lenge opplåsingen varer",
      "arm_seconds_help": "Etter den tiden låses PIN-kommandoene av seg selv igjen.",
      "seconds": "{value} s",
      "arm_notify": "Varsle ved opplåsing",
      "arm_notify_help": "Et varsel i Home Assistant hver gang kommandoer tillates.",
      "reading_title": "Datalesing",
      "reading_help": "Hvordan og hvor ofte kjøretøyet spørres.",
      "scan_title": "Leseintervall",
      "scan_help": "Hvor ofte kjøretøydataene leses. Svært lave verdier kan få Deepal til å strupe kontoen.",
      "minutes": "{value} min",
      "wake_title": "Vekk kjøretøyet ved behov",
      "wake_help": "Når du trykker Oppdater og før en PIN-kommando. Aldri ved automatiske lesinger, for å skåne 12 V-batteriet.",
      "manual_bev": "BEV-håndbok",
      "manual_phev": "PHEV-håndbok",
      "manual_help": "Lenken kortet åpner under Mer → Håndbok. Tomt = den offisielle.",
      "debug_title": "Feilsøkingsmodus",
      "debug_help": "Lagrer fullstendige forespørsler og svar (uten personopplysninger) i diagnostikken.",
      "save_check": "Lagre",
      "unsaved_settings": "Det er endringer som ikke er lagret.",
      "error_pin_required": "Skriv inn PIN-koden.",
      "error_pin_invalid": "PIN-koden er ikke riktig. Det er den fra den offisielle Deepal-appen, med denne samme kontoen.",
      "error_pin_rate_limited": "For mange PIN-forsøk. Vent noen minutter før du prøver igjen.",
      "error_cannot_connect": "Kunne ikke koble til Deepal. Prøv igjen senere.",
      "error_invalid_url": "Lenken til håndboken er ikke gyldig: den må begynne med http:// eller https://.",
      "error_unknown_model": "Den modellen finnes ikke i katalogen.",
      "close": "Lukk",
      "other": "Annet",
      "history": "Historikk",
      "manual": "Håndbok",
      "copied": "Kopiert: {text}",
      "form_maintenance": "Sett opp service",
      "form_itv": "Sett opp ITV",
      "form_insurance": "Sett opp forsikring",
      "form_maintenance_off": "Deaktivert: entitetene, lampen på kortet og varslene fjernes. Historikken går tapt.",
      "form_itv_off": "Deaktivert: entitetene, lampen på kortet og varslene fjernes.",
      "form_insurance_off": "Deaktivert: entitetene, lampen på kortet og varslene fjernes.",
      "first_notice": "Første varsel {days} dager før",
      "mt_last": "Siste service",
      "mt_last_help": "Hvis kjøretøyet ikke har hatt noen ennå, legg inn registreringsdatoen og 0 km.",
      "mt_next_is": "Den neste blir {number}. service.",
      "mt_km_then": "Kilometer den gangen",
      "mt_use_odometer": "Bruk kjøretøyets nåværende stand ({km} km)",
      "mt_every": "Hvor ofte",
      "mt_every_help": "Håndboken ber om kortere intervall ved gjentatte korte turer, støv, gjørme, ekstrem kulde eller salt.",
      "mt_interval_manual": "Fra håndboken",
      "mt_interval_value": "{km} km eller {months} måneder",
      "mt_interval_other": "Du velger",
      "mt_preview": "Neste service: {date} eller ved {km} km",
      "mt_whichever": "Det som kommer først: {date} eller ved {km} km.",
      "by_time": "Etter tid",
      "by_km": "Etter kilometer",
      "mt_km_detail": "Nå {now} km · service ved {due}",
      "mt_this_service": "Hva denne servicen omfatter",
      "n_operations": "{count} punkter",
      "mt_no_plan": "Denne modellen har ingen serviceplan i katalogen.",
      "mt_next_adds": "I den neste ({number}.) kommer i tillegg",
      "mt_history_item": "{number}. service · {date} · {km} km",
      "mt_no_history": "Ingen servicer er registrert ennå.",
      "itv_registration_title": "Registrering",
      "itv_registration_help": "Den står i vognkortet. Første ITV beregnes ut fra den.",
      "itv_passed_title": "ITV som allerede er bestått",
      "itv_passed_help": "Bare hvis kjøretøyet allerede har bestått en.",
      "itv_passed": "Det har allerede bestått en ITV",
      "itv_next_title": "Neste ITV",
      "itv_next_rules": "Den beregnes etter reglene i kontoens land.",
      "itv_next_auto": "Beregn den",
      "itv_next_manual": "Sett en annen dato",
      "itv_next_manual_note": "Hvis stasjonen ga deg en annen",
      "itv_preview": "Neste ITV: {date}",
      "itv_manual_date": "dato satt for hånd",
      "itv_age": "{years} år",
      "itv_none_yet": "Ingen ennå",
      "itv_first_at": "Den første etter {years} år",
      "itv_rules_title": "Hvor ofte",
      "itv_rules": "Den første etter {first} år; deretter hvert {interval}. år og, fra {reduced} år, hvert år.",
      "itv_history_item": "ITV bestått {date}",
      "itv_no_history": "Ingen ITV er registrert ennå.",
      "ins_policy_title": "Polisen",
      "ins_policy_help": "Polisenummeret og telefonnumrene vises bare på kortet og i panelet; de kommer aldri med i diagnostikken.",
      "ins_renewal_title": "Fornyelse",
      "ins_renewal_help": "Forsikringen fornyes av seg selv hvert år. For å si opp må du gi beskjed på forhånd.",
      "ins_renews_on": "Fornyes",
      "ins_notice_days": "Dagers varsel",
      "ins_phones_title": "Telefonnumre",
      "ins_phones_help": "For å ringe med ett trykk fra kortet og herfra.",
      "ins_preview": "Siste dag for å si opp: {date}",
      "ins_preview_passed": "Den fristen er ute. Den fornyes {date}.",
      "ins_dates": "Datoer",
      "ins_to_cancel": "Til å si opp",
      "ins_to_renewal": "Til fornyelsen",
      "ins_deadline_passed": "Fristen er ute",
      "ins_deadline_on": "Siste dag: {date}",
      "ins_renews_itself": "Fornyes av seg selv {date}",
      "ins_assistance": "Veihjelp",
      "read_only": "Kun lesing: endringer gjøres av en administrator i Home Assistant.",
      "people": "Personer",
      "people_none": "Ikke tildelt",
      "people_edit": "Velg",
      "people_title": "Personer for {name}",
      "people_help": "Velg hvem denne bilen tilhører. Det er personene i Innstillinger → Personer.",
      "mine": "Din",
      "error_unknown_person": "Den personen finnes ikke lenger i Home Assistant.",
      "error_unauthorized": "Bare en administrator kan gjøre denne endringen.",
      "plate": "Registreringsnummer"
    },
    "da": {
      "tab_cars": "Køretøjer",
      "tab_alerts": "Notifikationer",
      "tab_data": "Data",
      "tab_diagnostics": "Diagnostik",
      "loading": "Indlæser…",
      "retry": "Prøv igen",
      "no_cars": "Der er ingen køretøjer. Tilføj din Deepal-konto under Indstillinger → Enheder og tjenester.",
      "error_generic": "Det kunne ikke gennemføres. Prøv igen.",
      "day": "{value} dag",
      "days": "{value} dage",
      "or": " eller ",
      "not_configured": "Ingen model valgt",
      "sheet_verified": "Verificeret datablad",
      "sheet_catalogue": "Datablad fra kataloget",
      "battery": "Batteri",
      "range": "Rækkevidde",
      "odometer": "Kilometerstand",
      "appearance": "Udseende",
      "configure": "Konfigurer",
      "section_charge": "Opladning",
      "section_warnings": "Advarselslamper",
      "section_maintenance": "Service",
      "section_itv": "ITV",
      "section_insurance": "Forsikring",
      "section_appearance": "Udseende",
      "section_people": "Personer",
      "not_set": "Ikke sat op",
      "add_maintenance": "Aktivér service",
      "add_itv": "Tilføj ITV",
      "add_insurance": "Tilføj forsikring",
      "feature_seat_heat": "Sædevarme",
      "feature_seat_vent": "Sædeventilation",
      "feature_wheel_heat": "Ratvarme",
      "feature_power_tailgate": "Elektrisk bagklap",
      "wheel_pro": "18\"-fælge",
      "wheel_cover": "20\"-fælge med aerokapsler",
      "wheel_open": "20\"-fælge uden kapsler",
      "service_number": "{number}. service",
      "overdue": "Overskredet",
      "left": "{parts} tilbage",
      "overdue_since": "Overskredet med {days}",
      "cancel_until": "Frist for opsigelse: {date}",
      "renews_in": "Fornyes om {days}",
      "notify_to": "Giv besked til",
      "n_notices": "{count} notifikationer",
      "edit_threshold": "Ændr fristen",
      "accept": "Acceptér",
      "cancel": "Annuller",
      "unit_km": "km",
      "unit_days": "dage",
      "when_km": "{value} km tilbage",
      "when_days": "{value} dage tilbage",
      "when_days_deadline": "{value} dage før fristen",
      "when_maintenance_overdue": "på dagen, eller når km er nået",
      "when_itv_overdue": "på dagen",
      "when_insurance_last_day": "sidste dag for opsigelse",
      "when_insurance_renewed": "på dagen",
      "notice_charge_started": "Opladning startet",
      "notice_charge_interrupted": "Opladning afbrudt",
      "notice_charge_finished": "Opladning færdig",
      "notice_warnings": "Advarselslamper",
      "notice_tires": "Dæk",
      "notice_key_battery": "Lavt batteri i nøglen",
      "notice_maintenance_t1": "Tidspåmindelse 1",
      "notice_maintenance_t2": "Tidspåmindelse 2",
      "notice_maintenance_t3": "Tidspåmindelse 3",
      "notice_maintenance_k1": "Kilometerpåmindelse 1",
      "notice_maintenance_k2": "Kilometerpåmindelse 2",
      "notice_maintenance_k3": "Kilometerpåmindelse 3",
      "notice_maintenance_overdue": "Service forfalden",
      "notice_itv_t1": "Påmindelse 1",
      "notice_itv_t2": "Påmindelse 2",
      "notice_itv_t3": "Påmindelse 3",
      "notice_itv_overdue": "ITV forfalden",
      "notice_insurance_c1": "Opsigelsespåmindelse 1",
      "notice_insurance_c2": "Opsigelsespåmindelse 2",
      "notice_insurance_last_day": "Opsigelsesfrist",
      "notice_insurance_r1": "Fornyelsespåmindelse 1",
      "notice_insurance_r2": "Fornyelsespåmindelse 2",
      "notice_insurance_renewed": "Forsikring fornyet",
      "unsaved": "Dette køretøj har ændringer, der ikke er gemt.",
      "alerts_help": "Sæt kryds ved, hvem der får hver notifikation. Blyanten ændrer dagene eller kilometerne for den notifikation; fristerne hører til dette køretøj.",
      "factory_thresholds": "Standardfrister",
      "discard": "Kassér",
      "save": "Gem",
      "saved": "Gemt",
      "copy_from": "Kopiér fra et andet køretøj",
      "car": "Køretøj",
      "copy": "Kopiér",
      "error_threshold_range_limits": "Fristen skal være mellem {low} og {high}.",
      "error_threshold_range": "En frist er uden for området.",
      "error_threshold_order": "Fristerne skal gå fra længst til kortest: påmindelse 1 før 2, og 2 før 3.",
      "error_not_found": "Det køretøj er ikke længere i kontoen.",
      "error_invalid": "Nogle af oplysningerne er ikke gyldige.",
      "error_invalid_file": "Filen er ikke en DEC Deepal-sikkerhedskopi, eller den er beskadiget.",
      "error_newer_file": "Sikkerhedskopien kommer fra en nyere version af integrationen. Opdater DEC Deepal og prøv igen.",
      "error_empty_file": "Sikkerhedskopien har ikke data for noget køretøj.",
      "error_required": "Der mangler oplysninger.",
      "backup_title": "Sikkerhedskopi",
      "backup_help": "Service, ITV, forsikring og udseende for dine køretøjer. Dataene hører til køretøjet: de går ikke tabt, når kontoen fjernes.",
      "download_title": "Hent en sikkerhedskopi",
      "download_help": "En fil med data for alle køretøjer. Den indeholder policenummeret og forsikringens telefonnumre: opbevar den et sikkert sted.",
      "download": "Hent",
      "send_title": "Send sikkerhedskopien til en telefon",
      "send_help": "Der kommer en notifikation; når du trykker på den, åbner browseren og henter filen. Linket udløber om 10 minutter.",
      "send": "Send",
      "sent_to": "Notifikation sendt til {device}.",
      "upload_title": "Indlæs en sikkerhedskopi",
      "upload_help": "Sætter køretøjerne i filen tilbage, som de står i den. Andre køretøjer røres ikke.",
      "choose_file": "Vælg fil",
      "imported": "Sikkerhedskopi indlæst: {cars}.",
      "stored_title": "Gemte data",
      "stored_help": "Pr. køretøj, identificeret ved dets stelnummer.",
      "stored_none": "Der er ikke gemt data for noget køretøj.",
      "in_account": "I kontoen",
      "no_account": "Ingen konto",
      "no_account_note": "Ikke længere i nogen konto",
      "delete": "Slet",
      "delete_title": "Slet gemte data",
      "delete_confirm": "Service, ITV og forsikring for {name} bliver slettet. Det kan ikke fortrydes: hent en sikkerhedskopi først, hvis du vil beholde dem.",
      "deleted": "Data slettet.",
      "history_title": "Hvad der er sket",
      "history_help": "Ændringer, kommandoer og notifikationer siden sidste genstart. Det samme kommer med i diagnostikfilen.",
      "history_none": "Intet at vise endnu.",
      "filter_all": "Alle",
      "filter_orders": "Kommandoer",
      "filter_alerts": "Notifikationer",
      "filter_errors": "Fejl",
      "sheets_title": "Datablad for hvert køretøj",
      "sheets_help": "Hvilket udstyr integrationen går ud fra, og hvor den har det fra.",
      "diagnostics_file": "Diagnostik",
      "ev_alert": "Notifikation sendt: {name}",
      "ev_targets": "{count} modtagere",
      "ev_wake": "Køretøjet vækket",
      "ev_command": "Kommando: {name}",
      "ev_code": "kode",
      "today": "I dag",
      "yesterday": "I går",
      "enabled": "Aktiveret",
      "mt_services_done": "Servicer, der allerede er lavet",
      "mt_interval_km": "Interval (km)",
      "mt_interval_months": "Interval (måneder)",
      "mt_register": "Registrér udført service",
      "mt_register_help": "Noterer {number}. service for {name} og begynder at tælle mod den næste.",
      "date": "Dato",
      "mt_km": "Kilometer",
      "register": "Registrér",
      "registered": "Registreret",
      "itv_registration": "Registreringsdato",
      "itv_last": "Seneste beståede ITV",
      "itv_next": "Næste ITV (manuel)",
      "itv_register": "Registrér bestået ITV",
      "itv_register_help": "Noterer, at {name} har bestået ITV, og beregner det næste.",
      "ins_company": "Selskab",
      "ins_policy": "Policenummer",
      "ins_kind": "Type forsikring",
      "ins_notice": "Dages varsel for opsigelse",
      "ins_phone_assistance": "Telefon vejhjælp",
      "ins_phone_company": "Telefon selskab",
      "kind_third_party": "Ansvar",
      "kind_third_party_plus": "Udvidet ansvar",
      "kind_comprehensive_excess": "Kasko med selvrisiko",
      "kind_comprehensive": "Kasko uden selvrisiko",
      "tab_settings": "Indstillinger",
      "appearance_title": "Udseende for {name}",
      "appearance_help": "Bestemmer billedet, visningen af køretøjet, og hvilket udstyr der antages.",
      "model": "Model",
      "trim": "Version",
      "color": "Farve",
      "wheels": "Fælge",
      "model_ev": "Elektrisk",
      "model_phev": "Plug-in-hybrid",
      "trim_full": "Sæde- og ratvarme, elektrisk bagklap",
      "trim_basic": "Uden sæde- og ratvarme",
      "account": "Konto: {name}",
      "pin_title": "Fjernbetjening med pinkode",
      "pin_help": "Til at låse og låse op, ruder og bagagerum. Det er pinkoden fra den officielle Deepal-app, med samme konto. Den gælder for alle køretøjer i kontoen.",
      "pin_enabled": "Pinkodekommandoer",
      "pin_enabled_help": "Uden dette viser kortet kun tilstanden for døre, ruder og bagagerum.",
      "pin": "Pinkode",
      "pin_field_help": "Den tjekkes hos Deepal, når du gemmer. Lad feltet stå tomt for at beholde den nuværende.",
      "pin_checked": "Tjekket",
      "show_pin": "Vis pinkoden",
      "pin_mode_title": "Hvordan kommandoer bruges",
      "mode_direct": "Direkte",
      "mode_direct_help": "Kommandoen sendes, når du trykker, efter bekræftelse. Det nemmeste.",
      "mode_armed": "Lås op først",
      "mode_armed_help": "Du skal først aktivere »Lås pinkodehandlinger op«, og det varer kun et stykke tid. Det sikreste.",
      "arm_seconds": "Hvor længe oplåsningen varer",
      "arm_seconds_help": "Efter den tid låses pinkodekommandoerne af sig selv igen.",
      "seconds": "{value} s",
      "arm_notify": "Giv besked ved oplåsning",
      "arm_notify_help": "En notifikation i Home Assistant, hver gang kommandoer tillades.",
      "reading_title": "Dataaflæsning",
      "reading_help": "Hvordan og hvor ofte køretøjet spørges.",
      "scan_title": "Aflæsningsinterval",
      "scan_help": "Hvor ofte køretøjets data læses. Meget lave værdier kan få Deepal til at drosle kontoen.",
      "minutes": "{value} min",
      "wake_title": "Væk køretøjet efter behov",
      "wake_help": "Når du trykker Opdater, og før en pinkodekommando. Aldrig ved automatiske aflæsninger, for at skåne 12 V-batteriet.",
      "manual_bev": "BEV-instruktionsbog",
      "manual_phev": "PHEV-instruktionsbog",
      "manual_help": "Det link, kortet åbner under Mere → Instruktionsbog. Tomt = den officielle.",
      "debug_title": "Fejlsøgningstilstand",
      "debug_help": "Gemmer fulde forespørgsler og svar (uden personoplysninger) i diagnostikken.",
      "save_check": "Gem",
      "unsaved_settings": "Der er ændringer, der ikke er gemt.",
      "error_pin_required": "Indtast pinkoden.",
      "error_pin_invalid": "Pinkoden er ikke korrekt. Det er den fra den officielle Deepal-app, med denne samme konto.",
      "error_pin_rate_limited": "For mange pinkodeforsøg. Vent et par minutter, før du prøver igen.",
      "error_cannot_connect": "Kunne ikke oprette forbindelse til Deepal. Prøv igen senere.",
      "error_invalid_url": "Linket til instruktionsbogen er ikke gyldigt: det skal begynde med http:// eller https://.",
      "error_unknown_model": "Den model findes ikke i kataloget.",
      "close": "Luk",
      "other": "Andet",
      "history": "Historik",
      "manual": "Instruktionsbog",
      "copied": "Kopieret: {text}",
      "form_maintenance": "Sæt service op",
      "form_itv": "Sæt ITV op",
      "form_insurance": "Sæt forsikring op",
      "form_maintenance_off": "Deaktiveret: entiteterne, lampen på kortet og notifikationerne fjernes. Historikken går tabt.",
      "form_itv_off": "Deaktiveret: entiteterne, lampen på kortet og notifikationerne fjernes.",
      "form_insurance_off": "Deaktiveret: entiteterne, lampen på kortet og notifikationerne fjernes.",
      "first_notice": "Første notifikation {days} dage før",
      "mt_last": "Seneste service",
      "mt_last_help": "Hvis køretøjet ikke har haft nogen endnu, så angiv registreringsdatoen og 0 km.",
      "mt_next_is": "Den næste bliver {number}. service.",
      "mt_km_then": "Kilometer dengang",
      "mt_use_odometer": "Brug køretøjets aktuelle stand ({km} km)",
      "mt_every": "Hvor ofte",
      "mt_every_help": "Instruktionsbogen beder om kortere interval ved gentagne korte ture, støv, mudder, ekstrem kulde eller salt.",
      "mt_interval_manual": "Fra instruktionsbogen",
      "mt_interval_value": "{km} km eller {months} måneder",
      "mt_interval_other": "Du vælger",
      "mt_preview": "Næste service: {date} eller ved {km} km",
      "mt_whichever": "Alt efter hvad der kommer først: {date} eller ved {km} km.",
      "by_time": "Efter tid",
      "by_km": "Efter kilometer",
      "mt_km_detail": "Nu {now} km · service ved {due}",
      "mt_this_service": "Hvad denne service omfatter",
      "n_operations": "{count} punkter",
      "mt_no_plan": "Denne model har ingen serviceplan i kataloget.",
      "mt_next_adds": "Ved den næste ({number}.) kommer der desuden",
      "mt_history_item": "{number}. service · {date} · {km} km",
      "mt_no_history": "Der er ikke registreret nogen service endnu.",
      "itv_registration_title": "Registrering",
      "itv_registration_help": "Den står i registreringsattesten. Første ITV beregnes ud fra den.",
      "itv_passed_title": "ITV, der allerede er bestået",
      "itv_passed_help": "Kun hvis køretøjet allerede har bestået et.",
      "itv_passed": "Det har allerede bestået et ITV",
      "itv_next_title": "Næste ITV",
      "itv_next_rules": "Det beregnes efter reglerne i kontoens land.",
      "itv_next_auto": "Beregn det",
      "itv_next_manual": "Angiv en anden dato",
      "itv_next_manual_note": "Hvis synshallen gav dig en anden",
      "itv_preview": "Næste ITV: {date}",
      "itv_manual_date": "dato angivet i hånden",
      "itv_age": "{years} år",
      "itv_none_yet": "Ingen endnu",
      "itv_first_at": "Det første efter {years} år",
      "itv_rules_title": "Hvor ofte",
      "itv_rules": "Det første efter {first} år; derefter hvert {interval}. år og, fra {reduced} år, hvert år.",
      "itv_history_item": "ITV bestået {date}",
      "itv_no_history": "Der er ikke registreret noget ITV endnu.",
      "ins_policy_title": "Policen",
      "ins_policy_help": "Policenummeret og telefonnumrene vises kun på kortet og i panelet; de kommer aldrig med i diagnostikken.",
      "ins_renewal_title": "Fornyelse",
      "ins_renewal_help": "Forsikringen fornyes af sig selv hvert år. For at opsige skal du give besked på forhånd.",
      "ins_renews_on": "Fornyes",
      "ins_notice_days": "Dages varsel",
      "ins_phones_title": "Telefonnumre",
      "ins_phones_help": "Til at ringe med ét tryk fra kortet og herfra.",
      "ins_preview": "Sidste dag for opsigelse: {date}",
      "ins_preview_passed": "Den frist er overskredet. Den fornyes {date}.",
      "ins_dates": "Datoer",
      "ins_to_cancel": "Til at opsige",
      "ins_to_renewal": "Til fornyelsen",
      "ins_deadline_passed": "Fristen er overskredet",
      "ins_deadline_on": "Sidste dag: {date}",
      "ins_renews_itself": "Fornyes af sig selv {date}",
      "ins_assistance": "Vejhjælp",
      "read_only": "Kun læsning: ændringer foretages af en administrator i Home Assistant.",
      "people": "Personer",
      "people_none": "Ikke tildelt",
      "people_edit": "Vælg",
      "people_title": "Personer for {name}",
      "people_help": "Vælg, hvem denne bil tilhører. Det er personerne i Indstillinger → Personer.",
      "mine": "Din",
      "error_unknown_person": "Den person findes ikke længere i Home Assistant.",
      "error_unauthorized": "Kun en administrator kan foretage denne ændring.",
      "plate": "Nummerplade"
    },
    "el": {
      "tab_cars": "Οχήματα",
      "tab_alerts": "Ειδοποιήσεις",
      "tab_data": "Δεδομένα",
      "tab_diagnostics": "Διαγνωστικά",
      "loading": "Φόρτωση…",
      "retry": "Επανάληψη",
      "no_cars": "Δεν υπάρχουν οχήματα. Προσθέστε τον λογαριασμό σας Deepal στις Ρυθμίσεις → Συσκευές και υπηρεσίες.",
      "error_generic": "Δεν ήταν δυνατή η ολοκλήρωση. Δοκιμάστε ξανά.",
      "day": "{value} ημέρα",
      "days": "{value} ημέρες",
      "or": " ή ",
      "not_configured": "Δεν έχει επιλεγεί μοντέλο",
      "sheet_verified": "Επαληθευμένο δελτίο",
      "sheet_catalogue": "Δελτίο καταλόγου",
      "battery": "Μπαταρία",
      "range": "Αυτονομία",
      "odometer": "Χιλιομετρητής",
      "appearance": "Εμφάνιση",
      "configure": "Ρύθμιση",
      "section_charge": "Φόρτιση",
      "section_warnings": "Προειδοποιήσεις",
      "section_maintenance": "Σέρβις",
      "section_itv": "ITV",
      "section_insurance": "Ασφάλεια",
      "section_appearance": "Εμφάνιση",
      "section_people": "Άτομα",
      "not_set": "Δεν έχει ρυθμιστεί",
      "add_maintenance": "Ενεργοποίηση σέρβις",
      "add_itv": "Προσθήκη ITV",
      "add_insurance": "Προσθήκη ασφάλειας",
      "feature_seat_heat": "Θερμαινόμενα καθίσματα",
      "feature_seat_vent": "Αεριζόμενα καθίσματα",
      "feature_wheel_heat": "Θερμαινόμενο τιμόνι",
      "feature_power_tailgate": "Ηλεκτρική πόρτα χώρου αποσκευών",
      "wheel_pro": "Ζάντες 18\"",
      "wheel_cover": "Ζάντες 20\" με αεροδυναμικά καλύμματα",
      "wheel_open": "Ζάντες 20\" χωρίς καλύμματα",
      "service_number": "{number}ο σέρβις",
      "overdue": "Σε καθυστέρηση",
      "left": "Απομένουν {parts}",
      "overdue_since": "Καθυστέρηση {days}",
      "cancel_until": "Προθεσμία ακύρωσης: {date}",
      "renews_in": "Ανανεώνεται σε {days}",
      "notify_to": "Ειδοποίηση σε",
      "n_notices": "{count} ειδοποιήσεις",
      "edit_threshold": "Αλλαγή του χρόνου προειδοποίησης",
      "accept": "Αποδοχή",
      "cancel": "Ακύρωση",
      "unit_km": "km",
      "unit_days": "ημέρες",
      "when_km": "όταν απομένουν {value} km",
      "when_days": "όταν απομένουν {value} ημέρες",
      "when_days_deadline": "{value} ημέρες πριν από την προθεσμία",
      "when_maintenance_overdue": "την ίδια ημέρα ή όταν συμπληρωθούν τα km",
      "when_itv_overdue": "την ίδια ημέρα",
      "when_insurance_last_day": "τελευταία ημέρα για ακύρωση",
      "when_insurance_renewed": "την ίδια ημέρα",
      "notice_charge_started": "Η φόρτιση ξεκίνησε",
      "notice_charge_interrupted": "Η φόρτιση διακόπηκε",
      "notice_charge_finished": "Η φόρτιση ολοκληρώθηκε",
      "notice_warnings": "Προειδοποιητικές λυχνίες",
      "notice_tires": "Ελαστικά",
      "notice_key_battery": "Χαμηλή μπαταρία κλειδιού",
      "notice_maintenance_t1": "Ειδοποίηση χρόνου 1",
      "notice_maintenance_t2": "Ειδοποίηση χρόνου 2",
      "notice_maintenance_t3": "Ειδοποίηση χρόνου 3",
      "notice_maintenance_k1": "Ειδοποίηση χιλιομέτρων 1",
      "notice_maintenance_k2": "Ειδοποίηση χιλιομέτρων 2",
      "notice_maintenance_k3": "Ειδοποίηση χιλιομέτρων 3",
      "notice_maintenance_overdue": "Ώρα για σέρβις",
      "notice_itv_t1": "Ειδοποίηση 1",
      "notice_itv_t2": "Ειδοποίηση 2",
      "notice_itv_t3": "Ειδοποίηση 3",
      "notice_itv_overdue": "Λήξη ITV",
      "notice_insurance_c1": "Ειδοποίηση ακύρωσης 1",
      "notice_insurance_c2": "Ειδοποίηση ακύρωσης 2",
      "notice_insurance_last_day": "Προθεσμία ακύρωσης",
      "notice_insurance_r1": "Ειδοποίηση ανανέωσης 1",
      "notice_insurance_r2": "Ειδοποίηση ανανέωσης 2",
      "notice_insurance_renewed": "Η ασφάλεια ανανεώθηκε",
      "unsaved": "Αυτό το όχημα έχει αλλαγές που δεν αποθηκεύτηκαν.",
      "alerts_help": "Σημειώστε ποιος λαμβάνει κάθε ειδοποίηση. Το μολύβι αλλάζει τις ημέρες ή τα χιλιόμετρα της ειδοποίησης· οι χρόνοι ισχύουν για αυτό το όχημα.",
      "factory_thresholds": "Προεπιλεγμένοι χρόνοι",
      "discard": "Απόρριψη",
      "save": "Αποθήκευση",
      "saved": "Αποθηκεύτηκε",
      "copy_from": "Αντιγραφή από άλλο όχημα",
      "car": "Όχημα",
      "copy": "Αντιγραφή",
      "error_threshold_range_limits": "Ο χρόνος πρέπει να είναι μεταξύ {low} και {high}.",
      "error_threshold_range": "Ένας χρόνος είναι εκτός ορίων.",
      "error_threshold_order": "Οι χρόνοι πρέπει να πηγαίνουν από τον μεγαλύτερο στον μικρότερο: η ειδοποίηση 1 πριν από τη 2, και η 2 πριν από την 3.",
      "error_not_found": "Αυτό το όχημα δεν είναι πλέον στον λογαριασμό.",
      "error_invalid": "Κάποια στοιχεία δεν είναι έγκυρα.",
      "error_invalid_file": "Το αρχείο δεν είναι αντίγραφο ασφαλείας του DEC Deepal ή είναι κατεστραμμένο.",
      "error_newer_file": "Το αντίγραφο ασφαλείας προέρχεται από νεότερη έκδοση της ενσωμάτωσης. Ενημερώστε το DEC Deepal και δοκιμάστε ξανά.",
      "error_empty_file": "Το αντίγραφο ασφαλείας δεν έχει δεδομένα για κανένα όχημα.",
      "error_required": "Λείπουν στοιχεία.",
      "backup_title": "Αντίγραφο ασφαλείας",
      "backup_help": "Σέρβις, ITV, ασφάλεια και εμφάνιση των οχημάτων σας. Τα δεδομένα ανήκουν στο όχημα: δεν χάνονται όταν αφαιρεθεί ο λογαριασμός.",
      "download_title": "Λήψη αντιγράφου ασφαλείας",
      "download_help": "Ένα αρχείο με τα δεδομένα όλων των οχημάτων. Περιέχει τον αριθμό συμβολαίου και τα τηλέφωνα της ασφάλειας: φυλάξτε το σε ασφαλές μέρος.",
      "download": "Λήψη",
      "send_title": "Αποστολή του αντιγράφου σε κινητό",
      "send_help": "Φτάνει μια ειδοποίηση· όταν την πατήσετε, ανοίγει ο περιηγητής και κατεβαίνει το αρχείο. Ο σύνδεσμος λήγει σε 10 λεπτά.",
      "send": "Αποστολή",
      "sent_to": "Η ειδοποίηση στάλθηκε στο {device}.",
      "upload_title": "Φόρτωση αντιγράφου ασφαλείας",
      "upload_help": "Επαναφέρει τα οχήματα του αρχείου όπως ήταν σε αυτό. Τα υπόλοιπα οχήματα δεν αλλάζουν.",
      "choose_file": "Επιλογή αρχείου",
      "imported": "Το αντίγραφο ασφαλείας φορτώθηκε: {cars}.",
      "stored_title": "Αποθηκευμένα δεδομένα",
      "stored_help": "Ανά όχημα, με βάση τον αριθμό πλαισίου (VIN).",
      "stored_none": "Δεν υπάρχουν αποθηκευμένα δεδομένα για κανένα όχημα.",
      "in_account": "Στον λογαριασμό",
      "no_account": "Χωρίς λογαριασμό",
      "no_account_note": "Δεν ανήκει πλέον σε κανέναν λογαριασμό",
      "delete": "Διαγραφή",
      "delete_title": "Διαγραφή αποθηκευμένων δεδομένων",
      "delete_confirm": "Θα διαγραφούν το σέρβις, το ITV και η ασφάλεια του {name}. Αυτό δεν αναιρείται: κατεβάστε πρώτα ένα αντίγραφο ασφαλείας αν θέλετε να τα κρατήσετε.",
      "deleted": "Τα δεδομένα διαγράφηκαν.",
      "history_title": "Τι έχει συμβεί",
      "history_help": "Αλλαγές, εντολές και ειδοποιήσεις από την τελευταία επανεκκίνηση. Τα ίδια μπαίνουν στο αρχείο διαγνωστικών.",
      "history_none": "Δεν υπάρχει τίποτα ακόμη.",
      "filter_all": "Όλα",
      "filter_orders": "Εντολές",
      "filter_alerts": "Ειδοποιήσεις",
      "filter_errors": "Σφάλματα",
      "sheets_title": "Δελτίο κάθε οχήματος",
      "sheets_help": "Ποιον εξοπλισμό θεωρεί δεδομένο η ενσωμάτωση και από πού τον παίρνει.",
      "diagnostics_file": "Διαγνωστικά",
      "ev_alert": "Στάλθηκε ειδοποίηση: {name}",
      "ev_targets": "{count} παραλήπτες",
      "ev_wake": "Αφύπνιση οχήματος",
      "ev_command": "Εντολή: {name}",
      "ev_code": "κωδικός",
      "today": "Σήμερα",
      "yesterday": "Χθες",
      "enabled": "Ενεργό",
      "mt_services_done": "Σέρβις που έχουν ήδη γίνει",
      "mt_interval_km": "Διάστημα (km)",
      "mt_interval_months": "Διάστημα (μήνες)",
      "mt_register": "Καταχώριση σέρβις που έγινε",
      "mt_register_help": "Σημειώνει το {number}ο σέρβις του {name} και αρχίζει να μετρά για το επόμενο.",
      "date": "Ημερομηνία",
      "mt_km": "Χιλιόμετρα",
      "register": "Καταχώριση",
      "registered": "Καταχωρίστηκε",
      "itv_registration": "Ημερομηνία ταξινόμησης",
      "itv_last": "Τελευταίο ITV που πέρασε",
      "itv_next": "Επόμενο ITV (χειροκίνητα)",
      "itv_register": "Καταχώριση ITV που πέρασε",
      "itv_register_help": "Σημειώνει ότι το {name} πέρασε το ITV και υπολογίζει το επόμενο.",
      "ins_company": "Εταιρεία",
      "ins_policy": "Αριθμός συμβολαίου",
      "ins_kind": "Τύπος ασφάλειας",
      "ins_notice": "Ημέρες προειδοποίησης για ακύρωση",
      "ins_phone_assistance": "Τηλέφωνο οδικής βοήθειας",
      "ins_phone_company": "Τηλέφωνο εταιρείας",
      "kind_third_party": "Αστική ευθύνη",
      "kind_third_party_plus": "Αστική ευθύνη με επιπλέον καλύψεις",
      "kind_comprehensive_excess": "Μικτή με απαλλαγή",
      "kind_comprehensive": "Μικτή χωρίς απαλλαγή",
      "tab_settings": "Ρυθμίσεις",
      "appearance_title": "Εμφάνιση του {name}",
      "appearance_help": "Καθορίζει τη φωτογραφία, την όψη του οχήματος και ποιος εξοπλισμός θεωρείται δεδομένος.",
      "model": "Μοντέλο",
      "trim": "Έκδοση",
      "color": "Χρώμα",
      "wheels": "Ζάντες",
      "model_ev": "Ηλεκτρικό",
      "model_phev": "Plug-in υβριδικό",
      "trim_full": "Θερμαινόμενα καθίσματα και τιμόνι, ηλεκτρική πόρτα χώρου αποσκευών",
      "trim_basic": "Χωρίς θερμαινόμενα καθίσματα και τιμόνι",
      "account": "Λογαριασμός: {name}",
      "pin_title": "Τηλεχειρισμός με PIN",
      "pin_help": "Για κλείδωμα και ξεκλείδωμα, παράθυρα και πορτμπαγκάζ. Είναι το PIN της επίσημης εφαρμογής Deepal, με τον ίδιο λογαριασμό. Ισχύει για όλα τα οχήματα του λογαριασμού.",
      "pin_enabled": "Εντολές με PIN",
      "pin_enabled_help": "Χωρίς αυτό, η κάρτα δείχνει μόνο την κατάσταση θυρών, παραθύρων και πορτμπαγκάζ.",
      "pin": "PIN",
      "pin_field_help": "Ελέγχεται με την Deepal κατά την αποθήκευση. Αφήστε το κενό για να κρατήσετε το τρέχον.",
      "pin_checked": "Ελέγχθηκε",
      "show_pin": "Εμφάνιση του PIN",
      "pin_mode_title": "Πώς χρησιμοποιούνται οι εντολές",
      "mode_direct": "Άμεσα",
      "mode_direct_help": "Η εντολή στέλνεται όταν πατάτε, μετά από επιβεβαίωση. Το πιο βολικό.",
      "mode_armed": "Πρώτα ξεκλείδωμα",
      "mode_armed_help": "Πρέπει πρώτα να ενεργοποιήσετε το «Ξεκλείδωμα ενεργειών με PIN», και διαρκεί μόνο για λίγο. Το πιο ασφαλές.",
      "arm_seconds": "Πόσο διαρκεί το ξεκλείδωμα",
      "arm_seconds_help": "Μετά από αυτόν τον χρόνο, οι εντολές με PIN κλειδώνουν ξανά μόνες τους.",
      "seconds": "{value} s",
      "arm_notify": "Ειδοποίηση στο ξεκλείδωμα",
      "arm_notify_help": "Μια ειδοποίηση στο Home Assistant κάθε φορά που επιτρέπονται εντολές.",
      "reading_title": "Ανάγνωση δεδομένων",
      "reading_help": "Πώς και κάθε πότε ερωτάται το όχημα.",
      "scan_title": "Διάστημα ανάγνωσης",
      "scan_help": "Κάθε πότε διαβάζονται τα δεδομένα του οχήματος. Πολύ χαμηλές τιμές μπορεί να κάνουν την Deepal να περιορίσει τον λογαριασμό.",
      "minutes": "{value} λεπ.",
      "wake_title": "Αφύπνιση του οχήματος όταν χρειάζεται",
      "wake_help": "Όταν πατάτε Ανανέωση και πριν από εντολή με PIN. Ποτέ στις αυτόματες αναγνώσεις, για να προστατεύεται η μπαταρία 12 V.",
      "manual_bev": "Εγχειρίδιο BEV",
      "manual_phev": "Εγχειρίδιο PHEV",
      "manual_help": "Ο σύνδεσμος που ανοίγει η κάρτα στο Περισσότερα → Εγχειρίδιο. Κενό = το επίσημο.",
      "debug_title": "Λειτουργία αποσφαλμάτωσης",
      "debug_help": "Αποθηκεύει πλήρη αιτήματα και απαντήσεις (χωρίς προσωπικά δεδομένα) στα διαγνωστικά.",
      "save_check": "Αποθήκευση",
      "unsaved_settings": "Υπάρχουν αλλαγές που δεν αποθηκεύτηκαν.",
      "error_pin_required": "Εισαγάγετε το PIN.",
      "error_pin_invalid": "Το PIN δεν είναι σωστό. Είναι αυτό της επίσημης εφαρμογής Deepal, με τον ίδιο λογαριασμό.",
      "error_pin_rate_limited": "Πάρα πολλές προσπάθειες PIN. Περιμένετε λίγα λεπτά πριν δοκιμάσετε ξανά.",
      "error_cannot_connect": "Δεν ήταν δυνατή η σύνδεση με την Deepal. Δοκιμάστε ξανά αργότερα.",
      "error_invalid_url": "Ο σύνδεσμος του εγχειριδίου δεν είναι έγκυρος: πρέπει να αρχίζει με http:// ή https://.",
      "error_unknown_model": "Αυτό το μοντέλο δεν υπάρχει στον κατάλογο.",
      "close": "Κλείσιμο",
      "other": "Άλλο",
      "history": "Ιστορικό",
      "manual": "Εγχειρίδιο",
      "copied": "Αντιγράφηκε: {text}",
      "form_maintenance": "Ρύθμιση του σέρβις",
      "form_itv": "Ρύθμιση του ITV",
      "form_insurance": "Ρύθμιση της ασφάλειας",
      "form_maintenance_off": "Απενεργοποιημένο: αφαιρούνται οι οντότητες, η ένδειξη στην κάρτα και οι ειδοποιήσεις του. Το ιστορικό χάνεται.",
      "form_itv_off": "Απενεργοποιημένο: αφαιρούνται οι οντότητες, η ένδειξη στην κάρτα και οι ειδοποιήσεις του.",
      "form_insurance_off": "Απενεργοποιημένη: αφαιρούνται οι οντότητες, η ένδειξη στην κάρτα και οι ειδοποιήσεις της.",
      "first_notice": "Πρώτη ειδοποίηση {days} ημέρες πριν",
      "mt_last": "Τελευταίο σέρβις",
      "mt_last_help": "Αν το όχημα δεν έχει κάνει κανένα ακόμη, βάλτε την ημερομηνία ταξινόμησης και 0 km.",
      "mt_next_is": "Το επόμενο θα είναι το {number}ο σέρβις.",
      "mt_km_then": "Χιλιόμετρα τότε",
      "mt_use_odometer": "Χρήση της τρέχουσας ένδειξης του οχήματος ({km} km)",
      "mt_every": "Κάθε πότε",
      "mt_every_help": "Το εγχειρίδιο ζητά μικρότερο διάστημα με συχνές μικρές διαδρομές, σκόνη, λάσπη, ακραίο κρύο ή αλάτι.",
      "mt_interval_manual": "Του εγχειριδίου",
      "mt_interval_value": "{km} km ή {months} μήνες",
      "mt_interval_other": "Το επιλέγετε εσείς",
      "mt_preview": "Επόμενο σέρβις: {date} ή στα {km} km",
      "mt_whichever": "Όποιο έρθει πρώτο: στις {date} ή στα {km} km.",
      "by_time": "Με βάση τον χρόνο",
      "by_km": "Με βάση τα χιλιόμετρα",
      "mt_km_detail": "Τώρα {now} km · σέρβις στα {due}",
      "mt_this_service": "Τι περιλαμβάνει αυτό το σέρβις",
      "n_operations": "{count} εργασίες",
      "mt_no_plan": "Αυτό το μοντέλο δεν έχει πρόγραμμα συντήρησης στον κατάλογο.",
      "mt_next_adds": "Στο επόμενο ({number}ο) προστίθεται",
      "mt_history_item": "{number}ο σέρβις · {date} · {km} km",
      "mt_no_history": "Δεν έχει καταχωριστεί κανένα σέρβις ακόμη.",
      "itv_registration_title": "Ταξινόμηση",
      "itv_registration_help": "Αναγράφεται στην άδεια κυκλοφορίας. Με αυτήν υπολογίζεται το πρώτο ITV.",
      "itv_passed_title": "ITV που έχουν ήδη περάσει",
      "itv_passed_help": "Μόνο αν το όχημα έχει ήδη περάσει κάποιο.",
      "itv_passed": "Έχει ήδη περάσει ITV",
      "itv_next_title": "Επόμενο ITV",
      "itv_next_rules": "Υπολογίζεται με τους κανόνες της χώρας του λογαριασμού.",
      "itv_next_auto": "Αυτόματος υπολογισμός",
      "itv_next_manual": "Ορισμός άλλης ημερομηνίας",
      "itv_next_manual_note": "Αν ο σταθμός σάς έδωσε διαφορετική",
      "itv_preview": "Επόμενο ITV: {date}",
      "itv_manual_date": "ημερομηνία που ορίστηκε με το χέρι",
      "itv_age": "{years} έτη",
      "itv_none_yet": "Κανένα ακόμη",
      "itv_first_at": "Το πρώτο, στα {years} έτη",
      "itv_rules_title": "Κάθε πότε",
      "itv_rules": "Το πρώτο στα {first} έτη· έπειτα κάθε {interval} έτη και, από τα {reduced} έτη, κάθε χρόνο.",
      "itv_history_item": "Το ITV πέρασε στις {date}",
      "itv_no_history": "Δεν έχει καταχωριστεί κανένα ITV ακόμη.",
      "ins_policy_title": "Το συμβόλαιο",
      "ins_policy_help": "Ο αριθμός συμβολαίου και τα τηλέφωνα φαίνονται μόνο στην κάρτα και στον πίνακα· δεν εμφανίζονται ποτέ στα διαγνωστικά.",
      "ins_renewal_title": "Ανανέωση",
      "ins_renewal_help": "Η ασφάλεια ανανεώνεται μόνη της κάθε χρόνο. Για να ακυρωθεί, πρέπει να ειδοποιήσετε εκ των προτέρων.",
      "ins_renews_on": "Ανανεώνεται στις",
      "ins_notice_days": "Ημέρες προειδοποίησης",
      "ins_phones_title": "Τηλέφωνα",
      "ins_phones_help": "Για κλήση με ένα πάτημα από την κάρτα και από εδώ.",
      "ins_preview": "Τελευταία ημέρα για ακύρωση: {date}",
      "ins_preview_passed": "Αυτή η προθεσμία πέρασε. Ανανεώνεται στις {date}.",
      "ins_dates": "Ημερομηνίες",
      "ins_to_cancel": "Για ακύρωση",
      "ins_to_renewal": "Μέχρι την ανανέωση",
      "ins_deadline_passed": "Η προθεσμία πέρασε",
      "ins_deadline_on": "Τελευταία ημέρα: {date}",
      "ins_renews_itself": "Ανανεώνεται μόνη της στις {date}",
      "ins_assistance": "Οδική βοήθεια",
      "read_only": "Μόνο ανάγνωση: τις αλλαγές τις κάνει ένας διαχειριστής του Home Assistant.",
      "people": "Άτομα",
      "people_none": "Δεν έχει οριστεί",
      "people_edit": "Επιλογή",
      "people_title": "Άτομα του {name}",
      "people_help": "Επίλεξε σε ποιον ανήκει αυτό το αυτοκίνητο. Είναι τα άτομα από Ρυθμίσεις → Άτομα.",
      "mine": "Δικό σου",
      "error_unknown_person": "Αυτό το άτομο δεν υπάρχει πια στο Home Assistant.",
      "error_unauthorized": "Μόνο ένας διαχειριστής μπορεί να κάνει αυτή την αλλαγή.",
      "plate": "Πινακίδα"
    },
    "sl": {
      "tab_cars": "Vozila",
      "tab_alerts": "Obvestila",
      "tab_data": "Podatki",
      "tab_diagnostics": "Diagnostika",
      "loading": "Nalaganje…",
      "retry": "Poskusi znova",
      "no_cars": "Ni vozil. Dodajte svoj račun Deepal v Nastavitve → Naprave in storitve.",
      "error_generic": "Tega ni bilo mogoče dokončati. Poskusite znova.",
      "day": "{value} dan",
      "days": "{value} dni",
      "or": " ali ",
      "not_configured": "Model ni izbran",
      "sheet_verified": "Preverjen list",
      "sheet_catalogue": "List iz kataloga",
      "battery": "Baterija",
      "range": "Doseg",
      "odometer": "Števec kilometrov",
      "appearance": "Videz",
      "configure": "Nastavi",
      "section_charge": "Polnjenje",
      "section_warnings": "Opozorila",
      "section_maintenance": "Servis",
      "section_itv": "ITV",
      "section_insurance": "Zavarovanje",
      "section_appearance": "Videz",
      "section_people": "Osebe",
      "not_set": "Ni nastavljeno",
      "add_maintenance": "Omogoči servis",
      "add_itv": "Dodaj ITV",
      "add_insurance": "Dodaj zavarovanje",
      "feature_seat_heat": "Ogrevani sedeži",
      "feature_seat_vent": "Prezračevani sedeži",
      "feature_wheel_heat": "Ogrevan volan",
      "feature_power_tailgate": "Električna prtljažna vrata",
      "wheel_pro": "18\" platišča",
      "wheel_cover": "20\" platišča z aerodinamičnimi pokrovi",
      "wheel_open": "20\" platišča brez pokrovov",
      "service_number": "{number}. servis",
      "overdue": "Zamujeno",
      "left": "Še {parts}",
      "overdue_since": "Zamuda: {days}",
      "cancel_until": "Rok za odpoved: {date}",
      "renews_in": "Podaljša se čez {days}",
      "notify_to": "Obvesti",
      "n_notices": "Obvestil: {count}",
      "edit_threshold": "Spremeni rok obvestila",
      "accept": "Sprejmi",
      "cancel": "Prekliči",
      "unit_km": "km",
      "unit_days": "dni",
      "when_km": "ko ostane {value} km",
      "when_days": "ko ostane {value} dni",
      "when_days_deadline": "{value} dni pred rokom",
      "when_maintenance_overdue": "na dan roka ali ko so km doseženi",
      "when_itv_overdue": "na dan roka",
      "when_insurance_last_day": "zadnji dan za odpoved",
      "when_insurance_renewed": "na dan podaljšanja",
      "notice_charge_started": "Polnjenje se je začelo",
      "notice_charge_interrupted": "Polnjenje prekinjeno",
      "notice_charge_finished": "Polnjenje končano",
      "notice_warnings": "Opozorilne lučke",
      "notice_tires": "Pnevmatike",
      "notice_key_battery": "Baterija ključa je skoraj prazna",
      "notice_maintenance_t1": "Časovno obvestilo 1",
      "notice_maintenance_t2": "Časovno obvestilo 2",
      "notice_maintenance_t3": "Časovno obvestilo 3",
      "notice_maintenance_k1": "Kilometrsko obvestilo 1",
      "notice_maintenance_k2": "Kilometrsko obvestilo 2",
      "notice_maintenance_k3": "Kilometrsko obvestilo 3",
      "notice_maintenance_overdue": "Rok za servis",
      "notice_itv_t1": "Obvestilo 1",
      "notice_itv_t2": "Obvestilo 2",
      "notice_itv_t3": "Obvestilo 3",
      "notice_itv_overdue": "Rok za ITV",
      "notice_insurance_c1": "Obvestilo o odpovedi 1",
      "notice_insurance_c2": "Obvestilo o odpovedi 2",
      "notice_insurance_last_day": "Rok za odpoved",
      "notice_insurance_r1": "Obvestilo o podaljšanju 1",
      "notice_insurance_r2": "Obvestilo o podaljšanju 2",
      "notice_insurance_renewed": "Zavarovanje podaljšano",
      "unsaved": "To vozilo ima neshranjene spremembe.",
      "alerts_help": "Označite, kdo prejme katero obvestilo. Svinčnik spremeni dneve ali kilometre tega obvestila; roki veljajo za to vozilo.",
      "factory_thresholds": "Privzeti roki",
      "discard": "Zavrzi",
      "save": "Shrani",
      "saved": "Shranjeno",
      "copy_from": "Kopiraj iz drugega vozila",
      "car": "Vozilo",
      "copy": "Kopiraj",
      "error_threshold_range_limits": "Rok mora biti med {low} in {high}.",
      "error_threshold_range": "Eden od rokov je zunaj dovoljenega obsega.",
      "error_threshold_order": "Roki morajo iti od najdaljšega do najkrajšega: obvestilo 1 pred 2 in 2 pred 3.",
      "error_not_found": "Tega vozila ni več v računu.",
      "error_invalid": "Nekateri podatki niso veljavni.",
      "error_invalid_file": "Datoteka ni varnostna kopija DEC Deepal ali pa je poškodovana.",
      "error_newer_file": "Varnostna kopija izvira iz novejše različice integracije. Posodobite DEC Deepal in poskusite znova.",
      "error_empty_file": "Varnostna kopija nima podatkov za nobeno vozilo.",
      "error_required": "Manjkajo podatki.",
      "backup_title": "Varnostna kopija",
      "backup_help": "Servis, ITV, zavarovanje in videz vaših vozil. Podatki pripadajo vozilu: ne izgubijo se, ko se račun odstrani.",
      "download_title": "Prenos varnostne kopije",
      "download_help": "Datoteka s podatki vseh vozil. Vsebuje številko police in telefonske številke zavarovalnice: hranite jo na varnem.",
      "download": "Prenesi",
      "send_title": "Pošlji varnostno kopijo na telefon",
      "send_help": "Prispe obvestilo; ko ga tapnete, se odpre brskalnik in prenese datoteko. Povezava poteče čez 10 minut.",
      "send": "Pošlji",
      "sent_to": "Obvestilo poslano na {device}.",
      "upload_title": "Naloži varnostno kopijo",
      "upload_help": "Vozila iz datoteke povrne v stanje, zapisano v njej. Druga vozila ostanejo nedotaknjena.",
      "choose_file": "Izberi datoteko",
      "imported": "Varnostna kopija naložena: {cars}.",
      "stored_title": "Shranjeni podatki",
      "stored_help": "Po vozilih, prepoznanih po številki VIN.",
      "stored_none": "Za nobeno vozilo ni shranjenih podatkov.",
      "in_account": "V računu",
      "no_account": "Brez računa",
      "no_account_note": "Ni več v nobenem računu",
      "delete": "Izbriši",
      "delete_title": "Izbriši shranjene podatke",
      "delete_confirm": "Servis, ITV in zavarovanje vozila {name} bodo izbrisani. Tega ni mogoče razveljaviti: če jih želite ohraniti, najprej prenesite varnostno kopijo.",
      "deleted": "Podatki izbrisani.",
      "history_title": "Kaj se je zgodilo",
      "history_help": "Spremembe, ukazi in obvestila od zadnjega ponovnega zagona. Enako je zapisano v diagnostični datoteki.",
      "history_none": "Zaenkrat ni ničesar za prikaz.",
      "filter_all": "Vse",
      "filter_orders": "Ukazi",
      "filter_alerts": "Obvestila",
      "filter_errors": "Napake",
      "sheets_title": "List posameznega vozila",
      "sheets_help": "Katero opremo integracija predpostavlja in od kod jo ima.",
      "diagnostics_file": "Diagnostika",
      "ev_alert": "Obvestilo poslano: {name}",
      "ev_targets": "Prejemnikov: {count}",
      "ev_wake": "Prebujanje vozila",
      "ev_command": "Ukaz: {name}",
      "ev_code": "koda",
      "today": "Danes",
      "yesterday": "Včeraj",
      "enabled": "Omogočeno",
      "mt_services_done": "Že opravljeni servisi",
      "mt_interval_km": "Interval (km)",
      "mt_interval_months": "Interval (meseci)",
      "mt_register": "Zabeleži opravljen servis",
      "mt_register_help": "Zabeleži {number}. servis vozila {name} in začne šteti do naslednjega.",
      "date": "Datum",
      "mt_km": "Kilometri",
      "register": "Zabeleži",
      "registered": "Zabeleženo",
      "itv_registration": "Datum registracije",
      "itv_last": "Zadnji opravljeni ITV",
      "itv_next": "Naslednji ITV (ročno)",
      "itv_register": "Zabeleži opravljen ITV",
      "itv_register_help": "Zabeleži, da je vozilo {name} opravilo ITV, in izračuna naslednjega.",
      "ins_company": "Zavarovalnica",
      "ins_policy": "Številka police",
      "ins_kind": "Vrsta zavarovanja",
      "ins_notice": "Odpovedni rok v dneh",
      "ins_phone_assistance": "Telefon pomoči na cesti",
      "ins_phone_company": "Telefon zavarovalnice",
      "kind_third_party": "Avtomobilska odgovornost",
      "kind_third_party_plus": "Delni kasko",
      "kind_comprehensive_excess": "Polni kasko z odbitno franšizo",
      "kind_comprehensive": "Polni kasko brez odbitne franšize",
      "tab_settings": "Nastavitve",
      "appearance_title": "Videz vozila {name}",
      "appearance_help": "Določa fotografijo, pogled vozila in katera oprema se predpostavlja.",
      "model": "Model",
      "trim": "Različica",
      "color": "Barva",
      "wheels": "Platišča",
      "model_ev": "Električni",
      "model_phev": "Priključni hibrid",
      "trim_full": "Ogrevani sedeži in volan, električna prtljažna vrata",
      "trim_basic": "Brez ogrevanih sedežev in volana",
      "account": "Račun: {name}",
      "pin_title": "Daljinsko upravljanje s PIN-om",
      "pin_help": "Za zaklepanje in odklepanje, okna in prtljažnik. To je PIN uradne aplikacije Deepal z istim računom. Velja za vsa vozila v računu.",
      "pin_enabled": "Ukazi s PIN-om",
      "pin_enabled_help": "Brez tega kartica prikazuje samo stanje vrat, oken in prtljažnika.",
      "pin": "PIN",
      "pin_field_help": "Ob shranjevanju se preveri pri Deepalu. Pustite prazno, da ohranite trenutnega.",
      "pin_checked": "Preverjeno",
      "show_pin": "Pokaži PIN",
      "pin_mode_title": "Kako se uporabljajo ukazi",
      "mode_direct": "Neposredno",
      "mode_direct_help": "Ukaz se pošlje, ko tapnete, po potrditvi. Najbolj priročno.",
      "mode_armed": "Najprej odkleni",
      "mode_armed_help": "Najprej morate omogočiti »Odkleni dejanja s PIN-om«, in to traja le nekaj časa. Najvarneje.",
      "arm_seconds": "Kako dolgo traja odklep",
      "arm_seconds_help": "Po tem času se ukazi s PIN-om sami znova zaklenejo.",
      "seconds": "{value} s",
      "arm_notify": "Obvesti ob odklepu",
      "arm_notify_help": "Obvestilo v Home Assistantu vsakič, ko so ukazi dovoljeni.",
      "reading_title": "Branje podatkov",
      "reading_help": "Kako in kako pogosto se vozilo poizveduje.",
      "scan_title": "Interval branja",
      "scan_help": "Kako pogosto se berejo podatki vozila. Zelo nizke vrednosti lahko povzročijo, da Deepal omeji račun.",
      "minutes": "{value} min",
      "wake_title": "Zbudi vozilo, ko je treba",
      "wake_help": "Ko tapnete Osveži in pred ukazom s PIN-om. Nikoli pri samodejnih branjih, da se zaščiti 12 V akumulator.",
      "manual_bev": "Priročnik BEV",
      "manual_phev": "Priročnik PHEV",
      "manual_help": "Povezava, ki jo kartica odpre pod Več → Priročnik. Prazno = uradni.",
      "debug_title": "Razhroščevalni način",
      "debug_help": "V diagnostiko shranjuje celotne zahteve in odgovore (brez osebnih podatkov).",
      "save_check": "Shrani",
      "unsaved_settings": "Obstajajo neshranjene spremembe.",
      "error_pin_required": "Vnesite PIN.",
      "error_pin_invalid": "PIN ni pravilen. To je PIN uradne aplikacije Deepal s tem istim računom.",
      "error_pin_rate_limited": "Preveč poskusov PIN-a. Počakajte nekaj minut, preden poskusite znova.",
      "error_cannot_connect": "Povezava z Deepalom ni uspela. Poskusite znova pozneje.",
      "error_invalid_url": "Povezava do priročnika ni veljavna: začeti se mora s http:// ali https://.",
      "error_unknown_model": "Tega modela ni v katalogu.",
      "close": "Zapri",
      "other": "Drugo",
      "history": "Zgodovina",
      "manual": "Priročnik",
      "copied": "Kopirano: {text}",
      "form_maintenance": "Nastavi servis",
      "form_itv": "Nastavi ITV",
      "form_insurance": "Nastavi zavarovanje",
      "form_maintenance_off": "Onemogočeno: odstranijo se entitete, lučka na kartici in obvestila. Zgodovina se izgubi.",
      "form_itv_off": "Onemogočeno: odstranijo se entitete, lučka na kartici in obvestila.",
      "form_insurance_off": "Onemogočeno: odstranijo se entitete, lučka na kartici in obvestila.",
      "first_notice": "Prvo obvestilo {days} dni prej",
      "mt_last": "Zadnji servis",
      "mt_last_help": "Če vozilo še ni imelo nobenega, vnesite datum registracije in 0 km.",
      "mt_next_is": "Naslednji bo {number}. servis.",
      "mt_km_then": "Kilometri takrat",
      "mt_use_odometer": "Uporabi trenutno stanje vozila ({km} km)",
      "mt_every": "Kako pogosto",
      "mt_every_help": "Priročnik zahteva krajši interval pri pogostih kratkih vožnjah, prahu, blatu, hudem mrazu ali soli.",
      "mt_interval_manual": "Po priročniku",
      "mt_interval_value": "{km} km ali {months} mesecev",
      "mt_interval_other": "Izberete sami",
      "mt_preview": "Naslednji servis: {date} ali pri {km} km",
      "mt_whichever": "Kar nastopi prej: {date} ali pri {km} km.",
      "by_time": "Po času",
      "by_km": "Po kilometrih",
      "mt_km_detail": "Zdaj {now} km · servis pri {due}",
      "mt_this_service": "Kaj vključuje ta servis",
      "n_operations": "Opravil: {count}",
      "mt_no_plan": "Ta model v katalogu nima načrta vzdrževanja.",
      "mt_next_adds": "Pri naslednjem ({number}.) se doda",
      "mt_history_item": "{number}. servis · {date} · {km} km",
      "mt_no_history": "Zabeležen še ni noben servis.",
      "itv_registration_title": "Registracija",
      "itv_registration_help": "Zapisana je v prometnem dovoljenju. Iz nje se izračuna prvi ITV.",
      "itv_passed_title": "Že opravljeni ITV",
      "itv_passed_help": "Samo če je vozilo že opravilo katerega.",
      "itv_passed": "ITV je že opravilo",
      "itv_next_title": "Naslednji ITV",
      "itv_next_rules": "Izračuna se po pravilih države računa.",
      "itv_next_auto": "Izračunaj samodejno",
      "itv_next_manual": "Vnesi drug datum",
      "itv_next_manual_note": "Če so vam na pregledu dali drugačnega",
      "itv_preview": "Naslednji ITV: {date}",
      "itv_manual_date": "datum vnesen ročno",
      "itv_age": "Starost v letih: {years}",
      "itv_none_yet": "Še nobenega",
      "itv_first_at": "Prvi pri starosti {years} let",
      "itv_rules_title": "Kako pogosto",
      "itv_rules": "Prvi pri {first} letih; nato na vsaka {interval} leta in od {reduced} let naprej vsako leto.",
      "itv_history_item": "ITV opravljen {date}",
      "itv_no_history": "Zabeležen še ni noben ITV.",
      "ins_policy_title": "Polica",
      "ins_policy_help": "Številka police in telefonske številke so vidne samo na kartici in na plošči; v diagnostiki se nikoli ne pojavijo.",
      "ins_renewal_title": "Podaljšanje",
      "ins_renewal_help": "Zavarovanje se vsako leto podaljša samo. Za odpoved morate to sporočiti vnaprej.",
      "ins_renews_on": "Podaljša se",
      "ins_notice_days": "Dni odpovednega roka",
      "ins_phones_title": "Telefonske številke",
      "ins_phones_help": "Za klic z enim dotikom s kartice in od tukaj.",
      "ins_preview": "Zadnji dan za odpoved: {date}",
      "ins_preview_passed": "Ta rok je minil. Podaljša se {date}.",
      "ins_dates": "Datumi",
      "ins_to_cancel": "Za odpoved",
      "ins_to_renewal": "Do podaljšanja",
      "ins_deadline_passed": "Rok je minil",
      "ins_deadline_on": "Zadnji dan: {date}",
      "ins_renews_itself": "Samo se podaljša {date}",
      "ins_assistance": "Pomoč na cesti",
      "read_only": "Samo za branje: spremembe naredi skrbnik Home Assistanta.",
      "people": "Osebe",
      "people_none": "Ni dodeljeno",
      "people_edit": "Izberi",
      "people_title": "Osebe vozila {name}",
      "people_help": "Izberi, komu pripada to vozilo. To so osebe v Nastavitve → Osebe.",
      "mine": "Tvoje",
      "error_unknown_person": "Ta oseba v Home Assistantu ne obstaja več.",
      "error_unauthorized": "To spremembo lahko naredi samo skrbnik.",
      "plate": "Registrska tablica"
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
    .badge + .badge { margin-left: 6px; }
    .badge.warn { background: rgba(249, 168, 37, .18); color: var(--warning-color, #f57f17); }
    .badge.info { background: rgba(var(--rgb-primary-color, 3, 169, 244), .15); color: var(--primary-color); }

    /* --- Coches --- */
    .hero { display: flex; align-items: center; gap: 16px; padding: 12px 20px 0; flex-wrap: wrap; }
    .hero img { width: 380px; max-width: 100%; margin: -4px 0 -8px -16px; }
    .hero .who { flex: 1; min-width: 200px; }
    .hero .n { font-size: 26px; }
    .hero .m { color: var(--secondary-text-color); margin: 2px 0 10px; display: flex; align-items: center; gap: 4px 10px; flex-wrap: wrap; }
    .chead .nm { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .plate { display: inline-flex; align-items: stretch; height: 22px; flex: none; background: #fff; color: #111; border: 1.5px solid #1b1b1b;
      border-radius: 4px; overflow: hidden; line-height: 1; font-family: "DIN 1451", "Barlow Semi Condensed", "Roboto Condensed", "Arial Narrow", sans-serif; }
    .plate .eu { width: 12px; background: #0b3fa8; color: #fff; font-size: 7px; padding: 2px 0 1px; display: flex; flex-direction: column;
      align-items: center; justify-content: space-between; font-family: Arial, sans-serif; }
    .plate .num { display: flex; align-items: center; padding: 0 6px; font-size: 15px; font-weight: 500; letter-spacing: .03em; white-space: nowrap; }
    .plate .seals { display: inline-flex; flex-direction: column; gap: 2px; margin: 0 4px; }
    .plate .seals i { display: block; width: 5px; height: 5px; border-radius: 50%; border: 1px solid #444; }
    .kv { display: flex; gap: 26px; margin-top: 8px; flex-wrap: wrap; }
    .kv div { font-size: 13px; color: var(--secondary-text-color); } .kv b { display: block; font-size: 18px; font-weight: 400; color: var(--primary-text-color); }
    .chips { padding: 14px 20px 2px; }
    .people { display: flex; flex-wrap: wrap; align-items: center; gap: 0 6px; padding: 6px 20px 0; font-size: 13px; }
    .people .lbl { display: inline-flex; gap: 6px; align-items: center; color: var(--secondary-text-color); margin: 0 6px 6px 0; padding: 0; border: 0;
      font-size: 13px; --mdc-icon-size: 18px; }
    .people .chip { margin-bottom: 6px; }
    .people .none { color: var(--secondary-text-color); margin: 0 10px 6px 0; }
    .people .link { margin-bottom: 6px; }
    .ro { display: flex; gap: 10px; align-items: center; margin: 0 0 14px; padding: 10px 14px; border-radius: 10px;
      background: rgba(var(--rgb-primary-color, 3, 169, 244), .1); color: var(--primary-text-color); font-size: 14px; --mdc-icon-size: 20px; }
    .ro ha-icon { color: var(--primary-color); }
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
    :host([dark]) .hero img, :host([dark]) .chead img { background: ${STUDIO_BG}; }
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
    .box.ro { cursor: default; opacity: .8; }
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
    .dlg.dark .prev { background: ${STUDIO_BG}; }
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
      this._state = null; // lo que devuelve "state" (panel/)
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
      // Tema oscuro: fondo de estudio detrás de las fotos (STUDIO_BG).
      this.toggleAttribute("dark", this._dark());
      if (first) this._load();
      else if (language !== this._language()) this._render();
      this._syncMenu();
    }

    set narrow(narrow) {
      this._narrow = narrow;
      this._syncMenu();
    }

    // --- Idioma y textos ---------------------------------------------------------

    /** ¿Tema oscuro? (lo dice Home Assistant: el del usuario o el del sistema). */
    _dark() {
      return Boolean(((this._hass || {}).themes || {}).darkMode);
    }

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

    /** ¿Puede cambiar cosas? (los que no son administradores, solo miran). */
    _admin() {
      return !this._state || this._state.admin !== false;
    }

    /** Pestañas que puede ver quien está mirando. */
    _tabs() {
      return TABS.filter(([, , adminOnly]) => !adminOnly || this._admin());
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
      if (!this._tabs().some(([key]) => key === this._tab)) this._tab = "cars";
      const tabs = this._tabs().map(
        ([key, icon]) =>
          `<button class="${key === this._tab ? "on" : ""}" data-action="tab" data-tab="${key}"><ha-icon icon="${icon}"></ha-icon>${this._t(`tab_${key}`)}</button>`
      ).join("");
      let view;
      if (this._error) view = `<div class="empty">${escapeHtml(this._error)}<br><br><button class="btn o" data-action="reload">${this._t("retry")}</button></div>`;
      else if (!this._state) view = `<div class="empty">${this._t("loading")}</div>`;
      else if (!this._state.cars.length) view = `<div class="empty">${this._t("no_cars")}</div>`;
      else view = (this._admin() ? "" : `<div class="ro"><ha-icon icon="mdi:eye-outline"></ha-icon>${this._t("read_only")}</div>`) + this[`_view_${this._tab}`]();
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
      if (!this._admin() && !READ_ONLY_ACTIONS.has(target.dataset.action)) return;
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
      const mine = car.mine ? `<span class="badge ok"><ha-icon icon="mdi:account-check"></ha-icon>${this._t("mine")}</span>` : "";
      return `<div class="card">
        <div class="hero">
          ${photo ? `<img src="${escapeHtml(photo)}" alt="">` : ""}
          <div class="who">
            <div class="n">${escapeHtml(car.name)}</div>
            <div class="m"><span>${escapeHtml([car.model, car.color].filter(Boolean).join(" · "))}</span>${this._plateTag(car)}</div>
            ${badge}${mine}
            <div class="kv">
              ${car.battery == null ? "" : fact(`${this._number(car.battery)} %`, "battery")}
              ${car.range == null ? "" : fact(`${this._number(Math.round(car.range))} km`, "range")}
              ${car.odometer == null ? "" : fact(`${this._number(Math.round(car.odometer))} km`, "odometer")}
            </div>
          </div>
          ${this._admin() ? `<button class="btn o" data-action="appearance" data-car="${escapeHtml(car.id)}"><ha-icon icon="mdi:pencil"></ha-icon>${this._t("appearance")}</button>` : ""}
        </div>
        ${chips.length ? `<div class="chips">${chips.join("")}</div>` : ""}
        ${this._peopleRow(car)}
        <div class="grid3">
          ${this._maintenanceTile(car)}
          ${car.itv_available ? this._itvTile(car) : ""}
          ${this._insuranceTile(car)}
        </div>
      </div>`;
    }

    /** Recuadro con engranaje; `body` va vacío si el apartado está sin configurar. */
    _tile(car, kind, icon, level, body) {
      const gear = !this._admin() ? "" : `<button class="gear" data-action="gear" data-kind="${kind}" data-car="${escapeHtml(car.id)}" aria-label="${this._t("configure")}"><ha-icon icon="mdi:cog"></ha-icon></button>`;
      const head = `<div class="h"><ha-icon icon="${icon}"></ha-icon><span>${this._t(`section_${kind}`)}</span>${gear}</div>`;
      if (!body && !this._admin()) return `<div class="tile off">${head}<div class="v">${this._t("not_set")}</div></div>`;
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
      const admin = this._admin();
      const box = (state, action, extra) => {
        const icon = `<ha-icon icon="mdi:${state === "y" ? "checkbox-marked" : state === "some" ? "minus-box" : "checkbox-blank-outline"}"></ha-icon>`;
        // En solo lectura se ve lo marcado, pero no se puede tocar.
        if (!admin) return `<td><span class="box ${state} ro" role="checkbox" aria-checked="${state === "y"}" aria-readonly="true">${icon}</span></td>`;
        return `<td><button class="box ${state}" data-action="${action}" data-car="${escapeHtml(car.id)}" ${extra} aria-pressed="${state === "y"}">${icon}</button></td>`;
      };
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
          const pen = notice.threshold == null || !admin
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
      const others = admin && this._state.cars.length > 1;
      return `<div class="card" data-car-card="${escapeHtml(car.id)}">
        <div class="chead">
          ${photo ? `<img src="${escapeHtml(photo)}" alt="">` : ""}
          <div class="n"><span class="nm">${escapeHtml(car.name)}${this._plateTag(car)}</span><small>${escapeHtml(car.model)}</small></div>
          ${others ? `<button class="btn o" data-action="copy-alerts" data-car="${escapeHtml(car.id)}"><ha-icon icon="mdi:content-copy"></ha-icon>${this._t("copy_from")}</button>` : ""}
        </div>
        <div class="wide"><table>
          <tr><th>${this._t("notify_to")}</th>${targets.map((target) =>
            `<th><div class="dev ${target.kind}"><u><ha-icon icon="${TARGET_ICONS[target.kind] || TARGET_ICONS.service}"></ha-icon></u>${escapeHtml(target.name)}</div></th>`).join("")}</tr>
          ${rows.join("")}
        </table></div>
        ${!admin ? "" : `<div class="foot ${dirty ? "dirty" : ""}">
          <span>${dirty ? this._t("unsaved") : this._t("alerts_help")}</span>
          ${changedThresholds ? `<button class="btn o" data-action="reset-thresholds" data-car="${escapeHtml(car.id)}"><ha-icon icon="mdi:restore"></ha-icon>${this._t("factory_thresholds")}</button>` : ""}
          ${dirty ? `<button class="btn o" data-action="discard-alerts" data-car="${escapeHtml(car.id)}">${this._t("discard")}</button>
                     <button class="btn" data-action="save-alerts" data-car="${escapeHtml(car.id)}">${this._t("save")}</button>` : ""}
        </div>`}
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
        const base = `${pick.trim || ""}|${pick.color || ""}`;
        // Con la llanta elegida, su foto (p. ej. el Max sin tapacubos), si la hay.
        const photo = (choosable && model.photos[`${base}|${pick.wheels}`]) || model.photos[base] || model.photos["|"];
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
      dialog.root.querySelector(".dlg").classList.toggle("dark", this._dark());
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
         <div class="ifoot">${this._admin() ? `<button class="gearb" data-action="configure" aria-label="${this._t("configure")}"><ha-icon icon="mdi:cog"></ha-icon></button>` : ""}<span></span>${buttons || ""}
           <button class="tb" data-action="close">${this._t("close")}</button></div>`,
        (action, open, target) => {
          if (action === "configure" && this._admin()) {
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
        ${this._admin() ? `<button class="tb fill" data-action="register">${this._t("mt_register")}</button>` : ""}`;
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
        this._admin() ? `<button class="tb fill" data-action="register">${this._t("itv_register")}</button>` : "", (action, open) => {
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

  // ── src/68_personas.js ────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Personas de cada coche: a quién pertenece (pestaña "Coches")
  // ---------------------------------------------------------------------------
  // Las personas son las de Home Assistant (Ajustes → Personas). De momento
  // solo se enseña de quién es cada coche ("Tuyo" si es de quien mira); más
  // adelante servirá para decidir quién puede hacer qué con él.
  install(class {
    /** Fila "Personas" de la tarjeta del coche (con su botón, si se puede cambiar). */
    _peopleRow(car) {
      const people = car.people || [];
      const names = people.length
        ? people.map((person) => `<span class="chip"><ha-icon icon="mdi:account"></ha-icon>${escapeHtml(person.name)}</span>`).join("")
        : `<span class="none">${this._t("people_none")}</span>`;
      const edit = this._admin() && (this._state.people || []).length
        ? `<button class="link" data-action="people" data-car="${escapeHtml(car.id)}">${this._t("people_edit")}</button>`
        : "";
      return `<div class="people"><span class="lbl"><ha-icon icon="mdi:account-multiple"></ha-icon>${this._t("people")}</span>${names}${edit}</div>`;
    }

    /** Ventana para elegir las personas de un coche. */
    _do_people(data) {
      const car = this._car(data.car);
      const chosen = new Set((car.people || []).map((person) => person.id));
      const boxes = (this._state.people || []).map((person) =>
        `<label class="check"><input type="checkbox" name="${escapeHtml(person.id)}" ${chosen.has(person.id) ? "checked" : ""}>${escapeHtml(person.name)}</label>`).join("");
      openDialog(
        `<h2>${this._t("people_title", { name: escapeHtml(car.name) })}</h2><p>${this._t("people_help")}</p>
         ${boxes}
         <div class="err"></div>
         <div class="btns"><button class="tb" data-action="close">${this._t("cancel")}</button><button class="tb fill" data-action="ok">${this._t("save")}</button></div>`,
        (action, dialog) => {
          if (action !== "ok") return undefined;
          const people = Object.entries(dialog.values()).filter(([, on]) => on).map(([id]) => id);
          dialog.close();
          return this._run("set_people", { vehicle_id: car.id, people }, this._t("saved"));
        }
      );
    }
  });

  // ── src/69_matricula.js ───────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Placa de matrícula (pestañas "Coches" y "Avisos")
  // ---------------------------------------------------------------------------
  // Placa genérica europea: franja azul con las estrellas y la letra del país
  // de la cuenta, y la matrícula con el formato de ese país (lo pone
  // plates.py: "parts" trae el texto; con dos partes, Alemania, entre ellas
  // van los dos sellos). Sin matrícula, no se pinta nada.
  install(class {
    _plateTag(car) {
      const plate = car.plate;
      if (!plate || !plate.parts || !plate.parts.length) return "";
      const seals = `<span class="seals" aria-hidden="true"><i></i><i></i></span>`;
      const text = plate.parts.map((part) => escapeHtml(part)).join(seals);
      const label = `${this._t("plate")} ${plate.parts.join(" ")}`;
      return `<span class="plate" role="img" aria-label="${escapeHtml(label)}">
        <span class="eu">${PLATE_STARS}<span>${escapeHtml(plate.code)}</span></span><span class="num">${text}</span></span>`;
    }
  });

  // ── src/90_registro.js ────────────────────────────────────────────────────
  // ---------------------------------------------------------------------------
  // Alta del panel en Home Assistant
  // ---------------------------------------------------------------------------
  customElements.define(TAG, DecDeepalPanel);
})();
