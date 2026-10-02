"""Pruebas de las vistas por capas (planta e isométrica): capas y montaje."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from custom_components.dec_deepal.registries import RegistryError, load_all
from custom_components.dec_deepal.registries.vehicles import load_vehicles
from custom_components.dec_deepal.registries.views import load_view
from custom_components.dec_deepal.telemetry import signals as s

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "dec_deepal"
S05_DIR = INTEGRATION / "vehicles" / "vista_planta" / "s05_2024"

ALL_CLOSED = (
    "base.png",
    "hood_closed.png",
    "trunk_closed.png",
    "door_front_left_closed.png",
    "door_front_right_closed.png",
    "door_rear_left_closed.png",
    "door_rear_right_closed.png",
)


# Orden comprobado píxel a píxel contra la foto del coche cerrado (rc8):
# cristal antes que su puerta, puerta trasera antes que la delantera.
ISO_CLOSED = (
    "window_rear_right_closed.png",
    "door_rear_right_closed.png",
    "window_front_right_closed.png",
    "door_front_right_closed.png",
    "trunk_closed.png",
    "base.png",
    "hood_closed.png",
    "window_rear_left_closed.png",
    "door_rear_left_closed.png",
    "window_front_left_closed.png",
    "door_front_left_closed.png",
)


@pytest.fixture(scope="module")
def views():  # noqa: ANN201
    return load_all(INTEGRATION).vehicles.get("s05_2024").views


@pytest.fixture(scope="module")
def layers(views):  # noqa: ANN001, ANN201
    return views["top_view"]


@pytest.fixture(scope="module")
def iso(views):  # noqa: ANN001, ANN201
    return views["isometric_view"]


def test_catalogue_links_models(views) -> None:  # noqa: ANN001
    registries = load_all(INTEGRATION)
    assert list(views) == ["top_view", "isometric_view"]
    assert registries.vehicles.get("generico").views == {}
    # Todas las señales existen en el vocabulario de telemetría.
    known = {value for name, value in vars(s).items() if name.isupper()}
    for view in views.values():
        assert set(view.signals) <= known


def test_isometric_all_closed(iso) -> None:  # noqa: ANN001
    assert iso.select(lambda _name: None).images == ISO_CLOSED


def test_isometric_open_parts(iso) -> None:  # noqa: ANN001
    state = {s.TRUNK_OPEN: True, s.DOOR_FRONT_LEFT: True, s.WINDOW_REAR_LEFT: True}
    images = iso.select(lambda name: state.get(name, False)).images
    # El portón abierto va encima de la base; el cerrado, no aparece.
    assert "trunk_closed.png" not in images
    assert images.index("trunk_open.png") > images.index("base.png")
    # Puerta abierta: cristal de puerta abierta, no el de puerta cerrada.
    assert "window_front_left_closed_door_open.png" in images
    assert "window_front_left_closed.png" not in images
    # Ventanilla bajada: sin cristal.
    assert not any(name.startswith("window_rear_left") for name in images)
    # Lo del lado derecho va debajo de la base.
    assert images.index("door_front_right_closed.png") < images.index("base.png")
    # El cristal (con la puerta abierta) va debajo de su puerta.
    assert images.index("window_front_left_closed_door_open.png") < images.index(
        "door_front_left_open.png"
    )


def test_legacy_top_view_folder(tmp_path: Path) -> None:
    """``carpeta_vista_planta`` (rc6) sigue funcionando."""
    view_dir = tmp_path / "vista_planta" / "m"
    view_dir.mkdir(parents=True)
    (view_dir / "base.png").write_bytes(b"x")
    (view_dir / "capas.yaml").write_text("capas: [{imagen: base.png}]", encoding="utf-8")
    catalogue = tmp_path / "vehicles.yaml"
    catalogue.write_text(
        "modelos: {m: {nombre: M, carpeta_vista_planta: m}, generico: {nombre: G}}",
        encoding="utf-8",
    )
    assert list(load_vehicles(tmp_path).get("m").views) == ["top_view"]
    catalogue.write_text(
        "modelos: {m: {nombre: M, vistas: {lateral: x}}, generico: {nombre: G}}",
        encoding="utf-8",
    )
    with pytest.raises(RegistryError, match="lateral"):
        load_vehicles(tmp_path)


def test_unknown_draws_closed(layers) -> None:  # noqa: ANN001
    selection = layers.select(lambda _name: None)
    assert selection.images == ALL_CLOSED
    assert selection.active == ()
    assert s.DOOR_FRONT_LEFT in selection.unknown


def test_open_parts_and_lights(layers) -> None:  # noqa: ANN001
    state = {s.HOOD_OPEN: True, s.DOOR_REAR_RIGHT: True, s.LOW_BEAM: True}
    selection = layers.select(lambda name: state.get(name, False))
    assert "hood_open.png" in selection.images
    assert "hood_closed.png" not in selection.images
    assert "door_rear_right_open.png" in selection.images
    assert selection.images[-1] == "low_beam_on.png"
    assert set(selection.active) == set(state)
    assert selection.unknown == ()


def test_window_only_with_door_closed(layers) -> None:  # noqa: ANN001
    window_only = {s.WINDOW_FRONT_LEFT: True}
    images = layers.select(lambda name: window_only.get(name, False)).images
    assert "window_front_left_open.png" in images
    assert images.index("window_front_left_open.png") > images.index(
        "door_front_left_closed.png"
    )

    door_too = {s.WINDOW_FRONT_LEFT: True, s.DOOR_FRONT_LEFT: True}
    images = layers.select(lambda name: door_too.get(name, False)).images
    assert "window_front_left_open.png" not in images
    assert "door_front_left_open.png" in images


def test_color_folder_overrides(tmp_path: Path) -> None:
    (tmp_path / "base.png").write_bytes(b"x")
    (tmp_path / "negro").mkdir()
    (tmp_path / "negro" / "base.png").write_bytes(b"y")
    (tmp_path / "capas.yaml").write_text("capas:\n  - imagen: base.png\n", encoding="utf-8")
    view = load_view(tmp_path)
    assert view.image_path("base.png", "negro") == tmp_path / "negro" / "base.png"
    assert view.image_path("base.png", "blanco") == tmp_path / "base.png"
    assert view.image_path("base.png", None) == tmp_path / "base.png"


def test_validation(tmp_path: Path) -> None:
    (tmp_path / "capas.yaml").write_text(
        "capas:\n  - senal: hood_open\n    si_activo: falta.png\n", encoding="utf-8"
    )
    with pytest.raises(RegistryError, match="falta.png"):
        load_view(tmp_path)
    (tmp_path / "capas.yaml").write_text("capas:\n  - senal: hood_open\n", encoding="utf-8")
    with pytest.raises(RegistryError, match="si_activo"):
        load_view(tmp_path)


def test_render_png(layers, iso) -> None:  # noqa: ANN001
    image_module = pytest.importorskip("PIL.Image")
    from custom_components.dec_deepal.view_renderer import ViewRenderer

    renderer = ViewRenderer(layers, "mercury_silver")  # sin subcarpeta: plata
    closed = renderer.render(ALL_CLOSED)
    opened = renderer.render(
        layers.select(lambda name: name == s.DOOR_FRONT_LEFT).images
    )
    assert closed != opened
    assert renderer.render(ALL_CLOSED) is closed  # de memoria
    with image_module.open(io.BytesIO(closed)) as picture:
        assert picture.format == "PNG"
        assert picture.size == (750, 750)

    iso_png = ViewRenderer(iso, None).render(ISO_CLOSED)
    with image_module.open(io.BytesIO(iso_png)) as picture:
        assert picture.size == (750, 500)
