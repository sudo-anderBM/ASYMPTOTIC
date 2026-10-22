"""Ataques de falsificación de lecturas (idea tomada de ThermoShield).

Pregunta: si alguien manipula un medidor para ocultar una fuga, ¿lo notan
los cinco detectores? Se inyectan cuatro ataques en los datos limpios de
evaluación y se cuenta en cuántas ventanas de 12 h aparece al menos una
alarma. La misma cuenta sin ataque da la línea de "alarma por azar".

  fijo       la temperatura de entrada se congela en su primer valor
  deriva     el medidor de agua marca 1 % menos cada hora (oculta consumo)
  replay     el medidor de agua repite lo que marcó 24 h antes
  coherente  se repite la fila COMPLETA de 24 h antes (todas las columnas)

Los detectores no se modifican y se ajustan solo con la referencia.

Uso desde la raíz:
    python -m greenai.ataques            # escribe results/ataques.json
    python -m greenai.integridad --actualizar   # registra su huella

Origen de la idea: https://github.com/sudo-anderBM/ThermoShield (src/attacks.py).
Los parámetros (12 h, -1 %/h, 24 h) los elegimos para datos horarios.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from greenai.base_data import generar_base
from greenai.detectors import IForest, ResidualCusum, ResidualSigma, RulesVec, ZRules

RES = Path(__file__).resolve().parents[1] / "results"
DETECTORES = {"Reglas": RulesVec, "IsolationForest": IForest,
              "Residual 3σ": ResidualSigma, "CUSUM": ResidualCusum, "Z-score": ZRules}
SITIOS = ("SIM-A", "SIM-B", "SIM-C")
COLUMNAS = ["energy_it_kwh", "energy_total_kwh", "water_l", "load_pct",
            "outdoor_temp_c", "inlet_temp_c"]
ATAQUES = {
    "sin_ataque": "Sin ataque (alarma por azar)",
    "fijo": "Valor fijo en la temperatura de entrada",
    "deriva": "Deriva de -1 %/h en el agua",
    "replay": "Replay de 24 h solo del agua",
    "coherente": "Replay coherente de la fila completa",
}
DURACION = 12        # horas de cada ataque
INICIOS = (30, 60)   # hora de evaluación en que empieza (deja 24 h previas)


def atacar(ev, tipo: str, sitio: str, t0: int, dur: int = DURACION):
    """Devuelve (datos atacados, máscara booleana de la ventana atacada)."""
    ev = ev.copy()
    idx = ev.index[ev["site_id"] == sitio]
    w, antes = idx[t0:t0 + dur], idx[t0 - 24:t0 - 24 + dur]
    if tipo == "fijo":
        ev.loc[w, "inlet_temp_c"] = ev.loc[w[0], "inlet_temp_c"]
    elif tipo == "deriva":
        ev.loc[w, "water_l"] = ev.loc[w, "water_l"] * (1 - 0.01 * np.arange(1, dur + 1))
    elif tipo == "replay":
        ev.loc[w, "water_l"] = ev.loc[antes, "water_l"].to_numpy()
    elif tipo == "coherente":
        ev.loc[w, COLUMNAS] = ev.loc[antes, COLUMNAS].to_numpy()
    elif tipo != "sin_ataque":
        raise ValueError(f"Ataque desconocido: {tipo}")
    return ev, ev.index.isin(w)


def evaluar(semillas=range(1, 11)) -> dict:
    hits = {(a, d): [] for a in ATAQUES for d in DETECTORES}
    for semilla in semillas:
        base = generar_base(semilla)
        ref = base[base["split"] == "referencia"]
        ev0 = base[base["split"] == "evaluacion"]
        modelos = {n: cls(use_ot=False) for n, cls in DETECTORES.items()}
        for m in modelos.values():
            m.fit(ref)
        for ataque in ATAQUES:
            for sitio in SITIOS:
                for t0 in INICIOS:
                    ev, ventana = atacar(ev0, ataque, sitio, t0)
                    for n, m in modelos.items():
                        alarma = np.asarray(m.predict(ev)).astype(bool)
                        hits[(ataque, n)].append(bool(alarma[ventana].any()))
    n = len(next(iter(hits.values())))
    return {
        "simulated": True,
        "pregunta": "% de ventanas de 12 h con al menos una alarma",
        "ventanas_por_celda": n,
        "semillas": list(semillas),
        "ataques": ATAQUES,
        "detectores": list(DETECTORES),
        "tasa": {a: {d: round(float(np.mean(hits[(a, d)])), 3) for d in DETECTORES}
                 for a in ATAQUES},
        "nota": "Una tasa solo indica detección si supera claramente la de sin_ataque.",
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Ataques de falsificación de lecturas")
    p.add_argument("--semillas", type=int, default=10)
    args = p.parse_args(argv)
    r = evaluar(range(1, args.semillas + 1))
    RES.mkdir(exist_ok=True)
    (RES / "ataques.json").write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n",
                                      encoding="utf-8")
    print(f"{'ataque':38}" + "".join(f"{d:>17}" for d in DETECTORES))
    for a, nombre in ATAQUES.items():
        print(f"{nombre:38}" + "".join(f"{r['tasa'][a][d]:>17.0%}" for d in DETECTORES))
    print(f"\n{r['ventanas_por_celda']} ventanas por celda. Escrito results/ataques.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
