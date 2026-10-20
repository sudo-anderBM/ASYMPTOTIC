import unittest
from tools.compare_detectors import run, score

class BenchmarkTests(unittest.TestCase):
    def test_invalid_assumptions(self):
        for value in [float('nan'), float('inf'), -1]:
            with self.assertRaises(ValueError): run(watts=value)
            with self.assertRaises(ValueError): run(carbon=value)
    def test_score_undefined(self):
        s=score([0,0],[0,0]);self.assertIsNone(s['precision']);self.assertIsNone(s['recall'])
    def test_units_and_split(self):
        r=run(watts=30,carbon=300)
        self.assertEqual((r['train_rows'],r['test_rows']),(216,288))
        self.assertAlmostEqual(r['estimated_kwh'],30*r['wall_seconds']/3600000)
        self.assertAlmostEqual(r['estimated_gco2e'],r['estimated_kwh']*300)
