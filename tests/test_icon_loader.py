"""Cargador temprano de iconos (2.1.3): copia en ``www`` y recurso de paneles.

Se ejecuta con un Home Assistant de verdad (GitHub Actions): comprueba que la
API de recursos que usa ``frontend.py`` existe y se comporta como se espera.
"""

from __future__ import annotations

from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.dec_deepal import frontend
from custom_components.dec_deepal.const import (
    ICONS_LOADER_FILE,
    ICONS_LOADER_URL,
    ICONS_LOADER_WWW_DIR,
)

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "dec_deepal"


def _loader_items(hass: HomeAssistant) -> list[dict]:
    resources = frontend._resource_collection(hass)
    assert resources is not None
    return [item for item in resources.async_items() if item["url"] == ICONS_LOADER_URL]


def test_copy_loader(tmp_path: Path) -> None:
    """Copia el archivo, dice si ``www`` ya existía y no reescribe si es igual."""
    www = tmp_path / "www"
    assert frontend._copy_loader(www) is False  # www no existía
    target = www / ICONS_LOADER_WWW_DIR / ICONS_LOADER_FILE
    assert target.read_bytes() == (INTEGRATION / "icons" / ICONS_LOADER_FILE).read_bytes()
    stamp = target.stat().st_mtime_ns
    assert frontend._copy_loader(www) is True
    assert target.stat().st_mtime_ns == stamp
    target.write_text("viejo", encoding="utf-8")
    frontend._copy_loader(www)
    assert "dec-icons.js" in target.read_text(encoding="utf-8")


async def test_install_and_remove(hass: HomeAssistant, tmp_path: Path) -> None:
    """Registra el recurso una sola vez y lo quita al desinstalar."""
    hass.config.config_dir = str(tmp_path)
    assert await async_setup_component(hass, "lovelace", {})

    status = await frontend.async_install_early_loader(hass)
    assert status.startswith("recurso registrado"), status
    assert "www recién creada" in status
    assert len(_loader_items(hass)) == 1
    assert _loader_items(hass)[0]["type"] == "module"
    assert (tmp_path / "www" / ICONS_LOADER_WWW_DIR / ICONS_LOADER_FILE).is_file()

    # Segundo arranque: no se duplica.
    assert await frontend.async_install_early_loader(hass) == "recurso ya registrado"
    assert len(_loader_items(hass)) == 1

    await frontend.async_remove_early_loader(hass)
    assert _loader_items(hass) == []
    assert not (tmp_path / "www" / ICONS_LOADER_WWW_DIR).exists()


async def test_yaml_resources_are_left_alone(hass: HomeAssistant, tmp_path: Path) -> None:
    """Con los recursos en modo YAML no se toca nada (y no falla)."""
    hass.config.config_dir = str(tmp_path)
    assert await async_setup_component(hass, "lovelace", {"lovelace": {"resource_mode": "yaml", "resources": []}})
    status = await frontend.async_install_early_loader(hass)
    assert "YAML" in status
    await frontend.async_remove_early_loader(hass)


async def test_never_raises_without_lovelace(hass: HomeAssistant, tmp_path: Path) -> None:
    """Sin el componente de paneles tampoco falla: los iconos no impiden arrancar."""
    hass.config.config_dir = str(tmp_path)
    assert "no se registra" in await frontend.async_install_early_loader(hass)
