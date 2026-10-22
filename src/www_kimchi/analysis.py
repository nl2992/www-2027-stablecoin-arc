"""Kimchi premium: cross-asset common component and the USDT/KRW anchor test (pre-registered in docs/kimchi/PREREG.md).

g_i = 1e4 [log P_KRW,i - log P_USD,i - log FX] (bps), FX = FRED DEXKOUS forward-filled. Daily value = median of the UTC day's hours
(>= 12). Common component C = mean of BTC, ETH, XRP gaps. Anchor (Bithumb KRW-USDT, only 2023-12-08..2023-12-31):
  L = C (hourly), D = 1e4 [log USDTKRW - log FX], X = 1e4 log Kraken USDT/USD; slope of (D - X) on L, OLS and IV (instrument:
  BCH gap), day-block bootstrap. Daily statistics use calendar-week block bootstrap. 1,000 draws, seed 20261022.

    uv run python -m www_kimchi.analysis       # writes reports/kimchi/results.json
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
OUTPUT = REPO / "reports" / "kimchi" / "results.json"
DRAWS, SEED = 1000, 20261022
MIN_HOURS = 12
CORE = ("BTC", "ETH", "XRP")
ALL = ("BTC", "ETH", "XRP", "BCH", "ETC")
WINDOWS = {"E1_2017-12_2018-01": ("2017-12-01", "2018-01-31"), "E2_2021-03_2021-05": ("2021-03-01", "2021-05-31"),
           "E3_2022-05_2022-06": ("2022-05-01", "2022-06-30"), "C1_2019": ("2019-01-01", "2019-12-31"),
           "C2_2020": ("2020-01-01", "2020-12-31"), "C3_2023-01_2023-11": ("2023-01-01", "2023-11-30")}
HIGH = ("E1_2017-12_2018-01", "E2_2021-03_2021-05")
ANCHOR_WINDOW = ("2023-12-08", "2023-12-31 23:00")
H1_CORR, H1_LOWER, H1_R2 = 0.9, 0.85, 0.8


# ---- data -------------------------------------------------------------------------------------------------------------

def hourly_index() -> pd.DatetimeIndex:
    return pd.date_range("2017-10-01", "2023-12-31 23:00", freq="h", tz="UTC", name="timestamp_utc")


def read_krw(path: Path, col: str = "close") -> pd.Series:
    x = pd.read_csv(path)
    x.index = pd.to_datetime(x["timestamp_utc"], utc=True)
    s = x[col].astype(float)
    return np.log(s[s > 0]).reindex(hourly_index())


def read_usd_hourly(path: Path) -> pd.Series:
    x = pd.read_csv(path)
    x.index = pd.to_datetime(x["timestamp"], unit="s", utc=True)
    x = x[(x["volume"] > 0) & (x["close"] > 0)]
    return np.log(x["close"]).reindex(hourly_index())


def read_fx(path: Path) -> pd.Series:
    x = pd.read_csv(path, na_values=["."])
    s = pd.Series(x["DEXKOUS"].astype(float).to_numpy(), index=pd.to_datetime(x["date"]).dt.tz_localize("UTC"))
    return np.log(s.dropna())


def fx_hourly(fx: pd.Series, lag_days: int = 0) -> pd.Series:
    days = pd.date_range("2017-01-01", "2023-12-31", freq="D", tz="UTC")
    d = fx.reindex(days).ffill().shift(lag_days)
    out = d.reindex(hourly_index().floor("D"))
    out.index = hourly_index()
    return out


def load_all(root: Path = REPO) -> dict[str, Any]:
    from www_auto import probe
    raw = root / "data" / "raw"
    krw = {c: read_krw(raw / "upbit" / f"KRW-{c}_60m.csv") for c in ALL}
    usd = {"BTC": probe.hourly_median_log_close("coinbase", "BTCUSD")[0], "ETH": probe.hourly_median_log_close("coinbase", "ETHUSD")[0],
           "XRP": read_usd_hourly(raw / "bitstamp_1h" / "XRPUSD-1h-2017-2023.csv"),
           "BCH": read_usd_hourly(raw / "bitstamp_1h" / "BCHUSD-1h-2017-2023.csv"),
           "ETC": read_usd_hourly(raw / "coinbase_1h" / "ETCUSD-1h-2017-2023.csv")}
    k = pd.read_csv(raw / "kraken_ohlcvt" / "USDTUSD_60.csv", header=None, names=["t", "o", "h", "l", "c", "v", "n"])
    k.index = pd.to_datetime(k["t"], unit="s", utc=True)
    kr = np.log(k["c"][k["c"] > 0]).reindex(hourly_index())
    usdt = read_krw(raw / "bithumb" / "KRW-USDT_60m.csv")
    return {"krw": krw, "usd": usd, "fx": read_fx(raw / "fred" / "DEXKOUS.csv"), "usdt_krw": usdt, "kraken_usdt": kr}


# ---- statistics -------------------------------------------------------------------------------------------------------

def gaps_hourly(krw: dict[str, pd.Series], usd: dict[str, pd.Series], fxh: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({c: 1e4 * (krw[c] - usd[c] - fxh) for c in krw if c in usd})


def to_daily(h: pd.DataFrame, min_hours: int = MIN_HOURS) -> pd.DataFrame:
    g = h.groupby(h.index.floor("D"))
    return g.median().where(g.count() >= min_hours)


def hour_snapshot(h: pd.DataFrame, hour: int = 16) -> pd.DataFrame:
    s = h[h.index.hour == hour]
    s.index = s.index.floor("D")
    return s


def pair_corrs(d: pd.DataFrame, cols=CORE, diff: bool = False) -> dict[str, float]:
    x = d[list(cols)].dropna()
    if diff:
        x = x.diff().dropna()
    c = x.corr()
    return {f"{a}-{b}": float(c.loc[a, b]) for i, a in enumerate(cols) for b in cols[i + 1:]}


def loo_r2(d: pd.DataFrame, cols=CORE) -> dict[str, float]:
    x = d[list(cols)].dropna()
    out = {}
    for c in cols:
        o = x.drop(columns=c).mean(axis=1)
        out[c] = float(np.corrcoef(o, x[c])[0, 1] ** 2) if len(x) > 2 else float("nan")
    return out


def pc1_share(d: pd.DataFrame, cols=CORE) -> float:
    x = d[list(cols)].dropna()
    if len(x) < 3:
        return float("nan")
    return float(np.linalg.eigvalsh(x.corr().to_numpy())[-1] / len(cols))


def block_ci(df: pd.DataFrame, fn, freq: str, draws: int = DRAWS, seed: int = SEED) -> list[float] | None:
    blocks = [g.to_numpy() for _, g in df.groupby(df.index.tz_localize(None).to_period(freq))]
    if len(blocks) < 5:
        return None
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(draws):
        m = np.concatenate([blocks[i] for i in rng.integers(0, len(blocks), len(blocks))])
        out.append(fn(m))
    lo, hi = np.nanpercentile(out, [2.5, 97.5])
    return [float(lo), float(hi)]


def _med_pair_corr(m: np.ndarray) -> float:
    c = np.corrcoef(m, rowvar=False)
    return float(np.median(c[np.triu_indices(c.shape[0], 1)]))


def common_block(d: pd.DataFrame, cols=CORE) -> dict[str, Any]:
    """H1 statistics for one daily frame (levels and changes)."""
    x = d[list(cols)].dropna()
    out: dict[str, Any] = {"days": int(len(x))}
    if len(x) < 10:
        return out
    pc = pair_corrs(d, cols)
    out.update({"corr_levels": pc, "min_corr_levels": min(pc.values()), "median_corr_levels": float(np.median(list(pc.values()))),
                "median_corr_levels_ci95_week": block_ci(x, _med_pair_corr, "W"),
                "corr_changes": pair_corrs(d, cols, diff=True), "loo_r2": loo_r2(d, cols), "pc1_share": pc1_share(d, cols)})
    out["min_loo_r2"] = min(out["loo_r2"].values())
    lo = out["median_corr_levels_ci95_week"]
    out["H1_holds"] = bool(out["min_corr_levels"] >= H1_CORR and out["min_loo_r2"] >= H1_R2 and lo is not None and lo[0] >= H1_LOWER)
    return out


def _ols(x, y) -> float:
    xc = x - x.mean()
    den = float((xc * xc).sum())
    return float((xc * (y - y.mean())).sum() / den) if den > 0 else float("nan")


def _iv(z, x, y) -> float:
    zc = z - z.mean()
    den = float((zc * (x - x.mean())).sum())
    return float((zc * (y - y.mean())).sum() / den) if abs(den) > 0 else float("nan")


def anchor_block(df: pd.DataFrame, freq: str = "D") -> dict[str, Any]:
    """df columns L, D, X, Z (instrument), hourly. Slopes of D and D - X on L, OLS and IV, with block-bootstrap intervals."""
    df = df.dropna()
    out: dict[str, Any] = {"n": int(len(df))}
    if len(df) < 48 or df["L"].std() == 0:
        return out
    df = df.assign(A=df["D"] - df["X"])
    def est(cols, fn):
        d = df[list(cols)]
        return {"est": float(fn(d.to_numpy())), "ci95": block_ci(d, fn, freq)}
    out["slope_D_on_L_ols"] = est(("L", "D"), lambda m: _ols(m[:, 0], m[:, 1]))
    out["slope_D_minus_X_on_L_ols"] = est(("L", "A"), lambda m: _ols(m[:, 0], m[:, 1]))
    out["slope_D_minus_X_on_L_iv"] = est(("Z", "L", "A"), lambda m: _iv(m[:, 0], m[:, 1], m[:, 2]))
    out["first_stage_L_on_Z"] = float(_ols(df["Z"].to_numpy(), df["L"].to_numpy()))
    out["sd_L"], out["sd_D"], out["sd_X"] = float(df["L"].std()), float(df["D"].std()), float(df["X"].std())
    out["median_L"], out["median_D"], out["median_X"] = float(df["L"].median()), float(df["D"].median()), float(df["X"].median())
    ci = out["slope_D_minus_X_on_L_ols"]["ci95"]
    if ci is None:
        out["reading"] = "uninformative"
    elif ci[0] <= 1 <= ci[1] and not ci[0] <= 0 <= ci[1]:
        out["reading"] = "unit"
    elif ci[0] <= 0 <= ci[1] and not ci[0] <= 1 <= ci[1]:
        out["reading"] = "demand"
    elif ci[0] <= 0 <= ci[1] and ci[0] <= 1 <= ci[1]:
        out["reading"] = "uninformative (interval contains 0 and 1)"
    else:
        out["reading"] = "mixed (interval excludes 0 and 1)"
    return out


def premium_summary(d: pd.DataFrame) -> dict[str, Any]:
    out = {}
    for c in d.columns:
        x = d[c].dropna()
        out[c] = {"days": int(len(x)), "median_bps": float(x.median()), "p05": float(x.quantile(.05)), "p95": float(x.quantile(.95)),
                  "max": float(x.max()), "min": float(x.min())} if len(x) else {"days": 0}
    return out


def run(data: dict[str, Any]) -> dict[str, Any]:
    fxh = fx_hourly(data["fx"])
    h = gaps_hourly(data["krw"], data["usd"], fxh)
    d = to_daily(h)
    res: dict[str, Any] = {"method": __doc__.strip().split("\n\n")[0], "prereg": "docs/kimchi/PREREG.md",
                           "bootstrap": {"draws": DRAWS, "seed": SEED, "min_hours_per_day": MIN_HOURS}}
    res["windows"] = {}
    for n, (lo, hi) in WINDOWS.items():
        w = d.loc[lo:hi]
        res["windows"][n] = {"range": [lo, hi], "premium": premium_summary(w), "common": common_block(w),
                             "common_5coins": common_block(w, ALL)}
        snap = hour_snapshot(h).loc[lo:hi]
        res["windows"][n]["sens_16utc_snapshot"] = common_block(snap)
        h_lag = to_daily(gaps_hourly(data["krw"], data["usd"], fx_hourly(data["fx"], 1))).loc[lo:hi]
        res["windows"][n]["sens_fx_lag1"] = common_block(h_lag)
    res["by_year"] = {}
    for y in range(2017, 2024):
        w = d.loc[f"{y}-01-01":f"{y}-12-31"]
        res["by_year"][str(y)] = {"premium": premium_summary(w[list(CORE)]), "common": common_block(w)}
    res["H1"] = {"windows": list(HIGH), "supported": all(res["windows"][k]["common"].get("H1_holds", False) for k in HIGH),
                 "thresholds": {"pair_corr": H1_CORR, "ci_lower": H1_LOWER, "loo_r2": H1_R2}}
    # anchor, Bithumb USDT/KRW 2023-12-08..2023-12-31 (calm window); not testable in E1/E2
    lo, hi = ANCHOR_WINDOW
    D = 1e4 * (data["usdt_krw"] - fxh)
    X = 1e4 * data["kraken_usdt"]
    L = h[list(CORE)].mean(axis=1, skipna=False)
    frame = pd.DataFrame({"L": L, "D": D, "X": X, "Z": h["BCH"]}).loc[lo:hi]
    res["anchor"] = {"window": [lo, hi], "usdt_krw_first_candle": str(data["usdt_krw"].dropna().index.min()),
                     "note": "USDT/KRW (Bithumb) exists from 2023-12; Upbit from 2024-06. Not testable in E1, E2 (no USDT/KRW).",
                     "mean3_vs_bch_iv": anchor_block(frame),
                     "btc_only_vs_eth_iv": anchor_block(pd.DataFrame({"L": h["BTC"], "D": D, "X": X, "Z": h["ETH"]}).loc[lo:hi]),
                     "fx_lag1_mean3": anchor_block(pd.DataFrame({"L": gaps_hourly(data["krw"], data["usd"], fx_hourly(data["fx"], 1))[list(CORE)].mean(axis=1, skipna=False),
                                                                 "D": 1e4 * (data["usdt_krw"] - fx_hourly(data["fx"], 1)), "X": X, "Z": h["BCH"]}).loc[lo:hi]),
                     "kraken_usdt_X_hours": int(X.loc[lo:hi].notna().sum())}
    res["anchor"]["H2_high_premium_windows"] = "NOT TESTABLE: no USDT/KRW price before 2023-12 on Upbit or Bithumb"
    return res


def main() -> None:
    res = run(load_all())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(res, indent=1) + "\n")
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
