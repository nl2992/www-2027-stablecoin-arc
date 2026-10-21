"""Truth-discovery baselines on real data (answers the "relabelled median" objection); nothing here is tuned.

    uv run python -m www_auto.td_realdata        # writes reports/unit_td/td_realdata.json

Every method is causal: the value at hour t uses data up to t, and source/asset reliabilities are re-estimated once per
day from the trailing 30 days that end BEFORE that day. All hyperparameters are module constants fixed from the
literature defaults before any result was looked at (see ``HYPERPARAMETERS``); they were not changed afterwards.

PART 1  Fused USD index error (real venues bitfinex, coinbase, bitstamp; BTC, ETH, LTC, BCH, XLM, XRP, LINK; 2017-2023).
  Design: leave-one-open-venue-out. Only three venues list all seven assets, so for a reference R in {coinbase, bitstamp}
  the two OTHER venues (Bitfinex and the remaining open-rail venue) are fused and the fused log price is scored against
  R's own price (error = 1e4 (fused - R), bps). R never enters fusion, the offset estimator or the reliabilities.
  Caveat that follows from having two sources: the median equals the equal-weight mean, and no truth-discovery method can
  tell from one asset-hour which of two disagreeing sources is wrong; they can only learn it from history. The unit-aware
  method uses the other assets' gaps. Two further reference rows, not fusers, are reported: the remaining open-rail venue
  alone ("open_only") and Bitfinex alone ("bitfinex_only").
  Methods: median; vwap (volume-weighted mean); crh (Li et al. 2014, weights -log of normalised loss, trailing 30 days);
  gtm (Zhao & Han 2012 Gaussian truth model, used as the continuous-data truth-discovery baseline because a faithful
  continuous TruthFinder is not defined; trailing 30 days); unit_aware (frozen estimator, numeraire = the open-rail venue
  of the pair, offsets removed, median); unit_aware_dep (offsets within 10 bps form one vote, 24 h causal smoothing).
  The estimator sees every visible asset EXCEPT the one being fused (leave-one-asset-out, as in the harness) and only the two fused
  venues.
  Stress windows: Bitfinex 2017-04..2017-07 and 2018-10..2019-05. Binance.US 2023 is not run: the panel has no
  Binance.US series and the 2023 Binance.US minute files cover BTC/USD and BTC/USDT only, so there is no second asset for
  the estimator and no third open-rail venue to hold out.

PART 2  Held-out-asset correction (Bitfinex - Coinbase pair, the posthoc_eval score). The truth-discovery baselines act as
  offset estimators: each OTHER visible asset is a "source" claiming the pair gap g_a(t) at hour t; CRH (asset weights from the
  trailing 30 days) or GTM (asset variances from the trailing 30 days) discover the common offset; the implied offset is
  the discovered truth. Same score, same cells, same block bootstrap as posthoc_eval, so b1, b2 and the frozen estimator sit
  in the same table.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import harness as H
from . import panel as P
from . import posthoc_eval as X
from . import studies as S

REPO = P.REPO
OUT = REPO / "reports" / "unit_td" / "td_realdata.json"

HYPERPARAMETERS: dict[str, Any] = {
    "window_hours": 720,          # trailing 30 days for reliabilities, refit once per UTC day from data before that day
    "refit": "daily",
    "crh": {"max_iter": 100, "tol": 1e-9, "weights": "-log(loss/sum loss)", "loss": "squared error to weighted-mean truth",
            "init": "equal weights", "reference": "Li et al. 2014 (CRH), continuous data"},
    "gtm": {"alpha": 10.0, "beta": 10.0, "mu0": 0.0, "sigma0_sq": 1.0, "em_iter": 50, "sigma_sq_init": 1.0,
            "part1_center_each_object_on_source_mean": True, "part1_scale_bps": 10.0, "part2_scale_bps": 100.0,
            "reference": "Zhao & Han 2012 (Gaussian truth model); alpha, beta, mu0, sigma0^2 are the paper's defaults"},
    "unit_aware_dep": {"cluster_tol_bps": S.CLUSTER_TOL_BPS, "smooth_hours": S.CLUSTER_SMOOTH_H},
    "estimator": "www_auto.estimator (frozen, commit 724455b)",
    "error_threshold_bps": 50.0,
    "stress_windows": {"bitfinex_2017": ["2017-04-01", "2017-07-31 23:00"], "bitfinex_2018_19": ["2018-10-01", "2019-05-31 23:00"]},
}
WINDOW = HYPERPARAMETERS["window_hours"]
ASSETS = ("BTC", "ETH", "LTC", "BCH", "XLM", "XRP", "LINK")
FUSE_BASE = "bitfinex"
REFERENCES = ("coinbase", "bitstamp")
METHODS = ("median", "vwap", "crh", "gtm", "unit_aware", "unit_aware_dep")
EXTRA_ROWS = ("open_only", "bitfinex_only")
YEARS = tuple(range(2017, 2024))
THRESH = HYPERPARAMETERS["error_threshold_bps"]
GTM = HYPERPARAMETERS["gtm"]


# ================================================================== truth-discovery kernels

def crh_masked(x: np.ndarray, max_iter: int = 100, tol: float = 1e-9) -> np.ndarray:
    """CRH weights for an (objects x sources) claim matrix with NaN = no claim. Same update as studies.crh_weights
    (truth = weighted mean of the claims present; w_s = -log(loss_s / sum loss)); equal to it on complete data."""
    m = np.isfinite(x)
    k = x.shape[1]
    w = np.ones(k)
    keep = m.sum(axis=1) >= 2
    x, m = x[keep], m[keep]
    if x.shape[0] == 0:
        return w
    x0 = np.where(m, x, 0.0)
    for _ in range(max_iter):
        truth = (x0 * w).sum(axis=1) / (m * w).sum(axis=1)
        loss = (m * (x0 - truth[:, None]) ** 2).sum(axis=0)
        total = loss.sum()
        if total <= 1e-18:
            return np.ones(k)
        loss = np.maximum(loss, 1e-12 * total)
        new = -np.log(loss / loss.sum())
        if np.abs(new - w).max() < tol:
            return new
        w = new
    return w


def gtm_fit(x: np.ndarray, alpha: float = GTM["alpha"], beta: float = GTM["beta"], mu0: float = GTM["mu0"],
            s0: float = GTM["sigma0_sq"], n_iter: int = GTM["em_iter"]) -> np.ndarray:
    """Gaussian truth model (Zhao & Han 2012), EM. x: (objects x sources), NaN = no claim, already normalised.
    Truth mu_o ~ N(mu0, s0); claim x_os ~ N(mu_o, sigma_s^2); sigma_s^2 ~ InvGamma(alpha, beta). Returns sigma_s^2."""
    m = np.isfinite(x)
    k = x.shape[1]
    sig = np.full(k, GTM["sigma_sq_init"])
    keep = m.sum(axis=1) >= 1
    x, m = x[keep], m[keep]
    if x.shape[0] == 0:
        return sig
    x0 = np.where(m, x, 0.0)
    n_s = m.sum(axis=0)
    for _ in range(n_iter):
        mu = gtm_truth(x, sig, mu0, s0)
        sse = (m * (x0 - mu[:, None]) ** 2).sum(axis=0)
        sig = (2.0 * beta + sse) / (2.0 * (alpha + 1.0) + n_s)
    return sig


def gtm_truth(x: np.ndarray, sig: np.ndarray, mu0: float = GTM["mu0"], s0: float = GTM["sigma0_sq"]) -> np.ndarray:
    """Posterior mean of each object's truth given source variances (NaN claims ignored)."""
    m = np.isfinite(x)
    x0 = np.where(m, x, 0.0)
    prec = (m / sig).sum(axis=1) + 1.0 / s0
    return (mu0 / s0 + (x0 / sig).sum(axis=1)) / prec


def _day_blocks(index: pd.DatetimeIndex) -> list[tuple[int, int, int]]:
    """(start, end, window_start) positions of every UTC day; window = the WINDOW hours ending before the day."""
    day = index.floor("D")
    starts = np.r_[0, np.flatnonzero(day[1:] != day[:-1]) + 1]
    ends = np.r_[starts[1:], len(index)]
    ts = index.asi8
    out = []
    for s, e in zip(starts, ends):
        lo = np.searchsorted(ts, ts[s] - WINDOW * 3_600_000_000_000, side="left")
        out.append((int(s), int(e), int(lo)))
    return out


# ================================================================== Part 1

def _pair_inputs(raw: dict[str, pd.DataFrame], ref: str):
    """Hourly index and (T, 2) price/volume arrays per asset for the fused pair (bitfinex, other open venue)."""
    other = [v for v in REFERENCES if v != ref][0]
    fused = (FUSE_BASE, other)
    idx = raw[FUSE_BASE].index
    prices, vols, refp = {}, {}, {}
    for a in ASSETS:
        prices[a] = np.column_stack([raw[v][a].reindex(idx).to_numpy(float) for v in fused])
        vols[a] = np.column_stack([raw[v][a + "_vol"].reindex(idx).to_numpy(float) for v in fused])
        refp[a] = raw[ref][a].reindex(idx).to_numpy(float)
    return idx, fused, prices, vols, refp


def causal_td_fusion(idx: pd.DatetimeIndex, prices: dict[str, np.ndarray]) -> dict[str, dict[str, np.ndarray]]:
    """CRH and GTM fused log prices for every asset, weights refit daily on the trailing window (before the day)."""
    out = {m: {a: np.full(len(idx), np.nan) for a in prices} for m in ("crh", "gtm")}
    both = {a: np.isfinite(prices[a]).all(axis=1) for a in prices}
    for s, e, lo in _day_blocks(idx):
        xs = [1e4 * prices[a][lo:s][both[a][lo:s]] for a in prices]
        x = np.vstack(xs) if xs else np.empty((0, 2))
        w = crh_masked(x, HYPERPARAMETERS["crh"]["max_iter"], HYPERPARAMETERS["crh"]["tol"]) if len(x) else np.ones(2)
        if len(x):
            ctr = x.mean(axis=1, keepdims=True)
            sig = gtm_fit((x - ctr) / GTM["part1_scale_bps"])
        else:
            sig = np.full(2, GTM["sigma_sq_init"])
        for a, p in prices.items():
            blk = p[s:e]
            ok = both[a][s:e]
            out["crh"][a][s:e] = np.where(ok, blk @ w / w.sum(), np.nan)
            z = 1e4 * blk
            ctr = z.mean(axis=1)
            mu = gtm_truth(np.where(ok[:, None], (z - ctr[:, None]) / GTM["part1_scale_bps"], np.nan), sig)
            out["gtm"][a][s:e] = np.where(ok, (ctr + GTM["part1_scale_bps"] * mu) / 1e4, np.nan)
    return out


def visible_pair_panel(raw: dict[str, pd.DataFrame], fused: tuple[str, str], held: str) -> dict[str, pd.DataFrame]:
    """Estimator input: the two fused venues, visible assets only, held-out asset (and ETHBTC with ETH) removed."""
    keep = (set(P.VISIBLE) | set(P.EXTRA)) - {held}
    if held == "ETH":
        keep.discard("ETHBTC")
    return {v: raw[v][[c for c in raw[v].columns if c.removesuffix("_vol") in keep]].copy() for v in fused}


def part1(raw: dict[str, pd.DataFrame]) -> dict[str, Any]:
    factory = H.file_estimator_factory()
    est = factory()
    records = []
    for ref in REFERENCES:
        idx, fused, prices, vols, refp = _pair_inputs(raw, ref)
        td = causal_td_fusion(idx, prices)
        nu = 1  # numeraire = the open-rail venue of the pair (column 1); Bitfinex (column 0) is the platform venue
        for a in ASSETS:
            p, v, r = prices[a], vols[a], refp[a]
            ok = np.isfinite(p).all(axis=1) & (v > 0).all(axis=1) & np.isfinite(r)
            units = est(visible_pair_panel(raw, fused, a), fused[nu])
            off = np.nan_to_num(units[list(fused)].reindex(idx).to_numpy(float))
            dep, _ = S.fuse_unit_aware_cluster(np.where(ok[:, None], p, 0.0), off, np.where(ok[:, None], v, 1.0))
            fused_paths = {
                "median": np.median(p, axis=1),
                "vwap": np.where(ok, (p * np.where(ok[:, None], v, 1.0)).sum(axis=1) / np.where(ok, v.sum(axis=1), 1.0), np.nan),
                "crh": td["crh"][a], "gtm": td["gtm"][a],
                "unit_aware": S.fuse_unit_aware_median(p, off), "unit_aware_dep": dep,
                "open_only": p[:, nu], "bitfinex_only": p[:, 0],
            }
            for name, path in fused_paths.items():
                err = 1e4 * (path - r)
                err = np.where(ok, err, np.nan)
                records.append(pd.DataFrame({"ref": ref, "asset": a, "method": name, "err": err}, index=idx).dropna())
    return summarise(pd.concat(records))


def _stats(e: np.ndarray) -> dict[str, Any]:
    if len(e) == 0:
        return {"hours": 0}
    a = np.abs(e)
    return {"hours": int(len(a)), "median_abs_bps": float(np.median(a)), "p95_abs_bps": float(np.quantile(a, 0.95)),
            "hours_gt_50": int((a > THRESH).sum()), "share_gt_50": float((a > THRESH).mean())}


def summarise(long: pd.DataFrame) -> dict[str, Any]:
    sw = HYPERPARAMETERS["stress_windows"]
    subsets = {"btc_eth": ("BTC", "ETH"), "all_assets": ASSETS}
    refs = {"coinbase": ("coinbase",), "bitstamp": ("bitstamp",), "both": REFERENCES}
    res: dict[str, Any] = {}
    for sname, assets in subsets.items():
        for rname, rlist in refs.items():
            d = long[long["asset"].isin(assets) & long["ref"].isin(rlist)]
            # same hours for every method: keep asset-hours where all methods exist
            cnt = d.groupby([d.index, "ref", "asset"])["method"].transform("count")
            d = d[cnt == len(METHODS) + len(EXTRA_ROWS)]
            groups = {"all": d.index == d.index, **{f"year:{y}": d.index.year == y for y in YEARS}}
            for k, (lo, hi) in sw.items():
                groups[f"stress:{k}"] = (d.index >= pd.Timestamp(lo, tz="UTC")) & (d.index <= pd.Timestamp(hi, tz="UTC"))
            for gname, mask in groups.items():
                for m, x in d[mask].groupby("method"):
                    res.setdefault(f"{sname}/{rname}", {}).setdefault(gname, {})[m] = _stats(x["err"].to_numpy())
    return res


# ================================================================== Part 2 (offset estimators from truth discovery)

def asset_gap_matrix(raw, held: str, pair=H.PAIR) -> pd.DataFrame:
    """Visible-asset pair gaps (bps) at each hour, held-out asset excluded: the claims the offset estimators resolve."""
    vis = H.estimator_input(raw, held, "dev")
    shared = [c for c in vis[pair[0]].columns if not c.endswith("_vol") and c in vis[pair[1]].columns]
    return pd.concat([H.pair_gap(vis, c, pair).rename(c) for c in shared], axis=1)


def td_offset(g: pd.DataFrame, kind: str) -> pd.Series:
    """Causal CRH / GTM discovery of the pair offset from the asset claims; weights refit daily on the trailing window."""
    x = g.to_numpy(float)
    m = np.isfinite(x)
    out = np.full(len(g), np.nan)
    for s, e, lo in _day_blocks(g.index):
        hist = x[lo:s]
        blk, bm = x[s:e], m[s:e]
        if kind == "crh":
            w = crh_masked(hist, HYPERPARAMETERS["crh"]["max_iter"], HYPERPARAMETERS["crh"]["tol"])
            num = (np.where(bm, blk, 0.0) * w).sum(axis=1)
            den = (bm * w).sum(axis=1)
            out[s:e] = np.where(den > 0, num / np.where(den > 0, den, 1.0), np.nan)
        else:
            sc = GTM["part2_scale_bps"]
            sig = gtm_fit(hist / sc)
            mu = gtm_truth(np.where(bm, blk / sc, np.nan), sig)
            out[s:e] = np.where(bm.any(axis=1), sc * mu, np.nan)
    return pd.Series(out, index=g.index)


def part2(raw: dict[str, pd.DataFrame]) -> dict[str, Any]:
    outs = X.run_estimator(raw, P.DEV_SCORED + P.TEST_SCORED)
    res: dict[str, Any] = {}
    for split, assets in (("dev", P.DEV_SCORED), ("test", P.TEST_SCORED)):
        gs = {a: H.pair_gap(raw, a, H.PAIR) for a in assets}
        us: dict[str, dict[str, pd.Series]] = {k: {} for k in ("b1", "b2", "est", "crh", "gtm")}
        for a in assets:
            for k in ("b1", "b2"):
                us[k][a] = H.baseline_pair_u(raw, a, H.PAIR, k)
            us["est"][a] = outs[a][H.PAIR[0]] - outs[a][H.PAIR[1]]
            g = asset_gap_matrix(raw, a)
            for k in ("crh", "gtm"):
                us[k][a] = td_offset(g, k)
        parts = {k: X.cells(gs, us[k]) for k in us}
        points = {k: H.score_parts(gs, us[k]) for k in us}
        boot = X.bootstrap(parts, diff=None)
        extra = X.bootstrap({k: parts[k] for k in ("crh", "gtm", "est", "b2")}, diff=("est", "crh"))
        extra_g = X.bootstrap({k: parts[k] for k in ("crh", "gtm", "est", "b2")}, diff=("est", "gtm"))
        res[split] = {"assets": list(assets), "n_hours": points["est"]["n"], "bootstrap": boot,
                      "diff_est_minus_crh": {g: v["diff"] for g, v in extra.items()},
                      "diff_est_minus_gtm": {g: v["diff"] for g, v in extra_g.items()},
                      "points": {k: {"score": v["score"], "by_asset": v["by_asset"], "by_year": v["by_year"], "coverage": v["coverage"]}
                                 for k, v in points.items()},
                      "mean_abs_correction_bps": {k: X.mean_abs_correction(parts[k]) for k in parts}}
    return res


# ================================================================== driver

def build() -> dict[str, Any]:
    raw = X.load_raw(True)
    p2 = part2(raw)
    prior = json.loads(X.OUT.read_text())["bitfinex_coinbase"]
    drift = {s: abs(p2[s]["points"]["est"]["score"] - prior[s]["harness_points"]["est"]["score"]) for s in ("dev", "test")}
    if max(drift.values()) > 1e-9:
        raise SystemExit(f"estimator scores do not match posthoc.json: {drift}")
    return {"estimator_sha256": hashlib.sha256(Path(H.EST_PATH).read_bytes()).hexdigest(),
            "hyperparameters": HYPERPARAMETERS, "assets_part1": list(ASSETS),
            "part1_design": "leave-one-open-venue-out: fuse bitfinex + the other open venue, score against the held-out open venue",
            "part1_not_run": "Binance.US 2023: no Binance.US series in the panel; its 2023 files carry BTC only",
            "part1": part1(raw), "part2": p2, "part2_estimator_matches_posthoc": drift}


def main() -> int:
    res = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
