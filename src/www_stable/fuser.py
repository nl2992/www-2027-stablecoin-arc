"""STABLE fuser: the only file the autoresearch loop edits (numpy and pandas only; no harness imports).

Causal (row t uses rows at or before t only), label-agnostic (market, unit and venue labels are anonymous and re-drawn on
every call) and unaware of any reference price. Starting point: the naive median over all markets (baseline B0).
"""

from __future__ import annotations

import pandas as pd


def fuse(markets: dict[str, pd.DataFrame], meta: dict[str, dict[str, str]], side: pd.DataFrame) -> pd.Series:
    """Fused log BTC/USD per hour: ``markets[m]['BTC']`` is the log price in the market's own quote unit."""
    return pd.concat([markets[m]["BTC"] for m in sorted(markets)], axis=1).median(axis=1)
