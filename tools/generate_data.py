"""Genera datos ficticios reproducibles; biblioteca estándar, semilla 22102026."""
import argparse
import csv
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

SEED = 22102026
FIELDS = ['timestamp','site_id','cooling_type','energy_it_kwh','energy_total_kwh','water_l','load_pct','outdoor_temp_c','inlet_temp_c','ot_event','scenario','simulated_anomaly','split','is_simulated']


def generate(path, seed=SEED):
    rng = random.Random(seed)
    rows = []
    start = datetime(2026,10,12,tzinfo=timezone.utc)
    for h in range(168):
        for site, cooling, overhead, water_rate in [('SIM-A','aire',.35,.03),('SIM-B','evaporativa',.22,.8),('SIM-C','liquida',.18,.2)]:
            load = 55 + 18*math.sin((h%24-7)*math.pi/12) + rng.uniform(-4,4)
            temp = 23 + 7*math.sin((h%24-8)*math.pi/12) + rng.uniform(-1,1)
            it = 65 + 1.8*load + rng.uniform(-2,2)
            total = it*(1+overhead+max(0,temp-20)*.004+rng.uniform(-.015,.015))
            water = it*water_rate*(1+max(0,temp-20)*.015)
            inlet = 23 + max(0,temp-20)*.18+rng.uniform(-.5,.5)
            scenario, ot = 'base', 'normal'
            if 90 <= h < 98 and site=='SIM-A':
                scenario='ineficiencia'; total*=1.3; inlet+=6
            if 118 <= h < 126 and site=='SIM-B':
                scenario='fuga_agua'; water*=2.5
            if 145 <= h < 150 and site=='SIM-C':
                scenario='evento_ot'; ot='login_fallido' if h<148 else 'cambio_config_no_autorizado'
            rows.append(dict(zip(FIELDS,[(start+timedelta(hours=h)).isoformat(),site,cooling,round(it,4),round(total,4),round(water,4),round(load,3),round(temp,3),round(inlet,3),ot,scenario,int(scenario!='base'),'referencia' if h<72 else 'evaluacion',True])))
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS,lineterminator='\n');writer.writeheader();writer.writerows(rows)
    return len(rows)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=SEED);p.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'data'/'operaciones_simuladas.csv');a=p.parse_args()
    print(f'{generate(a.output,a.seed)} filas SIMULADAS: {a.output}')
