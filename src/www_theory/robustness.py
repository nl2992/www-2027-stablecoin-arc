"""Robustness grid for the anchored test on Bitfinex, plus a falsification check of assumption A3.

The grid was fixed before it was run (decision of 2026-10-22, in response to reviewers who noted that the window, anchor,
instrument and reference choices were single analyst choices).  Every cell is netted-USDT-anchor lambda-hat from three
estimators, each with a HAC (Andrews bandwidth) 95% interval and a moving-block-bootstrap 95% interval:

  windows      stress (2018-11-27..2019-05-31, headline) | 2018-11-27..2019-03-31 | 2019-01-01..2019-05-31 | 2019 | stress +/- 30 days
  instruments  eth | eth_ltc | eth_ltc_bch_etc (headline) | lags12 (the first two hourly lags of L only)
  reference    bitstamp (headline) | coinbase | mid (mean of the two log prices, i.e. the median of two) for L = Bitfinex BTC - ref BTC
  X            kraken hourly median of traded-minute closes (headline) | kraken hourly last close (60-minute file)
  block        24 h (1 day) | 168 h (1 week, headline) | 720 h (1 month)

Estimators.  OLS: Y on L (HAC).  IV: 2SLS with the whole instrument set (HAC sandwich).  GMM: two-step efficient GMM (the
headline estimator).  With one instrument IV and GMM coincide.  The three ETH-based sets use one sample per (window, reference, X),
the complete cases of the largest set (so differences across sets are not sample differences, and the headline cells reproduce
gmm_applied.json); the lags set uses the complete cases of L, D, X and its lags.  The instruments E, LTC, ETC and BCH are held fixed
at the headline definitions (Bitfinex vs Coinbase) whatever reference is used for L.

Bootstrap.  Moving blocks of the stated length are drawn with replacement from the overlapping blocks of the compacted sample
(hours with a missing series are dropped first, as in gmm_applied.json), truncated to n, 999 draws, seed 20261022.  The
estimating equations are linear, so each draw re-solves the estimator from the resampled moment means with the weight matrix held
at its full-sample value (a fixed-weight bootstrap: 2SLS weight for IV, the efficient second-step weight for GMM); intervals
are percentile intervals.  gmm_applied.json instead uses the Andrews-style plug-in block length (20 hours) and the just-identified
estimator for its single reported interval, so only the 1-week cells are comparable to the "1 week" headline in the text.

A3 falsification.  Assumption A3 says Kraken's measurement error xi is independent of the other shocks and lets x itself co-move
with the BTC offset c.  A necessary look: if Kraken's USDT deviation X responded strongly to Bitfinex's offset L (reverse
direction), the exclusion of xi from c would be in doubt.  X is regressed on L in the stress window on the headline sample.

    uv run python -m www_theory.robustness      # writes reports/theory/robustness.json
"""

from __future__ import annotations

import itertools
import json
from typing import Any

import numpy as np
import pandas as pd

from . import data, gmm

REPO = data.REPO
OUT = REPO / "reports" / "theory" / "robustness.json"
APPLIED = REPO / "reports" / "theory" / "gmm_applied.json"
DRAWS, SEED = 999, 20261022
WINDOWS = {"stress": ("2018-11-27", "2019-05-31"), "stress_to_mar": ("2018-11-27", "2019-03-31"),
           "jan_to_may_2019": ("2019-01-01", "2019-05-31"), "year_2019": ("2019-01-01", "2019-12-31"),
           "stress_pm30d": ("2018-10-28", "2019-06-30")}
INSTRUMENTS = {"eth": ["E"], "eth_ltc": ["E", "LTC"], "eth_ltc_bch_etc": ["E", "LTC", "BCH", "ETC"], "lags12": ["L_l1", "L_l2"]}
ETH_BASED = ("E", "LTC", "BCH", "ETC")
REFERENCES = ("bitstamp", "coinbase", "mid")
XKINDS = ("median", "last")
BLOCKS = {"day": 24, "week": 168, "month": 720}
HEADLINE = {"window": "stress", "instruments": "eth_ltc_bch_etc", "reference": "bitstamp", "x": "median", "block": "week"}
ESTIMATORS = ("ols", "iv", "gmm")
FACTORS = ("window", "instruments", "reference", "x", "block")


# ---- data ----------------------------------------------------------------------------------------------------------------

def build_frame() -> pd.DataFrame:
    """Hourly frame (bps) over 2018-10-28..2019-12-31 with every series the grid needs."""
    from www_auto import anchor_external as ae

    s = ae.load_series()["series"]
    panel = pd.read_parquet(data.PANEL)
    k60 = ae._read(ae.KRAKEN / "USDTUSD_60.csv")
    k60 = k60[k60["c"] > 0]
    last = np.log(k60["c"]).reindex(s["kraken|USDT"].index)
    bfx = s["bitfinex|BTC"]
    f = pd.DataFrame({"D": 1e4 * s["bitfinex|USDT"], "X_median": 1e4 * s["kraken|USDT"], "X_last": 1e4 * last,
                      "L_bitstamp": 1e4 * (bfx - s["bitstamp|BTC"]), "L_coinbase": 1e4 * (bfx - s["coinbase|BTC"]),
                      "L_mid": 1e4 * (bfx - 0.5 * (s["bitstamp|BTC"] + s["coinbase|BTC"])),
                      "E": 1e4 * (s["bitfinex|ETH"] - s["coinbase|ETH"])})
    for a in data.ALTS:
        f[a] = 1e4 * (panel[f"bitfinex|{a}"] - panel[f"coinbase|{a}"]).reindex(f.index)
    return data._cut(f, "2018-10-28", "2019-12-31")


def sample(f: pd.DataFrame, window: str, instruments: str, reference: str, x: str) -> pd.DataFrame:
    """Complete-case frame with columns L, D, X and the instruments of the set, in the window."""
    g = data._cut(f, *WINDOWS[window]).rename(columns={f"L_{reference}": "L", f"X_{x}": "X"})
    g = g[["L", "D", "X", *ETH_BASED]]
    if instruments == "lags12":
        g = data.add_lags(g[["L", "D", "X"]], "L", (1, 2))
        return g.dropna()
    return g.dropna()[["L", "D", "X", *INSTRUMENTS[instruments]]]


# ---- estimators ----------------------------------------------------------------------------------------------------------

def _moments(y: np.ndarray, x: np.ndarray, Z: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """a_t, B_t and the first-step weight of  y = c + lam x  with instruments (1, Z): as in gmm.iv."""
    Zc = gmm._with_const(Z)
    n = len(y)
    return Zc * y[:, None], np.stack([Zc * x[:, None], Zc], axis=2), np.linalg.inv(Zc.T @ Zc / n)


def _weight(a: np.ndarray, B: np.ndarray, W1: np.ndarray, efficient: bool) -> np.ndarray:
    """W1 for IV; for GMM the inverse HAC long-run variance of the first-step moments (as gmm.gmm_linear's step-2 weight)."""
    if not efficient or a.shape[1] == B.shape[2]:
        return W1
    b1 = gmm._solve(B.mean(0), a.mean(0), W1)
    S, _ = gmm.hac(a - np.einsum("tqp,p->tq", B, b1), "auto")
    return np.linalg.pinv(S, rcond=1e-12)


def block_means(M: np.ndarray, b: int, draws: int, rng: np.random.Generator) -> np.ndarray:
    """(draws, k) means of moving-block resamples of the rows of M (blocks of b, truncated to n); same draws as gmm.mbb_indices."""
    n = M.shape[0]
    nb = -(-n // b)
    rem = n - (nb - 1) * b
    starts = rng.integers(0, n - b + 1, size=(draws, nb))
    cs = np.vstack([np.zeros((1, M.shape[1])), np.cumsum(M, axis=0)])
    tot = (cs[starts[:, :-1] + b] - cs[starts[:, :-1]]).sum(1) + (cs[starts[:, -1] + rem] - cs[starts[:, -1]])
    return tot / n


def boot_lams(a: np.ndarray, B: np.ndarray, W: np.ndarray, b: int, draws: int = DRAWS, seed: int = SEED) -> np.ndarray:
    n, q, p = B.shape
    rng = np.random.default_rng(seed)
    M = block_means(np.concatenate([a, B.reshape(n, q * p)], axis=1), b, draws, rng)
    ab, Bb = M[:, :q], M[:, q:].reshape(draws, q, p)
    BtW = np.einsum("dqp,qr->dpr", Bb, W)
    lam = np.linalg.solve(np.einsum("dpr,drs->dps", BtW, Bb), np.einsum("dpr,dr->dp", BtW, ab)[..., None])[:, 0, 0]
    return lam[np.isfinite(lam)]


def _pct(v: np.ndarray) -> list[float]:
    return [float(x) for x in np.percentile(v, [2.5, 97.5])]


def estimate(h: pd.DataFrame, instruments: str, blocks: dict[str, int], draws: int = DRAWS) -> dict[str, Any]:
    """OLS, IV and GMM lambda-hat for one sample, with HAC intervals and a bootstrap interval for each block length."""
    y, L = (h["D"] - h["X"]).to_numpy(), h["L"].to_numpy()
    Z = h[INSTRUMENTS[instruments]].to_numpy()
    fits = {"ols": gmm.ols(y, L), "iv": gmm.iv(y, L, Z, two_step=False), "gmm": gmm.iv(y, L, Z, two_step=True)}
    data_: dict[str, Any] = {"n": int(len(h))}
    a_o, B_o, W_o = _moments(y, L, L[:, None])
    a_z, B_z, W_z = _moments(y, L, Z)
    mom = {"ols": (a_o, B_o, W_o), "iv": (a_z, B_z, _weight(a_z, B_z, W_z, False)), "gmm": (a_z, B_z, _weight(a_z, B_z, W_z, True))}
    for name, r in fits.items():
        lo, hi = r.ci(0)
        e: dict[str, Any] = {"lam": float(r.beta[0]), "se": float(r.se[0]), "hac_ci95": [lo, hi], "hac_lags": int(r.lags), "boot": {}}
        if name == "gmm":
            e.update({"J": r.J, "J_df": r.J_df, "J_p": None if r.J_df == 0 else r.J_p})
        for bn, bl in blocks.items():
            e["boot"][bn] = {"block_hours": bl, "ci95": _pct(boot_lams(*mom[name], bl, draws))}
        data_[name] = e
    return data_


# ---- grid, summary, A3 -----------------------------------------------------------------------------------------------------

def grid(f: pd.DataFrame, draws: int = DRAWS) -> list[dict[str, Any]]:
    cells = []
    for w, ins, ref, x in itertools.product(WINDOWS, INSTRUMENTS, REFERENCES, XKINDS):
        h = sample(f, w, ins, ref, x)
        res = estimate(h, ins, BLOCKS, draws)
        for bn, bl in BLOCKS.items():
            cell = {"window": w, "instruments": ins, "reference": ref, "x": x, "block": bn, "block_hours": bl, "n": res["n"]}
            for est in ESTIMATORS:
                r = res[est]
                cell[est] = {"lam": r["lam"], "hac_ci95": r["hac_ci95"], "boot_ci95": r["boot"][bn]["ci95"]}
                if est == "gmm":
                    cell[est].update({"J": r["J"], "J_df": r["J_df"], "J_p": r["J_p"]})
            cells.append(cell)
    return cells


def summarize(cells: list[dict[str, Any]]) -> dict[str, Any]:
    def stats(sub: list[dict[str, Any]], est: str) -> dict[str, Any]:
        lam = np.array([c[est]["lam"] for c in sub])
        boot = [c[est]["boot_ci95"] for c in sub]
        hac = [c[est]["hac_ci95"] for c in sub]
        return {"cells": len(sub), "min": float(lam.min()), "median": float(np.median(lam)), "max": float(lam.max()),
                "share_boot_ci_contains_1": float(np.mean([lo <= 1 <= hi for lo, hi in boot])),
                "share_boot_ci_excludes_0": float(np.mean([not lo <= 0 <= hi for lo, hi in boot])),
                "share_hac_ci_contains_1": float(np.mean([lo <= 1 <= hi for lo, hi in hac])),
                "share_hac_ci_excludes_0": float(np.mean([not lo <= 0 <= hi for lo, hi in hac]))}

    out: dict[str, Any] = {"overall": {e: stats(cells, e) for e in ESTIMATORS}, "gmm_by_factor": {}}
    levels = {"window": list(WINDOWS), "instruments": list(INSTRUMENTS), "reference": list(REFERENCES), "x": list(XKINDS), "block": list(BLOCKS)}
    for fac in FACTORS:
        out["gmm_by_factor"][fac] = {lv: stats([c for c in cells if c[fac] == lv], "gmm") for lv in levels[fac]}
    out["outside_0.9_1.1"] = [{**{k: c[k] for k in FACTORS}, "n": c["n"], **{e: c[e]["lam"] for e in ESTIMATORS}}
                              for c in cells if any(not 0.9 <= c[e]["lam"] <= 1.1 for e in ESTIMATORS)]
    out["outside_0.9_1.1_gmm_cells"] = sum(not 0.9 <= c["gmm"]["lam"] <= 1.1 for c in cells)
    out["gmm_boot_ci_excludes_1_count"] = sum(not c["gmm"]["boot_ci95"][0] <= 1 <= c["gmm"]["boot_ci95"][1] for c in cells)
    return out


def headline(f: pd.DataFrame, draws: int = DRAWS) -> dict[str, Any]:
    """The headline cell (stress, 4 instruments, Bitstamp, Kraken median) with the J test and instrument list as used."""
    h = sample(f, HEADLINE["window"], HEADLINE["instruments"], HEADLINE["reference"], HEADLINE["x"])
    res = estimate(h, HEADLINE["instruments"], {"week": BLOCKS["week"]}, draws)
    g = res["gmm"]
    q = h.shape[1] - 3 + 1                      # instruments plus the constant
    return {"cell": HEADLINE, "n": res["n"], "instruments": {"E": "Bitfinex ETH vs Coinbase ETH, hourly median of traded minutes",
            "LTC": "Bitfinex vs Coinbase LTC, hourly last close (UNIT-TD panel)", "BCH": "Bitfinex vs Coinbase BCH, hourly last close (UNIT-TD panel)",
            "ETC": "Bitfinex vs Coinbase ETC, hourly last close (UNIT-TD panel)"}, "instrument_columns": list(h.columns[3:]),
            "moment_conditions": q, "parameters": 2, "anchors": 1, "J_df_formula": "K*m - 1 with K = 1 anchor, m = 4 instruments (5 moments with the constant, 2 parameters: lambda and the intercept)",
            "J": g["J"], "J_df": g["J_df"], "J_p": g["J_p"], "lam": g["lam"], "hac_ci95": g["hac_ci95"],
            "boot_ci95_week": g["boot"]["week"]["ci95"]}


def a3_check(f: pd.DataFrame, draws: int = DRAWS) -> dict[str, Any]:
    """Regress Kraken's USDT deviation X on Bitfinex's L in the stress window (headline sample): slope with HAC and block-bootstrap CIs."""
    h = sample(f, "stress", "eth_ltc_bch_etc", "bitstamp", "median")
    out: dict[str, Any] = {"window": list(WINDOWS["stress"]), "n": int(len(h)), "sd_L_bps": float(h["L"].std(ddof=1)),
                           "sd_X_bps": float(h["X"].std(ddof=1)), "corr_X_L": float(h["X"].corr(h["L"]))}
    specs = {"contemporaneous": (h["X"].to_numpy(), h["L"].to_numpy())}
    lag = data.add_lags(h[["L", "X"]], "L", (1,)).dropna()
    specs["X_on_L_lag1h"] = (lag["X"].to_numpy(), lag["L_l1"].to_numpy())
    for name, (X, L) in specs.items():
        r = gmm.ols(X, L)
        lo, hi = r.ci(0)
        a, B, W = _moments(X, L, L[:, None])
        b = {bn: _pct(boot_lams(a, B, W, bl, draws)) for bn, bl in BLOCKS.items()}
        out[name] = {"n": int(len(X)), "slope": float(r.beta[0]), "se": float(r.se[0]), "hac_ci95": [lo, hi], "hac_lags": int(r.lags),
                     "boot_ci95": b, "p_zero_hac": r.wald(0, 0.0)[1],
                     "slope_x_sd_L_bps": float(r.beta[0] * np.std(L, ddof=1)), "r2": float(np.corrcoef(X, L)[0, 1] ** 2)}
    return out


def check_against_applied(f: pd.DataFrame) -> dict[str, float]:
    """The headline-window Bitstamp/Kraken-median cells must reproduce gmm_applied.json (lambda, n, J) to rounding."""
    app = json.loads(APPLIED.read_text())["bitfinex"]["specs"]
    diffs = {}
    for ins, key in (("eth", "netted|eth"), ("eth_ltc", "netted|eth_ltc"), ("eth_ltc_bch_etc", "netted|eth_ltc_bch_etc")):
        h = sample(f, "stress", ins, "bitstamp", "median")
        y, L = (h["D"] - h["X"]).to_numpy(), h["L"].to_numpy()
        r = gmm.iv(y, L, h[INSTRUMENTS[ins]].to_numpy())
        diffs[ins] = max(abs(r.beta[0] - app[key]["lam"]), abs(r.J - app[key]["J"]), abs(len(h) - app[key]["n"]))
    return diffs


def build(draws: int = DRAWS) -> dict[str, Any]:
    f = build_frame()
    cells = grid(f, draws)
    chk = check_against_applied(f)
    if draws == DRAWS and max(chk.values()) > 1e-8:
        raise AssertionError(f"headline cells do not reproduce gmm_applied.json: {chk}")
    return {"method": "Robustness grid for the anchored Bitfinex test, fixed before running; see www_theory/robustness.py.",
            "grid": {"windows": {k: list(v) for k, v in WINDOWS.items()}, "instrument_sets": INSTRUMENTS, "references": list(REFERENCES),
                     "x": {"median": "Kraken hourly median of traded-minute closes (headline)", "last": "Kraken 60-minute-file close"},
                     "blocks_hours": BLOCKS, "headline": HEADLINE, "draws": draws, "seed": SEED,
                     "reference_mid": "mean of the Bitstamp and Coinbase log prices (the median of two)",
                     "cells": len(cells)},
            "reproduces_gmm_applied_max_abs_diff": chk, "headline": headline(f, draws), "summary": summarize(cells),
            "a3_falsification": a3_check(f, draws), "cells": cells}


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), indent=1) + "\n")
    print(f"WROTE {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
