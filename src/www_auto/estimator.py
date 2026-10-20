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
        out[venue] = gaps.median(axis=1, skipna=True)
    return out
