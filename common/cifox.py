"""Métricas transparentes para intervalos horarios y perímetro común simulado."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'operaciones_simuladas.csv'
NUMERIC = ['energy_it_kwh', 'energy_total_kwh', 'water_l', 'load_pct', 'outdoor_temp_c', 'inlet_temp_c']
REQUIRED = ['timestamp', 'site_id', 'cooling_type', *NUMERIC, 'ot_event', 'split', 'scenario', 'simulated_anomaly', 'is_simulated']


def load_data(path=None):
    df = pd.read_csv(path or DATA)
    missing = set(REQUIRED) - set(df.columns)
    if missing:
        raise ValueError(f'Faltan columnas: {sorted(missing)}')
    if df[REQUIRED].isna().any().any():
        raise ValueError('No se admiten valores vacíos en columnas requeridas')
    domains = {'site_id': ['SIM-A', 'SIM-B', 'SIM-C'], 'cooling_type': ['aire', 'evaporativa', 'liquida'],
               'ot_event': ['normal', 'login_fallido', 'cambio_config_no_autorizado'],
               'split': ['referencia', 'evaluacion'], 'scenario': ['base', 'ineficiencia', 'fuga_agua', 'evento_ot'],
               'simulated_anomaly': [0, 1]}
    for col, allowed in domains.items():
        if not df[col].isin(allowed).all():
            raise ValueError(f'Valores no admitidos en {col}')
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='raise')
    if df['timestamp'].isna().any():
        raise ValueError('Timestamp vacío')
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors='raise')
        if df[col].isna().any() or not df[col].map(lambda x: float('-inf') < x < float('inf')).all():
            raise ValueError(f'Valores no finitos en {col}')
    if (df['energy_it_kwh'] <= 0).any() or (df['energy_total_kwh'] < df['energy_it_kwh']).any() or (df['water_l'] < 0).any():
        raise ValueError('Energía IT debe ser positiva, total >= IT y agua >= 0')
    if not df['load_pct'].between(0, 100).all():
        raise ValueError('Carga fuera de 0–100%')
    if df.duplicated(['timestamp', 'site_id']).any():
        raise ValueError('Intervalo y sitio duplicados')
    if not df['is_simulated'].astype(str).str.lower().isin(['true', '1']).all():
        raise ValueError('Este kit solo admite datos declarados simulados')
    return df


def flagged(df):
    """Reglas pedagógicas fijas, no alarmas operativas ni modelo entrenado."""
    out = df.copy()
    pue = out['energy_total_kwh'] / out['energy_it_kwh']
    wue = out['water_l'] / out['energy_it_kwh']
    rules = [(pue > 1.6, 'PUE > 1.6'), (wue > 1.5, 'agua > 1.5 L/kWh IT'),
             (out['inlet_temp_c'] > 29, 'entrada > 29 °C'),
             (out['ot_event'] != 'normal', 'evento OT simulado')]
    out['rule_reason'] = ['; '.join(reason for mask, reason in rules if bool(mask.iloc[i])) for i in range(len(out))]
    out['rule_alert'] = out['rule_reason'] != ''
    return out


def metrics(df):
    it = float(df['energy_it_kwh'].sum())
    total = float(df['energy_total_kwh'].sum())
    water = float(df['water_l'].sum())
    return {'pue': total / it if it > 0 else None, 'wue_l_kwh': water / it if it > 0 else None,
            'energy_it_kwh': it, 'energy_total_kwh': total, 'water_l': water,
            'rows': len(df), 'rule_alerts': int(flagged(df)['rule_alert'].sum())}
