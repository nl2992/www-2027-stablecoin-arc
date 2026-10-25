"""Loaders for the Kraken fiat-panel slice (autoresearch/program_panel_kraken.md): hourly Kraken closes and Bitstamp USD references."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from www_panel.data import log_bps, month_hours, months_between, read_kraken  # noqa: E402,F401
from www_panel.run import _hourly_from_minutes  # noqa: E402

KRAKEN = REPO / "data" / "raw" / "kraken_ohlcvt"
BITSTAMP = REPO / "data" / "raw" / "bitstamp"
FIATS = ("EUR", "GBP", "CAD", "AUD", "CHF", "JPY")
FIRST_MONTH, LAST_MONTH, LAST_ETH_MONTH = "2017-01", "2025-03", "2023-12"
BASES = ("XBT", "ETH", "USDT")


def pair_file(base: str, fiat: str) -> Path:
    return KRAKEN / f"{base}{fiat}_60.csv"


def available_fiats() -> list[str]:
    """Fiat currencies for which Kraken's XBT/F, ETH/F and USDT/F 60-minute files all exist."""
    return [f for f in FIATS if all(pair_file(b, f).exists() for b in BASES)]


def read_volume(base: str, fiat: str) -> pd.Series:
    """Hourly traded-volume indicator only (the price column is never read), hours with positive volume."""
    frame = pd.read_csv(pair_file(base, fiat), header=None, names=["t", "open", "high", "low", "close", "volume", "trades"],
                        usecols=["t", "volume"])
    idx = pd.DatetimeIndex(pd.to_datetime(frame["t"], unit="s", utc=True), name="timestamp_utc")
    s = pd.Series(frame["volume"].to_numpy(float), index=idx)
    s = s[~s.index.duplicated(keep="first")].sort_index()
    return s[s > 0]


def read_close(base: str, fiat: str) -> pd.Series:
    """Hourly close of the Kraken pair on hours with positive volume."""
    frame = pd.read_csv(pair_file(base, fiat), header=None, names=["t", "open", "high", "low", "close", "volume", "trades"])
    idx = pd.DatetimeIndex(pd.to_datetime(frame["t"], unit="s", utc=True), name="timestamp_utc")
    s = pd.Series(frame["close"].to_numpy(float), index=idx)[(frame["volume"] > 0).to_numpy()]
    s = s[~s.index.duplicated(keep="first")].sort_index()
    return s[s > 0]


def read_bitstamp_usd(pair: str) -> pd.Series:
    """Bitstamp <pair> (BTCUSD or ETHUSD) hourly close: last traded-minute close within each UTC hour, from the 1-minute CSVs."""
    parts = [pd.read_csv(p) for p in sorted(BITSTAMP.glob(f"{pair}-1m-*.csv"))]
    f = pd.concat(parts)
    idx = pd.DatetimeIndex(pd.to_datetime(f["timestamp"], unit="s", utc=True))
    h = _hourly_from_minutes(pd.Series(f["close"].to_numpy(float), index=idx).sort_index(),
                             pd.Series(f["volume"].to_numpy(float), index=idx).sort_index())
    return h[h > 0]


def gap(kraken: pd.Series, ref: pd.Series) -> pd.Series:
    j = pd.concat([kraken.rename("k"), ref.rename("r")], axis=1, join="inner")
    return log_bps(j["k"]) - log_bps(j["r"])
