"""Q2 calibration (autoresearch/program_q2.md): one threshold per detector on calm hours only.

Target: at most 1 false alarm per 1,000 calm hours, pooled over events. The threshold is the smallest value whose pooled alarm-episode
count is <= floor(N_calm / 1000) (alarms of P and S1 are runs of consecutive hours over tau; S2 alarms are CUSUM resets). The
discrete count means the realised rate is at or just below the target and is reported. Event windows are never read here.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import common as C
from . import detectors as D

TARGET_PER_1000 = 1.0
H_STEP, H_MAX = 0.5, 1e8


def allowed(n_calm: int) -> int:
    return int(np.floor(n_calm * TARGET_PER_1000 / 1000.0 + 1e-9))


def calibrate_threshold(stats: list[pd.Series], n_calm: int) -> tuple[float, int]:
    """Smallest tau such that the pooled episodes(|stat| >= tau') <= allowed for every tau' >= tau (scan down from the top; the
    episode count is not monotone in tau, e.g. a tiny tau gives one long run). ``stats`` are calm-hour series (NaN = no obs)."""
    cap = allowed(n_calm)
    vals = np.unique(np.abs(np.concatenate([s.dropna().to_numpy() for s in stats])))
    best, best_n = (float(vals[-1]) + 1e-9 if len(vals) else 0.0), 0
    for tau in vals[::-1]:
        n = sum(D.episodes(D.threshold_alarms(s, tau)) for s in stats)
        if n > cap:
            break
        best, best_n = float(tau), int(n)
    return best, best_n


def calibrate_cusum(gaps: list[pd.Series], n_calm: int) -> tuple[float, int]:
    """Smallest h (to 0.5 bps) with pooled alarms <= allowed: doubling to a feasible h, then bisection. Each series is one
    contiguous calm segment; the count is non-increasing in h up to resets, and bisection is deterministic."""
    cap = allowed(n_calm)

    def count(h: float) -> int:
        return sum(int(D.cusum(g, h)[0].sum()) for g in gaps)

    lo, hi = 0.0, H_STEP
    while count(hi) > cap:
        lo, hi = hi, hi * 2
        if hi > H_MAX:
            raise RuntimeError("no CUSUM threshold up to H_MAX")
    while hi - lo > H_STEP:
        mid = np.round((lo + hi) / 2 / H_STEP) * H_STEP
        if mid <= lo or mid >= hi:
            break
        lo, hi = (mid, hi) if count(mid) > cap else (lo, mid)
    return float(hi), count(hi)


def segments(idx: pd.DatetimeIndex) -> list[pd.DatetimeIndex]:
    if len(idx) == 0:
        return []
    cut = np.flatnonzero(np.diff(idx.asi8) != 3600 * 10**9) + 1
    return [idx[a:b] for a, b in zip(np.r_[0, cut], np.r_[cut, len(idx)])]


def event_series(markets, unit: str, eid: str) -> dict:
    """Causal detector inputs for one event on its calm hours (and the single-pair market chosen from them)."""
    calm = C.calm_index(eid)
    full = pd.date_range(calm[0], calm[-1], freq="h", tz="UTC") if len(calm) else calm
    market = D.top_volume_market(markets, unit, calm)
    p = D.pooled_statistic(markets, unit)
    g = D.single_pair_gap(markets, market)
    return {"calm": calm, "market": market, "P": p.reindex(calm), "S1": g.reindex(calm),
            "S2": [g.reindex(seg) for seg in segments(calm)], "full": full}


def build() -> dict:
    cache, per, P, S1, S2, n_calm = {}, {}, [], [], [], 0
    for eid, unit, a, b, panel in C.EVENTS:
        if panel not in cache:
            cache[panel] = C.load(panel)
        s = event_series(cache[panel][0], unit, eid)
        per[eid] = {"calm_hours": int(len(s["calm"])), "single_pair_market": s["market"],
                    "calm_first_utc": str(s["calm"][0]), "calm_last_utc": str(s["calm"][-1]),
                    "obs_hours": {"P": int(s["P"].notna().sum()), "S1": int(s["S1"].notna().sum())}}
        n_calm += len(s["calm"])
        P.append(s["P"]); S1.append(s["S1"]); S2 += s["S2"]
    tp, np_ = calibrate_threshold(P, n_calm)
    t1, n1 = calibrate_threshold(S1, n_calm)
    h2, n2 = calibrate_cusum(S2, n_calm)
    rate = lambda n: 1000.0 * n / n_calm
    return {"preregistration": "autoresearch/program_q2.md", "n_calm_hours": n_calm, "target_false_alarms_per_1000_calm_hours": TARGET_PER_1000,
            "allowed_false_alarms": allowed(n_calm), "events": per,
            "thresholds_bps": {"tau_P": tp, "tau_S1": t1, "h_S2": h2},
            "false_alarms": {"P": np_, "S1": n1, "S2": n2},
            "realised_per_1000_calm_hours": {"P": rate(np_), "S1": rate(n1), "S2": rate(n2)},
            "note": "calm hours only; event windows not read"}


if __name__ == "__main__":
    res = build()
    C.CALIBRATION.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("n_calm_hours", "thresholds_bps", "false_alarms", "realised_per_1000_calm_hours")}, indent=1))
    for e, v in res["events"].items():
        print(e, v)
