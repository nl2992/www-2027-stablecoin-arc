"""Continuous evaluation of the hour-level ledger-failure detector (frozen in docs/review/DETECTOR_PREREG.md).

Rule (not tuned here): hour flag |L| >= 100 bps and |S - L| <= 0.25 |L|; alarm day = UTC day with >= 6 flagged
hours; alarm episode = run of alarm days, runs separated by <= 3 non-alarm days merged. Baselines B1 (gap only),
B2 (trailing 30-day robust z) and B3 (Bitfinex USDT premium) feed the same day and episode logic.
Everything in this module is a function of dated labels and price series; nothing here chooses a headline.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from www_events.binance_klines import read_kline_zip, to_minute_grid, verify_checksum
from www_events.candles import load_venue_months

from .monitor import AGREE, THRESHOLD, classify
from .platform_dollar import dislocation, traded_log_close

MIN_HOURS = 6
MERGE_GAP_DAYS = 3
GRID_THRESHOLDS = (50.0, 100.0, 200.0)
GRID_AGREEMENTS = (0.1, 0.25, 0.5)
GRID = [(t, a) for t in GRID_THRESHOLDS for a in GRID_AGREEMENTS]
HOURS_PER_YEAR = 24 * 365.25
POSITIVE_TYPES = ("deposit_pause", "withdrawal_delay", "banking_partner_loss", "rail_shutdown")
PRE_DAYS, POST_DAYS_DEFAULT = 30, 90
LEAD_WINDOW_DAYS = 30
COVERAGE_MIN = 0.5
B2_WINDOW, B2_K, B2_MIN_OBS = "30D", 4.0, 360  # min_obs = half the nominal 720 hours (unspecified in the pre-registration)
P3_MAX_LEAD = 7
P4_MAX_ALARM_SHARE = 0.01
P1_MAX_PER_YEAR = 1.0
VENUES = ("bitfinex", "binance_us", "coinbase")
REFERENCE_LABELS = {"bitfinex": ("bitstamp",), "binance_us": ("bitstamp",), "coinbase": ("bitstamp",)}  # D1
METHODS = ("detector", "b1", "b2", "b3")
SEEN_BITFINEX = ({f"2017-{m:02d}" for m in range(2, 9)} | {f"2018-{m:02d}" for m in range(9, 13)}
                 | {f"2019-{m:02d}" for m in range(3, 8)})
SEEN_BINANCE_US_LAST = "2023-07"


# ---------------------------------------------------------------- flags, days, episodes

def hour_flags(L: pd.Series, S: pd.Series, threshold: float = THRESHOLD, agree: float = AGREE) -> pd.Series:
    """Detector hour flag on hours where both L and S exist (the evaluated hours); same rule as monitor.classify."""
    both = pd.concat([L, S], axis=1, keys=["L", "PD_USDT"]).dropna()
    return classify(both, threshold, agree)["ledger_flag"].astype(bool)


def gap_flags(L: pd.Series, threshold: float = THRESHOLD) -> pd.Series:
    """B1: |L| >= threshold with no second-asset agreement."""
    L = L.dropna()
    return (L.abs() >= threshold).astype(bool)


def robust_z_flags(L: pd.Series, window: str = B2_WINDOW, k: float = B2_K, min_obs: int = B2_MIN_OBS) -> pd.Series:
    """B2: |L - median| >= k * 1.4826 * MAD over the trailing window, which excludes the current hour (no look-ahead).

    Hours with fewer than ``min_obs`` window observations, or a zero MAD, are not evaluated (dropped).
    """
    L = L.dropna().sort_index().astype(float)
    roll = L.rolling(window, closed="left", min_periods=min_obs)
    med = roll.median()
    mad = roll.apply(lambda x: np.median(np.abs(x - np.median(x))), raw=True)
    ok = med.notna() & mad.notna() & (mad > 0)
    return ((L - med).abs() >= k * 1.4826 * mad)[ok].astype(bool)


def premium_flags(D: pd.Series, threshold: float = THRESHOLD) -> pd.Series:
    """B3: |1e4 log P(USDT/USD)| >= threshold, where D is that premium in bps."""
    D = D.dropna()
    return (D.abs() >= threshold).astype(bool)


def _utc(index: pd.Index) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(index)
    return idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")


def _daynum(index: pd.Index) -> np.ndarray:
    return np.asarray((_utc(index).tz_localize(None).normalize() - pd.Timestamp("1970-01-01")).days, dtype=np.int64)


def _num(d: date) -> int:
    return (d - date(1970, 1, 1)).days


def alarm_days(flags: pd.Series, min_hours: int = MIN_HOURS) -> list[date]:
    """UTC days with at least ``min_hours`` flagged hours."""
    if len(flags) == 0:
        return []
    counts = pd.Series(flags.to_numpy(dtype=bool).astype(int)).groupby(_daynum(flags.index)).sum()
    return [date(1970, 1, 1) + timedelta(days=int(n)) for n, c in counts.items() if c >= min_hours]


def alarm_episodes(days: list[date], merge_gap_days: int = MERGE_GAP_DAYS) -> list[tuple[date, date]]:
    """Runs of alarm days; runs separated by ``merge_gap_days`` or fewer non-alarm days are merged."""
    out: list[tuple[date, date]] = []
    for d in sorted(set(days)):
        if out and (d - out[-1][1]).days - 1 <= merge_gap_days:
            out[-1] = (out[-1][0], d)
        else:
            out.append((d, d))
    return out


# ---------------------------------------------------------------- labels

@dataclass(frozen=True)
class Episode:
    id: str
    venue: str
    type: str
    report: date
    window: tuple[date, date]
    positive: bool
    extra: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)


def norm_venue(name: str) -> str:
    """'Binance.US' / 'binance-us' / 'binance_us' -> 'binance_us'."""
    out = "".join(c if c.isalnum() else "_" for c in name.strip().lower())
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_")


def _d(x: Any) -> date | None:
    return date.fromisoformat(str(x)[:10]) if x not in (None, "") else None


def truth_window(report: date, impairment_end: date | None, impairment_start: date | None = None) -> tuple[date, date]:
    """Positives: [min(report, impairment_start) - 30 d, impairment_end if documented, else report + 90 d].

    Amendment D1 (pre-data): a retrospectively disclosed impairment (start well before the report) gets a window
    that starts at the impairment; a window that would end before it starts ends at report + 90 d instead.
    """
    lo = min(report, impairment_start or report) - timedelta(days=PRE_DAYS)
    hi = impairment_end or report + timedelta(days=POST_DAYS_DEFAULT)
    return lo, (hi if hi >= lo else report + timedelta(days=POST_DAYS_DEFAULT))


EXCLUDED_LABELS = {"CB-2019-01": "GBP rail; the monitored quantity is the USD ledger (amendment D1)"}
HIGH_QUALITY = ("primary_statement", "major_outlet")


def load_labels(path: Path, venue: str, also: tuple[str, ...] = (), min_quality: tuple[str, ...] | None = None) -> list[Episode]:
    """Positive and confounder episodes at ``venue`` (venue names compared after normalisation).

    Confounder windows are narrow (impairment_start or report date .. impairment_end or report date, no padding),
    so that fewer false alarms are explained away.
    """
    want = norm_venue(venue)
    venues = {want, *(norm_venue(a) for a in also)}  # D1: a pair gap cannot say which side's dollar moved
    out = []
    for e in json.loads(Path(path).read_text())["episodes"]:
        if norm_venue(e["venue"]) not in venues or e["id"] in EXCLUDED_LABELS:
            continue
        if min_quality is not None and e.get("evidence_quality") not in min_quality:
            continue
        typ = e["type"]
        start, end, report = _d(e.get("impairment_start")), _d(e.get("impairment_end")), _d(e.get("first_public_report_date"))
        if typ in POSITIVE_TYPES:
            if report is None:
                continue
            retro = start is not None and report > start + timedelta(days=LEAD_WINDOW_DAYS)
            out.append(Episode(e["id"], want, typ, report, truth_window(report, end, start), True,
                               {"retrospective": retro, "label_venue": norm_venue(e["venue"])}))
        elif typ == "confounder":
            lo = start or report
            if lo is None:
                continue
            hi = end or report or lo
            out.append(Episode(e["id"], want, typ, report or lo, (lo, max(lo, hi)), False))
    return out


# ---------------------------------------------------------------- scopes

def scope_mask(index: pd.Index, venue: str, scope: str) -> np.ndarray:
    """Boolean mask of hours in ``scope`` ('all' | 'seen' | 'unseen') by the pre-registration's section 1."""
    n = len(index)
    if scope == "all":
        return np.ones(n, bool)
    months = _utc(index).strftime("%Y-%m")
    if venue == "bitfinex":
        seen = np.asarray(months.isin(SEEN_BITFINEX), bool)
    elif venue == "binance_us":
        seen = np.asarray(months <= SEEN_BINANCE_US_LAST, bool)
    else:
        seen = np.zeros(n, bool)
    if scope == "seen":
        return seen
    if scope == "unseen":
        return ~seen
    raise ValueError(scope)


def _overlap(a: tuple[date, date], b: tuple[date, date]) -> bool:
    return a[0] <= b[1] and a[1] >= b[0]


# ---------------------------------------------------------------- metrics

def evaluate(flags: pd.Series | None, positives: list[Episode], confounders: list[Episode], *,
             min_hours: int = MIN_HOURS, merge_gap_days: int = MERGE_GAP_DAYS) -> dict[str, Any] | None:
    """Section 4 metrics for one hour-flag series (index = evaluated hours). None if the series does not exist."""
    if flags is None:
        return None
    flags = flags.astype(bool).sort_index()
    days = alarm_days(flags, min_hours)
    eps = alarm_episodes(days, merge_gap_days)
    nums = _daynum(flags.index)
    eval_days = set(np.unique(nums).tolist())
    n_hours = int(len(flags))
    windows = [p.window for p in positives]

    recs = []
    for p in positives:
        lo, hi = _num(p.window[0]), _num(p.window[1])
        covered = (sum(1 for d in range(lo, hi + 1) if d in eval_days) / (hi - lo + 1)) >= COVERAGE_MIN
        caught = covered and any(_overlap(p.window, e) for e in eps)
        retro = bool(p.extra.get("retrospective"))
        w = p.window if retro else (p.report - timedelta(days=LEAD_WINDOW_DAYS), p.report + timedelta(days=LEAD_WINDOW_DAYS))
        first = next((d for d in days if w[0] <= d <= w[1]), None)
        recs.append({"id": p.id, "type": p.type, "report": str(p.report), "window": [str(p.window[0]), str(p.window[1])],
                     "covered": bool(covered), "caught": bool(caught), "retrospective": retro,
                     "label_venue": p.extra.get("label_venue"),
                     "first_alarm_day": None if first is None else str(first),
                     "lead_days": None if first is None else (first - p.report).days})
    covered_n = sum(r["covered"] for r in recs)
    caught_n = sum(r["caught"] for r in recs)

    fa = []
    for e in eps:
        if any(_overlap(e, w) for w in windows):
            continue
        fa.append({"start": str(e[0]), "end": str(e[1]),
                   "class": "confounder" if any(_overlap(e, c.window) for c in confounders) else "unexplained"})
    n_conf = sum(f["class"] == "confounder" for f in fa)
    years = n_hours / HOURS_PER_YEAR
    rate = (lambda n: n / years) if years > 0 else (lambda n: None)

    truth = np.zeros(n_hours, bool)
    for lo, hi in windows:
        truth |= (nums >= _num(lo)) & (nums <= _num(hi))
    f = flags.to_numpy()
    tp = int((f & truth).sum())
    n_eval_days = len(eval_days)
    return {
        "evaluated_hours": n_hours, "evaluated_days": n_eval_days, "venue_years": years, "flagged_hours": int(f.sum()),
        "alarm_days": len(days), "alarm_day_share": len(days) / n_eval_days if n_eval_days else None,
        "episodes": [[str(s), str(e)] for s, e in eps], "n_episodes": len(eps),
        "positives": recs, "covered_positives": covered_n, "caught": caught_n,
        "recall": caught_n / covered_n if covered_n else None,
        "false_alarms": {"n": len(fa), "confounder": n_conf, "unexplained": len(fa) - n_conf, "episodes": fa,
                         "per_venue_year": {"total": rate(len(fa)), "confounder": rate(n_conf),
                                            "unexplained": rate(len(fa) - n_conf)}},
        "n_episodes_true": len(eps) - len(fa),
        "episode_precision": (len(eps) - len(fa)) / len(eps) if eps else None,
        "episode_f1": _f1(caught_n / covered_n if covered_n else None, (len(eps) - len(fa)) / len(eps) if eps else None),
        "hour_precision": tp / int(f.sum()) if f.sum() else None,
        "hour_recall": tp / int(truth.sum()) if truth.sum() else None,
    }


def _f1(recall: float | None, precision: float | None) -> float:
    if not recall or not precision:
        return 0.0
    return 2 * recall * precision / (recall + precision)


def pooled_f1(evs: list[dict[str, Any]]) -> float:
    """Episode F1 pooled over venues: recall over covered positives, precision over alarm episodes."""
    cov = sum(e["covered_positives"] for e in evs)
    cau = sum(e["caught"] for e in evs)
    tot = sum(e["n_episodes"] for e in evs)
    tru = sum(e["n_episodes_true"] for e in evs)
    return _f1(cau / cov if cov else None, tru / tot if tot else None)


def _brief(ev: dict[str, Any] | None) -> dict[str, Any] | None:
    if ev is None:
        return None
    return {"evaluated_hours": ev["evaluated_hours"], "n_episodes": ev["n_episodes"], "alarm_days": ev["alarm_days"],
            "covered_positives": ev["covered_positives"], "caught": ev["caught"], "recall": ev["recall"],
            "false_alarm_episodes": ev["false_alarms"]["n"], "unexplained": ev["false_alarms"]["unexplained"],
            "unexplained_per_venue_year": ev["false_alarms"]["per_venue_year"]["unexplained"],
            "episode_f1": ev["episode_f1"]}


# ---------------------------------------------------------------- predictions (section 6)

def score_predictions(results: dict[str, dict[str, dict[str, dict[str, Any] | None]]]) -> dict[str, Any]:
    """Mechanical scoring. ``results[scope][venue][method]`` = evaluate() output (scopes 'all' and 'unseen' used).

    Resolutions of wording (conservative, i.e. harder to pass): P1 compares the unexplained rate at the unseen
    scope; P2 must hold at every venue with data (false alarms <= B1's AND recall >= B1's, a missing detector
    recall against a defined B1 recall fails); P3 fails when a caught positive has no alarm day by report + 30 d;
    P4 uses all covered days.
    """
    p1_venues = {}
    for v in ("bitfinex", "coinbase"):
        ev = results.get("unseen", {}).get(v, {}).get("detector")
        rate = None if ev is None else ev["false_alarms"]["per_venue_year"]["unexplained"]
        p1_venues[v] = {"unexplained_per_venue_year": rate,
                        "status": "UNDEFINED" if rate is None else ("PASS" if rate <= P1_MAX_PER_YEAR else "FAIL")}
    st = [x["status"] for x in p1_venues.values()]
    p1 = "FAIL" if "FAIL" in st and "UNDEFINED" not in st else ("PASS" if st == ["PASS", "PASS"] else "PARTIAL")
    p1_both_fail = st == ["FAIL", "FAIL"]

    p2_venues, p2_ok, p2_any = {}, True, False
    for v, m in results.get("all", {}).items():
        d, b = m.get("detector"), m.get("b1")
        if d is None or b is None:
            continue
        p2_any = True
        recall_ok = (b["recall"] is None) or (d["recall"] is not None and d["recall"] >= b["recall"])
        ok = d["false_alarms"]["n"] <= b["false_alarms"]["n"] and recall_ok
        p2_venues[v] = {"detector_false_alarms": d["false_alarms"]["n"], "b1_false_alarms": b["false_alarms"]["n"],
                        "detector_recall": d["recall"], "b1_recall": b["recall"], "status": "PASS" if ok else "FAIL"}
        p2_ok &= ok
    p2 = "UNDEFINED" if not p2_any else ("PASS" if p2_ok else "FAIL")

    leads, p3_fail = [], []
    for v, m in results.get("all", {}).items():
        d = m.get("detector")
        for r in (d["positives"] if d else []):
            if r["caught"] and not r.get("retrospective"):  # D1: no lead-time claim for retrospective disclosures
                leads.append({"venue": v, "id": r["id"], "lead_days": r["lead_days"]})
                if r["lead_days"] is None or r["lead_days"] > P3_MAX_LEAD:
                    p3_fail.append(r["id"])
    p3 = "UNDEFINED" if not leads else ("FAIL" if p3_fail else "PASS")

    cb = results.get("all", {}).get("coinbase", {}).get("detector")
    share = None if cb is None else cb["alarm_day_share"]
    p4 = {"status": "UNDEFINED" if share is None else ("PASS" if share < P4_MAX_ALARM_SHARE else "FAIL"),
          "alarm_days": None if cb is None else cb["alarm_days"], "covered_days": None if cb is None else cb["evaluated_days"],
          "alarm_day_share": share, "recall": None if cb is None else cb["recall"],
          "recall_note": None if cb is None or cb["covered_positives"] else "undefined: no covered positives"}
    return {"P1": {"status": p1, "venues": p1_venues}, "P2": {"status": p2, "venues": p2_venues},
            "P3": {"status": p3, "caught_leads": leads, "violations": p3_fail}, "P4": p4,
            "falsified": bool(p1_both_fail or p2 == "FAIL"),
            "falsification": {"P1_fails_at_both_venues": p1_both_fail, "P2_fails": p2 == "FAIL"}}


# ---------------------------------------------------------------- venue data

@dataclass
class VenueData:
    """Hourly series for one monitored venue (bps): L, second asset S, optional alternative-reference L, USDT premium."""
    L: pd.Series
    S: pd.Series
    L_alt: pd.Series | None = None
    D_usdt: pd.Series | None = None


def method_flags(vd: VenueData, method: str, threshold: float = THRESHOLD, agree: float = AGREE) -> pd.Series | None:
    if method == "detector":
        return hour_flags(vd.L, vd.S, threshold, agree)
    if method == "detector_alt_ref":
        return None if vd.L_alt is None else hour_flags(vd.L_alt, vd.S, threshold, agree)
    if method == "b1":
        return gap_flags(vd.L)
    if method == "b2":
        return robust_z_flags(vd.L)
    if method == "b3":
        return None if vd.D_usdt is None else premium_flags(vd.D_usdt)
    raise ValueError(method)


def _scoped(flags: pd.Series | None, venue: str, scope: str) -> pd.Series | None:
    return None if flags is None else flags[scope_mask(flags.index, venue, scope)]


def _split(labels: list[Episode]) -> tuple[list[Episode], list[Episode]]:
    return [e for e in labels if e.positive], [e for e in labels if not e.positive]


def _drop_window(flags: pd.Series, window: tuple[date, date]) -> pd.Series:
    n = _daynum(flags.index)
    return flags[~((n >= _num(window[0])) & (n <= _num(window[1])))]


def loeo(data: dict[str, VenueData], labels: dict[str, list[Episode]], *, min_hours: int = MIN_HOURS) -> dict[str, Any]:
    """Leave-one-episode-out: pick the grid point maximising pooled episode F1 without the held-out episode, then score it.

    Without the held-out episode means: its positive is removed and its truth-window days are dropped from that
    venue's evaluated hours. Ties go to the headline point, then to grid order.
    """
    flags = {(t, a): {v: _scoped(hour_flags(vd.L, vd.S, t, a), v, "all") for v, vd in data.items()} for t, a in GRID}
    split = {v: _split(labels.get(v, [])) for v in data}
    head = (THRESHOLD, AGREE)
    base = {v: evaluate(flags[head][v], *split[v], min_hours=min_hours) for v in data}
    rows = []
    for v in data:
        for r, p in zip(base[v]["positives"], split[v][0]):
            if not r["covered"]:
                continue
            best, best_key = None, None
            for i, g in enumerate(GRID):
                evs = []
                for v2 in data:
                    pos, conf = split[v2]
                    f = flags[g][v2]
                    if v2 == v:
                        pos = [q for q in pos if q.id != p.id]
                        f = _drop_window(f, p.window)
                    evs.append(evaluate(f, pos, conf, min_hours=min_hours))
                key = (-pooled_f1(evs), g != head, i)
                if best_key is None or key < best_key:
                    best, best_key = g, key
            ev = evaluate(flags[best][v], *split[v], min_hours=min_hours)
            held = next(x for x in ev["positives"] if x["id"] == p.id)
            rows.append({"venue": v, "id": p.id, "chosen_threshold": best[0], "chosen_agreement": best[1],
                         "train_f1": -best_key[0], "caught": held["caught"], "lead_days": held["lead_days"],
                         "headline_caught": r["caught"], "headline_lead_days": r["lead_days"]})
    n = len(rows)
    return {"episodes": rows, "n": n,
            "loeo_recall": sum(r["caught"] for r in rows) / n if n else None,
            "headline_recall": sum(r["headline_caught"] for r in rows) / n if n else None}


def report(data: dict[str, VenueData], labels: dict[str, list[Episode]]) -> dict[str, Any]:
    """Full evaluation of section 4-7 for already-built hourly venue data. ``labels[venue]`` from load_labels."""
    split = {v: _split(labels.get(v, [])) for v in data}
    results: dict[str, dict[str, dict[str, Any]]] = {}
    for scope in ("all", "seen", "unseen"):
        results[scope] = {v: {m: evaluate(_scoped(method_flags(vd, m), v, scope), *split[v]) for m in METHODS}
                          for v, vd in data.items()}
    robust: dict[str, Any] = {"grid": {}, "min_hours": {}, "alt_reference": {}}
    for v, vd in data.items():
        robust["grid"][v] = [{"threshold": t, "agreement": a,
                              **_brief(evaluate(hour_flags(vd.L, vd.S, t, a), *split[v]))} for t, a in GRID]
        robust["min_hours"][v] = {str(h): _brief(evaluate(method_flags(vd, "detector"), *split[v], min_hours=h))
                                  for h in (3, 12)}
        alt = method_flags(vd, "detector_alt_ref")
        if alt is not None:
            robust["alt_reference"][v] = {"coinbase_reference": _brief(evaluate(alt, *split[v])),
                                          "bitstamp_reference": _brief(results["all"][v]["detector"])}
    robust["loeo"] = loeo(data, labels)
    return {
        "rule": {"threshold_bps": THRESHOLD, "agreement": AGREE, "min_hours": MIN_HOURS, "merge_gap_days": MERGE_GAP_DAYS},
        "labels": {v: [{"id": e.id, "type": e.type, "report": str(e.report), "window": [str(e.window[0]), str(e.window[1])]}
                       for e in labels.get(v, [])] for v in data},
        "metrics": results,
        "predictions": score_predictions(results),
        "robustness": robust,
        "alarm_episodes": {v: {m: (None if results["all"][v][m] is None else results["all"][v][m]["episodes"])
                               for m in METHODS} for v in data},
    }


# ---------------------------------------------------------------- loading

def _months(first: str, last: str) -> list[str]:
    return [str(p) for p in pd.period_range(first, last, freq="M")]


def _hourly_dislocation(a: pd.Series | None, b: pd.Series | None) -> pd.Series | None:
    if a is None or b is None or len(a) == 0 or len(b) == 0:
        return None
    d = dislocation(a, b)
    return d.resample("1h").median().dropna() if len(d) else None


def _candle_log_close(directory: Path, pair: str, venue: str, manifest: Path, month: str) -> pd.Series | None:
    try:
        grid, _ = load_venue_months(directory, pair, "x", manifest, venue, [month])
    except FileNotFoundError:
        return None  # NOT_AVAILABLE or not yet downloaded
    return traded_log_close(grid, "x")


def _binance_us_log_close(directory: Path, pair: str, month: str) -> pd.Series | None:
    archive = directory / f"{pair}-1m-{month}.zip"
    if not archive.exists():
        return None
    verify_checksum(archive, archive.with_name(archive.name + ".CHECKSUM"))
    frame = read_kline_zip(archive).frame
    start = pd.Timestamp(month + "-01", tz="UTC")
    grid = to_minute_grid(frame, start, start + pd.offsets.MonthBegin(1), "x")
    return traded_log_close(grid, "x")


def _concat(parts: list[pd.Series]) -> pd.Series:
    return pd.concat(parts).sort_index() if parts else pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC"))


def build_venues(raw: Path, manifest: Path) -> tuple[dict[str, VenueData], dict[str, Any]]:
    """Hourly series per monitored venue from whatever months are on disk (missing months are skipped and listed)."""
    raw, months = Path(raw), _months("2017-01", "2023-12")
    missing: dict[str, list[str]] = {}

    def candle(venue: str, directory: str, pair: str, month: str) -> pd.Series | None:
        s = _candle_log_close(raw / directory, pair, venue, manifest, month)
        if s is None:
            missing.setdefault(f"{venue}:{pair}", []).append(month)
        return s

    acc: dict[str, list[pd.Series]] = {k: [] for k in ("bfx_L", "bfx_S", "bfx_L_alt", "bfx_D", "cb_L", "cb_S")}
    for m in months:
        bfx, bst = candle("bitfinex", "bitfinex", "BTCUSD", m), candle("bitstamp", "bitstamp", "BTCUSD", m)
        cb = candle("coinbase", "coinbase", "BTCUSD", m)
        bfx_e, cb_e = candle("bitfinex", "bitfinex", "ETHUSD", m), candle("coinbase", "coinbase", "ETHUSD", m)
        bst_e = candle("bitstamp", "bitstamp", "ETHUSD", m)
        ust = candle("bitfinex", "bitfinex", "USTUSD", m) if m >= "2018-11" else None  # Bitfinex ticker for USDT/USD
        for key, val in (("bfx_L", _hourly_dislocation(bfx, bst)), ("bfx_S", _hourly_dislocation(bfx_e, cb_e)),
                         ("bfx_L_alt", _hourly_dislocation(bfx, cb)), ("cb_L", _hourly_dislocation(cb, bst)),
                         ("cb_S", _hourly_dislocation(cb_e, bst_e))):
            if val is not None:
                acc[key].append(val)
        if ust is not None and len(ust):
            acc["bfx_D"].append((1e4 * ust).resample("1h").median().dropna())

    data = {"bitfinex": VenueData(_concat(acc["bfx_L"]), _concat(acc["bfx_S"]), _concat(acc["bfx_L_alt"]),
                                  _concat(acc["bfx_D"]) if acc["bfx_D"] else None),
            "coinbase": VenueData(_concat(acc["cb_L"]), _concat(acc["cb_S"]))}

    bus_dir = raw / "binance_us"
    bus_months = sorted(p.stem.rsplit("-1m-", 1)[1] for p in bus_dir.glob("BTCUSD-1m-*.zip")) if bus_dir.exists() else []
    bl, bs = [], []
    for m in bus_months:
        bst_b, bst_u = candle("bitstamp", "bitstamp", "BTCUSD", m), candle("bitstamp", "bitstamp", "USDTUSD", m)
        b, u = _binance_us_log_close(bus_dir, "BTCUSD", m), _binance_us_log_close(bus_dir, "USDTUSD", m)
        for lst, val in ((bl, _hourly_dislocation(b, bst_b)), (bs, _hourly_dislocation(u, bst_u))):
            if val is not None:
                lst.append(val)
    data["binance_us"] = VenueData(_concat(bl), _concat(bs))
    data = {v: data[v] for v in VENUES}
    meta = {"months_requested": [months[0], months[-1]], "binance_us_months_on_disk": bus_months,
            "missing_months": {k: v for k, v in sorted(missing.items())},
            "hours": {v: {"L": int(len(d.L)), "S": int(len(d.S))} for v, d in data.items()}}
    return data, meta


def run(raw: Path, manifest: Path, labels: Path) -> dict[str, Any]:
    data, meta = build_venues(raw, manifest)
    lab = {v: load_labels(labels, v, also=REFERENCE_LABELS[v]) for v in data}
    out = report(data, lab)
    hq = {v: load_labels(labels, v, also=REFERENCE_LABELS[v], min_quality=HIGH_QUALITY) for v in data}
    hq_split = {v: _split(hq[v]) for v in data}
    out["robustness"]["high_quality_labels"] = {
        v: _brief(evaluate(method_flags(vd, "detector"), *hq_split[v])) for v, vd in data.items()}
    out["amendment"] = "D1 (pre-data, docs/review/DETECTOR_PREREG.md section 9)"
    out["excluded_labels"] = EXCLUDED_LABELS
    out["data"] = meta
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--manifest", type=Path, default=Path("reports/events/acquisition_manifest.json"))
    parser.add_argument("--labels", type=Path, default=Path("configs/fiat_rail_labels.json"))
    parser.add_argument("--out", type=Path, default=Path("reports/rescue/detector_eval.json"))
    args = parser.parse_args()
    out = run(args.raw, args.manifest, args.labels)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out["predictions"][k] for k in ("P1", "P2", "P3", "P4", "falsified")}, indent=1)[:4000])
    for v, per in out["alarm_episodes"].items():
        for m, eps in per.items():
            print(v, m, "n/a" if eps is None else f"{len(eps)} episodes", (eps or [])[:40])


if __name__ == "__main__":
    main()
