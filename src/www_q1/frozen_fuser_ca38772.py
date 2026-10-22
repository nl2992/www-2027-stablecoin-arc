"""STABLE fuser: the only file the autoresearch loop edits (numpy and pandas only; no harness imports).

Causal (row t uses rows at or before t only), label-agnostic (market, unit and venue labels are anonymous and re-drawn on
every call) and unaware of any reference price.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

HOLD = 24
SMOOTH = 3
W_ROOT = 2.0
SLOW = 48
BAND = 0.0005
REL_WIN = 72
REL_C = 0.0003
REL_ON = 1
TRIM = 0.002


def _nanmed(x: np.ndarray) -> np.ndarray:
    return pd.DataFrame(x).median(axis=1).to_numpy()


def _parse(col: str):
    pair, venue = col.split("@", 1)
    a, b = pair.split("/", 1)
    return a, b, venue


def _wmed(x: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Row-wise weighted median of x (NaN ignored); w is one weight per column."""
    ok = np.isfinite(x)
    ww = np.where(ok, w if w.ndim == 2 else w[None, :], 0.0)
    order = np.argsort(np.where(ok, x, np.inf), axis=1)
    xs = np.take_along_axis(np.where(ok, x, 0.0), order, 1)
    cw = np.cumsum(np.take_along_axis(ww, order, 1), axis=1)
    tot = cw[:, -1:]
    k = (cw >= 0.5 * tot).argmax(axis=1)
    out = xs[np.arange(len(x)), k]
    return np.where(tot[:, 0] > 0, out, np.nan)


def dollar_unit(meta, side):
    """Unit that is only ever a quote in the side rates (never a base); ties/none -> unit with most markets."""
    bases, quotes = {}, {}
    for c in side.columns:
        a, b, v = _parse(c)
        bases[a] = bases.get(a, 0) + 1
        quotes[b] = quotes.get(b, 0) + 1
    cand = [u for u in quotes if u not in bases]
    count = {}
    for m in meta.values():
        count[m["unit"]] = count.get(m["unit"], 0) + 1
    pool = cand if cand else list(count)
    return max(sorted(pool), key=lambda u: (quotes.get(u, 0), count.get(u, 0)))


def unit_values(units, root, side, n):
    """Log value of each unit in the root unit via shortest paths over side rates (NaN when unknown)."""
    edges = {}
    for c in side.columns:
        a, b, v = _parse(c)
        x = pd.Series(side[c].to_numpy(float)).ffill(limit=HOLD).to_numpy()
        edges.setdefault((a, b), []).append(x)
        edges.setdefault((b, a), []).append(-x)
    val = {root: np.zeros(n)}
    frontier = {root}
    while frontier:
        new = {}
        for (a, b), xs in edges.items():
            if a in val or b not in frontier:
                continue
            new.setdefault(a, []).extend(x + val[b] for x in xs)
        frontier = set()
        for a, xs in new.items():
            val[a] = _nanmed(np.column_stack(xs))
            frontier.add(a)
    return {u: val.get(u, np.full(n, np.nan)) for u in units}


def fuse(markets: dict[str, pd.DataFrame], meta: dict[str, dict[str, str]], side: pd.DataFrame) -> pd.Series:
    """Fused log BTC/USD per hour: ``markets[m]['BTC']`` is the log price in the market's own quote unit."""
    names = sorted(markets)
    idx = markets[names[0]].index
    n = len(idx)
    units = sorted({meta[m]["unit"] for m in names})
    root = dollar_unit(meta, side)
    vals = unit_values(units, root, side, n)
    fast = {u: pd.Series(v).rolling(SMOOTH, min_periods=1).median().to_numpy() for u, v in vals.items()}
    slow = {u: pd.Series(v).rolling(SLOW, min_periods=1).median().to_numpy() for u, v in vals.items()}
    vals = {u: np.where(np.abs(fast[u] - slow[u]) < BAND, slow[u], fast[u]) for u in vals}
    cols = []
    for m in names:
        r = vals[meta[m]["unit"]]
        cols.append(markets[m]["BTC"].to_numpy(float) + np.where(np.isfinite(r), r, 0.0))
    X = np.column_stack(cols)
    w = np.array([W_ROOT if meta[m]["unit"] == root else 1.0 for m in names])
    f = _wmed(X, w)
    if REL_ON:
        dev = pd.DataFrame(np.abs(X - f[:, None])).rolling(REL_WIN, min_periods=6).mean().shift(1).to_numpy()
        dev = np.where(np.isfinite(dev), dev, np.nanmean(dev, axis=1, keepdims=True) if False else REL_C * 3)
        W = w[None, :] / (dev + REL_C)
        f = _wmed(X, W)
        if TRIM > 0:
            near = np.isfinite(X) & (np.abs(X - f[:, None]) <= TRIM)
            ws = np.where(near, W, 0.0)
            den = ws.sum(axis=1)
            g = (np.where(near, X, 0.0) * ws).sum(axis=1) / np.where(den > 0, den, 1.0)
            f = np.where(den > 0, g, f)
    return pd.Series(f, index=idx)
