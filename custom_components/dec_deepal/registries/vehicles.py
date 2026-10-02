"""Cargador de ``vehicles/vehicles.yaml`` (modelos, versiones, colores, fotos).

Además de leer el catálogo, este módulo:

- **Reconoce** el modelo de cada coche de la cuenta (:meth:`VehicleRegistry.match`).
- Calcula las **funciones** efectivas de un coche según su modelo y versión
  (:meth:`VehicleModel.features_for`): así se crean solo las entidades que
  tienen sentido (p. ej. sin ventilación de asientos en el S05 Pro).
- Busca la **foto** que corresponde a versión + color (:meth:`VehicleModel.photo_for`).
- Carga las capas de las **vistas** del modelo ("Vista de planta", "Vista
  isométrica"...), si tiene (``vistas:``; ver :mod:`.views`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from ..api.models import VehicleInfo
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
FEATURE_FUEL: Final = "combustible"

KNOWN_FEATURES: Final = frozenset(
    {
        FEATURE_MQTT,
        FEATURE_CLIMATE,
        FEATURE_LIGHTS_HORN,
        FEATURE_SEAT_HEAT,
        FEATURE_SEAT_VENT,
        FEATURE_WHEEL_HEAT,
        FEATURE_DEFROST,
        FEATURE_PIN_COMMANDS,
        FEATURE_FUEL,
    }
)

#: Id del modelo de respaldo (obligatorio en el catálogo).
GENERIC_MODEL_ID: Final = "generico"

#: Vistas por capas conocidas (claves de "vistas" en el YAML). Cada una es una
#: entidad de imagen con su nombre en translations (``entity.image.<clave>``).
VIEW_TOP: Final = "top_view"
VIEW_ISOMETRIC: Final = "isometric_view"
KNOWN_VIEWS: Final = (VIEW_TOP, VIEW_ISOMETRIC)

#: Extensiones de foto admitidas, en orden de preferencia.
PHOTO_EXTENSIONS: Final = (".png", ".jpg", ".jpeg", ".webp")


@dataclass(frozen=True, slots=True)
class Trim:
    """Versión / acabado de un modelo."""

    id: str
    name: str
    description: str
    photo_group: str
    features: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Color:
    """Color oficial de un modelo."""

    id: str
    name: str
    description: str


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

    def has(self, feature: str, trim_id: str | None = None) -> bool:
        """¿Tiene esta función (con la versión indicada)?"""
        return bool(self.features_for(trim_id).get(feature, False))

    def photo_for(self, trim_id: str | None, color_id: str | None) -> Path | None:
        """Foto exacta para versión + color, o la de por defecto, o ``None``.

        Busca ``<carpeta_fotos>/<grupo_foto>_<color>.<ext>`` con cada extensión
        admitida. Si falta, ``<carpeta_fotos>/<foto_defecto>``. Si tampoco
        existe, ``None`` (la entidad de foto se mostrará como no disponible).
        """
        trim = self.trims.get(trim_id or "")
        if trim is not None and color_id in self.colors:
            for extension in PHOTO_EXTENSIONS:
                candidate = self.photos_dir / f"{trim.photo_group}_{color_id}{extension}"
                if candidate.is_file():
                    return candidate
        default = self.photos_dir / self.default_photo
        return default if default.is_file() else None

    def matches(self, vehicle: VehicleInfo) -> bool:
        """¿Encaja este coche de la cuenta con este modelo?"""
        if vehicle.series_code and vehicle.series_code in self.match_series_codes:
            return True
        texts = " ".join(
            filter(None, (vehicle.model_name, vehicle.series_name, vehicle.model_code))
        ).upper()
        return any(name.upper() in texts for name in self.match_names)


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
        """Reconoce el modelo de un coche; el genérico si no encaja ninguno."""
        for model in self.models.values():
            if model.id == GENERIC_MODEL_ID:
                continue
            if country_id and model.countries and country_id not in model.countries:
                continue
            if model.matches(vehicle):
                return model
        return self.generic

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


def load_vehicles(vehicles_dir: Path) -> VehicleRegistry:
    """Lee y valida ``vehicles/vehicles.yaml``."""
    path = vehicles_dir / "vehicles.yaml"
    data = read_yaml(path)
    file = path.name
    models: dict[str, VehicleModel] = {}

    for model_id, raw in as_dict(data.get("modelos"), f"{file} → modelos").items():
        where = f"{file} → modelos.{model_id}"
        raw = as_dict(raw, where)
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
            )
        colors: dict[str, Color] = {}
        for color_id, color_raw in as_dict(raw.get("colores"), f"{where}.colores").items():
            color_where = f"{where}.colores.{color_id}"
            color_raw = as_dict(color_raw, color_where)
            colors[str(color_id)] = Color(
                id=str(color_id),
                name=str(require(color_raw, "nombre", color_where)),
                description=str(color_raw.get("descripcion") or ""),
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
        )

    if GENERIC_MODEL_ID not in models:
        raise RegistryError(f"{file}: falta el modelo obligatorio '{GENERIC_MODEL_ID}'")
    return VehicleRegistry(models=models)
