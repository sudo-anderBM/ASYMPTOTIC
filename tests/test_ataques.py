"""Ataques de falsificación (greenai/ataques.py). Ejecutar: python -m unittest tests.test_ataques -v"""
import json
import unittest

from greenai import ataques
from greenai.base_data import generar_base


class AtaquesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = ataques.evaluar(semillas=[1, 2])

    def test_ataque_solo_cambia_su_ventana(self):
        ev = generar_base(1).query("split == 'evaluacion'")
        for tipo in ("fijo", "deriva", "replay", "coherente"):
            with self.subTest(tipo=tipo):
                atacado, ventana = ataques.atacar(ev, tipo, "SIM-B", 30)
                self.assertEqual(int(ventana.sum()), ataques.DURACION)
                cambio = (atacado[ataques.COLUMNAS] != ev[ataques.COLUMNAS]).any(axis=1)
                self.assertFalse(cambio[~ventana].any())
                self.assertTrue(cambio[ventana].any())

    def test_residual_detecta_falsificaciones_de_una_columna(self):
        azar = self.r["tasa"]["sin_ataque"]["Residual 3σ"]
        for tipo in ("fijo", "deriva", "replay"):
            with self.subTest(tipo=tipo):
                self.assertGreaterEqual(self.r["tasa"][tipo]["Residual 3σ"], 0.9)
        self.assertLessEqual(azar, 0.2)

    def test_limite_replay_coherente_no_se_detecta(self):
        # Límite documentado: la fila completa repetida conserva la física.
        self.assertLessEqual(self.r["tasa"]["coherente"]["Residual 3σ"], 0.2)

    def test_resultado_publicado_tiene_la_forma_esperada(self):
        r = json.loads((ataques.RES / "ataques.json").read_text(encoding="utf-8"))
        self.assertTrue(r["simulated"])
        self.assertEqual(r["ventanas_por_celda"], 60)
        self.assertEqual(set(r["tasa"]), set(ataques.ATAQUES))


if __name__ == "__main__":
    unittest.main()
