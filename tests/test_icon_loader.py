"""Cargador temprano de iconos: recurso de paneles servido desde la ruta propia.

Se ejecuta con un Home Assistant de verdad (GitHub Actions): comprueba que la
API de recursos que usa ``frontend.py`` existe y se comporta como se espera.
Desde la 2.6.0b9 nada se escribe en ``www`` (revisión de HACS): al arrancar se
quitan la copia y el recurso ``/local/`` de versiones anteriores.
"""

from __future__ import annotations

from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.dec_deepal import frontend
from custom_components.dec_deepal.const import (
    ICONS_LOADER_FILE,
    ICONS_LOADER_URL,
    LEGACY_LOADER_URL,
    LEGACY_LOADER_WWW_DIR,
)


def _items(hass: HomeAssistant, url: str) -> list[dict]:
    resources = frontend._resource_collection(hass)
    assert resources is not None
    return [item for item in resources.async_items() if item["url"].split("?")[0] == url]


async def test_install_and_remove(hass: HomeAssistant, tmp_path: Path) -> None:
    """Registra el recurso de la ruta propia una sola vez, sin tocar www, y lo quita al desinstalar."""
    hass.config.config_dir = str(tmp_path)
    assert await async_setup_component(hass, "lovelace", {})

    assert ICONS_LOADER_URL == "/dec_deepal/frontend/dec-icons-loader.js"
    assert await frontend.async_install_early_loader(hass) == "recurso registrado"
    assert len(_items(hass, ICONS_LOADER_URL)) == 1
    assert _items(hass, ICONS_LOADER_URL)[0]["type"] == "module"
    assert not (tmp_path / "www").exists()

    # Segundo arranque: no se duplica.
    assert await frontend.async_install_early_loader(hass) == "recurso ya registrado"
    assert len(_items(hass, ICONS_LOADER_URL)) == 1

    await frontend.async_remove_early_loader(hass)
    assert _items(hass, ICONS_LOADER_URL) == []


async def test_upgrade_removes_the_www_copy(hass: HomeAssistant, tmp_path: Path) -> None:
    """Al actualizar desde la 2.6.0b8 o antes: fuera la copia de www y el recurso /local/."""
    hass.config.config_dir = str(tmp_path)
    assert await async_setup_component(hass, "lovelace", {})
    resources = frontend._resource_collection(hass)
    await resources.async_create_item({"res_type": "module", "url": LEGACY_LOADER_URL})
    folder = tmp_path / "www" / LEGACY_LOADER_WWW_DIR
    folder.mkdir(parents=True)
    (folder / ICONS_LOADER_FILE).write_text("viejo", encoding="utf-8")
    (tmp_path / "www" / "del_usuario.png").write_bytes(b"x")

    status = await frontend.async_install_early_loader(hass)
    assert status == "recurso registrado; quitado el cargador antiguo de www"
    assert _items(hass, LEGACY_LOADER_URL) == []
    assert len(_items(hass, ICONS_LOADER_URL)) == 1
    assert not folder.exists()
    # Lo demás de www es del usuario: no se toca.
    assert (tmp_path / "www" / "del_usuario.png").is_file()


async def test_legacy_folder_with_user_files_is_kept(hass: HomeAssistant, tmp_path: Path) -> None:
    """Si el usuario guardó algo en www/dec_deepal/, solo se borra nuestro archivo."""
    hass.config.config_dir = str(tmp_path)
    folder = tmp_path / "www" / LEGACY_LOADER_WWW_DIR
    folder.mkdir(parents=True)
    (folder / ICONS_LOADER_FILE).write_text("viejo", encoding="utf-8")
    (folder / "mio.txt").write_text("mío", encoding="utf-8")
    assert frontend._remove_legacy_copy(tmp_path / "www") is True
    assert not (folder / ICONS_LOADER_FILE).exists() and (folder / "mio.txt").is_file()
    assert frontend._remove_legacy_copy(tmp_path / "www") is False


async def test_yaml_resources_are_left_alone(hass: HomeAssistant, tmp_path: Path) -> None:
    """Con los recursos en modo YAML no se registra nada (y no falla)."""
    hass.config.config_dir = str(tmp_path)
    assert await async_setup_component(hass, "lovelace", {"lovelace": {"resource_mode": "yaml", "resources": []}})
    status = await frontend.async_install_early_loader(hass)
    assert "YAML" in status
    await frontend.async_remove_early_loader(hass)


async def test_never_raises_without_lovelace(hass: HomeAssistant, tmp_path: Path) -> None:
    """Sin el componente de paneles tampoco falla: los iconos no impiden arrancar."""
    hass.config.config_dir = str(tmp_path)
    assert "no se registra" in await frontend.async_install_early_loader(hass)
