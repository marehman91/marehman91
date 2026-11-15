"""Competing-risks landmark model: one gradient-boosted classifier per horizon (1..12 months).

For horizon H the classifier answers: "starting from this month, does the person resign within H
months, and if so for which reason?" Stacking the horizons gives each employee a cumulative risk
curve per reason, and summing month-on-month differences across people gives the workforce forecast.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

from . import config as C
from .features import CATEGORICAL, FEATURES, label

N_REASONS = len(C.REASONS)


class LandmarkModel:
    def __init__(self, horizons: list[int] | None = None, random_state: int = 0):
        self.horizons = list(horizons or C.HORIZONS)
        self.random_state = random_state
        self.models: dict[int, HistGradientBoostingClassifier] = {}
        self.cats: dict[str, list] = {}
        self.training_rows: dict[int, dict] = {}

    def matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        X = df[FEATURES].copy()
        for c in CATEGORICAL:
            X[c] = pd.Categorical(X[c], categories=self.cats[c])
        return X

    def fit(self, panel: pd.DataFrame, cutoff: pd.Timestamp) -> "LandmarkModel":
        """Train on snapshots whose outcome window closed before `cutoff` (no peeking)."""
        self.cats = {c: sorted(panel[c].dropna().astype(str).unique()) for c in CATEGORICAL}
        snaps = panel["snapshot"]
        for H in self.horizons:
            window_end = snaps.map({t: t + pd.DateOffset(months=H) for t in snaps.unique()})
            rows = panel[window_end <= cutoff]
            y = label(rows, H)
            clf = HistGradientBoostingClassifier(
                learning_rate=0.05, max_iter=250, max_leaf_nodes=8, min_samples_leaf=150,
                l2_regularization=1.0, categorical_features="from_dtype", early_stopping=False,
                random_state=self.random_state,
            )
            clf.fit(self.matrix(rows), y)
            self.models[H] = clf
            self.training_rows[H] = {
                "rows": int(len(rows)),
                "first_snapshot": rows["snapshot"].min().date().isoformat(),
                "last_snapshot": rows["snapshot"].max().date().isoformat(),
                "events": {r: int((y == i + 1).sum()) for i, r in enumerate(C.REASONS)},
            }
        return self

    def proba(self, df: pd.DataFrame, H: int) -> np.ndarray:
        """(n, 5) probabilities [Stay, reasons...] for one horizon."""
        clf = self.models[H]
        p = clf.predict_proba(self.matrix(df))
        out = np.zeros((len(df), N_REASONS + 1))
        for j, cls in enumerate(clf.classes_):
            out[:, int(cls)] = p[:, j]
        return out

    def cif(self, df: pd.DataFrame) -> np.ndarray:
        """(n, len(horizons), n_reasons) cumulative probability of resigning by each horizon, per reason."""
        arr = np.stack([self.proba(df, H)[:, 1:] for H in self.horizons], axis=1)
        arr = np.maximum.accumulate(arr, axis=1)  # cumulative risk cannot go down with a longer window
        total = arr.sum(axis=2, keepdims=True)
        scale = np.where(total > 0.99, 0.99 / np.maximum(total, 1e-9), 1.0)
        return arr * scale
