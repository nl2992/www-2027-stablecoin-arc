"""R6: replication of the platform-ledger dislocation on Binance.com GBP (2023-05) and EUR (2023-09) rail cuts.

Predictions P1-P2 and the falsification rule were recorded in docs/review/RESCUE_SEARCH.md before any of these
data were downloaded. Same definition as R2: PD_X = 1e4 * [log P_platform(X/F) - log P_external(X/F)], with the
external reference on Bitstamp, whose fiat rails stayed open. X in {USDT, BTC}.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from www_events.bitstamp import load_months
from www_events.runner import load_binance_months

from .platform_dollar import dislocation, identification, phase_of, phase_table, traded_log_close

CASES: dict[str, dict[str, Any]] = {
    "GBP": {
        "event": "Paysafe stops GBP deposits/withdrawals for all Binance users (2023-05-22)",
        "phases": [("pre", "2023-04-15", "2023-05-22", "four-plus weeks before the suspension"),
                   ("post_4w", "2023-05-22", "2023-06-19", "first four weeks after the suspension (P1 window)"),
                   ("later", "2023-06-19", "2023-08-01", "after the P1 window")],
        "sources": ["https://www.theblock.co/post/219416/cloureiro@theblock.co",
                    "https://finder.com/uk/news/binance-suspends-sterling-deposits-and-withdrawals"],
    },
    "EUR": {
        "event": "Paysafe stops EUR transfers for its Binance users (2023-09-25); convert EUR by end of October",
        "phases": [("pre", "2023-08-25", "2023-09-25", "month before the suspension"),
                   ("post_4w", "2023-09-25", "2023-10-23", "first four weeks after the suspension (P2 window)"),
                   ("later", "2023-10-23", "2023-12-01", "after the P2 window")],
        "sources": ["https://www.theblock.co/news/markets/2023-09-28-binance-halts-eur-trading-paysafe-253346",
                    "https://cointelegraph.com/news/binance-loses-support-of-euro-banking-partner"],
    },
}


def series(binance: Path, bitstamp: Path, manifest: Path, fiat: str) -> tuple[pd.Series, pd.Series]:
    def bn(sym: str) -> pd.Series:
        grid, _ = load_binance_months(binance, sym, "x")
        return traded_log_close(grid, "x")

    def bs(pair: str) -> pd.Series:
        grid, _ = load_months(bitstamp, pair, "y", manifest)
        return traded_log_close(grid, "y")

    platform_usdt = -bn(f"{fiat}USDT")  # Binance {F}USDT is USDT per F, so USDT priced in F is its inverse
    if fiat == "EUR":
        external_usdt = bs("USDTEUR")
    else:  # USDT in GBP via external USD: (USDT/USD) / (GBP/USD)
        both = pd.concat([bs("USDTUSD"), bs("GBPUSD")], axis=1, join="inner").dropna()
        external_usdt = both.iloc[:, 0] - both.iloc[:, 1]
    return dislocation(platform_usdt, external_usdt), dislocation(bn(f"BTC{fiat}"), bs(f"BTC{fiat}"))


def verdict(case: dict[str, Any]) -> str:
    """Pre-recorded rule: the post-window |median PD| must be >= 10 bps and USDT/BTC must agree (corr >= 0.5)."""
    post = next(r for r in case["pd_usdt"] if r["phase"] == "post_4w")
    ident = case["identification"]["post_4w"]
    if post.get("minutes", 0) == 0 or "corr_hourly" not in ident:
        return "INSUFFICIENT_DATA"
    if abs(post["median_bps"]) < 10 or ident["corr_hourly"] < 0.5:
        return "FALSIFIED"
    return "SUPPORTED_SIGN_POSITIVE" if post["median_bps"] > 0 else "SUPPORTED_SIGN_NEGATIVE"


def run(binance: Path, bitstamp: Path, manifest: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"direction": "R6 replication (predictions pre-recorded)", "cases": {}}
    for fiat, spec in CASES.items():
        pd_usdt, pd_btc = series(binance, bitstamp, manifest, fiat)
        ph = spec["phases"]
        case = {"event": spec["event"], "sources": spec["sources"], "phases": ph,
                "pd_usdt": phase_table(pd_usdt, ph), "pd_btc": phase_table(pd_btc, ph),
                "identification": {n: identification(pd_usdt[phase_of(pd_usdt.index, ph) == n],
                                                     pd_btc[phase_of(pd_btc.index, ph) == n]) for n, *_ in ph},
                "daily_median_pd_usdt": {str(k.date()): round(float(v), 2)
                                         for k, v in pd_usdt.resample("D").median().dropna().items()}}
        case["verdict"] = verdict(case)
        out["cases"][fiat] = case
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binance", type=Path, default=Path("data/raw/binance"))
    parser.add_argument("--bitstamp", type=Path, default=Path("data/raw/bitstamp"))
    parser.add_argument("--manifest", type=Path, default=Path("reports/events/acquisition_manifest.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/rescue/fiat_rail.json"))
    args = parser.parse_args()
    out = run(args.binance, args.bitstamp, args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    for fiat, c in out["cases"].items():
        print(fiat, c["verdict"])
        for key in ("pd_usdt", "pd_btc"):
            for r in c[key]:
                print(" ", key, r["phase"], r["minutes"], round(r.get("median_bps", float("nan")), 1), r.get("ci95_bps"))
        print("  ident", c["identification"])


if __name__ == "__main__":
    main()
