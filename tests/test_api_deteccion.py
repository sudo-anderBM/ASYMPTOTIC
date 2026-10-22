import unittest
from fastapi.testclient import TestClient
from stack_b_api_web.main import app


class TestApiDeteccion(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.P = "tipo=fuga&magnitud=0.1&sitio=SIM-A&semilla=1"

    def test_detectors(self):
        r = self.client.get("/api/detectors")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["detectores"]), 5)

    def test_scenario_contrato_y_resultado(self):
        r = self.client.get(f"/api/scenario?{self.P}")
        self.assertEqual(r.status_code, 200)
        j = r.json()
        
        self.assertTrue(j["simulated"])
        self.assertEqual(j["variable"], "water_l")
        self.assertEqual(len(j["serie"]), 96)
        self.assertEqual(len(j["eventos_reales"]), 3)
        self.assertEqual(len(j["detectores"]), 5)
        
        d = {x["id"]: x for x in j["detectores"]}
        self.assertEqual(d["1_reglas"]["eventos_detectados"], 0)
        self.assertEqual(d["3_residual_3sigma"]["eventos_detectados"], 3)

    def test_explain(self):
        j = self.client.get(f"/api/scenario?{self.P}").json()
        ts = j["eventos_reales"][0]["inicio"]
        r = self.client.get(f"/api/explain?{self.P}&timestamp={ts}")
        
        self.assertEqual(r.status_code, 200)
        self.assertIn("por encima", r.json()["texto"])

    def test_errores_422_con_detail_texto(self):
        for q in ["tipo=otro&magnitud=0.1&sitio=SIM-A&semilla=1",
                  "tipo=fuga&magnitud=2&sitio=SIM-A&semilla=1",
                  "tipo=fuga&magnitud=0.1&sitio=SIM-Z&semilla=1",
                  "tipo=fuga&magnitud=0.1&sitio=SIM-A&semilla=0",
                  "tipo=fuga"]:
            r = self.client.get(f"/api/scenario?{q}")
            self.assertEqual(r.status_code, 422)
            self.assertIsInstance(r.json()["detail"], str)

    def test_sweep_sin_archivo_o_con_archivo(self):
        r1 = self.client.get("/api/sweep?tipo=fuga")
        self.assertIn(r1.status_code, (200, 503))
        
        r2 = self.client.get("/api/sweep?tipo=x")
        self.assertEqual(r2.status_code, 422)

    def test_magnitud_cero_sin_eventos(self):
        j = self.client.get("/api/scenario?tipo=fuga&magnitud=0&sitio=SIM-A&semilla=1").json()
        self.assertEqual(j["eventos_reales"], [])
        self.assertTrue(all(d["eventos_totales"] == 0 for d in j["detectores"]))

    def _m(self, q):
        return self.client.get(f"/api/scenario?{q}").json()["metricas"]

    def test_metricas_cero_iguales(self):
        m = self._m("tipo=fuga&magnitud=0&sitio=SIM-B&semilla=1")
        self.assertEqual(m["sin_problema"], m["con_problema"])

    def test_metricas_fuga_sube_wue(self):
        m = self._m("tipo=fuga&magnitud=0.5&sitio=SIM-B&semilla=1")
        self.assertGreater(m["con_problema"]["wue_l_kwh"], m["sin_problema"]["wue_l_kwh"])

    def test_metricas_ineficiencia_sube_pue(self):
        m = self._m("tipo=ineficiencia&magnitud=0.5&sitio=SIM-A&semilla=1")
        self.assertGreater(m["con_problema"]["pue"], m["sin_problema"]["pue"])


if __name__ == "__main__":
    unittest.main()