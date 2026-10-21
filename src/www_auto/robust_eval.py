"""Assets x time double holdout, longer bootstrap blocks and medians, for the FROZEN estimator (commit 724455b).

    uv run python -m www_auto.robust_eval        # writes reports/unit_td/robust_eval.json

Scoring only, never tuning. The estimator has no fitted parameters: it is a causal rule (row t uses row t only) with fixed
constants, so scoring it on a held-out PERIOD needs no refit. Time holdout matters only for the one constant that the dev
loop picked on all years: the shrinkage multiplier on the noise term (1.0 -> 0.5 -> 0.25 were tried; 0.5 kept). Section
"honest" re-picks that constant using ONLY 2017--2019 dev data (dev assets, leave-one-asset-out) among {1.0, 0.5, 0.25,
0.0}, where 0.0 is the unshrunk median that the loop started from, and scores 2020--2023 only.
The constant is varied by a text substitution on a copy of estimator.py; estimator.py itself is not edited.

  1. periods: 2017--2019 and 2020--2023, scores on test assets, dev assets, and the Coinbase--Bitstamp control
     (the control panel starts 2019-01, so its first period is 2019 only).
  2. blocks: 95% bootstrap with ISO-week, calendar-month and calendar-quarter blocks (1,000 draws, fixed seed).
  3. medians and ranges across assets, years and asset-years, for test and dev.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import harness as H
from . import panel as P
from . import posthoc_eval as X

REPO = P.REPO
OUT = REPO / "reports" / "unit_td" / "robust_eval.json"
LOOP_TSV = REPO / "autoresearch" / "results_unit_td_run1.tsv"
FROZEN_CONSTANT = 0.5
CANDIDATES = (1.0, 0.5, 0.25, 0.0)  # three tried by the loop (see LOOP_TSV) plus 0.0 = unshrunk median (loop start)
PERIODS = {"2017-2019": (2017, 2019), "2020-2023": (2020, 2023)}
BLOCKS = ("week", "month", "quarter")
BLOCK_SEED = X.BOOT_SEED
N_BOOT = X.N_BOOT
METHODS = ("b1", "b2", "est")
_NEEDLE = "keep = (1.0 - 0.5 * var /"


# ---------------------------------------------------------------- estimator with a different shrinkage constant

def estimator_factory(constant: float):
    """Factory for a copy of the frozen estimator with the shrinkage multiplier replaced (0.5 reproduces the frozen one)."""
    src = H.EST_PATH.read_text()
    if src.count(_NEEDLE) != 1:
        raise RuntimeError("estimator.py no longer has the expected shrinkage line")
    src = src.replace(_NEEDLE, f"keep = (1.0 - {constant!r} * var /")

    def make():
        spec = importlib.util.spec_from_loader("_robust_est", loader=None)
        mod = importlib.util.module_from_spec(spec)
        exec(compile(src, f"estimator_c{constant}", "exec"), mod.__dict__)  # noqa: S102 - our own source text
        return mod.estimate_units
    return make


def run_estimator(raw, assets, constant: float):
    factory = estimator_factory(constant)
    return {a: H.call_estimator(factory, raw, a, "final", X.SEED) for a in assets}


def loop_constants() -> dict[str, Any]:
    """The constants the dev loop tried, read from the loop log (commit -> description)."""
    rows = [ln.split("\t") for ln in LOOP_TSV.read_text().splitlines()[1:]]
    return {r[0]: {"dev_score": float(r[1]), "status": r[4], "description": r[5]} for r in rows
            if "shrinkage noise" in r[5].lower() or "mad dispersion" in r[5].lower()}


# ---------------------------------------------------------------- cells with block ids

def add_blocks(d: pd.DataFrame, index_by_asset: dict[str, pd.DatetimeIndex]) -> pd.DataFrame:
    """Add calendar month / quarter ids (year*100+month, year*10+quarter) in the row order produced by X.cells."""
    stamps = np.concatenate([index_by_asset[a].to_numpy() for a in index_by_asset])
    ts = pd.DatetimeIndex(stamps)
    d = d.copy()
    d["month"] = (ts.year * 100 + ts.month).to_numpy()
    d["quarter"] = (ts.year * 10 + ts.quarter).to_numpy()
    d["week"] = d["wk"]
    return d


def gather_cells(raw, outs, assets, pair, kind, start=None) -> pd.DataFrame:
    gs, us = X.gather(raw, outs, assets, pair, kind, start)
    idx = {a: gs[a].index[gs[a].notna().to_numpy()] for a in assets}
    return add_blocks(X.cells(gs, us), idx)


def boot(parts: dict[str, pd.DataFrame], block: str, diff=("est", "b2")) -> dict[str, Any]:
    """X.bootstrap with the chosen block column substituted for 'wk' (week reproduces posthoc.json exactly)."""
    return X.bootstrap({m: d.assign(wk=d[block]) for m, d in parts.items()}, diff=diff, n_boot=N_BOOT, seed=BLOCK_SEED)


def score(d: pd.DataFrame) -> float:
    den = d["g2"].sum()
    return float(1 - d["e2"].sum() / den) if den > 0 else float("nan")


def period_rows(d: pd.DataFrame, lo: int, hi: int) -> pd.DataFrame:
    return d[(d["year"] >= lo) & (d["year"] <= hi)].reset_index(drop=True)


# ---------------------------------------------------------------- sections

def all_cells(raw_main, raw_ctrl, dev_outs, test_outs, ctrl_outs) -> dict[str, dict[str, pd.DataFrame]]:
    """split -> method -> cells. Estimator outputs per split may use different constants (honest variant)."""
    res: dict[str, dict[str, pd.DataFrame]] = {}
    for split, raw, outs, assets, pair, start in (
            ("dev", raw_main, dev_outs, P.DEV_SCORED, H.PAIR, None), ("test", raw_main, test_outs, P.TEST_SCORED, H.PAIR, None),
            ("control", raw_ctrl, ctrl_outs, X.CONTROL_ASSETS, H.CONTROL_PAIR, H.CONTROL_START)):
        res[split] = {k: gather_cells(raw, outs, assets, pair, k, start) for k in METHODS}
    return res


def period_scores(cells_by_split) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for pname, (lo, hi) in PERIODS.items():
        out[pname] = {}
        for split, parts in cells_by_split.items():
            sub = {m: period_rows(d, lo, hi) for m, d in parts.items()}
            n = len(sub["est"])
            row: dict[str, Any] = {"n_hours": int(n)}
            if n == 0:
                out[pname][split] = row
                continue
            row.update({m: score(d) for m, d in sub.items()})
            row["diff_est_minus_b2"] = row["est"] - row["b2"]
            row["by_asset_est"] = {a: score(x) for a, x in sub["est"].groupby("asset")}
            b = boot(sub, "month")
            row["month_block_ci"] = {m: b["pooled"][m] for m in (*METHODS, "diff")}
            out[pname][split] = row
    return out


def block_comparison(cells_by_split) -> dict[str, Any]:
    """Full-sample 95% intervals for several block lengths: pooled test, per test asset, est - b2, and the control."""
    res: dict[str, Any] = {}
    for blk in BLOCKS:
        entry: dict[str, Any] = {}
        for split in ("test", "dev", "control"):
            b = boot(cells_by_split[split], blk)
            entry[split] = {g: {m: s for m, s in methods.items() if m != "b0"}
                            for g, methods in b.items() if not g.startswith("year:")}
            entry[split]["n_blocks"] = int(cells_by_split[split]["est"][blk].nunique())
        res[blk] = entry
    return res


def widening(blocks) -> dict[str, Any]:
    """Interval width relative to the weekly width, for the headline quantities."""
    def width(s):
        return s["hi"] - s["lo"]
    heads = {"test_pooled_est": ("test", "pooled", "est"), "test_pooled_diff": ("test", "pooled", "diff"),
             "control_pooled_est": ("control", "pooled", "est"), "control_pooled_diff": ("control", "pooled", "diff")}
    heads.update({f"test_{a}_est": ("test", f"asset:{a}", "est") for a in P.TEST_SCORED})
    out = {}
    for name, (split, g, m) in heads.items():
        w = {b: width(blocks[b][split][g][m]) for b in BLOCKS}
        out[name] = {"width": w, "ratio_vs_week": {b: w[b] / w["week"] for b in BLOCKS}}
    ratios = {b: [v["ratio_vs_week"][b] for v in out.values()] for b in BLOCKS}
    out["median_ratio_vs_week"] = {b: float(np.median(r)) for b, r in ratios.items()}
    return out


def summarize(vals: dict[Any, float]) -> dict[str, Any]:
    v = np.array(list(vals.values()), float)
    k = list(vals)
    return {"median": float(np.median(v)), "min": float(v.min()), "max": float(v.max()), "argmin": str(k[int(v.argmin())]),
            "argmax": str(k[int(v.argmax())]), "n": int(len(v)), "values": {str(a): float(x) for a, x in vals.items()}}


def medians(cells_by_split) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for split in ("test", "dev"):
        parts = cells_by_split[split]
        out[split] = {}
        for m in METHODS:
            d = parts[m]
            by_asset = {a: score(x) for a, x in d.groupby("asset")}
            by_year = {int(y): score(x) for y, x in d.groupby("year")}
            by_cell = {f"{a}-{int(y)}": score(x) for (a, y), x in d.groupby(["asset", "year"]) if x["g2"].sum() > 0}
            out[split][m] = {"pooled": score(d), "by_asset": summarize(by_asset), "by_year": summarize(by_year),
                             "by_asset_year": summarize(by_cell)}
    return out


def honest(raw_main, raw_ctrl) -> dict[str, Any]:
    """Re-pick the shrinkage constant on 2017-2019 dev data only; score 2020-2023 (and every other cell) with it."""
    sel: dict[str, Any] = {}
    outs_by_c = {}
    for c in CANDIDATES:
        outs = run_estimator(raw_main, P.DEV_SCORED, c)
        outs_by_c[c] = outs
        gs, us = X.gather(raw_main, outs, P.DEV_SCORED, H.PAIR, "est")
        d = X.cells(gs, us)
        sel[repr(c)] = {"dev_2017_2019": score(period_rows(d, 2017, 2019)), "dev_2020_2023": score(period_rows(d, 2020, 2023)),
                        "dev_all_years": score(d)}
    chosen = max(CANDIDATES, key=lambda c: sel[repr(c)]["dev_2017_2019"])
    test_outs = run_estimator(raw_main, P.TEST_SCORED, chosen)
    ctrl_outs = run_estimator(raw_ctrl, X.CONTROL_ASSETS, chosen)
    cells_by_split = all_cells(raw_main, raw_ctrl, outs_by_c[chosen], test_outs, ctrl_outs)
    full = period_scores(cells_by_split)
    return {"candidates": list(CANDIDATES), "selection_dev_scores": sel, "chosen_constant": chosen,
            "frozen_constant": FROZEN_CONSTANT, "same_as_frozen": bool(chosen == FROZEN_CONSTANT),
            "score_2020_2023": full["2020-2023"], "score_2017_2019_in_sample_for_selection": full["2017-2019"]}


def build(root: Path = REPO) -> dict[str, Any]:
    raw_main = X.load_raw(False, root)
    raw_ctrl = X.load_raw(True, root)
    frozen = estimator_factory(FROZEN_CONSTANT)
    ref = H.file_estimator_factory()
    # the constant-substituted copy at 0.5 must equal the frozen file
    probe = H.call_estimator(frozen, raw_main, "LINK", "final", X.SEED)
    if H._max_diff(probe, H.call_estimator(ref, raw_main, "LINK", "final", X.SEED)) != 0.0:
        raise SystemExit("substituted estimator at 0.5 differs from the frozen estimator")
    dev_outs = run_estimator(raw_main, P.DEV_SCORED, FROZEN_CONSTANT)
    test_outs = run_estimator(raw_main, P.TEST_SCORED, FROZEN_CONSTANT)
    ctrl_outs = run_estimator(raw_ctrl, X.CONTROL_ASSETS, FROZEN_CONSTANT)
    cs = all_cells(raw_main, raw_ctrl, dev_outs, test_outs, ctrl_outs)
    blocks = block_comparison(cs)
    return {"estimator_sha256": hashlib.sha256(H.EST_PATH.read_bytes()).hexdigest(), "anonymisation_seed": X.SEED,
            "bootstrap": {"blocks": list(BLOCKS), "draws": N_BOOT, "seed": BLOCK_SEED, "interval": "95% percentile"},
            "note": "The estimator has no fitted parameters; time holdout matters only for the shrinkage constant, "
                    "picked in the dev loop on all years. 'honest' re-picks it on 2017-2019 dev data only.",
            "loop_constants": loop_constants(),
            "periods": period_scores(cs), "honest": honest(raw_main, raw_ctrl), "blocks": blocks, "widening": widening(blocks),
            "medians": medians(cs)}


def main() -> int:
    res = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
