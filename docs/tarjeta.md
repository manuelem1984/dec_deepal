# Tarjeta DEC Deepal

Una tarjeta para los paneles de Home Assistant con tu coche de un vistazo. Se
instala sola con la integración: no hay que añadir recursos ni copiar archivos.

## Añadirla

Panel → **Editar** → **Añadir tarjeta** → buscar **DEC Deepal** → elegir el
coche. En YAML:

```yaml
type: custom:dec-deepal-card
device_id: <dispositivo del coche>   # opcional: si falta, el primero
```

Con dos coches, una tarjeta por coche.

### La misma tarjeta, con la vista de planta

Desde la 2.5.0b5 hay una segunda tarjeta, **DEC Deepal · Vista planta**:
es la misma (cabecera, testigos, batería, los seis botones y sus ventanas),
pero con el coche visto desde arriba, que es donde mejor se ve qué puerta o
ventanilla está abierta. Se añade igual, buscando **DEC Deepal**. En YAML:

```yaml
type: custom:dec-deepal-top-card
device_id: <dispositivo del coche>   # opcional: si falta, el primero
orientation: horizontal              # o "vertical"
```

- `horizontal` (por defecto): el coche tumbado, con el morro a la izquierda.
  La tarjeta queda casi igual de alta que la otra.
- `vertical`: el coche de pie, con el morro arriba. La tarjeta es más alta.

Las dos tarjetas pueden estar a la vez en el mismo panel. Si el modelo no
tiene vista de planta, se enseña la imagen DEC.

## Tarjeta del cargador

`custom:dec-deepal-charger-card`: ver `docs/cargadores.md`.

## Ventana de carga

Pulsar la franja de la batería (icono, autonomía, estado de carga y barra)
abre la ventana de carga, igual en las dos tarjetas (2.5.0b6):

- La **vista de carga**: el coche de lado con el cable en verde si carga, en
  gris si está enchufado sin cargar, y sin cable si no lo está. Va sobre el
  fondo de la ventana, en tema claro y en oscuro.
- El **porcentaje**, la autonomía y la barra (animada mientras carga).
- **Tiempo restante** y a qué hora termina, **corriente** y **conector**
  (AC · Tipo 2 o DC · CCS2), cuando hay algo enchufado. Al tiempo que da el
  coche se le suman 15 min de **equilibrado** de la batería («Incluye 15 min
  de equilibrado»), salvo que se quite en Panel → Ajustes (2.5.2b1). El
  sensor «Tiempo de carga restante» no cambia: es el dato del coche.
- La **autonomía**, sin decimales («318 km»), aunque la entidad los tenga.
- El botón **⟳** de la cabecera actualiza los datos (como el de la tarjeta);
  gira mientras tanto. Abajo solo está «Cerrar».
- **Esta carga**: cuánto ha subido y desde cuándo, mientras carga.
- **Última carga**: de qué porcentaje a cuál, cuándo y cuánto duró.

"Esta carga" y "Última carga" las apunta la integración desde que se instala
esta versión (no hay historial anterior) y se conservan al reiniciar. Son
atributos del sensor "Cargando" (`carga_actual` y `ultima_carga`), por si se
quieren usar en automatizaciones. El mismo sensor lleva `minutos_equilibrado`
(15, o 0 si el ajuste está quitado). La ventana se actualiza sola mientras está
abierta.

## Qué muestra

- **Cabecera:** nombre del coche, "Actualizado: hoy, 14:11" (el último informe
  del coche) y el botón de actualizar.
- **Vista isométrica** (o la de planta, en la otra tarjeta), que cambia sola
  con puertas, capó, maletero, ventanillas y luces. Tocarla no hace nada.
- **Línea de estado** (encima de la batería, a la derecha): un tic verde si
  no hay avisos. Si los hay, el icono de cada testigo encendido: en rojo
  los graves (frenos, líquido de frenos, batería de 12 V,
  refrigerante y sistema de propulsión) y en ámbar el resto (ABS,
  dirección asistida, neumáticos, potencia limitada, batería baja y pila
  del mando).
- **Batería:** icono según el nivel (verde con el 50 % o más, amarillo por
  debajo del 50 %, rojo por debajo del 15 %; con un rayo si está cargando),
  autonomía, estado de carga y la barra.
- **Seis botones** (dos filas de tres):

| Botón | Qué hace | PIN |
| --- | --- | --- |
| **Confort** | Abre la ventana de confort | No |
| **Bloqueo** | Bloquea o desbloquea las puertas | Sí |
| **Maletero** | Abre o cierra el maletero | Sí |
| **Ventilar** | Entreabre las ventanillas, o las cierra | Sí |
| **Localizar vehículo** | Abre un menú: Luces, Claxon, o Luces y claxon | No |
| **Otros** | Abre un menú: Manual y Mantenimiento | No |

### Botón "Otros"

Abre un menú con dos opciones:

- **Manual** (libro abierto): abre el manual de usuario (PDF) en el
  navegador, en una pestaña nueva. El manual no viene dentro de la
  integración: es un enlace a la web del fabricante. Sale del catálogo según
  el modelo y se puede cambiar en *panel DEC Deepal → Ajustes → Manual*. Si el
  modelo no tiene manual, la opción no aparece.
- **Mantenimiento** (llave inglesa): la ventana de mantenimiento, disponible
  siempre. Si el coche no lo tiene activado, explica cómo hacerlo.
- **ITV** (portapapeles): días que quedan, fecha límite, matriculación, última
  ITV, historial y el botón *Registrar ITV pasada*.
- **Seguro** (escudo): días para la renovación y para desistir, compañía, tipo,
  número de póliza y botones para llamar a la asistencia y a la compañía (si
  se pusieron los teléfonos).

Las cuatro opciones salen de dos en dos. ITV y Seguro tienen también su
testigo en la línea de estado, como el de mantenimiento.

Cuando la revisión está próxima o vencida, el texto del botón cambia a
"Revisión en 47 días" o "Revisión vencida".

### Testigo de mantenimiento

Si el coche tiene el mantenimiento activado (*panel DEC Deepal → Coches → Mantenimiento*), en
la línea de estado aparece una **llave inglesa** cuando quedan 2 meses o
3.000 km para la revisión: ámbar, o roja si está vencida. Es el único testigo
que se puede pulsar. Abre una ventana con los días y kilómetros que quedan, la
fecha prevista, lo que incluye la revisión, el historial y el botón
**Registrar mantenimiento**, que pide confirmación y anota la revisión con la
fecha de hoy y los kilómetros actuales. Ver
[avisos-y-mantenimiento.md](avisos-y-mantenimiento.md).

### Ventana de Confort

La vista interior con los botones encima de la foto:

- **Volante** calefactado (encendido / apagado).
- En cada asiento delantero, **ventilación** (izquierda) y **calefacción**
  (derecha). Cada toque sube un nivel: 1, 2, 3 y apagado.
- Los iconos no llevan color para no chocar con la vista: **blanco =
  encendido** (con su nivel), **atenuado = apagado**. Lo encendido se ve
  además iluminado en la propia foto (naranja = calor, azul = ventilación).
- **Temperatura** (− / +, de medio en medio grado) y **climatizador**
  encendido / apagado.
- Debajo: temperatura interior, humedad, ventilador y aire exterior o
  recirculación.

### Órdenes con PIN

Bloqueo, Maletero y Ventilar piden **confirmación**. Si en la integración
tienes el modo "con desbloqueo previo", la tarjeta hace sola el desbloqueo y
después la orden. Si el control con PIN no está activado, esos tres botones
solo muestran el estado y avisan de cómo activarlo.

## Cómo funciona por dentro

- JavaScript plano, sin dependencias y sin Node. El código está repartido en
  `frontend_card/src/`; Home Assistant carga un solo fichero,
  `frontend_card/dec-deepal-card.js`, que se **genera** uniendo esos módulos
  (ver "Tocar la tarjeta", más abajo).
- **Encuentra las entidades sola:** cada entidad de la integración tiene una
  clave interna (`translation_key`) que no cambia aunque se renombre. La
  tarjeta busca, entre las entidades del dispositivo elegido, la de cada
  clave. Una prueba comprueba que todas las claves que usa existen.
- **Carga:** la trae `dec-icons.js`, así llega por los mismos caminos que los
  iconos (ver [iconos.md](iconos.md)). Tras un reinicio, si llega tarde, Home
  Assistant la vuelve a pintar sola.
- Solo repinta cuando cambia alguna de sus entidades, y la imagen solo se
  vuelve a pedir cuando cambia.
- La posición de los botones sobre la foto interior y los recortes de las
  imágenes están en `src/10_constantes.js` (`HOTSPOTS`, `INTERIOR`,
  `ISOMETRIC`), hoy para el Deepal S05.

## Tocar la tarjeta

El código está en `custom_components/dec_deepal/frontend_card/src/`, un
fichero por parte. Se unen por orden de nombre:

| Fichero | Qué contiene |
|---|---|
| `00_cabecera.js` | Comentario de cabecera: qué hace la tarjeta |
| `10_constantes.js` | Recortes de las imágenes, botones de Confort, testigos |
| `20_textos.js` | Textos por idioma. **Generado** desde `idiomas/` |
| `21_idioma.js` | Qué idioma toca y cómo se rellenan los textos |
| `30_estilos.js` | Estilos de la tarjeta y de las ventanas |
| `40_dialogo.js` | La ventana emergente que usan todos los menús |
| `50_tarjeta.js` | La tarjeta: entidades, pintado, órdenes y pulsaciones |
| `60_localizar.js` … `65_confort.js` | Una ventana o menú por fichero |
| `90_registro.js` | Alta de la tarjeta en Home Assistant |

**Cambiar algo:**

1. Editar el fichero de `src/`.
2. Reconstruir: `python tools/construir_tarjeta.py` (no hace falta instalar
   nada). `python tools/generar_idiomas.py` también la reconstruye.
3. Subir **tanto** `src/` **como** `dec-deepal-card.js`. Si se olvida el paso
   2, una prueba falla y lo dice.

`dec-deepal-card.js` no se edita a mano: lo dice su primera línea.

**Añadir una ventana:** un fichero nuevo `src/6x_nombre.js` con sus métodos
dentro de `install(class { ... })` (dentro, `this` es la tarjeta), y la
llamada que la abre en `_onClick` (`50_tarjeta.js`) o en el menú "Otros".
El código va sangrado dos espacios porque acaba dentro de una función.

### Pruebas en un navegador

`tests_tarjeta/` prueba la tarjeta en un navegador de verdad, con un Home
Assistant falso (`banco.js`): lo que pinta, los idiomas, cada ventana y lo
que se le pide al coche al pulsar. Si la tarjeta lanza un error de
JavaScript, la prueba falla. GitHub las ejecuta en cada subida.

```
pip install -r tests_tarjeta/requirements.txt
playwright install chromium          # o usar uno instalado: DEC_NAVEGADOR=msedge
pytest -c tests_tarjeta/pytest.ini tests_tarjeta
```

Para mirarla a mano sin Home Assistant: abrir `tests_tarjeta/pagina.html` en
el navegador y escribir en la consola `banco.montar()`; con
`banco.cambiar({"climate.cabin_climate": ["heat_cool"]})` llega otra lectura
del coche.

Al arreglar un fallo de la tarjeta, añadir aquí la prueba que lo habría
detectado.

## Idiomas

La tarjeta está en español, inglés, portugués, italiano, polaco, alemán,
francés, neerlandés, noruego, danés, griego y esloveno, según el idioma de
cada usuario en Home Assistant (catalán, gallego y euskera se ven en
español; cualquier otro, en inglés). Los textos se escriben en
`idiomas/<idioma>.json` (sección `tarjeta`) y la tabla `TEXTS`
(`src/20_textos.js`) se genera (ver [idiomas.md](idiomas.md)).

## Límites conocidos

- Hoy solo con las vistas del Deepal S05.
- Sin opciones todavía: no se puede elegir qué botones mostrar.
- Los niveles de los asientos se envían al coche con cada toque; el coche
  tarda unos segundos en confirmar.

## Tema oscuro

Con el tema oscuro de Home Assistant, detrás de la foto del coche se pinta una
luz de estudio suave (`STUDIO_BG`, en `10_constantes.js` de la tarjeta y del
panel) que se funde con la tarjeta: las partes oscuras del coche (techo,
alerón, zaga) no se pierden en el fondo. Las fotos no cambian y en tema claro
no se pinta nada. La tarjeta y el panel lo saben por `hass.themes.darkMode`.
