"""Fixed baselines for the FUSE harness (not editable by the loop; the harness is their only caller).

All are causal, take (hours x sources) arrays of log prices per item and use only rows at or before each hour. Hyper-parameters
come from ``www_auto.td_realdata`` (literature defaults, fixed before any result).
"""

from __future__ import annotations

import warnings
from collections.abc import Callable

import numpy as np
import pandas as pd

from www_auto import td_realdata as TD
from www_auto.estimator import estimate_units

MIN_CRH_HISTORY = 24  # a source with fewer trailing claims gets the mean weight of the others
NUMERAIRE_MIN_OBS = 24
ORACLE_SOURCES = ("coinbase", "bitstamp")
METHODS = ("median", "vwap", "trimmed", "drop_deviant", "crh", "gtm", "unit_aware", "oracle")


def _quiet(fn: Callable[..., np.ndarray], *a, **k) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return fn(*a, **k)


def median(p: np.ndarray, v: np.ndarray) -> np.ndarray:
    return _quiet(np.nanmedian, p, axis=1)


def vwap(p: np.ndarray, v: np.ndarray) -> np.ndarray:
    w = np.where(np.isfinite(p), np.where(np.isfinite(v) & (v > 0), v, 1.0), 0.0)
    den = w.sum(axis=1)
    return np.where(den > 0, (np.where(np.isfinite(p), p, 0.0) * w).sum(axis=1) / np.where(den > 0, den, 1.0), np.nan)


def trimmed(p: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Drop the lowest and highest quote when four or more sources quote, else the median."""
    s = np.sort(p, axis=1)  # NaN sorts last
    n = np.isfinite(p).sum(axis=1)
    j = np.arange(p.shape[1])[None, :]
    keep = (j >= 1) & (j <= (n - 2)[:, None]) & (n >= 4)[:, None]
    mean = np.where(keep, s, 0.0).sum(axis=1) / np.maximum(keep.sum(axis=1), 1)
    return np.where(n >= 4, mean, median(p, v))


def drop_deviant(p: np.ndarray, v: np.ndarray) -> np.ndarray:
    """With three or more quotes, drop the one farthest from the median, then average the rest; else the mean."""
    med = median(p, v)
    n = np.isfinite(p).sum(axis=1)
    dev = np.where(np.isfinite(p), np.abs(p - med[:, None]), -1.0)
    far = dev.argmax(axis=1)
    q = p.copy()
    rows = np.flatnonzero(n >= 3)
    q[rows, far[rows]] = np.nan
    return _quiet(np.nanmean, q, axis=1)


def _stack(items: dict[str, np.ndarray], lo: int, hi: int) -> np.ndarray:
    return np.vstack([1e4 * a[lo:hi] for a in items.values()])


def truth_discovery(prices: dict[str, np.ndarray], idx: pd.DatetimeIndex) -> dict[str, dict[str, np.ndarray]]:
    """CRH and GTM fused log prices per item (td_realdata kernels), weights refit once per UTC day on the trailing 30 days
    that end before that day, pooled over items."""
    out = {m: {a: np.full(len(idx), np.nan) for a in prices} for m in ("crh", "gtm")}
    n_src = next(iter(prices.values())).shape[1]
    sc = TD.GTM["part1_scale_bps"]
    for s, e, lo in TD._day_blocks(idx):
        x = _stack(prices, lo, s) if s > lo else np.empty((0, n_src))
        w = np.ones(n_src)
        sig = np.full(n_src, TD.GTM["sigma_sq_init"])
        if len(x):
            multi = np.isfinite(x).sum(axis=1) >= 2
            if multi.any():
                w = TD.crh_masked(x, TD.HYPERPARAMETERS["crh"]["max_iter"], TD.HYPERPARAMETERS["crh"]["tol"])
                few = np.isfinite(x[multi]).sum(axis=0) < MIN_CRH_HISTORY
                if few.any():
                    w = np.where(few, w[~few].mean() if (~few).any() else 1.0, w)
                ctr = _quiet(np.nanmean, x[multi], axis=1, keepdims=True)
                sig = TD.gtm_fit((x[multi] - ctr) / sc)
        for a, p in prices.items():
            blk = p[s:e]
            m = np.isfinite(blk)
            den = (m * w).sum(axis=1)
            out["crh"][a][s:e] = np.where(den > 0, (np.where(m, blk, 0.0) * w).sum(axis=1) / np.where(den > 0, den, 1.0), np.nan)
            z = 1e4 * blk
            ctr = _quiet(np.nanmean, z, axis=1)
            has = m.any(axis=1)
            mu = TD.gtm_truth(np.where(m, (z - ctr[:, None]) / sc, np.nan), sig)
            out["gtm"][a][s:e] = np.where(has, (ctr + sc * mu) / 1e4, np.nan)
    return out


def pick_numeraire(prices: dict[str, np.ndarray], warm: int) -> int:
    """Name-free numeraire for the frozen estimator: the source whose first ``warm`` hours of quotes sit closest to the
    cross-source median (median absolute deviation over the fused items); only sources with enough quotes qualify."""
    n_src = next(iter(prices.values())).shape[1]
    dev = [[] for _ in range(n_src)]
    for p in prices.values():
        q = p[:warm]
        med = median(q, q)
        for i in range(n_src):
            d = np.abs(q[:, i] - med)
            dev[i].append(d[np.isfinite(d)])
    score = np.full(n_src, np.inf)
    for i in range(n_src):
        d = np.concatenate(dev[i])
        if len(d) >= NUMERAIRE_MIN_OBS:
            score[i] = np.median(d)
    return int(score.argmin())


def unit_aware(sources: dict[str, pd.DataFrame], names: list[str], items: list[str], prices: dict[str, np.ndarray],
               warm: int) -> dict[str, np.ndarray]:
    """Frozen unit-aware fuser (td_realdata.part1 recipe): estimator offsets from every visible asset EXCEPT the fused one,
    removed from each source's quote, then the median over sources (NaN-aware)."""
    num = pick_numeraire(prices, warm)
    out = {}
    for a in items:
        panel = {s: sources[s][[c for c in sources[s].columns if c.removesuffix("_vol") != a]] for s in names}
        units = estimate_units(panel, names[num])[names].reindex(sources[names[0]].index).to_numpy(float)
        out[a] = _quiet(np.nanmedian, prices[a] - np.nan_to_num(units) / 1e4, axis=1)
    return out


def oracle(prices: np.ndarray, names: list[str]) -> np.ndarray:
    cols = [i for i, n in enumerate(names) if n in ORACLE_SOURCES]
    return _quiet(np.nanmean, prices[:, cols], axis=1) if cols else np.full(len(prices), np.nan)


def all_baselines(sources: dict[str, pd.DataFrame], items: list[str], warm: int) -> dict[str, pd.DataFrame]:
    """Every baseline's fused log prices (hours x items) from the REAL-named sources of one episode slice."""
    names = list(sources)
    idx = sources[names[0]].index
    P = {a: np.column_stack([sources[s][a].to_numpy(float) if a in sources[s].columns else np.full(len(idx), np.nan)
                             for s in names]) for a in items}
    V = {a: np.column_stack([sources[s][a + "_vol"].to_numpy(float) if a + "_vol" in sources[s].columns else np.full(len(idx), np.nan)
                             for s in names]) for a in items}
    res: dict[str, dict[str, np.ndarray]] = {m: {} for m in METHODS}
    for a in items:
        for name, fn in (("median", median), ("vwap", vwap), ("trimmed", trimmed), ("drop_deviant", drop_deviant)):
            res[name][a] = fn(P[a], V[a])
        res["oracle"][a] = oracle(P[a], names)
    td = truth_discovery(P, idx)
    res["crh"], res["gtm"] = td["crh"], td["gtm"]
    res["unit_aware"] = unit_aware(sources, names, items, P, warm)
    return {m: pd.DataFrame(res[m], index=idx)[items] for m in METHODS}
