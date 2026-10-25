"""Step 1 (decision D20): download the ECB euro reference-rate history once and register it in the acquisition manifest.

    uv run python -m www_panel_fusion.download

The raw file goes to data/raw/ecb (git-ignored). One record is appended to reports/events/acquisition_manifest.json; existing records are kept.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from www_kimchi.download import sha256_file  # noqa: E402

URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip"
DEST = REPO / "data" / "raw" / "ecb" / "eurofxref-hist.zip"
MANIFEST = REPO / "reports" / "events" / "acquisition_manifest.json"
AUTH = ("User authorization 2026-10-25 (decision D20): the single public ECB euro foreign exchange reference rates history "
        "file eurofxref-hist.zip from ecb.europa.eu; nothing else new.")


def main() -> None:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if not DEST.exists():
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
        DEST.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    rec = {"venue": "ecb-reference-rates", "symbol": "eurofxref-hist", "month": "1999-01..2026-10", "url": URL, "for_events": ["PANEL_FUSION"],
           "authorization": AUTH, "terms_note": "Public ECB statistical data; ECB reuse terms apply; the raw file is not redistributed in this repository.",
           "status": "VERIFIED", "file": str(DEST.relative_to(REPO)), "bytes": DEST.stat().st_size, "sha256": sha256_file(DEST),
           "hash_kind": "self-recorded at acquisition (provider publishes no checksum)"}
    man = json.loads(MANIFEST.read_text())
    n0 = len(man["records"])
    man["records"] = [r for r in man["records"] if r.get("for_events") != ["PANEL_FUSION"]] + [rec]
    assert len(man["records"]) == n0 + 1, "existing records changed"
    man["summary"] = {k: sum(r["status"] == k for r in man["records"]) for k in ("VERIFIED", "NOT_AVAILABLE", "CHECKSUM_FAILED")}
    MANIFEST.write_text(json.dumps(man, indent=1) + "\n")
    print(f"before {n0}, after {len(man['records'])}, sha256 {rec['sha256']}")


if __name__ == "__main__":
    main()
