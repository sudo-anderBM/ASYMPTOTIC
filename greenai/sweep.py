"""Barrido de magnitudes: genera results/sweep_{tipo}.json.
python -m greenai.sweep [--semillas 10] [--reps 10]"""
import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from greenai.base_data import generar_base
from greenai.bench import medir, wilson
from greenai.detectors import ALL
from greenai.events import evaluar
from greenai.scenarios import SITIOS, TIPOS, inyectar

RES = Path(__file__).resolve().parents[1] / "results"
MAGS = [0.05, 0.1, 0.2, 0.3, 0.5, 1.0]
VARIABLE = {"fuga": "water_l", "ineficiencia": "energy_total_kwh"}


def _punto(tipo, dificil, semillas):
    """-> {id: {mag: [detectados, totales, [falsas_alarmas_dia por semilla]]}}"""
    var = VARIABLE[tipo]
    acc = {c.name: {m: [0, 0, []] for m in MAGS} for c in ALL}
    for s in range(1, semillas + 1):
        base = generar_base(s, dificil=dificil)
        ref = base[base.split == "referencia"]
        modelos = {c.name: c(False).fit(ref) for c in ALL}      # una vez por semilla
        pos_eval = np.flatnonzero((base.split == "evaluacion").to_numpy())
        for m in MAGS:
            mod, eventos = inyectar(base, tipo, m, SITIOS, s)
            test = mod.iloc[pos_eval]
            for nombre, det in modelos.items():
                full = np.zeros(len(mod), dtype=bool)
                full[pos_eval] = det.predict(test)
                det_n = tot = 0
                fa = []
                for sitio in SITIOS:
                    r = evaluar(full, mod, base, eventos, sitio, var)
                    det_n += r["eventos_detectados"]
                    tot += r["eventos_totales"]
                    fa.append(r["falsas_alarmas_dia"])
                a = acc[nombre][m]
                a[0] += det_n
                a[1] += tot
                a[2].append(float(np.mean(fa)))
    return acc


def _bloque(acc, costo):
    out = []
    for c in ALL:
        d = acc[c.name]
        det = [d[m][0] / d[m][1] for m in MAGS]
        ic = [list(wilson(d[m][0], d[m][1])) for m in MAGS]
        fa = [round(float(np.mean(d[m][2])), 3) for m in MAGS]
        out.append({"id": c.name, "deteccion": [round(x, 3) for x in det],
                    "deteccion_ic95": ic, "falsas_alarmas_dia": fa,
                    "fit_ms": costo[c.name][0], "pred_ms": costo[c.name][1],
                    "fit_desv_ms": costo[c.name][2], "pred_desv_ms": costo[c.name][3]})
    return out


def _costo(reps):
    base = generar_base(1)
    tr = base[base.split == "referencia"]
    te = base[base.split == "evaluacion"]
    out = {}
    for c in ALL:
        _, F, P, _, _ = medir(c, False, tr, te, reps, 2)
        out[c.name] = (round(float(np.median(F[:, 0])) * 1e3, 2),
                       round(float(np.median(P[:, 0])) * 1e3, 2),
                       round(float(np.std(F[:, 0], ddof=1)) * 1e3, 2) if len(F) > 1 else 0.0,
                       round(float(np.std(P[:, 0], ddof=1)) * 1e3, 2) if len(P) > 1 else 0.0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--semillas", type=int, default=10)
    ap.add_argument("--reps", type=int, default=10)
    a = ap.parse_args()

    import sklearn
    costo = _costo(a.reps)
    RES.mkdir(exist_ok=True)
    for tipo in TIPOS:
        data = {"simulated": True, "tipo": tipo, "magnitudes": MAGS,
                "normal": _bloque(_punto(tipo, False, a.semillas), costo),
                "dificil": _bloque(_punto(tipo, True, a.semillas), costo),
                "meta": {"semillas": a.semillas, "eventos_por_punto": 9 * a.semillas,
                         "generado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "equipo": platform.platform(),
                         "python": sys.version.split()[0],
                         "numpy": np.__version__,
                         "pandas": pd.__version__,
                         "sklearn": sklearn.__version__,
                         "filas_ref": 216,
                         "filas_eval": 288,
                         "nota": "Tiempos medidos en este equipo (mediana, datos normales, "
                                 f"{a.reps} repeticiones). Datos simulados."}}
        (RES / f"sweep_{tipo}.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"OK results/sweep_{tipo}.json")


if __name__ == "__main__":
    main()