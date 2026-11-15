"""Fairness audit on the backtest list, where real outcomes are known.

For each protected attribute (gender, age band, marital status) we compare:
  * flag rate        - share of the group put on the watchlist
  * actual exit rate - share of the group that really resigned in the window
  * precision        - of those flagged, how many really resigned (equal precision = equally reliable)
and apply the 4/5ths rule to flag rates. A proxy test checks whether the model's inputs can
reconstruct the attribute, which would let bias creep in even though the attribute itself is unused.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import cross_val_score

from . import config as C
from .features import CATEGORICAL, FEATURES


def _age_band(dob: pd.Series, asof: pd.Timestamp) -> pd.Series:
    age = (asof - pd.to_datetime(dob, errors="coerce")).dt.days / 365.25
    return pd.cut(age, [0, 26, 31, 200], right=False, labels=["Under 26", "26-30", "31+"]).astype(object)


def protected_frame(snap: pd.DataFrame, employees: pd.DataFrame, asof: pd.Timestamp) -> pd.DataFrame:
    emp = employees.set_index("employee_id").reindex(snap["employee_id"])
    out = pd.DataFrame(index=snap.index)
    if emp["gender"].notna().any():
        out["Gender"] = emp["gender"].values
    if emp["date_of_birth"].notna().any():
        out["Age band"] = _age_band(emp["date_of_birth"], asof).values
    if emp["marital_status"].notna().any():
        out["Marital status"] = emp["marital_status"].values
    return out


def audit(snap: pd.DataFrame, flagged: np.ndarray, left: np.ndarray, employees: pd.DataFrame, asof: pd.Timestamp) -> dict:
    prot = protected_frame(snap, employees, asof)
    result = {"attributes": [], "proxy": [], "excluded": C.PROTECTED_COLUMNS}
    for attr in prot.columns:
        g = prot[attr]
        rows = []
        for val in sorted(g.dropna().unique(), key=str):
            m = (g == val).values
            n = int(m.sum())
            nf = int((m & flagged).sum())
            rows.append({
                "group": str(val), "n": n,
                "flag_rate": nf / n if n else None,
                "exit_rate": float((m & left).sum() / n) if n else None,
                "precision": float((m & flagged & left).sum() / nf) if nf else None,
                "recall": float((m & flagged & left).sum() / (m & left).sum()) if (m & left).sum() else None,
            })
        big = [r for r in rows if r["n"] >= 20 and r["flag_rate"] is not None]
        rates = [r["flag_rate"] for r in big]
        di = (min(rates) / max(rates)) if rates and max(rates) > 0 else None
        precs = [r["precision"] for r in big if r["precision"] is not None]
        prec_gap = (max(precs) - min(precs)) if len(precs) >= 2 else None
        if di is None:
            verdict, note = "n/a", "Groups too small to test."
        elif di >= C.DISPARATE_IMPACT_FLOOR:
            verdict, note = "Pass", "Flag rates are within the 4/5ths rule."
        elif prec_gap is not None and prec_gap <= 0.15:
            verdict, note = "Review", ("Flag rates differ, but they track real exit rates and precision is similar across groups. "
                                      "Keep flags for support only, never for adverse decisions.")
        else:
            verdict, note = "Fail", "Flag rates differ and precision is uneven. Investigate before use."
        result["attributes"].append({"attribute": attr, "groups": rows, "di_ratio": di, "precision_gap": prec_gap,
                                     "verdict": verdict, "note": note})

    # proxy test: can the model's own inputs predict the protected attribute?
    X = snap[FEATURES].copy()
    for c in CATEGORICAL:
        X[c] = X[c].astype("category")
    for attr in prot.columns:
        g = prot[attr]
        ok = g.notna().values
        if attr == "Age band":
            y = (g == "Under 26").values
            target = "Under 26 vs older"
        else:
            top = g.value_counts().index[0]
            y = (g != top).values
            target = f"{g.value_counts().index[-1]} vs {top}" if g.nunique() == 2 else f"not {top}"
        if ok.sum() < 60 or y[ok].sum() < 10:
            continue
        clf = HistGradientBoostingClassifier(max_iter=120, max_leaf_nodes=8, categorical_features="from_dtype", random_state=0)
        auc = float(np.mean(cross_val_score(clf, X[ok], y[ok], cv=3, scoring="roc_auc")))
        level = "Low" if auc < 0.65 else "Moderate" if auc < 0.8 else "High"
        note = {
            "Low": "Model inputs carry little information about this attribute.",
            "Moderate": "Some job-related inputs correlate with this attribute; watch outcomes.",
            "High": "Inputs such as experience and tenure strongly track this attribute. They are job-related, "
                    "so they stay, but outcomes are audited every run.",
        }[level]
        result["proxy"].append({"attribute": attr, "target": target, "auc": auc, "level": level, "note": note})
    return result
