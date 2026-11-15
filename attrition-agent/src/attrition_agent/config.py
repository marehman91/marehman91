"""Business settings. Change these to match your company; the code reads them from here."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Forecast horizons in months (1..12). One model is trained per horizon (landmarking).
HORIZONS = list(range(1, 13))

# The resignation season and the month annual increments take effect (PK fiscal year starts July).
SEASON_MONTHS = (7, 8, 9, 10)
INCREMENT_MONTH = 7

# Exit reasons the model predicts. Anything else in your data maps to "Personal/Other".
REASONS = ["Foreign Study", "Competitor", "Performance", "Personal/Other"]
REASON_SHORT = {
    "Foreign Study": "Study",
    "Competitor": "Competitor",
    "Performance": "Performance",
    "Personal/Other": "Other",
}
# Free-text exit reasons in HR files are mapped with these keywords (lower-case "contains" match).
REASON_KEYWORDS = {
    "Foreign Study": ["study", "studies", "education", "abroad", "masters", "ms ", "phd", "university", "admission"],
    "Competitor": ["competitor", "better offer", "better opportunity", "salary", "package", "another company", "job offer"],
    "Performance": ["performance", "pip", "terminat", "non-performance", "probation"],
}

# Designation -> career level. Add your own titles here.
DESIGNATION_LEVELS = {
    "Trainee Engineer": 1,
    "Junior Engineer": 1,
    "Design Engineer": 2,
    "Engineer": 2,
    "Senior Engineer": 3,
    "Senior Design Engineer": 3,
    "Lead Engineer": 4,
    "Team Lead": 4,
    "Project Manager": 5,
    "Senior Project Manager": 5,
}

# Used when employees.billing_rate_usd is empty.
DEFAULT_BILLING_USD = {1: 18, 2: 24, 3: 32, 4: 40, 5: 48}
BILLABLE_HOURS_PER_MONTH = 160
# Vacancy + ramp-up of a replacement, expressed as months of lost billing.
VACANCY_IMPACT_MONTHS = 2.5

# Risk tiers on the 12-month probability of resigning.
TIER_HIGH = 0.40
TIER_MEDIUM = 0.20

# HR letter types that people typically need for admissions and student visas.
STUDY_DOC_TYPES = [
    "Experience Letter",
    "Salary Certificate",
    "Bank Letter",
    "Degree Attestation Support",
    "NOC",
]

# Never used as model inputs. Kept only for the fairness audit (and dropped if absent).
PROTECTED_COLUMNS = ["gender", "date_of_birth", "marital_status", "religion", "cnic", "full_name"]

# Fairness: 4/5ths rule on flag rates between groups.
DISPARATE_IMPACT_FLOOR = 0.80
