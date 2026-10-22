"""Tabla oficial de cifras: todo sale del codigo y de los resultados reales.

Uso (desde la raiz, con el venv):  python -m greenai.cifras
Llama a los endpoints con TestClient: son las mismas cifras que ve la pagina.
"""
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
from fastapi.testclient import TestClient  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from stack_b_api_web.main import app  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
client = TestClient(app)

FACTOR_OFICIAL = 0.444
FUENTE_FACTOR = (
    "0.444 tCO2e/MWh (= kg CO2e/kWh): factor del Sistema Electrico Nacional 2024, "
    "aviso de SEMARNAT del 28/02/2025 (gob.mx, aviso_fesen_2024.pdf)"
)
SITIOS = ("SIM-A", "SIM-B", "SIM-C")


def get(ruta, **params):
    r = client.get(ruta, params=params)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {r.text[:300]}"
    return r.json(), None


def titulo(texto):
    print(f"\n=== {texto} ===")


def redondear(obj, n=3):
    if isinstance(obj, float):
        return round(obj, n)
    if isinstance(obj, dict):
        return {k: redondear(v, n) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redondear(v, n) for v in obj]
    return obj


# 1. PUE, WUE y CUE por sitio, con y sin problema ---------------------------
titulo("1. PUE, WUE y CUE por sitio (fuga 10 %, semilla 1, generador simulado)")
print(f"{'sitio':6}| sin problema: PUE    WUE    CUE | con problema: PUE    WUE    CUE")
factor = None
for sitio in SITIOS:
    d, err = get("/api/scenario", tipo="fuga", magnitud=0.1, sitio=sitio, semilla=1)
    if err:
        print(sitio, err)
        continue
    m = d["metricas"]
    s, c = m["sin_problema"], m["con_problema"]
    factor = m["factor_kg_co2e_kwh"]
    print(f"{sitio:6}| {s['pue']:>19.3f} {s['wue_l_kwh']:>6.3f} {s['cue_kg_kwh']:>6.3f} "
          f"| {c['pue']:>19.3f} {c['wue_l_kwh']:>6.3f} {c['cue_kg_kwh']:>6.3f}")
print("PUE = suma total / suma IT; WUE en L/kWh; CUE (kg CO2e/kWh de IT) = PUE x factor.")

titulo("2. Factor de emision usado")
print("En la API:", factor, "kg CO2e/kWh")
print("Fuente oficial:", FUENTE_FACTOR)
if factor is not None and abs(factor - FACTOR_OFICIAL) > 1e-9:
    print("AVISO: la API no usa 0.444; revisa FACTOR_RED_KG_KWH en greenai/service.py")

# 3. Demo de una corrida ------------------------------------------------------
titulo("3. Demo (UNA corrida): fuga 10 %, SIM-B, semilla 1. Tiempos ruidosos: para la lamina usa la seccion 4")
d, err = get("/api/scenario", tipo="fuga", magnitud=0.1, sitio="SIM-B", semilla=1)
if err:
    print(err)
else:
    print(f"{'detector':22}{'detectados':>11}{'h hasta alerta':>16}{'FA/dia':>8}")
    for x in d["detectores"]:
        h = x["horas_hasta_alerta"]
        print(f"{x['id']:22}{x['eventos_detectados']:>7}/{x['eventos_totales']:<3}"
              f"{('-' if h is None else h):>16}{x['falsas_alarmas_dia']:>8}")

# 4. Barrido (sweep_fuga.json) -----------------------------------------------
titulo("4. Barrido de fugas de agua: deteccion al 10 % (90 eventos por punto)")
sw, err = get("/api/sweep", tipo="fuga")
if err:
    print(err)
else:
    mags = sw["magnitudes"]
    i10 = mags.index(0.1)
    print("Magnitudes del barrido:", ", ".join(f"{m * 100:g} %" for m in mags))
    for modo in ("normal", "dificil"):
        print(f"\n-- datos {modo} --")
        print(f"{'detector':22}{'det. 10 %':>10}{'IC 95 %':>12}{'FA/dia':>9}"
              f"{'fit+pred ms':>13}{'>=90 % desde':>14}   curva (% por magnitud)")
        for x in sw[modo]:
            det = x["deteccion"][i10]
            lo, hi = x["deteccion_ic95"][i10]
            fa = x["falsas_alarmas_dia"][i10]
            costo = x["fit_ms"] + x["pred_ms"]
            desde = next((f"{m * 100:g} %" for m, v in zip(mags, x["deteccion"]) if v >= 0.9), "nunca")
            curva = " ".join(f"{v * 100:.0f}" for v in x["deteccion"])
            print(f"{x['id']:22}{det * 100:>8.0f} %{f'[{lo * 100:.0f}-{hi * 100:.0f}]':>12}"
                  f"{fa:>9.3f}{costo:>13.1f}{desde:>14}   {curva}")
    print("\nmeta:", json.dumps(redondear(sw.get("meta")), ensure_ascii=False)[:500])

# 5. Balance neto ---------------------------------------------------------------
titulo("5. Balance neto del detector (fuga 10 %, SIM-B, 7 dias)")
b, err = get("/api/balance", tipo="fuga", magnitud=0.1, sitio="SIM-B", semilla=1, dias=7)
if err:
    print(err)
else:
    print("Supuestos:", json.dumps(redondear(b["supuestos"], 6), ensure_ascii=False))
    print("Costo anual del detector:", json.dumps(redondear(b["costo_detector_anual"], 8), ensure_ascii=False))
    print("Beneficio:", json.dumps(redondear(b["beneficio"], 3), ensure_ascii=False))
    print("Balance positivo:", b["balance_positivo"])
    if abs(b["supuestos"]["factor_kg_co2e_kwh"] - FACTOR_OFICIAL) > 1e-9:
        print("AVISO: /api/balance NO usa 0.444; el balance y la seccion 1 se contradicen")
print("\nTodas las cifras son de datos simulados; energia y CO2 son estimaciones con supuestos.")