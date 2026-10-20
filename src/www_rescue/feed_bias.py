"""What a naive multi-venue BTC/USD index gets wrong during ledger failures, and the timing of the signal.

Index (per hour, from hourly medians of traded minutes on each venue):
  naive    : BTC-volume-weighted mean of venue log prices, every venue's "USD" treated as one dollar
  clean    : the same over open-rail venues only (Bitstamp, and Coinbase where downloaded)
  filtered : naive, but a venue-hour is dropped when the monitor rule flags it as a ledger failure:
             |L| >= 100 bps and |PD_second - L| <= 0.25 |L|  (rule and thresholds from www_rescue.monitor)
Error = 1e4 (index - clean) in bps. A venue with weight w and dislocation PD moves the index by about w * PD,
so the error in a wider index with more venues scales down with that venue's share; both are reported.

Timeline: first day the daily median PD_BTC reaches 100 bps, and first day with >= 6 flagged hours, set against
dated public reports (sources in docs/review/FEED_BIAS.md).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from www_events.bitstamp import load_months
from www_events.candles import load_venue_months
from www_events.runner import load_binance_months

from .ledger_panel import EPISODES
from .monitor import AGREE, THRESHOLD

DISCLOSURES: dict[str, list[tuple[str, str]]] = {
    "L2017-04-BITFINEX-WIRES": [
        ("2017-04-09", "press: Bitfinex has sued Wells Fargo over blocked outbound wires (suit filed the week before)"),
        ("2017-04-13", "Bitfinex blog: USD withdrawal delays"),
        ("2017-04-18", "Bitfinex: Taiwanese banks refuse all incoming wires"),
    ],
    "L2018-10-BITFINEX-FIAT": [
        ("2018-10-02", "Bloomberg: Noble Bank has lost Bitfinex and Tether as clients"),
        ("2018-10-07", "Bitfinex blog denies insolvency"),
        ("2018-10-11", "The Block: all Bitfinex fiat deposits paused (confirmed 10-12)"),
        ("2019-04-25", "NYAG filing: about $850M of Bitfinex funds lost or seized at Crypto Capital"),
    ],
    "L2019-04-BITFINEX-NYAG": [
        ("2019-04-25", "NYAG filing against Bitfinex and Tether"),
    ],
    "BINANCEUS-2023": [
        ("2023-06-05", "SEC sues Binance and Binance.US"),
        ("2023-06-09", "Binance.US suspends USD deposits"),
        ("2023-06-13", "banking partners pause USD payments"),
    ],
}
BINANCEUS_WINDOW = ("2023-05-01", "2023-08-01")


def hourly(log_close: pd.Series, volume: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"p": log_close.resample("1h").median(), "v": volume.resample("1h").sum()})


def venue(grid: pd.DataFrame, prefix: str) -> pd.DataFrame:
    traded = grid[f"{prefix}_traded"].astype("boolean").fillna(False).astype(bool)
    g = grid[traded]
    return hourly(np.log(g[f"{prefix}_close"].astype(float)), g[f"{prefix}_volume"].astype(float))


def weighted(frames: dict[str, pd.DataFrame], drop: pd.DataFrame | None = None) -> pd.Series:
    p = pd.concat({k: f["p"] for k, f in frames.items()}, axis=1)
    w = pd.concat({k: f["v"] for k, f in frames.items()}, axis=1).where(p.notna())
    if drop is not None:
        for col in drop.columns:  # zero the weight of a flagged venue-hour; other venues untouched
            hit = drop[col].reindex(w.index).astype("boolean").fillna(False).to_numpy(dtype=bool)
            w.loc[hit, col] = 0.0
    return (p * w).sum(axis=1, min_count=1) / w.sum(axis=1).replace(0, np.nan)


def ledger_flags(L: pd.Series, second: pd.Series) -> pd.Series:
    both = pd.concat([L, second], axis=1).dropna()
    return (both.iloc[:, 0].abs() >= THRESHOLD) & ((both.iloc[:, 1] - both.iloc[:, 0]).abs() <= AGREE * both.iloc[:, 0].abs())


def error_stats(err: pd.Series) -> dict[str, Any]:
    e = err.dropna()
    return {"hours": int(len(e)), "median_abs_bps": float(e.abs().median()), "p95_abs_bps": float(e.abs().quantile(0.95)),
            "max_abs_bps": float(e.abs().max()), "hours_abs_ge_50": int((e.abs() >= 50).sum()),
            "hours_abs_ge_100": int((e.abs() >= 100).sum())}


def timeline(L: pd.Series, flags: pd.Series, disclosures: list[tuple[str, str]]) -> dict[str, Any]:
    daily = L.resample("1D").median().dropna()
    flag_days = flags.astype(int).resample("1D").sum()
    first = lambda s: str(s.index[0].date()) if len(s) else None  # noqa: E731
    on = (flag_days >= 6).astype(int)
    starts = on.index[(on.diff().fillna(on.iloc[0]) == 1).to_numpy()] if len(on) else []
    runs = []
    for s in starts:
        rest = on[s:]
        end = rest.index[rest.to_numpy() == 0]
        runs.append([str(s.date()), str((end[0] - pd.Timedelta("1D")).date()) if len(end) else str(rest.index[-1].date())])
    return {"first_day_daily_pd_ge_100": first(daily[daily >= 100]), "first_day_ge_6_flag_hours": first(flag_days[flag_days >= 6]),
            "flag_runs_ge_6_hours_per_day": runs,
            "flagged_hours": int(flags.sum()), "disclosures": [{"date": d, "event": e} for d, e in disclosures]}


def case(platform: str, frames: dict[str, pd.DataFrame], clean_keys: list[str], L: pd.Series, second: pd.Series,
         disclosures: list[tuple[str, str]]) -> dict[str, Any]:
    flags = ledger_flags(L, second)
    drop = pd.DataFrame({platform: flags})
    clean = weighted({k: frames[k] for k in clean_keys})
    naive = weighted(frames)
    equal = pd.concat({k: f["p"] for k, f in frames.items()}, axis=1).mean(axis=1)
    filtered = weighted(frames, drop)
    vol = pd.concat({k: f["v"] for k, f in frames.items()}, axis=1)
    share = (vol[platform] / vol.sum(axis=1)).replace([np.inf], np.nan)
    stress = flags.reindex(naive.index).astype("boolean").fillna(False).astype(bool)
    return {
        "venues": list(frames), "clean_venues": clean_keys,
        "platform_volume_share_median": float(share.median()),
        "platform_volume_share_flagged_hours_median": float(share[stress].median()) if stress.any() else None,
        "naive_vw": error_stats(1e4 * (naive - clean)), "naive_equal_weight": error_stats(1e4 * (equal - clean)),
        "filtered_vw": error_stats(1e4 * (filtered - clean)),
        "naive_vw_flagged_hours": error_stats(1e4 * (naive - clean)[stress]),
        "filtered_vw_flagged_hours": error_stats(1e4 * (filtered - clean)[stress]),
        "timeline": timeline(L, flags, disclosures),
    }


def run(raw: Path, manifest_ledger: Path, manifest_events: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"rule": {"threshold_bps": THRESHOLD, "agreement": AGREE}}
    for eid, spec in EPISODES.items():
        ms = spec["months"]
        def load(v: str, pair: str) -> pd.DataFrame:
            return venue(load_venue_months(raw / v, pair, "x", manifest_ledger, v, ms)[0], "x")
        frames = {"bitfinex": load("bitfinex", "BTCUSD"), "bitstamp": load("bitstamp", "BTCUSD"),
                  "coinbase": load("coinbase", "BTCUSD")}
        eth_bfx, eth_cb = load("bitfinex", "ETHUSD"), load("coinbase", "ETHUSD")
        L = 1e4 * (frames["bitfinex"]["p"] - frames["bitstamp"]["p"])
        pd_eth = 1e4 * (eth_bfx["p"] - eth_cb["p"])
        out[eid] = case("bitfinex", frames, ["bitstamp", "coinbase"], L.dropna(), pd_eth.dropna(), DISCLOSURES[eid])
    lo, hi = (pd.Timestamp(x, tz="UTC") for x in BINANCEUS_WINDOW)
    def cut(f: pd.DataFrame) -> pd.DataFrame:
        return f[(f.index >= lo) & (f.index < hi)]
    bus = {s: cut(venue(load_binance_months(raw / "binance_us", s, "x")[0], "x")) for s in ("BTCUSD", "USDTUSD")}
    bst = {s: cut(venue(load_months(raw / "bitstamp", s, "x", manifest_events)[0], "x")) for s in ("BTCUSD", "USDTUSD")}
    frames = {"binance_us": bus["BTCUSD"], "bitstamp": bst["BTCUSD"]}
    L = 1e4 * (bus["BTCUSD"]["p"] - bst["BTCUSD"]["p"])
    pd_usdt = 1e4 * (bus["USDTUSD"]["p"] - bst["USDTUSD"]["p"])
    out["BINANCEUS-2023"] = case("binance_us", frames, ["bitstamp"], L.dropna(), pd_usdt.dropna(),
                                 DISCLOSURES["BINANCEUS-2023"])
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--manifest-ledger", type=Path, default=Path("reports/events/acquisition_manifest.json"))
    parser.add_argument("--manifest-events", type=Path, default=Path("reports/events/acquisition_manifest.json"))
    parser.add_argument("--out", type=Path, default=Path("reports/rescue/feed_bias.json"))
    args = parser.parse_args()
    out = run(args.raw, args.manifest_ledger, args.manifest_events)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    for k, v in out.items():
        if k != "rule":
            print(k, json.dumps({x: v[x] for x in v if x not in ("venues", "clean_venues")}, indent=0)[:1500])


if __name__ == "__main__":
    main()
