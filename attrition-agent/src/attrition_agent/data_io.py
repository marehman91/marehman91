"""Load HR data from the Excel template (one sheet per table) or a folder of CSV files, then validate it."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from . import config as C

# table -> (required columns, optional columns, date columns)
SCHEMA: dict[str, tuple[list[str], list[str], list[str]]] = {
    "employees": (
        ["employee_id", "join_date", "designation_at_join", "discipline", "total_experience_at_join_years"],
        ["full_name", "gender", "date_of_birth", "marital_status", "highest_degree", "billing_rate_usd"],
        ["join_date", "date_of_birth"],
    ),
    "exits": (
        ["employee_id", "last_working_date", "exit_type", "exit_reason"],
        ["notice_date"],
        ["notice_date", "last_working_date"],
    ),
    "compensation": (
        ["employee_id", "effective_date", "monthly_salary_pkr", "designation", "change_type"],
        [],
        ["effective_date"],
    ),
    "performance_reviews": (["employee_id", "review_date", "rating"], ["cycle"], ["review_date"]),
    "timesheets": (
        ["employee_id", "month", "total_hours", "billable_hours"],
        ["overtime_hours", "client_feedback_score", "rework_items"],
        ["month"],
    ),
    "hr_requests": (["employee_id", "request_date", "request_type"], [], ["request_date"]),
    "leaves": (["employee_id", "start_date", "days", "leave_type"], [], ["start_date"]),
    "engagement_surveys": (["employee_id", "survey_date", "engagement_score"], ["growth_score"], ["survey_date"]),
    "project_assignments": (
        ["employee_id", "start_date", "client_region"],
        ["end_date", "project_code", "client_name", "manager_id"],
        ["start_date", "end_date"],
    ),
}
REQUIRED_TABLES = ["employees", "exits", "compensation"]


@dataclass
class DataReport:
    tables: dict[str, int] = field(default_factory=dict)
    missing_tables: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    data_end: pd.Timestamp | None = None

    def ok(self) -> bool:
        return not any(i.startswith("ERROR") for i in self.issues)


def map_reason(text: str) -> str:
    s = f" {str(text).lower()} "
    for reason, keys in C.REASON_KEYWORDS.items():
        if any(k in s for k in keys):
            return reason
    return "Personal/Other"


def load(path: Path) -> tuple[dict[str, pd.DataFrame], DataReport]:
    path = Path(path)
    raw: dict[str, pd.DataFrame] = {}
    if path.is_file() and path.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        sheets = pd.read_excel(path, sheet_name=None)
        for name, df in sheets.items():
            key = name.strip().lower().replace(" ", "_")
            if key in SCHEMA:
                raw[key] = df
    else:
        for name in SCHEMA:
            f = path / f"{name}.csv"
            if f.exists():
                raw[name] = pd.read_csv(f)
    return normalise(raw)


def normalise(raw: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], DataReport]:
    rep = DataReport()
    out: dict[str, pd.DataFrame] = {}
    for name, (req, opt, dates) in SCHEMA.items():
        df = raw.get(name)
        if df is None or df.empty:
            rep.missing_tables.append(name)
            level = "ERROR" if name in REQUIRED_TABLES else "WARN"
            rep.issues.append(f"{level}: table '{name}' not provided" + ("" if level == "ERROR" else " - related signals will be blank"))
            out[name] = pd.DataFrame({c: pd.Series(dtype="datetime64[ns]" if c in dates else "object") for c in req + opt})
            continue
        df = df.copy()
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
        df = df.dropna(how="all")
        missing = [c for c in req if c not in df.columns]
        if missing:
            rep.issues.append(f"ERROR: '{name}' is missing required column(s): {', '.join(missing)}")
        for c in req + opt:
            if c not in df.columns:
                df[c] = pd.NA
        for c in dates:
            before = df[c].isna().sum()
            df[c] = pd.to_datetime(df[c], errors="coerce")
            bad = df[c].isna().sum() - before
            if bad > 0:
                rep.issues.append(f"WARN: '{name}.{c}' has {bad} value(s) that are not valid dates")
        df["employee_id"] = df["employee_id"].astype(str).str.strip()
        out[name] = df
        rep.tables[name] = len(df)

    emp = out["employees"]
    known = set(emp["employee_id"])
    for name, df in out.items():
        if name == "employees" or df.empty:
            continue
        orphans = (~df["employee_id"].isin(known)).sum()
        if orphans:
            rep.issues.append(f"WARN: {orphans} row(s) in '{name}' refer to employee IDs not in 'employees' (ignored)")
            out[name] = df[df["employee_id"].isin(known)]

    ex = out["exits"]
    if not ex.empty:
        ex["notice_date"] = ex["notice_date"].fillna(ex["last_working_date"] - pd.Timedelta(days=30))
        ex["reason_class"] = ex["exit_reason"].map(map_reason)
        dup = ex["employee_id"].duplicated(keep="last").sum()
        if dup:
            rep.issues.append(f"WARN: {dup} employee(s) have more than one exit row; the latest is used")
            ex = ex.sort_values("notice_date").drop_duplicates("employee_id", keep="last")
        out["exits"] = ex

    for c in ("monthly_salary_pkr",):
        out["compensation"][c] = pd.to_numeric(out["compensation"][c], errors="coerce")
    for c in ("total_hours", "billable_hours", "overtime_hours", "client_feedback_score", "rework_items"):
        out["timesheets"][c] = pd.to_numeric(out["timesheets"][c], errors="coerce")
    out["timesheets"]["month"] = out["timesheets"]["month"].dt.to_period("M").dt.to_timestamp()

    unknown = sorted(set(out["compensation"]["designation"].dropna()) - set(C.DESIGNATION_LEVELS))
    if unknown:
        rep.issues.append("WARN: designation(s) not mapped to a career level in config.py: " + ", ".join(map(str, unknown[:8])))

    # Latest date seen anywhere = data cut-off.
    ends = []
    for name, (_, _, dates) in SCHEMA.items():
        for c in dates:
            if c in out[name] and c not in ("date_of_birth", "end_date", "last_working_date"):
                v = out[name][c].max()
                if pd.notna(v):
                    ends.append(v)
    rep.data_end = max(ends) if ends else None
    return out, rep
