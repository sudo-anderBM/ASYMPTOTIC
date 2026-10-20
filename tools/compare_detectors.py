"""Comparación educativa opcional. Tiempo/energía: estimaciones, no medición física."""
import argparse
import json
import math
import sys
import time
import tracemalloc
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common.cifox import load_data, flagged


def score(y, pred):
    tp=sum(bool(a) and bool(b) for a,b in zip(y,pred))
    fp=sum(not bool(a) and bool(b) for a,b in zip(y,pred))
    fn=sum(bool(a) and not bool(b) for a,b in zip(y,pred))
    return dict(tp=tp,fp=fp,fn=fn,precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None)


def run(method='rules',watts=30.,carbon=300.):
    if not math.isfinite(watts) or not math.isfinite(carbon) or watts<0 or carbon<0: raise ValueError('Supuestos finitos y no negativos')
    df=load_data();train=df[df.split=='referencia'];test=df[df.split=='evaluacion']
    # Imports excluded; include model fitting and prediction. Data loading excluded.
    if method=='isolation_forest':
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import make_pipeline
    tracemalloc.start();t0=time.perf_counter();c0=time.process_time()
    if method=='rules': pred=flagged(test).rule_alert.to_numpy()
    elif method=='isolation_forest':
        features=['energy_it_kwh','energy_total_kwh','water_l','load_pct','outdoor_temp_c','inlet_temp_c']
        model=make_pipeline(StandardScaler(),IsolationForest(n_estimators=100,contamination=.05,random_state=22102026,n_jobs=1))
        model.fit(train[features]);pred=model.predict(test[features])==-1
    else: raise ValueError('Método desconocido')
    elapsed=time.perf_counter()-t0;cpu=time.process_time()-c0;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    energy_est=watts*elapsed/3_600_000
    return dict(method=method,simulated_data=True,train_rows=len(train),test_rows=len(test),scores=score(test.simulated_anomaly,pred),wall_seconds=elapsed,cpu_seconds=cpu,python_peak_bytes=peak,assumed_watts=watts,estimated_kwh=energy_est,assumed_gco2e_per_kwh=carbon,estimated_gco2e=energy_est*carbon,note='Estimación de escenario; no medida. Sin PUE ni agua ni fabricación/red/imports. Python peak no es RAM total. Tiempo incluye entrenamiento para IF; reglas no entrenan. OT no está en features IF.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--method',choices=['rules','isolation_forest'],default='rules');p.add_argument('--assumed-watts',type=float,default=30);p.add_argument('--assumed-gco2e-per-kwh',type=float,default=300);a=p.parse_args()
    print(json.dumps(run(a.method,a.assumed_watts,a.assumed_gco2e_per_kwh),ensure_ascii=False,indent=2))
