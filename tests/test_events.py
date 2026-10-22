import unittest
import numpy as np
import pandas as pd
from greenai.events import evaluar

def _df(valores, base):
    t = pd.date_range("2026-10-15", periods=10, freq="h", tz="UTC")
    mod = pd.DataFrame({"site_id": "SIM-A", "timestamp": t, "water_l": valores})
    bas = pd.DataFrame({"site_id": "SIM-A", "timestamp": t, "water_l": base})
    return mod, bas

EV = [dict(sitio="SIM-A", inicio=None, fin=None, filas=[4, 5, 6])]

class TestEvents(unittest.TestCase):
    def test_detecta_en_segunda_hora_de_la_ventana(self):
        base = [10.0] * 10
        mod, bas = _df([10, 10, 10, 10, 12, 12, 12, 10, 10, 10], base)
        pred = np.zeros(10, bool)
        pred[[5, 8]] = True       # 5 dentro, 8 fuera
        r = evaluar(pred, mod, bas, EV, "SIM-A", "water_l")
        
        self.assertEqual(r["eventos_detectados"], 1)
        self.assertEqual(r["eventos_totales"], 1)
        self.assertEqual(r["horas_hasta_alerta"], 1.0)
        self.assertAlmostEqual(r["falsas_alarmas_dia"], 1 / 4)
        self.assertAlmostEqual(r["exceso_no_detectado"], 2.0)   # solo la hora 4
        self.assertEqual(len(r["alertas"]), 2)

    def test_no_detectado_exceso_es_toda_la_ventana(self):
        mod, bas = _df([10, 10, 10, 10, 12, 12, 12, 10, 10, 10], [10.0] * 10)
        r = evaluar(np.zeros(10, bool), mod, bas, EV, "SIM-A", "water_l")
        
        self.assertEqual(r["eventos_detectados"], 0)
        self.assertIsNone(r["horas_hasta_alerta"])
        self.assertEqual(r["falsas_alarmas_dia"], 0.0)
        self.assertAlmostEqual(r["exceso_no_detectado"], 6.0)

    def test_alerta_en_primera_hora_exceso_cero(self):
        mod, bas = _df([10, 10, 10, 10, 12, 12, 12, 10, 10, 10], [10.0] * 10)
        pred = np.zeros(10, bool)
        pred[4] = True
        r = evaluar(pred, mod, bas, EV, "SIM-A", "water_l")
        
        self.assertEqual(r["horas_hasta_alerta"], 0.0)
        self.assertEqual(r["exceso_no_detectado"], 0.0)

    def test_largo_distinto_falla(self):
        mod, bas = _df([1.0] * 10, [1.0] * 10)
        with self.assertRaises(ValueError):
            evaluar(np.zeros(5, bool), mod, bas, EV, "SIM-A", "water_l")

if __name__ == "__main__":
    unittest.main()