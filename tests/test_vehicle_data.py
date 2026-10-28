"""Datos por coche: clave, migración del almacén antiguo y copias de seguridad."""

from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace

import pytest

from custom_components.dec_deepal import vehicle_data as vd
from custom_components.dec_deepal.documents import InsuranceRecord, ItvRecord
from custom_components.dec_deepal.maintenance import MaintenanceRecord

VIN = "LS5A3ABE0RA000001"
MAINTENANCE = MaintenanceRecord(services_done=1, last_date=date(2026, 3, 10), last_km=19500).to_dict()
ITV = ItvRecord(registration_date=date(2024, 12, 12)).to_dict()
INSURANCE = InsuranceRecord(
    renewal_date=date(2027, 3, 14), company="Mutua Ejemplo", policy="0123", phone_company="910000000"
).to_dict()


APPEARANCE = {"model": "s05_2024", "trim": "max", "color": "gris", "wheels": "open"}


def test_appearance_is_checked_against_the_catalogue() -> None:
    model = SimpleNamespace(trims={"max": 1, "pro": 1}, colors={"gris": 1}, wheel_options=("cover", "open"))
    models = {"s05_2024": model}
    assert vd.clean_appearance(APPEARANCE, models) == APPEARANCE
    # Lo que el modelo no tiene se descarta; el modelo que ya no existe, entero.
    assert vd.clean_appearance({**APPEARANCE, "color": "rosa", "wheels": "x"}, models) == {
        "model": "s05_2024",
        "trim": "max",
        "color": None,
    }
    assert vd.clean_appearance({**APPEARANCE, "model": "otro"}, models) is None
    # Sin catálogo solo se mira la forma.
    assert vd.clean_appearance({"model": "otro"}) == {"model": "otro", "trim": None, "color": None}
    for bad in (None, "s05", {}, {"model": ""}, {"model": 5}):
        assert vd.clean_appearance(bad) is None


def test_car_key() -> None:
    assert vd.car_key(" ls5a3abe0ra000001 ", "77") == VIN
    # Sin bastidor: el identificador del servidor, marcado para no confundirlo.
    assert vd.car_key(None, "77") == "id:77" and vd.car_key("", "77") == "id:77"


def test_legacy_store_becomes_per_car() -> None:
    legacy = {
        "maintenance": {"77": MAINTENANCE},
        "itv": {"77": ITV},
        "insurance": {"88": INSURANCE},
        "active": {"77": ["warning_abs"]},
        "odometer": {"77": 37500.0, "88": 120.0},
    }
    cars = vd.from_legacy(legacy, {"77": VIN})
    assert cars[VIN] == {
        "vehicle_id": "77",
        "maintenance": MAINTENANCE,
        "itv": ITV,
        "active": ["warning_abs"],
        "odometer": 37500.0,
    }
    # Un coche que ya no está en la cuenta (sin bastidor conocido) no se pierde.
    assert cars["id:88"]["insurance"] == INSURANCE
    assert vd.from_legacy({}, {}) == {} and vd.from_legacy({"itv": None}, {}) == {}


def test_migrate() -> None:
    assert vd.migrate(None, 1) == {"cars": {}}
    assert vd.migrate({"cars": {VIN: {"itv": ITV}}}, 1) == {"cars": {VIN: {"itv": ITV}}}
    assert vd.migrate({"cars": "roto"}, 1) == {"cars": {}}
    with pytest.raises(vd.BackupError) as error:
        vd.migrate({"cars": {}}, vd.DATA_VERSION + 1)
    assert error.value.code == vd.ERROR_NEWER


def test_backup_round_trip() -> None:
    cars = {
        VIN: {
            "vehicle_id": "77",
            "name": "Changote",
            "maintenance": MAINTENANCE,
            "insurance": INSURANCE,
            "appearance": APPEARANCE,
            "active": ["warning_abs"],
            "odometer": 37500.0,
        },
        "id:88": {"vehicle_id": "88", "name": "Sin datos", "odometer": 10.0},
        # Solo con apariencia también merece copia (pero no tiene fichas).
        "id:99": {"vehicle_id": "99", "appearance": {"model": "s05_2024", "trim": None, "color": None}},
    }
    payload = vd.export_payload(cars, datetime(2026, 10, 11, 12, 0))  # noqa: DTZ001 - una hora local de ejemplo
    assert payload["formato"] == vd.EXPORT_FORMAT and payload["version"] == vd.DATA_VERSION
    # Solo viajan los coches con fichas, y sin el estado interno (testigos avisados).
    assert list(payload["coches"]) == [VIN, "id:99"] and "active" not in payload["coches"][VIN]
    parsed = vd.parse_backup(payload)
    assert parsed[VIN] == {
        "maintenance": MAINTENANCE,
        "insurance": INSURANCE,
        "appearance": APPEARANCE,
        "vehicle_id": "77",
        "name": "Changote",
        "odometer": 37500.0,
    }
    assert parsed["id:99"]["appearance"]["model"] == "s05_2024"
    assert vd.has_data(cars["id:99"]) and not vd.has_records(cars["id:99"])
    assert vd.label(VIN, cars[VIN]) == "Changote (…000001)"
    assert vd.label("id:88", {}) == "Deepal …88"
    assert vd.has_records(cars[VIN]) and not vd.has_records(cars["id:88"])


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (None, vd.ERROR_INVALID),
        ([], vd.ERROR_INVALID),
        ({"coches": {}}, vd.ERROR_INVALID),  # sin marca: no es nuestro
        ({"formato": vd.EXPORT_FORMAT, "version": "1", "coches": {}}, vd.ERROR_INVALID),
        ({"formato": vd.EXPORT_FORMAT, "version": 1, "coches": []}, vd.ERROR_INVALID),
        ({"formato": vd.EXPORT_FORMAT, "version": 99, "coches": {}}, vd.ERROR_NEWER),
        ({"formato": vd.EXPORT_FORMAT, "version": 1, "coches": {}}, vd.ERROR_EMPTY),
        ({"formato": vd.EXPORT_FORMAT, "version": 1, "coches": {VIN: {"name": "x"}}}, vd.ERROR_EMPTY),
        ({"formato": vd.EXPORT_FORMAT, "version": 1, "coches": {VIN: "x"}}, vd.ERROR_INVALID),
        # Ficha con una fecha imposible: se rechaza entera, no se carga a medias.
        (
            {
                "formato": vd.EXPORT_FORMAT,
                "version": 1,
                "coches": {VIN: {"itv": {"registration_date": "ayer"}}},
            },
            vd.ERROR_INVALID,
        ),
        (
            {"formato": vd.EXPORT_FORMAT, "version": 1, "coches": {VIN: {"insurance": ["x"]}}},
            vd.ERROR_INVALID,
        ),
        (
            {"formato": vd.EXPORT_FORMAT, "version": 1, "coches": {VIN: {"appearance": {"trim": "max"}}}},
            vd.ERROR_INVALID,
        ),
    ],
)
def test_bad_backups_are_rejected(payload, code) -> None:  # noqa: ANN001
    with pytest.raises(vd.BackupError) as error:
        vd.parse_backup(payload)
    assert error.value.code == code
