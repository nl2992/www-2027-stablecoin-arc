"""Generate ``paper/generated/numbers.tex`` from committed JSON reports.

Each macro records the report and JSON path it came from, so a reviewer can
trace every number in the manuscript. Run: ``uv run python -m www_paper.macros``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "paper/generated/numbers.tex"


def _get(data: Any, path: str) -> Any:
    for part in path.split("/"):
        data = data[int(part)] if isinstance(data, list) else data[part]
    return data


def _fmt(digits: int) -> Callable[[Any], str]:
    return lambda v: f"{v:,.{digits}f}"


def _pct(digits: int = 1) -> Callable[[Any], str]:
    return lambda v: f"{100 * v:.{digits}f}"


def _int(v: Any) -> str:
    return f"{int(v):,}"


C3 = "reports/c3/fragmentation_persistence.json"
ROB = "reports/c3/robustness.json"
ANCHOR = "reports/events/E2023-03-USDC-SVB_protocol.json"
C1 = "reports/c1/march01_sample_validation.json"
FDUSD = "reports/events/E2025-04-FDUSD_protocol.json"
PLACEBO = "reports/events/P2023-02-BUSD-PAXOS-HALT_protocol.json"
NEG = "reports/events/N2023-06-USDT-3POOL_protocol.json"
NEG_BNUS = "reports/events/N2023-06-USDT-3POOL_robustness_binanceus.json"
TUSD = "reports/events/E2024-01-TUSD_protocol.json"
UST = "reports/events/E2022-05-UST-COLLAPSE_protocol.json"
USDE = "reports/events/E2025-10-USDE-BINANCE_protocol.json"
U = "wedges/usdc/all_legs_traded"

# (macro name, report, json path, formatter)
SPEC: list[tuple[str, str, str, Callable[[Any], str]]] = [
    ("NumUsdcMedAbsPre", C3, f"{U}/pre_crisis/median_abs_bps", _fmt(2)),
    ("NumUsdcMedAbsCrisis", C3, f"{U}/crisis/median_abs_bps", _fmt(2)),
    ("NumUsdcMedAbsPost", C3, f"{U}/post/median_abs_bps", _fmt(2)),
    ("NumUsdcPNinetyFivePre", C3, f"{U}/pre_crisis/p95_abs_bps", _fmt(1)),
    ("NumUsdcPNinetyFiveCrisis", C3, f"{U}/crisis/p95_abs_bps", _fmt(1)),
    ("NumUsdcShareAboveTwentyFiveCrisis", C3, f"{U}/crisis/thresholds/25.0/share_observed_minutes_above", _pct()),
    ("NumUsdcShareAboveTwentyFivePre", C3, f"{U}/pre_crisis/thresholds/25.0/share_observed_minutes_above", _pct()),
    ("NumUsdcCrisisMinutes", C3, f"{U}/crisis/observed_minutes", _int),
    ("NumUsdcHalfLifeOneMinCrisis", C3, f"{U}/crisis/half_life_to_parity_minutes", _fmt(1)),
    ("NumUsdtPNinetyFiveCrisis", C3, "wedges/usdt/all_legs_traded/crisis/p95_abs_bps", _fmt(1)),
    ("NumUsdcDiffMedAbs", ROB, "regime_differences/usdc/crisis_minus_pre_crisis/median_abs/estimate", _fmt(2)),
    ("NumUsdcDiffMedAbsLo", ROB, "regime_differences/usdc/crisis_minus_pre_crisis/median_abs/ci95/0", _fmt(2)),
    ("NumUsdcDiffMedAbsHi", ROB, "regime_differences/usdc/crisis_minus_pre_crisis/median_abs/ci95/1", _fmt(2)),
    ("NumUsdcHalfLifeFifteenCrisis", ROB, "horizons/usdc/15/crisis/half_life_to_parity_minutes", _fmt(1)),
    ("NumUsdcHalfLifeSixtyCrisis", ROB, "horizons/usdc/60/crisis/half_life_to_parity_minutes", _fmt(1)),
    ("NumUsdcCoinbaseMedAbsCrisis", ROB, "alternative_dollar_leg/usdc_coinbase_btcusd/crisis/median_abs_bps", _fmt(2)),
    ("NumAnchorExtremeBps", ANCHOR, "r1/extreme_deviation_bps", _fmt(0)),
    ("NumAnchorBreachMinutes", ANCHOR, "r1/max_breach_minutes_in_window", _int),
    ("NumAnchorEventMedAbs", ANCHOR, "windows/event/diagnostics/median_abs_dev_bps", _fmt(1)),
    ("NumAnchorEventPNinetyFive", ANCHOR, "windows/event/diagnostics/p95_abs_dev_bps", _fmt(1)),
    ("NumAnchorEventShareHundred", ANCHOR, "windows/event/diagnostics/share_traded_minutes_ge_100bps", _pct(0)),
    ("NumAnchorEventHalfLife", ANCHOR, "windows/event/diagnostics/half_life_to_parity_minutes_15m_bins", _fmt(0)),
    ("NumAnchorBaselineMedAbs", ANCHOR, "windows/baseline/diagnostics/median_abs_dev_bps", _fmt(1)),
    ("NumAnchorRecoveryMedAbs", ANCHOR, "windows/recovery/diagnostics/median_abs_dev_bps", _fmt(1)),
    ("NumSampleRows", C1, "rows", _int),
    ("NumAnchorDvOne", ANCHOR, "plan/dv1/estimate", _fmt(0)),
    ("NumAnchorDvOneLo", ANCHOR, "plan/dv1/ci95/0", _fmt(0)),
    ("NumAnchorDvOneHi", ANCHOR, "plan/dv1/ci95/1", _fmt(0)),
    ("NumAnchorRecoveryHours", ANCHOR, "plan/dv3/recovery_minutes", lambda v: f"{v / 60:.0f}"),
    ("NumAnchorBtcVolBaseline", ANCHOR, "plan/covariates/baseline/btc_realized_vol_bps_per_hour", _fmt(0)),
    ("NumAnchorBtcVolEvent", ANCHOR, "plan/covariates/event/btc_realized_vol_bps_per_hour", _fmt(0)),
    ("NumAnchorDvFour", ANCHOR, "plan/dv4/estimate", _fmt(1)),
    ("NumAnchorDvFourLo", ANCHOR, "plan/dv4/ci95/0", _fmt(1)),
    ("NumAnchorDvFourHi", ANCHOR, "plan/dv4/ci95/1", _fmt(1)),
    ("NumAnchorDvFive", ANCHOR, "plan/dv5/ratio", _fmt(0)),
    ("NumFdusdExtreme", FDUSD, "r1/extreme_deviation_bps", _fmt(0)),
    ("NumFdusdDvOne", FDUSD, "plan/dv1/estimate", _fmt(0)),
    ("NumFdusdDvOneLo", FDUSD, "plan/dv1/ci95/0", _fmt(0)),
    ("NumFdusdDvOneHi", FDUSD, "plan/dv1/ci95/1", _fmt(0)),
    ("NumFdusdDvFour", FDUSD, "plan/dv4/estimate", _fmt(2)),
    ("NumFdusdDvFourLo", FDUSD, "plan/dv4/ci95/0", _fmt(2)),
    ("NumFdusdDvFourHi", FDUSD, "plan/dv4/ci95/1", _fmt(2)),
    ("NumFdusdRecoveryHours", FDUSD, "plan/dv3/recovery_minutes", lambda v: f"{v / 60:.0f}"),
    ("NumFdusdVolControl", FDUSD, "plan/covariates/control/btc_realized_vol_bps_per_hour", _fmt(0)),
    ("NumFdusdVolEvent", FDUSD, "plan/covariates/event/btc_realized_vol_bps_per_hour", _fmt(0)),
    ("NumPlaceboDvOne", PLACEBO, "plan/dv1/estimate", _fmt(0)),
    ("NumPlaceboDvFive", PLACEBO, "plan/dv5/ratio", _fmt(1)),
    ("NumNegativeExtreme", NEG_BNUS, "r1/extreme_deviation_bps", _fmt(0)),
    ("NumNegativeExtremeBitstamp", NEG, "r1/extreme_deviation_bps", _fmt(0)),
    ("NumTusdExtreme", TUSD, "r1/extreme_deviation_bps", _fmt(0)),
    ("NumUstExtreme", UST, "r1/extreme_deviation_bps", _fmt(0)),
    ("NumTusdDvOne", TUSD, "plan/dv1/estimate", _fmt(0)),
    ("NumTusdDvOneLo", TUSD, "plan/dv1/ci95/0", _fmt(0)),
    ("NumTusdDvOneHi", TUSD, "plan/dv1/ci95/1", _fmt(0)),
    ("NumTusdDvFour", TUSD, "plan/dv4/estimate", _fmt(2)),
    ("NumUsdeExtreme", USDE, "r1/extreme_deviation_bps", _fmt(0)),
    ("NumUsdeUsdtGate", USDE, "plan/usdt_gate/median_abs_bps", _fmt(0)),
]


def closed_base_rate() -> str:
    """Share of hours in a generic week that fall outside the assumed US banking redemption window."""
    import pandas as pd
    from www_capacity.redemption import RedemptionSchedule
    hours = pd.date_range("2024-01-08", periods=24 * 7, freq="1h", tz="America/New_York")  # Monday-start week
    sched = RedemptionSchedule()
    return f"{100 * sum(not sched.is_open(t.to_pydatetime()) for t in hours) / len(hours):.0f}"


def registry_counts() -> dict[str, int]:
    events = json.loads((ROOT / "configs/event_registry.json").read_text())["events"]
    primaries = [e for e in events if e["role"] == "PRIMARY"]
    return {
        "NumRegistryEntries": len(events),
        "NumRegistryClusters": len({e["cluster_id"] for e in events}),
        "NumAcceptedClusters": len({e["cluster_id"] for e in primaries if e["status"] == "ACCEPTED"}),
        "NumDocumentedPrimaries": sum(e["status"] == "SOURCE_DOCUMENTED" for e in primaries),
        "NumUnresolved": sum(e["status"] == "UNRESOLVED" for e in events),
    }


def build() -> str:
    lines = ["% Generated by `uv run python -m www_paper.macros`; do not edit by hand."]
    cache: dict[str, Any] = {}
    for name, report, path, fmt in SPEC:
        data = cache.setdefault(report, json.loads((ROOT / report).read_text()))
        lines.append(f"\\newcommand{{\\{name}}}{{{fmt(_get(data, path))}}} % {report}: {path}")
    lines.append(f"\\newcommand{{\\NumClosedBaseRate}}{{{closed_base_rate()}}} % www_capacity.redemption weekly base rate")
    for name, value in registry_counts().items():
        lines.append(f"\\newcommand{{\\{name}}}{{{value}}} % configs/event_registry.json")
    return "\n".join(lines) + "\n"


TABLE_OUTPUT = ROOT / "paper/generated/registry_table.tex"
ROLE_LABEL = {"IN_SAMPLE": "in", "OUT_OF_SAMPLE": "OOS", "PLACEBO": "placebo", "UNASSIGNED": "--"}


def _tex(text: str) -> str:
    return text.replace("\\", "").replace("_", "\\_").replace("&", "\\&").replace("%", "\\%")


def build_registry_table() -> str:
    """Event registry table generated from configs/event_registry.json."""
    events = json.loads((ROOT / "configs/event_registry.json").read_text())["events"]
    rows = []
    for e in events:
        w = e["reported_window_utc"]
        dates = w["start"] if w["start"] == w["end"] else f"{w['start']}--{w['end'][5:]}"
        name = e["id"] if e["role"] == "PRIMARY" else "$\\hookrightarrow$ " + e["id"]
        rows.append(" & ".join(_tex(x) if i not in (0, 3) else x for i, x in enumerate([
            name.replace("_", "\\_"), e["stablecoin"], e["mechanism"].replace("_", " ").lower(), dates,
            e["status"].replace("_", " ").lower(), ROLE_LABEL[e["sample_role"]]])) + " \\\\")
    return "\n".join([
        "% Generated by `uv run python -m www_paper.macros` from configs/event_registry.json; do not edit.",
        "\\begin{table*}[t]",
        "\\caption{Event registry. Reported dates come from cited sources; only accepted events are measured. "
        "$\\hookrightarrow$ marks linked legs, which never count as independent episodes.}",
        "\\label{tab:registry}",
        "\\small",
        "\\begin{tabular}{llllll}",
        "\\toprule",
        "Event & Coin & Mechanism & Reported dates & Status & Role \\\\",
        "\\midrule",
        *rows,
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table*}",
    ]) + "\n"


COVERAGE_TABLE_OUTPUT = ROOT / "paper/generated/coverage_table.tex"
STATUS_LETTER = {"OBSERVED_LOCAL": "O", "LISTED": "L", "UNVERIFIED_SOURCE": "U", "NOT_LISTED": "N",
                 "ACCESS_BLOCKED": "B"}
WINDOW_ORDER = ("control", "baseline", "event", "recovery")


def _window_letter(statuses: dict[str, int]) -> str:
    """Single letter if the window is uniform; otherwise the letters present with day counts."""
    if len(statuses) == 1:
        return STATUS_LETTER[next(iter(statuses))]
    return "/".join(f"{STATUS_LETTER[k]}{v}" for k, v in sorted(statuses.items()))


def build_coverage_table() -> str:
    """Appendix table: per event/venue/symbol, coverage status in each analysis window."""
    cov = json.loads((ROOT / "reports/events/coverage_matrix.json").read_text())
    rows = []
    for key in sorted(cov["summary"]):
        event, venue, symbol = key.split("|")
        cells = [_window_letter(cov["summary"][key].get(w, {"NOT_LISTED": 0})) for w in WINDOW_ORDER]
        rows.append(f"{_tex(event)} & {_tex(venue)} & {_tex(symbol)} & " + " & ".join(cells) + " \\\\")
    return "\n".join([
        "% Generated by `uv run python -m www_paper.macros` from reports/events/coverage_matrix.json; do not edit.",
        "\\begin{table*}[t]",
        f"\\caption{{Data coverage by analysis window (listing check {_tex(cov['checked_utc'])}). O: observed and "
        "audited locally; L: listed in a public archive, not downloaded; U: source not verified; N: not listed or "
        "not covered.}",
        "\\label{tab:coverage}",
        "\\small",
        "\\begin{tabular}{lllcccc}",
        "\\toprule",
        "Event & Venue & Symbol & Control & Baseline & Event & Recovery \\\\",
        "\\midrule",
        *rows,
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table*}",
    ]) + "\n"


RESULTS_TABLE_OUTPUT = ROOT / "paper/generated/results_table.tex"
RESULTS_MD_OUTPUT = ROOT / "reports/events/cross_event_results.md"


def _n(v: Any, digits: int = 0) -> str:
    return "--" if v is None else f"{v:,.{digits}f}"


def results_rows() -> list[dict[str, str]]:
    """One row per measured registry event, read from its protocol report."""
    events = {e["id"]: e for e in json.loads((ROOT / "configs/event_registry.json").read_text())["events"]}
    rows = []
    for path in sorted((ROOT / "reports/events").glob("*_protocol.json")):
        r = json.loads(path.read_text())
        e, plan, r1 = events[r["event_id"]], r["plan"], r.get("r1") or {}
        dv1, dv3, dv4, dv5 = (plan.get(k, {}) for k in ("dv1", "dv3", "dv4", "dv5"))
        cov = plan.get("covariates", {})
        ref = plan.get("dv1_reference_window", "")
        rows.append({
            "event": e["id"], "coin": e["stablecoin"], "role": e["sample_role"].replace("_", " ").lower(),
            "status": e["status"].replace("_", " ").lower(),
            "analysis": ("descriptive (not accepted)" if plan.get("analysis_status") == "CONFIRMATORY"
                         and e["status"] != "ACCEPTED" else plan.get("analysis_status", "").lower().replace("_", " ")),
            "extreme": _n(r1.get("extreme_deviation_bps")), "breach": _n(r1.get("max_breach_minutes_in_window")),
            "dv1": (f"{_n(dv1.get('estimate'))} [{_n(dv1['ci95'][0])}, {_n(dv1['ci95'][1])}]"
                    if dv1.get("estimate") is not None else "--") + ("$^b$" if ref == "baseline" else ""),
            "dv3": "--" if dv3.get("recovery_minutes") is None else
                   f"{dv3['recovery_minutes'] / 60:.0f}" + ("+" if dv3.get("censored") else ""),
            "dv4": "--" if dv4.get("estimate") is None else f"{dv4['estimate']:.2f}",
            "dv5": _n(dv5.get("ratio"), 1),
            "vol": f"{_n(cov.get(ref, {}).get('btc_realized_vol_bps_per_hour'))}$\\to${_n(cov.get('event', {}).get('btc_realized_vol_bps_per_hour'))}",
        })
    return rows


def build_results_table() -> str:
    head = ["Event", "Coin", "Role", "Registry", "Analysis", "Extreme", "R1 min", "DV1 [95\\% CI]", "DV3 h",
            "DV4", "DV5", "BTC vol"]
    body = [" & ".join(_tex(v) if k not in ("dv1", "vol") else v for k, v in row.items()) + " \\\\"
            for row in results_rows()]
    return "\n".join([
        "% Generated by `uv run python -m www_paper.macros` from reports/events/*_protocol.json; do not edit.",
        "\\begin{table*}[t]",
        "\\caption{Event protocol results (bps unless noted). Extreme: largest traded-minute deviation from par; "
        "R1 min: most breaching minutes in a 24h window; DV1: event minus control median $|D|$ ($^b$: baseline used, "
        "control uncovered); DV3: hours to recovery (+: censored); DV4: change in median $|W|$; DV5: half-life ratio "
        "D/W; BTC vol: realized volatility (bps/h), reference$\\to$event. Only accepted, non-exploratory events "
        "enter confirmatory counts.}",
        "\\label{tab:results}",
        "\\scriptsize",
        "\\begin{tabular}{llllllrrlrrrl}".replace("llllllrrlrrrl", "lllllrrlrrrl"),
        "\\toprule",
        " & ".join(head) + " \\\\",
        "\\midrule",
        *body,
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table*}",
    ]) + "\n"


def build_results_markdown() -> str:
    rows = results_rows()
    cols = list(rows[0])
    lines = ["<!-- generated by www_paper.macros from reports/events/*_protocol.json; do not edit -->", "",
             "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(r[c].replace("$^b$", " (b)").replace("$\\to$", " → ") for c in cols) + " |"
              for r in rows]
    return "\n".join(lines) + "\n"


ROBUSTNESS_TABLE_OUTPUT = ROOT / "paper/generated/robustness_table.tex"
MECHANISM_TABLE_OUTPUT = ROOT / "paper/generated/mechanism_table.tex"
MECHANISM_MD_OUTPUT = ROOT / "reports/events/mechanism_covariates.md"


def mechanism_rows() -> list[dict[str, str]]:
    """Plan section 6 covariates per measured event; associations only, never causal decompositions."""
    import pandas as pd
    from www_capacity.redemption import RedemptionSchedule
    from www_events.registry import _parse_date, analysis_windows

    sched = RedemptionSchedule()
    events = {e["id"]: e for e in json.loads((ROOT / "configs/event_registry.json").read_text())["events"]}
    rows = []
    for path in sorted((ROOT / "reports/events").glob("*_protocol.json")):
        r = json.loads(path.read_text())
        e, plan = events[r["event_id"]], r["plan"]
        cov, ref = plan.get("covariates", {}), plan.get("dv1_reference_window", "control")
        w = analysis_windows(_parse_date(e["reported_window_utc"]["start"]), _parse_date(e["reported_window_utc"]["end"]))
        minutes = pd.date_range(w["event"]["start"], pd.Timestamp(w["event"]["end"]) + pd.Timedelta("1D"),
                                freq="1h", inclusive="left", tz="UTC")
        closed_share = sum(not sched.is_open(t.to_pydatetime()) for t in minutes) / len(minutes)
        ext = (r.get("r1") or {}).get("extreme_utc")
        ext_closed = None if ext is None else not sched.is_open(pd.Timestamp(ext).to_pydatetime())
        vol_ref, vol_ev = (cov.get(ref, {}).get("btc_realized_vol_bps_per_hour"),
                           cov.get("event", {}).get("btc_realized_vol_bps_per_hour"))
        rows.append({
            "event": e["id"], "mechanism": e["mechanism"].replace("_", " ").lower(),
            "status": e["status"].replace("_", " ").lower(),
            "vol_ratio": "--" if not (vol_ref and vol_ev) else f"{vol_ev / vol_ref:.2f}",
            "traded_share": f"{_n((cov.get(ref, {}).get('traded_minute_share') or 0) * 100)}$\\to$"
                            f"{_n((cov.get('event', {}).get('traded_minute_share') or 0) * 100)}",
            "outage_runs": str(cov.get("event", {}).get("missing_runs_over_15m", "--")),
            "closed_share": f"{closed_share * 100:.0f}",
            "extreme_closed": "--" if ext_closed is None else ("yes" if ext_closed else "no"),
        })
    return rows


def build_mechanism_table() -> str:
    head = ["Event", "Mechanism", "Registry", "BTC vol ratio", "Traded \\% ref$\\to$event", "Outage runs",
            "Redemption closed \\%", "Extreme while closed"]
    body = [" & ".join(_tex(v) if k != "traded_share" else v for k, v in row.items()) + " \\\\"
            for row in mechanism_rows()]
    return "\n".join([
        "% Generated by `uv run python -m www_paper.macros` from reports/events/*_protocol.json; do not edit.",
        "\\begin{table*}[t]",
        "\\caption{Pre-listed alternative explanations (plan section 6), reported as associations only. BTC vol "
        "ratio: event over reference realized volatility; traded share of minutes on the stablecoin leg; outage "
        "runs: missing-data runs over 15 minutes in the event window; redemption closed: share of event-window hours "
        "outside a generic US banking window (America/New\\_York, 9:00--17:00 weekdays) \\emph{assumed}, not "
        "issuer-documented.}",
        "\\label{tab:mechanism}",
        "\\scriptsize",
        "\\begin{tabular}{lllrlrrl}",
        "\\toprule",
        " & ".join(head) + " \\\\",
        "\\midrule",
        *body,
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table*}",
    ]) + "\n"


def build_mechanism_markdown() -> str:
    rows = mechanism_rows()
    cols = list(rows[0])
    lines = ["<!-- generated by www_paper.macros; associations only; redemption window is an assumption -->", "",
             "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(r[c].replace("$\\to$", " → ") for c in cols) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def build_robustness_table() -> str:
    yes = lambda b: "pass" if b else "fail"
    rows = []
    for path in sorted((ROOT / "reports/events").glob("*_protocol.json")):
        r = json.loads(path.read_text())
        rb, r1 = r["plan"].get("robustness"), r.get("r1") or {}
        if rb is None:
            continue
        hl = rb["half_life_D_minutes"]
        trim = rb["dv1_trimmed_6h"].get("estimate")
        rows.append(" & ".join([_tex(r["event_id"]), yes(rb["r1_threshold_50"]), yes(r1.get("r1_pass")),
                                yes(rb["r1_threshold_200"]), _n(trim), _n(hl["15"]), _n(hl["30"]), _n(hl["60"])])
                    + " \\\\")
    return "\n".join([
        "% Generated by `uv run python -m www_paper.macros` from reports/events/*_protocol.json; do not edit.",
        "\\begin{table}[t]",
        "\\caption{Pre-registered robustness (plan section 7): R1 at 50/100/200 bps, DV1 with 6h trimmed from each "
        "end of the event window (bps), and the parity half-life of $D$ (minutes) on 15/30/60-minute bins (--: no "
        "mean reversion).}",
        "\\label{tab:robustness}",
        "\\scriptsize",
        "\\begin{tabular}{lccccrrr}",
        "\\toprule",
        "Event & R1@50 & R1@100 & R1@200 & DV1 trim & HL15 & HL30 & HL60 \\\\",
        "\\midrule",
        *rows,
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
    ]) + "\n"


def main() -> None:
    MECHANISM_TABLE_OUTPUT.write_text(build_mechanism_table())
    MECHANISM_MD_OUTPUT.write_text(build_mechanism_markdown())
    ROBUSTNESS_TABLE_OUTPUT.write_text(build_robustness_table())
    RESULTS_TABLE_OUTPUT.write_text(build_results_table())
    RESULTS_MD_OUTPUT.write_text(build_results_markdown())
    COVERAGE_TABLE_OUTPUT.write_text(build_coverage_table())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(build())
    TABLE_OUTPUT.write_text(build_registry_table())
    print(f"WROTE {OUTPUT.relative_to(ROOT)} and {TABLE_OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
