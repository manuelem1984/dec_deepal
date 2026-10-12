"""Sesiones de carga: cuándo empieza y termina cada una, y qué se guarda."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from custom_components.dec_deepal import charging as ch

T0 = datetime(2026, 10, 12, 14, 22, tzinfo=timezone(timedelta(hours=2)))


def test_a_full_session() -> None:
    # Sin cargar y sin nada apuntado: no pasa nada.
    state, changed = ch.update(None, False, 44, 217, T0)
    assert state == {} and changed is False

    # Empieza a cargar: se apunta la hora, el nivel y la autonomía.
    state, changed = ch.update(state, True, 44, 217, T0)
    assert changed and state == {
        "current": {"start": "2026-10-12T14:22:00+02:00", "start_level": 44, "start_range": 217}
    }
    # Las lecturas siguientes no cambian nada (se puede llamar las veces que sea).
    again, changed = ch.update(state, True, 51, 250, T0 + timedelta(minutes=30))
    assert again == state and changed is False
    # Dato desconocido (coche dormido): tampoco.
    assert ch.update(state, None, None, None, T0 + timedelta(minutes=40)) == (state, False)

    # Termina: pasa a ser la última carga.
    state, changed = ch.update(state, False, 100, 485, T0 + timedelta(hours=4, minutes=43))
    assert changed and "current" not in state
    assert state["last"] == {
        "start": "2026-10-12T14:22:00+02:00", "start_level": 44, "start_range": 217,
        "end": "2026-10-12T19:05:00+02:00", "end_level": 100, "end_range": 485,
    }
    assert ch.attributes(state) == {
        "ultima_carga": {
            "inicio": "2026-10-12T14:22:00+02:00", "fin": "2026-10-12T19:05:00+02:00",
            "nivel_inicio": 44, "nivel_fin": 100, "autonomia_inicio": 217, "autonomia_fin": 485,
        }
    }

    # Otra carga: la anterior sigue como "última" hasta que esta termine.
    state, _ = ch.update(state, True, 60, 290, T0 + timedelta(days=1))
    shown = ch.attributes(state)
    assert shown["carga_actual"] == {"inicio": "2026-10-13T14:22:00+02:00", "nivel_inicio": 60, "autonomia_inicio": 290}
    assert shown["ultima_carga"]["nivel_fin"] == 100


def test_level_arrives_late_and_blips_are_ignored() -> None:
    # El "cargando" llega antes que el nivel: se completa en la lectura siguiente.
    state, _ = ch.update({}, True, None, None, T0)
    assert state["current"]["start_level"] is None
    state, changed = ch.update(state, True, 30, 150, T0 + timedelta(seconds=20))
    assert changed and state["current"] == {"start": "2026-10-12T14:22:00+02:00", "start_level": 30, "start_range": 150}

    # Un amago de pocos segundos sin ganar batería no pisa la última carga.
    previous = {"last": {"start": "2026-10-11T22:10:00+02:00", "start_level": 22, "start_range": 108,
                         "end": "2026-10-12T03:40:00+02:00", "end_level": 80, "end_range": 394}}
    state, _ = ch.update(previous, True, 80, 394, T0)
    state, changed = ch.update(state, False, 80, 394, T0 + timedelta(seconds=30))
    assert changed and state == previous
    # Pero si en ese rato ha ganado batería, sí cuenta.
    state, _ = ch.update(previous, True, 80, 394, T0)
    state, _ = ch.update(state, False, 81, 399, T0 + timedelta(seconds=90))
    assert state["last"]["end_level"] == 81


def test_stored_data_is_validated() -> None:
    assert ch.clean(None) == {} and ch.clean("roto") == {} and ch.clean({"current": {"start": 5}}) == {}
    assert ch.clean({"current": {"start": "no es una fecha"}, "last": {"start": "2026-10-12T14:22:00+02:00"}}) == {}
    kept = ch.clean({"current": {"start": "2026-10-12T14:22:00+02:00", "start_level": True, "otro": 1}})
    assert kept == {"current": {"start": "2026-10-12T14:22:00+02:00", "start_level": None, "start_range": None}}
    assert ch.attributes(None) == {} and ch.attributes({}) == {}
