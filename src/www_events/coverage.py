"""Event × venue × symbol × day coverage matrix from documented public listings.

``LISTED`` means a provider index lists a file for the period; the file was not
downloaded or content-checked. Only ``OBSERVED_LOCAL`` rows rest on acquired data.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .registry import analysis_windows, load_registry, window_days, _parse_date


BINANCE_VISION_LIST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix={prefix}"
S3_NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
COVERAGE_STATUSES = {"OBSERVED_LOCAL", "LISTED", "NOT_LISTED", "UNVERIFIED_SOURCE", "ACCESS_BLOCKED"}


def parse_monthly_kline_listing(xml_text: str, symbol: str, interval: str = "1m") -> dict[str, dict[str, Any]]:
    """Map YYYY-MM -> {key, bytes, etag, last_modified} for monthly kline zip files in an S3 listing."""
    root = ET.fromstring(xml_text)
    if root.findtext("s3:IsTruncated", namespaces=S3_NS) == "true":
        raise ValueError("listing truncated; pagination not implemented")
    pattern = re.compile(rf"/{re.escape(symbol)}-{re.escape(interval)}-(\d{{4}}-\d{{2}})\.zip$")
    out: dict[str, dict[str, Any]] = {}
    for item in root.findall("s3:Contents", S3_NS):
        key = item.findtext("s3:Key", namespaces=S3_NS) or ""
        match = pattern.search(key)
        if match:
            out[match.group(1)] = {
                "key": key,
                "bytes": int(item.findtext("s3:Size", namespaces=S3_NS) or 0),
                "etag": (item.findtext("s3:ETag", namespaces=S3_NS) or "").strip('"'),
                "last_modified": item.findtext("s3:LastModified", namespaces=S3_NS),
            }
    return out


def fetch_binance_vision_listing(symbol: str, interval: str = "1m") -> str:
    """Read the public bucket index (metadata only; no data file is downloaded)."""
    url = BINANCE_VISION_LIST.format(prefix=f"data/spot/monthly/klines/{symbol}/{interval}/")
    with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 - fixed public https host
        return response.read().decode("utf-8")


def coverage_rows(events: Sequence[Mapping[str, Any]],
                  listing_for: Callable[[str], Mapping[str, Mapping[str, Any]]]) -> list[dict[str, Any]]:
    """Expand each event's data candidates to one row per analysis window day."""
    rows: list[dict[str, Any]] = []
    for e in events:
        windows = analysis_windows(_parse_date(e["reported_window_utc"]["start"]),
                                   _parse_date(e["reported_window_utc"]["end"]))
        for cand in e["data_candidates"]:
            listing = listing_for(cand["symbol"]) if cand["source"] == "binance_vision_monthly_klines" else None
            for window_name, window in windows.items():
                for day in window_days(window):
                    row = {"event_id": e["id"], "venue": cand["venue"], "symbol": cand["symbol"],
                           "quote_basis": cand["quote_basis"], "data_type": cand["data_type"],
                           "source": cand["source"], "window": window_name, "day": day}
                    if listing is not None:
                        meta = listing.get(day[:7])
                        row["status"] = "LISTED" if meta else "NOT_LISTED"
                        if meta:
                            row.update(file_key=meta["key"], file_bytes=meta["bytes"], etag=meta["etag"])
                    else:
                        row["status"] = cand.get("status", "UNVERIFIED_SOURCE")
                        if row["status"] == "OBSERVED_LOCAL":
                            first, last = cand["observed_range_utc"]  # required for local observations
                            if not first <= day <= last:
                                row["status"] = "NOT_LISTED"
                    rows.append(row)
    return rows


def summarize(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Per event/symbol/window: count of days by status."""
    out: dict[str, Any] = {}
    for r in rows:
        key = f"{r['event_id']}|{r['venue']}|{r['symbol']}"
        out.setdefault(key, {}).setdefault(r["window"], {}).setdefault(r["status"], 0)
        out[key][r["window"]][r["status"]] += 1
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("configs/event_registry.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/events/coverage_matrix.json"))
    parser.add_argument("--checked-utc", required=True, help="timestamp of the listing check, recorded as provenance")
    args = parser.parse_args()
    events = load_registry(args.registry)
    cache: dict[str, dict[str, Any]] = {}

    def listing_for(symbol: str) -> dict[str, Any]:
        if symbol not in cache:
            cache[symbol] = parse_monthly_kline_listing(fetch_binance_vision_listing(symbol), symbol)
        return cache[symbol]

    rows = coverage_rows(events, listing_for)
    result = {
        "checked_utc": args.checked_utc,
        "listing_endpoint": BINANCE_VISION_LIST,
        "status_meaning": {
            "OBSERVED_LOCAL": "acquired, hashed and audited in this repository",
            "LISTED": "public provider index lists a monthly file covering the day; content not checked",
            "NOT_LISTED": "no file listed (or acquired data does not cover the day)",
            "UNVERIFIED_SOURCE": "venue/source plausible but no listing or acquisition checked",
            "ACCESS_BLOCKED": "requires authentication, payment or authorization not granted",
        },
        "summary": summarize(rows),
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    print(f"WROTE {args.output} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
