"""FUSE fuser: the only file the autoresearch loop edits (numpy and pandas only; no harness imports).

Starting point = the plain cross-source median of the log prices. Causal (row t uses rows at or before t only),
source-agnostic (keys are anonymous) and unaware of any reference price.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def fuse(panel: dict[str, pd.DataFrame], items: list[str]) -> pd.DataFrame:
    """Fused log USD price per hour for each item.

    panel: anonymous source key -> DataFrame (hourly index) with a log-price column per asset (``BTC``, ``ETH``,
    altcoins, ``USDT``) and an ``{asset}_vol`` volume column; NaN where the source has no trade that hour.
    items: the assets to fuse. Returns hours x items (NaN where no source quotes the item).
    """
    index = None
    for frame in panel.values():
        index = frame.index if index is None else index.union(frame.index)
    out = pd.DataFrame(np.nan, index=index, columns=list(items))
    for item in items:
        cols = [frame[item].reindex(index) for frame in panel.values() if item in frame.columns]
        if cols:
            out[item] = pd.concat(cols, axis=1).median(axis=1, skipna=True)
    return out
