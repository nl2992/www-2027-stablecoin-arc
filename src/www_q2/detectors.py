"""Q2 detectors P, S1, S2 exactly as in autoresearch/program_q2.md. All are causal: the value at hour t uses hours <= t only.

Prices are the panel's log hourly last-traded closes; gaps are in bps. The USD-venue price of an asset is the row-wise median over
every market quoted in USD that has that asset. A missing observation (no trade in the hour) leaves the detector state unchanged
and raises no alarm in that hour.

  P    median over every (market in unit k, asset in BTC/ETH) pair of its gap to the USD-venue median, then an EWMA of span 3
       (alpha = 0.5, recursive, started at the first observation); alarm when |value| >= tau_P.
  S1   BTC gap of the highest-volume market of unit k to the USD-venue median; alarm when |gap| >= tau_S1. The market is the one
       with the largest BTC volume over the 30 calm days before the event window (known before onset).
  S2   two-sided CUSUM on the same gap, reference 5 bps, reset to zero after each alarm; alarm when the statistic >= h_S2.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import common as C

ASSETS = ("BTC", "ETH")
SPAN = 3
CUSUM_REF_BPS = 5.0


def unit_of(key: str) -> str:
    return key.split(".", 1)[1]


def usd_median(markets: dict[str, pd.DataFrame], asset: str) -> pd.Series:
    cols = [f[asset] for k, f in markets.items() if unit_of(k) == C.USD_UNIT and asset in f]
    return pd.concat(cols, axis=1).median(axis=1, skipna=True)


def pair_gaps_bps(markets: dict[str, pd.DataFrame], unit: str) -> pd.DataFrame:
    """One column per (market in ``unit``, asset): 1e4 * (log price - USD-venue median)."""
    out = {}
    for asset in ASSETS:
        ref = usd_median(markets, asset)
        for k, f in markets.items():
            if unit_of(k) == unit and asset in f:
                out[f"{k}|{asset}"] = 1e4 * (f[asset] - ref)
    return pd.DataFrame(out)


def ewma(x: pd.Series, span: int = SPAN) -> pd.Series:
    """Recursive EWMA, alpha = 2/(span+1). NaN input keeps the state and returns NaN at that hour."""
    a = 2.0 / (span + 1)
    v = x.to_numpy(float)
    out = np.full(len(v), np.nan)
    state = np.nan
    for i, xi in enumerate(v):
        if np.isnan(xi):
            continue
        state = xi if np.isnan(state) else a * xi + (1 - a) * state
        out[i] = state
    return pd.Series(out, index=x.index)


def pooled_statistic(markets: dict[str, pd.DataFrame], unit: str) -> pd.Series:
    gaps = pair_gaps_bps(markets, unit)
    return ewma(gaps.median(axis=1, skipna=True).where(gaps.notna().any(axis=1)))


def top_volume_market(markets: dict[str, pd.DataFrame], unit: str, hours: pd.DatetimeIndex) -> str:
    vols = {k: f["BTC_vol"].reindex(hours).sum() for k, f in markets.items()
            if unit_of(k) == unit and "BTC" in f and "BTC_vol" in f and f["BTC"].reindex(hours).notna().any()}
    if not vols:
        raise ValueError(f"no BTC market quoted in {unit}")
    return sorted(vols.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def single_pair_gap(markets: dict[str, pd.DataFrame], market: str) -> pd.Series:
    return 1e4 * (markets[market]["BTC"] - usd_median(markets, "BTC"))


def threshold_alarms(stat: pd.Series, tau: float) -> pd.Series:
    return (stat.abs() >= tau).fillna(False)


def cusum(x: pd.Series, h: float, ref: float = CUSUM_REF_BPS) -> tuple[pd.Series, pd.Series]:
    """(alarm flags, statistic max(S+, S-) before reset). State is zero at the first hour of ``x``."""
    v = x.to_numpy(float)
    alarm = np.zeros(len(v), bool)
    stat = np.full(len(v), np.nan)
    sp = sn = 0.0
    for i, xi in enumerate(v):
        if np.isnan(xi):
            continue
        sp = max(0.0, sp + xi - ref)
        sn = max(0.0, sn - xi - ref)
        stat[i] = max(sp, sn)
        if stat[i] >= h:
            alarm[i] = True
            sp = sn = 0.0
    return pd.Series(alarm, index=x.index), pd.Series(stat, index=x.index)


def episodes(flags: pd.Series) -> int:
    """Number of alarm episodes: maximal runs of consecutive alarm hours."""
    f = flags.to_numpy(bool)
    return int((f & ~np.r_[False, f[:-1]]).sum())
