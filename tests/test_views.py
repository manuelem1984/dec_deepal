"""Pruebas de las vistas por capas (planta e isométrica): capas y montaje."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from custom_components.dec_deepal.registries import RegistryError, load_all
from custom_components.dec_deepal.registries.vehicles import load_vehicles
from custom_components.dec_deepal.registries.views import is_option, load_view
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
    "plate_dec.png",
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
    assert list(views) == ["top_view", "isometric_view", "interior_view", "charging_view"]
    assert registries.vehicles.get("generico").views == {}
    # Todas las señales existen en el vocabulario de telemetría (salvo las
    # que son opciones del coche, como las llantas).
    known = {value for name, value in vars(s).items() if name.isupper()}
    for view in views.values():
        assert {name for name in view.signals if not is_option(name)} <= known
    assert [name for name in views["isometric_view"].signals if is_option(name)] == [
        "wheels_pro",
        "wheels_open",
    ]


def test_isometric_all_closed(iso) -> None:  # noqa: ANN001
    assert iso.select(lambda _name: None).images == ISO_CLOSED


def test_isometric_wheels_and_colours(iso) -> None:  # noqa: ANN001
    """Llantas según la versión o la opción elegida, y un juego de capas por color."""
    model = load_all(INTEGRATION).vehicles.get("s05_2024")
    # Pro: siempre su llanta de 18". Max: la elegida, o con tapacubos por defecto.
    assert model.wheel_for("pro", "open") == "pro"
    assert model.wheel_for("max", "open") == "open"
    assert model.wheel_for("max_awd", None) == "cover"
    assert model.wheel_for(None, "no_existe") == "cover"
    assert load_all(INTEGRATION).vehicles.generic.wheel_for(None, None) is None

    def images(wheel: str) -> tuple[str, ...]:
        return iso.select(lambda name: name == f"wheels_{wheel}").images

    assert "wheels_pro.png" in images("pro") and "wheels_open.png" not in images("pro")
    assert "wheels_open.png" in images("open")
    assert not any(name.startswith("wheels_") for name in images("cover"))
    # La llanta va justo encima de la base y por debajo de las puertas de delante.
    assert images("pro").index("wheels_pro.png") < images("pro").index("door_front_left_closed.png")

    # Cada color tiene sus capas de pintura; cristales, luz, matrícula y
    # llantas son comunes (se toman de la carpeta por defecto).
    for color in model.colors:
        assert iso.image_path("base.png", color).parent.name == color, color
        assert iso.image_path("door_front_left_open.png", color).parent.name == color
        assert iso.image_path("hood_open.png", color).parent.name == color
        for common in ("window_front_left_closed.png", "low_beam_on.png", "plate_dec.png", "wheels_pro.png"):
            assert iso.image_path(common, color).parent == iso.directory, (color, common)
    assert iso.image_path("base.png", None).parent == iso.directory


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


def test_interior_levels(views) -> None:  # noqa: ANN001
    interior = views["interior_view"]
    assert interior.select(lambda _name: None).images == ("base.png",)
    # Niveles 0-3: cualquier nivel enciende la capa; 0 la apaga.
    state = {s.SEAT_HEAT_DRIVER: 2, s.SEAT_VENT_PASSENGER: 1, s.SEAT_HEAT_PASSENGER: 0,
             s.STEERING_WHEEL_HEAT: True}
    images = interior.select(lambda name: bool(state.get(name))).images
    assert images == (
        "base.png",
        "steering_wheel_heat_on.png",
        "seat_heat_driver_on.png",
        "seat_vent_passenger_on.png",
    )


def test_charging_states(views) -> None:  # noqa: ANN001
    charging = views["charging_view"]
    states = {
        "sin enchufar": ({}, ("base.png",)),
        "enchufado": ({s.CHARGER_PLUGGED: True}, ("base.png", "cable_connected.png")),
        "cargando": (
            {s.CHARGER_PLUGGED: True, s.CHARGING: True},
            ("base.png", "cable_charging.png"),
        ),
    }
    for state, expected in states.values():
        assert charging.select(lambda name, st=state: st.get(name, False)).images == expected
    assert charging.select(lambda _name: None).images == ("base.png",)


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

    interior = load_all(INTEGRATION).vehicles.get("s05_2024").views["interior_view"]
    png = ViewRenderer(interior, None).render(("base.png", "seat_heat_driver_on.png"))
    with image_module.open(io.BytesIO(png)) as picture:
        assert picture.size == (1125, 1500)
