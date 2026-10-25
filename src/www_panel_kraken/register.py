"""Append the D21 Kraken fiat-pair records (the joined archive and 18 extracted 60-minute files) to the acquisition manifest.

    uv run python -m www_panel_kraken.register

Idempotent: records with venue ``kraken-ohlcvt-panel`` are replaced, all other records are kept untouched.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from .data import BASES, FIATS, KRAKEN, REPO

MANIFEST = REPO / "reports" / "events" / "acquisition_manifest.json"
VENUE = "kraken-ohlcvt-panel"
URL = "https://assets.kraken.com/marketing/institutions/Kraken_OHLCVT_Full.zip.part00..part04"
ARCHIVE_SHA256 = "bc273e9027470b07d790a7fa4df9bb43f0dfc527c20c6ecae48402e123e7b1c7"
ARCHIVE_BYTES = 9546553626
AUTH = ("User authorization 2026-10-25 (decision D21): re-download Kraken's free OHLCVT bundle from assets.kraken.com, linked from "
        "Kraken's support page, and extract XBT, ETH and USDT at 60 minutes quoted in EUR, GBP, CAD, AUD, CHF and JPY; no paid or "
        "authenticated access.")
TERMS = "Public bulk download linked from Kraken's support page; provider terms of use apply; raw files are not redistributed in this repository."


def main() -> int:
    m = json.loads(MANIFEST.read_text())
    keep = [r for r in m["records"] if r["venue"] != VENUE]
    new = [{"venue": VENUE, "symbol": "Kraken_OHLCVT_Full.zip", "month": "full history", "url": URL, "status": "VERIFIED",
            "file": "(deleted after extraction)", "bytes": ARCHIVE_BYTES, "sha256": ARCHIVE_SHA256,
            "hash_kind": "published by Kraken on its support page for the joined five-part archive; re-downloaded and verified (D21)",
            "note": "parts joined by streaming append with each part deleted after appending; archive deleted after extracting the 18 fiat-pair files below",
            "terms_note": TERMS, "authorization": AUTH}]
    for fiat in FIATS:
        for base in BASES:
            f = KRAKEN / f"{base}{fiat}_60.csv"
            raw = f.read_bytes()
            x = pd.read_csv(f, header=None, usecols=[0])[0]
            new.append({"venue": VENUE, "symbol": f"{base}{fiat}", "interval": 60, "month": "full history", "url": URL,
                        "status": "VERIFIED", "file": f"data/raw/kraken_ohlcvt/{f.name}", "bytes": len(raw),
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "hash_kind": "self-recorded after extraction from the checksum-verified archive", "rows": int(len(x)),
                        "first_utc": pd.Timestamp(int(x.min()), unit="s").strftime("%Y-%m-%dT%H:%MZ"),
                        "last_utc": pd.Timestamp(int(x.max()), unit="s").strftime("%Y-%m-%dT%H:%MZ"),
                        "terms_note": TERMS, "authorization": AUTH})
    m["records"] = keep + new
    m["summary"] = {s: sum(r["status"] == s for r in m["records"]) for s in ("VERIFIED", "NOT_AVAILABLE", "CHECKSUM_FAILED")}
    MANIFEST.write_text(json.dumps(m, indent=1) + "\n")
    print(f"records {len(keep)} -> {len(m['records'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
