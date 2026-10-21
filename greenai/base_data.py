"""Datos limpios (sin anomalias) con la misma formula de tools/generate_data.py.
dificil=True: agua con ruido +-5 % y termino no lineal (+0.004*max(0,temp-24)**2)."""
import math
import random
from datetime import datetime, timedelta, timezone

import pandas as pd

SEED_KIT = 22102026
SITIOS = [("SIM-A", "aire", .35, .03), ("SIM-B", "evaporativa", .22, .8),
          ("SIM-C", "liquida", .18, .2)]
COLS = ["timestamp", "site_id", "cooling_type", "energy_it_kwh", "energy_total_kwh",
        "water_l", "load_pct", "outdoor_temp_c", "inlet_temp_c", "ot_event",
        "split", "is_simulated"]


def generar_base(semilla: int, dificil: bool = False) -> pd.DataFrame:
    rng = random.Random(semilla)
    rng_agua = random.Random(semilla + 1_000_003)   # no altera el flujo base
    inicio = datetime(2026, 10, 12, tzinfo=timezone.utc)
    filas = []
    for h in range(168):
        for site, cooling, overhead, rate in SITIOS:
            load = 55 + 18 * math.sin((h % 24 - 7) * math.pi / 12) + rng.uniform(-4, 4)
            temp = 23 + 7 * math.sin((h % 24 - 8) * math.pi / 12) + rng.uniform(-1, 1)
            it = 65 + 1.8 * load + rng.uniform(-2, 2)
            total = it * (1 + overhead + max(0, temp - 20) * .004 + rng.uniform(-.015, .015))
            factor = 1 + max(0, temp - 20) * .015
            if dificil:
                factor += .004 * max(0, temp - 24) ** 2
            water = it * rate * factor
            if dificil:
                water *= 1 + rng_agua.uniform(-.05, .05)
            inlet = 23 + max(0, temp - 20) * .18 + rng.uniform(-.5, .5)
            filas.append(dict(
                timestamp=inicio + timedelta(hours=h), site_id=site, cooling_type=cooling,
                energy_it_kwh=round(it, 4), energy_total_kwh=round(total, 4),
                water_l=round(water, 4), load_pct=round(load, 3),
                outdoor_temp_c=round(temp, 3), inlet_temp_c=round(inlet, 3),
                ot_event="normal", split="referencia" if h < 72 else "evaluacion",
                is_simulated=True))
    df = pd.DataFrame(filas, columns=COLS)
    return df.sort_values(["site_id", "timestamp"]).reset_index(drop=True)