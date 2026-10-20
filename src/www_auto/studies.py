"""Reported-outside-the-loop UNIT-TD studies: T4 (unit diagnostic per venue pair and year) and T2 (fusion under injected unit bias).

    uv run python -m www_auto.studies [t4|t2|all] [--panel PATH] [--out reports/unit_td]

Dev assets only (BTC, ETH, LTC, BCH, ETC, XLM plus the Bitfinex USDT/ETHBTC feeds). The test assets are never loaded: the
panel is read with ``load_panel("dev")`` and any test column is dropped again as defence in depth.

Any estimator with the harness interface ``estimate_units(panel, numeraire_venue) -> DataFrame[venue -> bps]`` can be passed
in; the default is ``www_auto.estimator.estimate_units``. ``b2_median_gap`` below is a plain same-hour median-gap estimator
used as a second, shrinkage-free plug-in (the default estimator returns exactly 0 when only one asset is visible).
"""

from __future__ import annotations

import argparse
import itertools
import json
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import harness as H
from . import panel as P

Estimator = Callable[[dict[str, pd.DataFrame], str], pd.DataFrame]

# ------------------------------------------------------------------ constants (fixed in advance, not tuned)
SEPARATE_SHARE_MIN = 0.5     # T4: explained share >= this ...
SEPARATE_GAP_MIN_BPS = 3.0   # ... and median |gap| >= this  -> "separate dollar"
SHARED_SHARE_MAX = 0.1       # T4: explained share <= this -> "shared dollar"; anything else "mixed"
T4_YEARS = tuple(range(2017, 2024))
T4_PAIRS = (("bitfinex", "coinbase"), ("bitfinex", "bitstamp"), ("coinbase", "bitstamp"))
T4_NUMERAIRE = H.NUMERAIRE
MIN_HOURS = 500              # fewer scored hours in a venue-year -> "insufficient"
MIN_DAYS_CORR = 30           # fewer days for the cross-asset correlation -> NaN
MIN_HOURS_PER_DAY = 12

T2_START, T2_END = "2021-01-01", "2023-12-31 23:00"
T2_VENUES = ("bitfinex", "coinbase", "bitstamp")
T2_ASSETS = ("BTC", "ETH")
T2_DELTAS = (25, 50, 100, 200, 400, 800)
T2_KS = (1, 2)
T2_NUMERAIRE = "coinbase"   # reference venue handed to the estimator
BREAKDOWN_P95_BPS = 50.0
HOURS_GT_BPS = 50.0
REPLAY_START, REPLAY_END = "2018-10-01", "2019-05-31 23:00"  # Bitfinex-vs-Bitstamp BTC episode
CLUSTER_TOL_BPS = 10.0       # offsets within this are one unit
CLUSTER_SMOOTH_H = 24        # causal trailing median of the offsets before clustering
CRH_MAX_ITER, CRH_TOL = 100, 1e-9


# ------------------------------------------------------------------ loading and plug-ins

def default_estimator() -> Estimator:
    from . import estimator
    return estimator.estimate_units


def b2_median_gap(panel: dict[str, pd.DataFrame], numeraire_venue: str) -> pd.DataFrame:
    """Same-hour median over shared assets of the log gap to the numeraire, bps. Causal, venue-agnostic, no shrinkage."""
    base = panel[numeraire_venue]
    index = base.index
    for f in panel.values():
        index = index.union(f.index)
    out = pd.DataFrame(0.0, index=index, columns=list(panel))
    for venue, frame in panel.items():
        if venue == numeraire_venue:
            continue
        shared = [c for c in frame.columns if not str(c).endswith("_vol") and c in base.columns]
        if not shared:
            out[venue] = np.nan
            continue
        out[venue] = 1e4 * (frame[shared].reindex(index) - base[shared].reindex(index)).median(axis=1, skipna=True)
    return out


def default_panel_path() -> Path:
    """WWW_AUTO_PANEL, else the repo's own cache, else the cache of the main checkout above a git worktree."""
    import os
    env = os.environ.get("WWW_AUTO_PANEL")
    if env:
        return Path(env)
    for base in (P.REPO, *P.REPO.parents):
        cand = base / "data" / "derived" / "unit_td_panel.parquet"
        if cand.is_file() and cand.with_name("unit_td_panel_meta.json").is_file():
            return cand
    return P.PANEL_PATH


def load_dev_panel(path: Path | None = None) -> dict[str, pd.DataFrame]:
    raw, _ = P.load_panel("dev", path or default_panel_path())
    return strip_test_assets(raw)


def strip_test_assets(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {v: f[[c for c in f.columns if c.removesuffix("_vol") not in P.TEST_SCORED]] for v, f in raw.items()}


# ================================================================== T4: unit diagnostic

def classify(share: float, median_abs_gap_bps: float) -> str:
    """Fixed thresholds (module constants). NaN inputs -> 'insufficient'."""
    if not (np.isfinite(share) and np.isfinite(median_abs_gap_bps)):
        return "insufficient"
    if share >= SEPARATE_SHARE_MIN and median_abs_gap_bps >= SEPARATE_GAP_MIN_BPS:
        return "separate dollar"
    if share <= SHARED_SHARE_MAX:
        return "shared dollar"
    return "mixed"


def explained_share(g: np.ndarray, u: np.ndarray) -> float:
    """Harness formula 1 - sum (g-u)^2 / sum g^2 (u NaN counts as 0, no correction)."""
    g = np.asarray(g, float)
    u = np.nan_to_num(np.asarray(u, float), nan=0.0)
    den = float((g**2).sum())
    return float(1.0 - ((g - u) ** 2).sum() / den) if den > 0 else float("nan")


def daily_gap_corr(btc_gap: pd.Series, other_gap: pd.Series) -> float:
    """Correlation over days of the daily mean gap (bps) of BTC vs another asset; days need MIN_HOURS_PER_DAY hours of both."""
    both = pd.concat([btc_gap, other_gap], axis=1, keys=["b", "o"]).dropna()
    if both.empty:
        return float("nan")
    day = both.index.floor("D")
    cnt = both["b"].groupby(day).size()
    mean = both.groupby(day).mean()[cnt >= MIN_HOURS_PER_DAY]
    if len(mean) < MIN_DAYS_CORR or mean["b"].std() == 0 or mean["o"].std() == 0:
        return float("nan")
    return float(mean["b"].corr(mean["o"]))


def t4_unit_diagnostic(raw: dict[str, pd.DataFrame], estimate_units: Estimator | None = None,
                       pairs=T4_PAIRS, years=T4_YEARS, numeraire: str = T4_NUMERAIRE) -> dict[str, Any]:
    est = estimate_units or default_estimator()
    raw = strip_test_assets(raw)
    index = raw[numeraire].index
    shared_all = {p: [a for a in P.DEV_SCORED if a in raw[p[0]].columns and a in raw[p[1]].columns] for p in pairs}
    held = sorted({a for v in shared_all.values() for a in v})
    outs = {a: est({v: f.copy() for v, f in H.estimator_input(raw, a, "dev").items()}, numeraire).reindex(index) for a in held}
    rows: list[dict[str, Any]] = []
    for pair in pairs:
        assets = shared_all[pair]
        if not assets:
            continue
        frames = []
        for a in assets:
            g = H.pair_gap(raw, a, pair)
            d = pd.DataFrame({"g": g, "u_est": outs[a][pair[0]] - outs[a][pair[1]],
                              "u_b1": H.baseline_pair_u(raw, a, pair, "b1"),
                              "u_b2": H.baseline_pair_u(raw, a, pair, "b2")})
            d["asset"] = a
            frames.append(d[d["g"].notna()])
        long = pd.concat(frames)
        btc_gap = H.pair_gap(raw, "BTC", pair) if "BTC" in raw[pair[0]].columns and "BTC" in raw[pair[1]].columns else None
        for year in years:
            y = long[long.index.year == year]
            row: dict[str, Any] = {"pair": f"{pair[0]}-{pair[1]}", "year": year, "assets": assets, "n_hours": int(len(y))}
            if len(y) < MIN_HOURS:
                row.update(explained_share=None, share_b1=None, share_b2=None, median_abs_gap_bps=None,
                           corr_btc_by_asset={}, corr_btc_mean=None, classification="insufficient",
                           classification_b2="insufficient")
                rows.append(row)
                continue
            share = explained_share(y["g"].to_numpy(), y["u_est"].to_numpy())
            share_b2 = explained_share(y["g"].to_numpy(), y["u_b2"].to_numpy())
            med = float(y["g"].abs().median())
            corr = {}
            if btc_gap is not None:
                for a in assets:
                    gy = y[y["asset"] == a]["g"]
                    corr[a] = daily_gap_corr(btc_gap[btc_gap.index.year == year], gy)
            finite = [v for v in corr.values() if np.isfinite(v)]
            row.update(explained_share=share, share_b1=explained_share(y["g"].to_numpy(), y["u_b1"].to_numpy()),
                       share_b2=share_b2, median_abs_gap_bps=med,
                       corr_btc_by_asset=corr, corr_btc_mean=float(np.mean(finite)) if finite else None,
                       classification=classify(share, med), classification_b2=classify(share_b2, med))
            rows.append(row)
    return {"study": "T4", "dev_assets_only": True, "numeraire": numeraire,
            "thresholds": {"separate_share_min": SEPARATE_SHARE_MIN, "separate_gap_min_bps": SEPARATE_GAP_MIN_BPS,
                           "shared_share_max": SHARED_SHARE_MAX, "min_hours": MIN_HOURS},
            "rows": rows}


def _f(v: Any, nd: int = 2) -> str:
    return "n/a" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f"{v:.{nd}f}"


def t4_markdown(result: dict[str, Any]) -> str:
    t = result["thresholds"]
    lines = ["| Pair | Year | Hours | Explained (est) | b1 | b2 | Median abs gap (bps) | Corr BTC vs others | Class | Class if b2 used |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in result["rows"]:
        lines.append(f"| {r['pair']} | {r['year']} | {r['n_hours']} | {_f(r['explained_share'])} | {_f(r['share_b1'])} | "
                     f"{_f(r['share_b2'])} | {_f(r['median_abs_gap_bps'], 1)} | {_f(r['corr_btc_mean'])} | {r['classification']} | {r['classification_b2']} |")
    lines.append("")
    lines.append(f"Separate dollar: explained >= {t['separate_share_min']} and median abs gap >= {t['separate_gap_min_bps']} bps. "
                 f"Shared dollar: explained <= {t['shared_share_max']}. Otherwise mixed. Under {t['min_hours']} scored hours: insufficient.")
    return "\n".join(lines)


# ================================================================== T2: fusion under injected unit bias

def constant_path(delta_bps: float, n: int) -> np.ndarray:
    return np.full(n, float(delta_bps))


def replay_path(gap_bps: pd.Series | np.ndarray, n: int) -> np.ndarray:
    """Replay an episode gap by hour of episode: hour i of the window gets episode hour i (cycled if the window is longer).
    Gaps inside the episode are filled by linear interpolation (and nearest at the ends) before replay."""
    s = pd.Series(np.asarray(gap_bps, float))
    s = s.interpolate(limit_direction="both")
    if s.isna().all():
        raise ValueError("empty episode path")
    return np.resize(s.to_numpy(), n)


def inject(prices: np.ndarray, venues_hit: list[int], path_bps: np.ndarray) -> np.ndarray:
    """Add a shared unit offset path (bps, applied as log points / 1e4) to the chosen venue columns of a (T, V) log-price array."""
    out = prices.copy()
    for v in venues_hit:
        out[:, v] = out[:, v] + path_bps / 1e4
    return out


def truth_median(prices: np.ndarray) -> np.ndarray:
    return np.median(prices, axis=1)


def fuse_median(prices: np.ndarray) -> np.ndarray:
    return np.median(prices, axis=1)


def fuse_vwap(prices: np.ndarray, vols: np.ndarray) -> np.ndarray:
    w = np.asarray(vols, float)
    return (prices * w).sum(axis=1) / w.sum(axis=1)


def crh_weights(x: np.ndarray, max_iter: int = CRH_MAX_ITER, tol: float = CRH_TOL) -> np.ndarray:
    """CRH (Li et al. 2014) for continuous data: truth = weighted mean; w_s = -log(loss_s / sum loss), loss = squared error to the truth."""
    n_src = x.shape[1]
    w = np.ones(n_src)
    if x.shape[0] == 0:
        return w
    for _ in range(max_iter):
        truth = x @ w / w.sum()
        loss = ((x - truth[:, None]) ** 2).sum(axis=0)
        total = loss.sum()
        if total <= 1e-18:
            return np.ones(n_src)
        loss = np.maximum(loss, 1e-12 * total)
        new = -np.log(loss / loss.sum())
        if np.abs(new - w).max() < tol:
            return new
        w = new
    return w


def fuse_crh(prices: dict[str, np.ndarray], days: np.ndarray) -> dict[str, np.ndarray]:
    """Causal daily CRH: the weights used on day d are the converged CRH weights fitted on day d-1 (assets pooled, in bps);
    the first day, or a day after an empty day, carries the last weights (equal weights at the start)."""
    assets = list(prices)
    n_src = prices[assets[0]].shape[1]
    out = {a: np.empty(len(days)) for a in assets}
    w = np.ones(n_src)
    starts = np.r_[0, np.flatnonzero(np.diff(days)) + 1, len(days)]
    for s, e in zip(starts[:-1], starts[1:]):
        for a in assets:
            out[a][s:e] = prices[a][s:e] @ w / w.sum()
        x = np.vstack([1e4 * prices[a][s:e] for a in assets])
        w = crh_weights(x)
    return out


def cluster_labels(offsets_bps: np.ndarray, tol: float = CLUSTER_TOL_BPS) -> np.ndarray:
    """Per row single-linkage clusters of venues: venues whose offsets differ by <= tol (chained) share a unit.
    Returns (T, V) integer labels = the smallest venue index in the cluster."""
    t, v = offsets_bps.shape
    adj = np.abs(offsets_bps[:, :, None] - offsets_bps[:, None, :]) <= tol
    labels = np.tile(np.arange(v), (t, 1))
    for _ in range(v):
        cand = np.where(adj, labels[:, None, :], v)
        labels = np.minimum(labels, cand.min(axis=2))
    return labels


def smooth_offsets(offsets_bps: np.ndarray, window: int = CLUSTER_SMOOTH_H) -> np.ndarray:
    """Causal trailing median over ``window`` hours, per venue."""
    return pd.DataFrame(offsets_bps).rolling(window, min_periods=1).median().to_numpy()


def fuse_unit_aware_median(prices: np.ndarray, offsets_bps: np.ndarray) -> np.ndarray:
    """Remove the estimated venue offsets (all venues land in the numeraire's unit), then take the median."""
    return np.median(prices - np.nan_to_num(offsets_bps) / 1e4, axis=1)


def fuse_unit_aware_cluster(prices: np.ndarray, offsets_bps: np.ndarray, vols: np.ndarray,
                            tol: float = CLUSTER_TOL_BPS, window: int = CLUSTER_SMOOTH_H) -> tuple[np.ndarray, np.ndarray]:
    """Dependence-aware fusion. Venues are clustered on the smoothed offsets; each cluster casts ONE vote (the median of its
    members' raw prices); the numeraire is the largest cluster (ties: the most liquid); the other clusters' votes are
    moved into the numeraire unit with the cluster offset difference; the fused price is the median of the votes.
    Returns (fused, labels)."""
    off = np.nan_to_num(offsets_bps)
    labels = cluster_labels(smooth_offsets(off, window), tol)
    t, v = prices.shape
    vote = np.full((t, v), np.nan)
    c_off = np.full((t, v), np.nan)
    size = np.zeros((t, v))
    liq = np.zeros((t, v))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for c in range(v):
            m = labels == c
            active = m.any(axis=1)
            vote[:, c] = np.where(active, np.nanmedian(np.where(m, prices, np.nan), axis=1), np.nan)
            c_off[:, c] = np.where(active, np.nanmedian(np.where(m, off, np.nan), axis=1), np.nan)
            size[:, c] = m.sum(axis=1)
            liq[:, c] = np.where(m, vols, 0.0).sum(axis=1)
    score = size + liq / (liq.sum(axis=1, keepdims=True) + 1e-300) * 0.5  # size first, liquidity breaks ties
    score = np.where(size > 0, score, -1.0)
    num = score.argmax(axis=1)
    rows = np.arange(t)
    aligned = vote - (c_off - c_off[rows, num][:, None]) / 1e4
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        fused = np.nanmedian(aligned, axis=1)
    return fused, labels


def unit_offsets(prices_other: np.ndarray, vols_other: np.ndarray, other_asset: str, index: pd.DatetimeIndex,
                 venues: tuple[str, ...], est: Estimator, numeraire: str) -> np.ndarray:
    """Venue unit offsets (bps, relative to the numeraire) estimated from ONE asset (the other one); NaN -> 0."""
    panel = {v: pd.DataFrame({other_asset: prices_other[:, i], f"{other_asset}_vol": vols_other[:, i]}, index=index)
             for i, v in enumerate(venues)}
    out = est(panel, numeraire)
    return np.nan_to_num(out[list(venues)].reindex(index).to_numpy(float))


def t2_inputs(raw: dict[str, pd.DataFrame], start: str = T2_START, end: str = T2_END,
              venues: tuple[str, ...] = T2_VENUES, assets: tuple[str, ...] = T2_ASSETS):
    """Complete-case hours: every venue has a price and a positive volume for every asset. Returns (index, prices, vols)."""
    idx = raw[venues[0]].loc[start:end].index
    ok = np.ones(len(idx), bool)
    for v in venues:
        for a in assets:
            ok &= raw[v][a].reindex(idx).notna().to_numpy() & (raw[v][f"{a}_vol"].reindex(idx).to_numpy() > 0)
    idx = idx[ok]
    prices = {a: np.column_stack([raw[v][a].reindex(idx).to_numpy(float) for v in venues]) for a in assets}
    vols = {a: np.column_stack([raw[v][f"{a}_vol"].reindex(idx).to_numpy(float) for v in venues]) for a in assets}
    return idx, prices, vols


def replay_gap_from_panel(raw: dict[str, pd.DataFrame]) -> pd.Series:
    """Bitfinex minus Bitstamp BTC log gap (bps), 2018-10..2019-05."""
    g = 1e4 * (raw["bitfinex"]["BTC"] - raw["bitstamp"]["BTC"])
    return g.loc[REPLAY_START:REPLAY_END]


def fuse_all(prices: dict[str, np.ndarray], vols: dict[str, np.ndarray], index: pd.DatetimeIndex,
             estimators: dict[str, Estimator], venues: tuple[str, ...] = T2_VENUES,
             numeraire: str = T2_NUMERAIRE) -> tuple[dict[str, dict[str, np.ndarray]], dict[str, np.ndarray]]:
    """Run every fuser on the (already injected) prices. Returns (fused[name][asset], cluster labels[estimator label] stacked)."""
    assets = list(prices)
    days = index.normalize().asi8
    fused: dict[str, dict[str, np.ndarray]] = {
        "median": {a: fuse_median(prices[a]) for a in assets},
        "vwap": {a: fuse_vwap(prices[a], vols[a]) for a in assets},
        "crh": fuse_crh(prices, days),
    }
    labels: dict[str, dict[str, np.ndarray]] = {}
    for label, est in estimators.items():
        ua, uc, lab = {}, {}, {}
        for a in assets:
            others = [b for b in assets if b != a]
            offs = np.mean([unit_offsets(prices[b], vols[b], b, index, venues, est, numeraire) for b in others], axis=0)
            ua[a] = fuse_unit_aware_median(prices[a], offs)
            uc[a], lab[a] = fuse_unit_aware_cluster(prices[a], offs, vols[a])
        fused[f"ua_median[{label}]"], fused[f"ua_cluster[{label}]"] = ua, uc
        labels[label] = lab
    return fused, labels


def _summ(err: np.ndarray) -> dict[str, float]:
    a = np.abs(err)
    return {"median_abs_err_bps": float(np.median(a)), "p95_abs_err_bps": float(np.quantile(a, 0.95)),
            "hours_gt50": int((a > HOURS_GT_BPS).sum()), "share_gt50": float((a > HOURS_GT_BPS).mean()), "n": int(a.size)}


def partition_accuracy(lab: dict[str, np.ndarray], hit: list[int], v: int) -> float:
    """Share of asset-hours whose cluster partition equals the true one ({hit venues} vs the rest)."""
    truth = np.zeros(v, int)
    truth[hit] = 1
    same_true = truth[:, None] == truth[None, :]
    res = []
    for labels in lab.values():
        same = labels[:, :, None] == labels[:, None, :]
        res.append((same == same_true[None]).all(axis=(1, 2)))
    return float(np.concatenate(res).mean())


def run_t2(raw: dict[str, pd.DataFrame], estimators: dict[str, Estimator] | None = None,
           deltas=T2_DELTAS, ks=T2_KS, start: str = T2_START, end: str = T2_END) -> dict[str, Any]:
    raw = strip_test_assets(raw)
    estimators = estimators or {"default": default_estimator(), "b2_median_gap": b2_median_gap}
    index, prices, vols = t2_inputs(raw, start, end)
    assets, n_v = list(prices), len(T2_VENUES)
    truth = {a: truth_median(prices[a]) for a in assets}
    replay = replay_gap_from_panel(raw)
    scenarios: list[tuple[str, float | None, np.ndarray]] = [("constant", d, constant_path(d, len(index))) for d in deltas]
    scenarios.append(("realistic", None, replay_path(replay.to_numpy(), len(index))))
    records: list[dict[str, Any]] = []
    cluster_rows: list[dict[str, Any]] = []
    for k in ks:
        combos = list(itertools.combinations(range(n_v), k))
        for shape, delta, path in scenarios:
            acc: dict[str, dict[str, list[np.ndarray]]] = {}
            per_combo: dict[str, list[float]] = {}
            part: dict[tuple[str, str], list[float]] = {}
            for hit in combos:
                inj = {a: inject(prices[a], list(hit), path) for a in assets}
                fused, labels = fuse_all(inj, vols, index, estimators)
                majority_bias = path if k >= 2 else np.zeros_like(path)  # bias carried by the majority unit
                for name, by_asset in fused.items():
                    err = np.concatenate([1e4 * (by_asset[a] - truth[a]) for a in assets])
                    err_major = np.concatenate([1e4 * (by_asset[a] - truth[a]) - majority_bias for a in assets])
                    ratio = 1e4 * ((by_asset["ETH"] - by_asset["BTC"]) - (truth["ETH"] - truth["BTC"]))
                    d = acc.setdefault(name, {"err": [], "major": [], "ratio": []})
                    d["err"].append(err)
                    d["major"].append(err_major)
                    d["ratio"].append(ratio)
                    per_combo.setdefault(name, []).append(_summ(err)["p95_abs_err_bps"])
                for lbl, lab in labels.items():
                    part.setdefault((lbl, "x"), []).append(partition_accuracy(lab, list(hit), n_v))
            for name, d in acc.items():
                rec = {"k": k, "shape": shape, "delta_bps": delta, "fuser": name,
                       **_summ(np.concatenate(d["err"])),
                       "worst_combo_p95_abs_err_bps": float(max(per_combo[name])),
                       "ratio_p95_abs_err_bps": float(np.quantile(np.abs(np.concatenate(d["ratio"])), 0.95)),
                       "vs_majority_unit_p95_abs_err_bps": float(np.quantile(np.abs(np.concatenate(d["major"])), 0.95)),
                       "vs_majority_unit_median_abs_err_bps": float(np.median(np.abs(np.concatenate(d["major"]))))}
                records.append(rec)
            for (lbl, _), vals in part.items():
                cluster_rows.append({"k": k, "shape": shape, "delta_bps": delta, "estimator": lbl,
                                     "partition_accuracy": float(np.mean(vals))})
    return {"study": "T2", "dev_assets_only": True, "window": [T2_START, T2_END], "venues": list(T2_VENUES),
            "assets": list(T2_ASSETS), "n_asset_hours_per_combo": int(len(index) * len(assets)),
            "replay_path": {"median_bps": float(np.median(replay.dropna())), "p95_abs_bps": float(np.quantile(replay.abs().dropna(), 0.95)),
                            "max_abs_bps": float(replay.abs().max()), "episode_hours": int(len(replay))},
            "params": {"cluster_tol_bps": CLUSTER_TOL_BPS, "cluster_smooth_h": CLUSTER_SMOOTH_H,
                       "breakdown_p95_bps": BREAKDOWN_P95_BPS, "hours_gt_bps": HOURS_GT_BPS},
            "records": records, "cluster": cluster_rows, "breakdown": breakdown(records, deltas)}


def breakdown(records: list[dict[str, Any]], deltas=T2_DELTAS) -> dict[str, dict[str, dict[str, Any]]]:
    """delta* per k and fuser: the smallest constant delta whose p95 error exceeds 50 bps (None: never, within the grid).
    'pooled' uses the error pooled over which venues are hit; 'worst_combo' the worst single choice of venues."""
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for r in records:
        if r["shape"] != "constant":
            continue
        slot = out.setdefault(f"k={r['k']}", {}).setdefault(r["fuser"], {"pooled": None, "worst_combo": None})
        for key, field in (("pooled", "p95_abs_err_bps"), ("worst_combo", "worst_combo_p95_abs_err_bps")):
            if r[field] > BREAKDOWN_P95_BPS and (slot[key] is None or r["delta_bps"] < slot[key]):
                slot[key] = r["delta_bps"]
    return out


def t2_markdown(result: dict[str, Any]) -> str:
    recs = result["records"]
    fusers = list(dict.fromkeys(r["fuser"] for r in recs))
    lines = []
    for k in sorted({r["k"] for r in recs}):
        lines += [f"### k = {k} of 3 venues biased: p95 |error| vs truth (bps), pooled over which venues are hit", ""]
        cols = [(r["shape"], r["delta_bps"]) for r in recs if r["k"] == k and r["fuser"] == fusers[0]]
        lines.append("| Fuser | " + " | ".join("realistic" if s == "realistic" else f"{int(d)}" for s, d in cols) + " |")
        lines.append("|---|" + "---|" * len(cols))
        for f in fusers:
            vals = {(r["shape"], r["delta_bps"]): r for r in recs if r["k"] == k and r["fuser"] == f}
            lines.append(f"| {f} | " + " | ".join(_f(vals[c]["p95_abs_err_bps"], 1) for c in cols) + " |")
        lines.append("")
        lines += [f"Median |error| and hours above 50 bps for k = {k} (share of asset-hours):", "",
                  "| Fuser | " + " | ".join("realistic" if s == "realistic" else f"{int(d)}" for s, d in cols) + " |",
                  "|---|" + "---|" * len(cols)]
        for f in fusers:
            vals = {(r["shape"], r["delta_bps"]): r for r in recs if r["k"] == k and r["fuser"] == f}
            lines.append(f"| {f} | " + " | ".join(f"{_f(vals[c]['median_abs_err_bps'], 1)} / {100 * vals[c]['share_gt50']:.0f}%" for c in cols) + " |")
        lines.append("")
    lines += ["### Breakdown delta* (smallest tested delta, bps, with p95 error above 50; 'none' = not reached by 800)", "",
              "| k | Fuser | pooled | worst venue choice |", "|---|---|---|---|"]
    for k, by in result["breakdown"].items():
        for f in fusers:
            b = by.get(f, {})
            show = lambda v: "none" if v is None else str(int(v))  # noqa: E731
            lines.append(f"| {k} | {f} | {show(b.get('pooled'))} | {show(b.get('worst_combo'))} |")
    lines += ["", "### Cluster recovery: share of asset-hours whose venue partition equals the injected one", "",
              "| k | scenario | estimator | partition accuracy |", "|---|---|---|---|"]
    for c in result["cluster"]:
        sc = "realistic" if c["shape"] == "realistic" else f"{int(c['delta_bps'])} bps"
        lines.append(f"| {c['k']} | {sc} | {c['estimator']} | {c['partition_accuracy']:.2f} |")
    return "\n".join(lines)


# ================================================================== CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="www_auto.studies")
    ap.add_argument("which", nargs="?", default="all", choices=["t4", "t2", "all"])
    ap.add_argument("--panel", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=P.REPO / "reports" / "unit_td")
    args = ap.parse_args(argv)
    raw = load_dev_panel(args.panel)
    args.out.mkdir(parents=True, exist_ok=True)
    if args.which in ("t4", "all"):
        res = t4_unit_diagnostic(raw)
        (args.out / "t4_unit_diagnostic.json").write_text(json.dumps(res, indent=1, default=float))
        (args.out / "t4_unit_diagnostic.md").write_text(t4_markdown(res) + "\n")
    if args.which in ("t2", "all"):
        res = run_t2(raw)
        (args.out / "t2_breakdown.json").write_text(json.dumps(res, indent=1, default=float))
        (args.out / "t2_breakdown.md").write_text(t2_markdown(res) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
