"""EXPLORATORY (not pre-registered). Placebos for the panel's anchored slope. Writes reports/explore/placebo.json.

    uv run python -m www_explore.placebo

(a) Mismatched-currency placebo. For every ordered pair (F, G) of different Binance currencies, regress D_G - X on L_F with L2_F as the
    instrument, on hours where both units are observed, day-demeaned within the pair. Same estimator, 7-day block bootstrap, 1,000 draws and
    seed style as www_panel (seed 20261026 here). Primary sample: hours in F's stress months; secondary: all included hours of both units.
    Pooled sets stack pairs and resample them independently, exactly as the panel does for units (pairs share days, so the pooled interval is
    optimistic; per-pair intervals are the cleaner read).
(b) Calm cross-venue placebo. L = 1e4 [log Binance.US BTC/USD - log Bitstamp BTC/USD], D = Binance.US USDT/USD, X = Bitstamp USDT/USD (hourly
    last close of traded minutes). Binance.US has no ETH/USD archive here, so no instrument exists: OLS only (L2 := L, so IV == OLS).
    Primary: calm months of 2022 outside May and November, which leaves October 2022 (the only 2022 month with Binance.US BTC/USD, Bitstamp
    USDT/USD and no stress). Extended (labelled): the same plus calm 2023 months outside March (SVB/USDC stress).
Reading: lambda near 0 means the test discriminates (no mechanical slope of one); lambda near 1 would suggest the slope is mechanical.
"""
from __future__ import annotations

import json
import zipfile
from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd

from www_events.binance_klines import parse_kline_csv
from www_panel import run as P
from www_panel.classify import OUT as MONTHS
from www_panel.data import log_bps

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "reports" / "explore" / "placebo.json"
SEED, DRAWS, BLOCK = 20261026, 1000, 7
PRIMARY_MONTHS = ["2022-10"]
EXTENDED_MONTHS = ["2022-10", "2023-01", "2023-02", "2023-04", "2023-05", "2023-06", "2023-07"]


def _est(stats: dict) -> dict:
    old = P.SEED, P.DRAWS
    P.SEED, P.DRAWS = SEED, DRAWS  # the panel's estimator reads these module constants; restored so other analyses are unaffected
    try:
        return P.estimate(stats, block=BLOCK)
    finally:
        P.SEED, P.DRAWS = old


# ---- (a) mismatched currency ---------------------------------------------------------------------------------------------

def pair_frame(panel: pd.DataFrame, f_unit: str, g_unit: str, stress_only: bool) -> pd.DataFrame:
    """Rows indexed by hour with L, L2 of F and D, X of G (unit column = the pair label)."""
    pf = panel[panel["unit"] == f_unit]
    pg = panel[panel["unit"] == g_unit]
    if stress_only:
        pf = pf[pf["status"] == "stress"]
    j = pd.DataFrame({"L": pf["L"], "L2": pf["L2"]}).join(pd.DataFrame({"D": pg["D"], "X": pg["X"]}), how="inner")
    j["unit"] = f"{f_unit}>{g_unit}"
    j["month"] = j.index.strftime("%Y-%m")
    return j


def mismatched(panel: pd.DataFrame, stress_only: bool) -> dict:
    units = sorted(u for u in panel["unit"].unique() if u.startswith("binance-"))
    frames, per, skipped = [], {}, []
    for f_u, g_u in permutations(units, 2):
        fr = pair_frame(panel, f_u, g_u, stress_only)
        stats = P.hourly_stats(fr)
        if not stats:
            skipped.append(f"{f_u.split('-')[1]}>{g_u.split('-')[1]}")
            continue
        frames.append(fr)
        per[f"{f_u.split('-')[1]}>{g_u.split('-')[1]}"] = _est(stats)
    pooled = _est(P.hourly_stats(pd.concat(frames)))
    lams = np.array([v["iv"]["lam"] for v in per.values()])
    return {"pooled": pooled, "pairs": per, "n_pairs": len(per), "skipped_no_overlap": skipped,
            "summary": {"median_pair_iv": float(np.median(lams)), "min_pair_iv": float(lams.min()), "max_pair_iv": float(lams.max()),
                        "n_ci_excludes_0": int(sum(v["iv"]["lo"] > 0 or v["iv"]["hi"] < 0 for v in per.values())),
                        "n_ci_includes_1": int(sum(v["iv"]["lo"] <= 1 <= v["iv"]["hi"] for v in per.values()))}}


# ---- (b) calm cross-venue --------------------------------------------------------------------------------------------------

def _hourly(close: pd.Series, volume: pd.Series) -> pd.Series:
    return P._hourly_from_minutes(close, volume)


def bstamp_hourly(pair: str) -> pd.Series:
    parts = [pd.read_csv(p) for p in sorted((REPO / "data/raw/bitstamp").glob(f"{pair}-1m-*.csv"))]
    f = pd.concat(parts)
    idx = pd.DatetimeIndex(pd.to_datetime(f["timestamp"], unit="s", utc=True))
    return _hourly(pd.Series(f["close"].to_numpy(float), index=idx).sort_index(), pd.Series(f["volume"].to_numpy(float), index=idx).sort_index())


def bus_hourly(pair: str) -> pd.Series:
    parts = []
    for p in sorted((REPO / "data/raw/binance_us").glob(f"{pair}-1m-*.zip")):
        with zipfile.ZipFile(p) as zf:
            parts.append(parse_kline_csv(zf.read(zf.namelist()[0]).decode()).frame[["close", "volume"]])
    f = pd.concat(parts).sort_index()
    f = f[~f.index.duplicated(keep="first")]
    return _hourly(f["close"], f["volume"])


def venue_frame(bus_btc: pd.Series, bs_btc: pd.Series, bus_usdt: pd.Series, bs_usdt: pd.Series) -> pd.DataFrame:
    """Hourly L (BTC gap), D, X in bps; L2 := L because no second-asset instrument exists (IV == OLS)."""
    f = pd.concat({"b": log_bps(bus_btc), "s": log_bps(bs_btc), "D": log_bps(bus_usdt), "X": log_bps(bs_usdt)}, axis=1)
    f = f.dropna()
    out = pd.DataFrame({"L": f["b"] - f["s"], "D": f["D"], "X": f["X"]})
    out["L2"] = out["L"]
    out["unit"] = "binanceus-bitstamp"
    out["month"] = out.index.strftime("%Y-%m")
    return out


def calm_cross_venue(frame: pd.DataFrame, months: list[str]) -> dict:
    g = frame[frame["month"].isin(months)]
    stats = P.hourly_stats(g)
    if not stats:
        return {"months": months, "n_days": 0}
    est = _est(stats)
    # day-demeaned variances (the variation the estimator uses)
    h = g.dropna(subset=["L", "D", "X"]).copy()
    h["Y"] = h["D"] - h["X"]
    h["day"] = h.index.floor("D")
    h = h[h.groupby("day")["L"].transform("size") >= P.MIN_HOURS_PER_DAY]
    dm = lambda c: h[c] - h.groupby("day")[c].transform("mean")  # noqa: E731
    ols = est["ols"]
    return {"months": months, "n_days": est["n_days"], "n_hours": est["n_hours"], "ols": ols,
            "var_L_within_day_bps2": float(dm("L").var()), "sd_L_within_day_bps": float(dm("L").std()),
            "var_L_raw_bps2": float(h["L"].var()), "mean_L_bps": float(h["L"].mean()),
            "var_Y_within_day_bps2": float(dm("Y").var()),
            "note": "no L2 available (Binance.US has no ETH/USD archive): OLS, not IV; an attenuated slope toward 0 is expected when var(L) is mostly noise"}


def run() -> dict:
    panel = P.build_panel(json.loads(MONTHS.read_text()), {})
    res: dict = {"status": "EXPLORATORY, not pre-registered",
                 "design": {"seed": SEED, "draws": DRAWS, "block_days": BLOCK, "min_hours_per_day": P.MIN_HOURS_PER_DAY}}
    res["mismatched_currency"] = {"stress_F_hours": mismatched(panel, True), "all_included_hours": mismatched(panel, False),
                                  "reading": "lambda near 0: the test discriminates; near 1: the slope would be mechanical"}
    fr = venue_frame(bus_hourly("BTCUSD"), bstamp_hourly("BTCUSD"), bus_hourly("USDTUSD"), bstamp_hourly("USDTUSD"))
    res["calm_cross_venue"] = {"primary_2022_calm": calm_cross_venue(fr, PRIMARY_MONTHS),
                               "extended_2022_2023_calm": calm_cross_venue(fr, EXTENDED_MONTHS),
                               "excluded": "May 2022 and Nov 2022 (stress); Mar 2023 in the extension (SVB/USDC)",
                               "available_2022_months": sorted(m for m in set(fr["month"]) if m.startswith("2022"))}
    return res


def main() -> None:
    res = run()
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    m = res["mismatched_currency"]
    print(json.dumps({"stressF_pooled": m["stress_F_hours"]["pooled"]["iv"], "stressF_summary": m["stress_F_hours"]["summary"],
                      "all_pooled": m["all_included_hours"]["pooled"]["iv"], "calm": res["calm_cross_venue"]}, indent=1))


if __name__ == "__main__":
    main()
