# Avisos de terceros y agradecimientos

DEC Deepal es una reescritura desde cero, pero reutiliza conocimiento y, en
algunos puntos, código de otros proyectos con licencia MIT. La licencia MIT
obliga a conservar su aviso de copyright; se recogen aquí.

## ha-deepal-spain-dec (proyecto anterior de la comunidad)

- Repositorio: <https://github.com/manuelem1984/ha-deepal-spain-dec>
- Licencia: MIT — Copyright (c) 2026 Comunidad Deepal España (DEC) - manuelem1984
- Qué se reutiliza: cifrado del login, descifrado MQTT, firma de comandos,
  cliente MQTT de una sola lectura, clasificación de errores, diseño del PIN
  con Opción A / Opción B, fotos por versión y color, iconos `dec:`.

## Deepal Alternative (ha-deepal-alternative)

- Repositorio: <https://github.com/Sunek0/ha-deepal-alternative>
- Licencia: MIT — Copyright (c) 2026 Deepal Alternative contributors
- Qué se reutiliza (adaptado, no copiado tal cual):
  - Formato de los comandos con PIN: puertas (`{"command": "lock", "open": ...}`)
    y ventanillas (`{"command": "window", "open": ..., "openType": 10}`).
  - Petición completa del endpoint REST de estado (`vechileCriteria` con todas
    las categorías) y su interpretación (décimas de grado, presión en kPa,
    `driverLock == 0` = bloqueado).
  - Escala de los asientos por MQTT (0-3 directo; `6` = módulo dormido → desconocido).
  - Códigos de error adicionales (`HW_1_1_01_047`, `HW_1_1_01_073`,
    `HW_1_1_01_074`, `COMMON_1_1_01_001` en `serial-no/get`, `46000`,
    `APIGW_-1_7_01_004`, `APIGW_1_7_02_001`).
  - Renovación de sesión con caducidad del JWT, ventana de 30 min y una sola
    petición a la vez.
  - Cola de comandos por vehículo, tiempos de espera de luces (30 s) y claxon
    (6 s), mantenimiento del valor optimista durante 120 s y reversión si el
    coche rechaza el comando.
  - Conservar el último valor válido de asientos/volante/desempañado cuando el
    coche no lo informa.
  - Pista de versión (Pro/Max) a partir de las capacidades del vehículo.

Texto de la licencia MIT de Deepal Alternative:

```
MIT License

Copyright (c) 2026 Deepal Alternative contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Iconos

Los iconos incluidos en `custom_components/dec_deepal/icons/svg/` proceden de
Material Symbols (Google, Apache 2.0) y Material Design Icons (Pictogrammers,
Apache 2.0), vía Iconify. Detalle por icono en
`custom_components/dec_deepal/icons/README.md`.

## Material Design Icons (Pictogrammers)

- Web: <https://pictogrammers.com/library/mdi/> · paquete `@mdi/svg`
- Licencia: Pictogrammers Free License (libre, compatible con GPL; permite
  usar, modificar y redistribuir los iconos).
- Qué se reutiliza: los iconos propios de `icons/svg/` de puertas, capó y
  maletero están **derivados** de `mdi:car-door` y `mdi:car-hatchback`:
  - `door_front_left_closed.svg` es `mdi:car-door` sin cambios;
    `door_front_right_*` es su espejo; las `*_open` son la misma puerta en
    perspectiva oblicua; las `door_rear_*` son un dibujo propio con el mismo
    lenguaje.
  - `hood_*.svg` y `trunk_*.svg` usan la silueta de `mdi:car-hatchback` con la
    tapa del capó o el portón levantados (o su junta, cerrados).
- `icons/reserva/charge_cover_*.svg` (tapa de carga con el puerto CCS2) es un
  dibujo propio.

