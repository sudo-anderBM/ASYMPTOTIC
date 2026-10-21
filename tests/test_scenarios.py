import pytest
from greenai.base_data import generar_base
from greenai.scenarios import inyectar, SITIOS


def test_magnitud_cero_no_cambia_nada():
    df = generar_base(1)
    for tipo in ("fuga", "ineficiencia"):
        mod, _ = inyectar(df, tipo, 0.0, SITIOS, 1)
        assert mod.equals(df)


def test_misma_semilla_igual_y_distinta_cambia():
    df = generar_base(1)
    _, a = inyectar(df, "fuga", 0.1, ["SIM-A"], 5)
    _, b = inyectar(df, "fuga", 0.1, ["SIM-A"], 5)
    _, c = inyectar(df, "fuga", 0.1, ["SIM-A"], 6)
    assert a == b and a != c


def test_no_toca_referencia_ni_original():
    df = generar_base(1)
    copia = df.copy()
    mod, _ = inyectar(df, "fuga", 0.5, SITIOS, 2)
    assert df.equals(copia)
    ref = df.split == "referencia"
    assert mod[ref].equals(df[ref])


def test_tres_ventanas_de_6h_sin_encimarse_y_valor_exacto():
    df = generar_base(1)
    mod, ev = inyectar(df, "fuga", 0.2, ["SIM-B"], 3)
    assert len(ev) == 3
    todas = [f for e in ev for f in e["filas"]]
    assert len(todas) == 18 and len(set(todas)) == 18
    assert all(len(e["filas"]) == 6 for e in ev)
    for f in todas:
        assert mod.loc[f, "water_l"] == pytest.approx(df.loc[f, "water_l"] * 1.2)
    otras = df.index.difference(todas)
    assert mod.loc[otras, "water_l"].equals(df.loc[otras, "water_l"])


def test_ineficiencia_solo_sube_la_parte_no_it():
    df = generar_base(1)
    mod, ev = inyectar(df, "ineficiencia", 0.5, ["SIM-A"], 1)
    f = ev[0]["filas"][0]
    extra = df.loc[f, "energy_total_kwh"] - df.loc[f, "energy_it_kwh"]
    assert mod.loc[f, "energy_total_kwh"] == pytest.approx(df.loc[f, "energy_it_kwh"] + extra * 1.5)
    assert mod.loc[f, "energy_it_kwh"] == df.loc[f, "energy_it_kwh"]


def test_ventanas_de_un_sitio_iguales_solo_o_con_todos():
    df = generar_base(1)
    _, solo = inyectar(df, "fuga", 0.1, ["SIM-C"], 4)
    _, todos = inyectar(df, "fuga", 0.1, SITIOS, 4)
    assert solo == [e for e in todos if e["sitio"] == "SIM-C"]


def test_entrada_invalida():
    df = generar_base(1)
    with pytest.raises(ValueError):
        inyectar(df, "otro", 0.1, SITIOS, 1)
    with pytest.raises(ValueError):
        inyectar(df, "fuga", 1.5, SITIOS, 1)