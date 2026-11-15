"""End-to-end run: features -> backtest -> live scoring -> explanations -> fairness -> report data."""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from . import config as C
from .explain import LOW_RISK_ACTION, PLAYBOOK, contributions, tier, top_drivers, typical_values
from .fairness import audit
from .features import FEATURES, GROUP_LABEL, GROUPS, build_panel, label
from .model import LandmarkModel

PANEL_START_OFFSET_MONTHS = 12  # first snapshot needs a year of history for its signals


def month_start(d: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(year=d.year, month=d.month, day=1)


def default_dates(data_end: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Live 'as of' = first day after the data ends; backtest = 1 Feb of the last fully observed season."""
    asof = month_start(data_end) + pd.DateOffset(months=1)
    last_season_year = data_end.year if data_end >= pd.Timestamp(year=data_end.year, month=10, day=31) - pd.Timedelta(days=7) else data_end.year - 1
    return asof, pd.Timestamp(year=last_season_year, month=2, day=1)


def run(T: dict, data_report, asof: pd.Timestamp | None = None, backtest_asof: pd.Timestamp | None = None,
        synthetic: bool = False, log=print) -> dict:
    data_end = data_report.data_end
    d_asof, d_bt = default_dates(data_end)
    asof = asof or d_asof
    backtest_asof = backtest_asof or d_bt
    emp_dates = T["employees"]["join_date"].dropna()
    panel_start = max(month_start(emp_dates.min()) + pd.DateOffset(months=PANEL_START_OFFSET_MONTHS),
                      month_start(T["timesheets"]["month"].min()) + pd.DateOffset(months=PANEL_START_OFFSET_MONTHS)
                      if not T["timesheets"].empty else pd.Timestamp("1900-01-01"))
    log(f"Building monthly signals {panel_start.date()} -> {asof.date()} ...")
    panel = build_panel(T, panel_start, asof)
    log(f"  {len(panel):,} employee-months, {len(FEATURES)} signals")

    # ------------------------------------------------------------------ backtest
    bt_h = 9
    log(f"Backtest: training on data before {backtest_asof.date()} and predicting the next {bt_h} months ...")
    bt_model = LandmarkModel().fit(panel, backtest_asof)
    bt_snap = panel[panel["snapshot"] == backtest_asof].reset_index(drop=True)
    bt_cif = bt_model.cif(bt_snap)
    bt_any = bt_cif.sum(axis=2)
    bt_risk = bt_any[:, bt_h - 1]
    y = label(bt_snap, bt_h)
    left = y > 0
    k = int(round(0.2 * len(bt_snap)))
    order = np.argsort(-bt_risk)
    top = np.zeros(len(bt_snap), bool)
    top[order[:k]] = True
    pred_reason = bt_cif[:, bt_h - 1, :].argmax(axis=1) + 1
    caught = top & left
    months = [backtest_asof + pd.DateOffset(months=i) for i in range(bt_h)]
    exp_month = np.diff(np.concatenate([np.zeros((len(bt_snap), 1)), bt_any[:, :bt_h]], axis=1), axis=1).sum(axis=0)
    ev = bt_snap["event_date"]
    act_month = [int(((ev >= m) & (ev < m + pd.DateOffset(months=1))).sum()) for m in months]
    base_bt = typical_values(bt_snap)
    contrib_bt = contributions(bt_model, bt_h, bt_snap, pred_reason - 1, base_bt)
    drivers_bt = top_drivers(bt_snap, contrib_bt)

    per_reason = []
    for i, r in enumerate(C.REASONS):
        sel = y == i + 1
        per_reason.append({"reason": r, "left": int(sel.sum()), "caught": int((sel & top).sum())})
    examples = []
    min_lead = backtest_asof + pd.Timedelta(days=60)
    for i in order:  # strongest correct calls made at least two months ahead, at most two per reason
        if not caught[i] or pred_reason[i] != y[i] or len(examples) >= 6 or bt_snap["event_date"].iloc[i] < min_lead:
            continue
        rr = C.REASONS[y[i] - 1]
        if sum(1 for e in examples if e["actual_reason"] == rr) >= (2 if rr != "Personal/Other" else 1):
            continue
        row = bt_snap.iloc[i]
        examples.append({
            "name": row["full_name"], "id": row["employee_id"], "designation": row["designation"],
            "risk": float(bt_risk[i]), "predicted_reason": C.REASONS[pred_reason[i] - 1], "actual_reason": rr,
            "notice_date": row["event_date"].date().isoformat(), "drivers": drivers_bt[i],
        })
    examples.sort(key=lambda e: (C.REASONS.index(e["actual_reason"]), -e["risk"]))
    season_mask = left & bt_snap["event_date"].dt.month.isin(C.SEASON_MONTHS).values
    seasonal_catch = {"left": int(season_mask.sum()), "caught": int((season_mask & top).sum())}

    # rolling 90-day early warning (retrained every month, as in production)
    log("Rolling 90-day check (retrained monthly) ...")
    roll_start = max(panel_start + pd.DateOffset(months=18), backtest_asof - pd.DateOffset(months=6))
    roll_end = month_start(data_end) - pd.DateOffset(months=2)
    roll = {r: [0, 0] for r in C.REASONS}
    roll_exp = roll_act = 0.0
    for s in pd.date_range(roll_start, roll_end, freq="MS"):
        if s + pd.DateOffset(months=3) > asof:
            break
        m3 = LandmarkModel(horizons=[3]).fit(panel, s)
        sn = panel[panel["snapshot"] == s].reset_index(drop=True)
        y3 = label(sn, 3)
        r3 = m3.cif(sn)[:, 0, :].sum(axis=1)
        roll_exp += float(r3.sum())
        roll_act += float((y3 > 0).sum())
        t3 = np.zeros(len(sn), bool)
        t3[np.argsort(-r3)[: int(round(0.2 * len(sn)))]] = True
        for i, r in enumerate(C.REASONS):
            sel = y3 == i + 1
            roll[r][0] += int((sel & t3).sum())
            roll[r][1] += int(sel.sum())

    fair = audit(bt_snap, top, left, T["employees"], backtest_asof)

    backtest = {
        "asof": backtest_asof.date().isoformat(), "horizon_months": bt_h,
        "window_end": (backtest_asof + pd.DateOffset(months=bt_h) - pd.Timedelta(days=1)).date().isoformat(),
        "headcount": int(len(bt_snap)), "left": int(left.sum()), "list_size": k,
        "caught": int(caught.sum()), "precision": float(caught.sum() / k) if k else None,
        "auc": float(roc_auc_score(left, bt_risk)) if 0 < left.sum() < len(left) else None,
        "reason_accuracy": float((pred_reason[caught] == y[caught]).mean()) if caught.any() else None,
        "expected_total": float(exp_month.sum()), "actual_total": int(sum(act_month)),
        "monthly": [{"month": m.strftime("%Y-%m"), "expected": float(e), "actual": a} for m, e, a in zip(months, exp_month, act_month)],
        "per_reason": per_reason, "examples": examples, "season": seasonal_catch,
        "rolling_90d": {"from": roll_start.strftime("%Y-%m"), "to": roll_end.strftime("%Y-%m"),
                        "per_reason": [{"reason": r, "caught": v[0], "left": v[1]} for r, v in roll.items()],
                        "expected": roll_exp, "actual": roll_act},
    }

    # ------------------------------------------------------------------ live
    log(f"Live model: training on everything before {asof.date()} ...")
    model = LandmarkModel().fit(panel, asof)
    snap = panel[panel["snapshot"] == asof].reset_index(drop=True)
    cif = model.cif(snap)
    any_c = cif.sum(axis=2)
    reason_idx = cif[:, 11, :].argmax(axis=1)
    base = typical_values(snap)
    contrib = contributions(model, 12, snap, reason_idx, base)
    drivers = top_drivers(snap, contrib)

    fmonths = [asof + pd.DateOffset(months=i) for i in range(12)]
    season_idx = [i for i, m in enumerate(fmonths) if m.month in C.SEASON_MONTHS]
    exp_by_month = np.diff(np.concatenate([np.zeros((len(snap), 1, len(C.REASONS))), cif], axis=1), axis=1)  # (n,12,R)
    employees = []
    for i in range(len(snap)):
        row = snap.iloc[i]
        p12 = float(any_c[i, 11])
        t = tier(p12)
        reason = C.REASONS[reason_idx[i]]
        play = PLAYBOOK[reason] if t != "Low" else LOW_RISK_ACTION
        rate = row["billing_rate_usd"]
        lvl = row["level"]
        if pd.isna(rate):
            rate = C.DEFAULT_BILLING_USD.get(int(lvl) if pd.notna(lvl) else 2, 24)
        impact = float(rate) * C.BILLABLE_HOURS_PER_MONTH * C.VACANCY_IMPACT_MONTHS
        employees.append({
            "id": row["employee_id"], "name": row["full_name"] if pd.notna(row["full_name"]) else row["employee_id"],
            "designation": row["designation"], "discipline": row["discipline"], "region": row["client_region"],
            "tenure_years": round(float(row["tenure_months"]) / 12, 1),
            "risk3": round(float(any_c[i, 2]), 3), "risk6": round(float(any_c[i, 5]), 3), "risk12": round(p12, 3),
            "season_risk": round(float(exp_by_month[i, season_idx, :].sum()), 3) if season_idx else None,
            "by_reason": {C.REASON_SHORT[r]: round(float(cif[i, 11, j]), 3) for j, r in enumerate(C.REASONS)},
            "curve": [round(float(v), 3) for v in any_c[i]],
            "reason": reason, "tier": t, "drivers": drivers[i],
            "action": play["headline"], "steps": play["steps"], "invest": play["invest"],
            "impact_usd": round(impact), "expected_impact_usd": round(impact * p12),
        })
    employees.sort(key=lambda e: -e["risk12"])

    forecast = []
    for j, m in enumerate(fmonths):
        rec = {"month": m.strftime("%Y-%m")}
        for ri, r in enumerate(C.REASONS):
            rec[r] = round(float(exp_by_month[:, j, ri].sum()), 2)
        forecast.append(rec)
    ex = T["exits"]
    hist = []
    for m in pd.date_range(panel_start, month_start(data_end), freq="MS"):
        sel = ex[(ex["notice_date"] >= m) & (ex["notice_date"] < m + pd.DateOffset(months=1))]
        rec = {"month": m.strftime("%Y-%m")}
        for r in C.REASONS:
            rec[r] = int((sel["reason_class"] == r).sum())
        hist.append(rec)

    drivers_summary = {}
    for r in C.REASONS:
        counts: dict[str, int] = {}
        flagged = [e for e in employees if e["tier"] != "Low" and e["reason"] == r]
        for e in flagged:
            for d in e["drivers"]:
                counts[d["group"]] = counts.get(d["group"], 0) + 1
        drivers_summary[r] = {"people": len(flagged),
                              "groups": [{"group": g, "count": c} for g, c in sorted(counts.items(), key=lambda kv: -kv[1])[:6]]}

    notice = ex[(ex["notice_date"] < asof) & (ex["last_working_date"] >= asof)] if not ex.empty else ex
    tiers = {t: sum(1 for e in employees if e["tier"] == t) for t in ("High", "Medium", "Low")}
    high_by_reason = {C.REASON_SHORT[r]: sum(1 for e in employees if e["tier"] == "High" and e["reason"] == r) for r in C.REASONS}
    exp12 = float(any_c[:, 11].sum())
    exp_season = float(sum(sum(forecast[j][r] for r in C.REASONS) for j in season_idx))
    season_label = (f"{fmonths[season_idx[0]].strftime('%b')}-{fmonths[season_idx[-1]].strftime('%b %Y')}" if season_idx else "")
    kpis = {
        "headcount": int(len(snap)), "serving_notice": int(len(notice)),
        "expected_12m": exp12, "expected_12m_rate": exp12 / len(snap) if len(snap) else None,
        "expected_season": exp_season, "season_label": season_label,
        "tiers": tiers, "high_by_reason": high_by_reason,
        "expected_impact_usd": float(sum(e["expected_impact_usd"] for e in employees)),
        "high_impact_usd": float(sum(e["impact_usd"] for e in employees if e["tier"] == "High")),
    }

    model_card = {
        "method": "Competing-risks landmark model: 12 gradient-boosted classifiers (1-12 month horizons), monotone-corrected.",
        "features": FEATURES, "groups": {GROUP_LABEL[g]: cols for g, cols in GROUPS.items()},
        "training": {str(h): v for h, v in model.training_rows.items() if h in (3, 6, 12)},
        "tiers": {"High": C.TIER_HIGH, "Medium": C.TIER_MEDIUM},
        "impact_assumption": f"billing rate x {C.BILLABLE_HOURS_PER_MONTH} h x {C.VACANCY_IMPACT_MONTHS} months of vacancy and ramp-up",
    }
    return {
        "meta": {"asof": asof.date().isoformat(), "data_end": data_end.date().isoformat(), "synthetic": synthetic,
                 "generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "season_months": list(C.SEASON_MONTHS),
                 "reasons": C.REASONS, "reason_short": C.REASON_SHORT},
        "kpis": kpis, "backtest": backtest, "history": hist, "forecast": forecast,
        "employees": employees, "drivers": drivers_summary, "fairness": fair, "model": model_card,
        "data": {"tables": data_report.tables, "missing": data_report.missing_tables, "issues": data_report.issues},
    }
