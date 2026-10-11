"""Adapter for Binance public-data spot kline archives (data.binance.vision).

Archive CSVs have no header and the columns in ``KLINE_COLUMNS``. Spot archives
switched timestamp units from milliseconds to microseconds in 2025, so the unit
is inferred per file and recorded. Missing minutes stay missing: nothing is
forward-filled, and ``traded`` marks minutes with positive base volume.
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume", "close_time",
    "quote_volume", "trades", "taker_buy_base_volume", "taker_buy_quote_volume", "ignore",
]
PRICE_COLUMNS = ["open", "high", "low", "close"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksum(archive: Path, checksum_file: Path) -> str:
    """Compare the archive's SHA-256 with Binance's ``.CHECKSUM`` file ("<hex>  <name>")."""
    expected, _, name = checksum_file.read_text().strip().partition(" ")
    name = name.strip()
    if name and name != archive.name:
        raise ValueError(f"checksum file names {name}, not {archive.name}")
    actual = sha256_file(archive)
    if actual != expected.lower():
        raise ValueError(f"checksum mismatch for {archive.name}")
    return actual


def infer_time_unit(open_times: np.ndarray) -> str:
    """'ms' or 'us' from magnitude; mixed units within one file are rejected."""
    values = np.asarray(open_times, dtype=np.int64)
    if values.size == 0:
        raise ValueError("empty kline file")
    is_us = values >= 10**14
    if is_us.any() and not is_us.all():
        raise ValueError("mixed millisecond and microsecond timestamps")
    return "us" if is_us.all() else "ms"


@dataclass(frozen=True)
class KlineFile:
    frame: pd.DataFrame  # indexed by UTC minute open time
    time_unit: str
    rows: int
    duplicates_dropped: int
    issues: tuple[str, ...]


def parse_kline_csv(text: str, *, interval_minutes: int = 1) -> KlineFile:
    raw = pd.read_csv(io.StringIO(text), header=None)
    if raw.shape[1] != len(KLINE_COLUMNS):
        raise ValueError(f"expected {len(KLINE_COLUMNS)} columns, got {raw.shape[1]}")
    if not np.issubdtype(raw[0].dtype, np.integer):
        raise ValueError("first column must be integer open times (unexpected header row?)")
    raw.columns = KLINE_COLUMNS
    unit = infer_time_unit(raw["open_time"].to_numpy())
    times = pd.to_datetime(raw["open_time"], unit=unit, utc=True)
    issues: list[str] = []
    if (times != times.dt.floor(f"{interval_minutes}min")).any():
        raise ValueError("open times are not aligned to the interval")
    frame = raw[PRICE_COLUMNS + ["volume", "quote_volume", "trades"]].astype(float)
    frame.index = pd.DatetimeIndex(times, name="timestamp_utc")
    if not frame.index.is_monotonic_increasing:
        issues.append("rows out of order; sorted")
        frame = frame.sort_index(kind="stable")
    duplicated = frame.index.duplicated(keep="first")
    if duplicated.any():
        conflicting = frame[frame.index.duplicated(keep=False)].groupby(level=0).nunique().gt(1).any(axis=None)
        if conflicting:
            raise ValueError("duplicate open times with conflicting values")
        issues.append(f"{int(duplicated.sum())} identical duplicate rows dropped")
        frame = frame[~duplicated]
    bad = (frame[PRICE_COLUMNS] <= 0).any(axis=1) | (frame["volume"] < 0)
    if bad.any():
        raise ValueError(f"{int(bad.sum())} rows with non-positive price or negative volume")
    inconsistent = (frame["high"] < frame[["open", "close", "low"]].max(axis=1)) | (
        frame["low"] > frame[["open", "close", "high"]].min(axis=1))
    if inconsistent.any():
        raise ValueError(f"{int(inconsistent.sum())} rows violate low <= open/close <= high")
    return KlineFile(frame, unit, len(raw), int(duplicated.sum()), tuple(issues))


def read_kline_zip(archive: Path, *, interval_minutes: int = 1) -> KlineFile:
    with zipfile.ZipFile(archive) as zf:
        members = [n for n in zf.namelist() if n.endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"expected one CSV member, found {members}")
        return parse_kline_csv(zf.read(members[0]).decode("utf-8"), interval_minutes=interval_minutes)


def to_minute_grid(frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, prefix: str) -> pd.DataFrame:
    """Reindex to a complete UTC minute grid [start, end); absent minutes stay NaN and untraded."""
    grid = pd.date_range(start, end, freq="1min", inclusive="left", tz="UTC", name="timestamp_utc")
    out = frame.reindex(grid)
    result = pd.DataFrame(index=grid)
    result[f"{prefix}_close"] = out["close"]
    result[f"{prefix}_volume"] = out["volume"]
    result[f"{prefix}_present"] = out["close"].notna()
    result[f"{prefix}_traded"] = out["volume"].fillna(0) > 0
    return result


def gap_summary(grid: pd.DataFrame, prefix: str) -> dict[str, Any]:
    present = grid[f"{prefix}_present"].to_numpy()
    traded = grid[f"{prefix}_traded"].to_numpy()
    longest = run = 0
    for p in present:
        run = 0 if p else run + 1
        longest = max(longest, run)
    return {
        "grid_minutes": int(len(present)),
        "missing_minutes": int((~present).sum()),
        "longest_missing_run_minutes": int(longest),
        "present_untraded_minutes": int((present & ~traded).sum()),
        "traded_minutes": int(traded.sum()),
    }


def manifest_entry(archive: Path, *, source_url: str, listed_etag: str | None, listed_bytes: int | None,
                   checksum_verified: bool, terms_note: str) -> dict[str, Any]:
    """Provenance record for one acquired raw artifact (the artifact itself stays out of Git)."""
    size = archive.stat().st_size
    return {
        "file": archive.name,
        "bytes": size,
        "sha256": sha256_file(archive),
        "source_url": source_url,
        "listed_etag": listed_etag,
        "listed_bytes_match": None if listed_bytes is None else listed_bytes == size,
        "checksum_verified": checksum_verified,
        "terms_note": terms_note,
    }
