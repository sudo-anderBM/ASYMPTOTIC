"""Cinco detectores comparables. fit() solo con 'referencia'; sin etiquetas."""
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from common.cifox import NUMERIC

TARGETS = {
    "energy_total_kwh": ["energy_it_kwh", "load_pct", "outdoor_temp_c"],
    "water_l": ["energy_it_kwh", "load_pct", "outdoor_temp_c"],
    "inlet_temp_c": ["load_pct", "outdoor_temp_c"],
}


class Detector:
    name = "base"

    def __init__(self, use_ot=True):
        self.use_ot = use_ot

    def _ot(self, df):
        if not self.use_ot:
            return np.zeros(len(df), dtype=bool)
        return (df["ot_event"] != "normal").to_numpy()

    def fit(self, train):
        return self

    def predict(self, test):
        raise NotImplementedError


class RulesVec(Detector):
    """Mismas reglas del kit (PUE>1.6, WUE>1.5, entrada>29), vectorizadas."""
    name = "1_reglas"

    def predict(self, test):
        pue = test["energy_total_kwh"] / test["energy_it_kwh"]
        wue = test["water_l"] / test["energy_it_kwh"]
        a = (pue > 1.6) | (wue > 1.5) | (test["inlet_temp_c"] > 29)
        return a.to_numpy() | self._ot(test)


class IForest(Detector):
    """Igual que el kit (100 arboles, contamination .05); OT opcional."""
    name = "2_isolation_forest"

    def _X(self, df):
        X = df[NUMERIC].to_numpy(float)
        if self.use_ot:
            X = np.column_stack([X, self._ot(df).astype(float)])
        return X

    def fit(self, train):
        self.model = make_pipeline(
            StandardScaler(),
            IsolationForest(n_estimators=100, contamination=0.05,
                            random_state=22102026, n_jobs=1))
        self.model.fit(self._X(train))
        return self

    def predict(self, test):
        return self.model.predict(self._X(test)) == -1


class _Residual(Detector):
    """Regresion lineal por sitio y variable, ajustada en referencia."""

    def fit(self, train):
        self.beta, self.sigma = {}, {}
        for site, g in train.groupby("site_id"):
            for tgt, feats in TARGETS.items():
                A = np.column_stack([np.ones(len(g)), g[feats].to_numpy(float)])
                y = g[tgt].to_numpy(float)
                b, *_ = np.linalg.lstsq(A, y, rcond=None)
                r = y - A @ b
                dof = max(len(g) - A.shape[1], 1)
                self.beta[(site, tgt)] = b
                self.sigma[(site, tgt)] = max(np.sqrt((r ** 2).sum() / dof), 1e-9)
        return self

    def _z(self, df):
        z = np.zeros((len(df), len(TARGETS)))
        for site in df["site_id"].unique():
            mask = (df["site_id"] == site).to_numpy()
            g = df[mask]
            for j, (tgt, feats) in enumerate(TARGETS.items()):
                A = np.column_stack([np.ones(len(g)), g[feats].to_numpy(float)])
                r = g[tgt].to_numpy(float) - A @ self.beta[(site, tgt)]
                z[mask, j] = r / self.sigma[(site, tgt)]
        return z


class ResidualSigma(_Residual):
    name = "3_residual_3sigma"

    def predict(self, test):
        return (np.abs(self._z(test)) > 3).any(axis=1) | self._ot(test)


class ResidualCusum(_Residual):
    name = "4_residual_cusum"

    def __init__(self, use_ot=True, k=0.5, h=5.0):
        super().__init__(use_ot)
        self.k, self.h = k, h

    def predict(self, test):
        z = self._z(test)
        alarm = np.zeros(z.shape, dtype=bool)
        for site in test["site_id"].unique():
            pos = np.flatnonzero((test["site_id"] == site).to_numpy())
            order = test.iloc[pos]["timestamp"].argsort().to_numpy()
            pos = pos[order]
            for j in range(z.shape[1]):
                sp = sn = 0.0
                for i in pos:
                    sp = max(0.0, sp + z[i, j] - self.k)
                    sn = max(0.0, sn - z[i, j] - self.k)
                    if sp > self.h or sn > self.h:
                        alarm[i, j] = True
                        sp = sn = 0.0
        return alarm.any(axis=1) | self._ot(test)


class ZRules(Detector):
    """z-score simple de PUE, WUE y entrada por sitio (barato)."""
    name = "5_zscore_simple"

    def _feats(self, df):
        return np.column_stack([df["energy_total_kwh"] / df["energy_it_kwh"],
                                df["water_l"] / df["energy_it_kwh"],
                                df["inlet_temp_c"]])

    def fit(self, train):
        self.mu, self.sd = {}, {}
        for site, g in train.groupby("site_id"):
            F = self._feats(g)
            self.mu[site] = F.mean(axis=0)
            self.sd[site] = np.maximum(F.std(axis=0, ddof=1), 1e-9)
        return self

    def predict(self, test):
        F = self._feats(test)
        z = np.zeros_like(F)
        for site in test["site_id"].unique():
            m = (test["site_id"] == site).to_numpy()
            z[m] = (F[m] - self.mu[site]) / self.sd[site]
        return (np.abs(z) > 3).any(axis=1) | self._ot(test)


ALL = [RulesVec, IForest, ResidualSigma, ResidualCusum, ZRules]