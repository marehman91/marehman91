# Retention Radar

An early-warning agent for engineer resignations at a civil-engineering services firm whose engineers are deployed with US and Australian clients.

Every month it answers four questions for the HR head and CEO:

1. **Who** may resign in the next 3, 6 and 12 months, and in the July–October season?
2. **Why**: foreign study, a competitor offer, a performance slide, or personal reasons? Each flag lists its top three reasons in plain language, with the person's own numbers.
3. **What to do**: a playbook action for each reason, plus guidance on how to protect any training investment.
4. **Can we trust it?** A backtest on last season, a rolling 90-day check, and a fairness audit run on every execution.

> The data in `data/synthetic` and `reports/` is **synthetic**. Every name, salary and number in it is generated.

## Quick start

```bash
pip install -r requirements.txt

# 1) Demo on synthetic data (about 1 minute)
python run_agent.py --demo

# 2) Your data: fill in the Excel template, then
python run_agent.py --data data_template/Retention_Radar_Data_Template.xlsx
```

Outputs go to `reports/`:

| File | What it is |
|---|---|
| `retention_radar.html` | CEO dashboard: brief, backtest proof, seasonality, watchlist, drivers, fairness |
| `watchlist_<date>.csv` | Everyone's risk, main reason, top three "why", action and investment guidance |
| `results.json` | Everything above in machine-readable form, for audit and for the chat agent |

**Roman Urdu:** `data_template/Retention_Radar_Data_Template.xlsx` mein apna HR data dalein. Har table ki alag sheet hai, aur sirf `employees`, `exits` aur `compensation` zaroori hain. Jo log company chhor chuke hain un ka data zaroor dalein, kyunke agent unhi se seekhta hai. Phir `python run_agent.py --data <file>` chalayein aur `reports/retention_radar.html` kholein.

## How it works

```
HR tables ──► monthly signals (29 per engineer, past data only)
          ──► 12 models, one per horizon (1–12 months), each predicting
              Stay / Foreign Study / Competitor / Performance / Personal
          ──► cumulative risk curve per person + workforce forecast per month
          ──► reasons (signal-group occlusion) ──► playbook action
          ──► backtest + rolling 90-day check + fairness audit ──► dashboard
```

* **Signals**: tenure, experience, career level, pay vs peers (compa-ratio), raise history, time in grade, rating and its trend, utilisation/rework/client-feedback trends, overtime and shift (US night vs Australia early morning), study-type HR letters (experience letter, salary/bank letter, degree attestation, NOC), single-day leave pattern, engagement survey, manager and project changes, skill demand, and calendar month.
* **Model**: competing-risks landmarking with gradient-boosted trees (scikit-learn). A separate model per horizon captures the season: a study-type letter in January means something different for July than for next January.
* **Explanations**: for each signal group, the person's values are reset to the company norm and the risk is re-scored. The groups that lower the risk most become the "why".
* **No future leakage**: every signal for month *t* uses only records dated before *t*. A unit test checks this (`tests/test_pipeline.py`).

## Compliance by design

* Gender, date of birth, marital status, religion, CNIC and name are **never model inputs**. They are kept only for the fairness audit.
* The fairness audit compares flag rates (4/5ths rule), actual exit rates and precision for each group, and runs a proxy test that asks whether the model's inputs can reconstruct a protected attribute.
* The agent supports decisions and never makes them. It never blocks a raise, promotion or training; managers and HR decide. For performance flags, the playbook requires a diagnosis and an HR review before any formal step.
* Only data HR already holds. No monitoring of personal social media or LinkedIn.
* Restrict the dashboard to the HR head and CEO. Keep `results.json` from each run as the audit trail.

## Configure for your company

Edit `src/attrition_agent/config.py`:

* `DESIGNATION_LEVELS`: map your job titles to career levels 1–5.
* `INCREMENT_MONTH`, `SEASON_MONTHS`: your appraisal month and resignation season.
* `TIER_HIGH`, `TIER_MEDIUM`: risk cut-offs.
* `DEFAULT_BILLING_USD`, `VACANCY_IMPACT_MONTHS`: assumptions behind the billing-impact figures.
* `REASON_KEYWORDS`: how free-text exit reasons map to the four categories.

## Project layout

```
run_agent.py                      CLI entry point
src/attrition_agent/
  config.py                       business settings
  data_io.py                      load + validate the Excel template / CSV folder
  features.py                     monthly signals (no future leakage)
  model.py                        competing-risks landmark model
  explain.py                      reasons + retention playbook
  fairness.py                     fairness and proxy audit
  pipeline.py                     backtest, rolling check, live scoring
  report.py                       dashboard HTML
  generate_synthetic.py           synthetic data in the template format
  template.py                     builds the Excel template
data_template/                    Excel template for HR
tests/                            leakage, privacy, template round-trip tests
```

## Roadmap

* **Phase 2:** a chat agent on top of `results.json`, for questions like "Which Australian-client engineers are at risk before March?" and an auto-drafted monthly CEO brief.
* Scheduled monthly run that emails the HR head a short summary and the link.
* Market salary benchmarks to replace the internal compa-ratio.
