from fastapi.testclient import TestClient
from stack_b_api_web.main import app

c = TestClient(app)
P = "tipo=fuga&magnitud=0.1&sitio=SIM-A&semilla=1"


def test_detectors():
    r = c.get("/api/detectors")
    assert r.status_code == 200 and len(r.json()["detectores"]) == 5


def test_scenario_contrato_y_resultado():
    r = c.get(f"/api/scenario?{P}")
    assert r.status_code == 200
    j = r.json()
    assert j["simulated"] is True and j["variable"] == "water_l" and len(j["serie"]) == 96
    assert len(j["eventos_reales"]) == 3 and len(j["detectores"]) == 5
    d = {x["id"]: x for x in j["detectores"]}
    assert d["1_reglas"]["eventos_detectados"] == 0
    assert d["3_residual_3sigma"]["eventos_detectados"] == 3


def test_explain():
    j = c.get(f"/api/scenario?{P}").json()
    ts = j["eventos_reales"][0]["inicio"]
    r = c.get(f"/api/explain?{P}&timestamp={ts}")
    assert r.status_code == 200 and "por encima" in r.json()["texto"]


def test_errores_422_con_detail_texto():
    for q in ["tipo=otro&magnitud=0.1&sitio=SIM-A&semilla=1",
              "tipo=fuga&magnitud=2&sitio=SIM-A&semilla=1",
              "tipo=fuga&magnitud=0.1&sitio=SIM-Z&semilla=1",
              "tipo=fuga&magnitud=0.1&sitio=SIM-A&semilla=0",
              "tipo=fuga"]:
        r = c.get(f"/api/scenario?{q}")
        assert r.status_code == 422 and isinstance(r.json()["detail"], str)


def test_sweep_sin_archivo_o_con_archivo():
    assert c.get("/api/sweep?tipo=fuga").status_code in (200, 503)
    assert c.get("/api/sweep?tipo=x").status_code == 422


def test_magnitud_cero_sin_eventos():
    j = c.get("/api/scenario?tipo=fuga&magnitud=0&sitio=SIM-A&semilla=1").json()
    assert j["eventos_reales"] == []
    assert all(d["eventos_totales"] == 0 for d in j["detectores"])


def _m(q):
    return c.get(f"/api/scenario?{q}").json()["metricas"]


def test_metricas_cero_iguales():
    m = _m("tipo=fuga&magnitud=0&sitio=SIM-B&semilla=1")
    assert m["sin_problema"] == m["con_problema"]


def test_metricas_fuga_sube_wue():
    m = _m("tipo=fuga&magnitud=0.5&sitio=SIM-B&semilla=1")
    assert m["con_problema"]["wue_l_kwh"] > m["sin_problema"]["wue_l_kwh"]


def test_metricas_ineficiencia_sube_pue():
    m = _m("tipo=ineficiencia&magnitud=0.5&sitio=SIM-A&semilla=1")
    assert m["con_problema"]["pue"] > m["sin_problema"]["pue"]    