"""Amendment A6: systematic in-sample event screen over Binance.US USD-quoted stablecoin pairs.

Applies R1 unchanged on a complete 1-minute grid, keeps breaching minutes that belong
to an R1-satisfying 24h window, merges same-coin detections < 14 days apart, clusters
across coins, and matches clusters to registry windows (+-14 days). Writes every
detection, cluster, month scanned and non-detection to reports/events/screen_A6.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .registry import RULES, load_registry
from .runner import load_binance_months

SYMBOLS = ("USDCUSD", "USDTUSD", "DAIUSD", "TUSDUSD")
SCREEN_END = pd.Timestamp("2023-06-01", tz="UTC")  # exclusive: through 2023-05 (before the A2 impairment)
GAP = pd.Timedelta(days=RULES["R2_cluster_gap_days"])
WINDOW = 24 * 60


def r1_membership(dev: np.ndarray, traded: np.ndarray) -> np.ndarray:
    """Breaching minutes that lie inside some rolling 24h window holding >= R1 min_minutes breaches.

    Assumes a complete regular 1-minute grid (missing minutes are untraded).
    """
    rule = RULES["R1_severity"]
    breach = (traded & (np.abs(dev) >= rule["threshold_bps"])).astype(float)
    count = pd.Series(breach).rolling(WINDOW, min_periods=1).sum().to_numpy()  # window ending at t
    satisfied = (count >= rule["min_minutes"]).astype(float)
    # minute m belongs if some window ending in [m, m + 24h) is satisfied
    ahead = pd.Series(satisfied[::-1]).rolling(WINDOW, min_periods=1).max().to_numpy()[::-1]
    return (breach > 0) & (ahead > 0)


def episodes(times: pd.DatetimeIndex, dev: np.ndarray, member: np.ndarray, coin: str) -> list[dict[str, Any]]:
    idx = np.flatnonzero(member)
    out: list[dict[str, Any]] = []
    if idx.size == 0:
        return out
    groups, start = [], 0
    for k in range(1, idx.size):
        if times[idx[k]] - times[idx[k - 1]] >= GAP:
            groups.append(idx[start:k])
            start = k
    groups.append(idx[start:])
    for g in groups:
        ext = g[np.argmax(np.abs(dev[g]))]
        out.append({"coin": coin, "start_utc": times[g[0]].isoformat(), "end_utc": times[g[-1]].isoformat(),
                    "breach_minutes": int(g.size), "extreme_bps": float(dev[ext]),
                    "extreme_utc": times[ext].isoformat(), "direction": "DISCOUNT" if dev[ext] < 0 else "PREMIUM"})
    return out


def cluster(eps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eps = sorted(eps, key=lambda e: e["start_utc"])
    clusters: list[dict[str, Any]] = []
    for e in eps:
        s, t = pd.Timestamp(e["start_utc"]), pd.Timestamp(e["end_utc"])
        if clusters and s - pd.Timestamp(clusters[-1]["end_utc"]) < GAP:
            c = clusters[-1]
            c["members"].append(e)
            c["end_utc"] = max(c["end_utc"], e["end_utc"])
        else:
            clusters.append({"start_utc": e["start_utc"], "end_utc": e["end_utc"], "members": [e]})
    for c in clusters:
        c["primary"] = max(c["members"], key=lambda m: abs(m["extreme_bps"]))["coin"]
    return clusters


def match_registry(clusters: list[dict[str, Any]], registry: list[dict[str, Any]]) -> None:
    for c in clusters:
        lo, hi = pd.Timestamp(c["start_utc"]) - GAP, pd.Timestamp(c["end_utc"]) + GAP
        hits = sorted({e["cluster_id"] for e in registry
                       if pd.Timestamp(e["reported_window_utc"]["start"], tz="UTC") <= hi
                       and lo <= pd.Timestamp(e["reported_window_utc"]["end"], tz="UTC") + pd.Timedelta("1D")})
        c["registry_match"] = hits
        c["classification"] = "MATCHES_REGISTRY" if hits else "NEW_CANDIDATE"


def run_screen(data_dir: Path, registry: list[dict[str, Any]]) -> dict[str, Any]:
    eps, scanned = [], {}
    for coin in SYMBOLS:
        grid, prov = load_binance_months(data_dir, coin, "x")
        g = grid[grid.index < SCREEN_END].rename(columns=lambda col: col[2:])
        traded = g["traded"].astype("boolean").fillna(False).to_numpy(dtype=bool)
        dev = 10_000 * np.log(g["close"].to_numpy(dtype=float))
        member = r1_membership(np.nan_to_num(dev, nan=0.0), traded)
        coin_eps = episodes(g.index, dev, member, coin)
        eps += coin_eps
        monthly = pd.Series(traded, index=g.index).groupby(g.index.strftime("%Y-%m")).mean()
        detected_months = {pd.Timestamp(e["start_utc"]).strftime("%Y-%m") for e in coin_eps} | \
                          {pd.Timestamp(e["end_utc"]).strftime("%Y-%m") for e in coin_eps}
        scanned[coin] = {"first_minute": g.index[0].isoformat(), "last_minute": g.index[-1].isoformat(),
                         "months": len(monthly), "traded_share_by_month": {k: round(float(v), 4) for k, v in monthly.items()},
                         "months_without_detection": sorted(set(monthly.index) - detected_months),
                         "files": len([f for f in prov["files"] if f["file"] < f"{coin}-1m-2023-06"])}
    clusters = cluster(eps)
    match_registry(clusters, registry)
    return {"amendment": "A6", "rule": RULES["R1_severity"], "merge_gap_days": RULES["R2_cluster_gap_days"],
            "screen_end_exclusive": SCREEN_END.isoformat(), "scanned": scanned, "episodes": eps,
            "clusters": clusters,
            "summary": {"episodes": len(eps), "clusters": len(clusters),
                        "matched": sum(c["classification"] == "MATCHES_REGISTRY" for c in clusters),
                        "new": sum(c["classification"] == "NEW_CANDIDATE" for c in clusters)}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw/binance_us"))
    parser.add_argument("--output", type=Path, default=Path("reports/events/screen_A6.json"))
    args = parser.parse_args()
    out = run_screen(args.data_dir, load_registry(Path("configs/event_registry.json")))
    out["measured_utc"] = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%MZ")
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["summary"]))
    for c in out["clusters"]:
        print(c["classification"], c["start_utc"][:10], c["end_utc"][:10], c["primary"], c["registry_match"],
              [(m["coin"], m["breach_minutes"], round(m["extreme_bps"])) for m in c["members"]])


if __name__ == "__main__":
    main()
