"""Bitfinex and Coinbase Exchange public 1-minute candle adapters (authorized by the user 2026-10-18).

Both endpoints are unauthenticated and publish no checksums. Like the Bitstamp adapter, each month is paged,
written to a derived CSV with the Bitstamp columns, and its SHA-256 is recorded in the acquisition manifest at
download time; loads verify against that hash. Both providers omit minutes with no trades, so absent minutes
stay NaN and untraded on the grid.

Bitfinex:  /v2/candles/trade:1m:t{PAIR}/hist  rows [mts, open, close, high, low, volume], up to 10,000 per page.
Coinbase:  /products/{BASE-QUOTE}/candles     rows [time, low, high, open, close, volume], up to 300 per page,
           newest first; requests are made in fixed 300-minute windows.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

from .binance_klines import gap_summary, to_minute_grid
from .bitstamp import COLUMNS, month_bounds

BITFINEX = ("https://api-pub.bitfinex.com/v2/candles/trade:1m:t{pair}/hist"
            "?start={start}&end={end}&limit=10000&sort=1")
COINBASE = "https://api.exchange.coinbase.com/products/{product}/candles?granularity=60&start={start}&end={end}"
BITFINEX_1H = ("https://api-pub.bitfinex.com/v2/candles/trade:1h:t{pair}/hist"
               "?start={start}&end={end}&limit=10000&sort=1")
COINBASE_1H = "https://api.exchange.coinbase.com/products/{product}/candles?granularity=3600&start={start}&end={end}"
USER_AGENT = "www-stablecoin-research/0.1"


def _get(url: str, *, retries: int = 5) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - fixed public https hosts
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == retries - 1:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries - 1:
                raise
        time.sleep(10 * (attempt + 1))
    raise RuntimeError("unreachable")


def _frame(rows: dict[int, list[float]]) -> pd.DataFrame:
    frame = pd.DataFrame([[t, *rows[t]] for t in sorted(rows)], columns=COLUMNS)
    return frame.astype({"timestamp": "int64", **{c: "float64" for c in COLUMNS[1:]}})


def fetch_bitfinex_month(pair: str, month: str, *, get: Callable[[str], Any] = _get,
                         pause: float = 2.5) -> tuple[pd.DataFrame, int]:
    lo, hi = month_bounds(month)
    rows: dict[int, list[float]] = {}
    cursor, pages = lo, 0
    while cursor < hi:
        bars = get(BITFINEX.format(pair=pair.upper(), start=cursor * 1000, end=hi * 1000 - 1))
        pages += 1
        if not bars:
            break
        for mts, o, c, h, low, v in bars:
            t = int(mts) // 1000
            if lo <= t < hi:
                rows[t] = [o, h, low, c, v]
        last = int(bars[-1][0]) // 1000
        if last < cursor:
            raise ValueError("provider returned bars out of order")
        cursor = last + 60
        if pause:
            time.sleep(pause)
    return _frame(rows), pages


def fetch_coinbase_month(product: str, month: str, *, get: Callable[[str], Any] = _get,
                         pause: float = 0.2) -> tuple[pd.DataFrame, int]:
    lo, hi = month_bounds(month)
    rows: dict[int, list[float]] = {}
    pages = 0
    for start in range(lo, hi, 300 * 60):
        end = min(start + 300 * 60, hi) - 60  # Coinbase's end bound is inclusive
        iso = lambda s: pd.Timestamp(s, unit="s", tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
        bars = get(COINBASE.format(product=product.upper(), start=iso(start), end=iso(end)))
        pages += 1
        for t, low, h, o, c, v in bars:
            if lo <= int(t) < hi:
                rows[int(t)] = [o, h, low, c, v]
        if pause:
            time.sleep(pause)
    return _frame(rows), pages


def hourly_bounds(first_month: str, last_month: str) -> tuple[int, int]:
    return month_bounds(first_month)[0], month_bounds(last_month)[1]


def fetch_bitfinex_hourly(pair: str, first_month: str, last_month: str, *, get: Callable[[str], Any] = _get,
                          pause: float = 1.5) -> tuple[pd.DataFrame, int]:
    """All hourly bars with first_month start <= t < end of last_month (10,000 per page, ascending)."""
    lo, hi = hourly_bounds(first_month, last_month)
    rows: dict[int, list[float]] = {}
    cursor, pages = lo, 0
    while cursor < hi:
        bars = get(BITFINEX_1H.format(pair=pair.upper(), start=cursor * 1000, end=hi * 1000 - 1))
        pages += 1
        if not bars:
            break
        for mts, o, c, h, low, v in bars:
            t = int(mts) // 1000
            if lo <= t < hi:
                rows[t] = [o, h, low, c, v]
        last = int(bars[-1][0]) // 1000
        if last < cursor:
            raise ValueError("provider returned bars out of order")
        cursor = last + 3600
        if pause:
            time.sleep(pause)
    return _frame(rows), pages


def fetch_coinbase_hourly(product: str, first_month: str, last_month: str, *, get: Callable[[str], Any] = _get,
                          pause: float = 0.3) -> tuple[pd.DataFrame, int]:
    """All hourly bars in the range, requested in fixed 300-hour windows (Coinbase's end bound is inclusive)."""
    lo, hi = hourly_bounds(first_month, last_month)
    rows: dict[int, list[float]] = {}
    pages = 0
    iso = lambda s: pd.Timestamp(s, unit="s", tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
    for start in range(lo, hi, 300 * 3600):
        end = min(start + 300 * 3600, hi) - 3600
        bars = get(COINBASE_1H.format(product=product.upper(), start=iso(start), end=iso(end)))
        pages += 1
        for t, low, h, o, c, v in bars:
            if lo <= int(t) < hi:
                rows[int(t)] = [o, h, low, c, v]
        if pause:
            time.sleep(pause)
    return _frame(rows), pages


def load_venue_months(directory: Path, pair: str, prefix: str, manifest: Path, venue: str,
                      months: list[str] | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load {PAIR}-1m-YYYY-MM.csv files for ``venue`` (all, or only ``months``); each must match its manifest SHA-256."""
    records = {r["file"].rsplit("/", 1)[-1]: r for r in json.loads(manifest.read_text())["records"]
               if r.get("venue") == venue and r.get("status") == "VERIFIED"}
    files = sorted(directory.glob(f"{pair.upper()}-1m-*.csv"))
    if months is not None:
        files = [f for f in files if f.stem.rsplit("-1m-", 1)[1] in months]
    if not files:
        raise FileNotFoundError(f"no {pair} {venue} files in {directory}")
    frames, prov = [], []
    for f in files:
        rec = records.get(f.name)
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        if rec is None or rec["sha256"] != digest:
            raise ValueError(f"{f.name} does not match its recorded manifest hash")
        raw = pd.read_csv(f)
        if list(raw.columns) != COLUMNS:
            raise ValueError(f"{f.name}: unexpected columns {list(raw.columns)}")
        raw.index = pd.DatetimeIndex(pd.to_datetime(raw["timestamp"], unit="s", utc=True), name="timestamp_utc")
        frames.append(raw[COLUMNS[1:]])
        prov.append({"file": f.name, "sha256": digest, "hash_kind": "self-recorded at acquisition"})
    frame = pd.concat(frames).sort_index()
    if frame.index.has_duplicates:
        raise ValueError(f"overlapping {venue} months")
    start = frame.index[0].tz_convert(None).to_period("M").to_timestamp().tz_localize("UTC")
    end = (frame.index[-1].tz_convert(None).to_period("M") + 1).to_timestamp().tz_localize("UTC")
    grid = to_minute_grid(frame, start, end, prefix)
    return grid, {"source": f"{venue}_public_candles", "files": prov, "gaps": gap_summary(grid, prefix)}
