"""FUSE fuser: the only file the autoresearch loop edits (numpy and pandas only; no harness imports).

Causal (row t uses rows at or before t only), source-agnostic (keys are anonymous) and unaware of any reference price.
Step 1: trailing-window reliability-weighted mean (CRH-style weights refit once per day on the previous 30 days).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

WINDOW = 72
MIN_HIST = 24
OFF_WIN = 8
OFF_MIN = 6
SHRINK = 1.0
VAR_FLOOR = 0.3


def _crh_weights(x: np.ndarray, max_iter: int = 20, tol: float = 1e-9) -> np.ndarray:
    """Inverse-variance reliability weights from claims vs the weighted-mean truth (variance floored)."""
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
        var = (m * (x0 - truth[:, None]) ** 2).sum(axis=0) / np.maximum(m.sum(axis=0), 1)
        ok = m.sum(axis=0) > 0
        if not ok.any() or var[ok].mean() <= 1e-12:
            return np.ones(k)
        var = np.maximum(var, VAR_FLOOR * var[ok].mean())
        new = 1.0 / var
        new = new / new[ok].mean()
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


def _offsets(A: dict[str, np.ndarray], cols: list[str], skip: str, index: pd.DatetimeIndex) -> np.ndarray:
    """Per-source unit offset (hours x sources, log units): trailing median of the cross-asset median gap against the
    cross-source median, using every asset except ``skip``."""
    gaps = []
    for c in cols:
        if c == skip or c == "USDT":
            continue
        x = A[c]
        if (np.isfinite(x).sum(axis=1) >= 3).sum() == 0:
            continue
        with np.errstate(all="ignore"):
            med = np.nanmedian(np.where((np.isfinite(x).sum(axis=1) >= 3)[:, None], x, np.nan), axis=1)
        gaps.append(x - med[:, None])
    if not gaps:
        return np.zeros_like(A[skip])
    with np.errstate(all="ignore"):
        g = np.stack(gaps)
        raw = np.nanmedian(g, axis=0)
        disp = np.nanmedian(np.abs(g - raw[None]), axis=0)
    off = pd.DataFrame(raw, index=index).rolling(OFF_WIN, min_periods=OFF_MIN).median().to_numpy()
    dsp = pd.DataFrame(disp, index=index).rolling(OFF_WIN, min_periods=OFF_MIN).median().to_numpy()
    with np.errstate(all="ignore"):
        shrink = np.abs(off) / (np.abs(off) + SHRINK * dsp)
    return np.nan_to_num(off * shrink)


def fuse(panel: dict[str, pd.DataFrame], items: list[str]) -> pd.DataFrame:
    """Fused log USD price per hour for each item (hours x items; NaN where no source quotes the item)."""
    names = sorted(panel)
    index = None
    for frame in panel.values():
        index = frame.index if index is None else index.union(frame.index)
    T, S = len(index), len(names)
    P = {a: np.column_stack([panel[n][a].reindex(index).to_numpy(float) if a in panel[n].columns else np.full(T, np.nan)
                             for n in names]) for a in items}
    cols = sorted({c for n in names for c in panel[n].columns if not c.endswith("_vol")})
    A = {a: P[a] if a in P else np.column_stack([panel[n][a].reindex(index).to_numpy(float) if a in panel[n].columns
                                                   else np.full(T, np.nan) for n in names]) for a in cols}
    out = {a: np.full(T, np.nan) for a in items}
    Pc = {a: P[a] - _offsets(A, cols, a, index) for a in items}
    for s, e, lo in _blocks(index):
        w = np.ones(S)
        if s > lo:
            x = np.vstack([1e4 * Pc[a][lo:s] for a in items])
            multi = np.isfinite(x).sum(axis=1) >= 2
            if multi.any():
                w = _crh_weights(x)
                few = np.isfinite(x[multi]).sum(axis=0) < MIN_HIST
                if few.any():
                    w = np.where(few, w[~few].mean() if (~few).any() else 1.0, w)
        for a in items:
            blk = Pc[a][s:e]
            m = np.isfinite(blk)
            den = (m * w).sum(axis=1)
            out[a][s:e] = np.where(den > 0, (np.where(m, blk, 0.0) * w).sum(axis=1) / np.where(den > 0, den, 1.0), np.nan)
    return pd.DataFrame(out, index=index)[list(items)]
