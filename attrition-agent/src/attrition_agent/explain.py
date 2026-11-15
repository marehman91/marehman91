"""Plain-language reasons for every flag, plus the retention playbook.

Method (group occlusion): for each signal group, reset that person's values to what is typical
in the company and re-score them. The drop in risk is that group's contribution. Groups that
raise risk the most become the "why" shown to HR, written with the person's actual numbers.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .features import CATEGORICAL, GROUP_LABEL, GROUPS, NUMERIC

SHIFT_NAME = {"US": "US night shift", "Australia": "Australia early-morning shift"}


def typical_values(df: pd.DataFrame) -> dict:
    base = {}
    for c in NUMERIC:
        col = pd.to_numeric(df[c], errors="coerce")
        base[c] = np.nan if col.isna().mean() > 0.5 else float(col.median())
    for c in CATEGORICAL:
        mode = df[c].mode(dropna=True)
        base[c] = mode.iloc[0] if len(mode) else np.nan
    return base


def contributions(model, H: int, df: pd.DataFrame, reason_idx: np.ndarray, base: dict) -> np.ndarray:
    """(n, n_groups) drop in P(reason within H months) when each group is reset to typical values."""
    n = len(df)
    rows = np.arange(n)
    p0 = model.proba(df, H)[rows, reason_idx + 1]
    out = np.zeros((n, len(GROUPS)))
    for gi, cols in enumerate(GROUPS.values()):
        dg = df.copy()
        for c in cols:
            dg[c] = base[c]
        out[:, gi] = p0 - model.proba(dg, H)[rows, reason_idx + 1]
    return out


def _f(x, fmt="{:.0f}", none="n/a"):
    return none if x is None or (isinstance(x, float) and np.isnan(x)) else fmt.format(x)


def describe(group: str, r: pd.Series) -> str:
    if group == "study_letters":
        n = int(r["study_letters_12m"])
        if n == 0:
            return "No study-type HR letters requested"
        s = f"{n} study-type HR letter{'s' if n != 1 else ''} in 12 months"
        if r["attestation_12m"] > 0:
            s += ", incl. degree attestation"
        if pd.notna(r["months_since_study_letter"]):
            s += f" (latest {r['months_since_study_letter']:.0f} mo ago)"
        return s
    if group == "pay_vs_peers":
        d = (r["compa_ratio"] - 1) * 100
        if np.isnan(d):
            return "Pay vs peers unknown"
        return f"Paid {abs(d):.0f}% {'below' if d < 0 else 'above'} the median {r['designation']}"
    if group == "raise_history":
        if pd.isna(r["last_raise_pct"]):
            return f"No raise since joining ({r['months_since_raise']:.0f} months)"
        return f"Last raise {r['last_raise_pct']:.0f}%, {r['months_since_raise']:.0f} months ago"
    if group == "career_stagnation":
        return f"{r['months_in_grade'] / 12:.1f} years in the same grade"
    if group == "career_stage":
        return f"{r['tenure_months'] / 12:.1f} yrs with us, {r['total_exp_years']:.1f} yrs total experience"
    if group == "performance_rating":
        if pd.notna(r["rating_change"]) and r["rating_change"] < 0:
            return f"Rating fell from {r['rating_last'] - r['rating_change']:.0f} to {r['rating_last']:.0f}"
        return f"Latest rating {_f(r['rating_last'])}/5"
    if group == "delivery_trend":
        s = f"Utilisation {_f(r['utilization_3m'])}%"
        if pd.notna(r["utilization_trend"]):
            s += f" ({r['utilization_trend']:+.0f} pts vs prior 6 mo)"
        if pd.notna(r["rework_3m"]):
            s += f", rework {r['rework_3m']:.1f}/month"
        return s
    if group == "workload":
        return f"{_f(r['overtime_3m'])} overtime hrs/month on {SHIFT_NAME.get(r['client_region'], str(r['client_region']))}"
    if group == "engagement":
        if pd.isna(r["engagement_last"]):
            return "No recent engagement survey answer"
        s = f"Engagement {r['engagement_last']:.1f}/5"
        if pd.notna(r["engagement_change"]) and r["engagement_change"] <= -0.2:
            s += f", down {abs(r['engagement_change']):.1f}"
        if pd.notna(r["growth_last"]):
            s += f"; career-growth score {r['growth_last']:.1f}/5"
        return s
    if group == "leave_pattern":
        s = f"{int(r['single_day_leaves_6m'])} single-day leaves in 6 months"
        if r["unpaid_days_12m"] > 0:
            s += f", {int(r['unpaid_days_12m'])} unpaid days in 12 months"
        return s
    if group == "manager_project":
        if r["manager_changes_12m"] > 0:
            return f"{int(r['manager_changes_12m'])} manager change(s) in 12 months"
        return f"{_f(r['months_on_project'])} months on the same project"
    if group == "skill_demand":
        return f"{r['discipline']} skills are in high market demand"
    return group


def top_drivers(df: pd.DataFrame, contrib: np.ndarray, k: int = 3, min_effect: float = 0.005) -> list[list[dict]]:
    names = list(GROUPS)
    out = []
    for i in range(len(df)):
        order = np.argsort(-contrib[i])
        row = df.iloc[i]
        items = []
        for gi in order[:k]:
            if contrib[i, gi] < min_effect:
                break
            items.append({"group": GROUP_LABEL[names[gi]], "key": names[gi], "effect": round(float(contrib[i, gi]), 3),
                          "text": describe(names[gi], row)})
        out.append(items)
    return out


PLAYBOOK = {
    "Foreign Study": {
        "headline": "Open a no-penalty career conversation about study plans",
        "steps": [
            "Manager + HRBP talk within 2 weeks; ask about higher-study plans directly and make clear there is no penalty.",
            "Offer alternatives: sponsored local MS (evening/weekend), PE/CEng licensing support, or a dated rehire-after-degree path.",
            "If the plan is firm: start knowledge transfer and a shadow resource on the client account 8-12 weeks before the intake.",
            "Where visa rules allow, discuss part-time remote work during studies to keep the client relationship.",
        ],
        "invest": "Invest with protection: training bond or phased knowledge transfer",
    },
    "Competitor": {
        "headline": "Stay interview and pay check",
        "steps": [
            "Stay interview within 2 weeks (manager + HRBP): what would make them stay 2 more years?",
            "Compare pay with market and peers; correct a real gap now rather than after a counter-offer.",
            "Show a dated promotion path and give visible stretch work on the client account.",
            "Review overtime and shift load; rotate off the night shift where possible.",
        ],
        "invest": "Invest: training and recognition are retention levers here",
    },
    "Performance": {
        "headline": "Manager diagnosis before any decision",
        "steps": [
            "Manager 1:1 to find the cause: burnout, skill gap, project fit, or a personal issue.",
            "Try a project rotation or targeted upskilling for 90 days with clear, written goals.",
            "A formal improvement plan only after HR review; keep it documented and fair.",
            "Protect the client meanwhile: pair with a senior reviewer on deliverables.",
        ],
        "invest": "Hold new discretionary spend until the 90-day plan is reviewed (manager + HR decide)",
    },
    "Personal/Other": {
        "headline": "Wellbeing and flexibility check-in",
        "steps": [
            "Informal check-in by the manager on workload, family and health.",
            "Offer flexibility that the client contract allows (hours, hybrid days).",
        ],
        "invest": "Invest normally",
    },
}
LOW_RISK_ACTION = {"headline": "No action needed; keep regular 1:1s", "steps": [], "invest": "Invest normally"}


def tier(p12: float) -> str:
    if p12 >= C.TIER_HIGH:
        return "High"
    if p12 >= C.TIER_MEDIUM:
        return "Medium"
    return "Low"
