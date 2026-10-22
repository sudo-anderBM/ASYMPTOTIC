from fastapi.testclient import TestClient
from stack_b_api_web.main import app

c = TestClient(app)
Q = "tipo=fuga&magnitud=0.1&sitio=SIM-B&semilla=1"


def test_balance_real_cambia_con_dias():
    a = c.get(f"/api/balance?{Q}&dias=7").json()
    b = c.get(f"/api/balance?{Q}&dias=14").json()
    assert a["simulated"] is True
    assert b["beneficio"]["evitado"] > a["beneficio"]["evitado"] > 0
    assert a["costo_detector_anual"]["g_co2e"] < 0.01
    assert a["balance_positivo"] is True


def test_balance_ineficiencia_da_kwh():
    j = c.get("/api/balance?tipo=ineficiencia&magnitud=0.2&sitio=SIM-A&semilla=1").json()
    assert j["beneficio"]["unidad"] == "kWh"
    assert j["beneficio"]["kwh_evitados"] > 0 and j["beneficio"]["kg_co2e_evitados"] > 0


def test_balance_422_con_detail_texto():
    for q in [f"{Q}&dias=0", f"{Q}&watts=5000", f"{Q}&factor=3", f"{Q}&l_por_kwh=-1",
              "tipo=fuga", f"{Q}&dias=abc"]:
        r = c.get(f"/api/balance?{q}")
        assert r.status_code == 422 and isinstance(r.json()["detail"], str)
