"""Noise bounds on the calm-year unit component: fee bands, tick sizes, persistence, common share, timing, lead-lag.

Inputs: the verified minute files (``www_events.candles.load_venue_months``, manifest-checked) and
``configs/fee_schedule.json`` (base-tier taker fees by effective date, with sources and verification status).
Gaps are 1e4 * (log p_first - log p_second) for BTC/USD and ETH/USD on a venue pair, as in ``www_auto.probe``.

Per pair-year:
  fee band        hour-by-hour sum of the two venues' base-tier taker fees (bps); share of hours with |L| above it
  tick            smallest nonzero absolute change between consecutive traded-minute closes that occurs at least
                  ``TICK_MIN_COUNT`` times in the year (guards against float noise), in bps of the median close
  persistence     autocorrelation of the daily cross-asset gap (mean of the BTC and ETH daily-median gaps) at lags 1, 7, 30
  common share    2 sum(gB gE) / sum(gB^2 + gE^2) = 1 - 2 sum(resid^2)/sum(gap^2), where common = mean of the BTC and ETH gap
                  and resid = gap - common: 0 for independent gaps, 1 for identical ones (hourly, daily; with and
                  without removing the year mean)
  timing          correlation of the BTC and ETH hourly gaps and the explained share 1 - mean((gE-gB)^2)/mean(gE^2) under
                  (median) hourly median of traded-minute closes, (last) last traded close in the hour,
                  (sync) the :59 minute close, only in hours where all four legs traded in that minute
Lead-lag: cross-correlation of the BTC and ETH minute gaps (levels, and one-minute changes) for 2022-06 and 2019-03; a
positive peak lag means the ETH gap lags the BTC gap.

    uv run python -m www_auto.noise_bounds       # writes reports/unit_td/noise_bounds.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from www_auto.probe import ASSETS, MANIFEST, PAIRS, RAW, VENUES, months
from www_events.candles import load_venue_months

REPO = Path(__file__).resolve().parents[2]
FEES = REPO / "configs" / "fee_schedule.json"
OUTPUT = REPO / "reports" / "unit_td" / "noise_bounds.json"
YEARS = tuple(range(2017, 2024))
LAGS = (1, 7, 30)
TICK_MIN_COUNT = 20
MIN_HOURS = 100
MIN_DAYS = 60
LEADLAG_MONTHS = {"calm_2022-06": ("2022-06-01", "2022-07-01"), "stress_2019-03": ("2019-03-01", "2019-04-01")}
MAX_LEAD = 15
MIN_OBS_LEAD = 200


# ---------------------------------------------------------------- loading
def load_minutes(raw: Path = RAW, manifest: Path = MANIFEST) -> tuple[dict, dict, dict]:
    """Traded-minute close prices per (venue, asset): log closes, tick statistics by year, and file hashes."""
    logs, ticks, hashes = {}, {}, []
    for venue in VENUES:
        for asset, pair in ASSETS.items():
            parts = []
            for m in months():
                try:
                    grid, prov = load_venue_months(raw / venue, pair, "x", manifest, venue, [m])
                except FileNotFoundError:
                    continue
                hashes += [f"{f['file']}:{f['sha256']}" for f in prov["files"]]
                traded = grid["x_traded"].astype("boolean").fillna(False).astype(bool)
                px = grid.loc[traded, "x_close"].astype(float)
                parts.append(px[px > 0])
            px = pd.concat(parts).sort_index()
            px = px[~px.index.duplicated(keep="first")]
            ticks[(venue, asset)] = tick_by_year(px)
            logs[(venue, asset)] = np.log(px)
    return logs, ticks, {"files": len(hashes), "files_sha256": hashlib.sha256("\n".join(hashes).encode()).hexdigest()}


def tick_by_year(px: pd.Series) -> dict[int, dict]:
    """Smallest recurring nonzero minute-to-minute price change per year, absolute and in bps of the median close."""
    out = {}
    consecutive = px.index.to_series().diff() == pd.Timedelta(minutes=1)
    change = px.diff().abs().where(consecutive).round(8)
    for year in YEARS:
        sel = (px.index.year == year)
        ch = change[sel].dropna()
        ch = ch[ch > 0]
        if ch.empty:
            out[year] = None
            continue
        counts = ch.value_counts()
        recurring = counts[counts >= TICK_MIN_COUNT]
        tick = float(recurring.index.min()) if len(recurring) else float(ch.min())
        out[year] = {"min_nonzero": float(ch.min()), "tick": tick, "median_close": float(px[sel].median()),
                     "tick_bps": 1e4 * tick / float(px[sel].median()), "changes": int(len(ch))}
    return out


# ---------------------------------------------------------------- hourly conventions
def series_hourly(log_px: pd.Series, index: pd.DatetimeIndex) -> pd.DataFrame:
    """Hourly median and last of traded-minute log closes, and the :59 minute close, on ``index``."""
    hour = log_px.index.floor("h")
    g = log_px.groupby(hour)
    last59 = log_px[log_px.index.minute == 59]
    last59.index = last59.index.floor("h")
    return pd.DataFrame({"median": g.median(), "last": g.last(), "sync": last59}).reindex(index)


def pair_gaps(h: dict, a: str, b: str) -> dict[str, pd.DataFrame]:
    """Hourly BTC and ETH gaps (bps) of venue a minus venue b under the three timing conventions."""
    out = {}
    for conv in ("median", "last", "sync"):
        gaps = pd.DataFrame({k: 1e4 * (h[(a, k)][conv] - h[(b, k)][conv]) for k in ASSETS})
        if conv == "sync":
            gaps = gaps.where(gaps.notna().all(axis=1))  # all four legs traded in the final minute
        out[conv] = gaps
    return out


def agreement(gaps: pd.DataFrame) -> dict:
    both = gaps.dropna()
    if len(both) < MIN_HOURS or both["ETH"].pow(2).mean() == 0:
        return {"hours": int(len(both)), "corr": None, "explained_share": None}
    return {"hours": int(len(both)), "corr": float(both["BTC"].corr(both["ETH"])),
            "explained_share": float(1 - ((both["ETH"] - both["BTC"]) ** 2).mean() / (both["ETH"] ** 2).mean())}


def common_share(g: pd.DataFrame, center: bool = False) -> float | None:
    """Share of the gaps' second moment that is common: 1 - 2 sum(resid^2)/sum(gap^2) with common = mean of BTC and ETH gap."""
    both = g.dropna()
    if len(both) < MIN_DAYS:
        return None
    if center:
        both = both - both.mean()
    total = (both ** 2).to_numpy().sum()
    if total == 0:
        return None
    resid = ((both["BTC"] - both["ETH"]) ** 2 / 2).sum()
    return float(1 - 2 * resid / total)


def autocorr(s: pd.Series, lag: int) -> float | None:
    x = pd.concat([s, s.shift(lag)], axis=1).dropna()
    if len(x) < MIN_DAYS or x.iloc[:, 0].std() == 0 or x.iloc[:, 1].std() == 0:
        return None
    return float(x.iloc[:, 0].corr(x.iloc[:, 1]))


# ---------------------------------------------------------------- fees
def fee_schedule(path: Path = FEES) -> dict:
    return json.loads(path.read_text())


def taker_bps(schedule: dict, venue: str, index: pd.DatetimeIndex) -> pd.Series:
    """Base-tier taker fee in bps in force at each timestamp (step function of effective dates)."""
    steps = sorted(schedule["venues"][venue], key=lambda e: e["effective_from"])
    out = pd.Series(np.nan, index=index)
    for e in steps:
        out[index >= pd.Timestamp(e["effective_from"], tz="UTC")] = 100.0 * e["taker_pct"]
    return out


def band_bps(schedule: dict, a: str, b: str, index: pd.DatetimeIndex) -> pd.Series:
    return taker_bps(schedule, a, index) + taker_bps(schedule, b, index)


# ---------------------------------------------------------------- lead-lag
def cross_corr_peak(x: pd.Series, y: pd.Series, max_lag: int = MAX_LEAD) -> dict:
    """Peak of corr(x(t), y(t+k)) over k in [-max_lag, max_lag] minutes on a shared minute grid (NaN pairs dropped)."""
    grid = pd.date_range(min(x.index[0], y.index[0]), max(x.index[-1], y.index[-1]), freq="min")
    xs, ys = x.reindex(grid), y.reindex(grid)
    corrs = {}
    for k in range(-max_lag, max_lag + 1):
        pair = pd.concat([xs, ys.shift(-k)], axis=1).dropna()
        if len(pair) >= MIN_OBS_LEAD and pair.iloc[:, 0].std() > 0 and pair.iloc[:, 1].std() > 0:
            corrs[k] = float(pair.iloc[:, 0].corr(pair.iloc[:, 1]))
    if not corrs:
        return {"peak_lag_min": None, "peak_corr": None, "lag0_corr": None}
    k = max(corrs, key=lambda j: corrs[j])
    return {"peak_lag_min": int(k), "peak_corr": corrs[k], "lag0_corr": corrs.get(0)}


def minute_gap_leadlag(logs: dict, a: str, b: str, lo: str, hi: str) -> dict:
    sl = slice(pd.Timestamp(lo, tz="UTC"), pd.Timestamp(hi, tz="UTC") - pd.Timedelta(minutes=1))
    gap = {}
    for k in ASSETS:
        j = pd.concat([logs[(a, k)].loc[sl], logs[(b, k)].loc[sl]], axis=1, keys=["a", "b"]).dropna()
        gap[k] = 1e4 * (j["a"] - j["b"])
    levels = cross_corr_peak(gap["BTC"] - gap["BTC"].mean(), gap["ETH"] - gap["ETH"].mean())
    diffs = {}
    for k, g in gap.items():
        grid = g.reindex(pd.date_range(g.index[0], g.index[-1], freq="min"))
        diffs[k] = grid.diff().dropna()
    changes = cross_corr_peak(diffs["BTC"], diffs["ETH"])
    return {"levels": levels, "changes": changes, "minutes_btc": int(len(gap["BTC"])), "minutes_eth": int(len(gap["ETH"]))}


# ---------------------------------------------------------------- assembly
def pair_year_stats(gaps: dict, band: pd.Series, a: str, b: str) -> dict:
    med = gaps["median"]
    daily = med.groupby(med.index.floor("D")).median()
    cross = daily.mean(axis=1, skipna=False)  # daily cross-asset median gap: mean of the two daily medians
    out = {}
    for year in YEARS:
        sel = med.index.year == year
        m = med[sel]
        d = daily[daily.index.year == year]
        cs = cross[cross.index.year == year]
        row = {"hours_btc": int(m["BTC"].notna().sum()), "hours_eth": int(m["ETH"].notna().sum()),
               "band_bps": float(band[sel].mean()), "days": int(cs.notna().sum())}
        for k in ASSETS:
            ab = m[k].abs().dropna()
            bnd = band[sel].reindex(ab.index)
            row[f"median_abs_gap_{k.lower()}_bps"] = float(ab.median()) if len(ab) else None
            row[f"share_above_band_{k.lower()}"] = float((ab > bnd).mean()) if len(ab) else None
        row["daily_ac"] = {str(l): autocorr(cs, l) for l in LAGS}
        csd = cs.dropna()
        row["median_daily_cross_gap_bps"] = float(csd.median()) if len(csd) else None
        row["share_days_sign_of_median"] = float((np.sign(csd) == np.sign(csd.median())).mean()) if len(csd) else None
        row["common_share"] = {"hourly": common_share(m), "hourly_centered": common_share(m, True),
                               "daily": common_share(d), "daily_centered": common_share(d, True)}
        row["timing"] = {c: agreement(gaps[c][sel]) for c in gaps}
        out[str(year)] = row
    return out


def build(logs: dict, ticks: dict, meta: dict, schedule: dict) -> dict:
    index = pd.date_range(f"{YEARS[0]}-01-01", f"{YEARS[-1]}-12-31 23:00", freq="h", tz="UTC", name="timestamp_utc")
    hourly = {k: series_hourly(v, index) for k, v in logs.items()}
    result: dict = {
        "method": __doc__.split("\n\n")[1] if "\n\n" in (__doc__ or "") else "",
        "fee_schedule_sha256": hashlib.sha256(FEES.read_bytes()).hexdigest(), "series": meta,
        "tick_min_count": TICK_MIN_COUNT, "lags_days": list(LAGS), "ticks": {}, "pairs": {}, "leadlag": {}}
    for (venue, asset), per_year in ticks.items():
        result["ticks"][f"{venue}|{asset}"] = {str(y): v for y, v in per_year.items()}
    for a, b in PAIRS:
        key = f"{a}-{b}"
        result["pairs"][key] = pair_year_stats(pair_gaps(hourly, a, b), band_bps(schedule, a, b, index), a, b)
        result["leadlag"][key] = {name: minute_gap_leadlag(logs, a, b, lo, hi) for name, (lo, hi) in LEADLAG_MONTHS.items()}
    return result


def _round(o):
    if isinstance(o, float):
        return round(o, 6)
    if isinstance(o, dict):
        return {k: _round(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_round(v) for v in o]
    return o


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="www_auto.noise_bounds")
    ap.add_argument("--out", type=Path, default=OUTPUT)
    args = ap.parse_args(argv)
    logs, ticks, meta = load_minutes()
    result = _round(build(logs, ticks, meta, fee_schedule()))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(f"WROTE {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
