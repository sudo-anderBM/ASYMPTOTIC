import tempfile
import unittest
from pathlib import Path
import pandas as pd
from common.cifox import load_data, metrics, flagged, DATA
from tools.generate_data import generate

class CommonTests(unittest.TestCase):
    def test_reproducible(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'generated.csv'; generate(p)
            self.assertEqual(p.read_bytes(),DATA.read_bytes())
    def test_shape_split_labels(self):
        d=load_data(); self.assertEqual(len(d),504)
        self.assertEqual((d.split=='referencia').sum(),216)
        self.assertEqual((d.split=='evaluacion').sum(),288)
        self.assertEqual(d.simulated_anomaly.sum(),21)
        self.assertEqual(d[d.split=='referencia'].simulated_anomaly.sum(),0)
    def test_weighted_metrics(self):
        d=load_data().iloc[:2].copy();d['energy_it_kwh']=[10,30];d['energy_total_kwh']=[20,33];d['water_l']=[10,60]
        m=metrics(d);self.assertAlmostEqual(m['pue'],53/40);self.assertAlmostEqual(m['wue_l_kwh'],70/40)
        self.assertNotEqual(m['pue'],(2+1.1)/2)
    def test_empty(self):
        m=metrics(load_data().iloc[:0]); self.assertIsNone(m['pue']);self.assertIsNone(m['wue_l_kwh']);self.assertEqual(m['rule_alerts'],0)
    def test_flags_without_ground_truth(self):
        d=load_data();a=flagged(d);d['simulated_anomaly']=1-d.simulated_anomaly
        self.assertEqual(list(a.rule_alert),list(flagged(d).rule_alert))
        self.assertEqual(a.rule_alert.sum(),21)
    def test_reject_bad_energy(self):
        d=load_data();d.loc[0,'energy_it_kwh']=0
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bad.csv';d.to_csv(p,index=False)
            with self.assertRaises(ValueError): load_data(p)
    def test_reject_missing_timestamp(self):
        d=load_data();d.loc[0,'timestamp']=pd.NaT
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bad.csv';d.to_csv(p,index=False)
            with self.assertRaises(ValueError): load_data(p)
    def test_reject_invalid_split(self):
        d=load_data();d.loc[0,'split']='other'
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bad.csv';d.to_csv(p,index=False)
            with self.assertRaises(ValueError): load_data(p)
    def test_reject_not_simulated(self):
        d=load_data();d.loc[0,'is_simulated']=False
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bad.csv';d.to_csv(p,index=False)
            with self.assertRaises(ValueError): load_data(p)

if __name__=='__main__': unittest.main()
