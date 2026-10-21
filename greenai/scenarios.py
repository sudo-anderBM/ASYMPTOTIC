"""Inyecta fugas de agua o ineficiencias de tamano controlado, solo en evaluacion."""
import random

import pandas as pd

TIPOS = ("fuga", "ineficiencia")
SITIOS = ("SIM-A", "SIM-B", "SIM-C")
BLOQUE, VENTANA = 32, 6


def _ventanas(semilla: int, sitio: str):
    """3 ventanas (offset_inicio, offset_fin_incluido) dentro de las 96 h de evaluacion."""
    rng = random.Random(semilla * 1000 + SITIOS.index(sitio))
    out = []
    for b in range(3):
        ini = b * BLOQUE + rng.randint(0, BLOQUE - VENTANA)
        out.append((ini, ini + VENTANA - 1))
    return out


def inyectar(df: pd.DataFrame, tipo: str, magnitud: float, sitios, semilla: int):
    """Devuelve (df_mod, eventos). eventos = [{sitio, inicio, fin, filas}]; fin incluido."""
    if tipo not in TIPOS:
        raise ValueError(f"tipo desconocido: {tipo}")
    if not 0 <= magnitud <= 1:
        raise ValueError("magnitud fuera de 0..1")
    chk = df.sort_values(["site_id", "timestamp"]).reset_index(drop=True)
    if not (chk.index == df.index).all() or not (chk["timestamp"].to_numpy() == df["timestamp"].to_numpy()).all():
        raise ValueError("df debe venir ordenado por site_id, timestamp con indice limpio")

    out = df.copy()
    eventos = []
    for sitio in sitios:
        pos = df.index[(df.site_id == sitio) & (df.split == "evaluacion")].to_numpy()
        for ini, fin in _ventanas(semilla, sitio):
            filas = [int(p) for p in pos[ini:fin + 1]]
            if tipo == "fuga":
                out.loc[filas, "water_l"] = df.loc[filas, "water_l"] * (1 + magnitud)
            else:
                it = df.loc[filas, "energy_it_kwh"]
                out.loc[filas, "energy_total_kwh"] = it + (df.loc[filas, "energy_total_kwh"] - it) * (1 + magnitud)
            eventos.append(dict(sitio=sitio, inicio=df.loc[filas[0], "timestamp"],
                                fin=df.loc[filas[-1], "timestamp"], filas=filas))
    return out, eventos