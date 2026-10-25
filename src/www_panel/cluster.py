"""POST HOC robustness of the pre-registered panel: inference clustered by currency unit. Writes reports/panel/cluster.json.

    uv run python -m www_panel.cluster

NOT part of the pre-registration (autoresearch/program_panel.md); it changes none of reports/panel/results.json.
Units are the 8 currencies (TRY, BRL, RUB, UAH, ZAR, ARS, NGN, KRW); KRW stacks Upbit and Bithumb. Sample: the pre-registered stress months,
the same hourly rows and per-day sufficient statistics as run.py, so the pooled point estimate reproduces results.json exactly.
  a) cluster bootstrap: resample the 8 units with replacement (2,000 draws, seed 20261025), pooled IV lambda each draw; percentile 95% CI.
  b) leave-one-unit-out pooled IV lambda.
  c) mean and median of the 8 per-unit IV lambdas, t-interval with 7 df.
  d) effective number of independent units, two ways: Kish n_eff = (sum w)^2 / sum w^2 with w_u = unit share of the instrument moment L2*L
     (a pooled IV slope is a weighted mean of unit slopes with these weights); and design effect DEFF = Var(cluster bootstrap) / Var(7-day
     block bootstrap, results.json CI width converted at normal 1.96), n_eff = 8 / DEFF (capped to [1, 8] for reporting only).
  2) wedge size per unit: median |L - monthly median L| and median |L|, bps, over the stress-sample hours.
  3) venue concentration: Binance-only (7 units) and KRW-only pooled IV lambda.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import run as R
from .classify import OUT as MONTHS

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "panel" / "cluster.json"
SEED, DRAWS = 20261025, 2000
T975_DF7 = 2.3646242510102993  # two-sided 95% Student-t quantile, 7 degrees of freedom (no scipy in the environment)
UNITS8 = ("TRY", "BRL", "RUB", "UAH", "ZAR", "ARS", "NGN", "KRW")


def tquant(df: int) -> float:
    """0.975 Student-t quantile for df in 1..30 from the exact table values (df=7 is what the paper uses)."""
    tab = {1: 12.7062047, 2: 4.3026527, 3: 3.1824463, 4: 2.7764451, 5: 2.5705818, 6: 2.4469119, 7: 2.3646243, 8: 2.3060041,
           9: 2.2621572, 10: 2.2281389}
    return tab[df]


def unit_totals(stats: dict[str, np.ndarray], cluster_of: dict[str, str]) -> dict[str, np.ndarray]:
    """Sum the per-day moments [LY, L2Y, L2L, LL, n] within each cluster (venue-units of one currency stack)."""
    out: dict[str, np.ndarray] = {}
    for k, a in stats.items():
        out[cluster_of[k]] = out.get(cluster_of[k], 0.0) + a.sum(axis=0)
    return out


def iv_lam(tot: np.ndarray) -> float:
    return float(tot[1] / tot[2]) if tot[2] else float("nan")


def cluster_bootstrap(totals: dict[str, np.ndarray], draws: int = DRAWS, seed: int = SEED) -> dict:
    keys = sorted(totals)
    mat = np.array([totals[k] for k in keys])
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(keys), size=(draws, len(keys)))
    s = mat[pick].sum(axis=1)  # draws x 5
    with np.errstate(divide="ignore", invalid="ignore"):
        lam = np.where(s[:, 2] != 0, s[:, 1] / s[:, 2], np.nan)
    lam = lam[np.isfinite(lam)]
    return {"lam": iv_lam(mat.sum(axis=0)), "lo": float(np.percentile(lam, 2.5)), "hi": float(np.percentile(lam, 97.5)),
            "sd": float(lam.std(ddof=1)), "draws": int(draws), "seed": int(seed), "n_units": len(keys)}


def leave_one_out(totals: dict[str, np.ndarray]) -> dict[str, float]:
    tot = sum(totals.values())
    return {k: iv_lam(tot - totals[k]) for k in sorted(totals)}


def unit_lambdas(totals: dict[str, np.ndarray]) -> dict[str, float]:
    return {k: iv_lam(totals[k]) for k in sorted(totals)}


def t_summary(lams: dict[str, float]) -> dict:
    v = np.array(list(lams.values()))
    n = len(v)
    se = float(v.std(ddof=1) / np.sqrt(n))
    t = tquant(n - 1)
    return {"n": n, "mean": float(v.mean()), "median": float(np.median(v)), "sd": float(v.std(ddof=1)), "se": se, "t": t,
            "lo": float(v.mean() - t * se), "hi": float(v.mean() + t * se)}


def kish_n(totals: dict[str, np.ndarray]) -> dict:
    w = np.array([totals[k][2] for k in sorted(totals)], float)
    w = w / w.sum()
    return {"n_eff": float(1.0 / np.sum(w ** 2)), "weights": {k: float(x) for k, x in zip(sorted(totals), w)}}


def design_effect(cluster_sd: float, block_lo: float, block_hi: float, n_units: int) -> dict:
    block_sd = (block_hi - block_lo) / (2 * 1.96)
    deff = (cluster_sd / block_sd) ** 2
    return {"block_sd": float(block_sd), "cluster_sd": float(cluster_sd), "deff": float(deff),
            "n_eff": float(min(max(n_units / deff, 1.0), n_units)), "n_eff_uncapped": float(n_units / deff)}


def wedge_sizes(panel, units: tuple[str, ...] = UNITS8) -> dict:
    """Median |L - monthly median L| and median |L| in bps per currency, hours that enter the estimation (L, L2, D, X all present)."""
    g = panel.dropna(subset=["L", "L2", "D", "X"])
    out = {}
    for u in units:
        h = g[g["fiat"] == u]
        dev = (h["L"] - h.groupby(["unit", "month"])["L"].transform("median")).abs()
        out[u] = {"median_abs_dev_from_month_median_bps": float(dev.median()), "median_abs_L_bps": float(h["L"].abs().median()),
                  "n_hours": int(len(h))}
    return out


def run() -> dict:
    months = json.loads(MONTHS.read_text())
    panel = R.build_panel(months, {})
    stress = R.sel(panel, status="stress")
    stats = R.hourly_stats(stress)
    cof = {k: k.split("-")[1] for k in stats}
    totals = unit_totals(stats, cof)
    base = json.loads(R.RESULTS.read_text())
    bs = base["pooled_stress"]["iv"]
    cb = cluster_bootstrap(totals)
    loo = leave_one_out(totals)
    lams = unit_lambdas(totals)
    bin_t = {k: v for k, v in totals.items() if k != "KRW"}
    bin_cb = cluster_bootstrap(bin_t)
    krw = base["by_currency"]["KRW"]["stress"]["iv"]
    res = {
        "label": "POST HOC robustness; not pre-registered; changes nothing in results.json",
        "design": {"units": sorted(totals), "draws": DRAWS, "seed": SEED, "sample": "pre-registered stress months, hourly",
                   "t_df": len(totals) - 1},
        "pooled_point_check": {"this_run": iv_lam(sum(totals.values())), "results_json": bs["lam"]},
        "block_bootstrap_prereg": {"lam": bs["lam"], "lo": bs["lo"], "hi": bs["hi"]},
        "cluster_bootstrap": cb,
        "leave_one_out": loo,
        "leave_one_out_range": {"min": min(loo.values()), "max": max(loo.values()),
                                "min_dropped": min(loo, key=loo.get), "max_dropped": max(loo, key=loo.get)},
        "per_unit_lambda": lams,
        "per_unit_summary": t_summary(lams),
        "effective_units": {"kish": kish_n(totals), "design_effect": design_effect(cb["sd"], bs["lo"], bs["hi"], len(totals))},
        "wedge_bps": wedge_sizes(stress),
        "venue_concentration": {
            "binance_only": {"lam": iv_lam(sum(bin_t.values())), "cluster_lo": bin_cb["lo"], "cluster_hi": bin_cb["hi"],
                             "block_lo": base["by_venue"]["binance"]["stress"]["iv"]["lo"],
                             "block_hi": base["by_venue"]["binance"]["stress"]["iv"]["hi"], "n_units": len(bin_t)},
            "krw_only": {"lam": krw["lam"], "block_lo": krw["lo"], "block_hi": krw["hi"],
                         "upbit": base["by_venue"]["upbit"]["stress"]["iv"], "bithumb": base["by_venue"]["bithumb"]["stress"]["iv"]},
            "note": "7 of 8 units are Binance markets; one external price (Kraken) and one instrument (the ETH gap) throughout",
        },
    }
    return res


def main() -> None:
    res = run()
    OUT.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: res[k] for k in ("pooled_point_check", "cluster_bootstrap", "leave_one_out_range", "per_unit_summary",
                                          "effective_units", "venue_concentration")}, indent=1))
    print(json.dumps(res["wedge_bps"], indent=1))


if __name__ == "__main__":
    main()
