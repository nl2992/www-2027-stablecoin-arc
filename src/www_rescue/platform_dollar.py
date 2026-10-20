"""R2: what is a platform's internal dollar worth once its bank link is cut? (Binance.US, 2023-2025)

Exploratory, post-search direction (docs/review/RESCUE_SEARCH.md). Not part of the frozen plan.

Platform-dollar dislocation of asset X:  PD_X = 1e4 * [log P_platform(X/USD) - log P_external(X/USD)].
If the platform's USD ledger (not X) is what is mispriced, PD is the same for every X; we check this with two
unrelated assets, USDT and BTC, and with USDC where it traded (identification check). External reference: Bitstamp, whose USD stayed redeemable.
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
    d = h.diff().dropna()
    scale = float(h.iloc[:, 0].abs().median())
    return {"hours": int(len(h)), "corr_hourly": float(h.corr().iloc[0, 1]), "median_gap_bps": float(diff.median()),
            "median_abs_gap_bps": float(diff.abs().median()),
            "gap_to_size": float(diff.abs().median() / scale) if scale > 0 else None,
            "corr_hourly_changes": float(d.corr().iloc[0, 1]) if len(d) > 2 else None}


def liquidity(frame: pd.DataFrame, phases: list[tuple[str, str, str, str]] = PHASES) -> list[dict[str, Any]]:
    """Per phase: share of minutes with a trade, median hourly trade count and quote volume (venue USD)."""
    hourly = frame[["trades", "quote_volume"]].resample("1h").sum()
    rows = []
    for name, start, end, _ in phases:
        lo, hi = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
        minutes = (hi - lo) / pd.Timedelta("1min")
        f = frame[(frame.index >= lo) & (frame.index < hi)]
        h = hourly[(hourly.index >= lo) & (hourly.index < hi)]
        rows.append({"phase": name, "traded_minute_share": float((f["volume"] > 0).sum() / minutes),
                     "median_hourly_trades": float(h["trades"].median()) if len(h) else None,
                     "median_hourly_quote_volume": float(h["quote_volume"].median()) if len(h) else None})
    return rows


def shifted_phases(days: int) -> list[tuple[str, str, str, str]]:
    """Move every internal boundary by ``days`` (outer window fixed)."""
    bounds = [PHASES[0][1]] + [str((pd.Timestamp(p[1]) + pd.Timedelta(days=days)).date()) for p in PHASES[1:]] + [PHASES[-1][2]]
    return [(p[0], bounds[i], bounds[i + 1], p[3]) for i, p in enumerate(PHASES)]


def boundary_sensitivity(series: pd.Series, shifts: tuple[int, ...] = (-1, 0, 1)) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in shifts:
        for r in phase_table(series, shifted_phases(k)):
            if r.get("minutes"):
                out.setdefault(r["phase"], []).append(r["median_bps"])
    return {ph: {"min": min(v), "max": max(v), "n_shifts": len(v)} for ph, v in out.items()}


def raw_frame(directory: Path, symbol: str) -> pd.DataFrame:
    """Raw klines with trade counts; call only after load_binance_months has verified the checksums."""
    from www_events.binance_klines import read_kline_zip
    return pd.concat([read_kline_zip(a).frame for a in sorted(directory.glob(f"{symbol}-1m-*.zip"))]).sort_index()


def run(binance_us: Path, bitstamp: Path, manifest: Path, binance: Path | None = None) -> dict[str, Any]:
    def bus(sym: str) -> pd.Series:
        grid, _ = load_binance_months(binance_us, sym, "x")
        return traded_log_close(grid, "x")

    def bst(pair: str) -> pd.Series:
        grid, _ = load_months(bitstamp, pair, "y", manifest)
        return traded_log_close(grid, "y")

    usdt_v, btc_v = bus("USDTUSD"), bus("BTCUSD")
    pd_usdt = dislocation(usdt_v, bst("USDTUSD"))
    pd_btc = dislocation(btc_v, bst("BTCUSD"))
    pd_usdc = dislocation(bus("USDCUSD"), bst("USDCUSD"))
    # within-venue triangle W = log BTC/USD - log BTC/USDT - log USDT/USD (all Binance.US; USD cancels)
    tri = pd.concat([btc_v, bus("BTCUSDT"), usdt_v], axis=1, join="inner").dropna()
    triangle = 1e4 * (tri.iloc[:, 0] - tri.iloc[:, 1] - tri.iloc[:, 2])
    window = pd_usdt[(pd_usdt.index >= PHASES[0][1]) & (pd_usdt.index < PHASES[-1][2])]
    extra: dict[str, Any] = {}
    if binance is not None:  # second BTC reference: Binance.com BTC/USDT x Bitstamp USDT/USD (no new provider)
        bn = traded_log_close(load_binance_months(binance, "BTCUSDT", "z")[0], "z")
        ref = pd.concat([bn, bst("USDTUSD")], axis=1, join="inner").dropna().sum(axis=1)
        extra["pd_btc_alt_reference"] = phase_table(dislocation(btc_v, ref))
    extra["liquidity_usdtusd"] = liquidity(raw_frame(binance_us, "USDTUSD"))
    extra["boundary_sensitivity_pd_usdt"] = boundary_sensitivity(window)
    return {
        "direction": "R2 platform-dollar dislocation (exploratory, post-search)",
        "definition": "PD_X = 1e4*(log P_BinanceUS(X/USD) - log P_Bitstamp(X/USD)), minutes traded on both venues",
        "phases": [dict(zip(("phase", "start", "end", "trigger"), p)) for p in PHASES],
        "pd_usdt": phase_table(window),
        "pd_btc": phase_table(pd_btc),
        "pd_usdc": phase_table(pd_usdc),
        "within_venue_triangle": phase_table(triangle),
        "identification_usdt_vs_usdc": {name: identification(pd_usdt[phase_of(pd_usdt.index) == name],
                                                             pd_usdc[phase_of(pd_usdc.index) == name])
                                        for name, *_ in PHASES},
        "identification_usdt_vs_btc": {name: identification(pd_usdt[phase_of(pd_usdt.index) == name],
                                                            pd_btc[phase_of(pd_btc.index) == name])
                                       for name, *_ in PHASES},
        **extra,
        "daily_median_pd_usdt": {str(k.date()): round(float(v), 2)
                                 for k, v in window.resample("D").median().dropna().items()},
        "daily_median_pd_usdc": {str(k.date()): round(float(v), 2)
                                 for k, v in pd_usdc.resample("D").median().dropna().items()},
        "daily_median_pd_btc": {str(k.date()): round(float(v), 2)
                                for k, v in pd_btc.resample("D").median().dropna().items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binance-us", type=Path, default=Path("data/raw/binance_us"))
    parser.add_argument("--bitstamp", type=Path, default=Path("data/raw/bitstamp"))
    parser.add_argument("--manifest", type=Path, default=Path("reports/events/acquisition_manifest.json"))
    parser.add_argument("--binance", type=Path, default=Path("data/raw/binance"))
    parser.add_argument("--output", type=Path, default=Path("reports/rescue/platform_dollar.json"))
    args = parser.parse_args()
    out = run(args.binance_us, args.bitstamp, args.manifest, args.binance)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    for key in ("pd_usdt", "pd_btc", "pd_usdc", "within_venue_triangle", "pd_btc_alt_reference"):
        for r in out[key]:
            print(key, r["phase"], r["minutes"], round(r.get("median_bps", float("nan")), 1), r.get("ci95_bps"))
    for k, v in out["identification_usdt_vs_btc"].items():
        print("ident btc", k, v)
    for k, v in out["identification_usdt_vs_usdc"].items():
        print("ident usdc", k, v)
    for r in out["liquidity_usdtusd"]:
        print("liq", r)
    print("sens", out["boundary_sensitivity_pd_usdt"])


if __name__ == "__main__":
    main()
