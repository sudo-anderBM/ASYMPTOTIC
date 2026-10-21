"""Metricas por evento: detectado, horas hasta la alerta, falsas alarmas, exceso."""
import numpy as np
import pandas as pd

DIAS_EVAL = 4


def evaluar(pred, df_mod: pd.DataFrame, df_base: pd.DataFrame, eventos, sitio: str, variable: str) -> dict:
    """pred: bool por posicion, mismo largo e indice que df_mod (False en referencia)."""
    pred = np.asarray(pred, dtype=bool)
    if len(pred) != len(df_mod):
        raise ValueError("pred y df_mod deben tener el mismo largo")
    del_sitio = (df_mod["site_id"] == sitio).to_numpy()
    evs = [e for e in eventos if e["sitio"] == sitio]

    alertas_pos = np.flatnonzero(pred & del_sitio)
    en_ventana = set(f for e in evs for f in e["filas"])

    detectados, horas, exceso = 0, [], 0.0
    for e in evs:
        filas = e["filas"]
        hit = [i for i, f in enumerate(filas) if pred[f]]
        antes = filas if not hit else filas[:hit[0]]
        if antes:
            exceso += float((df_mod.loc[antes, variable] - df_base.loc[antes, variable]).sum())
        if hit:
            detectados += 1
            horas.append(float(hit[0]))        # ventana con paso de 1 h

    fuera = [p for p in alertas_pos if p not in en_ventana]
    return dict(
        alertas=[df_mod.loc[p, "timestamp"] for p in alertas_pos],
        eventos_detectados=detectados,
        eventos_totales=len(evs),
        horas_hasta_alerta=float(np.mean(horas)) if horas else None,
        falsas_alarmas_dia=len(fuera) / DIAS_EVAL,
        exceso_no_detectado=exceso,
    )