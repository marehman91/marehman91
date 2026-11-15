"""Render the CEO dashboard as one self-contained HTML file (no server, no external data)."""

from __future__ import annotations

import json

import pandas as pd

from . import config as C


def _brief(r: dict) -> list[str]:
    k, b, m = r["kpis"], r["backtest"], r["meta"]
    asof = pd.Timestamp(m["asof"]).strftime("%d %b %Y")
    hb = k["high_by_reason"]
    bt_asof = pd.Timestamp(b["asof"]).strftime("%d %b %Y")
    win_end = pd.Timestamp(b["window_end"]).strftime("%b %Y")
    lines = [
        f"As of {asof} we have {k['headcount']} engineers on active projects. The agent expects about "
        f"{k['expected_12m']:.0f} resignations in the next 12 months ({k['expected_12m_rate']:.0%} of headcount), "
        f"{k['expected_season']:.0f} of them in the {k['season_label']} season.",
        f"{k['tiers']['High']} engineers are high risk right now: {hb['Study']} likely to leave for foreign study, "
        f"{hb['Competitor']} at risk of a competitor offer and {hb['Performance']} on a performance slide. "
        f"Replacing all high-risk engineers would cost about ${k['high_impact_usd'] / 1e3:,.0f}k in lost billing.",
        f"Proof from last season: on {bt_asof} the agent ranked everyone using only data available that day. "
        f"Its top-{b['list_size']} list contained {b['caught']} of the {b['left']} engineers who resigned by {win_end}, "
        f"and named the right reason for {b['reason_accuracy']:.0%} of them.",
    ]
    return lines


def render(result: dict) -> str:
    data = json.dumps(result, ensure_ascii=True, default=str).replace("</", "<\\/")
    brief = "".join(f"<p>{line}</p>" for line in _brief(result))
    synthetic_banner = (
        '<p class="demo-banner" role="note"><strong>Synthetic demo data.</strong> Every name, salary and number on this page is '
        "generated. Your HR data replaces it when you run the agent on the filled-in template.</p>"
        if result["meta"]["synthetic"] else ""
    )
    return (TEMPLATE
            .replace("__DATA__", data)
            .replace("__BRIEF__", brief)
            .replace("__BANNER__", synthetic_banner)
            .replace("__ASOF__", pd.Timestamp(result["meta"]["asof"]).strftime("%d %b %Y").upper())
            .replace("__DATAEND__", pd.Timestamp(result["meta"]["data_end"]).strftime("%d %b %Y"))
            .replace("__SOURCE__", "SYNTHETIC" if result["meta"]["synthetic"] else "HRIS EXPORT")
            .replace("__TIER_HIGH__", f"{C.TIER_HIGH:.0%}")
            .replace("__TIER_MED__", f"{C.TIER_MEDIUM:.0%}"))


TEMPLATE = r"""<meta charset="utf-8">
<title>Retention Radar</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
/* Layout: an engineering drawing sheet. A title block heads the page, then numbered "sheets"
   (sections) stack in one column; colour is reserved for data (exit reasons) and status (risk tiers). */
:root {
  --bg: #f3f5f4; --sheet: #ffffff; --ink: #101614; --ink-2: #47504c; --muted: #6f7975;
  --line: #dfe4e1; --line-strong: #c3cbc7; --band: rgba(16, 22, 20, 0.05); --hover: rgba(16, 22, 20, 0.04);
  --s-study: #2a78d6; --s-comp: #eb6834; --s-perf: #1baf7a; --s-other: #a3aaa7; --neutral-bar: #b5c0cc;
  --crit: #d03b3b; --serious: #ec835a; --good: #0ca30c; --warn: #fab219;
  --on-bg: #101614; --on-fg: #ffffff; --banner-bg: #fff6e0; --banner-line: #f0d48a;
  --font-ui: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-head: "IBM Plex Sans Condensed", "IBM Plex Sans", system-ui, sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --r: 6px;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0e1110; --sheet: #161a19; --ink: #eef1ef; --ink-2: #b9c2be; --muted: #8b9591;
    --line: #29302d; --line-strong: #3b4441; --band: rgba(255, 255, 255, 0.055); --hover: rgba(255, 255, 255, 0.04);
    --s-study: #3987e5; --s-comp: #d95926; --s-perf: #199e70; --s-other: #6c7471; --neutral-bar: #4b5a6b;
    --on-bg: #eef1ef; --on-fg: #101614; --banner-bg: #2a2416; --banner-line: #5c4b1f;
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: #0e1110; --sheet: #161a19; --ink: #eef1ef; --ink-2: #b9c2be; --muted: #8b9591;
  --line: #29302d; --line-strong: #3b4441; --band: rgba(255, 255, 255, 0.055); --hover: rgba(255, 255, 255, 0.04);
  --s-study: #3987e5; --s-comp: #d95926; --s-perf: #199e70; --s-other: #6c7471; --neutral-bar: #4b5a6b;
  --on-bg: #eef1ef; --on-fg: #101614; --banner-bg: #2a2416; --banner-line: #5c4b1f;
  color-scheme: dark;
}
* { box-sizing: border-box; }
body { background: var(--bg); color: var(--ink); font-family: var(--font-ui); font-size: 15px; line-height: 1.5; }
.wrap { max-width: 1180px; margin: 0 auto; padding-block: 28px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 28px; }
h1, h2, h3 { font-family: var(--font-head); font-weight: 600; text-wrap: balance; margin: 0; letter-spacing: 0.005em; }
h1 { font-size: clamp(30px, 4.6vw, 46px); line-height: 1.05; }
h2 { font-size: 24px; line-height: 1.2; }
h3 { font-size: 17px; line-height: 1.3; }
p { margin: 0; overflow-wrap: anywhere; }
.mono { font-family: var(--font-mono); }
.label { font-family: var(--font-mono); font-size: 11.5px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }
.muted { color: var(--muted); }
.num { font-variant-numeric: tabular-nums; }
a { color: inherit; }
:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }

/* ---- title block */
.titleblock { background: var(--sheet); border: 1px solid var(--line-strong); border-radius: var(--r); display: grid;
  grid-template-columns: minmax(0, 1fr) auto; }
.tb-main { padding: 22px 24px; display: grid; gap: 10px; min-width: 0; }
.tb-main .sub { color: var(--ink-2); max-width: 62ch; }
.tb-cells { display: grid; grid-template-columns: repeat(2, minmax(130px, auto)); border-left: 1px solid var(--line-strong); }
.tb-cell { padding: 10px 16px; border-bottom: 1px solid var(--line); display: grid; gap: 2px; align-content: start; }
.tb-cell:nth-child(odd) { border-right: 1px solid var(--line); }
.tb-cell:nth-last-child(-n+2) { border-bottom: 0; }
.tb-cell b { font-family: var(--font-mono); font-weight: 500; font-size: 13px; }
.demo-banner { background: var(--banner-bg); border: 1px solid var(--banner-line); border-radius: var(--r); padding: 10px 14px; font-size: 14px; }

/* ---- sections ("sheets") */
.sheet { display: grid; gap: 16px; }
.sheet-head { display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; border-bottom: 1px solid var(--line-strong); padding-bottom: 8px; }
.sheet-head .label { min-width: 3.2em; }
.sheet-head p { color: var(--ink-2); flex-basis: 100%; max-width: 75ch; }
.card { background: var(--sheet); border: 1px solid var(--line); border-radius: var(--r); padding: 18px; min-width: 0; }

/* ---- brief + KPIs */
.brief { display: grid; gap: 10px; font-size: 16px; max-width: 78ch; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }
.kpi { background: var(--sheet); border: 1px solid var(--line); border-radius: var(--r); padding: 14px 16px; display: grid; gap: 4px; align-content: start; }
.kpi .v { font-family: var(--font-head); font-size: 32px; font-weight: 600; line-height: 1.1; }
.kpi .d { font-size: 13px; color: var(--ink-2); }
.split { display: flex; gap: 10px; flex-wrap: wrap; font-size: 13px; color: var(--ink-2); }
.sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: baseline; }
.sw.study { background: var(--s-study); } .sw.comp { background: var(--s-comp); } .sw.perf { background: var(--s-perf); } .sw.other { background: var(--s-other); }
.sw.actual { background: var(--neutral-bar); } .sw.line { height: 2px; width: 14px; background: var(--ink); vertical-align: middle; }
.sw.fc { background: repeating-linear-gradient(135deg, var(--s-study) 0 2px, transparent 2px 5px); outline: 1px solid var(--s-study); }
.sw.band { background: var(--band); outline: 1px solid var(--line-strong); }

/* ---- proof */
.proof { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
.stat { display: grid; gap: 2px; padding: 14px 16px; border-left: 3px solid var(--line-strong); background: var(--sheet); border-radius: 0 var(--r) var(--r) 0; }
.stat .v { font-family: var(--font-head); font-size: 28px; font-weight: 600; }
.stat .d { font-size: 13px; color: var(--ink-2); }
.grid-2 { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: 16px; }
.examples { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }
.ex { background: var(--sheet); border: 1px solid var(--line); border-radius: var(--r); padding: 14px; display: grid; gap: 8px; align-content: start; }
.ex .who { display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap; }
.ex ul { margin: 0; padding-left: 18px; color: var(--ink-2); font-size: 13.5px; }
.ex .out { font-size: 13.5px; border-top: 1px dashed var(--line-strong); padding-top: 8px; }
.reasonlist { display: grid; gap: 10px; }
.rrow { display: grid; grid-template-columns: 110px minmax(0, 1fr) 62px; gap: 10px; align-items: center; font-size: 14px; }
.track { height: 10px; background: var(--band); border-radius: 3px; position: relative; overflow: hidden; }
.track > span { position: absolute; inset: 0 auto 0 0; border-radius: 3px; }

/* ---- charts */
.chart { position: relative; overflow-x: auto; }
.chart svg { display: block; }
.legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px; color: var(--ink-2); }
.axis text, .tick text { fill: var(--muted); font-family: var(--font-mono); font-size: 10.5px; }
.grid line { stroke: var(--line); stroke-width: 1; }
.baseline { stroke: var(--line-strong); stroke-width: 1; }
.f-study { fill: var(--s-study); } .f-comp { fill: var(--s-comp); } .f-perf { fill: var(--s-perf); } .f-other { fill: var(--s-other); }
.f-actual { fill: var(--neutral-bar); }
.band { fill: var(--band); }
.fc { fill-opacity: 0.42; }
.divider { stroke: var(--ink-2); stroke-dasharray: 3 3; }
.ann { fill: var(--ink-2); font-family: var(--font-mono); font-size: 10.5px; }
.line-exp { fill: none; stroke: var(--ink); stroke-width: 2; }
.dot-exp { fill: var(--ink); stroke: var(--sheet); stroke-width: 2; }
.hit { fill: transparent; cursor: crosshair; }
.hit:hover { fill: var(--hover); }
.tip { position: absolute; pointer-events: none; background: var(--sheet); border: 1px solid var(--line-strong); border-radius: var(--r);
  padding: 8px 10px; font-size: 12.5px; box-shadow: 0 4px 16px rgba(0,0,0,0.12); min-width: 150px; z-index: 5; }
.tip .t { font-weight: 600; margin-bottom: 4px; }
.tip .r { display: flex; justify-content: space-between; gap: 12px; font-variant-numeric: tabular-nums; }

/* ---- study calendar */
.cal { display: grid; grid-template-columns: 150px repeat(14, minmax(34px, 1fr)); font-size: 12.5px; min-width: 700px; }
.cal .mh { font-family: var(--font-mono); font-size: 10.5px; color: var(--muted); text-align: center; padding: 4px 0; border-bottom: 1px solid var(--line-strong); }
.cal .mh.season { color: var(--ink); font-weight: 500; }
.cal .rl { padding: 6px 8px 6px 0; color: var(--ink-2); border-bottom: 1px solid var(--line); }
.cal .cell { border-bottom: 1px solid var(--line); position: relative; }
.cal .bar { position: absolute; top: 7px; bottom: 7px; border-radius: 3px; background: var(--s-study); opacity: 0.3; }
.cal .bar.strong { opacity: 0.9; }
.cal .bar.agent { background: var(--ink); opacity: 1; }
.cal .bar.exit { background: var(--crit); opacity: 0.85; }

/* ---- watchlist */
.controls { display: flex; gap: 10px 18px; flex-wrap: wrap; align-items: center; }
.chips { display: flex; gap: 6px; flex-wrap: wrap; }
.chip { font: inherit; font-size: 13px; border: 1px solid var(--line-strong); background: var(--sheet); color: var(--ink); border-radius: 999px;
  padding: 4px 12px; cursor: pointer; }
.chip[aria-pressed="true"] { background: var(--on-bg); color: var(--on-fg); border-color: var(--on-bg); }
.chip:hover { border-color: var(--ink-2); }
select, input[type="search"] { font: inherit; font-size: 13.5px; color: var(--ink); background: var(--sheet); border: 1px solid var(--line-strong);
  border-radius: var(--r); padding: 5px 10px; }
input[type="search"] { min-width: 0; width: 220px; max-width: 100%; }
.tablewrap { overflow-x: auto; border: 1px solid var(--line); border-radius: var(--r); background: var(--sheet); }
table { border-collapse: collapse; width: 100%; font-size: 13.5px; }
.watch { min-width: 980px; }
th { text-align: left; font-family: var(--font-mono); font-weight: 500; font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--muted); padding: 10px 12px; border-bottom: 1px solid var(--line-strong); white-space: nowrap; }
th button { all: unset; cursor: pointer; }
th button:focus-visible { outline: 2px solid var(--ink); }
td { padding: 10px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }
tr.row { cursor: pointer; }
tr.row:hover td { background: var(--hover); }
tr.row[aria-expanded="true"] td { background: var(--hover); border-bottom-color: transparent; }
.who b { font-weight: 600; }
.who .id { font-family: var(--font-mono); font-size: 11.5px; color: var(--muted); }
.risk { display: grid; gap: 4px; min-width: 120px; }
.riskline { display: flex; align-items: center; gap: 8px; }
.minibar { height: 6px; background: var(--band); border-radius: 3px; overflow: hidden; }
.minibar span { display: block; height: 100%; background: var(--ink-2); }
.pill { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 500; border: 1px solid var(--line-strong);
  border-radius: 999px; padding: 1px 8px 1px 6px; white-space: nowrap; }
.pill svg { width: 10px; height: 10px; }
.pill.high svg { fill: var(--crit); } .pill.medium svg { fill: var(--serious); } .pill.low svg { fill: var(--good); }
.pill.pass svg { fill: var(--good); } .pill.review svg { fill: var(--warn); } .pill.fail svg { fill: var(--crit); } .pill.na svg { fill: var(--muted); }
.detail td { padding: 4px 12px 18px; }
.dgrid { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr) minmax(0, 1.6fr); gap: 20px; }
.dgrid h4 { margin: 0 0 6px; font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); font-weight: 500; }
.dgrid ol, .dgrid ul { margin: 0; padding-left: 18px; display: grid; gap: 4px; }
.kv { display: grid; grid-template-columns: auto 1fr; gap: 2px 12px; font-size: 13px; }
.kv dt { color: var(--muted); } .kv dd { margin: 0; font-variant-numeric: tabular-nums; }
.empty { padding: 28px; text-align: center; color: var(--muted); }
.count { font-size: 13px; color: var(--muted); }

/* ---- drivers */
.drivers { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 12px; }
.drv { display: grid; gap: 8px; align-content: start; }
.drow { display: grid; grid-template-columns: minmax(0, 1fr) 90px 26px; gap: 8px; align-items: center; font-size: 13.5px; }

/* ---- fairness */
.fair { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px; }
.fair table td, .fair table th { padding: 6px 8px; }
.fair .note { font-size: 13px; color: var(--ink-2); }
.chiplist { display: flex; gap: 6px; flex-wrap: wrap; }
.tag { font-family: var(--font-mono); font-size: 12px; border: 1px dashed var(--line-strong); border-radius: 4px; padding: 1px 7px; color: var(--ink-2); text-decoration: line-through; }
.checks { margin: 0; padding: 0; list-style: none; display: grid; gap: 8px; }
.checks li { display: grid; grid-template-columns: 18px minmax(0, 1fr); gap: 8px; font-size: 14px; }
.checks svg { width: 16px; height: 16px; margin-top: 3px; fill: var(--good); }

/* ---- data + method */
.cols-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; }
.plain { margin: 0; padding-left: 18px; display: grid; gap: 6px; color: var(--ink-2); }
.datatable td, .datatable th { padding: 6px 10px; }
footer { color: var(--muted); font-size: 12.5px; border-top: 1px solid var(--line-strong); padding-top: 12px; }

@media (max-width: 760px) {
  .titleblock { grid-template-columns: 1fr; }
  .tb-cells { border-left: 0; border-top: 1px solid var(--line-strong); }
  .grid-2 { grid-template-columns: 1fr; }
  .dgrid { grid-template-columns: 1fr; }
  .kpi .v { font-size: 28px; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
</style>

<div class="wrap">
  <header class="titleblock">
    <div class="tb-main">
      <span class="label">Early-warning agent &middot; civil engineering delivery</span>
      <h1>Retention Radar</h1>
      <p class="sub">Who might resign in the next 12 months, why (foreign study, a competitor offer or a performance slide), and what to do about it before the July&ndash;October season.</p>
    </div>
    <div class="tb-cells">
      <div class="tb-cell"><span class="label">As of</span><b>__ASOF__</b></div>
      <div class="tb-cell"><span class="label">Data to</span><b>__DATAEND__</b></div>
      <div class="tb-cell"><span class="label">Source</span><b>__SOURCE__</b></div>
      <div class="tb-cell"><span class="label">Rev</span><b>0.1 DEMO</b></div>
      <div class="tb-cell"><span class="label">Prepared for</span><b>CEO OFFICE</b></div>
      <div class="tb-cell"><span class="label">Access</span><b>HR HEAD + CEO</b></div>
    </div>
  </header>
  __BANNER__

  <section class="sheet" aria-labelledby="s1">
    <div class="sheet-head"><span class="label">Sheet 01</span><h2 id="s1">This month's brief</h2></div>
    <div class="brief">__BRIEF__</div>
    <div class="kpis" id="kpis"></div>
  </section>

  <section class="sheet" aria-labelledby="s2">
    <div class="sheet-head"><span class="label">Sheet 02</span><h2 id="s2">Would it have worked last season?</h2>
      <p id="proof-lead"></p></div>
    <div class="proof" id="proof"></div>
    <div class="grid-2">
      <div class="card">
        <div class="legend" style="margin-bottom:10px"><span><i class="sw actual"></i>Actual resignations</span><span><i class="sw line"></i>Agent's forecast, made on day one</span></div>
        <div class="chart" id="bt-chart"></div>
      </div>
      <div class="card">
        <h3 style="margin-bottom:4px">Caught on the list, by real exit reason</h3>
        <p class="muted" style="font-size:13px;margin-bottom:12px" id="bt-reason-note"></p>
        <div class="reasonlist" id="bt-reasons"></div>
        <h3 style="margin:18px 0 4px">90-day early warning</h3>
        <p class="muted" style="font-size:13px;margin-bottom:12px" id="roll-note"></p>
        <div class="reasonlist" id="roll-reasons"></div>
      </div>
    </div>
    <h3>What the agent said on day one, and what happened</h3>
    <div class="examples" id="examples"></div>
  </section>

  <section class="sheet" aria-labelledby="s3">
    <div class="sheet-head"><span class="label">Sheet 03</span><h2 id="s3">The July&ndash;October pattern</h2>
      <p>Resignations by month and reason, with the agent's forecast for the next 12 months. Shaded columns are the July&ndash;October season.</p></div>
    <div class="card">
      <div class="legend" style="margin-bottom:10px">
        <span><i class="sw study"></i>Foreign study</span><span><i class="sw comp"></i>Competitor</span><span><i class="sw perf"></i>Performance</span><span><i class="sw other"></i>Personal / other</span>
        <span><i class="sw fc"></i>Forecast (lighter)</span><span><i class="sw band"></i>Jul&ndash;Oct season</span>
      </div>
      <div class="chart" id="season-chart"></div>
    </div>
    <div class="card">
      <h3>Why the agent has to flag study leavers in December&ndash;March, not June</h3>
      <p class="muted" style="font-size:13.5px;margin:4px 0 12px">The decision to study abroad is made 6&ndash;9 months before the resignation letter. By June the admission letter is already in hand.</p>
      <div style="overflow-x:auto"><div class="cal" id="cal"></div></div>
    </div>
  </section>

  <section class="sheet" aria-labelledby="s4">
    <div class="sheet-head"><span class="label">Sheet 04</span><h2 id="s4">Watchlist</h2>
      <p>Everyone ranked by their chance of resigning in the next 12 months. High is __TIER_HIGH__ or more, Medium __TIER_MED__&ndash;__TIER_HIGH__. Select a row for the full reasoning, the action plan and investment guidance.</p></div>
    <div class="controls">
      <div class="chips" id="tier-chips" role="group" aria-label="Risk tier"></div>
      <div class="chips" id="reason-chips" role="group" aria-label="Main reason"></div>
      <select id="region" aria-label="Client region"><option value="All">All clients</option><option value="US">US clients</option><option value="Australia">Australian clients</option></select>
      <input type="search" id="q" placeholder="Search name, ID, discipline" aria-label="Search">
      <span class="count" id="count"></span>
    </div>
    <div class="tablewrap">
      <table class="watch">
        <thead><tr>
          <th><button data-sort="name">Engineer</button></th><th>Client &middot; discipline</th><th><button data-sort="tenure_years">Tenure</button></th>
          <th><button data-sort="risk12">12-month risk &darr;</button></th><th>Main reason</th><th>Top reason why</th><th>Recommended action</th>
        </tr></thead>
        <tbody id="rows"></tbody>
      </table>
    </div>
  </section>

  <section class="sheet" aria-labelledby="s5">
    <div class="sheet-head"><span class="label">Sheet 05</span><h2 id="s5">What drives each type of exit</h2>
      <p>How often each signal appears among the top three reasons for flagged engineers. This is where policy changes pay off.</p></div>
    <div class="drivers" id="drivers"></div>
  </section>

  <section class="sheet" aria-labelledby="s6">
    <div class="sheet-head"><span class="label">Sheet 06</span><h2 id="s6">Fairness and compliance</h2>
      <p id="fair-lead"></p></div>
    <div class="cols-2">
      <div class="card" style="display:grid;gap:10px;align-content:start">
        <h3>Never used to score anyone</h3>
        <div class="chiplist" id="excluded"></div>
        <p class="note muted" style="font-size:13px">Kept only to run the checks on this sheet. If a column is missing from your data, its check is skipped.</p>
      </div>
      <div class="card" style="display:grid;gap:10px;align-content:start">
        <h3>Guardrails built into the agent</h3>
        <ul class="checks">
          <li><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6.2 11.6 2.6 8l1.1-1.1 2.5 2.5 6.1-6.1L13.4 4.4z"/></svg><span>Decision support only. The agent never stops a promotion, raise or training; a manager and HR decide.</span></li>
          <li><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6.2 11.6 2.6 8l1.1-1.1 2.5 2.5 6.1-6.1L13.4 4.4z"/></svg><span>Every flag shows its reasons in plain language, so it can be challenged.</span></li>
          <li><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6.2 11.6 2.6 8l1.1-1.1 2.5 2.5 6.1-6.1L13.4 4.4z"/></svg><span>Only HR records the company already holds. No personal social media or LinkedIn monitoring.</span></li>
          <li><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6.2 11.6 2.6 8l1.1-1.1 2.5 2.5 6.1-6.1L13.4 4.4z"/></svg><span>Access limited to the HR head and CEO; each run is saved with its inputs for audit.</span></li>
          <li><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6.2 11.6 2.6 8l1.1-1.1 2.5 2.5 6.1-6.1L13.4 4.4z"/></svg><span>Bias checks (below) rerun automatically every month on real outcomes.</span></li>
        </ul>
      </div>
    </div>
    <div class="fair" id="fair"></div>
    <div class="card" style="display:grid;gap:8px">
      <h3>Proxy test: can the model's inputs guess a protected attribute?</h3>
      <div class="tablewrap" style="border:0"><table id="proxy"></table></div>
    </div>
  </section>

  <section class="sheet" aria-labelledby="s7">
    <div class="sheet-head"><span class="label">Sheet 07</span><h2 id="s7">Data and method</h2></div>
    <div class="cols-2">
      <div class="card" style="display:grid;gap:10px;align-content:start">
        <h3>Data this run used</h3>
        <div class="tablewrap" style="border:0"><table class="datatable" id="datatable"></table></div>
        <p class="muted" style="font-size:13px">To run on your data, fill in <span class="mono">data_template/Retention_Radar_Data_Template.xlsx</span> and run <span class="mono">python run_agent.py --data &lt;file&gt;</span>. Only <i>employees</i>, <i>exits</i> and <i>compensation</i> are required; every extra table sharpens the signals.</p>
      </div>
      <div class="card" style="display:grid;gap:10px;align-content:start">
        <h3>How it works</h3>
        <ul class="plain">
          <li>Every month, 29 signals are computed for each engineer from records dated before that month only.</li>
          <li>Twelve models (one per horizon, 1&ndash;12 months) learn which signal patterns came before each type of resignation in past years.</li>
          <li>Each flag is explained by resetting one signal group at a time to the company norm and measuring how much the risk falls.</li>
          <li>Backtest: models trained only on data before the test date, then compared with what really happened.</li>
          <li>Billing impact assumes <span id="impact-assumption"></span>.</li>
        </ul>
        <h3>Limits to keep in mind</h3>
        <ul class="plain">
          <li>A risk score is a probability, not a verdict; many High-risk people will stay.</li>
          <li>Personal reasons (family, health, relocation) leave little trace in HR data and are hard to predict.</li>
          <li>Competitor exits are clearer 1&ndash;3 months ahead than 9 months ahead.</li>
          <li>Accuracy depends on history: aim for 2&ndash;3 years and 100+ past exits with reasons recorded.</li>
        </ul>
      </div>
    </div>
  </section>
  <footer id="footer"></footer>
</div>

<script type="application/json" id="radar-data">__DATA__</script>
<script>
(function () {
  const D = JSON.parse(document.getElementById("radar-data").textContent);
  const REASONS = D.meta.reasons;
  const SHORT = D.meta.reason_short;
  const CLS = { "Foreign Study": "study", "Competitor": "comp", "Performance": "perf", "Personal/Other": "other" };
  const NICE = { "Foreign Study": "Foreign study", "Competitor": "Competitor", "Performance": "Performance", "Personal/Other": "Personal / other" };
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const SEASON = D.meta.season_months;
  const NS = "http://www.w3.org/2000/svg";
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pct = (x, d = 0) => (x == null ? "n/a" : (x * 100).toFixed(d) + "%");
  const n0 = (x) => Math.round(x).toLocaleString("en-US");
  const usd = (x) => x >= 1e6 ? "$" + (x / 1e6).toFixed(2) + "M" : x >= 1e3 ? "$" + Math.round(x / 1e3) + "k" : "$" + Math.round(x);
  const mon = (ym) => MONTHS[+ym.slice(5, 7) - 1] + " " + ym.slice(0, 4);
  const dfmt = (iso) => { const d = new Date(iso + "T00:00:00"); return d.getDate() + " " + MONTHS[d.getMonth()] + " " + d.getFullYear(); };
  const svgEl = (tag, attrs, parent) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; };
  const tierIcon = { High: '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M5 0.6 9.6 9.2H0.4z"/></svg>',
                     Medium: '<svg viewBox="0 0 10 10" aria-hidden="true"><rect x="1" y="1" width="8" height="8" rx="1"/></svg>',
                     Low: '<svg viewBox="0 0 10 10" aria-hidden="true"><circle cx="5" cy="5" r="4.2"/></svg>' };
  const pill = (t) => `<span class="pill ${t.toLowerCase()}">${tierIcon[t]}${t}</span>`;
  const verdictPill = (v) => { const c = { Pass: "pass", Review: "review", Fail: "fail" }[v] || "na"; const label = v === "Fail" ? "Investigate" : v;
    const ic = c === "pass" ? tierIcon.Low : c === "review" ? tierIcon.Medium : c === "fail" ? tierIcon.High : tierIcon.Low; return `<span class="pill ${c}">${ic}${label}</span>`; };
  // integer-friendly axis: step is 1, 2 or 5 x 10^k, max is a whole number of steps
  function axis(v, n = 4) { const raw = Math.max(v, 1) / n; const p = Math.pow(10, Math.floor(Math.log10(raw))); const f = raw / p;
    const step = Math.max(1, (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p); const max = Math.ceil(v / step) * step || step;
    return { max, ticks: Array.from({ length: Math.round(max / step) + 1 }, (_, i) => i * step) }; }

  // tooltip
  function tooltip(host) { let t = host.querySelector(".tip"); if (!t) { t = document.createElement("div"); t.className = "tip"; t.hidden = true; host.appendChild(t); } return t; }
  function showTip(host, tip, html, evt) {
    tip.innerHTML = html; tip.hidden = false;
    const hb = host.getBoundingClientRect(); const x = evt.clientX - hb.left + host.scrollLeft; const y = evt.clientY - hb.top;
    const w = tip.offsetWidth; const left = x + 14 + w > host.scrollLeft + hb.width ? x - w - 14 : x + 14;
    tip.style.left = Math.max(host.scrollLeft + 4, left) + "px"; tip.style.top = Math.max(4, y - 10) + "px";
  }

  // ---------------- KPIs
  const K = D.kpis;
  const hb = K.high_by_reason;
  $("kpis").innerHTML = [
    ["Active engineers", n0(K.headcount), K.serving_notice ? K.serving_notice + " more already serving notice" : "Excludes anyone already serving notice"],
    ["Expected resignations, 12 months", n0(K.expected_12m), pct(K.expected_12m_rate) + " of headcount"],
    ["Expected in " + K.season_label, n0(K.expected_season), pct(K.expected_season / Math.max(K.expected_12m, 1)) + " of the year's exits"],
    ["High-risk engineers", n0(K.tiers.High), `<span class="split"><span><i class="sw study"></i>${hb.Study} study</span><span><i class="sw comp"></i>${hb.Competitor} competitor</span><span><i class="sw perf"></i>${hb.Performance} perf.</span></span>`],
    ["Billing at risk, 12 months", usd(K.expected_impact_usd), "Probability-weighted vacancy cost"],
  ].map(([l, v, d]) => `<div class="kpi"><span class="label">${l}</span><span class="v num">${v}</span><span class="d">${d}</span></div>`).join("");

  // ---------------- Proof
  const B = D.backtest;
  $("proof-lead").textContent = `On ${dfmt(B.asof)} the agent was trained only on data before that day and asked to rank all ${B.headcount} engineers. We then checked who actually resigned between ${dfmt(B.asof)} and ${dfmt(B.window_end)}.`;
  const seasonShare = B.season.left ? B.season.caught / B.season.left : null;
  $("proof").innerHTML = [
    [`${B.caught} of ${B.left}`, `leavers were on its top-${B.list_size} list (${pct(B.caught / Math.max(B.left, 1))}). A random list of the same size would catch about ${Math.round(B.left * B.list_size / B.headcount)}.`],
    [pct(B.reason_accuracy), "of those caught were given the right reason (study, competitor, performance)."],
    [`${B.season.caught} of ${B.season.left}`, `July&ndash;October resignations were flagged five months or more in advance (${pct(seasonShare)}).`],
    [`${n0(B.expected_total)} vs ${B.actual_total}`, `forecast vs actual resignations in the window. AUC ${B.auc ? B.auc.toFixed(2) : "n/a"} (0.5 = guessing, 1.0 = perfect).`],
  ].map(([v, d]) => `<div class="stat"><span class="v num">${v}</span><span class="d">${d}</span></div>`).join("");

  function reasonRows(host, items, note) {
    host.innerHTML = items.map((r) => { const share = r.left ? r.caught / r.left : 0; return `<div class="rrow"><span><i class="sw ${CLS[r.reason]}"></i>${SHORT[r.reason]}</span>
      <span class="track" title="${r.caught} of ${r.left}"><span style="width:${(share * 100).toFixed(1)}%;background:var(--s-${CLS[r.reason]})"></span></span>
      <span class="num" style="text-align:right">${r.caught}/${r.left}</span></div>`; }).join("");
  }
  reasonRows($("bt-reasons"), B.per_reason);
  $("bt-reason-note").textContent = `Top-${B.list_size} list on ${dfmt(B.asof)}, outcomes to ${dfmt(B.window_end)}.`;
  const RL = B.rolling_90d;
  reasonRows($("roll-reasons"), RL.per_reason);
  $("roll-note").textContent = `Retrained every month from ${mon(RL.from)} to ${mon(RL.to)}; share of resignations that were on that month's top-20% list one to three months before. Forecast ${n0(RL.expected)} vs actual ${n0(RL.actual)}.`;

  $("examples").innerHTML = B.examples.map((e) => `<article class="ex">
      <div class="who"><div><b>${esc(e.name)}</b> <span class="mono muted" style="font-size:11.5px">${esc(e.id)}</span><br><span class="muted" style="font-size:13px">${esc(e.designation)}</span></div>
      <div style="text-align:right"><span class="label">Flagged ${dfmt(B.asof).split(" ").slice(1).join(" ")}</span><br><b class="num">${pct(e.risk)}</b> <span style="font-size:13px"><i class="sw ${CLS[e.predicted_reason]}"></i>${SHORT[e.predicted_reason]}</span></div></div>
      <ul>${e.drivers.slice(0, 3).map((d) => `<li>${esc(d.text)}</li>`).join("")}</ul>
      <div class="out">Resigned <b>${dfmt(e.notice_date)}</b> &middot; reason recorded: <i class="sw ${CLS[e.actual_reason]}"></i>${NICE[e.actual_reason]}</div>
    </article>`).join("");

  // backtest chart
  function btChart() {
    const host = $("bt-chart"); host.querySelectorAll("svg").forEach((s) => s.remove());
    const W = Math.max(420, host.clientWidth), H = 300, m = { l: 34, r: 10, t: 14, b: 28 }, iw = W - m.l - m.r, ih = H - m.t - m.b;
    const rows = B.monthly; const ax = axis(Math.max(...rows.map((r) => Math.max(r.actual, r.expected))) * 1.05); const max = ax.max;
    const svg = svgEl("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Actual resignations by month versus the agent's forecast" });
    const g = svgEl("g", { class: "grid" }, svg);
    ax.ticks.forEach((v) => { const y = m.t + ih - (v / max) * ih; svgEl("line", { x1: m.l, x2: W - m.r, y1: y, y2: y }, g); const t = svgEl("text", { x: m.l - 6, y: y + 3, "text-anchor": "end", class: "ann" }, svg); t.textContent = v; });
    const bw = iw / rows.length, w = Math.min(28, bw * 0.55);
    const pts = [];
    rows.forEach((r, i) => {
      const cx = m.l + bw * i + bw / 2, h = (r.actual / max) * ih;
      if (h > 0) svgEl("rect", { x: cx - w / 2, y: m.t + ih - h, width: w, height: h, rx: 3, class: "f-actual" }, svg);
      pts.push([cx, m.t + ih - (r.expected / max) * ih]);
      const t = svgEl("text", { x: cx, y: H - 8, "text-anchor": "middle", class: "ann" }, svg); t.textContent = MONTHS[+r.month.slice(5) - 1];
    });
    svgEl("line", { x1: m.l, x2: W - m.r, y1: m.t + ih, y2: m.t + ih, class: "baseline" }, svg);
    svgEl("path", { d: "M" + pts.map((p) => p.join(",")).join("L"), class: "line-exp" }, svg);
    pts.forEach((p) => svgEl("circle", { cx: p[0], cy: p[1], r: 4, class: "dot-exp" }, svg));
    const tip = tooltip(host);
    rows.forEach((r, i) => { const hit = svgEl("rect", { x: m.l + bw * i, y: m.t, width: bw, height: ih, class: "hit" }, svg);
      hit.addEventListener("mousemove", (e) => showTip(host, tip, `<div class="t">${mon(r.month)}</div><div class="r"><span>Actual</span><b>${r.actual}</b></div><div class="r"><span>Forecast</span><b>${r.expected.toFixed(1)}</b></div>`, e));
      hit.addEventListener("mouseleave", () => (tip.hidden = true)); });
    host.prepend(svg);
  }

  // season chart
  function seasonChart() {
    const host = $("season-chart"); host.querySelectorAll("svg").forEach((s) => s.remove());
    const rows = D.history.map((r) => Object.assign({ fc: false }, r)).concat(D.forecast.map((r) => Object.assign({ fc: true }, r)));
    const W = Math.max(760, host.clientWidth), H = 280, m = { l: 34, r: 10, t: 22, b: 30 }, iw = W - m.l - m.r, ih = H - m.t - m.b;
    const tot = (r) => REASONS.reduce((s, k) => s + r[k], 0);
    const ax = axis(Math.max(...rows.map(tot)) * 1.02); const max = ax.max;
    const svg = svgEl("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Monthly resignations by reason, history and forecast" });
    const bw = iw / rows.length, w = Math.max(3, bw - Math.min(3, bw * 0.28));
    rows.forEach((r, i) => { if (SEASON.includes(+r.month.slice(5))) svgEl("rect", { x: m.l + bw * i, y: m.t, width: bw, height: ih, class: "band" }, svg); });
    const g = svgEl("g", { class: "grid" }, svg);
    ax.ticks.forEach((v) => { const y = m.t + ih - (v / max) * ih; svgEl("line", { x1: m.l, x2: W - m.r, y1: y, y2: y }, g); const t = svgEl("text", { x: m.l - 6, y: y + 3, "text-anchor": "end", class: "ann" }, svg); t.textContent = v; });
    rows.forEach((r, i) => {
      let acc = 0; const x = m.l + bw * i + (bw - w) / 2;
      REASONS.forEach((k) => { const v = r[k]; if (v <= 0) return; const y1 = m.t + ih - ((acc + v) / max) * ih, y0 = m.t + ih - (acc / max) * ih; acc += v;
        const h = Math.max(0, y0 - y1 - 1); if (h <= 0) return; svgEl("rect", { x, y: y1, width: w, height: h, class: `f-${CLS[k]}${r.fc ? " fc" : ""}` }, svg); });
      if (r.month.endsWith("-01")) { const t = svgEl("text", { x: m.l + bw * i, y: H - 9, class: "ann" }, svg); t.textContent = r.month.slice(0, 4); svgEl("line", { x1: m.l + bw * i, x2: m.l + bw * i, y1: m.t + ih, y2: m.t + ih + 5, class: "baseline" }, svg); }
    });
    svgEl("line", { x1: m.l, x2: W - m.r, y1: m.t + ih, y2: m.t + ih, class: "baseline" }, svg);
    const fi = D.history.length, fx = m.l + bw * fi;
    svgEl("line", { x1: fx, x2: fx, y1: m.t - 8, y2: m.t + ih, class: "divider" }, svg);
    const ft = svgEl("text", { x: fx + 5, y: m.t - 10, class: "ann" }, svg); ft.textContent = "Forecast →";
    const ht = svgEl("text", { x: fx - 5, y: m.t - 10, class: "ann", "text-anchor": "end" }, svg); ht.textContent = "← Actual";
    const tip = tooltip(host);
    rows.forEach((r, i) => { const hit = svgEl("rect", { x: m.l + bw * i, y: m.t, width: bw, height: ih, class: "hit" }, svg);
      hit.addEventListener("mousemove", (e) => showTip(host, tip, `<div class="t">${mon(r.month)}${r.fc ? " &middot; forecast" : ""}</div>` +
        REASONS.map((k) => `<div class="r"><span><i class="sw ${CLS[k]}"></i>${SHORT[k]}</span><b>${r.fc ? r[k].toFixed(1) : r[k]}</b></div>`).join("") +
        `<div class="r" style="border-top:1px solid var(--line);margin-top:3px;padding-top:3px"><span>Total</span><b>${r.fc ? tot(r).toFixed(1) : tot(r)}</b></div>`, e));
      hit.addEventListener("mouseleave", () => (tip.hidden = true)); });
    host.prepend(svg);
  }

  // study calendar (Sep -> Oct of the following year)
  (function cal() {
    const cols = [9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
    const tracks = [
      ["Decides to apply", [[0, 1]], ""],
      ["IELTS / GRE test days", [[1, 4]], ""],
      ["Applications + degree attestation", [[2, 6]], ""],
      ["Offers; experience letter", [[5, 9]], ""],
      ["Visa; salary / bank letters", [[7, 11]], ""],
      ["Resignation letters", [[9, 13]], "strong"],
      ["Agent flags here", [[3, 7]], "agent"],
    ];
    let h = '<div class="mh"></div>' + cols.map((c, i) => `<div class="mh${SEASON.includes(c) && i > 6 ? " season" : ""}">${MONTHS[c - 1]}</div>`).join("");
    tracks.forEach(([label, spans, kind]) => {
      h += `<div class="rl">${label}</div>`;
      for (let i = 0; i < cols.length; i++) {
        let bar = ""; spans.forEach(([a, b]) => { if (i >= a && i < b) { const first = i === a, last = i === b - 1;
          bar = `<span class="bar ${kind}" style="left:${first ? 3 : 0}px;right:${last ? 3 : 0}px;border-radius:${first ? 3 : 0}px ${last ? 3 : 0}px ${last ? 3 : 0}px ${first ? 3 : 0}px"></span>`; } });
        h += `<div class="cell">${bar}</div>`;
      }
    });
    $("cal").innerHTML = h;
  })();

  // ---------------- Watchlist
  const E = D.employees;
  const state = { tier: "High", reason: "All", region: "All", q: "", sort: "risk12", dir: -1, open: new Set() };
  try { const s = JSON.parse(localStorage.getItem("radar-filters") || "null"); if (s) Object.assign(state, { tier: s.tier, reason: s.reason, region: s.region }); } catch (e) {}
  const tiers = ["High", "Medium", "Low", "All"];
  function chips() {
    $("tier-chips").innerHTML = tiers.map((t) => { const n = t === "All" ? E.length : E.filter((e) => e.tier === t).length;
      return `<button class="chip" data-tier="${t}" aria-pressed="${state.tier === t}">${t === "All" ? "Everyone" : t} <span class="num">${n}</span></button>`; }).join("");
    $("reason-chips").innerHTML = ["All"].concat(REASONS).map((r) => `<button class="chip" data-reason="${r}" aria-pressed="${state.reason === r}">${r === "All" ? "All reasons" : `<i class="sw ${CLS[r]}"></i>${SHORT[r]}`}</button>`).join("");
    $("region").value = state.region;
  }
  function save() { try { localStorage.setItem("radar-filters", JSON.stringify({ tier: state.tier, reason: state.reason, region: state.region })); } catch (e) {} }
  function sparkline(curve) {
    const W = 240, H = 90, m = { l: 26, r: 8, t: 8, b: 18 }, iw = W - m.l - m.r, ih = H - m.t - m.b;
    const x = (i) => m.l + (i / (curve.length - 1)) * iw, y = (v) => m.t + ih - v * ih;
    const pts = curve.map((v, i) => [x(i), y(v)]);
    const asof = new Date(D.meta.asof + "T00:00:00");
    const lab = (i) => MONTHS[(asof.getMonth() + i) % 12];
    return `<svg width="100%" viewBox="0 0 ${W} ${H}" role="img" aria-label="Cumulative chance of resigning over the next 12 months">
      <g class="grid">${[0, 0.5, 1].map((v) => `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}"/>`).join("")}</g>
      ${[0, 0.5, 1].map((v) => `<text class="ann" x="${m.l - 4}" y="${y(v) + 3}" text-anchor="end">${v * 100}%</text>`).join("")}
      <path d="M${x(0)},${y(0)}L${pts.map((p) => p.join(",")).join("L")}L${x(curve.length - 1)},${y(0)}Z" style="fill:var(--band)"/>
      <path d="M${pts.map((p) => p.join(",")).join("L")}" class="line-exp"/>
      <circle cx="${pts[pts.length - 1][0]}" cy="${pts[pts.length - 1][1]}" r="3.5" class="dot-exp"/>
      ${[0, 4, 8, 11].map((i) => `<text class="ann" x="${x(i)}" y="${H - 4}" text-anchor="middle">${lab(i)}</text>`).join("")}
    </svg>`;
  }
  function detail(e) {
    const br = REASONS.map((r) => { const v = e.by_reason[SHORT[r]]; return `<div class="rrow" style="grid-template-columns:96px minmax(0,1fr) 44px"><span><i class="sw ${CLS[r]}"></i>${SHORT[r]}</span>
      <span class="track"><span style="width:${(v * 100).toFixed(1)}%;background:var(--s-${CLS[r]})"></span></span><span class="num" style="text-align:right">${pct(v)}</span></div>`; }).join("");
    return `<div class="dgrid">
      <div><h4>Chance of resigning, by reason (12 months)</h4><div class="reasonlist" style="gap:6px">${br}</div>
        <dl class="kv" style="margin-top:12px"><dt>Next 3 months</dt><dd>${pct(e.risk3)}</dd><dt>Next 6 months</dt><dd>${pct(e.risk6)}</dd>
        <dt>In ${esc(K.season_label)}</dt><dd>${pct(e.season_risk)}</dd><dt>Billing impact if they leave</dt><dd>${usd(e.impact_usd)}</dd></dl></div>
      <div><h4>Cumulative risk, next 12 months</h4>${sparkline(e.curve)}</div>
      <div><h4>Why</h4><ol>${e.drivers.map((d) => `<li><b>${esc(d.group)}:</b> ${esc(d.text)}</li>`).join("") || "<li>No single signal stands out.</li>"}</ol>
        <h4 style="margin-top:12px">Action plan</h4><p style="font-weight:600;margin-bottom:4px">${esc(e.action)}</p>
        ${e.steps.length ? `<ul>${e.steps.map((s) => `<li>${esc(s)}</li>`).join("")}</ul>` : ""}
        <h4 style="margin-top:12px">Investment guidance</h4><p>${esc(e.invest)}</p></div>
    </div>`;
  }
  function render() {
    const q = state.q.trim().toLowerCase();
    let list = E.filter((e) => (state.tier === "All" || e.tier === state.tier) && (state.reason === "All" || e.reason === state.reason) &&
      (state.region === "All" || e.region === state.region) && (!q || (e.name + " " + e.id + " " + e.discipline + " " + e.designation).toLowerCase().includes(q)));
    list.sort((a, b) => { const k = state.sort; const va = a[k], vb = b[k]; return (typeof va === "string" ? va.localeCompare(vb) : va - vb) * state.dir; });
    $("count").textContent = `${list.length} engineer${list.length === 1 ? "" : "s"}`;
    if (!list.length) { $("rows").innerHTML = `<tr><td colspan="7" class="empty">No engineers match these filters. Choose "Everyone" or clear the search.</td></tr>`; return; }
    $("rows").innerHTML = list.map((e) => { const open = state.open.has(e.id); const d = e.drivers[0];
      return `<tr class="row" data-id="${e.id}" tabindex="0" aria-expanded="${open}">
        <td class="who"><b>${esc(e.name)}</b><br><span class="id">${esc(e.id)}</span> <span class="muted" style="font-size:12.5px">&middot; ${esc(e.designation)}</span></td>
        <td>${esc(e.region === "US" ? "US" : "Australia")} &middot; ${esc(e.discipline)}</td>
        <td class="num">${e.tenure_years.toFixed(1)} yrs</td>
        <td><div class="risk"><div class="riskline">${pill(e.tier)}<b class="num">${pct(e.risk12)}</b></div><div class="minibar"><span style="width:${(e.risk12 * 100).toFixed(1)}%"></span></div></div></td>
        <td style="white-space:nowrap"><i class="sw ${CLS[e.reason]}"></i>${SHORT[e.reason]}</td>
        <td>${d ? esc(d.text) : '<span class="muted">No single signal stands out</span>'}${e.drivers.length > 1 ? ` <span class="muted">+${e.drivers.length - 1} more</span>` : ""}</td>
        <td>${esc(e.action)}</td></tr>` + (open ? `<tr class="detail"><td colspan="7">${detail(e)}</td></tr>` : ""); }).join("");
  }
  chips(); render();
  $("tier-chips").addEventListener("click", (ev) => { const b = ev.target.closest("[data-tier]"); if (!b) return; state.tier = b.dataset.tier; save(); chips(); render(); });
  $("reason-chips").addEventListener("click", (ev) => { const b = ev.target.closest("[data-reason]"); if (!b) return; state.reason = b.dataset.reason; save(); chips(); render(); });
  $("region").addEventListener("change", (ev) => { state.region = ev.target.value; save(); render(); });
  $("q").addEventListener("input", (ev) => { state.q = ev.target.value; render(); });
  document.querySelectorAll("th button[data-sort]").forEach((b) => b.addEventListener("click", () => {
    const k = b.dataset.sort; if (state.sort === k) state.dir *= -1; else { state.sort = k; state.dir = k === "name" ? 1 : -1; }
    document.querySelectorAll("th button[data-sort]").forEach((x) => (x.innerHTML = x.innerHTML.replace(/ [↑↓]$/, "")));
    b.innerHTML += state.dir === 1 ? " ↑" : " ↓"; render(); }));
  function toggle(tr) { const id = tr.dataset.id; if (state.open.has(id)) state.open.delete(id); else state.open.add(id); render();
    const again = document.querySelector(`tr.row[data-id="${id}"]`); if (again) again.focus(); }
  $("rows").addEventListener("click", (ev) => { const tr = ev.target.closest("tr.row"); if (tr) toggle(tr); });
  $("rows").addEventListener("keydown", (ev) => { if ((ev.key === "Enter" || ev.key === " ") && ev.target.matches("tr.row")) { ev.preventDefault(); toggle(ev.target); } });

  // ---------------- Drivers
  $("drivers").innerHTML = ["Foreign Study", "Competitor", "Performance"].map((r) => { const d = D.drivers[r]; const max = Math.max(1, ...d.groups.map((g) => g.count));
    return `<div class="card drv"><h3><i class="sw ${CLS[r]}"></i>${NICE[r]}</h3><p class="muted" style="font-size:13px">${d.people} flagged engineer${d.people === 1 ? "" : "s"}</p>
      ${d.groups.map((g) => `<div class="drow"><span>${esc(g.group)}</span><span class="track"><span style="width:${(g.count / max * 100).toFixed(1)}%;background:var(--s-${CLS[r]})"></span></span><span class="num" style="text-align:right">${g.count}</span></div>`).join("") || '<p class="muted">Nobody flagged for this reason.</p>'}</div>`; }).join("");

  // ---------------- Fairness
  const F = D.fairness;
  $("fair-lead").textContent = `Checked on the ${dfmt(B.asof)} backtest list, where real outcomes are known. Flag rates follow the 4/5ths rule; precision shows whether a flag is equally reliable for every group.`;
  $("excluded").innerHTML = F.excluded.map((c) => `<span class="tag">${esc(c)}</span>`).join("");
  $("fair").innerHTML = F.attributes.map((a) => `<div class="card" style="display:grid;gap:10px;align-content:start">
      <div style="display:flex;justify-content:space-between;gap:8px;align-items:center;flex-wrap:wrap"><h3>${esc(a.attribute)}</h3>${verdictPill(a.verdict)}</div>
      <div class="tablewrap" style="border:0"><table><thead><tr><th>Group</th><th>People</th><th>Flagged</th><th>Actually left</th><th>Precision</th></tr></thead><tbody>
      ${a.groups.map((g) => `<tr><td>${esc(g.group)}</td><td class="num">${g.n}</td><td class="num">${pct(g.flag_rate)}</td><td class="num">${pct(g.exit_rate)}</td><td class="num">${pct(g.precision)}</td></tr>`).join("")}
      </tbody></table></div>
      <p class="note">${a.di_ratio != null ? `Lowest/highest flag-rate ratio <b class="num">${a.di_ratio.toFixed(2)}</b> (floor 0.80). ` : ""}${esc(a.note)}</p></div>`).join("");
  $("proxy").innerHTML = `<thead><tr><th>Attribute</th><th>Test</th><th>Score (AUC)</th><th>Link</th><th>What it means</th></tr></thead><tbody>` +
    F.proxy.map((p) => `<tr><td>${esc(p.attribute)}</td><td>${esc(p.target)}</td><td class="num">${p.auc.toFixed(2)}${p.auc < 0.55 ? " (chance)" : ""}</td><td>${verdictPill(p.level === "Low" ? "Pass" : p.level === "Moderate" ? "Review" : "Fail").replace(/Pass|Review|Investigate/, p.level)}</td><td style="min-width:260px">${esc(p.note)}</td></tr>`).join("") + "</tbody>";

  // ---------------- Data + footer
  const T = D.data.tables;
  $("datatable").innerHTML = `<thead><tr><th>Table</th><th>Rows</th></tr></thead><tbody>` + Object.keys(T).map((k) => `<tr><td class="mono" style="font-size:12.5px">${esc(k)}</td><td class="num">${n0(T[k])}</td></tr>`).join("") +
    D.data.missing.map((k) => `<tr><td class="mono" style="font-size:12.5px">${esc(k)}</td><td class="muted">not provided</td></tr>`).join("") + "</tbody>";
  $("impact-assumption").textContent = D.model.impact_assumption;
  $("footer").textContent = `Retention Radar 0.1 · generated ${D.meta.generated} · scores as of ${dfmt(D.meta.asof)} · ${D.meta.synthetic ? "synthetic demo data" : "confidential: HR head and CEO only"}`;

  btChart(); seasonChart();
  let rt; window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => { btChart(); seasonChart(); }, 150); });
})();
</script>
"""
