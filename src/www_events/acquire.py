"""Download authorized public kline archives and record a provenance manifest.

Authorized by the user on 2026-10-11 for Binance.com (data.binance.vision) and
Binance.US (data.binance.us) public spot klines only. No paid or authenticated
source is touched. Every archive is verified against its published .CHECKSUM
before it is kept; raw files go to git-ignored directories and only the
manifest (names, sizes, hashes, URLs) is committed.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .binance_klines import manifest_entry, verify_checksum

SOURCES = {
    "binance": {"base": "https://data.binance.vision/data/spot/monthly/klines", "dir": "data/raw/binance"},
    "binance-us": {"base": "https://data.binance.us/public_data/spot/monthly/klines", "dir": "data/raw/binance_us"},
}
TERMS_NOTE = ("Public market-data archive downloaded with user authorization (2026-10-11); provider terms of use "
              "apply; raw files are not redistributed in this repository.")


def archive_url(venue: str, symbol: str, month: str, interval: str = "1m") -> str:
    return f"{SOURCES[venue]['base']}/{symbol}/{interval}/{symbol}-{interval}-{month}.zip"


def _fetch(url: str, dest: Path, *, retries: int = 3) -> None:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310 - fixed public https hosts
                dest.write_bytes(response.read())
            return
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))


def acquire(root: Path, venue: str, symbol: str, month: str) -> dict[str, Any]:
    directory = root / SOURCES[venue]["dir"]
    directory.mkdir(parents=True, exist_ok=True)
    url = archive_url(venue, symbol, month)
    archive = directory / url.rsplit("/", 1)[1]
    checksum = archive.with_name(archive.name + ".CHECKSUM")
    record: dict[str, Any] = {"venue": venue, "symbol": symbol, "month": month, "url": url}
    try:
        if not checksum.exists():
            _fetch(url + ".CHECKSUM", checksum)
        if not archive.exists():
            _fetch(url, archive)
        verify_checksum(archive, checksum)
    except urllib.error.HTTPError as exc:
        record.update(status="NOT_AVAILABLE", http_status=exc.code)
        return record
    except ValueError as exc:  # checksum mismatch: never keep an unverified archive
        archive.unlink(missing_ok=True)
        record.update(status="CHECKSUM_FAILED", error=str(exc))
        return record
    record.update(status="VERIFIED", **manifest_entry(archive, source_url=url, listed_etag=None, listed_bytes=None,
                                                      checksum_verified=True, terms_note=TERMS_NOTE))
    record["file"] = str(archive.relative_to(root))
    return record


def acquire_bitstamp(root: Path, pair: str, month: str) -> dict[str, Any]:
    from .bitstamp import ENDPOINT, fetch_month, save_month
    path = root / "data/raw/bitstamp" / f"{pair.upper()}-1m-{month}.csv"
    record: dict[str, Any] = {"venue": "bitstamp", "symbol": pair.upper(), "month": month,
                              "url": ENDPOINT.format(pair=pair.lower(), start="<paged>")}
    try:
        frame, pages = fetch_month(pair, month)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        record.update(status="NOT_AVAILABLE", error=f"{type(exc).__name__}: {exc}")
        return record
    if frame.empty:
        record.update(status="NOT_AVAILABLE", error="no bars returned")
        return record
    digest = save_month(frame, path)
    record.update(status="VERIFIED", file=str(path.relative_to(root)), bytes=path.stat().st_size, sha256=digest,
                  hash_kind="self-recorded at acquisition (provider publishes no checksum)", pages=pages,
                  rows=len(frame), traded_minutes=int((frame["volume"] > 0).sum()),
                  first_utc=pd_ts(frame["timestamp"].iloc[0]), last_utc=pd_ts(frame["timestamp"].iloc[-1]),
                  terms_note=TERMS_NOTE)
    return record


CANDLE_DIRS = {"bitfinex": "data/raw/bitfinex", "coinbase": "data/raw/coinbase"}
CANDLE_NOTE = ("Public market-data endpoint downloaded with user authorization (2026-10-18); provider terms of use "
               "apply; raw files are not redistributed in this repository.")


def acquire_candles(root: Path, venue: str, symbol: str, month: str) -> dict[str, Any]:
    """Bitfinex or Coinbase public 1-minute candles for one month, saved with a self-recorded SHA-256."""
    from .bitstamp import save_month
    from .candles import BITFINEX, COINBASE, fetch_bitfinex_month, fetch_coinbase_month
    fetch, url = ((fetch_bitfinex_month, BITFINEX.format(pair=symbol.upper(), start="<paged>", end="<month end>"))
                  if venue == "bitfinex" else
                  (fetch_coinbase_month, COINBASE.format(product=symbol.upper(), start="<paged>", end="<paged>")))
    name = symbol.upper().replace("-", "")
    path = root / CANDLE_DIRS[venue] / f"{name}-1m-{month}.csv"
    record: dict[str, Any] = {"venue": venue, "symbol": name, "month": month, "url": url}
    try:
        frame, pages = fetch(symbol, month)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        record.update(status="NOT_AVAILABLE", error=f"{type(exc).__name__}: {exc}")
        return record
    if frame.empty:
        record.update(status="NOT_AVAILABLE", error="no bars returned")
        return record
    digest = save_month(frame, path)
    record.update(status="VERIFIED", file=str(path.relative_to(root)), bytes=path.stat().st_size, sha256=digest,
                  hash_kind="self-recorded at acquisition (provider publishes no checksum)", pages=pages,
                  rows=len(frame), traded_minutes=int((frame["volume"] > 0).sum()),
                  first_utc=pd_ts(frame["timestamp"].iloc[0]), last_utc=pd_ts(frame["timestamp"].iloc[-1]),
                  terms_note=CANDLE_NOTE)
    return record


TARDIS = "https://datasets.tardis.dev/v1/{exchange}/{dtype}/{y}/{m}/{d}/{symbol}.csv.gz"
TARDIS_MAX_BYTES = 300 * 1024 * 1024
TARDIS_NOTE = ("Tardis free first-of-month sample (documented: 'available to download without API key'); downloaded "
               "with reviewer approval for normal-market comparison only; licence page not located; raw files are "
               "not redistributed.")


def acquire_tardis(root: Path, exchange: str, dtype: str, date: str, symbol: str) -> dict[str, Any]:
    """Bounded download of one free first-of-month file; refuses non-first days and files over the size cap."""
    import hashlib
    y, m, d = date.split("-")
    record: dict[str, Any] = {"venue": f"tardis:{exchange}", "symbol": symbol, "month": date, "data_type": dtype,
                              "url": TARDIS.format(exchange=exchange, dtype=dtype, y=y, m=m, d=d, symbol=symbol)}
    if d != "01":
        record.update(status="NOT_AVAILABLE", error="only first-of-month files are free")
        return record
    path = root / "data/raw/tardis" / f"{exchange}_{dtype}_{date}_{symbol}.csv.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        req = urllib.request.Request(record["url"], headers={"User-Agent": "www-stablecoin-research/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=120) as response:  # noqa: S310 - fixed public https host
                data = response.read(TARDIS_MAX_BYTES + 1)
        except urllib.error.HTTPError as exc:
            record.update(status="NOT_AVAILABLE", http_status=exc.code)
            return record
        if len(data) > TARDIS_MAX_BYTES:
            record.update(status="NOT_AVAILABLE", error="exceeds bounded size cap; not stored")
            return record
        path.write_bytes(data)
    record.update(status="VERIFIED", file=str(path.relative_to(root)), bytes=path.stat().st_size,
                  sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  hash_kind="self-recorded at acquisition (provider publishes no checksum)", terms_note=TARDIS_NOTE)
    return record


def pd_ts(seconds: int) -> str:
    import datetime as _dt
    return _dt.datetime.fromtimestamp(int(seconds), _dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--plan", type=Path, default=Path("configs/acquisition_plan.json"))
    parser.add_argument("--manifest", type=Path, default=Path("reports/events/acquisition_manifest.json"))
    args = parser.parse_args()
    plan = json.loads((args.root / args.plan).read_text())
    manifest_path = args.root / args.manifest
    previous = json.loads(manifest_path.read_text())["records"] if manifest_path.is_file() else []
    records = []
    done = {(r["venue"], r["symbol"], r["month"]) for r in previous if r["status"] == "VERIFIED"}
    for item in plan["items"]:
        for month in item["months"]:
            for symbol in item["symbols"]:
                if item["venue"].startswith("tardis:"):
                    if (item["venue"], symbol, month) in done:
                        continue
                    rec = acquire_tardis(args.root, item["venue"].split(":", 1)[1], item["data_type"], month, symbol)
                elif item["venue"] == "bitstamp":
                    if ("bitstamp", symbol.upper(), month) in done:
                        continue  # never re-page an already verified month; keeps recorded hashes stable
                    rec = acquire_bitstamp(args.root, symbol, month)
                elif item["venue"] in CANDLE_DIRS:
                    if (item["venue"], symbol.upper().replace("-", ""), month) in done:
                        continue
                    rec = acquire_candles(args.root, item["venue"], symbol, month)
                else:
                    rec = acquire(args.root, item["venue"], symbol, month)
                rec["for_events"] = item["events"]
                records.append(rec)
                print(f"{rec['status']:16} {item['venue']:10} {symbol:10} {month}")
    kept = [r for r in previous if (r["venue"], r["symbol"], r["month"]) not in
            {(x["venue"], x["symbol"], x["month"]) for x in records}]
    records = kept + records
    out = {"authorized": plan["authorized"], "records": records,
           "summary": {s: sum(r["status"] == s for r in records) for s in ("VERIFIED", "NOT_AVAILABLE", "CHECKSUM_FAILED")}}
    (args.root / args.manifest).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["summary"]))


if __name__ == "__main__":
    main()
