"""Fixed FUSE evaluation harness (read-only for the autoresearch loop).

    uv run python -m www_fuse.harness              # dev mode: only dev-episode rows are loaded and passed on
    uv run python -m www_fuse.harness --final      # locked test; refuses unless autoresearch/FINAL_UNLOCK_FUSE exists
    uv run python -m www_fuse.harness --coverage   # also print hours present per episode, source and item (diagnostic)

Task. For each episode the fuser is called ONCE with that episode's rows plus a 30-day warm-up before the window:
    fuse(panel: dict[anon_source -> DataFrame], items: list[str]) -> DataFrame[hours x items] of fused log prices.
Only the episode window is scored. Error = 1e4 (fused - Kraken) in bps on BTC and ETH hours where Kraken exists, pooled
over both items; Kraken columns are held by the harness and never passed to the fuser. Source keys are anonymised with a
printed seed ('s0', 's1', ... in a random order, columns shuffled too). A source is passed on only if it quotes anything
in the episode's rows (Binance.US appears from 2022-10).
Scorable hours = item-hours where Kraken and the plain median both exist. A method's missing output on a scorable hour is
replaced by the median (no correction), so withholding output cannot lower the error; coverage_ok separately requires the
fuser's output on >= 99% of scorable hours in every episode.

rel_e = fuser MAE / median MAE per episode. dev_score = mean rel_e over D1..D3 (test_score over T1..T5 in --final).

Checks: causal_ok (3 random truncations per episode reproduce the full run before each cut, 1e-6 bps), perm_ok
(re-anonymisation changes nothing, 1e-6 bps), static_ok (fuser.py has no I/O, dates, venue names, kraken, or imports other
than numpy/pandas), coverage_ok, calm_ok (rel_e <= 1.02 on every calm episode: D2 and D3 in dev).
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import baselines as B
from . import panel as P

REPO = P.REPO
FUSER_PATH = Path(__file__).with_name("fuser.py")
UNLOCK = "autoresearch/FINAL_UNLOCK_FUSE"
ITEMS = list(P.FUSED)
N_CUTS = 3
TOL_BPS = 1e-6
COVERAGE_MIN = 0.99
CALM_MAX = 1.02
THRESHOLDS = (25.0, 50.0)
FuserFactory = Callable[[], Callable[[dict[str, pd.DataFrame], list[str]], pd.DataFrame]]

FORBIDDEN_SOURCE = [
    r"\bopen\(", r"\bimport\s+os\b", r"\bfrom\s+os\b", r"\bpathlib\b", r"\bPath\(", r"read_(parquet|csv|json|pickle)",
    r"\bsubprocess\b", r"\bimportlib\b", r"__import__", r"\beval\(", r"\bexec\(", r"www_auto", r"www_fuse", r"www_events",
    r"\b(19|20)\d\d-\d\d", r"Timestamp\(\s*['\"]", r"(?i)bitfinex|coinbase|bitstamp|binance|kraken",
    r"(?m)^\s*(?:from|import)\s+(?!numpy\b|pandas\b|__future__\b|typing\b)",
]


def static_ok(source: str) -> tuple[bool, list[str]]:
    hits = [pat for pat in FORBIDDEN_SOURCE if re.search(pat, source)]
    return not hits, hits


def file_fuser_factory(path: Path = FUSER_PATH) -> FuserFactory:
    """Each call loads fuser.py as a brand new module, so module-level state cannot carry over between calls."""
    def make():
        spec = importlib.util.spec_from_file_location("_fuse_fuser_instance", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.fuse
    return make


def anonymise(names: list[str], seed: int) -> dict[str, str]:
    order = np.random.default_rng(seed).permutation(len(names))
    return {v: f"s{order[i]}" for i, v in enumerate(sorted(names))}


# ---------------------------------------------------------------- episode slices

def episode_slice(sources: dict[str, pd.DataFrame], ep: P.Episode) -> dict[str, pd.DataFrame]:
    """Rows from 30 days before the window to its end; sources that quote nothing in those rows are dropped."""
    lo, hi = ep.load_bounds()
    out = {}
    for name, frame in sources.items():
        f = frame[(frame.index >= lo) & (frame.index <= hi)]
        price_cols = [c for c in f.columns if not c.endswith("_vol")]
        if price_cols and f[price_cols].notna().any().any():
            out[name] = f.copy()
    return out


def call_fuser(factory: FuserFactory, sl: dict[str, pd.DataFrame], seed: int, cut: int | None = None) -> pd.DataFrame:
    """One fuser call on the anonymised slice; returns the fused log prices (hours x ITEMS) on the slice index."""
    index = next(iter(sl.values())).index
    mapping = anonymise(list(sl), seed)
    names = sorted(sl)
    order = np.random.default_rng(seed + 1).permutation(len(names))
    anon = {}
    for i in order:
        f = sl[names[i]]
        if cut is not None:
            f = f.iloc[:cut]
        cols = list(f.columns)
        cols = [cols[j] for j in np.random.default_rng(seed + 2 + int(i)).permutation(len(cols))]
        anon[mapping[names[i]]] = f[cols].copy()
    out = factory()(anon, list(ITEMS))
    if not isinstance(out, pd.DataFrame):
        raise TypeError("fuser must return a DataFrame")
    missing = set(ITEMS) - set(out.columns)
    if missing:
        raise ValueError(f"fuser output lacks items {sorted(missing)}")
    if not out.index.is_unique:
        raise ValueError("fuser output index is not unique")
    out = out[ITEMS].astype(float)
    if np.isinf(out.to_numpy()).any():
        raise ValueError("fuser output contains inf")
    return out.reindex(index if cut is None else index[:cut])


def _max_diff_bps(a: pd.DataFrame, b: pd.DataFrame) -> float:
    x, y = 1e4 * a.to_numpy(float), 1e4 * b.reindex(index=a.index, columns=a.columns).to_numpy(float)
    if (np.isnan(x) != np.isnan(y)).any():
        return float("inf")
    both = ~np.isnan(x)
    return float(np.abs(x[both] - y[both]).max()) if both.any() else 0.0


# ---------------------------------------------------------------- scoring

def error_stats(err: np.ndarray) -> dict[str, float]:
    a = np.abs(err)
    if len(a) == 0:
        return {"n": 0, "mae": float("nan"), "p95": float("nan"), "n25": 0, "n50": 0}
    return {"n": int(len(a)), "mae": float(a.mean()), "p95": float(np.quantile(a, 0.95)),
            "n25": int((a >= THRESHOLDS[0]).sum()), "n50": int((a >= THRESHOLDS[1]).sum())}


def score_episode(ep: P.Episode, methods: dict[str, pd.DataFrame], ref: pd.DataFrame) -> dict[str, Any]:
    """Pooled error stats per method on the episode's scorable item-hours; also each method's output coverage."""
    idx = methods["median"].index
    win = ep.scored_mask(idx)
    ref = ref.reindex(idx)
    med = methods["median"]
    scorable = {a: win & ref[a].notna().to_numpy() & med[a].notna().to_numpy() for a in ITEMS}
    out: dict[str, Any] = {"hours": {a: int(scorable[a].sum()) for a in ITEMS}, "methods": {}}
    for name, df in methods.items():
        errs, have, tot = [], 0, 0
        for a in ITEMS:
            m = scorable[a]
            f = df[a].to_numpy(float)[m]
            fused = np.where(np.isfinite(f), f, med[a].to_numpy(float)[m])
            errs.append(1e4 * (fused - ref[a].to_numpy(float)[m]))
            have += int(np.isfinite(f).sum())
            tot += int(m.sum())
        st = error_stats(np.concatenate(errs))
        st["coverage"] = have / tot if tot else float("nan")
        out["methods"][name] = st
    return out


def presence(sl: dict[str, pd.DataFrame], ref: pd.DataFrame, ep: P.Episode) -> dict[str, dict[str, int]]:
    """Hours with a price in the episode window, per source and item (diagnostic; real names)."""
    out: dict[str, dict[str, int]] = {}
    for name, frame in {**sl, P.REFERENCE: ref.reindex(next(iter(sl.values())).index)}.items():
        win = ep.scored_mask(frame.index)
        out[name] = {a: int(frame.loc[win, a].notna().sum()) for a in (*ITEMS, "USDT") if a in frame.columns}
    return out


# ---------------------------------------------------------------- evaluation

def evaluate(sources: dict[str, pd.DataFrame], ref: pd.DataFrame, factory: FuserFactory, mode: str, seed: int,
             episodes: tuple[P.Episode, ...] = P.EPISODES, fuser_path: Path | None = FUSER_PATH) -> dict[str, Any]:
    t0 = time.time()
    eps = P.episodes_for(mode, episodes)
    ref = ref[[c for c in ref.columns if c in ITEMS]]
    res: dict[str, Any] = {"mode": mode, "seed": seed, "episodes": {}, "presence": {}}
    causal = perm = True
    worst_c = worst_p = 0.0
    for ep in eps:
        sl = episode_slice(sources, ep)
        warm = min(P.WARMUP_HOURS, len(next(iter(sl.values()))))
        methods = B.all_baselines(sl, ITEMS, warm)
        full = call_fuser(factory, sl, seed)
        methods = {"fuser": full, **methods}
        res["episodes"][ep.name] = score_episode(ep, methods, ref)
        res["presence"][ep.name] = presence(sl, ref, ep)
        n = len(full)
        rng = np.random.default_rng(seed + 7)
        for cut in sorted(int(c) for c in rng.integers(int(0.2 * n), int(0.95 * n), N_CUTS)):
            d = _max_diff_bps(call_fuser(factory, sl, seed, cut=cut), full.iloc[:cut])
            worst_c, causal = max(worst_c, d), causal and d <= TOL_BPS
        seed2 = seed + 1000
        while anonymise(list(sl), seed2) == anonymise(list(sl), seed):
            seed2 += 1
        d = _max_diff_bps(call_fuser(factory, sl, seed2), full)
        worst_p, perm = max(worst_p, d), perm and d <= TOL_BPS
    rel = {}
    for name, e in res["episodes"].items():
        base = e["methods"]["median"]["mae"]
        for m, st in e["methods"].items():
            st["rel_e"] = st["mae"] / base if base > 0 else float("nan")
        rel[name] = e["methods"]["fuser"]["rel_e"]
    res["score"] = float(np.mean(list(rel.values()))) if rel else float("nan")
    calm = [ep.name for ep in eps if ep.calm]
    res["calm_ok"] = bool(all(rel[c] <= CALM_MAX for c in calm))
    res["coverage_ok"] = bool(all(e["methods"]["fuser"]["coverage"] >= COVERAGE_MIN for e in res["episodes"].values()))
    stat, hits = static_ok(fuser_path.read_text()) if fuser_path is not None and fuser_path.is_file() else (True, [])
    res.update(causal_ok=bool(causal), perm_ok=bool(perm), causal_max_diff_bps=worst_c, perm_max_diff_bps=worst_p,
               static_ok=bool(stat), static_hits=hits, calm_episodes=calm,
               all_checks=bool(causal and perm and stat and res["coverage_ok"] and res["calm_ok"]),
               runtime_s=time.time() - t0)
    return res


def format_result(res: dict[str, Any], coverage: bool = False) -> list[str]:
    tag = "dev" if res["mode"] == "dev" else "test"
    f = lambda v: f"{v:.6f}"  # noqa: E731
    lines = [f"mode: {res['mode']}", f"seed: {res['seed']}", f"{tag}_score: {f(res['score'])}",
             f"causal_ok: {res['causal_ok']}", f"perm_ok: {res['perm_ok']}", f"static_ok: {res['static_ok']}",
             f"static_hits: {res['static_hits']}", f"coverage_ok: {res['coverage_ok']}", f"calm_ok: {res['calm_ok']}",
             f"all_checks: {res['all_checks']}", f"runtime_s: {res['runtime_s']:.1f}",
             f"causal_max_diff_bps: {res['causal_max_diff_bps']:.3g}", f"perm_max_diff_bps: {res['perm_max_diff_bps']:.3g}"]
    for ep, e in res["episodes"].items():
        lines.append(f"hours_{ep}: " + " ".join(f"{a}={n}" for a, n in e["hours"].items()))
        for m, st in e["methods"].items():
            lines += [f"mae_{ep}_{m}: {st['mae']:.4f}", f"rel_e_{ep}_{m}: {f(st['rel_e'])}", f"p95_{ep}_{m}: {st['p95']:.4f}",
                      f"n25_{ep}_{m}: {st['n25']}", f"n50_{ep}_{m}: {st['n50']}", f"cov_{ep}_{m}: {st['coverage']:.4f}"]
    if coverage:
        for ep, pres in res["presence"].items():
            for src, items in pres.items():
                lines.append(f"present_{ep}_{src}: " + " ".join(f"{a}={n}" for a, n in items.items()))
    return lines


def main(argv: list[str] | None = None, root: Path = REPO, factory: FuserFactory | None = None,
         panel_path: Path | None = None, episodes: tuple[P.Episode, ...] = P.EPISODES) -> int:
    ap = argparse.ArgumentParser(prog="www_fuse.harness")
    ap.add_argument("--final", action="store_true", help=f"locked test; needs {UNLOCK}")
    ap.add_argument("--seed", type=int, default=None, help="anonymisation seed (default: random, printed)")
    ap.add_argument("--coverage", action="store_true", help="also print hours present per episode, source and item")
    args = ap.parse_args(argv)
    mode = "final" if args.final else "dev"
    if args.final and not (root / UNLOCK).is_file():
        print(f"refused: --final requires {UNLOCK}, which does not exist", file=sys.stderr)
        return 2
    seed = args.seed if args.seed is not None else int.from_bytes(os.urandom(3), "big")
    try:
        sources, ref, _ = P.load_panel(mode, panel_path or P.PANEL_PATH, episodes)
        res = evaluate(sources, ref, factory or file_fuser_factory(), mode, seed, episodes,
                       FUSER_PATH if factory is None else None)
    except Exception:  # noqa: BLE001 - a crashing fuser is a failed run, not a harness bug
        traceback.print_exc()
        print("crash: true")
        return 1
    print("\n".join(format_result(res, args.coverage)))
    return 0 if res["all_checks"] and np.isfinite(res["score"]) else 1


if __name__ == "__main__":
    sys.exit(main())
