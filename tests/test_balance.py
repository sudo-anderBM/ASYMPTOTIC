import unittest
from fastapi.testclient import TestClient
from stack_b_api_web.main import app


class TestBalance(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.Q = "tipo=fuga&magnitud=0.1&sitio=SIM-B&semilla=1"

    def test_balance_real_cambia_con_dias(self):
        a = self.client.get(f"/api/balance?{self.Q}&dias=7").json()
        b = self.client.get(f"/api/balance?{self.Q}&dias=14").json()
        
        self.assertTrue(a["simulated"])
        self.assertGreater(b["beneficio"]["evitado"], a["beneficio"]["evitado"])
        self.assertGreater(a["beneficio"]["evitado"], 0)
        self.assertLess(a["costo_detector_anual"]["g_co2e"], 0.01)
        self.assertTrue(a["balance_positivo"])

    def test_balance_ineficiencia_da_kwh(self):
        j = self.client.get("/api/balance?tipo=ineficiencia&magnitud=0.2&sitio=SIM-A&semilla=1").json()
        
        self.assertEqual(j["beneficio"]["unidad"], "kWh")
        self.assertGreater(j["beneficio"]["kwh_evitados"], 0)
        self.assertGreater(j["beneficio"]["kg_co2e_evitados"], 0)

    def test_balance_422_con_detail_texto(self):
        for q in [f"{self.Q}&dias=0", f"{self.Q}&watts=5000", f"{self.Q}&factor=3", f"{self.Q}&l_por_kwh=-1",
                  "tipo=fuga", f"{self.Q}&dias=abc"]:
            r = self.client.get(f"/api/balance?{q}")
            
            self.assertEqual(r.status_code, 422)
            self.assertIsInstance(r.json()["detail"], str)


if __name__ == "__main__":
    unittest.main()