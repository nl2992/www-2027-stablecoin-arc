"""FUSE fuser: the only file the autoresearch loop edits (numpy and pandas only; no harness imports).

Causal (row t uses rows at or before t only), source-agnostic (keys are anonymous) and unaware of any reference price.
Step 1: trailing-window reliability-weighted mean (CRH-style weights refit once per day on the previous 30 days).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

WINDOW = 168
MIN_HIST = 24


def _crh_weights(x: np.ndarray, max_iter: int = 100, tol: float = 1e-9) -> np.ndarray:
    m = np.isfinite(x)
    k = x.shape[1]
    w = np.ones(k)
    keep = m.sum(axis=1) >= 2
    x, m = x[keep], m[keep]
    if x.shape[0] == 0:
        return w
    x0 = np.where(m, x, 0.0)
    for _ in range(max_iter):
        truth = (x0 * w).sum(axis=1) / (m * w).sum(axis=1)
        loss = (m * (x0 - truth[:, None]) ** 2).sum(axis=0)
        total = loss.sum()
        if total <= 1e-18:
            return np.ones(k)
        loss = np.maximum(loss, 1e-12 * total)
        new = -np.log(loss / loss.sum())
        if np.abs(new - w).max() < tol:
            return new
        w = new
    return w


def _blocks(index: pd.DatetimeIndex):
    day = index.floor("D")
    starts = np.r_[0, np.flatnonzero(day[1:] != day[:-1]) + 1]
    ends = np.r_[starts[1:], len(index)]
    ts = index.asi8
    for s, e in zip(starts, ends):
        lo = np.searchsorted(ts, ts[s] - WINDOW * 3_600_000_000_000, side="left")
        yield int(s), int(e), int(lo)


def fuse(panel: dict[str, pd.DataFrame], items: list[str]) -> pd.DataFrame:
    """Fused log USD price per hour for each item (hours x items; NaN where no source quotes the item)."""
    names = sorted(panel)
    index = None
    for frame in panel.values():
        index = frame.index if index is None else index.union(frame.index)
    T, S = len(index), len(names)
    P = {a: np.column_stack([panel[n][a].reindex(index).to_numpy(float) if a in panel[n].columns else np.full(T, np.nan)
                             for n in names]) for a in items}
    out = {a: np.full(T, np.nan) for a in items}
    for s, e, lo in _blocks(index):
        w = np.ones(S)
        if s > lo:
            x = np.vstack([1e4 * P[a][lo:s] for a in items])
            multi = np.isfinite(x).sum(axis=1) >= 2
            if multi.any():
                w = _crh_weights(x)
                few = np.isfinite(x[multi]).sum(axis=0) < MIN_HIST
                if few.any():
                    w = np.where(few, w[~few].mean() if (~few).any() else 1.0, w)
        for a in items:
            blk = P[a][s:e]
            m = np.isfinite(blk)
            den = (m * w).sum(axis=1)
            out[a][s:e] = np.where(den > 0, (np.where(m, blk, 0.0) * w).sum(axis=1) / np.where(den > 0, den, 1.0), np.nan)
    return pd.DataFrame(out, index=index)[list(items)]
