"""Bitstamp public OHLC adapter (authorized by the user 2026-10-11; unauthenticated public endpoint).

Bitstamp publishes no archive checksums. Each month is paged from
``/api/v2/ohlc/{pair}/`` (step 60 s, up to 1,000 bars per request), written to a
derived CSV, and its SHA-256 is recorded in the acquisition manifest at download
time; loads verify against that recorded hash. The manifest labels this a
self-recorded hash, not a provider checksum. Zero-volume bars (price carried
forward by the provider) are kept, and the traded mask excludes them.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

from .binance_klines import gap_summary, to_minute_grid

ENDPOINT = "https://www.bitstamp.net/api/v2/ohlc/{pair}/?step=60&limit=1000&start={start}"
COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def _get(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310 - fixed public https host
        return json.loads(response.read())


def month_bounds(month: str) -> tuple[int, int]:
    start = pd.Timestamp(f"{month}-01", tz="UTC")
    end = start + pd.offsets.MonthBegin(1)
    return int(start.timestamp()), int(end.timestamp())


def fetch_month(pair: str, month: str, *, get: Callable[[str], dict[str, Any]] = _get,
                pause: float = 0.15) -> tuple[pd.DataFrame, int]:
    """All 1-minute bars with start <= t < end for the month; returns (frame, pages requested)."""
    lo, hi = month_bounds(month)
    rows: dict[int, dict[str, str]] = {}
    cursor, pages = lo, 0
    while cursor < hi:
        payload = get(ENDPOINT.format(pair=pair.lower(), start=cursor))
        pages += 1
        bars = payload.get("data", {}).get("ohlc", [])
        if not bars:
            break
        for bar in bars:
            t = int(bar["timestamp"])
            if lo <= t < hi:
                rows[t] = bar
        last = int(bars[-1]["timestamp"])
        if last < cursor:
            raise ValueError("provider returned bars out of order")
        cursor = last + 60
        if pause:
            time.sleep(pause)
    frame = pd.DataFrame([rows[t] for t in sorted(rows)], columns=COLUMNS)
    return frame.astype({"timestamp": "int64", **{c: "float64" for c in COLUMNS[1:]}}), pages


def save_month(frame: pd.DataFrame, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, float_format="%.10g")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_months(directory: Path, pair: str, prefix: str, manifest: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load every {PAIR}-1m-YYYY-MM.csv in ``directory``; each must match its manifest SHA-256."""
    records = {r["file"].rsplit("/", 1)[-1]: r for r in json.loads(manifest.read_text())["records"]
               if r.get("venue") == "bitstamp" and r.get("status") == "VERIFIED"}
    files = sorted(directory.glob(f"{pair.upper()}-1m-*.csv"))
    if not files:
        raise FileNotFoundError(f"no {pair} Bitstamp files in {directory}")
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
        raise ValueError("overlapping Bitstamp months")
    grid = to_minute_grid(frame, frame.index[0].floor("D"), frame.index[-1].floor("D") + pd.Timedelta("1D"), prefix)
    return grid, {"source": "bitstamp_public_ohlc", "files": prov, "gaps": gap_summary(grid, prefix)}
