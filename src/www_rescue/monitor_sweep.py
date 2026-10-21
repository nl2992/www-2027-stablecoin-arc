"""Operating-curve sweep, exposure definitions and timeline facts for the hour-level ledger-failure monitor.

Answers simulated review V3 issue 3 (docs/review/SIM_REVIEW_V3_SUMMARY.md): the paper reported one operating point per
method. This module reuses the loaders, flags, labels (amendment D1), day and episode logic and metrics of
``detector_eval`` unchanged and only varies the parameters:

- detector (agreement 0.25, and 0.1 / 0.5) and B1 gap-only and a matched two-asset rule at 25..300 bps,
- B2 trailing robust z at k = 3..6 (it has no bps threshold), B3 Bitfinex USDT premium at the same thresholds.

Nothing here selects a headline. The point (100 bps, agreement 0.25) must reproduce reports/rescue/detector_eval.json.
Run: ``uv run python -m www_rescue.monitor_sweep`` (about 30 s; reads data/raw).
"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from . import detector_eval as de

THRESHOLDS = (25.0, 50.0, 75.0, 100.0, 150.0, 200.0, 300.0)
AGREEMENTS = (0.25, 0.1, 0.5)
B2_KS = (3.0, 4.0, 5.0, 6.0)
RECALL_LEVELS = (0.6, 0.7, 0.85, 1.0)
HEADLINE = {"threshold": 100.0, "agreement": 0.25, "k": 4.0}
VENUES = de.VENUES
SCOPES = (*VENUES, "pooled")
H2_2018 = (date(2018, 7, 1), date(2018, 12, 31))
BIG_GAP_BPS = 100.0
ROOT = Path(__file__).resolve().parents[2]
PROBE = "reports/unit_td/probe.json"
DAYS_PER_MONTH = 30.44


def two_asset_flags(L: pd.Series, S: pd.Series, threshold: float) -> pd.Series:
    """Matched two-asset rule: |L| >= threshold and |S| >= threshold with the same sign, no ratio condition.

    Evaluated hours are those where both gaps exist, as for the detector."""
    both = pd.concat([L, S], axis=1, keys=["L", "S"]).dropna()
    up = (both["L"] >= threshold) & (both["S"] >= threshold)
    down = (both["L"] <= -threshold) & (both["S"] <= -threshold)
    return (up | down).astype(bool)


def _num(x: float) -> str:
    return f"{x:g}"


def method_specs() -> list[tuple[str, str, tuple[float, ...]]]:
    """(method key, parameter name, parameter values)."""
    return [*((f"detector_a{_num(a)}", "threshold_bps", THRESHOLDS) for a in AGREEMENTS),
            ("b1", "threshold_bps", THRESHOLDS), ("two_asset", "threshold_bps", THRESHOLDS),
            ("b2", "k", B2_KS), ("b3", "threshold_bps", THRESHOLDS)]


def _flags(vd: de.VenueData, method: str, p: float) -> pd.Series | None:
    if method.startswith("detector_a"):
        return de.hour_flags(vd.L, vd.S, p, float(method[len("detector_a"):]))
    if method == "b1":
        return de.gap_flags(vd.L, p)
    if method == "two_asset":
        return two_asset_flags(vd.L, vd.S, p)
    if method == "b2":
        return de.robust_z_flags(vd.L, k=p)
    if method == "b3":
        return None if vd.D_usdt is None else de.premium_flags(vd.D_usdt, p)
    raise ValueError(method)


def _point(ev: dict[str, Any] | None) -> dict[str, Any] | None:
    """Counts of one evaluation that can be summed over venues."""
    if ev is None:
        return None
    fa = ev["false_alarms"]
    return {"evaluated_hours": ev["evaluated_hours"], "evaluated_days": ev["evaluated_days"],
            "n_episodes": ev["n_episodes"], "alarm_days": ev["alarm_days"],
            "covered_positives": ev["covered_positives"], "caught": ev["caught"],
            "false_alarm_episodes": fa["n"], "unexplained": fa["unexplained"]}


def derived(c: dict[str, Any] | None) -> dict[str, Any] | None:
    """Rates from the counts. The venue-year divisor is the module's HOURS_PER_YEAR, exactly as in detector_eval."""
    if c is None:
        return None
    years = c["evaluated_hours"] / de.HOURS_PER_YEAR
    rec = c["caught"] / c["covered_positives"] if c["covered_positives"] else None
    n_true = c["n_episodes"] - c["false_alarm_episodes"]
    prec = n_true / c["n_episodes"] if c["n_episodes"] else None
    return {**c, "venue_years": years, "recall": rec,
            "fa_per_venue_year": c["false_alarm_episodes"] / years if years > 0 else None,
            "unexplained_per_venue_year": c["unexplained"] / years if years > 0 else None,
            "episode_precision": prec, "episode_f1": de._f1(rec, prec),
            "alarm_day_share": c["alarm_days"] / c["evaluated_days"] if c["evaluated_days"] else None}


def pool(points: list[dict[str, Any] | None]) -> dict[str, Any] | None:
    """Sum counts over the venues where the method exists (a Bitstamp-side label counts at each venue)."""
    pts = [p for p in points if p is not None]
    return {k: sum(p[k] for p in pts) for k in pts[0]} if pts else None


def sweep(data: dict[str, de.VenueData], labels: dict[str, list[de.Episode]]) -> dict[str, Any]:
    split = {v: de._split(labels.get(v, [])) for v in data}
    out: dict[str, Any] = {}
    for method, pname, values in method_specs():
        rows: dict[str, Any] = {}
        for p in values:
            counts = {v: _point(de.evaluate(_flags(vd, method, p), *split[v])) for v, vd in data.items()}
            rows[_num(p)] = {"param": {pname: p},
                             **{v: derived(c) for v, c in counts.items()}, "pooled": derived(pool(list(counts.values())))}
        out[method] = rows
    return out


def frontier(points: list[tuple[float | None, float | None, str]]) -> list[dict[str, Any]]:
    """False alarms per venue-year at each recall level reached: the minimum over points that reach at least that recall."""
    pts = [(r, f, lab) for r, f, lab in points if r is not None and f is not None and r > 0]
    out = []
    for level in sorted({r for r, _, _ in pts}):
        best = min(((f, lab) for r, f, lab in pts if r >= level), key=lambda t: (t[0], t[1]))
        out.append({"recall": level, "fa_per_venue_year": best[0], "at": best[1]})
    return out


def min_fa_at(points: list[tuple[float | None, float | None, str]], level: float) -> float | None:
    """Smallest false-alarm rate among points whose recall is at least ``level`` (None if never reached)."""
    ok = [f for r, f, _ in points if r is not None and f is not None and r >= level - 1e-12]
    return min(ok) if ok else None


def _curve(sw: dict[str, Any], method: str, scope: str) -> list[tuple[float | None, float | None, str]]:
    pts = []
    for key, row in sw[method].items():
        d = row.get(scope)
        if d is not None:
            pts.append((d["recall"], d["fa_per_venue_year"], f"{next(iter(row['param']))}={key}"))
    return pts


def curves(sw: dict[str, Any]) -> dict[str, Any]:
    """Frontier and matched-recall false-alarm rates per method and scope, plus the largest recall reached."""
    out: dict[str, Any] = {}
    for method in sw:
        out[method] = {}
        for scope in SCOPES:
            pts = _curve(sw, method, scope)
            out[method][scope] = ({"frontier": frontier(pts), "max_recall": max((r for r, _, _ in pts if r is not None), default=None),
                                   "at_recall": {_num(lv): min_fa_at(pts, lv) for lv in RECALL_LEVELS}} if pts else None)
    return out


def dominance(sw: dict[str, Any]) -> dict[str, Any]:
    """Pointwise (same threshold) comparison of the detector at 0.25 with B1 and the two-asset rule.

    'dominates' means recall >= and false alarms <= with at least one strict; recall None is treated as 0."""
    det = sw["detector_a0.25"]
    out: dict[str, Any] = {}
    for scope in SCOPES:
        out[scope] = {}
        for other in ("b1", "two_asset"):
            rows = []
            for key, row in det.items():
                d, o = row.get(scope), sw[other][key].get(scope)
                if d is None or o is None:
                    continue
                dr, orr = d["recall"] or 0.0, o["recall"] or 0.0
                df, of = d["false_alarm_episodes"], o["false_alarm_episodes"]
                relation = ("dominates" if dr >= orr and df <= of and (dr > orr or df < of)
                            else "identical" if dr == orr and df == of
                            else "dominated" if orr >= dr and of <= df else "incomparable")
                rows.append({"threshold_bps": float(key), "detector_recall": d["recall"], f"{other}_recall": o["recall"],
                             "detector_false_alarms": df, f"{other}_false_alarms": of, "relation": relation})
            out[scope][other] = rows
    return out


# ---------------------------------------------------------------- exposure and label reconciliation

def exposure(data: dict[str, de.VenueData], labels: dict[str, list[de.Episode]], sw: dict[str, Any]) -> dict[str, Any]:
    """Headline-point false-alarm denominators per venue and method, and the recall denominators against the label list."""
    t, a, k = HEADLINE["threshold"], HEADLINE["agreement"], HEADLINE["k"]
    heads = {"detector": ("detector_a0.25", _num(t)), "b1": ("b1", _num(t)), "two_asset": ("two_asset", _num(t)),
             "b2": ("b2", _num(k)), "b3": ("b3", _num(t))}
    per: dict[str, Any] = {}
    for v in VENUES:
        per[v] = {}
        for name, (m, key) in heads.items():
            d = sw[m][key][v]
            if d is None:
                per[v][name] = None
                continue
            per[v][name] = {"evaluated_hours": d["evaluated_hours"], "hours_per_year_divisor": de.HOURS_PER_YEAR,
                            "venue_years": d["venue_years"], "venue_years_at_8760": d["evaluated_hours"] / 8760,
                            "false_alarm_episodes": d["false_alarm_episodes"], "fa_per_venue_year": d["fa_per_venue_year"],
                            "fa_per_venue_year_at_8760": d["false_alarm_episodes"] / (d["evaluated_hours"] / 8760),
                            "covered_positives": d["covered_positives"], "caught": d["caught"]}
    b = per["binance_us"]
    bus_note = None
    if b["detector"] and b["b1"] and b["detector"]["false_alarm_episodes"] == b["b1"]["false_alarm_episodes"]:
        bus_note = (f"Binance.US: detector and B1 both have {b['b1']['false_alarm_episodes']} false-alarm episode(s); the rates "
                    f"{b['detector']['fa_per_venue_year']:.2f} vs {b['b1']['fa_per_venue_year']:.2f} differ only because the detector "
                    f"is evaluated on {b['detector']['evaluated_hours']:,} hours (BTC and the second-asset gap both present) and "
                    f"B1 on {b['b1']['evaluated_hours']:,} hours (BTC gap present).")
    split = {v: de._split(labels.get(v, [])) for v in data}
    rec: dict[str, Any] = {}
    for v in VENUES:
        det_positives = []
        ev = de.evaluate(_flags(data[v], "detector_a0.25", t), *split[v])
        for r in ev["positives"]:
            det_positives.append({"id": r["id"], "type": r["type"], "label_venue": r["label_venue"],
                                  "window": r["window"], "covered": r["covered"], "caught": r["caught"]})
        n_own = sum(1 for r in det_positives if r["label_venue"] == v)
        rec[v] = {"positives_in_scope": len(det_positives), "own_venue_positives": n_own,
                  "reference_side_bitstamp_positives": sum(r["label_venue"] == "bitstamp" for r in det_positives),
                  "covered_by_method_at_headline": {name: (None if per[v][name] is None else per[v][name]["covered_positives"])
                                                    for name in heads},
                  "positives": det_positives}
    ids = {v: {r["id"]: r for r in rec[v]["positives"] if r["covered"]} for v in VENUES}
    unique = {i for v in VENUES for i in ids[v]}
    pooled_ids = {"covered_entries": sum(len(ids[v]) for v in VENUES), "unique_covered_labels": len(unique),
                  "unique_caught_at_any_venue": len({i for v in VENUES for i, r in ids[v].items() if r["caught"]}),
                  "labels_counted_at_several_venues": sorted(i for i in unique if sum(i in ids[v] for v in VENUES) > 1)}
    return {"headline_point": {"threshold_bps": t, "agreement": a, "b2_k": k}, "per_venue_method": per,
            "pooled_detector_denominator": pooled_ids,
            "binance_us_note": bus_note, "recall_denominators": rec,
            "recall_note": ("A positive is covered when at least half of its truth-window days have evaluated hours. Under D1 "
                            "reference-side Bitstamp labels (BST-*) are positives at every venue measured against Bitstamp, so the "
                            "pooled covered count adds each such label once per venue where it is covered. B2 loses its first "
                            "30 days of each series to the trailing window, which can change coverage."),
            "false_alarm_denominator": ("evaluated venue-hours / HOURS_PER_YEAR; the module divisor is 24 x 365.25 = 8,766, "
                                        "and the _at_8760 columns repeat the rate with 8,760."),
            "label_file_positive_counts": _label_counts()}


def _label_counts(path: Path | None = None) -> dict[str, Any]:
    eps = json.loads((path or ROOT / "configs/fiat_rail_labels.json").read_text())["episodes"]
    counts: dict[str, int] = {}
    for e in eps:
        if e["type"] in de.POSITIVE_TYPES and e["id"] not in de.EXCLUDED_LABELS and e.get("first_public_report_date"):
            counts[de.norm_venue(e["venue"])] = counts.get(de.norm_venue(e["venue"]), 0) + 1
    return {"positives_by_label_venue": dict(sorted(counts.items())), "excluded": de.EXCLUDED_LABELS}


# ---------------------------------------------------------------- timeline

def _runs(days: list[date]) -> list[tuple[date, date]]:
    out: list[tuple[date, date]] = []
    for d in sorted(days):
        if out and d - out[-1][1] == timedelta(days=1):
            out[-1] = (out[-1][0], d)
        else:
            out.append((d, d))
    return out


def timeline(L: pd.Series, labels_path: Path, probe_path: Path, flags_by_method: dict[str, pd.Series]) -> dict[str, Any]:
    """First 2018-H2 day with a Bitfinex-Bitstamp daily BTC gap above 100 bps (committed daily series), how long it
    stayed above, and the label dates for the public reports. No web lookups; label dates come from the label file."""
    daily = json.loads(probe_path.read_text())["daily_gaps_bps"]["bitfinex-bitstamp"]["BTC"]
    s = pd.Series({date.fromisoformat(k): v for k, v in daily.items()}).sort_index()
    labs = {e["id"]: e for e in json.loads(labels_path.read_text())["episodes"]}
    nyag = date.fromisoformat(labs["BFX-2018-06"]["first_public_report_date"])

    def runs_above(series: pd.Series, lo: date, hi: date) -> list[dict[str, Any]]:
        days = [d for d, x in series.items() if lo <= d <= hi and abs(x) > BIG_GAP_BPS]
        return [{"start": str(a), "end": str(b), "days": (b - a).days + 1,
                 "max_abs_bps": float(series.reindex([a + timedelta(days=i) for i in range((b - a).days + 1)]).abs().max())}
                for a, b in _runs(days)]

    h2 = runs_above(s, *H2_2018)
    first = date.fromisoformat(h2[0]["start"]) if h2 else None
    until_nyag = runs_above(s, first, nyag - timedelta(days=1)) if first else []
    days_above = sum(r["days"] for r in until_nyag)
    # the same fact from the hourly series used by the sweep: daily median of hourly L
    hourly_daily = L.groupby(de._utc(L.index).tz_localize(None).normalize()).median()
    hs = pd.Series({ts.date(): float(x) for ts, x in hourly_daily.items()})
    h2h = runs_above(hs, *H2_2018)
    alarms = {}
    for m, f in flags_by_method.items():
        days = [d for d in de.alarm_days(f) if H2_2018[0] <= d <= H2_2018[1]]
        alarms[m] = str(days[0]) if days else None

    def lab(i: str) -> dict[str, Any]:
        e = labs[i]
        return {"id": i, "type": e["type"], "first_public_report_date": e["first_public_report_date"],
                "impairment_start": e.get("impairment_start"), "evidence_quality": e.get("evidence_quality")}

    bitfinex_pos = [lab(i) for i, e in labs.items() if de.norm_venue(e["venue"]) == "bitfinex" and e["type"] in de.POSITIVE_TYPES]
    return {
        "daily_btc_gap_source": f"{PROBE} daily_gaps_bps/bitfinex-bitstamp/BTC (Bitfinex minus Bitstamp, bps)",
        "first_day_above_100bps_2018H2": None if first is None else str(first),
        "first_day_gap_bps": None if first is None else float(s[first]),
        "runs_above_100bps_2018H2": h2,
        "first_run_days": h2[0]["days"] if h2 else None,
        "runs_above_100bps_first_day_to_day_before_nyag": until_nyag,
        "days_above_100bps_first_day_to_day_before_nyag": days_above,
        "calendar_days_first_day_to_nyag": None if first is None else (nyag - first).days,
        "months_first_day_to_nyag": None if first is None else (nyag - first).days / DAYS_PER_MONTH,
        "hourly_daily_median_runs_above_100bps_2018H2": h2h,
        "first_alarm_day_2018H2_by_method_at_100bps": alarms,
        "label_dates": {"first_public_reports_bitfinex_positives": bitfinex_pos,
                        "first_public_deposit_pause_report": lab("BFX-2018-04"),
                        "first_public_banking_partner_report_2018": lab("BFX-2018-03"),
                        "nyag_disclosure": lab("BFX-2018-06")},
        "framing": (f"The price measured the impairment continuously from {first} (first day the daily Bitfinex-Bitstamp BTC gap "
                    f"exceeded 100 bps in 2018-H2), while the documented disclosure of the loss came on {nyag} (NYAG complaint). "
                    "The Noble Bank and deposit-pause reports (2018-09-30, 2018-10-11) were public earlier and are labels, not "
                    "prices."),
    }


# ---------------------------------------------------------------- driver

def compute(data: dict[str, de.VenueData], labels: dict[str, list[de.Episode]], labels_path: Path, probe_path: Path) -> dict[str, Any]:
    sw = sweep(data, labels)
    t = HEADLINE["threshold"]
    bfx = data["bitfinex"]
    tl = timeline(bfx.L, labels_path, probe_path,
                  {"detector": _flags(bfx, "detector_a0.25", t), "b1": _flags(bfx, "b1", t),
                   "two_asset": _flags(bfx, "two_asset", t), "b2": _flags(bfx, "b2", HEADLINE["k"])})
    return {
        "design": {"thresholds_bps": list(THRESHOLDS), "detector_agreements": list(AGREEMENTS), "b2_k": list(B2_KS),
                   "recall_levels": list(RECALL_LEVELS), "scope": "all months, all venues (detector_eval scope 'all')",
                   "headline_point": HEADLINE, "label_amendment": "D1",
                   "second_asset": ("the detector's own second-asset gap per venue: Bitfinex ETH vs Coinbase ETH, Coinbase ETH vs "
                                    "Bitstamp ETH, Binance.US USDT/USD vs Bitstamp USDT/USD"),
                   "b2_note": "B2 has no bps threshold; its curve is indexed by k",
                   "b3_note": "B3 exists for Bitfinex only (USTUSD from 2018-11); pooled B3 is the Bitfinex point alone",
                   "pooled": "sum of counts over the venues where the method exists"},
        "sweep": sw, "curves": curves(sw), "dominance": dominance(sw),
        "exposure": exposure(data, labels, sw), "timeline": tl,
    }


def run(raw: Path, manifest: Path, labels: Path, probe: Path) -> dict[str, Any]:
    data, meta = de.build_venues(raw, manifest)
    lab = {v: de.load_labels(labels, v, also=de.REFERENCE_LABELS[v]) for v in data}
    out = compute(data, lab, labels, probe)
    out["data"] = meta
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=ROOT / "data/raw")
    parser.add_argument("--manifest", type=Path, default=ROOT / "reports/events/acquisition_manifest.json")
    parser.add_argument("--labels", type=Path, default=ROOT / "configs/fiat_rail_labels.json")
    parser.add_argument("--probe", type=Path, default=ROOT / PROBE)
    parser.add_argument("--out", type=Path, default=ROOT / "reports/rescue/monitor_sweep.json")
    args = parser.parse_args()
    out = run(args.raw, args.manifest, args.labels, args.probe)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(f"WROTE {args.out}")


if __name__ == "__main__":
    main()
