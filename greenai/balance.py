"""Balance neto: costo anual del detector vs lo que evita. Todo estimado."""
import json
from pathlib import Path

from greenai.service import _base, FACTOR_RED_KG_KWH  # noqa: F401

RES = Path(__file__).resolve().parents[1] / "results"
VAR = {"fuga": "water_l", "ineficiencia": "energy_total_kwh"}


def _tiempos():
    d = json.loads((RES / "sweep_fuga.json").read_text(encoding="utf-8"))
    r = next(x for x in d["normal"] if x["id"] == "3_residual_3sigma")
    return r["fit_ms"] / 1e3, r["pred_ms"] / 1e3


def calcular(tipo, magnitud, sitio, semilla, dias, watts, factor, l_por_kwh) -> dict:
    fit_s, pred_s = _tiempos()
    seg = pred_s * (8760 * 3 / 288) + fit_s * 365
    kwh = watts * seg / 3_600_000
    costo = {"segundos_cpu": round(seg, 3), "kwh": kwh,
             "g_co2e": kwh * factor * 1000, "l_agua_indirecta": kwh * l_por_kwh}

    base = _base(semilla)
    g = base[(base.site_id == sitio) & (base.split == "evaluacion")]
    perdida = float(g[VAR[tipo]].mean()) * magnitud
    total = perdida * 24 * dias
    if tipo == "fuga":
        ben = {"unidad": "L", "perdida_por_hora": round(perdida, 2),
               "evitado": round(total, 1), "kwh_evitados": None, "kg_co2e_evitados": None}
        positivo = total > costo["l_agua_indirecta"]
    else:
        ben = {"unidad": "kWh", "perdida_por_hora": round(perdida, 2), "evitado": None,
               "kwh_evitados": round(total, 1), "kg_co2e_evitados": round(total * factor, 2)}
        positivo = total > kwh
    return {"simulated": True,
            "supuestos": {"watts": watts, "factor_kg_co2e_kwh": factor,
                          "agua_indirecta_l_kwh": l_por_kwh, "dias_sin_detector": dias,
                          "revisiones_por_anio": 8760, "reentrenos_por_anio": 365},
            "costo_detector_anual": costo, "beneficio": ben, "balance_positivo": positivo}