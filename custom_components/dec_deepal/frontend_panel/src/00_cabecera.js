// =============================================================================
// DEC Deepal — Panel de la barra lateral de Home Assistant
// =============================================================================
// Una página propia (como la de Alarmo) donde se ve y se configura todo lo de
// los coches. El botón "Configurar" de la integración lleva aquí.
//
// Pestañas:
//   - Coches: una tarjeta por coche con su foto, versión, equipamiento (el de
//     su ficha del catálogo) y tres recuadros —mantenimiento, ITV y seguro—,
//     cada uno con un engranaje que abre su configuración. El botón
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
