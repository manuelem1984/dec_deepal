"""Cargador de ``vehicles/vehicles.yaml`` (modelos, versiones, colores, fotos).

Además de leer el catálogo, este módulo:

- **Reconoce** el modelo de cada coche de la cuenta (:meth:`VehicleRegistry.match`).
- Calcula las **funciones** efectivas de un coche según su modelo y versión
  (:meth:`VehicleModel.features_for`): así se crean solo las entidades que
  tienen sentido (p. ej. sin ventilación de asientos en el S05 Pro).
- Busca la **foto** que corresponde a versión + color (:meth:`VehicleModel.photo_for`).
- Carga las capas de las **vistas** del modelo ("Vista planta", "Vista
  isométrica"...), si tiene (``vistas:``; ver :mod:`.views`).
- Lee el **plan de mantenimiento** del modelo (``mantenimiento:``): cada
  cuánto toca la revisión y qué operaciones lleva cada una.
- Compone la **ficha** de cada coche (:meth:`VehicleModel.sheet`): lo que
  dice el modelo, cambiado por lo que diga su versión. Un modelo puede
  copiar a otro (``como:``). Ver la cabecera de ``vehicles.yaml``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from ..api.models import VehicleInfo
from ..textos_generados import CATALOGUE_TEXTS
from ..maintenance import (
    DEFAULT_INTERVAL_KM,
    DEFAULT_INTERVAL_MONTHS,
    MaintenancePlan,
    Operation,
)
from .errors import RegistryError, as_dict, as_str_list, read_yaml, require
from .views import ViewLayers, load_view

# ---------------------------------------------------------------------------
# Funciones conocidas (claves de "funciones" en el YAML)
# ---------------------------------------------------------------------------
FEATURE_MQTT: Final = "telemetria_mqtt"
FEATURE_CLIMATE: Final = "climatizacion"
FEATURE_LIGHTS_HORN: Final = "luces_claxon"
FEATURE_SEAT_HEAT: Final = "asientos_calefaccion"
FEATURE_SEAT_VENT: Final = "asientos_ventilacion"
FEATURE_WHEEL_HEAT: Final = "volante_calefactado"
FEATURE_DEFROST: Final = "desempanado"
FEATURE_PIN_COMMANDS: Final = "comandos_pin"
FEATURE_POWER_TAILGATE: Final = "porton_electrico"
FEATURE_FUEL: Final = "combustible"
FEATURE_CHARGE_LIMIT: Final = "limite_carga"

KNOWN_FEATURES: Final = frozenset(
    {
        FEATURE_MQTT,
        FEATURE_CHARGE_LIMIT,
        FEATURE_CLIMATE,
        FEATURE_LIGHTS_HORN,
        FEATURE_SEAT_HEAT,
        FEATURE_SEAT_VENT,
        FEATURE_WHEEL_HEAT,
        FEATURE_DEFROST,
        FEATURE_PIN_COMMANDS,
        FEATURE_POWER_TAILGATE,
        FEATURE_FUEL,
    }
)

#: Id del modelo de respaldo (obligatorio en el catálogo).
GENERIC_MODEL_ID: Final = "generico"

#: Vistas por capas conocidas (claves de "vistas" en el YAML). Cada una es una
#: entidad de imagen con su nombre en translations (``entity.image.<clave>``).
VIEW_TOP: Final = "top_view"
VIEW_ISOMETRIC: Final = "isometric_view"
VIEW_INTERIOR: Final = "interior_view"
VIEW_CHARGING: Final = "charging_view"
KNOWN_VIEWS: Final = (VIEW_TOP, VIEW_ISOMETRIC, VIEW_INTERIOR, VIEW_CHARGING)

#: Extensiones de foto admitidas, en orden de preferencia.
PHOTO_EXTENSIONS: Final = (".png", ".jpg", ".jpeg", ".webp")


def _battery_kwh(value: object, where: str) -> float | None:
    """Capacidad de la batería (``bateria_kwh``): un número positivo o nada."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise RegistryError(f"{where}.bateria_kwh: debe ser un número de kWh mayor que 0")
    return float(value)


@dataclass(frozen=True, slots=True)
class Trim:
    """Versión / acabado de un modelo."""

    id: str
    name: str
    description: str
    photo_group: str
    features: dict[str, bool] = field(default_factory=dict)
    #: Llanta fija de la versión ("" = la que elija el usuario).
    wheel: str = ""
    #: ¿Se ha comprobado la ficha de esta versión en un coche real?
    verified: bool = False
    #: Capacidad útil de la batería en kWh (``None`` = no se sabe).
    battery_kwh: float | None = None


@dataclass(frozen=True, slots=True)
class Color:
    """Color oficial de un modelo."""

    id: str
    name: str
    description: str
    #: Color aproximado (``#rrggbb``) para la muestra del panel ("" = no se sabe).
    swatch: str = ""


@dataclass(frozen=True, slots=True)
class VehicleModel:
    """Un modelo del catálogo."""

    id: str
    name: str
    #: Plantilla del nombre con versión, con ``{version}`` donde va la versión
    #: (p. ej. ``"Deepal S05 {version} (2024-25)"``). Vacía = "<nombre> <versión>".
    name_with_trim: str
    description: str
    manufacturer: str
    countries: tuple[str, ...]
    match_names: tuple[str, ...]
    match_series_codes: tuple[str, ...]
    features: dict[str, bool]
    photos_dir: Path
    default_photo: str
    trims: dict[str, Trim]
    colors: dict[str, Color]
    #: Vistas por capas del modelo: ``{clave de vista: capas}``.
    views: dict[str, ViewLayers] = field(default_factory=dict)
    #: Llantas que se pueden elegir; la primera es la de por defecto.
    wheel_options: tuple[str, ...] = ()
    #: Enlace al manual de usuario en PDF ("" = no tiene).
    manual_url: str = ""
    #: Plan de mantenimiento (intervalo y operaciones de cada revisión).
    maintenance: MaintenancePlan = field(default_factory=MaintenancePlan)
    #: Testigos que el coche enciende sin motivo: ni avisan ni salen en la tarjeta.
    silent_warnings: frozenset[str] = frozenset()
    #: Modelo del que se copió lo que este no escribe ("" = ninguno).
    based_on: str = ""

    def display_name(self, trim_id: str | None) -> str:
        """Nombre para mostrar, con la versión si se conoce.

        Ejemplo: ``"Deepal S05 Pro (2024-25)"`` (con plantilla) o
        ``"Deepal S05 (2024-25)"`` (sin versión elegida).
        """
        trim = self.trims.get(trim_id or "")
        if trim is None:
            return self.name
        if self.name_with_trim:
            return self.name_with_trim.replace("{version}", trim.name)
        return f"{self.name} {trim.name}"

    def wheel_for(self, trim_id: str | None, chosen: str | None) -> str | None:
        """Llanta que lleva el coche: la fija de la versión, la elegida o la de por defecto."""
        trim = self.trims.get(trim_id or "")
        if trim is not None and trim.wheel:
            return trim.wheel
        if chosen in self.wheel_options:
            return chosen
        return self.wheel_options[0] if self.wheel_options else None

    def features_for(self, trim_id: str | None) -> dict[str, bool]:
        """Funciones efectivas: las del modelo, cambiadas por las de la versión.

        Si no se sabe la versión, se usan las del modelo (se crean todas las
        entidades posibles; el usuario puede elegir la versión en Configurar).
        """
        result = dict(self.features)
        trim = self.trims.get(trim_id or "")
        if trim is not None:
            result.update(trim.features)
        return result

    def sheet(self, trim_id: str | None) -> dict[str, object]:
        """Ficha que se le está aplicando a un coche (para los diagnósticos).

        Dice de dónde sale: de su versión, o del modelo tal cual (la versión
        más equipada) si el coche no tiene versión o no existe en el catálogo.
        """
        trim = self.trims.get(trim_id or "")
        if self.id == GENERIC_MODEL_ID:
            source = "genérica (coche sin modelo elegido)"
        elif trim is not None:
            source = "de su versión"
        elif trim_id:
            source = f"del modelo (la versión '{trim_id}' no está en el catálogo)"
        else:
            source = "del modelo (sin versión elegida)"
        return {
            "modelo": self.id,
            "version": trim.id if trim is not None else None,
            "origen": source,
            "copia_de": self.based_on or None,
            "verificada": bool(trim is not None and trim.verified),
            "funciones": dict(sorted(self.features_for(trim_id).items())),
            "testigos_sin_aviso": sorted(self.silent_warnings),
        }

    def has(self, feature: str, trim_id: str | None = None) -> bool:
        """¿Tiene esta función (con la versión indicada)?"""
        return bool(self.features_for(trim_id).get(feature, False))

    def photo_for(
        self, trim_id: str | None, color_id: str | None, wheel: str | None = None
    ) -> Path | None:
        """Foto exacta para versión + color (+ llanta), o la de por defecto, o ``None``.

        Busca ``<carpeta_fotos>/<grupo_foto>_<color>.<ext>`` con cada extensión
        admitida. Con una llanta elegible que no es la de serie (la primera de
        ``llantas``, p. ej. ``open`` = sin tapacubos), antes prueba
        ``<grupo_foto>_<color>_<llanta>.<ext>``. Si falta, la de serie; si
        tampoco, ``<carpeta_fotos>/<foto_defecto>``; y si no, ``None`` (la
        entidad de foto se mostrará como no disponible).
        """
        trim = self.trims.get(trim_id or "")
        if trim is not None and color_id in self.colors:
            names = [f"{trim.photo_group}_{color_id}"]
            if wheel and wheel in self.wheel_options and wheel != self.wheel_options[0]:
                names.insert(0, f"{trim.photo_group}_{color_id}_{wheel}")
            for name in names:
                for extension in PHOTO_EXTENSIONS:
                    candidate = self.photos_dir / f"{name}{extension}"
                    if candidate.is_file():
                        return candidate
        default = self.photos_dir / self.default_photo
        return default if default.is_file() else None

    def match_score(self, vehicle: VehicleInfo) -> int:
        """Cuánto encaja este coche con este modelo (0 = nada).

        El código de serie exacto es lo que más pesa; después, el texto más
        largo de ``nombre_contiene`` que aparezca en sus nombres o códigos.
        """
        if vehicle.series_code and vehicle.series_code in self.match_series_codes:
            return 1000
        texts = " ".join(
            filter(None, (vehicle.model_name, vehicle.series_name, vehicle.model_code))
        ).upper()
        return max((len(name) for name in self.match_names if name.upper() in texts), default=0)

    def matches(self, vehicle: VehicleInfo) -> bool:
        """¿Encaja este coche de la cuenta con este modelo?"""
        return self.match_score(vehicle) > 0


@dataclass(frozen=True, slots=True)
class VehicleRegistry:
    """Todos los modelos del catálogo."""

    models: dict[str, VehicleModel]

    @property
    def generic(self) -> VehicleModel:
        """Modelo de respaldo para coches no catalogados."""
        return self.models[GENERIC_MODEL_ID]

    def get(self, model_id: str | None) -> VehicleModel:
        """Modelo por id; el genérico si no existe."""
        return self.models.get(model_id or "", self.generic)

    def match(self, vehicle: VehicleInfo, country_id: str | None = None) -> VehicleModel:
        """Reconoce el modelo de un coche; el genérico si no encaja ninguno.

        Si encajan varios, gana el que lo hace con el texto más largo: así
        "PHEV" (S05 PHEV) se prefiere a "S05" (S05 EV) cuando están los dos.
        """
        best: tuple[int, VehicleModel] | None = None
        for model in self.models.values():
            if model.id == GENERIC_MODEL_ID:
                continue
            if country_id and model.countries and country_id not in model.countries:
                continue
            score = model.match_score(vehicle)
            if score and (best is None or score > best[0]):
                best = (score, model)
        return best[1] if best else self.generic

    def for_country(self, country_id: str) -> list[VehicleModel]:
        """Modelos ofrecidos en un país (para el selector de Configurar)."""
        return [
            model
            for model in self.models.values()
            if not model.countries or country_id in model.countries
        ]


def _features(raw: object, where: str) -> dict[str, bool]:
    """Lee un bloque ``funciones`` y avisa de claves desconocidas."""
    features = {str(key): bool(value) for key, value in as_dict(raw, where).items()}
    unknown = set(features) - KNOWN_FEATURES
    if unknown:
        raise RegistryError(
            f"{where}: funciones desconocidas {sorted(unknown)}; "
            f"válidas: {sorted(KNOWN_FEATURES)}"
        )
    return features


def _views(vehicles_dir: Path, raw: dict, where: str) -> dict[str, ViewLayers]:
    """Lee el bloque ``vistas`` (``clave: carpeta dentro de vehicles/``).

    ``carpeta_vista_planta`` (rc6) se sigue aceptando como atajo de
    ``vistas: {top_view: vista_planta/<carpeta>}``.
    """
    folders = {
        str(key): str(value)
        for key, value in as_dict(raw.get("vistas"), f"{where}.vistas").items()
        if value
    }
    legacy = raw.get("carpeta_vista_planta")
    if legacy and VIEW_TOP not in folders:
        folders[VIEW_TOP] = f"vista_planta/{legacy}"
    unknown = set(folders) - set(KNOWN_VIEWS)
    if unknown:
        raise RegistryError(
            f"{where}.vistas: vistas desconocidas {sorted(unknown)}; "
            f"válidas: {list(KNOWN_VIEWS)}"
        )
    return {
        key: load_view(vehicles_dir / folders[key])
        for key in KNOWN_VIEWS
        if key in folders
    }


def _maintenance(raw: object, trims: dict[str, Trim], where: str) -> MaintenancePlan:
    """Lee el bloque ``mantenimiento`` (sin él, el intervalo habitual y sin operaciones)."""
    block = as_dict(raw, where)
    operations: list[Operation] = []
    for index, item in enumerate(block.get("operaciones") or []):
        item_where = f"{where}.operaciones[{index}]"
        item = as_dict(item, item_where)
        every = int(item.get("cada") or 1)
        if every < 1:
            raise RegistryError(f"{item_where}: 'cada' debe ser 1 o más")
        only = as_str_list(item.get("versiones"), f"{item_where}.versiones")
        unknown = set(only) - set(trims)
        if unknown:
            raise RegistryError(
                f"{item_where}: versiones desconocidas {sorted(unknown)}; válidas: {sorted(trims)}"
            )
        key = item.get("clave")
        if key:
            # Nombre traducido: idiomas/<idioma>.json → catalogo.operacion_<clave>.
            text_key = f"operacion_{key}"
            names = {
                lang: texts[text_key] for lang, texts in CATALOGUE_TEXTS.items() if text_key in texts
            }
            if not names:
                raise RegistryError(
                    f"{item_where}: no hay texto 'catalogo.{text_key}' en los ficheros de idiomas/"
                )
        else:
            raw_name = require(item, "nombre", item_where)
            names = (
                {str(lang): str(text) for lang, text in raw_name.items()}
                if isinstance(raw_name, dict)
                else {"es": str(raw_name)}
            )
            if not names:
                raise RegistryError(f"{item_where}: 'nombre' está vacío")
        operations.append(Operation(names=names, every=every, trims=only))
    return MaintenancePlan(
        interval_km=int(block.get("intervalo_km") or DEFAULT_INTERVAL_KM),
        interval_months=int(block.get("intervalo_meses") or DEFAULT_INTERVAL_MONTHS),
        operations=tuple(operations),
    )


def _resolved(raw_models: dict, model_id: str, file: str, seen: tuple[str, ...] = ()) -> dict:
    """Datos de un modelo, con lo que copia de otro (``como:``) ya incluido.

    ``funciones`` se mezcla (el modelo solo escribe las que cambian); el resto
    de campos, si el modelo los escribe, sustituyen a los copiados.
    """
    where = f"{file} → modelos.{model_id}"
    raw = as_dict(raw_models.get(model_id), where)
    base_id = raw.get("como")
    if not base_id:
        return raw
    base_id = str(base_id)
    if base_id not in raw_models:
        raise RegistryError(f"{where}.como: no existe el modelo '{base_id}'")
    if base_id == model_id or base_id in seen:
        raise RegistryError(f"{where}.como: los modelos se copian en círculo")
    base = _resolved(raw_models, base_id, file, (*seen, model_id))
    merged = {**base, **raw}
    merged["funciones"] = {
        **as_dict(base.get("funciones"), f"{where}.funciones"),
        **as_dict(raw.get("funciones"), f"{where}.funciones"),
    }
    return merged


def load_vehicles(vehicles_dir: Path) -> VehicleRegistry:
    """Lee y valida ``vehicles/vehicles.yaml``."""
    path = vehicles_dir / "vehicles.yaml"
    data = read_yaml(path)
    file = path.name
    models: dict[str, VehicleModel] = {}
    raw_models = as_dict(data.get("modelos"), f"{file} → modelos")

    for model_id in raw_models:
        where = f"{file} → modelos.{model_id}"
        raw = _resolved(raw_models, str(model_id), file)
        recognise = as_dict(raw.get("reconocer"), f"{where}.reconocer")
        trims: dict[str, Trim] = {}
        for trim_id, trim_raw in as_dict(raw.get("versiones"), f"{where}.versiones").items():
            trim_where = f"{where}.versiones.{trim_id}"
            trim_raw = as_dict(trim_raw, trim_where)
            trims[str(trim_id)] = Trim(
                id=str(trim_id),
                name=str(require(trim_raw, "nombre", trim_where)),
                description=str(trim_raw.get("descripcion") or ""),
                photo_group=str(trim_raw.get("grupo_foto") or trim_id),
                features=_features(trim_raw.get("funciones"), f"{trim_where}.funciones"),
                wheel=str(trim_raw.get("llanta") or ""),
                verified=bool(trim_raw.get("verificada", False)),
                battery_kwh=_battery_kwh(trim_raw.get("bateria_kwh"), trim_where),
            )
        colors: dict[str, Color] = {}
        for color_id, color_raw in as_dict(raw.get("colores"), f"{where}.colores").items():
            color_where = f"{where}.colores.{color_id}"
            color_raw = as_dict(color_raw, color_where)
            colors[str(color_id)] = Color(
                id=str(color_id),
                name=str(require(color_raw, "nombre", color_where)),
                description=str(color_raw.get("descripcion") or ""),
                swatch=str(color_raw.get("muestra") or ""),
            )
        models[str(model_id)] = VehicleModel(
            id=str(model_id),
            name=str(require(raw, "nombre", where)),
            name_with_trim=str(raw.get("nombre_con_version") or ""),
            description=str(raw.get("descripcion") or ""),
            manufacturer=str(raw.get("fabricante") or "Changan Deepal"),
            countries=as_str_list(raw.get("paises"), f"{where}.paises"),
            match_names=as_str_list(recognise.get("nombre_contiene"), f"{where}.reconocer"),
            match_series_codes=as_str_list(recognise.get("codigo_serie"), f"{where}.reconocer"),
            features=_features(raw.get("funciones"), f"{where}.funciones"),
            photos_dir=vehicles_dir / "photos" / str(raw.get("carpeta_fotos") or model_id),
            default_photo=str(raw.get("foto_defecto") or "default.png"),
            trims=trims,
            colors=colors,
            views=_views(vehicles_dir, raw, where),
            wheel_options=as_str_list(raw.get("llantas"), f"{where}.llantas"),
            manual_url=str(raw.get("manual") or "").strip(),
            maintenance=_maintenance(raw.get("mantenimiento"), trims, f"{where}.mantenimiento"),
            silent_warnings=frozenset(
                as_str_list(raw.get("testigos_sin_aviso"), f"{where}.testigos_sin_aviso")
            ),
            based_on=str(raw.get("como") or ""),
        )

    if GENERIC_MODEL_ID not in models:
        raise RegistryError(f"{file}: falta el modelo obligatorio '{GENERIC_MODEL_ID}'")
    return VehicleRegistry(models=models)
