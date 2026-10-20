"""Downstream impact: how well index methodologies survive an exchange-dollar discount, and a dislocation-aware repair.

Setting. A multi-venue BTC/USD index averages venue prices as if every "USD" were one dollar. When a venue's ledger
dollar trades at a discount, its BTC/USD price carries that discount. Per hour, in log prices (hourly medians of
traded minutes, as in www_rescue.feed_bias), error = 1e4 (index - clean) in bps, where clean is the volume-weighted
mean over open-rail venues only (the same benchmark as feed_bias).

Methods
  naive         BTC-volume-weighted mean of all venues (feed_bias "naive")
  equal         equal-weight mean of all venues
  median        cross-venue median
  excl_k        drop a venue-hour whose price is more than k bps from the cross-venue median (k = 50, 100, 200),
                then volume-weighted mean of the rest. If every venue is dropped the hour falls back to naive
                (counted in `exclusion_fallback_hours`).
  filtered      naive, with flagged platform venue-hours dropped (feed_bias "filtered")
  repaired      flagged platform venue-hours are kept, but the platform price is converted into external dollars:
                p_repaired = p_platform - PD_second / 1e4, where PD_second is the dislocation of a different asset
                (ETH for Bitfinex, USDT for Binance.US) measured against an external venue.

Non-circularity of the repair. The adjustment uses only PD_second. It never uses the platform's own BTC gap L (the
platform BTC price minus an external BTC price) and never the benchmark. L enters only the flag, which decides
WHERE to apply the adjustment, not by HOW MUCH. The repaired error is therefore the part of the BTC gap that the
second asset's dislocation does not explain, and it can be large when the two disagree.

Caveat on degenerate cases. With two venues (Binance.US) the cross-venue median equals the equal-weight mean, and
both venues sit at the same distance from the median, so exclusion drops both or neither: exclusion equals naive.
With three venues (Bitfinex) a median ignores a single outlier by construction.
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

from .feed_bias import BINANCEUS_WINDOW, error_stats, ledger_flags, venue, weighted
from .ledger_panel import EPISODES

EXCLUSION_K = (50.0, 100.0, 200.0)
SCALING_WEIGHTS = (0.05, 0.1, 0.2, 0.3)
ORACLE_DEVIATION_BPS = 50.0  # 0.5%, a typical price-oracle deviation threshold (no specific oracle's parameters claimed)
EPISODE_NAMES = {
    "L2017-04-BITFINEX-WIRES": "Bitfinex 2017", "L2018-10-BITFINEX-FIAT": "Bitfinex 2018",
    "L2019-04-BITFINEX-NYAG": "Bitfinex 2019", "BINANCEUS-2023": "Binance.US 2023",
}


def pivot(frames: dict[str, pd.DataFrame], col: str) -> pd.DataFrame:
    return pd.concat({k: f[col] for k, f in frames.items()}, axis=1)


def exclusion_index(frames: dict[str, pd.DataFrame], k: float) -> tuple[pd.Series, int]:
    """Outlier-exclusion index; returns the index and the number of hours that fell back to naive."""
    p = pivot(frames, "p")
    dev = 1e4 * p.sub(p.median(axis=1), axis=0).abs()
    idx = weighted(frames, dev > k)
    undefined = idx.isna() & p.notna().any(axis=1)
    return idx.where(~undefined, weighted(frames)), int(undefined.sum())


def repaired_frames(frames: dict[str, pd.DataFrame], platform: str, flags: pd.Series, pd_second: pd.Series) -> dict[str, pd.DataFrame]:
    """Platform price minus PD_second (bps -> log) in flagged hours; uses nothing about the platform's own BTC gap."""
    out = {k: f.copy() for k, f in frames.items()}
    p = out[platform]["p"]
    adj = (pd_second.reindex(p.index) / 1e4).where(flags.reindex(p.index).astype("boolean").fillna(False).to_numpy(dtype=bool))
    out[platform]["p"] = p - adj.fillna(0.0)
    return out


def indexes(frames: dict[str, pd.DataFrame], platform: str, flags: pd.Series, pd_second: pd.Series) -> tuple[dict[str, pd.Series], dict[str, int]]:
    drop = pd.DataFrame({platform: flags})
    out = {"naive": weighted(frames), "equal": pivot(frames, "p").mean(axis=1), "median": pivot(frames, "p").median(axis=1)}
    fallback = {}
    for k in EXCLUSION_K:
        out[f"excl_{int(k)}"], fallback[f"excl_{int(k)}"] = exclusion_index(frames, k)
    out["filtered"] = weighted(frames, drop)
    out["repaired"] = weighted(repaired_frames(frames, platform, flags, pd_second))
    return out, fallback


def stats(err: pd.Series) -> dict[str, Any]:
    e = err.dropna()
    if e.empty:
        return {"hours": 0}
    return error_stats(e)


def scaling(L: pd.Series, second: pd.Series) -> list[dict[str, Any]]:
    """Implied index error w * PD for a platform of index weight w, using the observed PD paths."""
    rows = []
    for w in SCALING_WEIGHTS:
        row: dict[str, Any] = {"w": w}
        for name, pdp in (("btc_gap", L), ("second_asset", second)):
            e = (w * pdp.dropna()).abs()
            row[name] = {"hours": int(len(e)), "hours_ge_50": int((e >= ORACLE_DEVIATION_BPS).sum()),
                         "share_ge_50": float((e >= ORACLE_DEVIATION_BPS).mean()) if len(e) else None,
                         "p95_abs_bps": float(e.quantile(0.95)) if len(e) else None,
                         "max_abs_bps": float(e.max()) if len(e) else None}
        rows.append(row)
    return rows


def case(platform: str, frames: dict[str, pd.DataFrame], clean_keys: list[str], L: pd.Series, second: pd.Series) -> dict[str, Any]:
    flags = ledger_flags(L, second)
    clean = weighted({k: frames[k] for k in clean_keys})
    idx, fallback = indexes(frames, platform, flags, second)
    flagged = flags.reindex(clean.index).astype("boolean").fillna(False).to_numpy(dtype=bool)
    vol = pivot(frames, "v").where(pivot(frames, "p").notna())
    leader = (vol.idxmax(axis=1) == platform).reindex(clean.index).fillna(False).to_numpy(dtype=bool)
    share = (vol[platform] / vol.sum(axis=1)).reindex(clean.index)
    errors = {m: 1e4 * (s - clean) for m, s in idx.items()}
    subsets = {"all_hours": np.ones(len(clean), dtype=bool), "flagged_hours": flagged, "platform_volume_leader_hours": leader,
               "flagged_and_leader_hours": flagged & leader}
    return {
        "venues": list(frames), "n_venues": len(frames), "clean_venues": clean_keys,
        "degenerate_for_median_and_exclusion": len(frames) <= 2,
        "hours": int(clean.notna().sum()), "flagged_hours": int(flagged.sum()),
        "platform_volume_leader_hours": int(leader.sum()), "flagged_and_leader_hours": int((flagged & leader).sum()),
        "platform_volume_share_median": float(share.median()),
        "platform_volume_share_flagged_median": float(share[flagged].median()) if flagged.any() else None,
        "exclusion_fallback_hours": fallback,
        "methods": {m: {name: stats(e[mask]) for name, mask in subsets.items()} for m, e in errors.items()},
        "scaling": scaling(L, second),
    }


def run(raw: Path, manifest_ledger: Path, manifest_events: Path) -> dict[str, Any]:
    out: dict[str, Any] = {
        "note": "error = 1e4 (index - clean) bps, clean = open-rail venues, as in feed_bias; repair uses PD_second only, never the platform's own BTC gap",
        "oracle_deviation_bps": ORACLE_DEVIATION_BPS, "exclusion_k_bps": list(EXCLUSION_K)}
    for eid, spec in EPISODES.items():
        ms = spec["months"]

        def load(v: str, pair: str) -> pd.DataFrame:
            return venue(load_venue_months(raw / v, pair, "x", manifest_ledger, v, ms)[0], "x")

        frames = {"bitfinex": load("bitfinex", "BTCUSD"), "bitstamp": load("bitstamp", "BTCUSD"), "coinbase": load("coinbase", "BTCUSD")}
        L = (1e4 * (frames["bitfinex"]["p"] - frames["bitstamp"]["p"])).dropna()
        pd_eth = (1e4 * (load("bitfinex", "ETHUSD")["p"] - load("coinbase", "ETHUSD")["p"])).dropna()
        out[eid] = case("bitfinex", frames, ["bitstamp", "coinbase"], L, pd_eth)
    lo, hi = (pd.Timestamp(x, tz="UTC") for x in BINANCEUS_WINDOW)

    def cut(f: pd.DataFrame) -> pd.DataFrame:
        return f[(f.index >= lo) & (f.index < hi)]

    bus = {s: cut(venue(load_binance_months(raw / "binance_us", s, "x")[0], "x")) for s in ("BTCUSD", "USDTUSD")}
    bst = {s: cut(venue(load_months(raw / "bitstamp", s, "x", manifest_events)[0], "x")) for s in ("BTCUSD", "USDTUSD")}
    L = (1e4 * (bus["BTCUSD"]["p"] - bst["BTCUSD"]["p"])).dropna()
    pd_usdt = (1e4 * (bus["USDTUSD"]["p"] - bst["USDTUSD"]["p"])).dropna()
    out["BINANCEUS-2023"] = case("binance_us", {"binance_us": bus["BTCUSD"], "bitstamp": bst["BTCUSD"]}, ["bitstamp"], L, pd_usdt)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--manifest-ledger", type=Path, default=Path("reports/events/acquisition_manifest.json"))
    parser.add_argument("--manifest-events", type=Path, default=Path("reports/events/acquisition_manifest.json"))
    parser.add_argument("--out", type=Path, default=Path("reports/rescue/index_repair.json"))
    args = parser.parse_args()
    out = run(args.raw, args.manifest_ledger, args.manifest_events)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    for eid in EPISODE_NAMES:
        c = out[eid]
        print(EPISODE_NAMES[eid], c["n_venues"], "venues; hours", c["hours"], "flagged", c["flagged_hours"], "leader", c["platform_volume_leader_hours"])
        for m, s in c["methods"].items():
            a = s["all_hours"]
            print(f"  {m:9s} >=50 {a['hours_abs_ge_50']:5d} >=100 {a['hours_abs_ge_100']:5d} med {a['median_abs_bps']:6.1f} p95 {a['p95_abs_bps']:6.1f} max {a['max_abs_bps']:7.1f}")


if __name__ == "__main__":
    main()
