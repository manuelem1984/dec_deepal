# Panel DEC Deepal

Una página propia en la barra lateral de Home Assistant, donde se ve y se
configura todo lo de los coches de un vistazo.

Aparece sola al instalar la integración (**DEC Deepal** en la barra lateral).
El botón **Configurar** de la integración (Ajustes → Dispositivos y servicios
→ DEC Deepal) lleva también aquí, como en Alarmo. Lo único que queda fuera es
añadir la cuenta y volver a iniciar sesión.

**Quién ve qué** (desde la 2.5.0b9):

- **Administradores:** todo, y lo pueden cambiar.
- **Resto de usuarios:** las pestañas **Coches** y **Avisos**, en solo
  lectura (un aviso arriba lo dice). Ven las fichas, a quién pertenece cada
  coche ("Tuyo" en los suyos) y a quién avisa de cada cosa, sin engranajes,
  casillas ni botones de guardar. La integración comprueba los permisos en
  cada orden: aunque se forzara el panel, no podrían cambiar nada.

### Matrícula

Junto al modelo y el color (Coches) y junto al nombre (Avisos) sale la
matrícula como una placa europea genérica: franja azul con la letra del país
de la cuenta y el texto con el formato de ese país (`plates.py`). Si no
encaja con el formato se enseña tal cual; sin matrícula, no sale.

### Personas de cada coche

En la tarjeta de cada coche, la fila **Personas** dice a quién pertenece:
personas de Home Assistant (Ajustes → Personas). El administrador las elige
con **Elegir**. Se guardan con el coche (por bastidor) y viajan en la copia
de seguridad. De momento solo se enseñan; más adelante servirán para decidir
quién puede hacer qué con cada coche.

## Pestañas

### Coches

Una tarjeta por coche: foto, versión, batería, autonomía y kilómetros; el
equipamiento de su ficha del catálogo (y si la ficha está verificada), y
tres recuadros. **Pulsar el recuadro abre su ficha**; su **engranaje**, la
configuración (desde la 2.5.0b3):

| Recuadro | Ficha (pulsar el recuadro) | Engranaje |
|---|---|---|
| Mantenimiento | Qué revisión toca, cuánto falta por tiempo y por kilómetros, las operaciones de esa revisión, lo que se añade en la siguiente, el historial y el enlace al manual. Botón **Registrar revisión hecha** | Revisiones ya pasadas, fecha y kilómetros de la última, y cada cuánto (el del manual u otro) |
| ITV | Fecha límite, matriculación, última ITV, las normas del país y el historial. Botón **Registrar ITV pasada** | Matriculación, si ya ha pasado alguna, y la próxima (calculada o a mano) |
| Seguro | Compañía, tipo, póliza (con copiar), la línea del año con el plazo para desistir, y los teléfonos para llamar con un toque | Compañía, póliza, tipo, renovación, días de preaviso (15, 30, 60 u otro) y teléfonos |

Un recuadro sin configurar abre directamente su formulario. Los formularios
van por bloques, con una explicación en cada uno, y terminan con un recuadro
verde que adelanta el resultado ("Próxima revisión: 29 jul 2027 o a los
20.000 km") según se escribe; nada se guarda hasta pulsar "Guardar". Apagar
"Activado" arriba a la derecha desactiva ese apartado (y quita sus entidades
y avisos).

El botón **Apariencia** abre una ventana para elegir modelo, versión, color
y llanta, con la foto del catálogo delante: cambia con lo que se va
eligiendo y nada se guarda hasta pulsar "Guardar". Cada versión dice qué
trae, y la llanta solo se pregunta cuando la versión deja elegirla. Guardar
recarga la integración: se crean las entidades de esa versión y se quitan
las que no le tocan.

### Avisos

Una tabla por coche, con los destinos en columnas (cada móvil con la app y
la campana de Home Assistant) y un apartado plegable por cada cosa:

| Apartado | Avisos |
|---|---|
| Carga | Iniciada, interrumpida, terminada |
| Testigos | Testigos del cuadro, neumáticos, pila del mando |
| Mantenimiento | Tiempo 1, 2 y 3 (60, 30 y 15 días); kilometraje 1, 2 y 3 (5.000, 2.500 y 1.000 km); cumplido |
| ITV | Avisos 1, 2 y 3 (60, 30 y 15 días); cumplida |
| Seguro | Desistimiento 1 y 2 (30 y 15 días antes del límite) y cumplido; renovación 1 y 2 (30 y 15 días); renovado |

- **Cada aviso tiene sus destinos.** La casilla del apartado marca todos sus
  avisos de golpe; con solo algunos marcados sale una raya.
- **Lápiz:** en los avisos con plazo, cambia los días o los kilómetros. Los
  plazos son de cada coche. El aviso 1 tiene que saltar antes que el 2, y el
  2 antes que el 3; si no, no deja guardar y lo explica. "Plazos de fábrica"
  los devuelve a su valor.
- **Guardar:** los cambios de un coche se quedan en borrador hasta pulsar
  "Guardar" (guardar recarga la integración).
- **Copiar de otro coche** trae sus avisos y plazos al borrador.
- Los avisos de **renovación del seguro** son nuevos en la 2.5.0 y nacen sin
  destinos.

### Datos

Descargar la copia (un enlace que se abre en el navegador, también desde la
app del móvil), enviarla a un móvil, cargarla y borrar los datos guardados
de un coche, estén o no en una cuenta.

### Diagnóstico

Lo que ha pasado desde el último reinicio —cambios de señales, órdenes con
la respuesta del servidor y avisos enviados—, con filtros por coche y por
tipo; la ficha que se le aplica a cada coche, y el fichero de diagnóstico de
la cuenta.

### Ajustes

Son de la cuenta, no de un coche (con varias cuentas, una tarjeta por cuenta).

- **Control remoto con PIN:** activarlo, el PIN (el de la app oficial de
  Deepal; se comprueba al guardar) y cómo se usan las órdenes: **Directo** o
  **Desbloquear antes**, con cuánto dura el desbloqueo y si avisa. Un solo
  PIN para todos los coches de la cuenta. El panel nunca recibe el PIN
  guardado: el campo sale vacío, y vacío significa "no cambiarlo".
- **Cargadores:** activarlos, quién puede desbloquear y cada cargador con
  sus entidades, coches, cobertura, desbloqueo, bloqueo al desenchufar,
  pérdidas y precio (ver `docs/cargadores.md`).
- **Límite de carga:** usarlo, el límite de cada coche, avisar al llegar y
  recordar cargar al 100 % cada 3-6 cargas (o hacerla sin preguntar).
- **Lectura de datos:** intervalo, despertar el coche cuando haga falta,
  **sumar el equilibrado** (15 min más al tiempo de carga de la ventana de
  carga; activado de fábrica), el enlace del manual (BEV o PHEV, según el
  coche) y el modo depuración.

## Tocar el panel

Como la tarjeta: JavaScript plano, sin dependencias y sin Node. El código
está en `custom_components/dec_deepal/frontend_panel/src/`, un fichero por
parte, y se une en `frontend_panel/dec-deepal-panel.js` con
`python tools/construir_tarjeta.py`.

| Fichero | Qué contiene |
|---|---|
| `00_cabecera.js` | Comentario de cabecera: qué hace el panel |
| `10_constantes.js` | Pestañas, apartados, iconos |
| `20_textos.js` | Textos por idioma. **Generado** desde `idiomas/` (sección `panel`) |
| `21_idioma.js` | Qué idioma toca y cómo se rellenan los textos |
| `30_estilos.js` | Estilos del panel y de las ventanas |
| `40_dialogo.js` | La ventana emergente de formularios y confirmaciones |
| `50_panel.js` | El panel: carga de datos, pestañas y pulsaciones |
| `60_coches.js` … `68_personas.js` | Una pestaña (o una ventana) por fichero |
| `90_registro.js` | Alta del panel en Home Assistant |

Cada pulsación lleva `data-action="algo"` y la atiende el método `_do_algo`.
En solo lectura solo se atienden las de `READ_ONLY_ACTIONS` (`10_constantes.js`).

El lado de la integración está en `panel/`, un módulo por pestaña con el
mismo nombre que su fichero del panel (`coches.py` ↔ `60_coches.js`,
`avisos.py` ↔ `61_avisos.js`...). Cada orden se declara con `@command`
(`panel/comun.py`), que por defecto exige ser administrador; solo `state` la
puede pedir cualquiera, y `estado.py` le quita lo de administración. Los
errores van con un código y el panel enseña el texto `error_<código>`.

**Idiomas:** el panel está en los doce idiomas de la integración (ver
[idiomas.md](idiomas.md)), según el idioma de cada usuario en Home Assistant.

### Pruebas

- En un navegador: `tests_tarjeta/test_panel.py`, con `banco_panel.js`
  haciendo de Home Assistant y de la integración (ver
  [tarjeta.md](tarjeta.md), "Pruebas en un navegador").
- Del lado de la integración: `tests/test_panel.py`.

Para mirarlo a mano sin Home Assistant: abrir
`tests_tarjeta/pagina_panel.html?iconos=1` y escribir en la consola
`banco.montar()`.

## Límites conocidos

- El historial se pierde al reiniciar Home Assistant.
- No se puede ocultar el panel de la barra lateral desde la integración (sí
  desde el perfil de cada usuario, como cualquier otro panel).
