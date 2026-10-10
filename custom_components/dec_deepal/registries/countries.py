"""Cargador de ``countries/countries.yaml`` (países y servidores).

Formato del fichero: ver los comentarios de la cabecera del propio YAML.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from ..api.transport import CountryProfile
from ..documents import CountryRules
from .errors import RegistryError, as_dict, as_str_list, read_yaml, require

#: Métodos de login que entiende la integración.
VALID_LOGIN_METHODS: Final = frozenset({"sms", "email"})


@dataclass(frozen=True, slots=True)
class Environment:
    """Grupo de servidores de una región."""

    id: str
    name: str
    intl_base_url: str
    ca_base_url: str
    sda_base_url: str


@dataclass(frozen=True, slots=True)
class Country:
    """Un país tal como se define en el catálogo."""

    id: str
    name: str
    enabled: bool
    environment: Environment
    sales_country: str
    dial_code: str
    mobile_digits: int
    api_language: str
    login_methods: tuple[str, ...]
    verified: bool
    notes: str
    #: Normas del país (ITV, preaviso del seguro). Por defecto, las de España.
    rules: CountryRules = CountryRules()

    def profile(self) -> CountryProfile:
        """Perfil mínimo que necesita el cliente de la API."""
        return CountryProfile(
            country_id=self.id,
            sales_country=self.sales_country,
            dial_code=self.dial_code,
            api_language=self.api_language,
            intl_base_url=self.environment.intl_base_url,
            ca_base_url=self.environment.ca_base_url,
            sda_base_url=self.environment.sda_base_url,
        )

    def normalize_mobile(self, raw: str) -> str:
        """Limpia un móvil: quita espacios, guiones, paréntesis y el prefijo.

        Acepta ``+34 600 000 000``, ``0034600000000``, ``34600000000`` (si
        tiene la longitud justa) y ``600000000``.
        """
        cleaned = "".join(ch for ch in raw if ch.isdigit() or ch == "+")
        for prefix in (f"+{self.dial_code}", f"00{self.dial_code}"):
            if cleaned.startswith(prefix):
                return cleaned[len(prefix) :]
        if (
            self.mobile_digits
            and cleaned.startswith(self.dial_code)
            and len(cleaned) == len(self.dial_code) + self.mobile_digits
        ):
            return cleaned[len(self.dial_code) :]
        return cleaned.lstrip("+")

    def is_valid_mobile(self, normalized: str) -> bool:
        """``True`` si el móvil ya normalizado tiene las cifras esperadas."""
        if not normalized.isdigit():
            return False
        return not self.mobile_digits or len(normalized) == self.mobile_digits


@dataclass(frozen=True, slots=True)
class CountryRegistry:
    """Todos los países del catálogo."""

    countries: dict[str, Country]

    def enabled(self) -> list[Country]:
        """Países activos, ordenados por nombre (para el asistente)."""
        return sorted(
            (country for country in self.countries.values() if country.enabled),
            key=lambda country: country.name,
        )

    def get(self, country_id: str) -> Country:
        """Devuelve un país por id.

        Raises:
            RegistryError: el país no existe en el catálogo.
        """
        try:
            return self.countries[country_id]
        except KeyError as err:
            raise RegistryError(f"País desconocido: {country_id}") from err


#: Campo de ``normas`` en el YAML → atributo de :class:`CountryRules`.
RULE_FIELDS: Final = {
    "itv_primera_meses": "itv_first_months",
    "itv_cada_meses": "itv_interval_months",
    "itv_reducida_desde_meses": "itv_reduced_from_months",
    "itv_reducida_cada_meses": "itv_reduced_interval_months",
    "seguro_preaviso_dias": "insurance_notice_days",
}


def _rules(raw: object, where: str) -> CountryRules:
    """Lee el bloque ``normas`` de un país (lo que falte, como en España)."""
    block = as_dict(raw, where)
    unknown = set(block) - set(RULE_FIELDS)
    if unknown:
        raise RegistryError(f"{where}: normas desconocidas {sorted(unknown)}; válidas: {sorted(RULE_FIELDS)}")
    try:
        return CountryRules(**{RULE_FIELDS[key]: int(value) for key, value in block.items()})
    except (TypeError, ValueError) as err:
        raise RegistryError(f"{where}: cada norma debe ser un número entero") from err


def load_countries(path: Path) -> CountryRegistry:
    """Lee y valida ``countries.yaml``."""
    data = read_yaml(path)
    file = path.name

    environments: dict[str, Environment] = {}
    for env_id, raw in as_dict(data.get("entornos"), f"{file} → entornos").items():
        where = f"{file} → entornos.{env_id}"
        environments[str(env_id)] = Environment(
            id=str(env_id),
            name=str(raw.get("nombre", env_id)) if isinstance(raw, dict) else str(env_id),
            intl_base_url=str(require(raw, "url_intl", where)).rstrip("/"),
            ca_base_url=str(require(raw, "url_ca", where)).rstrip("/"),
            sda_base_url=str(require(raw, "url_sda", where)).rstrip("/"),
        )

    countries: dict[str, Country] = {}
    for country_id, raw in as_dict(data.get("paises"), f"{file} → paises").items():
        where = f"{file} → paises.{country_id}"
        raw = as_dict(raw, where)
        env_id = str(require(raw, "entorno", where))
        if env_id not in environments:
            raise RegistryError(f"{where}: entorno '{env_id}' no definido en 'entornos'")
        methods = as_str_list(require(raw, "metodos_login", where), f"{where}.metodos_login")
        unknown = set(methods) - VALID_LOGIN_METHODS
        if unknown or not methods:
            raise RegistryError(
                f"{where}.metodos_login: valores válidos {sorted(VALID_LOGIN_METHODS)}"
            )
        countries[str(country_id)] = Country(
            id=str(country_id),
            name=str(require(raw, "nombre", where)),
            enabled=bool(raw.get("activo", False)),
            environment=environments[env_id],
            sales_country=str(require(raw, "pais_venta", where)).upper(),
            dial_code=str(require(raw, "prefijo", where)).lstrip("+"),
            mobile_digits=int(raw.get("digitos_movil") or 0),
            api_language=str(raw.get("idioma_api") or "en_US"),
            login_methods=methods,
            verified=bool(raw.get("verificado", False)),
            notes=str(raw.get("notas") or ""),
            rules=_rules(raw.get("normas"), f"{where}.normas"),
        )

    if not any(country.enabled for country in countries.values()):
        raise RegistryError(f"{file}: no hay ningún país con 'activo: true'")
    return CountryRegistry(countries=countries)
