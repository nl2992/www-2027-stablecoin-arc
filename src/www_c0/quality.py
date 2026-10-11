"""Diagnostics for the March 2023 one-minute candle panel.

These functions deliberately do not treat OHLC ranges or no-trade runs as
observed bid/ask spread or executable order-book depth.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EXPECTED_START = pd.Timestamp("2023-03-01T00:00:00Z")
EXPECTED_END = pd.Timestamp("2023-03-21T23:59:00Z")
EXPECTED_ROWS = 30_240
REQUIRED_LEGS = ("bnus_btcusdc_close", "bnus_usdcusd_close", "bnus_btcusd_close")


def parity_wedge_bps(btc_per_quote: Any, quote_usd: Any, btc_usd: Any) -> Any:
    """FX-corrected log BTC parity wedge, in basis points.

    btc_per_quote is quote tokens per BTC; quote_usd is USD per quote token.
    All three legs must refer to the same observation time and valuation venue
    convention before this result can be interpreted as an arbitrage incentive.
    """
    legs = [np.asarray(x, dtype=float) for x in (btc_per_quote, quote_usd, btc_usd)]
    if any(np.any((x <= 0) & np.isfinite(x)) for x in legs):
        raise ValueError("prices and FX rates must be positive")
    return 10_000 * (np.log(legs[0]) + np.log(legs[1]) - np.log(legs[2]))


def require_quote_direction(pair: str, *, base: str, quote: str) -> None:
    """Reject inverse or unrelated currency conventions before conversion."""
    if pair.upper().replace("-", "") != (base + quote).upper():
        raise ValueError(f"expected {base}/{quote}; got {pair}")


def validate_utc_minutes(values: pd.Series) -> pd.DatetimeIndex:
    """Require explicit UTC timestamps, unique and minute aligned."""
    parsed = [pd.Timestamp(value) for value in values]
    if any(value.tzinfo is None or value.utcoffset() is None for value in parsed):
        raise ValueError("timestamps must include an explicit timezone")
    index = pd.DatetimeIndex(parsed).tz_convert("UTC")
    if index.hasnans:
        raise ValueError("timestamps contain null values")
    if index.has_duplicates:
        raise ValueError("duplicate timestamps")
    if not index.is_monotonic_increasing:
        raise ValueError("timestamps are not increasing")
    if any(index != index.floor("min")):
        raise ValueError("timestamps are not minute aligned")
    return index


def age_since_observation_minutes(
    timestamps: pd.DatetimeIndex, observed: pd.Series
) -> list[int | None]:
    """Age since an explicitly observed row; null before the first observation."""
    if len(timestamps) != len(observed):
        raise ValueError("timestamp and observation lengths differ")
    last: pd.Timestamp | None = None
    ages: list[int | None] = []
    for timestamp, is_observed in zip(timestamps, observed, strict=True):
        if bool(is_observed):
            last = timestamp
        ages.append(None if last is None else int((timestamp - last).total_seconds() // 60))
    return ages


def _prefixes(frame: pd.DataFrame) -> list[str]:
    return sorted(column.removesuffix("_close") for column in frame if column.endswith("_close"))


def audit_panel(frame: pd.DataFrame, *, stale_after_minutes: int = 5) -> dict[str, Any]:
    """Audit observed panel coverage; zero-volume age is a proxy, not quote age."""
    if "timestamp_utc" not in frame:
        raise ValueError("missing timestamp_utc")
    timestamps = validate_utc_minutes(frame["timestamp_utc"])
    expected = pd.date_range(EXPECTED_START, EXPECTED_END, freq="1min")
    missing = expected.difference(timestamps)
    unexpected = timestamps.difference(expected)
    pair_stats: dict[str, Any] = {}
    for prefix in _prefixes(frame):
        close = pd.to_numeric(frame[f"{prefix}_close"], errors="coerce")
        invalid = int(((close <= 0) & close.notna()).sum())
        stat: dict[str, Any] = {
            "non_null_close": int(close.notna().sum()),
            "positive_close": int((close > 0).sum()),
            "invalid_nonpositive_close": invalid,
            "first_non_null": None,
            "last_non_null": None,
        }
        valid_positions = np.flatnonzero(close.notna().to_numpy())
        if len(valid_positions):
            stat["first_non_null"] = timestamps[valid_positions[0]].isoformat()
            stat["last_non_null"] = timestamps[valid_positions[-1]].isoformat()
        volume_col = f"{prefix}_volume"
        if volume_col in frame:
            volume = pd.to_numeric(frame[volume_col], errors="coerce")
            observed_trade = volume.gt(0).fillna(False)
            age = age_since_observation_minutes(timestamps, observed_trade)
            finite_age = [value for value in age if value is not None]
            stat.update({
                "positive_volume_minutes": int(observed_trade.sum()),
                "zero_volume_minutes": int(volume.eq(0).sum()),
                "close_present_without_trade_minutes": int((close.notna() & volume.eq(0)).sum()),
                "max_age_since_positive_volume_minutes": max(finite_age, default=None),
                "minutes_over_stale_threshold_by_volume_proxy": sum(
                    value is not None and value > stale_after_minutes for value in age
                ),
            })
        pair_stats[prefix] = stat

    invalid_total = sum(v["invalid_nonpositive_close"] for v in pair_stats.values())
    output: dict[str, Any] = {
        "status": "AUDITED",
        "validation": {
            "timestamp_unique": not timestamps.has_duplicates,
            "timestamp_monotonic": timestamps.is_monotonic_increasing,
            "minute_aligned": bool((timestamps == timestamps.floor("min")).all()),
            "invalid_nonpositive_close_count": invalid_total,
            "invalid_prices_pass": invalid_total == 0,
            "expected_grid_complete": len(missing) == 0 and len(unexpected) == 0,
        },
        "source_kind": "OHLCV candle panel, not historical L2",
        "rows": len(frame),
        "columns": len(frame.columns),
        "expected_rows": EXPECTED_ROWS,
        "first_timestamp": timestamps.min().isoformat() if len(timestamps) else None,
        "last_timestamp": timestamps.max().isoformat() if len(timestamps) else None,
        "missing_expected_minutes": len(missing),
        "unexpected_minutes": len(unexpected),
        "non_minute_gaps": int((np.diff(timestamps.asi8) != 60_000_000_000).sum()),
        "pair_coverage": pair_stats,
        "limitations": [
            "A zero-volume candle with a close is not a contemporaneous executable quote.",
            "The panel lacks bid/ask ladders, quote timestamps and source-row provenance.",
            "Age since positive volume is a trade-activity proxy, not order-book staleness.",
        ],
    }
    if all(leg in frame for leg in REQUIRED_LEGS):
        legs = [pd.to_numeric(frame[leg], errors="coerce").where(lambda x: x > 0) for leg in REQUIRED_LEGS]
        wedge = parity_wedge_bps(*legs)
        valid = np.isfinite(wedge)
        output["fx_corrected_usdc_wedge_bps"] = {
            "finite_minutes": int(valid.sum()),
            "median": float(np.median(wedge[valid])) if valid.any() else None,
            "min": float(np.min(wedge[valid])) if valid.any() else None,
            "max": float(np.max(wedge[valid])) if valid.any() else None,
        }
    return output


def audit_parquet(path: Path, *, stale_after_minutes: int = 5) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "NOT_AVAILABLE", "input": str(path), "reason": "file missing"}
    frame = pd.read_parquet(path)
    result = audit_panel(frame, stale_after_minutes=stale_after_minutes)
    result["input"] = str(path)
    return result
