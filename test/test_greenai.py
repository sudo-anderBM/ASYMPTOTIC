from common.cifox import load_data, flagged, metrics
from greenai.detectors import ALL, RulesVec

LABELS = ["scenario", "simulated_anomaly"]


def _split():
    X = load_data().drop(columns=LABELS)
    return X[X.split == "referencia"], X[X.split == "evaluacion"]


def test_reglas_vectorizadas_igual_al_kit():
    df = load_data()
    te = df[df.split == "evaluacion"]
    mia = RulesVec(True).predict(te.drop(columns=LABELS))
    assert mia.tolist() == flagged(te).rule_alert.tolist()


def test_detectores_corren_sin_etiquetas_y_con_ambas_configs():
    tr, te = _split()
    for cls in ALL:
        for ot in (True, False):
            p = cls(ot).fit(tr).predict(te)
            assert p.dtype == bool and len(p) == len(te)


def test_pue_es_cociente_de_sumas():
    df = load_data()
    m = metrics(df)
    assert abs(m["pue"] - df.energy_total_kwh.sum() / df.energy_it_kwh.sum()) < 1e-9