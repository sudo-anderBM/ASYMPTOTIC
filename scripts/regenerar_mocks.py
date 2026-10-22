"""Regenera scenario.json y balance.json con respuestas reales (TestClient, sin servidor).

Uso (desde la raiz):  python scripts/regenerar_mocks.py
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

DESTINO = ROOT / "stack_b_api_web" / "static" / "mock"
client = TestClient(app)
BASE = dict(tipo="fuga", magnitud=0.1, sitio="SIM-B", semilla=1)
PEDIDOS = {
    "scenario.json": ("/api/scenario", BASE),
    "balance.json": ("/api/balance", {**BASE, "dias": 7}),
}

for nombre, (ruta, params) in PEDIDOS.items():
    r = client.get(ruta, params=params)
    if r.status_code != 200:
        raise SystemExit(f"{ruta} -> HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    if data.get("simulated") is not True:
        raise SystemExit(f"{ruta} no trae simulated: true")
    (DESTINO / nombre).write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print("OK ", nombre)

balance = json.loads((DESTINO / "balance.json").read_text(encoding="utf-8"))
print("factor en balance.json:", balance["supuestos"]["factor_kg_co2e_kwh"])
print("g CO2e del detector al anio:", balance["costo_detector_anual"]["g_co2e"])