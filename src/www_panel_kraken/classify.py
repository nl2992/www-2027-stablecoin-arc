"""Step 2: hourly L, the 80% coverage rule and the stress/calm classification from L alone (autoresearch/program_panel_kraken.md).

    uv run python -m www_panel_kraken.classify      # writes reports/panel_kraken/months.json

L = 1e4 [log P_Kraken(XBT/F) - log P_Bitstamp(BTC/USD)]. Coverage: a full month is kept only if XBT/F, ETH/F and USDT/F each traded in at
least 80% of the month's hours (volume indicator only for ETH/F and USDT/F). Stress iff the median over the month's hours of
|L - median_month(L)| >= 25 bps. D and X are not loaded.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .data import (BASES, FIRST_MONTH, LAST_MONTH, available_fiats, gap, month_hours, months_between, read_bitstamp_usd, read_close,
                   read_volume)

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "panel_kraken" / "months.json"
COVERAGE_MIN = 0.80
STRESS_BPS = 25.0


def traded_by_month(vol: pd.Series) -> dict[str, int]:
    return {str(k): int(v) for k, v in vol.groupby(vol.index.tz_localize(None).to_period("M")).size().items()}


def classify() -> dict:
    ref = read_bitstamp_usd("BTCUSD")
    out = {"rule": {"coverage_min": COVERAGE_MIN, "stress_bps": STRESS_BPS, "first_month": FIRST_MONTH, "last_month": LAST_MONTH,
                    "stress": "median over the month's hours of |L - median_month(L)| >= 25 bps; L only, never D"},
           "units": {}}
    for fiat in available_fiats():
        L = gap(read_close("XBT", fiat), ref)
        tr = {b: traded_by_month(read_volume(b, fiat)) for b in BASES}
        months = {}
        for m in months_between(FIRST_MONTH, LAST_MONTH):
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
        out["units"][fiat] = {"fiat": fiat, "months": months,
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
