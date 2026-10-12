"""Stablecoin parity-wedge construction and persistence statistics.

A wedge is the FX-corrected BTC triangle deviation (see ``www_c0.quality``).
"Fresh" minutes are those in which every leg printed positive volume, so each
close is a trade inside that minute; it is still not a synchronized quote.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from www_c0.quality import parity_wedge_bps, validate_utc_minutes


# (wedge name) -> (BTC/quote pair, quote/USD pair, BTC/USD pair), Binance.US prefixes.
TRIANGLES = {
    "usdc": ("bnus_btcusdc", "bnus_usdcusd", "bnus_btcusd"),
    "usdt": ("bnus_btcusdt", "bnus_usdtusd", "bnus_btcusd"),
}


def build_wedges(panel: pd.DataFrame) -> pd.DataFrame:
    """Return timestamp-indexed wedges, fresh-trade masks, depeg deviations and regime."""
    index = validate_utc_minutes(panel["timestamp_utc"])
    out = pd.DataFrame(index=index)
    out["regime"] = panel["regime"].to_numpy() if "regime" in panel else None
    for name, legs in TRIANGLES.items():
        closes = [pd.to_numeric(panel[f"{leg}_close"], errors="coerce").to_numpy() for leg in legs]
        out[f"{name}_wedge_bps"] = parity_wedge_bps(*closes)
        fresh = np.ones(len(panel), dtype=bool)
        for leg in legs:
            fresh &= pd.to_numeric(panel[f"{leg}_volume"], errors="coerce").fillna(0).to_numpy() > 0
        out[f"{name}_fresh"] = fresh & np.isfinite(out[f"{name}_wedge_bps"].to_numpy())
        out[f"{name}_depeg_bps"] = 10_000 * np.log(closes[1])
    return out


@dataclass(frozen=True)
class AR1:
    phi: float | None
    half_life_minutes: float | None
    pairs: int


def half_life(phi: float | None) -> float | None:
    """Minutes for a deviation to halve under x_t = c + phi x_{t-1}; None if not mean-reverting."""
    if phi is None or not 0 < phi < 1:
        return None
    return -math.log(2) / math.log(phi)


def _ols_phi(prev: np.ndarray, curr: np.ndarray) -> float | None:
    if len(prev) < 3:
        return None
    dx = prev - prev.mean()
    denom = float(dx @ dx)
    if denom == 0:
        return None
    return float(dx @ (curr - curr.mean())) / denom


def adjacent_pairs(values: np.ndarray, mask: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """(x_{t-1}, x_t) pairs on consecutive grid minutes where both points are usable."""
    values = np.asarray(values, dtype=float)
    ok = np.isfinite(values)
    if mask is not None:
        ok &= np.asarray(mask, dtype=bool)
    both = ok[1:] & ok[:-1]
    return values[:-1][both], values[1:][both]


def ar1(values: np.ndarray, mask: np.ndarray | None = None) -> AR1:
    """AR(1) with intercept: reversion toward the sample mean of the masked window."""
    prev, curr = adjacent_pairs(values, mask)
    phi = _ols_phi(prev, curr)
    return AR1(phi, half_life(phi), len(prev))


def ar1_to_parity(values: np.ndarray, mask: np.ndarray | None = None) -> AR1:
    """AR(1) without intercept: reversion toward a zero wedge (parity), not toward a regime mean."""
    prev, curr = adjacent_pairs(values, mask)
    denom = float(prev @ prev)
    phi = float(prev @ curr) / denom if len(prev) >= 3 and denom > 0 else None
    return AR1(phi, half_life(phi), len(prev))


def block_bootstrap_phi(values: np.ndarray, mask: np.ndarray | None = None, *, block: int = 60,
                        draws: int = 500, seed: int = 20230310) -> tuple[float, float] | None:
    """Percentile 95% interval for phi from a moving-block bootstrap of adjacent pairs."""
    prev, curr = adjacent_pairs(values, mask)
    n = len(prev)
    if n < 2 * block:
        return None
    rng = np.random.default_rng(seed)
    blocks = math.ceil(n / block)
    estimates = []
    for _ in range(draws):
        starts = rng.integers(0, n - block + 1, size=blocks)
        idx = (starts[:, None] + np.arange(block)).ravel()[:n]
        phi = _ols_phi(prev[idx], curr[idx])
        if phi is not None:
            estimates.append(phi)
    if not estimates:
        return None
    lo, hi = np.percentile(estimates, [2.5, 97.5])
    return float(lo), float(hi)


@dataclass(frozen=True)
class Episode:
    start: pd.Timestamp
    end: pd.Timestamp | None  # first observed minute back inside the band; None if censored
    duration_minutes: float
    peak_abs_bps: float


def excursions(times: pd.DatetimeIndex, values: np.ndarray, observed: np.ndarray,
               threshold_bps: float) -> list[Episode]:
    """Episodes with |wedge| > threshold, judged only at observed minutes.

    An episode starts at the first observed breach and ends at the next observed
    minute inside the band; unobserved minutes neither start nor end an episode.
    Duration is clock time from start to end (or to the last observation if censored).
    """
    if threshold_bps <= 0:
        raise ValueError("threshold must be positive")
    values = np.asarray(values, dtype=float)
    keep = np.asarray(observed, dtype=bool) & np.isfinite(values)
    obs_times, obs_values = times[keep], values[keep]
    episodes: list[Episode] = []
    start: pd.Timestamp | None = None
    peak = 0.0
    for t, v in zip(obs_times, obs_values, strict=True):
        breach = abs(v) > threshold_bps
        if start is None and breach:
            start, peak = t, abs(v)
        elif start is not None and breach:
            peak = max(peak, abs(v))
        elif start is not None:
            episodes.append(Episode(start, t, (t - start).total_seconds() / 60, peak))
            start = None
    if start is not None:
        last = obs_times[-1]
        episodes.append(Episode(start, None, (last - start).total_seconds() / 60, peak))
    return episodes


def summarize_series(times: pd.DatetimeIndex, values: np.ndarray, observed: np.ndarray,
                     thresholds: tuple[float, ...], *, bootstrap_draws: int = 500) -> dict[str, Any]:
    values = np.asarray(values, dtype=float)
    observed = np.asarray(observed, dtype=bool) & np.isfinite(values)
    absolute = np.abs(values[observed])
    fit = ar1(values, observed)
    parity = ar1_to_parity(values, observed)
    ci = block_bootstrap_phi(values, observed, draws=bootstrap_draws)
    result: dict[str, Any] = {
        "observed_minutes": int(observed.sum()),
        "mean_bps": float(values[observed].mean()) if absolute.size else None,
        "median_abs_bps": float(np.median(absolute)) if absolute.size else None,
        "p95_abs_bps": float(np.percentile(absolute, 95)) if absolute.size else None,
        "max_abs_bps": float(absolute.max()) if absolute.size else None,
        "ar1_phi": fit.phi,
        "ar1_adjacent_pairs": fit.pairs,
        "half_life_minutes": fit.half_life_minutes,
        "ar1_phi_ci95": list(ci) if ci else None,
        "half_life_ci95_minutes": [half_life(ci[0]), half_life(ci[1])] if ci else None,
        "ar1_to_parity_phi": parity.phi,
        "half_life_to_parity_minutes": parity.half_life_minutes,
        "thresholds": {},
    }
    for threshold in thresholds:
        episodes = excursions(times, values, observed, threshold)
        durations = [e.duration_minutes for e in episodes]
        result["thresholds"][str(threshold)] = {
            "share_observed_minutes_above": float((absolute > threshold).mean()) if absolute.size else None,
            "episodes": len(episodes),
            "censored_episodes": sum(e.end is None for e in episodes),
            "median_duration_minutes": float(np.median(durations)) if durations else None,
            "max_duration_minutes": float(max(durations)) if durations else None,
        }
    return result


def fragmentation_report(panel: pd.DataFrame, *, thresholds: tuple[float, ...] = (10.0, 25.0, 50.0),
                         bootstrap_draws: int = 500) -> dict[str, Any]:
    """Regime-by-regime wedge level and persistence under two observation rules."""
    wedges = build_wedges(panel)
    regimes = [r for r in pd.unique(wedges["regime"]) if r is not None]
    report: dict[str, Any] = {"wedges": {}}
    for name in TRIANGLES:
        values = wedges[f"{name}_wedge_bps"].to_numpy()
        fresh = wedges[f"{name}_fresh"].to_numpy()
        rules = {"all_minutes_last_close": np.isfinite(values), "all_legs_traded": fresh}
        per_rule: dict[str, Any] = {}
        for rule, mask in rules.items():
            per_regime: dict[str, Any] = {}
            for regime in ["full_sample", *regimes]:
                in_regime = np.ones(len(wedges), bool) if regime == "full_sample" else (wedges["regime"] == regime).to_numpy()
                # Restrict pairs to the regime by masking outside it; adjacency never spans regimes.
                per_regime[regime] = summarize_series(wedges.index, values, mask & in_regime, thresholds,
                                                      bootstrap_draws=bootstrap_draws)
            per_rule[rule] = per_regime
        report["wedges"][name] = per_rule
    return report
