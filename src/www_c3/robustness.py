"""C3 robustness: horizon aggregation, regime-difference bootstrap, alternative dollar leg."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from www_c0.quality import parity_wedge_bps

from .cli import sha256
from .fragmentation import ar1_to_parity, build_wedges


HORIZONS = (1, 5, 15, 60)
SEED = 20230310


def horizon_medians(values: pd.Series, observed: pd.Series, minutes: int, *, min_obs: int = 1) -> pd.Series:
    """Median observed wedge in non-overlapping clock bins; bins with too few observations are NaN."""
    if minutes < 1 or min_obs < 1:
        raise ValueError("minutes and min_obs must be positive")
    kept = values.where(observed.astype(bool))
    grouped = kept.resample(f"{minutes}min", origin="epoch", label="left", closed="left")
    medians = grouped.median()
    counts = grouped.count()
    return medians.where(counts >= min_obs)


def horizon_profile(values: pd.Series, observed: pd.Series, regimes: pd.Series) -> dict[str, Any]:
    """Per horizon and regime: median |bin wedge| and parity-anchored half-life in clock minutes."""
    out: dict[str, Any] = {}
    for h in HORIZONS:
        bins = horizon_medians(values, observed, h, min_obs=max(1, h // 5))
        bin_regime = regimes.resample(f"{h}min", origin="epoch", label="left", closed="left").first()
        per: dict[str, Any] = {}
        for regime in pd.unique(regimes):
            in_regime = (bin_regime == regime).to_numpy()
            arr = bins.to_numpy()
            fit = ar1_to_parity(arr, in_regime & np.isfinite(arr))
            obs = arr[in_regime & np.isfinite(arr)]
            per[str(regime)] = {
                "bins": int(obs.size),
                "median_abs_bps": float(np.median(np.abs(obs))) if obs.size else None,
                "ar1_to_parity_phi": fit.phi,
                "half_life_to_parity_minutes": None if fit.half_life_minutes is None else fit.half_life_minutes * h,
            }
        out[str(h)] = per
    return out


def _block_resample(x: np.ndarray, block: int, rng: np.random.Generator) -> np.ndarray:
    n = len(x)
    if n <= block:
        return x[rng.integers(0, n, size=n)]
    starts = rng.integers(0, n - block + 1, size=math.ceil(n / block))
    return x[(starts[:, None] + np.arange(block)).ravel()[:n]]


def regime_difference(a: np.ndarray, b: np.ndarray, statistic: str, *, threshold: float = 25.0,
                      block: int = 60, draws: int = 1000, seed: int = SEED) -> dict[str, Any]:
    """Statistic(b) - statistic(a) on |wedge|, with an independent moving-block bootstrap per regime.

    a and b are time-ordered observed wedges; blocks preserve within-regime serial dependence.
    """
    stats = {
        "median_abs": lambda x: float(np.median(np.abs(x))),
        "p95_abs": lambda x: float(np.percentile(np.abs(x), 95)),
        "share_above": lambda x: float((np.abs(x) > threshold).mean()),
    }
    if statistic not in stats:
        raise ValueError(f"unknown statistic {statistic}")
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.size < 2 or b.size < 2:
        raise ValueError("each regime needs at least two observations")
    f = stats[statistic]
    rng = np.random.default_rng(seed)
    diffs = np.array([f(_block_resample(b, block, rng)) - f(_block_resample(a, block, rng)) for _ in range(draws)])
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return {
        "statistic": statistic,
        "estimate": f(b) - f(a),
        "ci95": [float(lo), float(hi)],
        "ci_excludes_zero": bool(lo > 0 or hi < 0),
        "bootstrap": {"block": block, "draws": draws, "seed": seed},
    }


def coinbase_leg_wedge(panel: pd.DataFrame, index: pd.DatetimeIndex) -> tuple[pd.Series, pd.Series]:
    """USDC wedge with Coinbase BTC-USD as the dollar leg; mixes in a cross-venue basis."""
    closes = [pd.to_numeric(panel[c], errors="coerce").to_numpy()
              for c in ("bnus_btcusdc_close", "bnus_usdcusd_close", "cb_btcusd_close")]
    wedge = pd.Series(parity_wedge_bps(*closes), index=index)
    fresh = np.ones(len(panel), bool)
    for c in ("bnus_btcusdc_volume", "bnus_usdcusd_volume", "cb_btcusd_volume"):
        fresh &= pd.to_numeric(panel[c], errors="coerce").fillna(0).to_numpy() > 0
    return wedge, pd.Series(fresh & np.isfinite(wedge.to_numpy()), index=index)


def robustness_report(panel: pd.DataFrame, *, draws: int = 1000) -> dict[str, Any]:
    w = build_wedges(panel)
    regimes = w["regime"]
    report: dict[str, Any] = {"horizons": {}, "regime_differences": {}, "alternative_dollar_leg": {}}
    for name in ("usdc", "usdt"):
        values, fresh = w[f"{name}_wedge_bps"], w[f"{name}_fresh"]
        report["horizons"][name] = horizon_profile(values, fresh, regimes)
        diffs: dict[str, Any] = {}
        pre = values[fresh & (regimes == "pre_crisis")].to_numpy()
        for regime in ("crisis", "recovery", "post"):
            other = values[fresh & (regimes == regime)].to_numpy()
            diffs[f"{regime}_minus_pre_crisis"] = {
                s: regime_difference(pre, other, s, draws=draws) for s in ("median_abs", "p95_abs", "share_above")
            }
        report["regime_differences"][name] = diffs
    cb_values, cb_fresh = coinbase_leg_wedge(panel, w.index)
    alt: dict[str, Any] = {}
    for regime in pd.unique(regimes):
        sel = (cb_fresh & (regimes == regime)).to_numpy()
        x = cb_values.to_numpy()[sel]
        alt[str(regime)] = {
            "observed_minutes": int(sel.sum()),
            "median_abs_bps": float(np.median(np.abs(x))) if x.size else None,
            "p95_abs_bps": float(np.percentile(np.abs(x), 95)) if x.size else None,
            "share_above_25": float((np.abs(x) > 25).mean()) if x.size else None,
        }
    report["alternative_dollar_leg"]["usdc_coinbase_btcusd"] = alt
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--draws", type=int, default=1000)
    args = parser.parse_args()
    result = {
        "checkpoint": "C3-robustness",
        "input_sha256": sha256(args.panel),
        **robustness_report(pd.read_parquet(args.panel), draws=args.draws),
        "limitations": [
            "Horizon bins take the median of all-legs-traded minutes; bins need at least max(1, h/5) observations.",
            "Regime-difference intervals resample each regime independently in 60-observation blocks; observed minutes are not equally spaced in clock time.",
            "The Coinbase-leg wedge combines Binance.US BTC-USDC and USDC-USD with Coinbase BTC-USD, so it includes a cross-venue BTC basis.",
            "All inputs are last-trade candle closes, not executable quotes.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"WROTE {args.output}")


if __name__ == "__main__":
    main()
