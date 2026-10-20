"""Harness GreenAI: repeticiones, calentamiento, fases, memoria, calidad con IC,
energia/CO2 ESTIMADOS con sensibilidad.   python -m greenai.bench --reps 30"""
import argparse, json, math, platform, sys, time, tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd

from common.cifox import load_data
from greenai.detectors import ALL

LABELS = ["scenario", "simulated_anomaly"]
WATTS = [15, 30, 65]            # supuestos editables, NO medidos
GCO2 = [100, 300, 600]
RES = Path("results")


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 3), round(c + h, 3))


def calidad(y, p, seed=22102026, B=2000):
    tp = int((y & p).sum()); fp = int((~y & p).sum()); fn = int((y & ~p).sum())
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else None
    idx = np.random.default_rng(seed).integers(0, len(y), (B, len(y)))
    yy, pp = y[idx], p[idx]
    btp = (yy & pp).sum(1); bfp = (~yy & pp).sum(1); bfn = (yy & ~pp).sum(1)
    den = 2 * btp + bfp + bfn
    bf1 = np.where(den > 0, 2 * btp / np.maximum(den, 1), 0.0)
    lo, hi = np.percentile(bf1, [2.5, 97.5])
    return dict(tp=tp, fp=fp, fn=fn, precision=prec, recall=rec, f1=f1,
                prec_ic95=wilson(tp, tp + fp), recall_ic95=wilson(tp, tp + fn),
                f1_ic95=(round(float(lo), 3), round(float(hi), 3)))


def calibrar(fn, objetivo=0.2, tope=500):
    """Cuantas llamadas por muestra para que dure ~objetivo s (evita la
    resolucion de ~15.6 ms de process_time en Windows)."""
    t0 = time.perf_counter(); fn()
    dt = max(time.perf_counter() - t0, 1e-6)
    return int(min(tope, max(1, math.ceil(objetivo / dt))))


def muestra(fn, inner):
    t0 = time.perf_counter(); c0 = time.process_time()
    for _ in range(inner):
        fn()
    return ((time.perf_counter() - t0) / inner, (time.process_time() - c0) / inner)


def medir(cls, use_ot, train, test, reps, warm):
    mk = lambda: cls(use_ot)
    det = mk().fit(train)
    i_fit = calibrar(lambda: mk().fit(train))
    i_pred = calibrar(lambda: det.predict(test))
    F, P = [], []
    for i in range(warm + reps):
        f = muestra(lambda: mk().fit(train), i_fit)
        p = muestra(lambda: det.predict(test), i_pred)
        if i >= warm:
            F.append(f); P.append(p)
    F, P = np.array(F), np.array(P)
    # memoria: pico de asignaciones Python (NO RAM total), corrida aparte
    tracemalloc.start()
    d = mk().fit(train)
    peak_fit = tracemalloc.get_traced_memory()[1]
    tracemalloc.reset_peak()
    d.predict(test)
    peak_pred = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return det.predict(test), F, P, peak_fit, peak_pred


def resumen(a):
    return dict(media=a.mean(), mediana=np.median(a), desv=a.std(ddof=1), min=a.min())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=30)
    ap.add_argument("--warmup", type=int, default=3)
    a = ap.parse_args()

    df = load_data()
    y_all = df["simulated_anomaly"].to_numpy().astype(bool)
    X = df.drop(columns=LABELS)                      # sin fuga de etiquetas
    tr = X[X["split"] == "referencia"]
    te = X[X["split"] == "evaluacion"]
    y = y_all[(df["split"] == "evaluacion").to_numpy()]

    filas, sens = [], []
    for use_ot in (True, False):
        cfg = "con_OT" if use_ot else "sin_OT"
        for cls in ALL:
            pred, F, P, mf, mp = medir(cls, use_ot, tr, te, a.reps, a.warmup)
            q = calidad(y, pred)
            wf, wp = resumen(F[:, 0]), resumen(P[:, 0])
            cf, cp = resumen(F[:, 1]), resumen(P[:, 1])
            ciclo = F[:, 0].mean() + P[:, 0].mean()
            fila = dict(config=cfg, detector=cls.name, reps=a.reps,
                        fit_wall_mediana_ms=wf["mediana"] * 1e3, fit_wall_media_ms=wf["media"] * 1e3,
                        fit_wall_desv_ms=wf["desv"] * 1e3, fit_cpu_media_ms=cf["media"] * 1e3,
                        pred_wall_mediana_ms=wp["mediana"] * 1e3, pred_wall_media_ms=wp["media"] * 1e3,
                        pred_wall_desv_ms=wp["desv"] * 1e3, pred_cpu_media_ms=cp["media"] * 1e3,
                        pico_py_fit_kb=mf / 1024, pico_py_pred_kb=mp / 1024,
                        mwh_ciclo_30W=30 * ciclo / 3.6e6 * 1e3,
                        **{k: q[k] for k in q})
            filas.append(fila)
            for w in WATTS:
                for g in GCO2:
                    kwh = w * ciclo / 3.6e6
                    sens.append(dict(config=cfg, detector=cls.name, watts=w,
                                     gco2e_kwh=g, mwh=kwh * 1e3, ug_co2e=kwh * g * 1e6))
            print(f"[{cfg}] {cls.name}: F1={q['f1']} fp={q['fp']} fn={q['fn']} "
                  f"pred={wp['mediana']*1e3:.3f} ms fit={wf['mediana']*1e3:.3f} ms", flush=True)

    RES.mkdir(exist_ok=True)
    pd.DataFrame(filas).to_csv(RES / "bench.csv", index=False)
    pd.DataFrame(sens).to_csv(RES / "sensibilidad.csv", index=False)
    import sklearn, scipy
    env = dict(so=platform.platform(), cpu=platform.processor(), python=sys.version,
               numpy=np.__version__, pandas=pd.__version__, sklearn=sklearn.__version__,
               filas_ref=len(tr), filas_eval=len(te), positivos_eval=int(y.sum()),
               reps=a.reps, warmup=a.warmup,
               nota="Tiempos medidos; energia y CO2 son ESTIMACIONES con supuestos. Datos simulados.")
    (RES / "env.json").write_text(json.dumps(env, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nGuardado en results/ (bench.csv, sensibilidad.csv, env.json)")


if __name__ == "__main__":
    main()