"""Turn raw HR tables into one row of signals per employee per month ("snapshot").

Every feature for snapshot date t uses only records dated before t, so the backtest
cannot peek into the future. Protected attributes (gender, age, marital status...)
are never turned into features.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C

DAYS_PER_MONTH = 30.44

CATEGORICAL = ["discipline", "client_region"]
NUMERIC = [
    "tenure_months", "total_exp_years", "level",
    "compa_ratio", "months_since_raise", "last_raise_pct", "months_in_grade",
    "rating_last", "rating_change",
    "utilization_3m", "utilization_trend", "overtime_3m", "feedback_3m", "feedback_trend", "rework_3m", "rework_trend",
    "study_letters_12m", "attestation_12m", "months_since_study_letter",
    "single_day_leaves_6m", "unpaid_days_12m",
    "engagement_last", "engagement_change", "growth_last",
    "manager_changes_12m", "months_on_project",
    "snapshot_month",
]
FEATURES = NUMERIC + CATEGORICAL

# Signal groups used for plain-language explanations (season is shared by everyone, so not a "reason").
GROUPS: dict[str, list[str]] = {
    "study_letters": ["study_letters_12m", "attestation_12m", "months_since_study_letter"],
    "pay_vs_peers": ["compa_ratio"],
    "raise_history": ["months_since_raise", "last_raise_pct"],
    "career_stagnation": ["months_in_grade"],
    "career_stage": ["tenure_months", "total_exp_years", "level"],
    "performance_rating": ["rating_last", "rating_change"],
    "delivery_trend": ["utilization_3m", "utilization_trend", "rework_3m", "rework_trend", "feedback_3m", "feedback_trend"],
    "workload": ["overtime_3m", "client_region"],
    "engagement": ["engagement_last", "engagement_change", "growth_last"],
    "leave_pattern": ["single_day_leaves_6m", "unpaid_days_12m"],
    "manager_project": ["manager_changes_12m", "months_on_project"],
    "skill_demand": ["discipline"],
}
GROUP_LABEL = {
    "study_letters": "Study-type HR letters",
    "pay_vs_peers": "Pay vs peers",
    "raise_history": "Raise history",
    "career_stagnation": "Time in grade",
    "career_stage": "Career stage",
    "performance_rating": "Performance rating",
    "delivery_trend": "Delivery trend",
    "workload": "Overtime and shift",
    "engagement": "Engagement survey",
    "leave_pattern": "Leave pattern",
    "manager_project": "Manager / project changes",
    "skill_demand": "Skill demand",
}


def _months(delta: pd.Series) -> pd.Series:
    return delta.dt.days / DAYS_PER_MONTH


def build_snapshot(T: dict[str, pd.DataFrame], t: pd.Timestamp) -> pd.DataFrame:
    """Signals for everyone employed (and not yet resigned) on date t."""
    emp = T["employees"]
    ex = T["exits"].set_index("employee_id") if not T["exits"].empty else pd.DataFrame(columns=["notice_date", "reason_class"])
    df = emp.loc[emp["join_date"] < t, ["employee_id", "full_name", "join_date", "designation_at_join", "discipline",
                                       "total_experience_at_join_years", "billing_rate_usd"]].copy()
    df["event_date"] = df["employee_id"].map(ex["notice_date"])
    df["reason_class"] = df["employee_id"].map(ex["reason_class"])
    df = df[df["event_date"].isna() | (df["event_date"] >= t)].set_index("employee_id")
    df["snapshot"] = t
    df["snapshot_month"] = t.month
    df["tenure_months"] = _months(t - df["join_date"])
    df["total_exp_years"] = pd.to_numeric(df["total_experience_at_join_years"], errors="coerce") + df["tenure_months"] / 12

    # ---- compensation
    c = T["compensation"]
    c = c[c["effective_date"] < t].sort_values(["employee_id", "effective_date"])
    c = c.assign(prev=c.groupby("employee_id")["monthly_salary_pkr"].shift(1))
    last = c.groupby("employee_id").tail(1).set_index("employee_id").reindex(df.index)
    df["salary"] = last["monthly_salary_pkr"]
    df["designation"] = last["designation"].fillna(df["designation_at_join"])
    df["level"] = df["designation"].map(C.DESIGNATION_LEVELS)
    df["months_since_raise"] = _months(t - last["effective_date"]).fillna(df["tenure_months"])
    df["last_raise_pct"] = (last["monthly_salary_pkr"] / last["prev"] - 1) * 100
    grade = c[c["change_type"].isin(["Promotion", "Joining"])].groupby("employee_id")["effective_date"].max()
    df["months_in_grade"] = _months(t - grade.reindex(df.index).fillna(df["join_date"]))
    peer_median = df.groupby("designation")["salary"].transform("median")
    df["compa_ratio"] = df["salary"] / peer_median

    # ---- performance reviews
    r = T["performance_reviews"]
    r = r[r["review_date"] < t].sort_values(["employee_id", "review_date"])
    r = r.assign(prev=r.groupby("employee_id")["rating"].shift(1))
    rl = r.groupby("employee_id").tail(1).set_index("employee_id").reindex(df.index)
    df["rating_last"] = pd.to_numeric(rl["rating"], errors="coerce")
    df["rating_change"] = df["rating_last"] - pd.to_numeric(rl["prev"], errors="coerce")

    # ---- timesheets: last 3 months vs the 6 months before
    ts = T["timesheets"]
    m3, m9 = t - pd.DateOffset(months=3), t - pd.DateOffset(months=9)

    def agg(w: pd.DataFrame) -> pd.DataFrame:
        w = w.assign(util=w["billable_hours"] / w["total_hours"].replace(0, np.nan))
        return w.groupby("employee_id").agg(util=("util", "mean"), ot=("overtime_hours", "mean"),
                                            fb=("client_feedback_score", "mean"), rw=("rework_items", "mean")).reindex(df.index)

    a3 = agg(ts[(ts["month"] >= m3) & (ts["month"] < t)])
    a9 = agg(ts[(ts["month"] >= m9) & (ts["month"] < m3)])
    df["utilization_3m"] = a3["util"] * 100
    df["utilization_trend"] = (a3["util"] - a9["util"]) * 100
    df["overtime_3m"] = a3["ot"]
    df["feedback_3m"] = a3["fb"]
    df["feedback_trend"] = a3["fb"] - a9["fb"]
    df["rework_3m"] = a3["rw"]
    df["rework_trend"] = a3["rw"] - a9["rw"]

    # ---- HR letter requests
    h = T["hr_requests"]
    h = h[(h["request_date"] < t) & (h["request_date"] >= t - pd.Timedelta(days=730))]
    study = h[h["request_type"].isin(C.STUDY_DOC_TYPES)]
    s12 = study[study["request_date"] >= t - pd.Timedelta(days=365)]
    df["study_letters_12m"] = s12.groupby("employee_id").size().reindex(df.index).fillna(0)
    df["attestation_12m"] = (s12[s12["request_type"] == "Degree Attestation Support"]
                             .groupby("employee_id").size().reindex(df.index).fillna(0))
    df["months_since_study_letter"] = _months(t - study.groupby("employee_id")["request_date"].max().reindex(df.index))

    # ---- leaves
    lv = T["leaves"]
    lv = lv[lv["start_date"] < t]
    one = lv[(pd.to_numeric(lv["days"], errors="coerce") <= 1) & (lv["start_date"] >= t - pd.Timedelta(days=182))]
    df["single_day_leaves_6m"] = one.groupby("employee_id").size().reindex(df.index).fillna(0)
    unpaid = lv[(lv["leave_type"].astype(str).str.lower() == "unpaid") & (lv["start_date"] >= t - pd.Timedelta(days=365))]
    df["unpaid_days_12m"] = pd.to_numeric(unpaid["days"], errors="coerce").groupby(unpaid["employee_id"]).sum().reindex(df.index).fillna(0)

    # ---- engagement pulse (ignore answers older than 9 months)
    s = T["engagement_surveys"]
    s = s[s["survey_date"] < t].sort_values(["employee_id", "survey_date"])
    s = s.assign(prev=s.groupby("employee_id")["engagement_score"].shift(1))
    sl = s.groupby("employee_id").tail(1).set_index("employee_id").reindex(df.index)
    fresh = sl["survey_date"] >= t - pd.DateOffset(months=9)
    df["engagement_last"] = pd.to_numeric(sl["engagement_score"], errors="coerce").where(fresh)
    df["engagement_change"] = (pd.to_numeric(sl["engagement_score"], errors="coerce") - pd.to_numeric(sl["prev"], errors="coerce")).where(fresh)
    df["growth_last"] = pd.to_numeric(sl["growth_score"], errors="coerce").where(fresh)

    # ---- project / manager assignments
    pa = T["project_assignments"]
    pa = pa[pa["start_date"] < t].sort_values(["employee_id", "start_date"]).copy()
    if not pa.empty:
        g = pa.groupby("employee_id")
        pa["first"] = g.cumcount() == 0
        pa["mgr_changed"] = (g["manager_id"].shift(1) != pa["manager_id"]) & ~pa["first"]
        proj = pa["project_code"].fillna(pa["start_date"].astype(str))
        pa["proj_changed"] = (proj != g["project_code"].shift(1).fillna("")) | pa["first"]
        pa["block"] = pa.groupby("employee_id")["proj_changed"].cumsum()
        pa["block_start"] = pa.groupby(["employee_id", "block"])["start_date"].transform("min")
        cur = pa.groupby("employee_id").tail(1).set_index("employee_id").reindex(df.index)
        df["client_region"] = cur["client_region"]
        df["months_on_project"] = _months(t - cur["block_start"])
        df["manager_changes_12m"] = (pa[pa["mgr_changed"] & (pa["start_date"] >= t - pd.Timedelta(days=365))]
                                     .groupby("employee_id").size().reindex(df.index).fillna(0))
    else:
        df["client_region"] = np.nan
        df["months_on_project"] = np.nan
        df["manager_changes_12m"] = 0.0

    return df.reset_index()


def build_panel(T: dict[str, pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Monthly snapshots from start to end (inclusive, month starts)."""
    frames = [build_snapshot(T, t) for t in pd.date_range(start, end, freq="MS")]
    return pd.concat(frames, ignore_index=True)


def label(panel: pd.DataFrame, horizon: int) -> np.ndarray:
    """0 = still here after `horizon` months, 1..4 = resigned within the window (index into config.REASONS + 1)."""
    ends = {t: t + pd.DateOffset(months=horizon) for t in panel["snapshot"].unique()}
    window_end = panel["snapshot"].map(ends)
    inside = panel["event_date"].notna() & (panel["event_date"] < window_end)
    codes = panel["reason_class"].map({r: i + 1 for i, r in enumerate(C.REASONS)}).fillna(0).astype(int)
    return np.where(inside, codes, 0)
