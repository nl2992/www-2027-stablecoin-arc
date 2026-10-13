"""Hourly token/ledger failure monitor on Binance.US, evaluated over every month with overlapping data.

Rule (fixed before running; threshold = the pre-registered R1 severity level, 100 bps):
  ledger flag  : |L| >= 100 and |PD_USDT - L| <= 0.25 |L|      (unit moved, and two assets agree)
  token flag(q): |T_q| >= 100                                     (coin moved in external dollars)
where L = PD_BTC (venue BTC/USD vs Bitstamp BTC/USD), T_q = D_q - L, hourly medians of traded minutes.
Periods are labelled from documented dates only, so flag rates can be read as specificity in calm months.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from www_events.bitstamp import load_months
from www_events.runner import load_binance_months

from .platform_dollar import dislocation, traded_log_close

THRESHOLD = 100.0
AGREE = 0.25
PERIODS = [  # (label, start, end) -- documented events; everything else in covered months is "calm"
    ("ftx_collapse", "2022-11-06", "2022-11-21"),
    ("svb_run", "2023-03-10", "2023-03-14"),
    ("binanceus_rail_cut", "2023-06-05", "2023-08-01"),
]


def classify(hourly: pd.DataFrame) -> pd.DataFrame:
    """hourly has columns L, PD_USDT and T_<coin>; adds boolean flag columns."""
    out = hourly.copy()
    out["ledger_flag"] = (out["L"].abs() >= THRESHOLD) & ((out["PD_USDT"] - out["L"]).abs() <= AGREE * out["L"].abs())
    for c in [c for c in out.columns if c.startswith("T_")]:
        out[f"token_flag_{c[2:]}"] = out[c].abs() >= THRESHOLD
    return out


def label(index: pd.DatetimeIndex) -> np.ndarray:
    lab = np.full(len(index), "calm", dtype=object)
    for name, start, end in PERIODS:
        lab[(index >= pd.Timestamp(start, tz="UTC")) & (index < pd.Timestamp(end, tz="UTC"))] = name
    return lab


def summarize(flags: pd.DataFrame) -> dict[str, Any]:
    flags = flags.assign(period=label(flags.index))
    cols = [c for c in flags.columns if c.endswith("_flag") or "_flag_" in c]
    out = {}
    for period, g in flags.groupby("period"):
        row: dict[str, Any] = {"hours": int(len(g))}
        for c in cols:
            v = g[c].dropna()
            row[c] = {"hours_evaluated": int(len(v)), "flag_share": float(v.mean()) if len(v) else None}
        out[period] = row
    return out


def run(binance_us: Path, bitstamp: Path, manifest: Path) -> dict[str, Any]:
    def bus(sym: str) -> pd.Series:
        return traded_log_close(load_binance_months(binance_us, sym, "x")[0], "x")

    def bst(pair: str) -> pd.Series:
        return traded_log_close(load_months(bitstamp, pair, "y", manifest)[0], "y")

    L = dislocation(bus("BTCUSD"), bst("BTCUSD")).resample("1h").median()
    pd_usdt = dislocation(bus("USDTUSD"), bst("USDTUSD")).resample("1h").median()
    hourly = pd.DataFrame({"L": L, "PD_USDT": pd_usdt})
    for coin in ("USDT", "USDC"):
        d = (1e4 * bus(f"{coin}USD")).resample("1h").median()
        hourly[f"T_{coin}"] = d - hourly["L"]
    hourly = hourly.dropna(subset=["L", "PD_USDT"])
    flags = classify(hourly)
    months = sorted({str(t)[:7] for t in flags.index})
    calm = flags[label(flags.index) == "calm"]
    flagged_days = calm.index[calm["ledger_flag"]].strftime("%Y-%m-%d").value_counts().sort_index()
    # Post hoc (disclosed): calm-period flags compared with the registry's UNRESOLVED venue episode, which the
    # A6 screen had found independently before this monitor existed.
    reg = json.loads(Path("configs/event_registry.json").read_text())["events"]
    unresolved = next(e for e in reg if e["id"] == "U2023-05-BINANCEUS-USD-LIQUIDITY")["reported_window_utc"]
    lo = pd.Timestamp(unresolved["start"], tz="UTC")
    hi = pd.Timestamp(unresolved["end"], tz="UTC") + pd.Timedelta("1D")
    inside = (calm.index >= lo) & (calm.index < hi)
    calm_detail = {"ledger_flag_hours_by_day": {k: int(v) for k, v in flagged_days.items()},
                   "registry_unresolved_window": [str(lo), str(hi)],
                   "ledger_flag_hours_inside_unresolved_window": int(calm["ledger_flag"][inside].sum()),
                   "ledger_flag_share_outside_unresolved_window": float(calm["ledger_flag"][~inside].mean())}
    return {"rule": __doc__.strip().splitlines()[2:5], "threshold_bps": THRESHOLD, "agreement": AGREE,
            "periods": PERIODS, "months_covered": months, "hours_evaluated": int(len(flags)),
            "by_period": summarize(flags), "calm_detail": calm_detail,
            "hourly": {str(t): [None if np.isnan(v) else round(float(v), 1) for v in row] + [bool(lf)]
                       for t, row, lf in zip(flags.index, flags[["L", "T_USDT", "T_USDC"]].to_numpy(),
                                             flags["ledger_flag"])},
            "hourly_columns": ["L", "T_USDT", "T_USDC", "ledger_flag"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binance-us", type=Path, default=Path("data/raw/binance_us"))
    parser.add_argument("--bitstamp", type=Path, default=Path("data/raw/bitstamp"))
    parser.add_argument("--manifest", type=Path, default=Path("reports/events/acquisition_manifest.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/rescue/monitor.json"))
    args = parser.parse_args()
    out = run(args.binance_us, args.bitstamp, args.manifest)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    print(out["months_covered"], out["hours_evaluated"], out["calm_detail"])
    for p, r in out["by_period"].items():
        print(p, {k: (v if not isinstance(v, dict) else (v["hours_evaluated"], None if v["flag_share"] is None
                                                          else round(v["flag_share"], 3))) for k, v in r.items()})


if __name__ == "__main__":
    main()
