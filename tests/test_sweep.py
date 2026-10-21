from greenai.sweep import _punto, _bloque, MAGS


def test_punto_y_bloque_forma_y_rangos():
    acc = _punto("fuga", False, 2)
    costo = {k: (1.0, 1.0) for k in acc}
    b = _bloque(acc, costo)
    assert len(b) == 5
    for d in b:
        assert len(d["deteccion"]) == len(MAGS) == len(d["deteccion_ic95"])
        assert all(0 <= x <= 1 for x in d["deteccion"])
    r = {d["id"]: d for d in b}
    assert r["3_residual_3sigma"]["deteccion"][-1] == 1.0     # fuga del 100 %
    assert r["1_reglas"]["deteccion"][1] == 0.0               # fuga del 10 %
