"""R2: what is a platform's internal dollar worth once its bank link is cut? (Binance.US, 2023-2025)

Exploratory, post-search direction (docs/review/RESCUE_SEARCH.md). Not part of the frozen plan.

Platform-dollar dislocation of asset X:  PD_X = 1e4 * [log P_platform(X/USD) - log P_external(X/USD)].
If the platform's USD ledger (not X) is what is mispriced, PD is the same for every X; we check this with two
unrelated assets, USDT and BTC (identification check). External reference: Bitstamp, whose USD stayed redeemable.
Phase boundaries are documented dates from configs/usd_rail_impairments.json and news sources listed in PHASES;
they are fixed here before the phase statistics are computed (daily medians of PD_USDT were inspected first; disclosed).
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

PHASES = [  # (name, start_utc inclusive, end_utc exclusive, documented trigger)
    ("pre", "2023-05-01", "2023-06-05", "baseline before the SEC complaint"),
    ("sec_complaint", "2023-06-05", "2023-06-09", "SEC sues Binance and Binance.US (2023-06-05)"),
    ("deposits_suspended", "2023-06-09", "2023-06-13", "Binance.US suspends USD deposits (2023-06-09)"),
    ("withdrawal_halt_window", "2023-06-13", "2023-06-22", "banking partners to pause USD payments from 2023-06-13"),
    ("crypto_only_transition", "2023-06-22", "2023-08-01", "USD pairs delisted; users told to convert USD (2023-06-22)"),
    ("impaired", "2023-08-01", "2025-02-19", "USD rail impaired (configs/usd_rail_impairments.json)"),
    ("restored", "2025-02-19", "2025-11-01", "USD deposits/withdrawals restored (2025-02-19)"),
]
BLOCK = "60min"


def traded_log_close(grid: pd.DataFrame, prefix: str) -> pd.Series:
    traded = grid[f"{prefix}_traded"].astype("boolean").fillna(False).astype(bool)
    return np.log(grid.loc[traded, f"{prefix}_close"].astype(float))


def dislocation(platform: pd.Series, external: pd.Series) -> pd.Series:
    """Minute-aligned PD in bps; only minutes traded on both venues."""
    both = pd.concat([platform, external], axis=1, join="inner").dropna()
    return 1e4 * (both.iloc[:, 0] - both.iloc[:, 1])


def phase_of(index: pd.DatetimeIndex, phases: list[tuple[str, str, str, str]] = PHASES) -> np.ndarray:
    out = np.full(len(index), None, dtype=object)
    for name, start, end, _ in phases:
        out[(index >= pd.Timestamp(start, tz="UTC")) & (index < pd.Timestamp(end, tz="UTC"))] = name
    return out


def block_bootstrap_median(x: pd.Series, *, draws: int = 1000, seed: int = 20230609) -> tuple[float, float] | None:
    """95% interval for the median, resampling whole hours (minutes within an hour are dependent)."""
    blocks = [b.to_numpy() for _, b in x.groupby(x.index.floor(BLOCK)) if len(b)]
    if len(blocks) < 10:
        return None
    rng = np.random.default_rng(seed)
    meds = [np.median(np.concatenate([blocks[i] for i in rng.integers(0, len(blocks), len(blocks))]))
            for _ in range(draws)]
    lo, hi = np.percentile(meds, [2.5, 97.5])
    return float(lo), float(hi)


def phase_table(pd_series: pd.Series, phases: list[tuple[str, str, str, str]] = PHASES) -> list[dict[str, Any]]:
    ph = phase_of(pd_series.index, phases)
    rows = []
    for name, start, end, trigger in phases:
        x = pd_series[ph == name]
        if x.empty:
            rows.append({"phase": name, "start": start, "end": end, "trigger": trigger, "minutes": 0})
            continue
        ci = block_bootstrap_median(x)
        rows.append({"phase": name, "start": start, "end": end, "trigger": trigger, "minutes": int(len(x)),
                     "median_bps": float(x.median()), "ci95_bps": ci,
                     "iqr_bps": [float(x.quantile(0.25)), float(x.quantile(0.75))],
                     "share_abs_ge_50bps": float((x.abs() >= 50).mean())})
    return rows


def identification(pd_a: pd.Series, pd_b: pd.Series) -> dict[str, Any]:
    """Do two unrelated assets show the same dislocation? Hourly medians, minutes traded everywhere."""
    h = pd.concat([pd_a.resample("1h").median(), pd_b.resample("1h").median()], axis=1, join="inner").dropna()
    if len(h) < 24:
        return {"hours": int(len(h))}
    diff = h.iloc[:, 0] - h.iloc[:, 1]
    return {"hours": int(len(h)), "corr_hourly": float(h.corr().iloc[0, 1]), "median_gap_bps": float(diff.median()),
            "median_abs_gap_bps": float(diff.abs().median())}


def run(binance_us: Path, bitstamp: Path, manifest: Path) -> dict[str, Any]:
    def bus(sym: str) -> pd.Series:
        grid, _ = load_binance_months(binance_us, sym, "x")
        return traded_log_close(grid, "x")

    def bst(pair: str) -> pd.Series:
        grid, _ = load_months(bitstamp, pair, "y", manifest)
        return traded_log_close(grid, "y")

    pd_usdt = dislocation(bus("USDTUSD"), bst("USDTUSD"))
    pd_btc = dislocation(bus("BTCUSD"), bst("BTCUSD"))
    window = pd_usdt[(pd_usdt.index >= PHASES[0][1]) & (pd_usdt.index < PHASES[-1][2])]
    return {
        "direction": "R2 platform-dollar dislocation (exploratory, post-search)",
        "definition": "PD_X = 1e4*(log P_BinanceUS(X/USD) - log P_Bitstamp(X/USD)), minutes traded on both venues",
        "phases": [dict(zip(("phase", "start", "end", "trigger"), p)) for p in PHASES],
        "pd_usdt": phase_table(window),
        "pd_btc": phase_table(pd_btc),
        "identification_usdt_vs_btc": {name: identification(pd_usdt[phase_of(pd_usdt.index) == name],
                                                            pd_btc[phase_of(pd_btc.index) == name])
                                       for name, *_ in PHASES},
        "daily_median_pd_usdt": {str(k.date()): round(float(v), 2)
                                 for k, v in window.resample("D").median().dropna().items()},
        "daily_median_pd_btc": {str(k.date()): round(float(v), 2)
                                for k, v in pd_btc.resample("D").median().dropna().items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binance-us", type=Path, default=Path("data/raw/binance_us"))
    parser.add_argument("--bitstamp", type=Path, default=Path("data/raw/bitstamp"))
    parser.add_argument("--manifest", type=Path, default=Path("reports/events/acquisition_manifest.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/rescue/platform_dollar.json"))
    args = parser.parse_args()
    out = run(args.binance_us, args.bitstamp, args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    for key in ("pd_usdt", "pd_btc"):
        for r in out[key]:
            print(key, r["phase"], r["minutes"], round(r.get("median_bps", float("nan")), 1), r.get("ci95_bps"))
    for k, v in out["identification_usdt_vs_btc"].items():
        print("ident", k, v)


if __name__ == "__main__":
    main()
