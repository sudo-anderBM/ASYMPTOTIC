"""Logica de /api/detectors, /scenario, /explain y /sweep (sin FastAPI)."""
import json
import math
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from greenai.base_data import generar_base
from greenai.detectors import ALL
from greenai.events import evaluar
from greenai.explain import explicar
from greenai.scenarios import SITIOS, TIPOS, inyectar

RES = Path(__file__).resolve().parents[1] / "results"
VARIABLE = {"fuga": ("water_l", "L"), "ineficiencia": ("energy_total_kwh", "kWh")}
RESIDUAL = "3_residual_3sigma"

DETECTORES = [
    {"id": "1_reglas", "nombre": "Reglas del kit",
     "descripcion": "Umbrales fijos: PUE > 1.6, agua > 1.5 L/kWh, entrada > 29 °C", "entrena": False},
    {"id": "2_isolation_forest", "nombre": "IsolationForest",
     "descripcion": "Modelo que aprende qué es raro; caro de ajustar", "entrena": True},
    {"id": "3_residual_3sigma", "nombre": "Residual 3σ",
     "descripcion": "Compara con lo esperado para la carga y la temperatura de cada sitio", "entrena": True},
    {"id": "4_residual_cusum", "nombre": "Residual CUSUM",
     "descripcion": "Acumula desviaciones pequeñas del residual", "entrena": True},
    {"id": "5_zscore_simple", "nombre": "z-score simple",
     "descripcion": "Desviación de PUE y agua/kWh respecto a su promedio normal", "entrena": True},
]


def iso(t) -> str:
    return pd.Timestamp(t).strftime("%Y-%m-%dT%H:%M:%SZ")


def parsear(tipo, magnitud, sitio, semilla):
    for nombre, v in (("tipo", tipo), ("magnitud", magnitud), ("sitio", sitio), ("semilla", semilla)):
        if v is None or v == "":
            raise ValueError(f"Falta el parámetro: {nombre}.")
    if tipo not in TIPOS:
        raise ValueError("tipo debe ser fuga o ineficiencia.")
    if sitio not in SITIOS:
        raise ValueError("sitio debe ser SIM-A, SIM-B o SIM-C.")
    try:
        m = float(magnitud)
    except ValueError:
        raise ValueError("magnitud debe ser un número entre 0 y 1.") from None
    if not math.isfinite(m) or not 0 <= m <= 1:
        raise ValueError("magnitud debe ser un número entre 0 y 1.")
    try:
        s = int(semilla)
    except ValueError:
        raise ValueError("semilla debe ser un entero entre 1 y 1000.") from None
    if not 1 <= s <= 1000:
        raise ValueError("semilla debe ser un entero entre 1 y 1000.")
    return tipo, round(m, 4), sitio, s


@lru_cache(maxsize=16)
def _base(semilla):
    return generar_base(semilla)


@lru_cache(maxsize=16)
def _modelos(semilla):
    base = _base(semilla)
    ref = base[base.split == "referencia"]
    out = {}
    for cls in ALL:
        t0 = time.perf_counter()
        det = cls(False).fit(ref)                      # use_ot=False siempre
        out[cls.name] = (det, (time.perf_counter() - t0) * 1e3)
    return out


@lru_cache(maxsize=64)
def _mod(tipo, magnitud, sitio, semilla):
    return inyectar(_base(semilla), tipo, magnitud, [sitio], semilla)


def escenario(tipo, magnitud, sitio, semilla) -> dict:
    tipo, m, sitio, s = parsear(tipo, magnitud, sitio, semilla)
    var, unidad = VARIABLE[tipo]
    base = _base(s)
    mod, eventos = _mod(tipo, m, sitio, s)
    modelos = _modelos(s)
    pos = np.flatnonzero(((mod.site_id == sitio) & (mod.split == "evaluacion")).to_numpy())
    test = mod.iloc[pos]

    esp = modelos[RESIDUAL][0].esperado(test, var)
    serie = [{"timestamp": iso(t), "observado": round(float(o), 3), "esperado": round(float(e), 3)}
             for t, o, e in zip(test["timestamp"], test[var], esp)]

    dets = []
    for did, (det, fit_ms) in modelos.items():
        t0 = time.perf_counter()
        p = det.predict(test)
        pred_ms = (time.perf_counter() - t0) * 1e3
        full = np.zeros(len(mod), dtype=bool)
        full[pos] = p
        r = evaluar(full, mod, base, eventos, sitio, var)
        dets.append({"id": did, "alertas": [iso(t) for t in r["alertas"]],
                     "eventos_detectados": r["eventos_detectados"],
                     "eventos_totales": r["eventos_totales"],
                     "horas_hasta_alerta": r["horas_hasta_alerta"],
                     "falsas_alarmas_dia": r["falsas_alarmas_dia"],
                     "exceso_no_detectado": round(r["exceso_no_detectado"], 3),
                     "fit_ms": round(fit_ms, 2), "pred_ms": round(pred_ms, 2)})
    return {"simulated": True,
            "parametros": {"tipo": tipo, "magnitud": m, "sitio": sitio, "semilla": s},
            "variable": var, "unidad": unidad, "serie": serie,
            "eventos_reales": [{"inicio": iso(e["inicio"]), "fin": iso(e["fin"])} for e in eventos],
            "detectores": dets}


def explicacion(tipo, magnitud, sitio, semilla, timestamp) -> dict:
    tipo, m, sitio, s = parsear(tipo, magnitud, sitio, semilla)
    if not timestamp:
        raise ValueError("Falta el parámetro: timestamp.")
    try:
        ts = pd.Timestamp(timestamp)
    except Exception:
        raise ValueError("timestamp no válido.") from None
    mod, _ = _mod(tipo, m, sitio, s)
    return explicar(mod, _modelos(s)[RESIDUAL][0], sitio, ts, VARIABLE[tipo][0])


def barrido(tipo) -> dict:
    if tipo not in TIPOS:
        raise ValueError("tipo debe ser fuga o ineficiencia.")
    f = RES / f"sweep_{tipo}.json"
    if not f.exists():
        raise FileNotFoundError(f)
    data = json.loads(f.read_text(encoding="utf-8"))
    data["simulated"] = True
    return data