"""Unit diagnostic probe on the hourly core panel (BTC/USD and ETH/USD, Bitfinex, Bitstamp, Coinbase, 2017-2023).

The hourly price is the median of the log closes of the traded minutes inside the hour, built month by month from the
verified minute files (``www_events.candles.load_venue_months`` checks every file against the acquisition manifest).
For each venue pair and calendar year:
  daily_corr       correlation across days of the daily-median hourly BTC gap and ETH gap
  median_abs_gap   median |hourly gap| in bps, BTC and ETH separately
  explained_share  1 - mean((g_ETH - g_BTC)^2) / mean(g_ETH^2) over hours where both gaps exist
  days_ge_50       days with |daily-median BTC gap| >= 50 bps
The daily gap series are stored so that the manuscript figure needs no raw data.

    uv run python -m www_auto.probe            # writes reports/unit_td/probe.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from www_events.candles import load_venue_months

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "data" / "raw"
MANIFEST = REPO / "reports" / "events" / "acquisition_manifest.json"
OUTPUT = REPO / "reports" / "unit_td" / "probe.json"
START, END = "2017-01", "2023-12"
VENUES = ("bitfinex", "bitstamp", "coinbase")
ASSETS = {"BTC": "BTCUSD", "ETH": "ETHUSD"}
PAIRS = (("bitfinex", "bitstamp"), ("bitfinex", "coinbase"), ("coinbase", "bitstamp"))
MIN_DAYS_CORR = 30
MIN_HOURS = 100
BIG_DAY_BPS = 50.0


def months() -> list[str]:
    return [m.strftime("%Y-%m") for m in pd.period_range(START, END, freq="M")]


def hourly_median_log_close(venue: str, pair: str, raw: Path = RAW, manifest: Path = MANIFEST) -> tuple[pd.Series, dict]:
    """Hourly median of traded-minute log closes, loaded month by month with manifest checks."""
    parts, hashes, missing = [], [], []
    for m in months():
        try:
            grid, prov = load_venue_months(raw / venue, pair, "x", manifest, venue, [m])
        except FileNotFoundError:
            missing.append(m)
            continue
        hashes += [f"{f['file']}:{f['sha256']}" for f in prov["files"]]
        traded = grid["x_traded"].astype("boolean").fillna(False).astype(bool)
        px = grid.loc[traded, "x_close"].astype(float)
        px = px[px > 0]
        parts.append(np.log(px).groupby(px.index.floor("h")).median())
    series = pd.concat(parts).sort_index()
    series = series[~series.index.duplicated(keep="first")]
    index = pd.date_range(f"{START}-01", "2023-12-31 23:00", freq="h", tz="UTC", name="timestamp_utc")
    series = series.reindex(index)
    digest = hashlib.sha256("\n".join(hashes).encode()).hexdigest()
    return series, {"files": len(hashes), "files_sha256": digest, "missing_months": missing,
                    "hours": int(series.notna().sum())}


def build_panel(raw: Path = RAW, manifest: Path = MANIFEST) -> tuple[pd.DataFrame, dict]:
    cols, meta = {}, {}
    for venue in VENUES:
        for asset, pair in ASSETS.items():
            cols[(venue, asset)], meta[f"{venue}|{asset}"] = hourly_median_log_close(venue, pair, raw, manifest)
    return pd.DataFrame(cols), meta


def pair_stats(panel: pd.DataFrame, a: str, b: str) -> tuple[dict, pd.DataFrame]:
    """Per-year statistics and the daily-median gap series for the pair (a minus b)."""
    gaps = pd.DataFrame({k: 1e4 * (panel[(a, k)] - panel[(b, k)]) for k in ASSETS})
    both = gaps.dropna()
    daily = gaps.groupby(gaps.index.floor("D")).median()
    out: dict[str, dict] = {}
    for year in range(int(START[:4]), int(END[:4]) + 1):
        g = gaps[gaps.index.year == year]
        gb = both[both.index.year == year]
        d = daily[daily.index.year == year].dropna()
        corr = float(d["BTC"].corr(d["ETH"])) if len(d) >= MIN_DAYS_CORR and d.std().min() > 0 else None
        share = None
        if len(gb) >= MIN_HOURS:
            share = float(1 - ((gb["ETH"] - gb["BTC"]) ** 2).mean() / (gb["ETH"] ** 2).mean())
        out[str(year)] = {
            "hours_btc": int(g["BTC"].notna().sum()), "hours_eth": int(g["ETH"].notna().sum()), "hours_both": int(len(gb)),
            "days": int(len(d)), "daily_corr": corr,
            "median_abs_gap_btc_bps": float(g["BTC"].abs().median()), "median_abs_gap_eth_bps": float(g["ETH"].abs().median()),
            "explained_share": share, "days_ge_50": int((d["BTC"].abs() >= BIG_DAY_BPS).sum())}
    return out, daily


def build(panel: pd.DataFrame, meta: dict) -> dict:
    result: dict = {
        "method": "hourly median of traded-minute log closes; gap = 1e4 (log p_first - log p_second); daily gap = median of "
                  "hourly gaps; explained share = 1 - mean((g_ETH - g_BTC)^2) / mean(g_ETH^2) on hours with both gaps",
        "window": [START, END], "assets": list(ASSETS), "min_days_corr": MIN_DAYS_CORR, "min_hours_share": MIN_HOURS,
        "big_day_bps": BIG_DAY_BPS, "series": meta, "pairs": {}, "daily_gaps_bps": {}}
    for a, b in PAIRS:
        stats, daily = pair_stats(panel, a, b)
        key = f"{a}-{b}"
        result["pairs"][key] = stats
        result["daily_gaps_bps"][key] = {k: {d.strftime("%Y-%m-%d"): round(float(v), 3) for d, v in daily[k].dropna().items()}
                                         for k in ASSETS}
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="www_auto.probe")
    ap.add_argument("--out", type=Path, default=OUTPUT)
    args = ap.parse_args(argv)
    panel, meta = build_panel()
    result = build(panel, meta)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(f"WROTE {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
