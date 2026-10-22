import unittest
from greenai.sweep import _punto, _bloque, MAGS


class TestSweep(unittest.TestCase):
    def test_punto_y_bloque_forma_y_rangos(self):
        acc = _punto("fuga", False, 2)
        costo = {k: (1.0, 1.0, 0.1, 0.1) for k in acc}   # mediana fit, pred y desviaciones
        b = _bloque(acc, costo)
        
        self.assertEqual(len(b), 5)
        for d in b:
            self.assertEqual(len(d["deteccion"]), len(MAGS))
            self.assertEqual(len(MAGS), len(d["deteccion_ic95"]))
            self.assertTrue(all(0 <= x <= 1 for x in d["deteccion"]))
            
        r = {d["id"]: d for d in b}
        self.assertEqual(r["3_residual_3sigma"]["deteccion"][-1], 1.0)     # fuga del 100 %
        self.assertEqual(r["1_reglas"]["deteccion"][1], 0.0)               # fuga del 10 %


if __name__ == "__main__":
    unittest.main()