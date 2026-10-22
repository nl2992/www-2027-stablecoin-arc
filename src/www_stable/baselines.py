"""Fixed baselines for the STABLE harness (not editable by the loop; the harness is their only caller).

All are causal and take REAL-named markets (``venue.UNIT``), because B2 (conversion) and the oracle need to know the quote
units: this de-anonymisation happens inside the harness only; the fuser never sees names. Per hour, a market's price is its
BTC log price in its own quote unit. Methods (``autoresearch/program_stable.md``):

  B0      median of all markets, every stablecoin treated as exactly 1 USD
  B1      volume-weighted mean of all markets (weights: hourly BTC volume), stablecoins = 1 USD
  B2      conversion: each non-USD market is converted at its unit's USD rate (direct stablecoin/USD rate from Binance.US or
          Bitstamp, else the Binance cross-rate in USDT chained through USDT/USD); the median over the converted markets.
          A rate is carried forward at most 24 hours; a market whose unit has no rate (after that) is used unconverted.
          Where several venues quote one rate the median is used. Kraken is never used.
  B3      CRH (Li et al. 2014) over all markets, stablecoins = 1 USD; reliabilities refit once per UTC day on the trailing
          30 days (BTC and ETH claims pooled), hyper-parameters from ``www_auto.td_realdata``
  B4      the round-2 fuser frozen at commit 914b3cb (``frozen_fuse_914b3cb.py``, unchanged), each market a source, BTC the
          fused item and ETH in the same unit a second item
  oracle  median of the USD-quoted markets only (it knows which units are dollars; a reference point, not a method)
"""

from __future__ import annotations

import importlib.util
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from www_auto import td_realdata as TD

USD = "USD"
RATE_FFILL_HOURS = 24
MIN_CRH_HISTORY = 24
METHODS = ("B0", "B1", "B2", "B3", "B4", "oracle")
FROZEN_PATH = Path(__file__).with_name("frozen_fuse_914b3cb.py")


def unit_of(key: str) -> str:
    return key.split(".", 1)[1]


def _median(p: np.ndarray) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmedian(p, axis=1)


def _matrix(markets: dict[str, pd.DataFrame], names: list[str], col: str, n: int) -> np.ndarray:
    return np.column_stack([markets[k][col].to_numpy(float) if col in markets[k].columns else np.full(n, np.nan)
                            for k in names])


def b0(p: np.ndarray) -> np.ndarray:
    return _median(p)


def b1(p: np.ndarray, v: np.ndarray) -> np.ndarray:
    w = np.where(np.isfinite(p), np.where(np.isfinite(v) & (v > 0), v, 1.0), 0.0)
    den = w.sum(axis=1)
    return np.where(den > 0, (np.where(np.isfinite(p), p, 0.0) * w).sum(axis=1) / np.where(den > 0, den, 1.0), np.nan)


def usd_log_rates(side: pd.DataFrame, units: list[str]) -> dict[str, np.ndarray]:
    """Causal log USD value of one unit of each stablecoin (0 for USD itself; NaN where no rate has been seen for 24 hours)."""
    n = len(side)
    parsed = {}
    for c in side.columns:
        base, rest = c.split(".", 1)
        quote, venue = rest.split("@", 1)
        parsed[c] = (base, quote, venue)

    def direct(base: str, quote: str) -> np.ndarray:
        cols = [side[c].to_numpy(float) for c, (b, q, _) in parsed.items() if b == base and q == quote]
        return _median(np.column_stack(cols)) if cols else np.full(n, np.nan)

    def held(x: np.ndarray) -> np.ndarray:
        return pd.Series(x).ffill(limit=RATE_FFILL_HOURS).to_numpy()

    usdt = held(direct("USDT", "USD"))
    out = {USD: np.zeros(n)}
    for u in units:
        if u == USD:
            continue
        d = held(direct(u, USD))
        chained = held(direct(u, "USDT")) + usdt if u != "USDT" else np.full(n, np.nan)
        out[u] = np.where(np.isfinite(d), d, chained)
    return out


def b2(markets: dict[str, pd.DataFrame], names: list[str], side: pd.DataFrame, n: int) -> np.ndarray:
    rates = usd_log_rates(side, sorted({unit_of(k) for k in names}))
    cols = []
    for k in names:
        r = rates[unit_of(k)]
        cols.append(markets[k]["BTC"].to_numpy(float) + np.where(np.isfinite(r), r, 0.0))
    return _median(np.column_stack(cols))


def crh(prices: dict[str, np.ndarray], idx: pd.DatetimeIndex) -> np.ndarray:
    """CRH fused log price of the first item: weights refit once per UTC day from the trailing window (TD kernels)."""
    items = list(prices)
    n_src = prices[items[0]].shape[1]
    out = np.full(len(idx), np.nan)
    for s, e, lo in TD._day_blocks(idx):
        w = np.ones(n_src)
        if s > lo:
            x = np.vstack([1e4 * a[lo:s] for a in prices.values()])
            multi = np.isfinite(x).sum(axis=1) >= 2
            if multi.any():
                w = TD.crh_masked(x, TD.HYPERPARAMETERS["crh"]["max_iter"], TD.HYPERPARAMETERS["crh"]["tol"])
                few = np.isfinite(x[multi]).sum(axis=0) < MIN_CRH_HISTORY
                if few.any():
                    w = np.where(few, w[~few].mean() if (~few).any() else 1.0, w)
        blk = prices[items[0]][s:e]
        m = np.isfinite(blk)
        den = (m * w).sum(axis=1)
        out[s:e] = np.where(den > 0, (np.where(m, blk, 0.0) * w).sum(axis=1) / np.where(den > 0, den, 1.0), np.nan)
    return out


def frozen_fuser():
    spec = importlib.util.spec_from_file_location("_stable_frozen_914b3cb", FROZEN_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.fuse


def b4(markets: dict[str, pd.DataFrame], names: list[str], idx: pd.DatetimeIndex) -> np.ndarray:
    panel = {}
    for k in names:
        f = markets[k]
        cols = [c for c in ("BTC", "ETH", "BTC_vol", "ETH_vol") if c in f.columns]
        panel[k] = f[cols]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # the frozen file is not edited; all-NaN slices are expected
        out = frozen_fuser()(panel, ["BTC", "ETH"])
    return out["BTC"].reindex(idx).to_numpy(float)


def oracle(p: np.ndarray, names: list[str]) -> np.ndarray:
    cols = [i for i, k in enumerate(names) if unit_of(k) == USD]
    return _median(p[:, cols]) if cols else np.full(len(p), np.nan)


def all_baselines(markets: dict[str, pd.DataFrame], side: pd.DataFrame, idx: pd.DatetimeIndex) -> dict[str, pd.Series]:
    """Every baseline's fused log BTC/USD (index ``idx``) from the REAL-named markets of one episode window."""
    names = sorted(markets)
    n = len(idx)
    P = {"BTC": _matrix(markets, names, "BTC", n), "ETH": _matrix(markets, names, "ETH", n)}
    V = _matrix(markets, names, "BTC_vol", n)
    res = {"B0": b0(P["BTC"]), "B1": b1(P["BTC"], V), "B2": b2(markets, names, side, n), "B3": crh(P, idx),
           "B4": b4(markets, names, idx), "oracle": oracle(P["BTC"], names)}
    return {m: pd.Series(res[m], index=idx) for m in METHODS}
