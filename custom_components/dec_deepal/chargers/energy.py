"""Cargadores: kWh de cada carga (contador o potencia), % estimado sin cobertura y pérdidas medidas."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.core import callback

from ..telemetry import signals as s
from .const import (
    LOSS_SAMPLES,
    ROLE_POWER,
)
from .estimate import estimate_level, measured_loss
from .util import _iso, _when


class EnergyMixin:
    """kWh de cada carga (contador o potencia), % estimado sin cobertura y pérdidas medidas.

    Es una parte de :class:`~.manager.ChargerManager` (se juntan por herencia):
    usa sus atributos y los métodos de las demás partes a través de ``self``.
    """

    def _track_power(self, charger: Mapping[str, Any], session: dict[str, Any]) -> None:
        """kWh por la potencia: la última potencia leída por el tiempo que ha durado."""
        now = self._clock()
        last = _when(session.get("pw_at"))
        watts = float(session.get("pw_w") or 0.0)
        if last is not None and watts > 0:
            session["energy_power"] = float(session.get("energy_power") or 0.0) + watts * (now - last).total_seconds() / 3_600_000
        power = self.power_w(charger) if self.charging(charger) is not False else 0.0
        session["pw_at"] = _iso(now)
        session["pw_w"] = power or 0.0

    def _track_energy(self, charger: Mapping[str, Any], session: dict[str, Any] | None = None, *, save: bool = True) -> None:
        """kWh de esta carga: los del contador del cargador o, si no avanza, por la potencia.

        ``save=False`` para calcular sobre una copia sin guardar nada (la tarjeta).
        """
        session = session if session is not None else self._sessions.get(charger["id"])
        if session is None:
            return
        if charger["entities"].get(ROLE_POWER):
            self._track_power(charger, session)
        self._track_meter(charger, session)
        meter = session.get("energy_meter")
        power = float(session.get("energy_power") or 0.0)
        # El contador manda; si no hay, o no se mueve mientras la potencia sí, la potencia.
        if power > 0.3 and (meter is None or meter < 0.05 or (power > 1.0 and meter < power * 0.5)):
            energy, source = power, "power"
        else:
            energy, source = float(meter or 0.0), "meter" if meter is not None else None
        session["energy"] = max(float(session.get("energy") or 0.0), energy)
        if source:
            session["energy_source"] = source
        if save:
            self._save()

    def _track_meter(self, charger: Mapping[str, Any], session: dict[str, Any]) -> None:
        """kWh de esta carga: lo que ha subido el contador desde que se enchufó."""
        value = self._energy_raw(charger)
        if value is None:
            return
        start = session.get("energy_start")
        if start is None or value < start:
            # Contador por sesión (se pone a 0 al enchufar) o reiniciado.
            session["energy_start"] = start = 0.0 if start is None or value < start else start
        session["energy_meter"] = max(float(session.get("energy_meter") or 0.0), value - start)

    def measured(self, charger_id: str) -> dict[str, Any] | None:
        """Pérdida medida con las últimas cargas: ``{"value": 11.8, "count": 4}``."""
        samples = self._losses.get(charger_id) or []
        if not samples:
            return None
        return {"value": round(sum(samples) / len(samples), 1), "count": len(samples)}

    def _is_estimated(self, session: Mapping[str, Any]) -> bool:
        vehicle_id = session.get("vehicle_id")
        return bool(vehicle_id) and not self._reported_since(vehicle_id, _when(session.get("charging_since") or session.get("plugged_at")))

    def _level(self, charger: Mapping[str, Any], session: Mapping[str, Any]) -> float | None:
        """% del coche: el real si ha informado durante la carga; si no, estimado."""
        vehicle_id = session.get("vehicle_id")
        if not vehicle_id:
            return None
        if not self._is_estimated(session):
            return self._car_data(vehicle_id).get(s.BATTERY_LEVEL)
        return estimate_level(session.get("soc_start"), session.get("energy"), charger["loss"], self._capacity(vehicle_id))

    @callback
    def _learn(self, _now: Any = None) -> None:
        """Cargas terminadas sin cobertura: cuando el coche vuelve a informar, se mide la pérdida.

        De paso, mira el límite de las cargas en curso (el coche puede haber
        informado por su cuenta).
        """
        for charger_id in list(self._sessions):
            if (charger := self.chargers.get(charger_id)) is not None:
                self._check_limit(charger)
        changed = False
        for charger_id, history in self._history.items():
            charger = self.chargers.get(charger_id)
            if charger is None:
                continue
            for record in history[-5:]:
                vehicle_id = record.get("vehicle_id")
                if record.get("learned") or not vehicle_id or record.get("soc_start") is None:
                    continue
                end = _when(record.get("end"))
                data = self._car_data(vehicle_id)
                if not self._reported_since(vehicle_id, end):
                    continue
                record["learned"] = True
                changed = True
                level = data.get(s.BATTERY_LEVEL)
                odometer = data.get(s.ODOMETER_KM)
                if level is None or (record.get("odometer") is not None and odometer is not None and odometer - record["odometer"] > 1):
                    continue  # ya ha circulado: el % no sirve
                record["soc_end"] = level
                record["estimated"] = False
                capacity = self._capacity(vehicle_id)
                if charger["learn"] and capacity and (loss := measured_loss(record["soc_start"], level, record["energy"], capacity)) is not None:
                    samples = self._losses.setdefault(charger_id, [])
                    samples.append(loss)
                    del samples[:-LOSS_SAMPLES]
        if changed:
            self._save()
            self._changed()
