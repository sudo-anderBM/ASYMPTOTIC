"""Genera static/mock/balance.json a partir del CSV simulado del kit.

Uso (desde la raíz):  python scripts/generar_balance.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from common.cifox import load_data, metrics  # noqa: E402

SALIDA = ROOT / "stack_b_api_web" / "static" / "mock" / "balance.json"


def _fila(m: dict) -> dict:
    return {
        "energia_it_kwh": round(float(m["energy_it_kwh"]), 2),
        "energia_total_kwh": round(float(m["energy_total_kwh"]), 2),
        "agua_l": round(float(m["water_l"]), 2),
        "pue": round(float(m["pue"]), 4),
        "wue_l_kwh": round(float(m["wue_l_kwh"]), 4),
    }


df = load_data(ROOT / "data" / "operaciones_simuladas.csv")
ts = pd.to_datetime(df["timestamp"], utc=True)
fmt = "%Y-%m-%dT%H:%M:%SZ"

sitios = []
for sitio in sorted(df["site_id"].astype(str).unique()):
    sub = df.loc[df["site_id"].astype(str) == sitio]
    sitios.append({
        "sitio": sitio,
        "refrigeracion": str(sub["cooling_type"].iloc[0]),
        **_fila(metrics(sub)),
    })

balance = {
    "simulated": True,
    "nota": "Calculado del CSV simulado del kit (PUE y WUE como cociente de sumas).",
    "periodo": {"inicio": ts.min().strftime(fmt), "fin": ts.max().strftime(fmt)},
    "sitios": sitios,
    "total": _fila(metrics(df)),
}

SALIDA.parent.mkdir(parents=True, exist_ok=True)
SALIDA.write_text(json.dumps(balance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("OK", SALIDA)