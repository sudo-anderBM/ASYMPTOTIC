import pytest
from greenai.base_data import generar_base
from greenai.scenarios import inyectar
from greenai.detectors import ResidualSigma
from greenai.explain import explicar


def _setup():
    base = generar_base(1)
    mod, ev = inyectar(base, "fuga", 0.1, ["SIM-A"], 1)
    det = ResidualSigma(False).fit(base[base.split == "referencia"])
    return base, mod, ev, det


def test_esperado_cerca_del_observado_en_datos_limpios():
    base, _, _, det = _setup()
    ev = base[base.split == "evaluacion"]
    esp = det.esperado(ev, "water_l")
    rel = abs(esp - ev["water_l"].to_numpy()) / ev["water_l"].to_numpy()
    assert rel.max() < 0.08


def test_explicar_fuga_10_por_ciento():
    base, mod, ev, det = _setup()
    f = ev[0]["filas"][0]
    r = explicar(mod, det, "SIM-A", mod.loc[f, "timestamp"], "water_l")
    assert r["simulated"] is True and r["unidad"] == "L"
    assert 8 < r["desviacion_pct"] < 13
    assert "por encima" in r["texto"]
    assert r["z"] > 3


def test_timestamp_invalido():
    _, mod, _, det = _setup()
    with pytest.raises(ValueError):
        explicar(mod, det, "SIM-A", "2020-01-01T00:00:00Z", "water_l")
