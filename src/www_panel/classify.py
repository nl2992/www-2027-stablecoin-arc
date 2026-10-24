"""Step 2: hourly L and L2, the 80% coverage rule and the stress/calm classification, from L alone.

    uv run python -m www_panel.classify      # writes reports/panel/months.json

L_v(t)  = 1e4 [log P_v(BTC/F)  - log P_Kraken(BTC/USD)]
L2_v(t) = 1e4 [log P_v(ETH/F)  - log P_Kraken(ETH/USD)]
Coverage: a full calendar month is kept only if each of BTC/F, ETH/F and USDT/F traded (positive volume, row present) in at least 80%
of the month's hours; for USDT/F only the traded-hour indicator is read here (the price column is discarded on load; no USDT/F or
Kraken USDT/USD price enters this step). A month is stress if the median over its hours of |L - median_month(L)| is >= 25 bps.
D and X are not loaded.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .data import (LAST_MONTH, UNITS, log_bps, month_hours, months_between, read_kraken, read_pair, unit_key)

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "panel" / "months.json"
COVERAGE_MIN = 0.80
STRESS_BPS = 25.0


def gap(venue: str, fiat: str, base: str, kraken: pd.Series) -> pd.Series:
    """Venue-minus-Kraken log gap in bps on the hours both exist."""
    px = read_pair(venue, fiat, base)
    px = px["close"][px["volume"] > 0]
    j = pd.concat([px.rename("v"), kraken.rename("k")], axis=1, join="inner")
    return log_bps(j["v"]) - log_bps(j["k"])


def traded_by_month(venue: str, fiat: str, base: str) -> dict[str, int]:
    vol = read_pair(venue, fiat, base, volume_only=True)["volume"]
    vol = vol[vol > 0]
    return {str(k): int(v) for k, v in vol.groupby(vol.index.tz_convert("UTC").tz_localize(None).to_period("M")).size().items()}


def classify() -> dict:
    kb, ke = read_kraken("XBTUSD"), read_kraken("ETHUSD")
    out = {"rule": {"coverage_min": COVERAGE_MIN, "stress_bps": STRESS_BPS, "last_month": LAST_MONTH,
                    "stress": "median over the month's hours of |L - median_month(L)| >= 25 bps; L only, never D"},
           "units": {}}
    for venue, fiat in UNITS:
        L = gap(venue, fiat, "BTC", kb)
        tr = {b: traded_by_month(venue, fiat, b) for b in ("BTC", "ETH", "USDT")}
        months = {}
        for m in months_between(L.index.min().strftime("%Y-%m"), LAST_MONTH):
            n = month_hours(m)
            cov = {b: tr[b].get(m, 0) / n for b in tr}
            row = {"hours": n, "coverage": {b: round(c, 4) for b, c in cov.items()}}
            if min(cov.values()) < COVERAGE_MIN:
                row["status"] = "excluded_coverage"
            else:
                t0 = pd.Timestamp(m + "-01", tz="UTC")
                Lm = L[(L.index >= t0) & (L.index < t0 + pd.offsets.MonthBegin(1))]
                if len(Lm) == 0:
                    row["status"] = "excluded_no_L"
                else:
                    stat = float(np.median(np.abs(Lm - np.median(Lm))))
                    row.update(L_hours=int(len(Lm)), stress_stat_bps=round(stat, 4), status="stress" if stat >= STRESS_BPS else "calm")
            months[m] = row
        out["units"][unit_key(venue, fiat)] = {"venue": venue, "fiat": fiat, "months": months,
                                               "counts": {s: sum(r["status"] == s for r in months.values())
                                                          for s in ("stress", "calm", "excluded_coverage", "excluded_no_L")}}
    return out


def main() -> None:
    res = classify()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    for k, u in res["units"].items():
        print(k, u["counts"])


if __name__ == "__main__":
    main()
