# Iconos propios (`dec:`)

- Guía completa: [docs/iconos.md](../../../docs/iconos.md).
- Registro de entidades y estados: [`icons.yaml`](icons.yaml).
- Los archivos van en [`svg/`](svg/) con el nombre `<entidad>.svg` o
  `<entidad>_<sufijo>.svg`.

## Origen y licencia de los iconos incluidos

| Archivo(s) | Origen | Colección | Licencia |
| --- | --- | --- | --- |
| `steering_wheel_heat.svg` | [Iconify](https://icon-sets.iconify.design/material-symbols/steering-wheel-heat/) | Material Symbols (Google) | Apache 2.0 |
| `indicator_left_on.svg` / `indicator_left_off.svg` | [Iconify](https://icon-sets.iconify.design/material-symbols/arrow-circle-left/) | Material Symbols (Google) | Apache 2.0 |
| `indicator_right_on.svg` / `indicator_right_off.svg` | [Iconify](https://icon-sets.iconify.design/material-symbols/arrow-circle-right/) | Material Symbols (Google) | Apache 2.0 |
| `high_beam_on.svg` / `high_beam_off.svg` | [Iconify](https://icon-sets.iconify.design/line-md/car-light-filled/) (reconstruido*) | line-md (Vjacheslav Trushkin) | MIT |
| `low_beam_on.svg` / `low_beam_off.svg` | [Iconify](https://icon-sets.iconify.design/line-md/car-light-dimmed-filled/) (reconstruido*) | line-md | MIT |
| `position_lamp_on.svg` / `position_lamp_off.svg` | [Iconify](https://icon-sets.iconify.design/line-md/car-light-twotone/) (reconstruido*) | line-md | MIT |

\* Los originales de line-md son animados (máscaras + trazos), incompatibles
con el sistema de iconos de Home Assistant. Se reconstruyeron a mano como un
único trazado relleno (carcasa del faro + rayos convertidos en cápsulas; los
"off" llevan una barra diagonal), verificando el resultado en un navegador.
Heredados del proyecto anterior (ha-deepal-spain-dec 1.3.1b15-b18).

Al añadir un icono, añade aquí su fila con origen y licencia.
