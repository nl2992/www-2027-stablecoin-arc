"""Fixed UNIT-TD evaluation harness (read-only for the autoresearch loop).

    uv run python -m www_auto.harness            # dev mode (test assets are never read)
    uv run python -m www_auto.harness --final    # locked test; refuses unless autoresearch/FINAL_UNLOCK exists

Scoring (leave-one-asset-out). For each scored asset a the estimator is called once with a's columns removed from every
venue (and, for ETH, the Bitfinex ETHBTC feed, which would re-create ETH). With the estimator's units u, the pair
estimate is u_hat(t) = u_bitfinex(t) - u_coinbase(t) against the gap g_a(t) = 1e4 (p_bitfinex,a - p_coinbase,a):
    score = 1 - sum (g - u_hat)^2 / sum g^2     pooled over scored assets and hours where g exists.
Hardening versus the bare spec: a missing u_hat on an hour where g exists counts as u_hat = 0 (no correction), so
withholding the output on hard hours cannot raise the score; coverage_ok separately requires >= 99% non-NaN.

Control: coinbase vs bitstamp on ETH, 2019-01..2023-12 (ETH removed): g = 1e4 (p_coinbase - p_bitstamp), u_hat = u_coinbase - u_bitstamp.

Checks (run on CHECK_ASSETS = ETH and BCH only, for speed; coverage is checked on every scored asset and the control):
  causal_ok  - outputs of the estimator on the panel truncated at 3 random cut points match the full run before each cut (1e-6 bps).
  perm_ok    - a different venue anonymisation gives the same outputs after mapping keys back (1e-6 bps).
  coverage_ok- u_hat is non-NaN on >= 99% of hours where g exists, for every scored asset and the control.
Each estimator call gets deep copies of the data and a freshly loaded copy of estimator.py (module state does not
survive between calls). Venue keys are anonymised v0, v1, v2 in a random order seeded per run (printed as `seed`).

Baselines (harness-internal, not importable from the estimator): b0 = 0; b1 = same-hour BTC pair gap; b2 = same-hour
median of the pair gaps over all visible assets (the held-out asset excluded).
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import panel as P

REPO = P.REPO
EST_PATH = Path(__file__).with_name("estimator.py")
NUMERAIRE = "coinbase"
PAIR = ("bitfinex", "coinbase")
CONTROL_PAIR = ("coinbase", "bitstamp")
CONTROL_ASSET = "ETH"
CONTROL_START = pd.Timestamp("2019-01-01", tz="UTC")
CHECK_ASSETS = ("ETH", "BCH")
N_CUTS = 3
TOL_BPS = 1e-6
COVERAGE_MIN = 0.99
EstimatorFactory = Callable[[], Callable[[dict[str, pd.DataFrame], str], pd.DataFrame]]


# ---------------------------------------------------------------- estimator calls

def file_estimator_factory(path: Path = EST_PATH) -> EstimatorFactory:
    """Each call loads estimator.py as a brand new module object, so module-level caches cannot carry over."""
    def make():
        spec = importlib.util.spec_from_file_location("_unit_td_estimator_instance", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.estimate_units
    return make


def anonymise(venues: list[str], seed: int) -> dict[str, str]:
    """real venue name -> key ('v0', 'v1', ...), random but fixed per seed."""
    order = np.random.default_rng(seed).permutation(len(venues))
    return {v: f"v{order[i]}" for i, v in enumerate(sorted(venues))}


def estimator_input(raw: dict[str, pd.DataFrame], held_out: str, mode: str) -> dict[str, pd.DataFrame]:
    """Visible columns only: BTC + dev assets + extra feeds, minus the held-out asset (and ETHBTC when ETH is held out)."""
    keep = set(P.VISIBLE) | set(P.EXTRA)
    keep.discard(held_out)
    if held_out == "ETH":
        keep.discard("ETHBTC")
    out = {}
    for venue, frame in raw.items():
        cols = [c for c in frame.columns if c.removesuffix("_vol") in keep]
        out[venue] = frame[cols].copy()
    return out


def call_estimator(factory: EstimatorFactory, raw: dict[str, pd.DataFrame], held_out: str, mode: str, seed: int,
                   cut: int | None = None) -> pd.DataFrame:
    """Run the estimator once; returns units (bps) with REAL venue names as columns, on the full hourly index."""
    mapping = anonymise(list(raw), seed)
    data = estimator_input(raw, held_out, mode)
    index = next(iter(raw.values())).index
    if cut is not None:
        data = {v: f.iloc[:cut].copy() for v, f in data.items()}
    shuffle = np.random.default_rng(seed + 1).permutation(len(data))
    names = sorted(data)
    anon = {mapping[names[i]]: data[names[i]] for i in shuffle}
    out = factory()(anon, mapping[NUMERAIRE])
    if not isinstance(out, pd.DataFrame):
        raise TypeError("estimator must return a DataFrame")
    inverse = {k: v for v, k in mapping.items()}
    missing = set(inverse) - set(out.columns)
    if missing:
        raise ValueError(f"estimator output lacks venue keys {sorted(missing)}")
    out = out[list(inverse)].rename(columns=inverse).astype(float)
    if np.isinf(out.to_numpy()).any():
        raise ValueError("estimator output contains inf")
    if not out.index.is_unique:
        raise ValueError("estimator output index is not unique")
    out = out.reindex(index if cut is None else index[:cut])
    if (out[NUMERAIRE].abs() > 1e-9).any():
        raise ValueError("numeraire column must be 0")
    out[NUMERAIRE] = 0.0
    return out


# ---------------------------------------------------------------- scoring

def pair_gap(raw: dict[str, pd.DataFrame], asset: str, pair: tuple[str, str]) -> pd.Series:
    a, b = pair
    if asset not in raw[a].columns or asset not in raw[b].columns:
        return pd.Series(np.nan, index=raw[a].index)
    return 1e4 * (raw[a][asset] - raw[b][asset])


def score_parts(gs: dict[str, pd.Series], us: dict[str, pd.Series]) -> dict[str, Any]:
    """Pooled / per-asset / per-year score and coverage. NaN u_hat on an hour where g exists counts as 0."""
    rows = []
    for a, g in gs.items():
        m = g.notna()
        u = us[a].reindex(g.index)[m]
        rows.append(pd.DataFrame({"asset": a, "year": g.index[m].year, "g": g[m].to_numpy(),
                                  "u": u.fillna(0.0).to_numpy(), "has_u": u.notna().to_numpy()}))
    d = pd.concat(rows, ignore_index=True)
    d["e2"], d["g2"] = (d["g"] - d["u"]) ** 2, d["g"] ** 2

    def score(x: pd.DataFrame) -> float:
        den = x["g2"].sum()
        return float(1 - x["e2"].sum() / den) if den > 0 else float("nan")

    return {"score": score(d), "by_asset": {a: score(x) for a, x in d.groupby("asset")},
            "by_year": {int(y): score(x) for y, x in d.groupby("year")},
            "coverage": float(d["has_u"].mean()), "coverage_by_asset": {a: float(x["has_u"].mean()) for a, x in d.groupby("asset")},
            "n": int(len(d))}


def baseline_pair_u(raw: dict[str, pd.DataFrame], asset: str, pair: tuple[str, str], kind: str) -> pd.Series:
    """Harness-internal baselines for the pair gap, using only the visible columns (held-out asset excluded)."""
    vis = estimator_input(raw, asset, "dev")
    index = raw[pair[0]].index
    if kind == "b0":
        return pd.Series(0.0, index=index)
    if kind == "b1":
        return pair_gap(vis, "BTC", pair)
    if kind == "b2":
        shared = [c for c in vis[pair[0]].columns if not c.endswith("_vol") and c in vis[pair[1]].columns]
        gaps = pd.concat([pair_gap(vis, c, pair) for c in shared], axis=1)
        return gaps.median(axis=1, skipna=True)
    raise ValueError(kind)


# ---------------------------------------------------------------- evaluation

def evaluate(raw: dict[str, pd.DataFrame], factory: EstimatorFactory, mode: str, seed: int) -> dict[str, Any]:
    if mode not in ("dev", "final"):
        raise ValueError(mode)
    t0 = time.time()
    scored = P.DEV_SCORED if mode == "dev" else P.TEST_SCORED
    if mode == "dev":  # defence in depth: test assets are dropped even if a caller supplied them
        raw = {v: f[[c for c in f.columns if c.removesuffix("_vol") not in P.TEST_SCORED]] for v, f in raw.items()}
    needed = tuple(dict.fromkeys(tuple(scored) + (CONTROL_ASSET,) + CHECK_ASSETS))
    outs = {a: call_estimator(factory, raw, a, mode, seed) for a in needed}

    def gather(assets, pair, kind=None, start=None):
        gs, us = {}, {}
        for a in assets:
            g = pair_gap(raw, a, pair)
            u = (outs[a][pair[0]] - outs[a][pair[1]]) if kind is None else baseline_pair_u(raw, a, pair, kind)
            if start is not None:
                g, u = g[g.index >= start], u[u.index >= start]
            gs[a], us[a] = g, u
        return gs, us

    res: dict[str, Any] = {"mode": mode, "seed": seed}
    main = score_parts(*gather(scored, PAIR))
    ctrl = score_parts(*gather((CONTROL_ASSET,), CONTROL_PAIR, start=CONTROL_START))
    res["main"], res["control"] = main, ctrl
    for kind in ("b0", "b1", "b2"):
        res[kind] = score_parts(*gather(scored, PAIR, kind))["score"]
        res[kind + "_control"] = score_parts(*gather((CONTROL_ASSET,), CONTROL_PAIR, kind, CONTROL_START))["score"]
    res["coverage_ok"] = bool(min(list(main["coverage_by_asset"].values()) + [ctrl["coverage"]]) >= COVERAGE_MIN)

    # causal and permutation checks on CHECK_ASSETS
    n = len(next(iter(raw.values())))
    rng = np.random.default_rng(seed + 7)
    cuts = sorted(int(c) for c in rng.integers(int(0.2 * n), int(0.95 * n), N_CUTS))
    causal, worst = True, 0.0
    for a in CHECK_ASSETS:
        for cut in cuts:
            part = call_estimator(factory, raw, a, mode, seed, cut=cut)
            diff = _max_diff(part, outs[a].iloc[:cut])
            worst = max(worst, diff)
            causal &= diff <= TOL_BPS
    perm, worst_perm, seed2 = True, 0.0, seed + 1000
    while anonymise(list(raw), seed2) == anonymise(list(raw), seed):
        seed2 += 1
    for a in CHECK_ASSETS:
        alt = call_estimator(factory, raw, a, mode, seed2)
        diff = _max_diff(alt, outs[a])
        worst_perm = max(worst_perm, diff)
        perm &= diff <= TOL_BPS
    est_src = (REPO / "src" / "www_auto" / "estimator.py")
    stat, hits = static_ok(est_src.read_text()) if est_src.is_file() else (True, [])
    res.update(causal_ok=bool(causal), perm_ok=bool(perm), causal_max_diff_bps=worst, perm_max_diff_bps=worst_perm,
               cuts=cuts, static_ok=bool(stat), static_hits=hits,
               all_checks=bool(causal and perm and res["coverage_ok"] and stat), runtime_s=time.time() - t0)
    return res


FORBIDDEN_SOURCE = [  # static guard on estimator.py: no I/O, no environment, no hard-coded dates or venue names
    r"\bopen\(", r"\bimport\s+os\b", r"\bfrom\s+os\b", r"\bpathlib\b", r"\bPath\(", r"read_(parquet|csv|json|pickle)",
    r"\bsubprocess\b", r"\bimportlib\b", r"__import__", r"\beval\(", r"\bexec\(", r"www_auto\.(harness|panel)",
    r"\b(19|20)\d\d-\d\d", r"Timestamp\(\s*['\"]", r"(?i)bitfinex|coinbase|bitstamp|binance",
]


def static_ok(source: str) -> tuple[bool, list[str]]:
    import re
    hits = [pat for pat in FORBIDDEN_SOURCE if re.search(pat, source)]
    return not hits, hits


def _max_diff(a: pd.DataFrame, b: pd.DataFrame) -> float:
    x, y = a.to_numpy(float), b.reindex(index=a.index, columns=a.columns).to_numpy(float)
    if (np.isnan(x) != np.isnan(y)).any():
        return float("inf")
    both = ~np.isnan(x)
    return float(np.abs(x[both] - y[both]).max()) if both.any() else 0.0


def format_result(res: dict[str, Any]) -> list[str]:
    tag = "dev" if res["mode"] == "dev" else "test"
    f = lambda v: f"{v:.6f}"  # noqa: E731
    lines = [f"mode: {res['mode']}", f"seed: {res['seed']}",
             f"{tag}_score: {f(res['main']['score'])}", f"control_score: {f(res['control']['score'])}",
             f"causal_ok: {res['causal_ok']}", f"perm_ok: {res['perm_ok']}", f"coverage_ok: {res['coverage_ok']}",
             f"static_ok: {res['static_ok']}", f"static_hits: {res['static_hits']}",
             f"all_checks: {res['all_checks']}", f"runtime_s: {res['runtime_s']:.1f}",
             f"b0_{tag}: {f(res['b0'])}", f"b1_{tag}: {f(res['b1'])}", f"b2_{tag}: {f(res['b2'])}",
             f"b1_control: {f(res['b1_control'])}", f"b2_control: {f(res['b2_control'])}",
             f"coverage: {f(res['main']['coverage'])}", f"control_coverage: {f(res['control']['coverage'])}",
             f"causal_max_diff_bps: {res['causal_max_diff_bps']:.3g}", f"perm_max_diff_bps: {res['perm_max_diff_bps']:.3g}"]
    lines += [f"asset_{a}: {f(v)}" for a, v in res["main"]["by_asset"].items()]
    lines += [f"year_{y}: {f(v)}" for y, v in res["main"]["by_year"].items()]
    return lines


def main(argv: list[str] | None = None, root: Path = REPO, factory: EstimatorFactory | None = None,
         panel_path: Path | None = None) -> int:
    ap = argparse.ArgumentParser(prog="www_auto.harness")
    ap.add_argument("--final", action="store_true", help="locked test; needs autoresearch/FINAL_UNLOCK")
    ap.add_argument("--seed", type=int, default=None, help="anonymisation seed (default: random, printed)")
    args = ap.parse_args(argv)
    mode = "final" if args.final else "dev"
    if args.final and not (root / "autoresearch" / "FINAL_UNLOCK").is_file():
        print("refused: --final requires autoresearch/FINAL_UNLOCK, which does not exist", file=sys.stderr)
        return 2
    seed = args.seed if args.seed is not None else int.from_bytes(os.urandom(3), "big")
    try:
        raw, meta = P.load_panel(mode, panel_path or P.PANEL_PATH)
        res = evaluate(raw, factory or file_estimator_factory(), mode, seed)
    except Exception:  # noqa: BLE001 - a crashing estimator is a failed run, not a harness bug
        traceback.print_exc()
        print("crash: true")
        return 1
    print("\n".join(format_result(res)))
    return 0 if res["all_checks"] and np.isfinite(res["main"]["score"]) else 1


if __name__ == "__main__":
    sys.exit(main())
