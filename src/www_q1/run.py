"""Q1 locked run (autoresearch/program_q1.md). Run once, only after the gate result was committed.

Refuses to run unless ``reports/q1/gate.json`` says the study proceeds. The frozen fuser (ca38772) and baselines B0-B4 and the
oracle are called once per kept event on its window plus the 30-day warm-up; the Kraken reference scores them and is never passed on.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

from www_stable import baselines as B
from www_stable import harness as H

from . import gate as G
from . import panel as P

REPO = P.REPO
OUT = REPO / "reports" / "q1" / "results.json"
FROZEN = Path(__file__).with_name("frozen_fuser_ca38772.py")
ANON_SEED = 20261022
BOOT_SEED, BOOT_DRAWS = 20261022, 1000
EPS_BP = 1.0
PLACEBO_MAX = 1.02
METHODS = ("fuser", "B0", "B1", "B2", "B3", "B4", "oracle")


def frozen_factory():
    def make():
        spec = importlib.util.spec_from_file_location("_q1_frozen_fuser", FROZEN)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.fuse
    return make


def s_hi_mask(markets, side, unit: str) -> pd.Series:
    share = G.volume_share(markets, unit)
    off, _ = G.offset_bps(markets, side, unit)
    return ((share >= G.SHARE_MIN) & (off.abs() >= G.OFFSET_MIN_BPS)).fillna(False)


def stats(e: np.ndarray) -> dict:
    a = np.abs(e)
    if len(a) == 0:
        return {"n": 0, "mae": None, "p95": None, "n25": 0, "n50": 0}
    return {"n": int(len(a)), "mae": float(a.mean()), "p95": float(np.quantile(a, 0.95)), "n25": int((a >= 25).sum()),
            "n50": int((a >= 50).sum())}


def boot(diff: np.ndarray, block: np.ndarray) -> dict:
    """Day-block bootstrap of the mean of ``diff`` (blocks = event-days)."""
    ids, inv = np.unique(block, return_inverse=True)
    sums = np.bincount(inv, weights=diff, minlength=len(ids))
    cnt = np.bincount(inv, minlength=len(ids)).astype(float)
    rng = np.random.default_rng(BOOT_SEED)
    draws = rng.integers(0, len(ids), size=(BOOT_DRAWS, len(ids)))
    m = sums[draws].sum(axis=1) / cnt[draws].sum(axis=1)
    lo, hi = np.quantile(m, [0.025, 0.975])
    return {"mean": float(diff.mean()), "ci95": [float(lo), float(hi)], "n_hours": int(len(diff)), "n_blocks": int(len(ids)),
            "success": bool(hi < 0)}


def run(panel_path: Path = P.PANEL_PATH, gate_path: Path = G.OUT) -> dict:
    gate = json.loads(gate_path.read_text())
    if not gate["proceed"]:
        raise SystemExit("gate did not pass: no locked run")
    markets, side, ref, _ = P.load_all(panel_path)
    eps = {e.name: e for e in P.episodes()}
    rows = []  # one record per scorable hour
    for eid in gate["kept_events"]:
        unit = P.shifted_unit(eid)
        w = H.episode_windows(markets, side, ref, eps[eid])[0]
        base = B.all_baselines(w.markets, w.side, w.index)
        fused = H.call_fuser(frozen_factory(), w, ANON_SEED)
        out = pd.DataFrame({"fuser": fused, **base})
        r = w.ref.reindex(w.index).to_numpy(float)
        b0 = out["B0"].to_numpy(float)
        ok = np.isfinite(r) & np.isfinite(b0)
        hi_all = s_hi_mask(markets, side, unit).reindex(w.index).fillna(False).to_numpy(bool)
        frame = pd.DataFrame({"event": eid, "t": w.index, "scored": w.scored(), "s_hi": hi_all})[ok]
        for m in METHODS:
            f = out[m].to_numpy(float)[ok]
            frame[m] = 1e4 * (np.where(np.isfinite(f), f, b0[ok]) - r[ok])
        frame["covered"] = np.isfinite(out["fuser"].to_numpy(float)[ok])
        rows.append(frame)
    df = pd.concat(rows, ignore_index=True)
    hi = df[df["scored"] & df["s_hi"]].reset_index(drop=True)
    block = (hi["event"] + "|" + hi["t"].dt.strftime("%Y-%m-%d")).to_numpy()
    res: dict = {"preregistration": "autoresearch/program_q1.md", "frozen_fuser": "ca38772", "anonymisation_seed": ANON_SEED,
                 "bootstrap": {"draws": BOOT_DRAWS, "seed": BOOT_SEED, "block": "event-UTC-day"}, "kept_events": gate["kept_events"],
                 "s_hi_hours": {e: int((hi["event"] == e).sum()) for e in gate["kept_events"]}, "primary": {}, "per_event": {},
                 "pooled_s_hi": {}, "placebo": {}}
    lg = lambda x: np.log(np.abs(x) + EPS_BP)  # noqa: E731
    for m in ("B0", "B2", "B3", "B1", "B4", "oracle"):
        res["primary"][f"fuser_vs_{m}"] = boot((lg(hi["fuser"]) - lg(hi[m])).to_numpy(), block)
    res["primary_success"] = bool(res["primary"]["fuser_vs_B0"]["success"])
    res["coprimary_success"] = bool(res["primary"]["fuser_vs_B2"]["success"] and res["primary"]["fuser_vs_B3"]["success"])
    res["headline_beats_existing_methods"] = bool(res["primary_success"] and res["coprimary_success"])
    for m in METHODS:
        res["pooled_s_hi"][m] = stats(hi[m].to_numpy())
    res["gap_to_oracle_s_hi"] = res["pooled_s_hi"]["fuser"]["mae"] / res["pooled_s_hi"]["oracle"]["mae"]
    for e in gate["kept_events"]:
        h = hi[hi["event"] == e]
        a = df[(df["event"] == e) & df["scored"]]
        res["per_event"][e] = {
            "s_hi": {m: stats(h[m].to_numpy()) for m in METHODS},
            "mae_ratio_s_hi": {m: stats(h[m].to_numpy())["mae"] / stats(h["B0"].to_numpy())["mae"] for m in METHODS},
            "window_all_hours": {m: stats(a[m].to_numpy()) for m in METHODS},
            "mae_ratio_window": {m: stats(a[m].to_numpy())["mae"] / stats(a["B0"].to_numpy())["mae"] for m in METHODS},
            "fuser_coverage_window": float(a["covered"].mean())}
    pre = df[~df["scored"] & ~df["s_hi"]]
    ratios = {}
    for e in gate["kept_events"]:
        p = pre[pre["event"] == e]
        ratios[e] = {"hours": int(len(p)), "fuser_mae": stats(p["fuser"].to_numpy())["mae"], "B0_mae": stats(p["B0"].to_numpy())["mae"]}
        ratios[e]["ratio"] = ratios[e]["fuser_mae"] / ratios[e]["B0_mae"]
    pooled = stats(pre["fuser"].to_numpy())["mae"] / stats(pre["B0"].to_numpy())["mae"]
    res["placebo"] = {"definition": "warm-up hours (30 days before the window) not in S_hi; fuser/B0 MAE ratio <= 1.02",
                      "per_event": ratios, "pooled_ratio": float(pooled),
                      "pass_every_event": bool(all(v["ratio"] <= PLACEBO_MAX for v in ratios.values())),
                      "pass_pooled": bool(pooled <= PLACEBO_MAX)}
    return res


if __name__ == "__main__":
    r = run()
    OUT.write_text(json.dumps(r, indent=1) + "\n")
    print(json.dumps({k: r[k] for k in ("primary", "primary_success", "coprimary_success", "gap_to_oracle_s_hi", "placebo")}, indent=1))
