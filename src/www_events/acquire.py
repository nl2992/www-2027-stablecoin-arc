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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--plan", type=Path, default=Path("configs/acquisition_plan.json"))
    parser.add_argument("--manifest", type=Path, default=Path("reports/events/acquisition_manifest.json"))
    args = parser.parse_args()
    plan = json.loads((args.root / args.plan).read_text())
    records = []
    for item in plan["items"]:
        for month in item["months"]:
            for symbol in item["symbols"]:
                rec = acquire(args.root, item["venue"], symbol, month)
                rec["for_events"] = item["events"]
                records.append(rec)
                print(f"{rec['status']:16} {item['venue']:10} {symbol:10} {month}")
    out = {"authorized": plan["authorized"], "records": records,
           "summary": {s: sum(r["status"] == s for r in records) for s in ("VERIFIED", "NOT_AVAILABLE", "CHECKSUM_FAILED")}}
    (args.root / args.manifest).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["summary"]))


if __name__ == "__main__":
    main()
