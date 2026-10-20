"""UNIT-TD estimator: the only file the autoresearch loop edits (numpy and pandas only; no harness imports).

Starting point = the b2 logic: for each venue, the same-hour median over assets of the log-price gap to the numeraire
venue, in bps. Causal (row t uses row t only), venue-agnostic (no names), and the numeraire column is 0.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _price_columns(frame: pd.DataFrame) -> list[str]:
    return [c for c in frame.columns if not str(c).endswith("_vol")]


def estimate_units(panel: dict[str, pd.DataFrame], numeraire_venue: str) -> pd.DataFrame:
    """Unit offset (bps) of every venue relative to ``numeraire_venue``, per hour.

    panel: venue -> DataFrame with a log-price column per asset and an ``{asset}_vol`` column.
    Returns hours x venues; the numeraire column is 0. NaN where no asset is shared with the numeraire that hour.
    """
    index = panel[numeraire_venue].index
    for frame in panel.values():
        index = index.union(frame.index)
    base = panel[numeraire_venue]
    out = pd.DataFrame(0.0, index=index, columns=list(panel))
    for venue, frame in panel.items():
        if venue == numeraire_venue:
            continue
        shared = [c for c in _price_columns(frame) if c in base.columns]
        if not shared:
            out[venue] = np.nan
            continue
        gaps = 1e4 * (frame[shared].reindex(index) - base[shared].reindex(index))
        loc = gaps.median(axis=1, skipna=True)
        n = gaps.notna().sum(axis=1)
        dev = gaps.sub(loc, axis=0).abs().median(axis=1, skipna=True)
        var = (1.4826 * dev) ** 2 * n / (n - 1).clip(lower=1)
        # James-Stein-style shrinkage toward 0: keep the share of loc^2 not explained by cross-asset noise
        keep = (1.0 - var / (n * loc**2 + 1e-12)).clip(lower=0.0, upper=1.0).fillna(0.0)
        out[venue] = (loc * keep).where(loc.notna())
    return out
