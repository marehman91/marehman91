"""Synthetic HR data for a Pakistani civil-engineering services firm with US and Australian clients.

The output uses exactly the same tables and columns as the Excel data template, so the
rest of the pipeline cannot tell synthetic data from real data. Everything here is fake.

Behaviour that the simulation builds in (and that the model has to discover on its own):
  * Foreign study: aspirants decide in September, take IELTS/GRE leaves Oct-Jan, ask HR for
    attestation / experience / salary letters Nov-Jun, and resign 3-8 weeks before their intake
    (Australia July, USA/UK September, Germany October). About 40% fail and stay.
  * Competitor: hazard rises when pay falls behind peers, when the July increment disappoints,
    after manager changes, under heavy overtime, and for in-demand skills (BIM, Structural).
    A job search shows up as single-day leaves and a dip in engagement before the notice.
  * Performance fade: some engineers plateau after 1.5-4 years; ratings, utilisation and client
    feedback slide and rework rises before a performance exit.
  * Noise: plenty of people request letters for car loans or tourist visas and never leave,
    some leavers show no signal at all, and "Personal/Other" exits are close to random.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C

SIM_START = pd.Timestamp("2021-01-01")
DATA_END = pd.Timestamp("2026-10-31")
MONTHS = pd.date_range(SIM_START, "2026-10-01", freq="MS")

LEVEL_NAME = {1: "Junior Engineer", 2: "Design Engineer", 3: "Senior Engineer", 4: "Lead Engineer", 5: "Project Manager"}
BASE_SALARY_2021 = {1: 85_000, 2: 135_000, 3: 210_000, 4: 310_000, 5: 440_000}
MARKET_GROWTH = {2022: 0.20, 2023: 0.24, 2024: 0.18, 2025: 0.14, 2026: 0.13}
INCREMENT_BY_RATING = {5: 0.17, 4: 0.13, 3: 0.09, 2: 0.04, 1: 0.0}

DISCIPLINES = ["Structural", "Civil / Site Development", "BIM / Revit", "Transportation", "Water Resources", "Geotechnical"]
DISCIPLINE_P = [0.30, 0.20, 0.18, 0.12, 0.10, 0.10]
DEMAND = {"Structural": 1.25, "Civil / Site Development": 1.0, "BIM / Revit": 1.45,
          "Transportation": 1.0, "Water Resources": 0.9, "Geotechnical": 0.8}
# destination, intake month, intake day, share
DESTINATIONS = [("USA / Canada", 9, 1, 0.35), ("UK", 9, 20, 0.15), ("Australia", 7, 20, 0.30), ("Germany", 10, 10, 0.20)]

MALE = ["Ahmed", "Ali", "Hamza", "Usman", "Bilal", "Hassan", "Zain", "Faisal", "Imran", "Saad", "Omer", "Fahad",
        "Asad", "Waqas", "Junaid", "Kamran", "Shahzaib", "Talha", "Haris", "Danish", "Abdullah", "Arsalan", "Noman",
        "Adeel", "Salman", "Rizwan", "Moiz", "Taimur", "Shoaib", "Yasir", "Hammad", "Awais", "Sohaib", "Uzair"]
FEMALE = ["Ayesha", "Fatima", "Hira", "Sana", "Maryam", "Zainab", "Amna", "Mahnoor", "Iqra", "Rabia", "Komal",
          "Areeba", "Sidra", "Nimra", "Alishba", "Mehwish", "Anum"]
LAST = ["Khan", "Ahmed", "Malik", "Butt", "Qureshi", "Sheikh", "Chaudhry", "Raza", "Hussain", "Mirza", "Siddiqui",
        "Abbasi", "Javed", "Iqbal", "Shah", "Afridi", "Yousafzai", "Bhatti", "Rana", "Awan", "Durrani", "Khattak",
        "Bangash", "Gondal", "Niazi", "Tareen", "Kazmi", "Rizvi"]
US_CLIENTS = [f"US-{c}" for c in ("ATL", "DAL", "PHX", "DEN", "CLT", "SEA")]
AU_CLIENTS = [f"AU-{c}" for c in ("SYD", "MEL", "BNE", "PER")]
MANAGERS = [f"MGR-{i:02d}" for i in range(1, 25)]


def market_salary(level: int, d: pd.Timestamp) -> float:
    s = BASE_SALARY_2021[level]
    for y in range(2022, d.year + 1):
        g = MARKET_GROWTH.get(y, 0.10)
        s *= (1 + g) if y < d.year else (1 + g * (d.month - 1) / 12)
    return s


def level_for_experience(exp: float) -> int:
    if exp < 1.5:
        return 1
    if exp < 4:
        return 2
    if exp < 7:
        return 3
    if exp < 11:
        return 4
    return 5


def months_between(a: pd.Timestamp, b: pd.Timestamp) -> float:
    return (b - a).days / 30.44


class Emp:
    pass


class Simulator:
    def __init__(self, seed: int = 7):
        self.rng = np.random.default_rng(seed)
        self.next_id = 1001
        self.active: list[Emp] = []
        self.t = {k: [] for k in ("employees", "compensation", "performance_reviews", "timesheets",
                                  "hr_requests", "leaves", "engagement_surveys", "project_assignments", "exits")}

    # ------------------------------------------------------------------ hiring
    def hire(self, join: pd.Timestamp, exp: float, initial: bool = False) -> Emp:
        r = self.rng
        e = Emp()
        e.id = f"EMP-{self.next_id}"
        self.next_id += 1
        e.gender = "Female" if r.random() < 0.18 else "Male"
        first = r.choice(FEMALE if e.gender == "Female" else MALE)
        e.name = f"{first} {r.choice(LAST)}"
        e.join = join
        e.exp_at_join = round(exp, 1)
        age_at_join = 22.5 + exp + r.uniform(0, 2.5)
        e.dob = join - pd.Timedelta(days=int(age_at_join * 365.25))
        p_married = float(np.clip((age_at_join - 24) / 10, 0.05, 0.85))
        e.marital = "Married" if r.random() < p_married else "Single"
        e.discipline = r.choice(DISCIPLINES, p=DISCIPLINE_P)
        e.degree = "MSc" if r.random() < (0.12 if exp < 3 else 0.35) else "BSc"
        e.level = level_for_experience(exp)
        e.billing = C.DEFAULT_BILLING_USD[e.level] + (2 if e.discipline in ("BIM / Revit", "Structural") else 0)
        e.region = "US" if r.random() < 0.6 else "Australia"
        e.client = r.choice(US_CLIENTS if e.region == "US" else AU_CLIENTS)
        e.manager = r.choice(MANAGERS)
        e.project = f"P-{r.integers(100, 999)}"
        e.project_start = join
        e.seg_start = join

        # latent traits
        e.perf_base = float(np.clip(r.normal(3.35, 0.55), 1.6, 4.8))
        e.eng_base = float(np.clip(r.normal(3.7, 0.45), 2.2, 4.8))
        e.growth_base = float(np.clip(r.normal(3.6, 0.5), 2.0, 4.8))
        p_aspire = 0.55 if exp < 3 else 0.30 if exp < 5 else 0.09 if exp < 8 else 0.02
        if e.perf_base > 3.7:
            p_aspire *= 1.25
        if e.degree == "MSc":
            p_aspire *= 0.5
        e.aspire = r.random() < p_aspire
        e.strength = r.uniform(0.35, 1.0)
        e.attempts = 0
        e.applying = False
        e.fade_onset = r.uniform(18, 48) if r.random() < 0.18 else None
        e.fade_rate = r.uniform(0.7, 1.5)
        e.low_perf_months = 0
        e.search_left = 0
        e.planned = []  # (date, kind, payload)
        e.planned_notice = None
        e.rating = None
        e.prev_rating = None

        # salary
        if initial:
            tenure_y = months_between(join, SIM_START) / 12
            e.salary = market_salary(e.level, SIM_START) * float(np.exp(r.normal(-0.04, 0.09)))
            join_sal = e.salary / (1.10 ** max(tenure_y, 0))
            self.comp(e, join, join_sal, "Joining")
            if tenure_y > 0.6:
                self.comp(e, pd.Timestamp("2020-07-01"), e.salary, "Annual Increment")
            e.last_change = pd.Timestamp("2020-07-01") if tenure_y > 0.6 else join
            e.last_inc_pct = 0.08
            e.grade_since = join if tenure_y < 3 else join + pd.DateOffset(years=int(tenure_y) - 1)
            if e.fade_onset is not None and months_between(join, SIM_START) > e.fade_onset:
                e.fade_onset = months_between(join, SIM_START) + r.uniform(0, 36)
            e.rating = int(np.clip(round(e.perf_base + r.normal(0, 0.45)), 1, 5))
            self.t["performance_reviews"].append((e.id, pd.Timestamp("2020-12-15"), e.rating, "Mid-Year"))
        else:
            e.salary = market_salary(e.level, join) * float(np.exp(r.normal(0, 0.07)))
            self.comp(e, join, e.salary, "Joining")
            e.last_change = join
            e.last_inc_pct = 0.0
            e.grade_since = join
        self.t["employees"].append(dict(
            employee_id=e.id, full_name=e.name, gender=e.gender, date_of_birth=e.dob.date(),
            marital_status=e.marital, join_date=e.join.date(), designation_at_join=LEVEL_NAME[e.level],
            discipline=e.discipline, highest_degree=e.degree, total_experience_at_join_years=e.exp_at_join,
            billing_rate_usd=e.billing,
        ))
        self.active.append(e)
        return e

    def comp(self, e: Emp, d: pd.Timestamp, salary: float, kind: str):
        self.t["compensation"].append((e.id, d, int(round(salary, -2)), LEVEL_NAME[e.level], kind))

    def close_segment(self, e: Emp, end: pd.Timestamp):
        self.t["project_assignments"].append((e.id, e.seg_start, end, e.project, e.client, e.region, e.manager))

    # ------------------------------------------------------------------ exits
    def exit(self, e: Emp, notice: pd.Timestamp, reason: str, kind: str = "Resignation"):
        if notice <= DATA_END:
            lwd = notice + pd.Timedelta(days=30 if kind == "Resignation" else 14)
            self.t["exits"].append(dict(employee_id=e.id, notice_date=notice.date(), last_working_date=lwd.date(),
                                        exit_type=kind, exit_reason=reason))
            self.close_segment(e, lwd)
        else:
            self.close_segment(e, pd.NaT)
        self.active.remove(e)

    # ------------------------------------------------------------------ study pathway
    def plan_study(self, e: Emp, m: pd.Timestamp):
        r = self.rng
        e.applying = True
        e.attempts += 1
        idx = r.choice(len(DESTINATIONS), p=[d[3] for d in DESTINATIONS])
        dest, im, iday, _ = DESTINATIONS[idx]
        intake = pd.Timestamp(year=m.year + 1, month=im, day=iday)
        uses_hr = r.random() < 0.78

        def at(y, mo_lo, mo_hi):
            mo = int(r.integers(mo_lo, mo_hi + 1))
            yy = y if mo >= 9 else y + 1
            return pd.Timestamp(year=yy, month=mo, day=int(r.integers(1, 28)))

        if r.random() < 0.7:  # IELTS / GRE / PTE test days
            for _ in range(int(r.integers(1, 3))):
                test_day = at(m.year, 10, 12) if r.random() < 0.7 else at(m.year, 1, 1)
                e.planned.append((test_day, "leave1", None))
        if uses_hr:
            if r.random() < 0.65:
                e.planned.append((at(m.year, 11, 12) if r.random() < 0.6 else at(m.year, 1, 2), "hr", "Degree Attestation Support"))
            if r.random() < 0.75:
                e.planned.append((at(m.year, 12, 12) if r.random() < 0.4 else at(m.year, 1, 3), "hr", "Experience Letter"))
            if r.random() < 0.6:
                e.planned.append((at(m.year, 3, 6), "hr", r.choice(["Salary Certificate", "Bank Letter"])))
            if r.random() < 0.15:
                e.planned.append((at(m.year, 4, 6), "hr", "NOC"))
        success = r.random() < 0.6
        if success:
            e.planned_notice = intake - pd.Timedelta(days=int(r.integers(12, 50)))
            e.dest = dest
        else:
            e.planned_notice = None
            e.give_up = pd.Timestamp(year=m.year + 1, month=8, day=1)

    # ------------------------------------------------------------------ main loop
    def run(self):
        r = self.rng
        # initial cohort
        for _ in range(430):
            exp = float(np.clip(r.gamma(2.0, 2.2), 0.2, 18))
            tenure_y = min(exp, float(r.exponential(2.4)))
            join = SIM_START - pd.Timedelta(days=int(tenure_y * 365.25) + int(r.integers(1, 28)))
            self.hire(join, exp - tenure_y, initial=True)

        for m in MONTHS:
            nxt = m + pd.DateOffset(months=1)
            # hiring towards a growing headcount target (fresh grads land Oct-Jan)
            target = 430 + months_between(SIM_START, m) * 1.6
            n_hire = max(0, int(round(target - len(self.active)))) + int(r.poisson(1.0))
            for _ in range(n_hire):
                fresh_share = 0.65 if m.month in (10, 11, 12, 1) else 0.4
                exp = float(r.uniform(0, 1)) if r.random() < fresh_share else float(np.clip(r.gamma(2.0, 2.0), 1, 14))
                self.hire(m + pd.Timedelta(days=int(r.integers(0, 20))), exp)

            levels = {}
            for e in self.active:
                levels.setdefault(e.level, []).append(e.salary)
            med = {k: float(np.median(v)) for k, v in levels.items()}
            market_g = MARKET_GROWTH.get(m.year, 0.12)

            for e in list(self.active):
                if e.join >= nxt:
                    continue
                tenure = months_between(e.join, m)

                # ---- annual increments and promotions (July)
                if m.month == C.INCREMENT_MONTH and tenure >= 6 and e.rating is not None:
                    pct = max(0.0, INCREMENT_BY_RATING[e.rating] + r.normal(0, 0.015) + (0.03 if m.year in (2023, 2024) else 0))
                    promo = (e.rating >= 4 and months_between(e.grade_since, m) >= 24 and e.level < 5 and r.random() < 0.45)
                    if promo:
                        e.level += 1
                        e.grade_since = m
                        pct += 0.15
                        e.billing += 6
                    e.last_inc_pct = pct
                    if pct > 0.005:  # a 0% "increment" is not a raise
                        e.salary *= 1 + pct
                        self.comp(e, m, e.salary, "Promotion" if promo else "Annual Increment")
                        e.last_change = m
                # ---- occasional market adjustment for strong, underpaid people (January)
                if m.month == 1 and e.rating and e.rating >= 4 and e.salary < 0.92 * med.get(e.level, e.salary) and r.random() < 0.15:
                    e.salary *= 1.10
                    self.comp(e, m, e.salary, "Market Adjustment")
                    e.last_change = m
                    e.last_inc_pct = 0.10

                compa = e.salary / med.get(e.level, e.salary)
                fading = e.fade_onset is not None and tenure > e.fade_onset
                fade = min(2.0, e.fade_rate * (tenure - e.fade_onset) / 12) if fading else 0.0
                perf = e.perf_base - fade
                searching = e.search_left > 0

                # ---- project / manager changes
                if r.random() < 1 / 20 and tenure > 3:
                    self.close_segment(e, m - pd.Timedelta(days=1))
                    if r.random() < 0.12:
                        e.region = "Australia" if e.region == "US" else "US"
                    e.client = r.choice(US_CLIENTS if e.region == "US" else AU_CLIENTS)
                    e.project = f"P-{r.integers(100, 999)}"
                    e.project_start = m
                    if r.random() < 0.7:
                        e.manager = r.choice(MANAGERS)
                    e.seg_start = m
                elif r.random() < 0.006:
                    self.close_segment(e, m - pd.Timedelta(days=1))
                    e.manager = r.choice(MANAGERS)
                    e.seg_start = m
                mgr_recent = months_between(e.seg_start, m) < 6 and e.seg_start > e.join

                # ---- reviews (June annual, December mid-year)
                if m.month in (6, 12) and tenure >= 4:
                    e.prev_rating = e.rating
                    e.rating = int(np.clip(round(perf + r.normal(0, 0.45)), 1, 5))
                    self.t["performance_reviews"].append((e.id, m + pd.Timedelta(days=14), e.rating,
                                                          "Annual" if m.month == 6 else "Mid-Year"))

                # ---- timesheets
                total = float(np.clip(r.normal(176, 6), 140, 200))
                util = float(np.clip(0.66 + 0.07 * (perf - 3.3) - 0.03 * searching + r.normal(0, 0.04), 0.3, 0.97))
                ot = max(0.0, r.normal(8, 5) + (6 if e.region == "US" else 2) + (4 if e.level in (3, 4) else 0) - 3 * fading)
                fb = float(np.clip(perf + 0.3 + r.normal(0, 0.4), 1, 5)) if r.random() < 0.6 else np.nan
                rework = int(r.poisson(max(0.2, 1.6 - 0.7 * (perf - 3.3))))
                self.t["timesheets"].append((e.id, m, round(total, 1), round(total * util, 1), round(ot, 1),
                                             None if np.isnan(fb) else round(fb, 1), rework))

                # ---- leaves (baseline)
                if r.random() < 0.12:
                    self.t["leaves"].append((e.id, m + pd.Timedelta(days=int(r.integers(0, 25))), int(r.integers(2, 7)), "Annual"))
                if r.random() < 0.16:
                    self.t["leaves"].append((e.id, m + pd.Timedelta(days=int(r.integers(0, 27))), 1, r.choice(["Casual", "Sick"])))
                if r.random() < 0.004:
                    self.t["leaves"].append((e.id, m + pd.Timedelta(days=int(r.integers(0, 20))), int(r.integers(3, 15)), "Unpaid"))

                # ---- HR letters requested for non-study reasons (car loans, tourist visas, PEC renewals)
                if r.random() < 0.012:
                    self.t["hr_requests"].append((e.id, m + pd.Timedelta(days=int(r.integers(0, 27))), r.choice(["Salary Certificate", "Bank Letter"])))
                if r.random() < 0.003:
                    self.t["hr_requests"].append((e.id, m + pd.Timedelta(days=int(r.integers(0, 27))), "Experience Letter"))
                if r.random() < 0.002:
                    self.t["hr_requests"].append((e.id, m + pd.Timedelta(days=int(r.integers(0, 27))), "Degree Attestation Support"))
                if r.random() < 0.004:
                    self.t["hr_requests"].append((e.id, m + pd.Timedelta(days=int(r.integers(0, 27))), "Employment Verification"))

                # ---- engagement pulse (quarterly, ~75% response)
                if m.month in (3, 6, 9, 12) and tenure >= 2 and r.random() < 0.75:
                    eng = e.eng_base - 0.55 * searching - 0.4 * fading - 0.3 * (compa < 0.9) - 0.15 * e.applying + r.normal(0, 0.35)
                    gro = e.growth_base - 0.4 * (months_between(e.grade_since, m) > 30) - 0.35 * e.applying - 0.2 * searching + r.normal(0, 0.4)
                    self.t["engagement_surveys"].append((e.id, m + pd.Timedelta(days=20),
                                                         round(float(np.clip(eng, 1, 5)), 1), round(float(np.clip(gro, 1, 5)), 1)))

                # ---- emit planned study events falling in this month
                keep = []
                for (d, kind, payload) in e.planned:
                    if m <= d < nxt:
                        if kind == "hr":
                            self.t["hr_requests"].append((e.id, d, payload))
                        elif kind == "leave1":
                            self.t["leaves"].append((e.id, d, 1, r.choice(["Casual", "Annual"])))
                    elif d >= nxt:
                        keep.append((d, kind, payload))
                e.planned = keep

                # ---- exits ---------------------------------------------------------
                # 1) foreign study
                if e.planned_notice is not None and m <= e.planned_notice < nxt:
                    self.exit(e, e.planned_notice, "Higher Studies Abroad")
                    continue
                if e.applying and e.planned_notice is None and m >= getattr(e, "give_up", m + pd.DateOffset(years=5)):
                    e.applying = False
                    e.strength *= 0.6
                if (m.month == 9 and e.aspire and not e.applying and tenure >= 8 and e.attempts < 3
                        and r.random() < 0.6 * e.strength + 0.15):
                    self.plan_study(e, m)

                # 2) competitor
                if searching:
                    if r.random() < 0.6:
                        self.t["leaves"].append((e.id, m + pd.Timedelta(days=int(r.integers(0, 27))), 1, r.choice(["Casual", "Annual"])))
                    e.search_left -= 1
                    if e.search_left == 0:
                        if r.random() < 0.72:
                            self.exit(e, m + pd.Timedelta(days=int(r.integers(0, 27))), r.choice(
                                ["Better Offer", "Joined Competitor", "Better salary package"]))
                            continue
                else:
                    msi = months_between(e.last_change, m)
                    h = 0.0036 * DEMAND[e.discipline]
                    h *= float(np.exp(-5.0 * (compa - 1.0)))
                    h *= 1 + 0.07 * max(0.0, msi - 12)
                    h *= 1 + 0.55 * max(0.0, perf - 3.4)
                    h *= float(np.exp(-0.9 * (e.eng_base - 3.7)))
                    h *= 1 + 0.03 * max(0.0, ot - 15)
                    h *= 1.6 if mgr_recent else 1.0
                    h *= 0.35 if tenure < 9 else 1.2 if 24 <= tenure <= 60 else 1.0
                    if m.month in (7, 8, 9, 10) and tenure >= 12:
                        # a July increment below market inflation pushes people to look outside
                        h *= float(np.exp(np.clip(10 * (market_g - e.last_inc_pct), -0.5, 1.6)))
                    if m.month in (5, 6):
                        h *= 0.6  # waiting for appraisal/bonus
                    if e.applying:
                        h *= 0.3
                    if r.random() < min(h, 0.08):
                        e.search_left = int(r.integers(2, 5))

                # 3) performance fade
                if perf < 2.6:
                    e.low_perf_months += 1
                    hp = min(0.15, 0.025 + 0.02 * e.low_perf_months)
                    if r.random() < hp:
                        if r.random() < 0.6:
                            self.exit(e, m + pd.Timedelta(days=int(r.integers(0, 27))), "Performance - terminated", "Termination")
                        else:
                            self.exit(e, m + pd.Timedelta(days=int(r.integers(0, 27))), "Resigned after PIP")
                        continue
                else:
                    e.low_perf_months = 0

                # 4) personal / other
                if r.random() < 0.0016:
                    self.exit(e, m + pd.Timedelta(days=int(r.integers(0, 27))), r.choice(
                        ["Family relocation", "Health", "Government job", "Started own business", "Personal reasons"]))
                    continue

        # close open assignment segments
        for e in self.active:
            self.close_segment(e, pd.NaT)
        return self.tables()

    def tables(self) -> dict[str, pd.DataFrame]:
        t = self.t
        out = {
            "employees": pd.DataFrame(t["employees"]),
            "compensation": pd.DataFrame(t["compensation"], columns=["employee_id", "effective_date", "monthly_salary_pkr", "designation", "change_type"]),
            "performance_reviews": pd.DataFrame(t["performance_reviews"], columns=["employee_id", "review_date", "rating", "cycle"]),
            "timesheets": pd.DataFrame(t["timesheets"], columns=["employee_id", "month", "total_hours", "billable_hours", "overtime_hours", "client_feedback_score", "rework_items"]),
            "hr_requests": pd.DataFrame(t["hr_requests"], columns=["employee_id", "request_date", "request_type"]),
            "leaves": pd.DataFrame(t["leaves"], columns=["employee_id", "start_date", "days", "leave_type"]),
            "engagement_surveys": pd.DataFrame(t["engagement_surveys"], columns=["employee_id", "survey_date", "engagement_score", "growth_score"]),
            "project_assignments": pd.DataFrame(t["project_assignments"], columns=["employee_id", "start_date", "end_date", "project_code", "client_name", "client_region", "manager_id"]),
            "exits": pd.DataFrame(t["exits"]),
        }
        # nothing recorded after the data cut-off
        cut = {"compensation": "effective_date", "performance_reviews": "review_date", "timesheets": "month",
               "hr_requests": "request_date", "leaves": "start_date", "engagement_surveys": "survey_date"}
        for name, col in cut.items():
            df = out[name]
            df[col] = pd.to_datetime(df[col])
            out[name] = df[df[col] <= DATA_END].sort_values(["employee_id", col]).reset_index(drop=True)
        pa = out["project_assignments"]
        pa["start_date"] = pd.to_datetime(pa["start_date"])
        pa["end_date"] = pd.to_datetime(pa["end_date"])
        pa = pa[pa["start_date"] <= DATA_END]
        pa.loc[pa["end_date"] > DATA_END, "end_date"] = pd.NaT
        out["project_assignments"] = pa.sort_values(["employee_id", "start_date"]).reset_index(drop=True)
        return out


def generate(out_dir: Path, seed: int = 7) -> dict[str, pd.DataFrame]:
    tables = Simulator(seed).run()
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(out_dir / f"{name}.csv", index=False, date_format="%Y-%m-%d")
    return tables


def main():
    ap = argparse.ArgumentParser(description="Generate synthetic HR data in the template format.")
    ap.add_argument("--out", type=Path, default=C.PROJECT_ROOT / "data" / "synthetic")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    tables = generate(a.out, a.seed)
    for k, v in tables.items():
        print(f"{k:22s} {len(v):>7,d} rows")


if __name__ == "__main__":
    main()
