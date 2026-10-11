"""Unauthenticated Tardis dataset probes; 404 is not an absence verdict."""

from __future__ import annotations

import json
import urllib.parse
import urllib.error
import urllib.request
from datetime import UTC, date, datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Any


BASE = "https://datasets.tardis.dev/v1/binance-us/incremental_book_L2"


def probe_public_csv(symbol: str, day: date, *, timeout_seconds: float = 15) -> dict[str, Any]:
    url = f"{BASE}/{day:%Y/%m/%d}/{symbol}.csv.gz"
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "www-c1-audit/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return {"url": url, "http_status": response.status, "content_length": response.headers.get("Content-Length")}
    except urllib.error.HTTPError as exc:
        return {"url": url, "http_status": exc.code, "error": str(exc.reason)}
    except Exception as exc:  # preserve timeouts and network failures as observations
        return {"url": url, "http_status": None, "error": f"{type(exc).__name__}: {exc}"}


def probe_metadata_api(symbol: str, day: date, *, timeout_seconds: float = 15) -> dict[str, Any]:
    filters = [{"channel": "depth", "symbols": [symbol.lower()]}]
    url = (
        "https://api.tardis.dev/v1/data-feeds/binance-us?from="
        + day.isoformat()
        + "&filters="
        + urllib.parse.quote(json.dumps(filters, separators=(",", ":")), safe="")
        + "&offset=0"
    )
    request = urllib.request.Request(url, headers={"User-Agent": "www-c1-audit/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read(4096).decode("utf-8", errors="replace")
            return {"url": url, "http_status": response.status, "response_excerpt": body}
    except urllib.error.HTTPError as exc:
        body = exc.read(4096).decode("utf-8", errors="replace")
        return {"url": url, "http_status": exc.code, "response_excerpt": body}
    except Exception as exc:
        return {"url": url, "http_status": None, "response_excerpt": f"{type(exc).__name__}: {exc}"}


def fetch_exchange_metadata(*, timeout_seconds: float = 15) -> dict[str, Any]:
    url = "https://api.tardis.dev/v1/exchanges/binance-us"
    request = urllib.request.Request(url, headers={"User-Agent": "www-c1-audit/0.1"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        payload = json.loads(response.read())
    return {"url": url, "http_status": response.status, "payload": payload}


def build_coverage_matrix(symbols: list[str], days: list[date]) -> dict[str, Any]:
    metadata_result = fetch_exchange_metadata()
    metadata = {
        item["id"]: item
        for item in metadata_result["payload"]["datasets"]["symbols"]
    }
    requests = [(symbol, day) for symbol in symbols for day in days]
    with ThreadPoolExecutor(max_workers=6) as executor:
        csv_results = list(executor.map(lambda pair: probe_public_csv(*pair), requests))
        api_results = list(executor.map(lambda pair: probe_metadata_api(*pair), requests))
    by_cell: dict[str, dict[str, Any]] = {}
    for (symbol, day), csv_result, api_result in zip(requests, csv_results, api_results, strict=True):
        instrument = metadata.get(symbol)
        listed = bool(instrument and "incremental_book_L2" in instrument.get("dataTypes", []))
        within_metadata_range = bool(
            instrument
            and date.fromisoformat(instrument["availableSince"][:10]) <= day
            and date.fromisoformat(instrument["availableTo"][:10]) >= day
        )
        by_cell.setdefault(symbol, {})[day.isoformat()] = {
            "status": "VERIFIED_DATA" if csv_result.get("http_status") == 200 else "METADATA_ONLY",
            "access_state": (
                "VERIFIED_DATA" if csv_result.get("http_status") == 200
                else "ACCESS_BLOCKED" if api_result.get("http_status") == 401
                else "NOT_TESTED"
            ),
            "instrument_metadata": {
                "listed": listed,
                "supports_incremental_book_L2": bool(instrument and "incremental_book_L2" in instrument.get("dataTypes", [])),
                "available_since": instrument.get("availableSince") if instrument else None,
                "available_to": instrument.get("availableTo") if instrument else None,
                "date_within_advertised_range": within_metadata_range,
            },
            "unauthenticated_csv_probe": csv_result,
            "unauthenticated_replay_api_probe": api_result,
            "interpretation": (
                "A failed unauthenticated request does not establish that licensed historical data are absent."
                if csv_result.get("http_status") != 200 else "Direct unauthenticated data response observed."
            ),
        }
    return {
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "exchange_metadata_url": metadata_result["url"],
        "exchange_metadata_http_status": metadata_result["http_status"],
        "unauthenticated_access_only": True,
        "cells": by_cell,
    }


def main() -> None:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--symbols", nargs="+", default=["BTCUSD", "BTCUSDC", "USDCUSD", "BTCUSDT", "USDCUSDT", "USDTUSD"])
    parser.add_argument("--dates", nargs="+", default=["2023-03-10", "2023-03-11", "2023-03-12"])
    args = parser.parse_args()
    report = build_coverage_matrix(args.symbols, [date.fromisoformat(value) for value in args.dates])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"COVERAGE_PROBED: {args.output}")


if __name__ == "__main__":
    main()
