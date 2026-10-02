"""Pruebas de la "Vista de planta": elección de capas y montaje del PNG."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from custom_components.dec_deepal.registries import RegistryError, load_all
from custom_components.dec_deepal.registries.top_view import load_top_view
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


@pytest.fixture(scope="module")
def layers():  # noqa: ANN201
    return load_all(INTEGRATION).vehicles.get("s05_2024").top_view


def test_catalogue_links_models(layers) -> None:  # noqa: ANN001
    registries = load_all(INTEGRATION)
    assert layers is not None
    assert registries.vehicles.get("generico").top_view is None
    # Todas las señales existen en el vocabulario de telemetría.
    known = {value for name, value in vars(s).items() if name.isupper()}
    assert set(layers.signals) <= known


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
    view = load_top_view(tmp_path)
    assert view.image_path("base.png", "negro") == tmp_path / "negro" / "base.png"
    assert view.image_path("base.png", "blanco") == tmp_path / "base.png"
    assert view.image_path("base.png", None) == tmp_path / "base.png"


def test_validation(tmp_path: Path) -> None:
    (tmp_path / "capas.yaml").write_text(
        "capas:\n  - senal: hood_open\n    si_activo: falta.png\n", encoding="utf-8"
    )
    with pytest.raises(RegistryError, match="falta.png"):
        load_top_view(tmp_path)
    (tmp_path / "capas.yaml").write_text("capas:\n  - senal: hood_open\n", encoding="utf-8")
    with pytest.raises(RegistryError, match="si_activo"):
        load_top_view(tmp_path)


def test_render_png(layers) -> None:  # noqa: ANN001
    image_module = pytest.importorskip("PIL.Image")
    from custom_components.dec_deepal.top_view import TopViewRenderer

    renderer = TopViewRenderer(layers, "mercury_silver")  # sin subcarpeta: plata
    closed = renderer.render(ALL_CLOSED)
    opened = renderer.render(
        layers.select(lambda name: name == s.DOOR_FRONT_LEFT).images
    )
    assert closed != opened
    assert renderer.render(ALL_CLOSED) is closed  # de memoria
    with image_module.open(io.BytesIO(closed)) as picture:
        assert picture.format == "PNG"
        assert picture.size == (750, 750)
