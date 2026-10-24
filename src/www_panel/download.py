"""Step 1 of the currency-wedge panel (autoresearch/program_panel.md, decision D19): list, download, verify, register.

    uv run python -m www_panel.download

Binance: data.binance.vision monthly 1h spot klines for {BTC, ETH, USDT} against each pre-registered F, up to 2025-09, each archive
verified against its published .CHECKSUM. Upbit/Bithumb: public 60-minute KRW candles 2023-12..2025-09 (www_kimchi.download patterns).
Raw files go to data/raw/panel (git-ignored); records are appended to reports/events/acquisition_manifest.json (existing records kept).
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from www_events.acquire import _fetch  # noqa: E402
from www_events.binance_klines import manifest_entry, verify_checksum  # noqa: E402
from www_kimchi.download import fetch_candles, sha256_file, write_csv, _get  # noqa: E402

RAW = REPO / "data" / "raw" / "panel"
MANIFEST = REPO / "reports" / "events" / "acquisition_manifest.json"
FIATS = ("NGN", "TRY", "ARS", "BRL", "RUB", "UAH", "ZAR", "EUR", "GBP", "AUD")
BASES = ("BTC", "ETH", "USDT")
LAST_MONTH = "2025-09"
LIST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?prefix=data/spot/monthly/klines/{sym}/1h/&delimiter=/"
URL = "https://data.binance.vision/data/spot/monthly/klines/{sym}/1h/{sym}-1h-{month}.zip"
AUTH = ("User authorization 2026-10-24 (decision D19): Binance public monthly 1h spot klines (data.binance.vision) for "
        "{BTC,ETH,USDT} against NGN, TRY, ARS, BRL, RUB, UAH, ZAR, EUR, GBP, AUD up to 2025-09, and Upbit/Bithumb public "
        "60-minute KRW candles for BTC, ETH, USDT 2023-12..2025-09; no other sources.")
TERMS = ("Public market-data archive downloaded with user authorization (2026-10-24, D19); provider terms of use apply; "
         "raw files are not redistributed in this repository.")
KRW_START = datetime(2023, 12, 1, tzinfo=timezone.utc)
KRW_END = datetime(2025, 10, 1, tzinfo=timezone.utc)


def list_months(sym: str) -> list[str]:
    xml = _get(LIST.format(sym=sym)).decode()
    return sorted(m for m in re.findall(rf"{sym}-1h-(\d{{4}}-\d{{2}})\.zip</Key>", xml) if m <= LAST_MONTH)


def binance_records() -> list[dict]:
    recs = []
    for fiat in FIATS:
        for base in BASES:
            sym = base + fiat
            months = list_months(sym)
            if not months:
                recs.append({"venue": "binance-panel", "symbol": sym, "month": f"..{LAST_MONTH}",
                             "url": LIST.format(sym=sym), "status": "NOT_AVAILABLE",
                             "notes": "no 1h monthly klines listed in the data.binance.vision bucket", "for_events": ["PANEL"],
                             "authorization": AUTH})
                continue
            if fiat in ("EUR", "GBP", "AUD"):  # no USDT/F market: the pre-registered market set is empty, nothing is analysed
                pass
            for month in months:
                if any(len(list_months_cache.get(f"{b}{fiat}", [1])) == 0 for b in BASES):
                    continue
                recs.append(acquire(sym, month))
    return recs


list_months_cache: dict[str, list[str]] = {}


def acquire(sym: str, month: str) -> dict:
    d = RAW / "binance" / sym
    d.mkdir(parents=True, exist_ok=True)
    url = URL.format(sym=sym, month=month)
    archive = d / url.rsplit("/", 1)[1]
    checksum = archive.with_name(archive.name + ".CHECKSUM")
    rec = {"venue": "binance-panel", "symbol": sym, "month": month, "url": url, "for_events": ["PANEL"], "authorization": AUTH}
    try:
        if not checksum.exists():
            _fetch(url + ".CHECKSUM", checksum)
        if not archive.exists():
            _fetch(url, archive)
        verify_checksum(archive, checksum)
    except urllib.error.HTTPError as exc:
        rec.update(status="NOT_AVAILABLE", http_status=exc.code)
        return rec
    except ValueError as exc:
        archive.unlink(missing_ok=True)
        rec.update(status="CHECKSUM_FAILED", error=str(exc))
        return rec
    rec.update(status="VERIFIED", **manifest_entry(archive, source_url=url, listed_etag=None, listed_bytes=None,
                                                   checksum_verified=True, terms_note=TERMS))
    rec["file"] = str(archive.relative_to(REPO))
    return rec


def krw_records() -> list[dict]:
    recs = []
    for venue, base in (("upbit", "https://api.upbit.com"), ("bithumb", "https://api.bithumb.com")):
        for m in ("KRW-BTC", "KRW-ETH", "KRW-USDT"):
            p = RAW / venue / f"{m}_60m.csv"
            if not p.exists():
                write_csv(p, fetch_candles(base, m, KRW_START, KRW_END))
            lines = p.read_text().splitlines()[1:]
            rec = {"venue": f"{venue}-panel", "symbol": m, "month": "2023-12..2025-09",
                   "url": f"{base}/v1/candles/minutes/60?market={m}&count=200&to=<paged>", "for_events": ["PANEL"],
                   "authorization": AUTH, "terms_note": TERMS}
            if not lines:
                rec.update(status="NOT_AVAILABLE", notes="API returned no candles in the window")
            else:
                rec.update(status="VERIFIED", file=str(p.relative_to(REPO)), bytes=p.stat().st_size, sha256=sha256_file(p),
                           hash_kind="self-recorded at acquisition (provider publishes no checksum)", rows=len(lines),
                           first_utc=lines[0].split(",")[0], last_utc=lines[-1].split(",")[0])
            recs.append(rec)
    return recs


def main() -> None:
    for fiat in FIATS:
        for base in BASES:
            list_months_cache[base + fiat] = list_months(base + fiat)
    recs = binance_records() + krw_records()
    man = json.loads(MANIFEST.read_text())
    n0 = len(man["records"])
    man["records"] = [r for r in man["records"] if r.get("for_events") != ["PANEL"]] + recs
    assert len(man["records"]) == n0 + len(recs) or n0 == len(man["records"]) - len(recs), "existing records changed"
    man["summary"] = {k: sum(r["status"] == k for r in man["records"]) for k in ("VERIFIED", "NOT_AVAILABLE", "CHECKSUM_FAILED")}
    MANIFEST.write_text(json.dumps(man, indent=1) + "\n")
    print(f"before {n0}, added {len(recs)}, after {len(man['records'])}")


if __name__ == "__main__":
    main()
