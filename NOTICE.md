# Avisos de terceros

## Aviso de licencia MIT

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
- `key_battery_low_*.svg` (la llave del Deepal S05) es un diseño propio de la
  Comunidad Deepal España.
- `icons/reserva/charge_cover_*.svg` (tapa de carga con el puerto CCS2) es un
  dibujo propio.

## Vista isométrica: colores y llantas

Las capas de color de la vista isométrica son las capas originales
repintadas por el proyecto. La llanta del Pro procede de una imagen oficial
de Deepal; la del Max sin tapacubos, de una fotografía cedida por un miembro
de la Comunidad Deepal España.
