"""API de demostración, de solo lectura y sin servicios externos.

Desde la raíz del kit:
    python -m uvicorn stack_b_api_web.main:app --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from common.cifox import flagged, load_data, metrics  # noqa: E402
from greenai import balance as balance_calc  # noqa: E402
from greenai import service  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
DATA_FILE = ROOT / "data" / "operaciones_simuladas.csv"
FILTER_COLUMNS = ("site_id", "cooling_type", "split")

app = FastAPI(
    title="CIFOX · API de demostración",
    description="Solo lectura. Todos los datos son simulados; no controla equipos.",
    version="1.0.0",
    docs_url=None,  # El visor predeterminado usa una CDN. Este kit funciona offline.
    redoc_url=None,
)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.middleware("http")
async def local_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; font-src 'self'; "
        "object-src 'none'; frame-ancestors 'none'; base-uri 'self'"
    )
    response.headers["Cache-Control"] = "no-store"
    return response


def _data() -> pd.DataFrame:
    try:
        return load_data(DATA_FILE)
    except (OSError, ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=503,
            detail="No se pueden leer los datos de ejemplo. Comprueba el CSV del kit.",
        ) from exc


def _filters(df: pd.DataFrame) -> dict[str, list[str]]:
    return {
        column: sorted(str(value) for value in df[column].dropna().unique())
        for column in FILTER_COLUMNS
        if column in df.columns
    }


def _select(
    df: pd.DataFrame,
    site_id: str | None,
    cooling_type: str | None,
    split: str | None,
) -> pd.DataFrame:
    options = _filters(df)
    for column, value in zip(FILTER_COLUMNS, (site_id, cooling_type, split)):
        if value is None:
            continue
        if value not in options.get(column, []):
            raise HTTPException(status_code=422, detail=f"Filtro no válido: {column}.")
        df = df.loc[df[column].astype(str) == value]
    return df.copy()


def _safe(value: Any) -> Any:
    """Convierte escalares de pandas/numpy y evita NaN en JSON."""
    if isinstance(value, dict):
        return {str(key): _safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    if hasattr(value, "item"):
        return _safe(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html", media_type="text/html")


@app.get("/health")
@app.get("/api/health")
def health():
    """Comprueba también que el CSV se puede cargar."""
    df = _data()
    return {"status": "ok", "simulated": True, "read_only": True, "rows": len(df)}


@app.get("/api/metrics")
def get_metrics(
    site_id: str | None = Query(default=None, max_length=40),
    cooling_type: str | None = Query(default=None, max_length=40),
    split: str | None = Query(default=None, max_length=40),
):
    full = _data()
    selected = _select(full, site_id, cooling_type, split)
    if selected.empty:
        values = dict(pue=None, wue_l_kwh=None, energy_it_kwh=0, energy_total_kwh=0,
                      water_l=0, rows=0, rule_alerts=0)
    else:
        values = metrics(selected)
    timestamps = pd.to_datetime(selected["timestamp"], utc=True) if len(selected) else None
    return _safe({
        **values,
        "simulated": True,
        "read_only": True,
        "filters": _filters(full),
        "selected_filters": {"site_id": site_id, "cooling_type": cooling_type, "split": split},
        "period_start": timestamps.min().isoformat() if timestamps is not None else None,
        "period_end": timestamps.max().isoformat() if timestamps is not None else None,
        "source": "operaciones_simuladas.csv",
    })


@app.get("/api/records")
def get_records(
    limit: int = Query(default=100, ge=1, le=1000),
    site_id: str | None = Query(default=None, max_length=40),
    cooling_type: str | None = Query(default=None, max_length=40),
    split: str | None = Query(default=None, max_length=40),
    alerts_only: bool = False,
):
    selected = _select(_data(), site_id, cooling_type, split)
    selected = flagged(selected)
    if alerts_only:
        selected = selected.loc[selected["rule_alert"].astype(bool)]
    selected = selected.sort_values(["timestamp", "site_id"], ascending=[False, True])
    # pandas serializa correctamente las fechas, los booleanos y los valores nulos.
    records = json.loads(selected.head(limit).to_json(orient="records", date_format="iso"))
    return {"simulated": True, "total": len(selected), "returned": len(records), "records": records}


# ---------------------------------------------------------------------------
# Deteccion de fugas e ineficiencias (nuestro aporte; el resto es del kit)
# Parametros como str y validacion manual: asi `detail` siempre es texto.
# ---------------------------------------------------------------------------
def _422(fn, *args):
    try:
        return _safe(fn(*args))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.get("/api/detectors")
def api_detectors():
    return {"simulated": True, "detectores": service.DETECTORES}


@app.get("/api/scenario")
def api_scenario(
    tipo: str | None = Query(default=None, max_length=40),
    magnitud: str | None = Query(default=None, max_length=20),
    sitio: str | None = Query(default=None, max_length=40),
    semilla: str | None = Query(default=None, max_length=20),
):
    return _422(service.escenario, tipo, magnitud, sitio, semilla)


@app.get("/api/explain")
def api_explain(
    tipo: str | None = Query(default=None, max_length=40),
    magnitud: str | None = Query(default=None, max_length=20),
    sitio: str | None = Query(default=None, max_length=40),
    semilla: str | None = Query(default=None, max_length=20),
    timestamp: str | None = Query(default=None, max_length=40),
):
    return _422(service.explicacion, tipo, magnitud, sitio, semilla, timestamp)


@app.get("/api/sweep")
def api_sweep(tipo: str | None = Query(default=None, max_length=40)):
    try:
        return _422(service.barrido, tipo)
    except FileNotFoundError:
        raise HTTPException(
            status_code=503, detail="Falta ejecutar python -m greenai.sweep"
        ) from None


# ---------------------------------------------------------------------------
# Balance neto: costo anual del detector frente a lo que evita (estimado).
# ---------------------------------------------------------------------------
def _num(valor, nombre: str, lo: float, hi: float) -> float:
    try:
        x = float(valor)
    except (TypeError, ValueError):
        raise ValueError(f"{nombre} debe ser un número entre {lo:g} y {hi:g}.") from None
    if not math.isfinite(x) or not lo <= x <= hi:
        raise ValueError(f"{nombre} debe ser un número entre {lo:g} y {hi:g}.")
    return x


def _balance(tipo, magnitud, sitio, semilla, dias, watts, factor, l_por_kwh):
    tipo, m, sitio, s = service.parsear(tipo, magnitud, sitio, semilla)
    return balance_calc.calcular(
        tipo, m, sitio, s,
        _num(dias, "dias", 1, 365),
        _num(watts, "watts", 1, 1000),
        _num(factor, "factor", 0, 2),
        _num(l_por_kwh, "l_por_kwh", 0, 10),
    )


@app.get("/api/balance")
def api_balance(
    tipo: str | None = Query(default=None, max_length=40),
    magnitud: str | None = Query(default=None, max_length=20),
    sitio: str | None = Query(default=None, max_length=40),
    semilla: str | None = Query(default="1", max_length=20),
    dias: str | None = Query(default="7", max_length=20),
    watts: str | None = Query(default="30", max_length=20),
    factor: str | None = Query(default="0.444", max_length=20),
    l_por_kwh: str | None = Query(default="1.2", max_length=20),
):
    return _422(_balance, tipo, magnitud, sitio, semilla, dias, watts, factor, l_por_kwh)