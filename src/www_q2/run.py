"""Q2 scoring (autoresearch/program_q2.md). Needs reports/q2/labels.json and calibration.json (committed first); never retunes.

Lead = first alarm hour - onset hour, counted only for alarms in [onset - 72 h, onset + 72 h]; otherwise the event is a miss. For
the median and the bootstrap a miss is given the latest possible lead, +72 h (the pre-registration does not say how misses enter a
median; this choice is fixed here and the median over detected events only is reported beside it). Each detector runs causally over
a stream that starts at the first calm hour of the event (30 days before its window) and stops at onset + 72 h.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import common as C
from . import detectors as D

BOOT_DRAWS, BOOT_SEED = 1000, 20261023
HALF_WINDOW_H = 72
MISS_LEAD_H = HALF_WINDOW_H
DETECTORS = ("P", "S1", "S2")


def first_alarm_lead(flags: pd.Series, onset: pd.Timestamp) -> float | None:
    w = flags[(flags.index >= onset - pd.Timedelta(hours=HALF_WINDOW_H)) & (flags.index <= onset + pd.Timedelta(hours=HALF_WINDOW_H))]
    hit = w[w]
    return None if hit.empty else float((hit.index[0] - onset) / pd.Timedelta(hours=1))


def alarms_for_event(markets, unit: str, eid: str, onset: pd.Timestamp, th: dict) -> dict[str, pd.Series]:
    calm = C.calm_index(eid)
    start, stop = calm[0], onset + pd.Timedelta(hours=HALF_WINDOW_H)
    market = D.top_volume_market(markets, unit, calm)
    p = D.pooled_statistic(markets, unit)[start:stop]
    g = D.single_pair_gap(markets, market)[start:stop]
    return {"P": D.threshold_alarms(p, th["tau_P"]), "S1": D.threshold_alarms(g, th["tau_S1"]),
            "S2": D.cusum(g, th["h_S2"])[0]}


def median_lead(leads: list[float | None]) -> float:
    return float(np.median([MISS_LEAD_H if x is None else x for x in leads]))


def bootstrap(leads: dict[str, list[float | None]]) -> dict:
    n = len(leads["P"])
    arr = {d: np.array([MISS_LEAD_H if x is None else x for x in leads[d]], float) for d in DETECTORS}
    rng = np.random.default_rng(BOOT_SEED)
    draws = rng.integers(0, n, size=(BOOT_DRAWS, n))
    out = {}
    for comp in ("S1", "S2"):
        diff = np.median(arr["P"][draws], axis=1) - np.median(arr[comp][draws], axis=1)
        out[f"P_minus_{comp}"] = {"point": float(np.median(arr["P"]) - np.median(arr[comp])),
                                  "ci95": [float(np.quantile(diff, 0.025)), float(np.quantile(diff, 0.975))],
                                  "mean_of_draws": float(diff.mean())}
    return {"draws": BOOT_DRAWS, "seed": BOOT_SEED, "unit": "event", "n_events": n, "differences_hours": out}


def verdict(boot: dict, misses: dict[str, int]) -> dict:
    out = {}
    for comp in ("S1", "S2"):
        b = boot["differences_hours"][f"P_minus_{comp}"]
        earlier, upper_below_0, no_more_misses = b["point"] < 0, b["ci95"][1] < 0, misses["P"] <= misses[comp]
        if earlier and upper_below_0 and no_more_misses:
            res = "win"
        elif b["ci95"][0] > 0 and misses["P"] >= misses[comp]:
            res = "loss"
        elif b["ci95"][0] <= 0 <= b["ci95"][1]:
            res = "tie"
        else:
            res = "loss" if b["point"] > 0 else "no success (interval excludes 0 but misses condition fails)"
        out[comp] = {"P_median_earlier": bool(earlier), "ci_upper_below_0": bool(upper_below_0),
                     "P_misses_not_more": bool(no_more_misses), "outcome": res}
    return out


def run() -> dict:
    labels = json.loads(C.LABELS.read_text())
    cal = json.loads(C.CALIBRATION.read_text())
    th = cal["thresholds_bps"]
    cache, per = {}, {}
    leads: dict[str, list] = {d: [] for d in DETECTORS}
    scored = []
    for eid, unit, a, b, panel in C.EVENTS:
        lab = labels["events"][eid]
        if not lab["scorable"]:
            per[eid] = {"scored": False, "reason": lab.get("reason")}
            continue
        if panel not in cache:
            cache[panel] = C.load(panel)
        onset = pd.Timestamp(lab["onset_utc"])
        fl = alarms_for_event(cache[panel][0], unit, eid, onset, th)
        rec = {"scored": True, "onset_utc": lab["onset_utc"], "single_pair_market": cal["events"][eid]["single_pair_market"], "lead_hours": {}}
        for d in DETECTORS:
            ld = first_alarm_lead(fl[d], onset)
            rec["lead_hours"][d] = ld
            leads[d].append(ld)
        per[eid] = rec
        scored.append(eid)
    misses = {d: sum(x is None for x in leads[d]) for d in DETECTORS}
    boot = bootstrap(leads)
    return {"preregistration": "autoresearch/program_q2.md", "scored_events": scored, "thresholds_bps": th, "per_event": per,
            "misses": misses, "median_lead_hours": {d: median_lead(leads[d]) for d in DETECTORS},
            "median_lead_hours_detected_only": {d: (float(np.median([x for x in leads[d] if x is not None]))
                                                    if any(x is not None for x in leads[d]) else None) for d in DETECTORS},
            "miss_lead_convention_hours": MISS_LEAD_H, "false_alarms_per_1000_calm_hours": cal["realised_per_1000_calm_hours"],
            "bootstrap": boot, "success_rule": verdict(boot, misses)}


if __name__ == "__main__":
    res = run()
    C.RESULTS.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "preregistration"}, indent=1))
