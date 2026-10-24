"""Hourly loaders for the currency-wedge panel (autoresearch/program_panel.md). Hourly close prices on a UTC hour grid."""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from www_events.binance_klines import parse_kline_csv  # noqa: E402

RAW = REPO / "data" / "raw" / "panel"
KRAKEN = REPO / "data" / "raw" / "kraken_ohlcvt"
BINANCE_FIATS = ("NGN", "TRY", "ARS", "BRL", "RUB", "UAH", "ZAR")  # EUR, GBP, AUD have no USDT market
UNITS = [("binance", f) for f in BINANCE_FIATS] + [("upbit", "KRW"), ("bithumb", "KRW")]
BASES = ("BTC", "ETH", "USDT")
LAST_MONTH = "2025-09"


def unit_key(venue: str, fiat: str) -> str:
    return f"{venue}-{fiat}"


def _binance_files(base: str, fiat: str) -> list[Path]:
    return sorted((RAW / "binance" / f"{base}{fiat}").glob("*.zip"))


def read_binance(base: str, fiat: str, *, volume_only: bool = False) -> pd.DataFrame:
    """Hourly close and volume. ``volume_only`` drops the price column at once (used for the coverage count on USDT/F)."""
    parts = []
    for path in _binance_files(base, fiat):
        with zipfile.ZipFile(path) as zf:
            name = [n for n in zf.namelist() if n.endswith(".csv")][0]
            frame = parse_kline_csv(zf.read(name).decode("utf-8"), interval_minutes=60).frame[["close", "volume"]]
        if volume_only:
            frame = frame[["volume"]]
        parts.append(frame)
    out = pd.concat(parts).sort_index()
    return out[~out.index.duplicated(keep="first")]


def read_krw(venue: str, base: str, *, volume_only: bool = False) -> pd.DataFrame:
    frame = pd.read_csv(RAW / venue / f"KRW-{base}_60m.csv", usecols=["timestamp_utc", "close", "volume"])
    frame.index = pd.DatetimeIndex(pd.to_datetime(frame.pop("timestamp_utc"), utc=True), name="timestamp_utc")
    frame = frame.sort_index()
    frame = frame[~frame.index.duplicated(keep="first")]
    return frame[["volume"]] if volume_only else frame


def read_pair(venue: str, fiat: str, base: str, *, volume_only: bool = False) -> pd.DataFrame:
    return read_binance(base, fiat, volume_only=volume_only) if venue == "binance" else read_krw(venue, base, volume_only=volume_only)


def read_kraken(pair: str) -> pd.Series:
    """Hourly close of data/raw/kraken_ohlcvt/<pair>_60.csv (epoch seconds, hour start), as a UTC-indexed Series."""
    frame = pd.read_csv(KRAKEN / f"{pair}_60.csv", header=None, names=["t", "open", "high", "low", "close", "volume", "trades"])
    s = pd.Series(frame["close"].to_numpy(float), index=pd.DatetimeIndex(pd.to_datetime(frame["t"], unit="s", utc=True), name="timestamp_utc"))
    s = s[~s.index.duplicated(keep="first")].sort_index()
    return s[s > 0]


def month_hours(month: str) -> int:
    p = pd.Period(month, freq="M")
    return p.days_in_month * 24


def months_between(first: str, last: str) -> list[str]:
    return [str(p) for p in pd.period_range(first, last, freq="M")]


def log_bps(price: pd.Series) -> pd.Series:
    return 1e4 * np.log(price.where(price > 0))
