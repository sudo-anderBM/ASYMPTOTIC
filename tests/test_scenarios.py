import unittest
from greenai.base_data import generar_base
from greenai.scenarios import inyectar, SITIOS


class TestScenarios(unittest.TestCase):
    def test_magnitud_cero_no_cambia_nada(self):
        df = generar_base(1)
        for tipo in ("fuga", "ineficiencia"):
            mod, _ = inyectar(df, tipo, 0.0, SITIOS, 1)
            self.assertTrue(mod.equals(df))

    def test_misma_semilla_igual_y_distinta_cambia(self):
        df = generar_base(1)
        _, a = inyectar(df, "fuga", 0.1, ["SIM-A"], 5)
        _, b = inyectar(df, "fuga", 0.1, ["SIM-A"], 5)
        _, c = inyectar(df, "fuga", 0.1, ["SIM-A"], 6)
        
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_no_toca_referencia_ni_original(self):
        df = generar_base(1)
        copia = df.copy()
        mod, _ = inyectar(df, "fuga", 0.5, SITIOS, 2)
        
        self.assertTrue(df.equals(copia))
        ref = df.split == "referencia"
        self.assertTrue(mod[ref].equals(df[ref]))

    def test_tres_ventanas_de_6h_sin_encimarse_y_valor_exacto(self):
        df = generar_base(1)
        mod, ev = inyectar(df, "fuga", 0.2, ["SIM-B"], 3)
        
        self.assertEqual(len(ev), 3)
        todas = [f for e in ev for f in e["filas"]]
        self.assertEqual(len(todas), 18)
        self.assertEqual(len(set(todas)), 18)
        self.assertTrue(all(len(e["filas"]) == 6 for e in ev))
        
        for f in todas:
            self.assertAlmostEqual(mod.loc[f, "water_l"], df.loc[f, "water_l"] * 1.2)
            
        otras = df.index.difference(todas)
        self.assertTrue(mod.loc[otras, "water_l"].equals(df.loc[otras, "water_l"]))

    def test_ineficiencia_solo_sube_la_parte_no_it(self):
        df = generar_base(1)
        mod, ev = inyectar(df, "ineficiencia", 0.5, ["SIM-A"], 1)
        f = ev[0]["filas"][0]
        extra = df.loc[f, "energy_total_kwh"] - df.loc[f, "energy_it_kwh"]
        
        self.assertAlmostEqual(mod.loc[f, "energy_total_kwh"], df.loc[f, "energy_it_kwh"] + extra * 1.5)
        self.assertEqual(mod.loc[f, "energy_it_kwh"], df.loc[f, "energy_it_kwh"])

    def test_ventanas_de_un_sitio_iguales_solo_o_con_todos(self):
        df = generar_base(1)
        _, solo = inyectar(df, "fuga", 0.1, ["SIM-C"], 4)
        _, todos = inyectar(df, "fuga", 0.1, SITIOS, 4)
        
        self.assertEqual(solo, [e for e in todos if e["sitio"] == "SIM-C"])

    def test_entrada_invalida(self):
        df = generar_base(1)
        with self.assertRaises(ValueError):
            inyectar(df, "otro", 0.1, SITIOS, 1)
        with self.assertRaises(ValueError):
            inyectar(df, "fuga", 1.5, SITIOS, 1)


if __name__ == "__main__":
    unittest.main()