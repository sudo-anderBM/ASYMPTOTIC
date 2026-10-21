"""Explicacion de una alerta: observado vs esperado, desviacion y z."""
import pandas as pd

UNIDAD = {"water_l": "L", "energy_total_kwh": "kWh"}
NOMBRE = {"water_l": "Agua", "energy_total_kwh": "Energía total"}
AVISO = "Señal para revisión humana; no es un diagnóstico."


def explicar(df_mod: pd.DataFrame, modelo, sitio: str, timestamp, variable: str) -> dict:
    ts = pd.Timestamp(timestamp)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    m = ((df_mod["site_id"] == sitio) & (df_mod["timestamp"] == ts)).to_numpy()
    if not m.any():
        raise ValueError("timestamp fuera del rango del sitio")
    fila = df_mod[m]
    obs = float(fila[variable].iloc[0])
    esp = float(modelo.esperado(fila, variable)[0])
    z = float(modelo.z(fila, variable)[0])
    desv = (obs - esp) / esp * 100 if esp else None
    carga = float(fila["load_pct"].iloc[0])
    temp = float(fila["outdoor_temp_c"].iloc[0])
    if desv is None:
        texto = "Sin valor esperado para comparar."
    else:
        sentido = "por encima" if desv >= 0 else "por debajo"
        texto = (f"{NOMBRE[variable]} {abs(desv):.1f} % {sentido} de lo esperado "
                 f"para {carga:.0f} % de carga y {temp:.1f} °C.")
    return dict(simulated=True, timestamp=ts.strftime("%Y-%m-%dT%H:%M:%SZ"), sitio=sitio,
                variable=variable, unidad=UNIDAD[variable],
                observado=round(obs, 2), esperado=round(esp, 2),
                desviacion_pct=None if desv is None else round(desv, 1),
                z=round(z, 1), carga_pct=round(carga, 1), temp_exterior_c=round(temp, 1),
                texto=texto, aviso=AVISO)