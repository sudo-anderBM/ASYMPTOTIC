"""Ejecutar desde la raíz: python -m unittest discover -s stack_b_api_web/tests -v"""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from common.cifox import load_data, metrics
from stack_b_api_web.main import app


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.data = load_data()

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_health_checks_data(self):
        for path in ("/health", "/api/health"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], "ok")
                self.assertTrue(response.json()["simulated"])
                self.assertTrue(response.json()["read_only"])
                self.assertEqual(response.json()["rows"], len(self.data))

    def test_metrics_match_shared_calculations(self):
        response = self.client.get("/api/metrics")
        self.assertEqual(response.status_code, 200)
        result = response.json()
        expected = metrics(self.data)
        for key, value in expected.items():
            with self.subTest(metric=key):
                self.assertAlmostEqual(result[key], value)
        self.assertTrue(result["simulated"])
        self.assertTrue(result["read_only"])
        self.assertIn("site_id", result["filters"])
        self.assertTrue(result["period_start"].endswith("+00:00"))

    def test_default_limit_and_newest_first(self):
        result = self.client.get("/api/records").json()
        self.assertEqual(result["returned"], min(100, len(self.data)))
        self.assertEqual(result["total"], len(self.data))
        records = result["records"]
        self.assertIn("rule_alert", records[0])
        self.assertIn("rule_reason", records[0])
        dates = [record["timestamp"] for record in records]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_explicit_limit_and_hard_cap(self):
        self.assertEqual(self.client.get("/api/records?limit=7").json()["returned"], 7)
        self.assertEqual(self.client.get("/api/records?limit=1000").status_code, 200)
        for limit in (0, -1, 1001, "invalid"):
            with self.subTest(limit=limit):
                self.assertEqual(self.client.get(f"/api/records?limit={limit}").status_code, 422)

    def test_all_filters_match_data(self):
        for column in ("site_id", "cooling_type", "split"):
            for value in self.data[column].unique():
                with self.subTest(column=column, value=value):
                    subset = self.data.loc[self.data[column] == value]
                    result = self.client.get("/api/metrics", params={column: value}).json()
                    self.assertEqual(result["rows"], len(subset))
                    self.assertAlmostEqual(result["pue"], metrics(subset)["pue"])
                    records = self.client.get("/api/records", params={column: value, "limit": 1000}).json()
                    self.assertTrue(all(row[column] == value for row in records["records"]))

    def test_invalid_filter_is_rejected(self):
        for path in ("/api/metrics", "/api/records"):
            response = self.client.get(path, params={"site_id": "no-existe"})
            self.assertEqual(response.status_code, 422)
            self.assertIn("Filtro no válido", response.json()["detail"])

    def test_valid_but_empty_combination(self):
        site = self.data.iloc[0]["site_id"]
        existing_cooling = self.data.loc[self.data["site_id"] == site, "cooling_type"].unique()
        other = next(value for value in self.data["cooling_type"].unique() if value not in existing_cooling)
        params = {"site_id": site, "cooling_type": other}
        result = self.client.get("/api/metrics", params=params).json()
        self.assertEqual(result["rows"], 0)
        self.assertIsNone(result["pue"])
        self.assertIsNone(result["wue_l_kwh"])
        self.assertEqual(self.client.get("/api/records", params=params).json()["records"], [])

    def test_alerts_only(self):
        result = self.client.get("/api/records?alerts_only=true&limit=1000").json()
        self.assertGreater(result["returned"], 0)
        self.assertTrue(all(row["rule_alert"] and row["rule_reason"] for row in result["records"]))
        self.assertEqual(result["total"], metrics(self.data)["rule_alerts"])

    def test_ui_and_assets_are_local(self):
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn('lang="es"', home.text)
        self.assertIn("DATOS SIMULADOS", home.text)
        self.assertIn('src="/static/app.js"', home.text)
        self.assertNotIn("https://", home.text)
        for path in ("/static/app.js", "/static/style.css", "/static/favicon.svg"):
            self.assertEqual(self.client.get(path).status_code, 200)
        self.assertEqual(home.headers["x-content-type-options"], "nosniff")
        self.assertIn("connect-src 'self'", home.headers["content-security-policy"])

    def test_no_write_routes(self):
        for method in ("post", "put", "patch", "delete"):
            for path in ("/api/metrics", "/api/records"):
                with self.subTest(method=method, path=path):
                    self.assertEqual(getattr(self.client, method)(path).status_code, 405)
        self.assertEqual(self.client.get("/docs").status_code, 404)
        self.assertEqual(self.client.get("/openapi.json").status_code, 200)

    def test_missing_or_invalid_data_is_reported(self):
        for error in (FileNotFoundError("missing"), ValueError("invalid")):
            with self.subTest(error=error):
                with patch("stack_b_api_web.main.load_data", side_effect=error):
                    for path in ("/health", "/api/metrics", "/api/records"):
                        response = self.client.get(path)
                        self.assertEqual(response.status_code, 503)
                        self.assertIn("datos de ejemplo", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
