"""Step 3: pre-registered estimation (autoresearch/program_panel.md, commit bfb6205). Writes reports/panel/results.json.

    uv run python -m www_panel.run

Model: D - X = lambda L + day effects + error, fitted on day-demeaned hourly data by OLS and by IV with L2 as the instrument.
Inference: moving-block bootstrap over days (7-day blocks, 1,000 draws, seed 20261024); 95% percentile intervals.
Mechanical choices not spelled out in the pre-registration: hours need L, L2, D and X all present; a UTC day needs at least 2 such hours;
blocks are 7 consecutive entries of a unit's sorted day list in the resampled set; units are resampled independently within a pooled set;
the pooled and per-currency sets stack unit-days (day effects are per unit-day, so the pooled slope is a sum of within-day moments).
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from .data import UNITS, log_bps, read_kraken, read_pair, unit_key
from .classify import gap, OUT as MONTHS

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "reports" / "panel" / "results.json"
SEED, DRAWS, BLOCK = 20261024, 1000, 7
MIN_HOURS_PER_DAY = 2
FIELDS = ("LY", "L2Y", "L2L", "LL")  # per-day sufficient statistics of the demeaned data


# ---- data -----------------------------------------------------------------------------------------------------------------

def _hourly_from_minutes(close: pd.Series, volume: pd.Series) -> pd.Series:
    c = close[volume > 0]
    return c.groupby(c.index.floor("h")).last()


def alt_x(kind: str) -> pd.Series:
    """Alternative USDT/USD hourly close: 'binance_us' (2019-09 on) or 'bitstamp' (2022-04 on), traded minutes only."""
    if kind == "bitstamp":
        parts = [pd.read_csv(p) for p in sorted((REPO / "data/raw/bitstamp").glob("USDTUSD-1m-*.csv"))]
        f = pd.concat(parts)
        idx = pd.DatetimeIndex(pd.to_datetime(f["timestamp"], unit="s", utc=True))
        return _hourly_from_minutes(pd.Series(f["close"].to_numpy(float), index=idx).sort_index(),
                                    pd.Series(f["volume"].to_numpy(float), index=idx).sort_index())
    from www_events.binance_klines import parse_kline_csv
    parts = []
    for p in sorted((REPO / "data/raw/binance_us").glob("USDTUSD-1m-*.zip")):
        with zipfile.ZipFile(p) as zf:
            parts.append(parse_kline_csv(zf.read(zf.namelist()[0]).decode()).frame[["close", "volume"]])
    f = pd.concat(parts).sort_index()
    f = f[~f.index.duplicated(keep="first")]
    return _hourly_from_minutes(f["close"], f["volume"])


def build_panel(months: dict, x_series: dict[str, pd.Series]) -> pd.DataFrame:
    """Hourly rows for every included (not coverage-excluded) month: unit, month, status, L, L2, D, and one X column per reference."""
    kb, ke, ku = read_kraken("XBTUSD"), read_kraken("ETHUSD"), read_kraken("USDTUSD")
    xs = {"X": ku, **x_series}
    frames = []
    for venue, fiat in UNITS:
        key = unit_key(venue, fiat)
        st = {m: r["status"] for m, r in months["units"][key]["months"].items() if r["status"] in ("stress", "calm")}
        if not st:
            continue
        f = pd.concat({"L": gap(venue, fiat, "BTC", kb), "L2": gap(venue, fiat, "ETH", ke)}, axis=1)
        usdt = read_pair(venue, fiat, "USDT")
        usdt = usdt["close"][usdt["volume"] > 0]
        f["D"] = log_bps(usdt).reindex(f.index)
        for name, x in xs.items():
            f[name] = log_bps(x).reindex(f.index)
        f["month"] = f.index.strftime("%Y-%m")
        f = f[f["month"].isin(st)]
        f["status"] = f["month"].map(st)
        f["unit"], f["venue"], f["fiat"] = key, venue, fiat
        frames.append(f)
    return pd.concat(frames)


# ---- estimation -----------------------------------------------------------------------------------------------------------

def _moments(g: pd.DataFrame, keys: list, min_n: int) -> pd.DataFrame:
    grp = g.groupby(keys, sort=True)
    n = grp["L"].transform("size")
    g = g[n >= min_n]
    grp = g.groupby(keys, sort=True)
    d = {c: g[c] - grp[c].transform("mean") for c in ("L", "L2", "Y")}
    out = pd.DataFrame({"LY": d["L"] * d["Y"], "L2Y": d["L2"] * d["Y"], "L2L": d["L2"] * d["L"], "LL": d["L"] * d["L"], "n": 1.0})
    for k in keys:
        out[k] = g[k]
    return out.groupby(keys, sort=True)[list(FIELDS) + ["n"]].sum()


def hourly_stats(f: pd.DataFrame, xcol: str = "X") -> dict[str, np.ndarray]:
    g = f.dropna(subset=["L", "L2", "D", xcol]).copy()
    g["Y"] = g["D"] - g[xcol]
    g["day"] = g.index.floor("D")
    m = _moments(g, ["unit", "day"], MIN_HOURS_PER_DAY)
    return {u: m.loc[u].to_numpy() for u in m.index.get_level_values(0).unique()}


def weekly_stats(f: pd.DataFrame, xcol: str = "X") -> dict[str, np.ndarray]:
    """Daily medians of L, L2, D, X (hours where all exist), demeaned within unit-week (Monday-start), >= 2 days per week."""
    g = f.dropna(subset=["L", "L2", "D", xcol]).copy()
    g["Y"] = g["D"] - g[xcol]
    g["day"] = g.index.floor("D")
    d = g.groupby(["unit", "day"])[["L", "L2", "Y"]].median().reset_index()
    d["week"] = d["day"].dt.tz_localize(None).dt.to_period("W-SUN").astype(str)
    m = _moments(d, ["unit", "week"], 2)
    return {u: m.loc[u].to_numpy() for u in m.index.get_level_values(0).unique()}


def _lams(tot: np.ndarray) -> tuple[float, float]:
    ols = tot[..., 0] / tot[..., 3] if np.all(tot[..., 3] != 0) else np.nan
    iv = tot[..., 1] / tot[..., 2] if np.all(tot[..., 2] != 0) else np.nan
    return float(ols), float(iv)


def estimate(stats: dict[str, np.ndarray], block: int = BLOCK) -> dict:
    if not stats:
        return {"n_days": 0}
    pt = sum(a.sum(axis=0) for a in stats.values())
    ols, iv = _lams(pt)
    rng = np.random.default_rng(SEED)
    draws = np.empty((DRAWS, 2))
    units = sorted(stats)
    for b in range(DRAWS):
        tot = np.zeros(5)
        for u in units:
            a = stats[u]
            n = len(a)
            bl = min(block, n)
            nb = -(-n // bl)
            starts = rng.integers(0, n - bl + 1, size=nb)
            idx = (starts[:, None] + np.arange(bl)[None, :]).ravel()[:n]
            tot += a[idx].sum(axis=0)
        with np.errstate(divide="ignore", invalid="ignore"):
            draws[b] = (tot[0] / tot[3] if tot[3] else np.nan, tot[1] / tot[2] if tot[2] else np.nan)
    ci = lambda v: [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]  # noqa: E731
    return {"n_units": len(units), "n_days": int(sum(len(a) for a in stats.values())), "n_hours": int(pt[4]),
            "iv": {"lam": iv, "lo": ci(draws[:, 1])[0], "hi": ci(draws[:, 1])[1]},
            "ols": {"lam": ols, "lo": ci(draws[:, 0])[0], "hi": ci(draws[:, 0])[1]}}


def sel(panel: pd.DataFrame, **kw) -> pd.DataFrame:
    m = np.ones(len(panel), bool)
    for k, v in kw.items():
        m &= panel[k].isin(v if isinstance(v, (list, tuple, set)) else [v]).to_numpy()
    return panel[m]


def run() -> dict:
    months = json.loads(MONTHS.read_text())
    alts = {"XB": alt_x("binance_us"), "XS": alt_x("bitstamp")}
    panel = build_panel(months, alts)
    fiats = sorted(panel["fiat"].unique())
    res: dict = {"design": {"seed": SEED, "draws": DRAWS, "block_days": BLOCK, "min_hours_per_day": MIN_HOURS_PER_DAY,
                            "months_file": "reports/panel/months.json",
                            "daily_week_fe_note": "in robustness.daily_week_fe, n_hours counts daily rows and blocks are single weeks (7 days)"}}
    est = lambda f, x="X": estimate(hourly_stats(f, x))  # noqa: E731
    stress, calm = sel(panel, status="stress"), sel(panel, status="calm")
    res["pooled_stress"], res["pooled_calm"] = est(stress), est(calm)
    res["by_currency"] = {}
    for fiat in fiats:
        c = {"stress_months": int(sel(stress, fiat=fiat).groupby("unit")["month"].nunique().sum()),
             "calm_months": int(sel(calm, fiat=fiat).groupby("unit")["month"].nunique().sum()),
             "stress": est(sel(stress, fiat=fiat))}
        if c["calm_months"]:
            c["calm"] = est(sel(calm, fiat=fiat))
        res["by_currency"][fiat] = c
    res["by_venue"] = {v: {"stress": est(sel(stress, venue=v)), **({"calm": est(sel(calm, venue=v))} if len(sel(calm, venue=v)) else {})}
                       for v in sorted(panel["venue"].unique())}
    res["by_month"] = []
    for (unit, month), f in panel.groupby(["unit", "month"], sort=True):
        res["by_month"].append({"unit": unit, "month": month, "status": f["status"].iloc[0], **est(f)})
    # ---- P1, P2, falsification, evaluated mechanically
    ps = res["pooled_stress"]["iv"]
    p1 = {"lam": ps["lam"], "lo": ps["lo"], "hi": ps["hi"], "excludes_0": bool(ps["lo"] > 0 or ps["hi"] < 0),
          "includes_1": bool(ps["lo"] <= 1 <= ps["hi"])}
    p1["pass"] = p1["excludes_0"] and p1["includes_1"]
    elig = {k: v for k, v in res["by_currency"].items() if v["stress_months"] >= 3}
    inside = {k: bool(0.8 <= v["stress"]["iv"]["lam"] <= 1.2) for k, v in elig.items()}
    p2 = {"eligible": sorted(elig), "in_0.8_1.2": inside, "n_inside": int(sum(inside.values())), "n_eligible": len(elig)}
    p2["pass"] = bool(p2["n_inside"] > p2["n_eligible"] / 2)
    res["P1"], res["P2"] = p1, p2
    res["P3"] = {"months_with_lam_below_0.5": [m for m in res["by_month"] if m.get("iv") and m["iv"]["lam"] < 0.5],
                 "currencies_with_lam_below_0.5": [k for k, v in res["by_currency"].items() if v["stress"]["iv"]["lam"] < 0.5]}
    res["falsification"] = {"pooled_upper": ps["hi"], "triggered": bool(ps["hi"] < 0.5)}
    # ---- robustness (reported, not used to choose anything)
    rob: dict = {"ols_pooled_stress": res["pooled_stress"]["ols"]}
    rob["ols_by_currency_stress"] = {k: v["stress"]["ols"] for k, v in res["by_currency"].items()}
    rob["daily_week_fe"] = {"pooled_stress": estimate(weekly_stats(stress), block=1),
                            "by_currency": {k: estimate(weekly_stats(sel(stress, fiat=k)), block=1) for k in fiats}}
    for name, col in (("alt_x_binance_us", "XB"), ("alt_x_bitstamp", "XS")):
        have = stress.dropna(subset=[col])
        rob[name] = {"pooled_stress": est(have, col), "by_currency": {k: est(sel(have, fiat=k), col) for k in fiats if len(sel(have, fiat=k))}}
    rob["krw_venues_stress"] = {v: res["by_venue"][v]["stress"] for v in ("upbit", "bithumb") if v in res["by_venue"]}
    res["robustness"] = rob
    return res


def main() -> None:
    res = run()
    RESULTS.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: res[k] for k in ("P1", "P2", "falsification")}, indent=1))


if __name__ == "__main__":
    main()
