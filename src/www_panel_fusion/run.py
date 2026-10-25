"""Steps 2-3: official versus anchor-corrected conversion on the currency panel (autoresearch/program_panel_fusion.md, commit e257447).

    uv run python -m www_panel_fusion.run        # writes reports/panel_fusion/results.json

Error e = 1e4 (method - truth) in bps, truth = Kraken BTC/USD hourly close.
  O : log P_v(BTC/F) - log(official F per USD)               ->  e_O = L - 1e4 log(official)
  A : log P_v(BTC/F) - log P_v(USDT/F) + log P_ext(USDT/USD) ->  e_A = L - D + X_ext
with L, D from ``www_panel`` (L = 1e4 [log P_v(BTC/F) - log P_Kraken(BTC/USD)], D = 1e4 log P_v(USDT/F)).
External USDT/USD, hour by hour: Bitstamp (2022-04+), else Binance.US (2019-09+), else Kraken.
MO / MA: median over the units observed in the hour of the O / A log prices (equivalently of e_O / e_A, since truth is common).
Mechanical choices not spelled out in the pre-registration: the sample is the unit-hours (from the panel's stress and calm months) with
L, D, an official rate and an external USDT/USD all present, so O and A are paired; MO and MA use the units in that sample; the
bootstrap resamples UTC days with replacement (pooled over units; per unit for the per-unit endpoint; a fresh generator seeded 20261025
for each endpoint), and the 95% interval is the 2.5% to 97.5% percentile range, with the "upper 95% bound" being its upper end;
"hours >= 50 bps" counts |e| >= 50.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from www_panel.classify import OUT as MONTHS
from www_panel.data import log_bps
from www_panel.run import alt_x, build_panel

from .fx import hourly_official, read_ecb

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "reports" / "panel_fusion" / "results.json"
SEED, DRAWS, EPS_BPS, BIG_BPS = 20261025, 1000, 1.0, 50.0
FIATS = ("TRY", "BRL", "ZAR", "RUB", "KRW")  # ECB-covered; ARS, NGN, UAH are excluded by the pre-registration
SOURCES = ("bitstamp", "binance_us", "kraken")


def external_usdt(panel: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Hour-by-hour external USDT/USD in bps: Bitstamp, else Binance.US, else Kraken. Returns (value, source label)."""
    cols = {"bitstamp": panel["XS"], "binance_us": panel["XB"], "kraken": panel["X"]}
    val = cols["bitstamp"].copy()
    src = pd.Series(np.where(val.notna(), "bitstamp", ""), index=panel.index)
    for name in SOURCES[1:]:
        miss = val.isna()
        val = val.where(~miss, cols[name])
        src = src.where(~miss, np.where(cols[name].notna(), name, ""))
    return val, src.where(val.notna(), "")


def build_sample(months: dict | None = None, ecb: pd.DataFrame | None = None, panel: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per unit-hour: unit, fiat, venue, e_O, e_A (bps), X source. Only ECB-covered units, hours with all inputs present."""
    months = months if months is not None else json.loads(MONTHS.read_text())
    ecb = ecb if ecb is not None else read_ecb()
    if panel is None:
        panel = build_panel(months, {"XB": alt_x("binance_us"), "XS": alt_x("bitstamp")})
    panel = panel[panel["fiat"].isin(FIATS)].copy()
    return sample_from_panel(panel, ecb)


def sample_from_panel(panel: pd.DataFrame, ecb: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for fiat, g in panel.groupby("fiat", sort=True):
        off = hourly_official(ecb, fiat, g.index.unique().sort_values())
        g = g.assign(off=log_bps(off).reindex(g.index).to_numpy())
        g["x_ext"], g["x_src"] = external_usdt(g)
        g = g.dropna(subset=["L", "D", "off", "x_ext"])
        parts.append(pd.DataFrame({"unit": g["unit"], "fiat": g["fiat"], "venue": g["venue"], "e_O": g["L"] - g["off"],
                                   "e_A": g["L"] - g["D"] + g["x_ext"], "x_src": g["x_src"]}))
    return pd.concat(parts).sort_index()


# ---- statistics --------------------------------------------------------------------------------------------------------------

def logdiff(e_a: np.ndarray, e_o: np.ndarray) -> np.ndarray:
    return np.log(np.abs(e_a) + EPS_BPS) - np.log(np.abs(e_o) + EPS_BPS)


def day_bootstrap(d: np.ndarray, days: pd.DatetimeIndex) -> dict:
    """Mean of d with a day-block bootstrap (resample UTC days with replacement)."""
    uniq, inv = np.unique(days.to_numpy(), return_inverse=True)
    s, n = np.bincount(inv, weights=d), np.bincount(inv).astype(float)
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(uniq), size=(DRAWS, len(uniq)))
    draws = s[idx].sum(axis=1) / n[idx].sum(axis=1)
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return {"mean": float(d.mean()), "lo": float(lo), "hi": float(hi), "n_hours": int(len(d)), "n_days": int(len(uniq)), "success": bool(hi < 0)}


def err_summary(e: np.ndarray) -> dict:
    a = np.abs(e)
    return {"mae": float(a.mean()), "p95": float(np.percentile(a, 95)), "hours_ge_50": int((a >= BIG_BPS).sum()), "mean_signed": float(e.mean())}


def fused(sample: pd.DataFrame) -> pd.DataFrame:
    g = sample.groupby(level=0)
    return pd.DataFrame({"e_MO": g["e_O"].median(), "e_MA": g["e_A"].median(), "n_units": g.size()})


def evaluate(sample: pd.DataFrame) -> dict:
    day = lambda idx: idx.floor("D")  # noqa: E731
    eo, ea = sample["e_O"].to_numpy(), sample["e_A"].to_numpy()
    res: dict = {"design": {"seed": SEED, "draws": DRAWS, "eps_bps": EPS_BPS, "big_bps": BIG_BPS, "truth": "Kraken XBTUSD hourly close",
                            "fiats": list(FIATS), "months_file": "reports/panel/months.json"}}
    prim = day_bootstrap(logdiff(ea, eo), day(sample.index))
    res["primary"] = {**prim, "O": err_summary(eo), "A": err_summary(ea), "rule": "success iff the upper 95% bound of the pooled mean of log(|e_A|+1)-log(|e_O|+1) is below 0",
                      "outcome": "success: anchor-corrected conversion has smaller log error than official conversion" if prim["success"]
                      else "fail: official conversion was as good as anchor-corrected conversion for these units"}
    res["x_source_hours"] = {s: int((sample["x_src"] == s).sum()) for s in SOURCES}
    res["units"] = {}
    for unit, g in sample.groupby("unit", sort=True):
        o, a = g["e_O"].to_numpy(), g["e_A"].to_numpy()
        ms, me = g.index.min(), g.index.max()
        res["units"][unit] = {"fiat": g["fiat"].iloc[0], "venue": g["venue"].iloc[0], "first": ms.isoformat(), "last": me.isoformat(),
                              "log_error_diff": day_bootstrap(logdiff(a, o), day(g.index)),
                              "O": err_summary(o), "A": err_summary(a), "mae_ratio_A_over_O": float(np.abs(a).mean() / np.abs(o).mean())}
    res["pooled_mae_ratio_A_over_O"] = float(np.abs(ea).mean() / np.abs(eo).mean())
    ratios = sorted(u["mae_ratio_A_over_O"] for u in res["units"].values())
    res["median_unit_mae_ratio_A_over_O"] = float(np.median(ratios))
    res["median_unit_mae"] = {"O": float(np.median([u["O"]["mae"] for u in res["units"].values()])),
                              "A": float(np.median([u["A"]["mae"] for u in res["units"].values()]))}
    f = fused(sample)
    mo, ma = f["e_MO"].to_numpy(), f["e_MA"].to_numpy()
    res["fused"] = {"n_hours": int(len(f)), "mean_units_per_hour": float(f["n_units"].mean()), "MO": err_summary(mo), "MA": err_summary(ma),
                    "log_error_diff_MA_vs_MO": day_bootstrap(logdiff(ma, mo), day(f.index)),
                    "hours_by_unit_count": {str(k): int(v) for k, v in f["n_units"].value_counts().sort_index().items()}}
    res["fused"]["multi_unit_hours_only"] = None
    multi = f[f["n_units"] >= 2]
    if len(multi):
        res["fused"]["multi_unit_hours_only"] = {"n_hours": int(len(multi)), "MO": err_summary(multi["e_MO"].to_numpy()), "MA": err_summary(multi["e_MA"].to_numpy()),
                                                 "log_error_diff_MA_vs_MO": day_bootstrap(logdiff(multi["e_MA"].to_numpy(), multi["e_MO"].to_numpy()), day(multi.index))}
    res["sample"] = {"n_unit_hours": int(len(sample)), "n_units": int(sample["unit"].nunique()), "first": sample.index.min().isoformat(), "last": sample.index.max().isoformat()}
    return res


def run() -> dict:
    return evaluate(build_sample())


def main() -> None:
    res = run()
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"sample": res["sample"], "primary": res["primary"], "fused": res["fused"]["log_error_diff_MA_vs_MO"]}, indent=1))


if __name__ == "__main__":
    main()
