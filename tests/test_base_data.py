import unittest
import pandas as pd
from common.cifox import load_data, metrics
from greenai.base_data import generar_base, SEED_KIT


class TestBaseData(unittest.TestCase):
    def test_504_filas_y_split(self):
        df = generar_base(1)
        self.assertEqual(len(df), 504)
        self.assertEqual((df.split == "referencia").sum(), 216)
        self.assertTrue((df.ot_event == "normal").all())

    def test_misma_semilla_mismo_resultado(self):
        pd.testing.assert_frame_equal(generar_base(7), generar_base(7))
        self.assertFalse(generar_base(7).equals(generar_base(8)))

    def test_reproduce_el_kit_en_filas_sin_anomalia(self):
        kit = load_data().sort_values(["site_id", "timestamp"]).reset_index(drop=True)
        mia = generar_base(SEED_KIT)
        limpias = (kit.scenario == "base").to_numpy()
        for col in ["energy_it_kwh", "energy_total_kwh", "water_l", "load_pct",
                    "outdoor_temp_c", "inlet_temp_c"]:
            diff = (kit.loc[limpias, col] - mia.loc[limpias, col]).abs().max()
            self.assertLess(diff, 1e-6, col)

    def test_pue_parecido_al_del_kit(self):
        kit = metrics(load_data())["pue"]
        self.assertLess(abs(metrics(generar_base(SEED_KIT))["pue"] - kit), 0.02)

    def test_dificil_cambia_solo_el_agua(self):
        n, d = generar_base(3), generar_base(3, dificil=True)
        self.assertTrue((n.energy_total_kwh == d.energy_total_kwh).all())
        self.assertTrue((n.load_pct == d.load_pct).all())
        self.assertFalse((n.water_l == d.water_l).all())


if __name__ == "__main__":
    unittest.main()