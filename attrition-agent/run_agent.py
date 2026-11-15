#!/usr/bin/env python3
"""Retention Radar - run the full agent.

Examples
  python run_agent.py --demo                                   # synthetic data, regenerated
  python run_agent.py --data data_template/My_HR_Data.xlsx     # your filled-in template
  python run_agent.py --data path/to/csv_folder --asof 2026-12-01
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from attrition_agent import data_io, pipeline, report  # noqa: E402
from attrition_agent.generate_synthetic import generate  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, help="Filled-in Excel template, or a folder of CSV files")
    ap.add_argument("--demo", action="store_true", help="Generate synthetic data and run on it")
    ap.add_argument("--asof", type=pd.Timestamp, help="Scoring date (default: the 1st after your data ends)")
    ap.add_argument("--backtest-asof", type=pd.Timestamp, help="Backtest date (default: 1 Feb of the last full season)")
    ap.add_argument("--out", type=Path, default=ROOT / "reports")
    a = ap.parse_args()

    if not a.data and not a.demo:
        ap.error("pass --data <file-or-folder> or --demo")
    synthetic = a.demo
    data_path = a.data
    if a.demo:
        data_path = ROOT / "data" / "synthetic"
        print(f"Generating synthetic data in {data_path} ...")
        generate(data_path)

    T, rep = data_io.load(data_path)
    print("Data check:")
    for name, n in rep.tables.items():
        print(f"  {name:22s} {n:>7,d} rows")
    for issue in rep.issues:
        print(f"  {issue}")
    if not rep.ok():
        print("Fix the ERROR lines above and run again.")
        return 1

    result = pipeline.run(T, rep, asof=a.asof, backtest_asof=a.backtest_asof, synthetic=synthetic)
    a.out.mkdir(parents=True, exist_ok=True)
    asof = result["meta"]["asof"]
    (a.out / "results.json").write_text(json.dumps(result, indent=1, default=str))
    rows = []
    for e in result["employees"]:
        rows.append({
            "employee_id": e["id"], "name": e["name"], "designation": e["designation"], "discipline": e["discipline"],
            "client_region": e["region"], "tenure_years": e["tenure_years"], "tier": e["tier"],
            "risk_3m": e["risk3"], "risk_6m": e["risk6"], "risk_12m": e["risk12"], "season_risk": e["season_risk"],
            "main_reason": e["reason"], **{f"p12_{k.lower()}": v for k, v in e["by_reason"].items()},
            "why_1": e["drivers"][0]["text"] if len(e["drivers"]) > 0 else "",
            "why_2": e["drivers"][1]["text"] if len(e["drivers"]) > 1 else "",
            "why_3": e["drivers"][2]["text"] if len(e["drivers"]) > 2 else "",
            "recommended_action": e["action"], "investment_guidance": e["invest"],
        })
    pd.DataFrame(rows).to_csv(a.out / f"watchlist_{asof}.csv", index=False)
    html = report.render(result)
    (a.out / "retention_radar.html").write_text(html)

    k, b = result["kpis"], result["backtest"]
    print("\nSummary")
    print(f"  As of {asof}: {k['headcount']} active engineers, {k['serving_notice']} serving notice")
    print(f"  Expected resignations next 12 months: {k['expected_12m']:.0f} ({k['expected_12m_rate']:.0%}); "
          f"in {k['season_label']}: {k['expected_season']:.0f}")
    print(f"  Tiers: {k['tiers']}  High by reason: {k['high_by_reason']}")
    print(f"  Backtest {b['asof']}: caught {b['caught']}/{b['left']} leavers in a top-{b['list_size']} list; "
          f"AUC {b['auc']:.2f}; reason correct {b['reason_accuracy']:.0%}; forecast {b['expected_total']:.0f} vs actual {b['actual_total']}")
    print(f"  Outputs in {a.out}: retention_radar.html, watchlist_{asof}.csv, results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
