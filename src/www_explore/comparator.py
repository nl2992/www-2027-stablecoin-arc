"""EXPLORATORY (not pre-registered). Comparator C for the official-rate fusion test. Writes reports/explore/comparator.json.

    uv run python -m www_explore.comparator

Same units, hours and truth (Kraken BTC/USD hourly close) as www_panel_fusion. Errors e = 1e4 (method - truth) in bps:
  O : L - 1e4 log(official)            (official conversion)
  A : L - D + X_ext                    (anchor-corrected conversion)
  C : L - D                            (through the venue's own USDT market, Tether taken as exactly one dollar)
Log-error difference = log(|e_1|+1) - log(|e_2|+1); day-block bootstrap (UTC days), 1,000 draws, seed 20261026; 95% percentile interval.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from www_panel.classify import OUT as MONTHS
from www_panel.data import log_bps
from www_panel.run import alt_x, build_panel
from www_panel_fusion import run as F
from www_panel_fusion.fx import hourly_official, read_ecb

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "reports" / "explore" / "comparator.json"
SEED, DRAWS = 20261026, 1000


def sample_from_panel(panel: pd.DataFrame, ecb: pd.DataFrame) -> pd.DataFrame:
    """The fusion test's unit-hours (identical filter) with e_O, e_A and e_C."""
    parts = []
    for fiat, g in panel[panel["fiat"].isin(F.FIATS)].groupby("fiat", sort=True):
        off = hourly_official(ecb, fiat, g.index.unique().sort_values())
        g = g.assign(off=log_bps(off).reindex(g.index).to_numpy())
        g["x_ext"], _ = F.external_usdt(g)
        g = g.dropna(subset=["L", "D", "off", "x_ext"])
        parts.append(pd.DataFrame({"unit": g["unit"], "fiat": g["fiat"], "e_O": g["L"] - g["off"], "e_A": g["L"] - g["D"] + g["x_ext"], "e_C": g["L"] - g["D"]}))
    return pd.concat(parts).sort_index()


def logdiff(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.log(np.abs(a) + F.EPS_BPS) - np.log(np.abs(b) + F.EPS_BPS)


def day_bootstrap(d: np.ndarray, days: pd.DatetimeIndex) -> dict:
    uniq, inv = np.unique(days.to_numpy(), return_inverse=True)
    s, n = np.bincount(inv, weights=d), np.bincount(inv).astype(float)
    idx = np.random.default_rng(SEED).integers(0, len(uniq), size=(DRAWS, len(uniq)))
    draws = s[idx].sum(axis=1) / n[idx].sum(axis=1)
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return {"mean": float(d.mean()), "lo": float(lo), "hi": float(hi), "n_hours": int(len(d)), "n_days": int(len(uniq))}


def summarise(g: pd.DataFrame) -> dict:
    days = g.index.floor("D")
    a = {k: np.abs(g[f"e_{k}"].to_numpy()) for k in "OAC"}
    out = {"n_hours": int(len(g)), "mae": {k: float(v.mean()) for k, v in a.items()},
           "median_abs": {k: float(np.median(v)) for k, v in a.items()},
           "p95": {k: float(np.percentile(v, 95)) for k, v in a.items()},
           "mean_signed": {k: float(g[f"e_{k}"].mean()) for k in "OAC"},
           "logdiff_A_minus_C": day_bootstrap(logdiff(g["e_A"].to_numpy(), g["e_C"].to_numpy()), days),
           "logdiff_C_minus_O": day_bootstrap(logdiff(g["e_C"].to_numpy(), g["e_O"].to_numpy()), days),
           "mae_ratio_A_over_C": float(a["A"].mean() / a["C"].mean()), "mae_ratio_C_over_O": float(a["C"].mean() / a["O"].mean())}
    return out


def evaluate(sample: pd.DataFrame) -> dict:
    res = {"status": "EXPLORATORY, not pre-registered",
           "design": {"seed": SEED, "draws": DRAWS, "eps_bps": F.EPS_BPS, "truth": "Kraken XBTUSD hourly close", "fiats": list(F.FIATS),
                      "C": "e_C = L - D = log P_v(BTC/F) - log P_v(USDT/F) - log P_Kraken(BTC/USD); Tether = 1 USD",
                      "reading": "negative logdiff means the first method has the smaller error"},
           "pooled": summarise(sample), "units": {}}
    for unit, g in sample.groupby("unit", sort=True):
        res["units"][unit] = summarise(g)
    return res


def run() -> dict:
    panel = build_panel(json.loads(MONTHS.read_text()), {"XB": alt_x("binance_us"), "XS": alt_x("bitstamp")})
    sample = sample_from_panel(panel, read_ecb())
    ref = F.sample_from_panel(panel[panel["fiat"].isin(F.FIATS)].copy(), read_ecb())
    assert len(ref) == len(sample) and np.allclose(ref["e_A"], sample["e_A"]) and np.allclose(ref["e_O"], sample["e_O"]), "sample differs from the fusion test"
    return evaluate(sample)


def main() -> None:
    res = run()
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    p = res["pooled"]
    print(json.dumps({k: p[k] for k in ("n_hours", "mae", "logdiff_A_minus_C", "logdiff_C_minus_O")}, indent=1))
    for u, v in res["units"].items():
        print(u, v["mae"], v["logdiff_A_minus_C"]["mean"], v["logdiff_C_minus_O"]["mean"])


if __name__ == "__main__":
    main()
