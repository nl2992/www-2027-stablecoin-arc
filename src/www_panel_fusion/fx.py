"""ECB euro reference rates (decision D20) turned into an official F-per-USD hourly series with no look-ahead.

The ECB publishes the daily reference rates at about 14:15 CET. CET is taken literally as UTC+1 all year (13:15 UTC), which is never
earlier than the real publication time, so a rate is never used before it existed. A rate published at time T is usable by every hour
whose START is at or after T; the first usable hour start is therefore the next full hour (14:00 UTC), and the rate is carried forward
to every later hour until the next publication.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
ECB_ZIP = REPO / "data" / "raw" / "ecb" / "eurofxref-hist.zip"
CURRENCIES = ("USD", "TRY", "BRL", "ZAR", "KRW", "RUB")
PUBLISH_UTC = pd.Timedelta(hours=13, minutes=15)  # 14:15 CET = UTC+1
RUB_LAST_DAY = pd.Timestamp("2022-02-28")  # the ECB stopped publishing RUB on 2022-03-01


def read_ecb(path: Path = ECB_ZIP) -> pd.DataFrame:
    """Daily ECB rates (F per EUR) for USD, TRY, BRL, ZAR, KRW, RUB, indexed by publication date (tz-naive), N/A as NaN."""
    with zipfile.ZipFile(path) as zf:
        raw = pd.read_csv(io.BytesIO(zf.read(zf.namelist()[0])), na_values=["N/A"], usecols=lambda c: c == "Date" or c in CURRENCIES)
    raw["Date"] = pd.to_datetime(raw["Date"])
    return raw.set_index("Date").sort_index()[list(CURRENCIES)]


def f_per_usd(ecb: pd.DataFrame, fiat: str) -> pd.Series:
    """Official F per USD = (F per EUR) / (USD per EUR), indexed by the UTC instant from which the rate is usable (publication time)."""
    s = (ecb[fiat] / ecb["USD"]).dropna()
    if fiat == "RUB":
        s = s[s.index <= RUB_LAST_DAY]
    s.index = pd.DatetimeIndex(s.index.tz_localize("UTC") + PUBLISH_UTC, name="published_utc")
    return s[s > 0]


def hourly_official(ecb: pd.DataFrame, fiat: str, hours: pd.DatetimeIndex) -> pd.Series:
    """Official F-per-USD for each hour START in ``hours``: the latest rate with publication time <= hour start (carried forward).
    RUB has no hour after the last published rate's validity window: hours from 2022-03-01 00:00 UTC are NaN."""
    s = f_per_usd(ecb, fiat)
    pos = s.index.searchsorted(hours, side="right") - 1
    out = pd.Series(np.where(pos >= 0, s.to_numpy()[np.clip(pos, 0, None)], np.nan), index=hours, name=fiat)
    if fiat == "RUB":
        out[out.index >= pd.Timestamp("2022-03-01", tz="UTC")] = np.nan
    return out
