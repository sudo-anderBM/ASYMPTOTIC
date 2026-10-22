"""Pruebas del panel educativo. Ejecutar desde la raíz con unittest discover."""
from datetime import timedelta
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common.cifox import load_data, metrics


def formatted(value, digits=2):
    return f"{value:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()
        cls.first = cls.data.timestamp.min().date()
        cls.last = cls.data.timestamp.max().date()

    def app(self):
        return AppTest.from_file(str(ROOT / "stack_a_streamlit" / "app.py"), default_timeout=20).run()

    def assert_metrics_match(self, at, frame):
        self.assertEqual(len(at.exception), 0)
        expected = metrics(frame)
        cards = {item.label: item.value for item in at.metric}
        self.assertEqual(cards["PUE simplificado"], formatted(expected["pue"]))
        self.assertEqual(cards["WUE local simplificado"], formatted(expected["wue_l_kwh"]) + " L/kWh TI")
        self.assertEqual(cards["Registros con alerta por reglas"], str(expected["rule_alerts"]))
        self.assertEqual(cards["Energía TI"], formatted(expected["energy_it_kwh"], 0) + " kWh")
        self.assertEqual(cards["Energía total"], formatted(expected["energy_total_kwh"], 0) + " kWh")
        self.assertEqual(cards["Agua local extraída"], formatted(expected["water_l"], 0) + " L")

    def test_initial_metrics_and_simulation_label(self):
        at = self.app()
        self.assert_metrics_match(at, self.data)
        self.assertTrue(any("DATOS SIMULADOS" in w.value for w in at.warning))
        self.assertEqual(len(at.get("file_uploader")), 0)
        self.assertEqual(len(at.get("vega_lite_chart")), 3)

    def test_all_chart_scales_use_utc(self):
        at = self.app()
        for chart in at.get("vega_lite_chart"):
            spec = json.loads(chart.proto.spec)
            self.assertEqual(spec["encoding"]["x"]["scale"]["type"], "utc")
            self.assertEqual(spec["encoding"]["tooltip"][0]["field"], "hour_label")

    def test_each_cooling_type_and_repeated_reset(self):
        at = self.app()
        types = sorted(self.data.cooling_type.unique().tolist())
        for cooling in types:
            at.multiselect(key="cooling").set_value([cooling]).run()
            self.assert_metrics_match(at, self.data[self.data.cooling_type == cooling])
        at.multiselect(key="cooling").set_value(types).run()
        self.assert_metrics_match(at, self.data)
        at.multiselect(key="cooling").set_value(types).run()
        self.assert_metrics_match(at, self.data)

    def test_single_day_is_inclusive(self):
        at = self.app()
        at.date_input(key="end_date").set_value(self.first).run()
        selected = self.data[self.data.timestamp.dt.date == self.first]
        self.assert_metrics_match(at, selected)
        at.checkbox(key="only_alerts").set_value(False).run()
        self.assertEqual(len(at.dataframe[-1].value), len(selected))
        self.assertEqual(len(at.dataframe[0].value), selected.timestamp.nunique())
        self.assertEqual(selected.timestamp.dt.hour.max(), 23)

    def test_combined_filters(self):
        at = self.app()
        start = self.first + timedelta(days=1)
        end = self.last - timedelta(days=1)
        cooling = sorted(self.data.cooling_type.unique().tolist())[0]
        at.multiselect(key="cooling").set_value([cooling])
        at.date_input(key="start_date").set_value(start)
        at.date_input(key="end_date").set_value(end).run()
        selected = self.data[(self.data.cooling_type == cooling) & self.data.timestamp.dt.date.between(start, end)]
        self.assert_metrics_match(at, selected)

    def test_no_cooling_selected_and_recovery(self):
        at = self.app()
        at.multiselect(key="cooling").set_value([]).run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.metric), 0)
        self.assertTrue(any("No hay datos" in i.value for i in at.info))
        at.multiselect(key="cooling").set_value(sorted(self.data.cooling_type.unique().tolist())).run()
        self.assert_metrics_match(at, self.data)

    def test_reversed_dates_and_recovery(self):
        at = self.app()
        at.date_input(key="start_date").set_value(self.last)
        at.date_input(key="end_date").set_value(self.first).run()
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(any("fecha inicial" in e.value for e in at.error))
        self.assertEqual(len(at.metric), 0)
        at.date_input(key="start_date").set_value(self.first)
        at.date_input(key="end_date").set_value(self.last).run()
        self.assert_metrics_match(at, self.data)

    def test_alert_toggle_preserves_metrics(self):
        at = self.app()
        self.assertEqual(len(at.dataframe[-1].value), metrics(self.data)["rule_alerts"])
        for selected in [False, True, False]:
            at.checkbox(key="only_alerts").set_value(selected).run()
            self.assert_metrics_match(at, self.data)
            expected = metrics(self.data)["rule_alerts"] if selected else len(self.data)
            self.assertEqual(len(at.dataframe[-1].value), expected)

    def test_missing_csv_has_clear_error(self):
        with patch("common.cifox.load_data", side_effect=FileNotFoundError("CSV no encontrado")):
            at = self.app()
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(any("No se pudo leer" in e.value for e in at.error))
        self.assertEqual(len(at.metric), 0)

    def test_empty_csv_has_clear_message(self):
        with patch("common.cifox.load_data", return_value=self.data.iloc[:0].copy()):
            at = self.app()
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(any("no contiene filas" in i.value for i in at.info))
        self.assertEqual(len(at.metric), 0)


if __name__ == "__main__":
    unittest.main()
