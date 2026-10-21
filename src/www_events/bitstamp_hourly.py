"""Bitstamp public HOURLY OHLC adapter (decision D14; unauthenticated public endpoint, one CSV per pair).

Pages ``/api/v2/ohlc/{pair}/?step=3600&limit=1000&start=...`` ascending, at least one second between calls, writes
``data/raw/bitstamp_1h/{PAIR}-1h-2017-2023.csv`` and records a self-recorded SHA-256 in the acquisition manifest under
venue ``bitstamp-1h``; existing manifest records are never dropped.
"""

from __future__ import annotations

import json
import time
import urllib.error
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

from .acquire import merge_records, pd_ts
from .bitstamp import COLUMNS, _get, month_bounds, save_month

ENDPOINT_1H = "https://www.bitstamp.net/api/v2/ohlc/{pair}/?step=3600&limit=1000&start={start}"
VENUE = "bitstamp-1h"
PAIRS = ("ltcusd", "xrpusd", "xlmusd", "linkusd", "bchusd")
NOTE = ("Public market-data endpoint downloaded with user authorization (decision D14, 2026-10-20); provider "
        "terms of use apply; raw files are not redistributed in this repository.")
HOUR = 3600


def fetch_bitstamp_hourly(pair: str, first_month: str, last_month: str, *, get: Callable[[str], dict[str, Any]] = _get,
                          pause: float = 1.0) -> tuple[pd.DataFrame, int]:
    """All hourly bars with first_month start <= t < end of last_month (1,000 per page, ascending)."""
    lo, hi = month_bounds(first_month)[0], month_bounds(last_month)[1]
    rows: dict[int, dict[str, str]] = {}
    cursor, pages = lo, 0
    while cursor < hi:
        payload = get(ENDPOINT_1H.format(pair=pair.lower(), start=cursor))
        pages += 1
        bars = payload.get("data", {}).get("ohlc", [])
        if not bars:  # before the pair's history (the provider does not jump forward): probe one page later
            cursor += 1000 * HOUR
            if pause:
                time.sleep(pause)
            continue
        for bar in bars:
            t = int(bar["timestamp"])
            if lo <= t < hi:
                rows[t] = bar
        last = int(bars[-1]["timestamp"])
        if last < cursor:
            raise ValueError("provider returned bars out of order")
        cursor = last + HOUR
        if pause:
            time.sleep(pause)
    frame = pd.DataFrame([rows[t] for t in sorted(rows)], columns=COLUMNS)
    return frame.astype({"timestamp": "int64", **{c: "float64" for c in COLUMNS[1:]}}), pages


def acquire_bitstamp_hourly(root: Path, pair: str, first: str = "2017-01", last: str = "2023-12",
                            fetch: Callable[..., tuple[pd.DataFrame, int]] = fetch_bitstamp_hourly) -> dict[str, Any]:
    name = pair.upper()
    path = root / "data" / "raw" / "bitstamp_1h" / f"{name}-1h-{first[:4]}-{last[:4]}.csv"
    record: dict[str, Any] = {"venue": VENUE, "symbol": name, "month": f"{first}..{last}",
                              "url": ENDPOINT_1H.format(pair=pair.lower(), start="<paged>"), "provider_symbol": pair.lower()}
    try:
        frame, pages = fetch(pair, first, last)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        record.update(status="NOT_AVAILABLE", error=f"{type(exc).__name__}: {exc}")
        return record
    if frame.empty:
        record.update(status="NOT_AVAILABLE", error="no bars returned")
        return record
    digest = save_month(frame, path)
    record.update(status="VERIFIED", file=str(path.relative_to(root)), bytes=path.stat().st_size, sha256=digest,
                  hash_kind="self-recorded at acquisition (provider publishes no checksum)", pages=pages,
                  rows=len(frame), traded_hours=int((frame["volume"] > 0).sum()),
                  first_utc=pd_ts(frame["timestamp"].iloc[0]), last_utc=pd_ts(frame["timestamp"].iloc[-1]), terms_note=NOTE)
    return record


def main(root: Path = Path("."), manifest: Path = Path("reports/events/acquisition_manifest.json"),
         pairs: tuple[str, ...] = PAIRS) -> None:
    path = root / manifest
    data = json.loads(path.read_text())
    new = []
    for pair in pairs:
        rec = acquire_bitstamp_hourly(root, pair)
        new.append(rec)
        print(f"{rec['status']:14} {pair:8} {rec.get('rows', '')} {rec.get('first_utc', '')} {rec.get('last_utc', '')} "
              f"{rec.get('error', '')}", flush=True)
    data["records"] = merge_records(data["records"], new)
    data["summary"] = {s: sum(r["status"] == s for r in data["records"])
                       for s in ("VERIFIED", "NOT_AVAILABLE", "CHECKSUM_FAILED")}
    path.write_text(json.dumps(data, indent=1) + "\n")


if __name__ == "__main__":
    main()
