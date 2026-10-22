"""Download Upbit/Bithumb hourly KRW candles and FRED DEXKOUS (decision D17) and register them in the acquisition manifest.

    uv run python -m www_kimchi.download            # fetch missing files, then write manifest records
The FRED key is read from the environment or the local .env (FRED_API_KEY); it is never printed, saved or written to the manifest
(URLs are recorded with ``api_key=<redacted>``).
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
UPBIT = REPO / "data" / "raw" / "upbit"
BITHUMB = REPO / "data" / "raw" / "bithumb"
FRED = REPO / "data" / "raw" / "fred"
MANIFEST = REPO / "reports" / "events" / "acquisition_manifest.json"
MARKETS = ("KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-BCH", "KRW-ETC")
START = datetime(2017, 10, 1, tzinfo=timezone.utc)
END = datetime(2024, 1, 1, tzinfo=timezone.utc)
AUTH = ("User authorization 2026-10-22 (decision D17): Upbit (Bithumb only where Upbit lacks the series) public candle API for "
        "KRW-quoted majors and KRW-USDT, and FRED daily KRW/USD (DEXKOUS) with the user's key held in local .env only.")
TERMS = "Public market-data API; provider terms of use apply; raw files are not redistributed in this repository."
SLEEP = 0.25
FIELDS = ["timestamp_utc", "open", "high", "low", "close", "volume", "value_krw"]


def _get(url: str, tries: int = 8) -> bytes:
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "www-paper-research/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and k < tries - 1:
                time.sleep(2.0 * (k + 1))
                continue
            raise RuntimeError(f"HTTP {e.code} from {url.split('?')[0]}") from None
        except (urllib.error.URLError, TimeoutError):
            if k == tries - 1:
                raise RuntimeError(f"network failure for {url.split('?')[0]}") from None
            time.sleep(2.0 * (k + 1))
    raise RuntimeError("unreachable")


def fetch_candles(base: str, market: str, start: datetime, end: datetime) -> list[list]:
    rows: dict[str, list] = {}
    to = end
    while True:
        # Upbit takes an ISO UTC time; Bithumb takes "YYYY-MM-DD HH:MM:SS" read as KST (UTC+9)
        ts = (to + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S") if "bithumb" in base else to.strftime("%Y-%m-%dT%H:%M:%SZ")
        q = urllib.parse.urlencode({"market": market, "count": 200, "to": ts})
        data = json.loads(_get(f"{base}/v1/candles/minutes/60?{q}"))
        time.sleep(SLEEP)
        if not data or not isinstance(data, list):
            break
        for c in data:
            rows[c["candle_date_time_utc"]] = [c["candle_date_time_utc"], c["opening_price"], c["high_price"], c["low_price"],
                                              c["trade_price"], c["candle_acc_trade_volume"], c["candle_acc_trade_price"]]
        oldest = min(datetime.fromisoformat(c["candle_date_time_utc"]).replace(tzinfo=timezone.utc) for c in data)
        if oldest <= start:
            break
        to = oldest
    return sorted((r for r in rows.values() if datetime.fromisoformat(r[0]).replace(tzinfo=timezone.utc) >= start), key=lambda r: r[0])


def write_csv(path: Path, rows: list[list], header: list[str] = FIELDS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def fred_key() -> str:
    key = os.environ.get("FRED_API_KEY")
    if not key:
        for line in (REPO / ".env").read_text().splitlines():
            if line.startswith("FRED_API_KEY="):
                key = line.split("=", 1)[1].strip().strip("'\"")
    if not key:
        raise RuntimeError("FRED_API_KEY not found in environment or .env")
    return key


def fetch_fred() -> list[list]:
    q = urllib.parse.urlencode({"series_id": "DEXKOUS", "api_key": fred_key(), "file_type": "json",
                                "observation_start": "2017-01-01", "observation_end": "2024-01-31"})
    data = json.loads(_get(f"https://api.stlouisfed.org/fred/series/observations?{q}"))
    return [[o["date"], o["value"]] for o in data["observations"]]


def record(path: Path, venue: str, symbol: str, url: str, rows: list[list], first: str, last: str, notes: str) -> dict:
    return {"venue": venue, "symbol": symbol, "month": "2017-10..2023-12", "url": url, "status": "VERIFIED",
            "file": str(path.relative_to(REPO)), "bytes": path.stat().st_size, "sha256": sha256_file(path),
            "hash_kind": "self-recorded at acquisition (provider publishes no checksum)", "rows": len(rows),
            "first_utc": first, "last_utc": last, "terms_note": TERMS, "authorization": AUTH, "for_events": ["KIMCHI"], "notes": notes}


def main() -> None:
    recs = []
    for m in MARKETS:
        p = UPBIT / f"{m}_60m.csv"
        if not p.exists():
            rows = fetch_candles("https://api.upbit.com", m, START, END)
            write_csv(p, rows)
        rows = list(csv.reader(p.open()))[1:]
        recs.append(record(p, "upbit", m, f"https://api.upbit.com/v1/candles/minutes/60?market={m}&count=200&to=<paged>", rows,
                           rows[0][0], rows[-1][0], "Hourly candles, UTC hour start; hours with no trade are absent."))
    p = BITHUMB / "KRW-USDT_60m.csv"
    if not p.exists():
        write_csv(p, fetch_candles("https://api.bithumb.com", "KRW-USDT", datetime(2023, 11, 25, tzinfo=timezone.utc), END))
    rows = list(csv.reader(p.open()))[1:]
    recs.append(record(p, "bithumb", "KRW-USDT", "https://api.bithumb.com/v1/candles/minutes/60?market=KRW-USDT&count=200&to=<paged>",
                       rows, rows[0][0], rows[-1][0], "Used because Upbit KRW-USDT starts 2024-06; Bithumb first month is 2023-12."))
    p = FRED / "DEXKOUS.csv"
    if not p.exists():
        write_csv(p, fetch_fred(), ["date", "DEXKOUS"])
    rows = list(csv.reader(p.open()))[1:]
    recs.append(record(p, "fred", "DEXKOUS", "https://api.stlouisfed.org/fred/series/observations?series_id=DEXKOUS&api_key=<redacted>&"
                       "file_type=json&observation_start=2017-01-01&observation_end=2024-01-31", rows, rows[0][0], rows[-1][0],
                       "Daily KRW per USD, H.10 noon New York buying rate; '.' marks no observation."))
    man = json.loads(MANIFEST.read_text())
    keep = [r for r in man["records"] if r.get("for_events") != ["KIMCHI"]]
    man["records"] = keep + recs
    man["summary"] = {k: sum(r["status"] == k for r in man["records"]) for k in ("VERIFIED", "NOT_AVAILABLE", "CHECKSUM_FAILED")}
    MANIFEST.write_text(json.dumps(man, indent=1) + "\n")
    print(f"{len(recs)} records; manifest now {len(man['records'])}")


if __name__ == "__main__":
    main()
