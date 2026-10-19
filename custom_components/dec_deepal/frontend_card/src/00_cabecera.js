// =============================================================================
// DEC Deepal — Tarjeta para los paneles de Home Assistant
// =============================================================================
//
//   type: custom:dec-deepal-card
//   device_id: <dispositivo del coche>     (opcional: si falta, el primero)
//   main_value: range | battery | both     (opcional: range; 2.6.0b8)
//
// Y la misma tarjeta con el coche visto desde arriba (2.5.0b5):
//
//   type: custom:dec-deepal-top-card
//   device_id: <dispositivo del coche>
//   orientation: horizontal | vertical     (opcional: horizontal)
//   main_value: range | battery | both     (opcional: range)
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
