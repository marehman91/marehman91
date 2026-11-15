"""Run with:  python -m pytest tests   (or  python tests/test_pipeline.py)"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from attrition_agent import data_io, features as F  # noqa: E402
from attrition_agent.generate_synthetic import Simulator  # noqa: E402
from attrition_agent.template import build  # noqa: E402

_CACHE = {}


def tables():
    if "T" not in _CACHE:
        raw = Simulator(seed=11).run()
        _CACHE["T"], _CACHE["rep"] = data_io.normalise(raw)
    return _CACHE["T"], _CACHE["rep"]


def truncate(T, t):
    """Drop every record dated on/after t, as if we were living on day t."""
    cols = {"compensation": "effective_date", "performance_reviews": "review_date", "timesheets": "month",
            "hr_requests": "request_date", "leaves": "start_date", "engagement_surveys": "survey_date",
            "project_assignments": "start_date"}
    out = {k: v.copy() for k, v in T.items()}
    for name, col in cols.items():
        out[name] = out[name][out[name][col] < t]
    pa = out["project_assignments"]
    pa.loc[pa["end_date"] >= t, "end_date"] = pd.NaT
    out["employees"] = out["employees"][out["employees"]["join_date"] < t]
    return out


def test_no_future_leakage():
    """Signals on day t must be identical whether or not later data exists."""
    T, _ = tables()
    t = pd.Timestamp("2025-02-01")
    full = F.build_snapshot(T, t).set_index("employee_id")[F.NUMERIC].sort_index()
    past = F.build_snapshot(truncate(T, t), t).set_index("employee_id")[F.NUMERIC].sort_index()
    assert list(full.index) == list(past.index)
    np.testing.assert_allclose(full.to_numpy(float), past.to_numpy(float), equal_nan=True)


def test_protected_attributes_not_features():
    banned = {"gender", "date_of_birth", "marital_status", "religion", "cnic", "full_name", "age"}
    assert not banned & set(F.FEATURES)


def test_excel_template_round_trip(tmp_path=None):
    T, rep = tables()
    tmp = Path(tmp_path or (ROOT / "reports"))
    path = build(tmp / "_template_test.xlsx")
    from openpyxl import load_workbook
    wb = load_workbook(path)
    for name in ("employees", "exits", "compensation"):
        ws = wb[name]
        cols = [c.value for c in ws[1] if c.value and c.value in T[name].columns]
        for row in T[name][cols].head(200).itertuples(index=False):
            ws.append([None if pd.isna(v) else (v.to_pydatetime() if isinstance(v, pd.Timestamp) else v) for v in row])
    wb.save(path)
    T2, rep2 = data_io.load(path)
    path.unlink()
    assert rep2.ok(), rep2.issues
    assert len(T2["employees"]) == 200
    assert T2["exits"]["reason_class"].isin(["Foreign Study", "Competitor", "Performance", "Personal/Other"]).all()


def test_minimal_data_still_scores():
    """Only the three required tables: signals from missing tables are blank, nothing crashes."""
    T, _ = tables()
    raw = {k: T[k] for k in ("employees", "exits", "compensation")}
    T2, rep = data_io.normalise(raw)
    assert rep.ok()
    snap = F.build_snapshot(T2, pd.Timestamp("2025-02-01"))
    assert len(snap) > 100 and snap["utilization_3m"].isna().all()


def test_reason_mapping():
    assert data_io.map_reason("Got admission for MS in Australia") == "Foreign Study"
    assert data_io.map_reason("Better offer from another company") == "Competitor"
    assert data_io.map_reason("Terminated - performance") == "Performance"
    assert data_io.map_reason("Family moved to Lahore") == "Personal/Other"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
