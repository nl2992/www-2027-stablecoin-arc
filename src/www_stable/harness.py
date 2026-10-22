"""Fixed STABLE evaluation harness (read-only for the autoresearch loop).

    uv run python -m www_stable.harness              # dev mode: only dev-episode rows are loaded and passed on
    uv run python -m www_stable.harness --final      # locked test; refuses unless autoresearch/FINAL_UNLOCK_STABLE exists
    uv run python -m www_stable.harness --coverage   # also print hours present per episode window and market (diagnostic)

Task. For each episode window the fuser is called ONCE with that window's rows plus a 30-day warm-up:
    fuse(markets: dict[anon_market -> DataFrame], meta: dict[anon_market -> {"unit": anon_unit, "venue": anon_venue}],
         side: DataFrame) -> Series
A market is a (venue, quote unit) pair quoting BTC. Its frame holds hourly log prices ``BTC`` (and ``ETH`` where the venue
lists it in the same unit) and volumes ``BTC_vol`` / ``ETH_vol`` in the market's own quote unit. ``side`` holds anonymised
log rates ``"<unit a>/<unit b>@<venue>"`` (price of a in b: stablecoin cross-rates in the Binance quote unit, stablecoin/USD
rates on two other venues). Market, unit and venue labels are re-drawn at random on every call; stablecoin units and the
U.S. dollar get labels alike, so the fuser is NOT told which unit is the dollar. The fuser returns the fused log BTC/USD per
hour. Kraken BTC/USD is the reference: it is held by the harness, scores the output and is never passed on.

Error = 1e4 (fused - Kraken) in bps. Scorable hours = window hours where Kraken and B0 both exist; a method's missing output
on a scorable hour is replaced by B0, so withholding output cannot lower the error (coverage_ok separately requires output on
>= 99% of scorable hours in every episode). B2 (conversion) and the oracle use the real names inside the harness only.

rel_e = fuser MAE / B0 MAE per episode. dev_score = mean rel_e over S1..S3 (test_score over X1..X4 in --final).
Placebo constraint: rel_e <= 1.02 on every placebo episode (S3 in dev; X4 in final).

Checks: causal_ok (3 random truncations per window reproduce the full run before each cut, 1e-6 bps), perm_ok
(re-anonymisation changes nothing, 1e-6 bps), static_ok (fuser.py has no I/O, dates, venue or coin names, or imports other
than numpy/pandas), coverage_ok, placebo_ok.
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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import baselines as B
from . import panel as P

REPO = P.REPO
FUSER_PATH = Path(__file__).with_name("fuser.py")
UNLOCK = "autoresearch/FINAL_UNLOCK_STABLE"
N_CUTS = 3
TOL_BPS = 1e-6
COVERAGE_MIN = 0.99
PLACEBO_MAX = 1.02
THRESHOLDS = (25.0, 50.0)
METHODS = ("fuser", *B.METHODS)
FuserFactory = Callable[[], Callable[[dict, dict, pd.DataFrame], pd.Series]]

FORBIDDEN_SOURCE = [
    r"\bopen\(", r"\bimport\s+os\b", r"\bfrom\s+os\b", r"\bpathlib\b", r"\bPath\(", r"read_(parquet|csv|json|pickle)",
    r"\bsubprocess\b", r"\bimportlib\b", r"__import__", r"\beval\(", r"\bexec\(", r"www_auto", r"www_fuse", r"www_events",
    r"www_stable", r"\b(19|20)\d\d-\d\d", r"Timestamp\(\s*['\"]", r"(?i)bitfinex|coinbase|bitstamp|binance|kraken",
    r"(?i)(?<![a-z])(usdt|usdc|busd|tusd|fdusd|ust)(?![a-z])",
    r"(?m)^\s*(?:from|import)\s+(?!numpy\b|pandas\b|__future__\b|typing\b)",
]


def static_ok(source: str) -> tuple[bool, list[str]]:
    hits = [pat for pat in FORBIDDEN_SOURCE if re.search(pat, source)]
    return not hits, hits


def file_fuser_factory(path: Path = FUSER_PATH) -> FuserFactory:
    """Each call loads fuser.py as a brand new module, so module-level state cannot carry over between calls."""
    def make():
        spec = importlib.util.spec_from_file_location("_stable_fuser_instance", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.fuse
    return make


# ---------------------------------------------------------------- episode slices

@dataclass
class Window:
    """One fuser call: REAL-named rows from 30 days before the window to its end, plus the reference (harness only)."""
    markets: dict[str, pd.DataFrame]
    side: pd.DataFrame
    ref: pd.Series
    index: pd.DatetimeIndex
    lo: pd.Timestamp  # first scored hour
    hi: pd.Timestamp

    def scored(self) -> np.ndarray:
        return np.asarray((self.index >= self.lo) & (self.index <= self.hi))


def episode_windows(markets: dict[str, pd.DataFrame], side: pd.DataFrame, ref: pd.Series, ep: P.Episode) -> list[Window]:
    out = []
    for (lo, hi), (wlo, _) in zip(ep.bounds(), ep.load_bounds()):
        m = {}
        for name, frame in markets.items():
            f = frame[(frame.index >= wlo) & (frame.index <= hi)]
            if "BTC" in f.columns and f["BTC"].notna().any():  # a source is a market that quotes BTC in these rows
                m[name] = f.copy()
        idx = pd.date_range(wlo, hi, freq="h")
        s = side[(side.index >= wlo) & (side.index <= hi)]
        s = s.loc[:, s.notna().any()]
        out.append(Window(m, s, ref[(ref.index >= wlo) & (ref.index <= hi)], idx, lo, hi))
    return out


# ---------------------------------------------------------------- anonymisation

def _perm(names: list[str], seed: int, prefix: str) -> dict[str, str]:
    order = np.random.default_rng(seed).permutation(len(names))
    return {v: f"{prefix}{order[i]}" for i, v in enumerate(sorted(names))}


def _parse_side(col: str) -> tuple[str, str, str]:
    base, rest = col.split(".", 1)
    quote, venue = rest.split("@", 1)
    return base, quote, venue


def anonymise(w: Window, seed: int) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """(market map, unit map, venue map) real -> anonymous label. Units and venues cover markets and side series alike."""
    mk = sorted(w.markets)
    units = {k.split(".", 1)[1] for k in mk}
    venues = {k.split(".", 1)[0] for k in mk}
    for c in w.side.columns:
        a, b, v = _parse_side(c)
        units |= {a, b}
        venues.add(v)
    return _perm(mk, seed, "m"), _perm(sorted(units), seed + 3, "u"), _perm(sorted(venues), seed + 5, "v")


def fuser_inputs(w: Window, seed: int, cut: int | None = None) -> tuple[dict, dict, pd.DataFrame]:
    """The anonymised (markets, meta, side) a fuser receives; rows are cut to the first ``cut`` hours if given."""
    mm, um, vm = anonymise(w, seed)
    names = sorted(w.markets)
    order = np.random.default_rng(seed + 1).permutation(len(names))
    markets, meta = {}, {}
    n = len(w.index) if cut is None else cut
    for i in order:
        real = names[i]
        venue, unit = real.split(".", 1)
        f = w.markets[real].reindex(w.index).iloc[:n]
        cols = list(f.columns)
        cols = [cols[j] for j in np.random.default_rng(seed + 2 + int(i)).permutation(len(cols))]
        markets[mm[real]] = f[cols].copy()
        meta[mm[real]] = {"unit": um[unit], "venue": vm[venue]}
    used = {m["unit"] for m in meta.values()}
    keep = []
    for c in w.side.columns:
        a, b, _ = _parse_side(c)
        if um[a] in used and um[b] in used:
            keep.append(c)
    side = w.side.reindex(w.index).iloc[:n][keep]
    side = side.rename(columns=lambda c: "{}/{}@{}".format(um[_parse_side(c)[0]], um[_parse_side(c)[1]], vm[_parse_side(c)[2]]))
    side = side[[side.columns[j] for j in np.random.default_rng(seed + 9).permutation(len(side.columns))]]
    return markets, meta, side.copy()


def call_fuser(factory: FuserFactory, w: Window, seed: int, cut: int | None = None) -> pd.Series:
    markets, meta, side = fuser_inputs(w, seed, cut)
    out = factory()(markets, meta, side)
    if not isinstance(out, pd.Series):
        raise TypeError("fuser must return a Series")
    if not out.index.is_unique:
        raise ValueError("fuser output index is not unique")
    out = out.astype(float)
    if np.isinf(out.to_numpy()).any():
        raise ValueError("fuser output contains inf")
    return out.reindex(w.index if cut is None else w.index[:cut])


def _max_diff_bps(a: pd.Series, b: pd.Series) -> float:
    x, y = 1e4 * a.to_numpy(float), 1e4 * b.reindex(a.index).to_numpy(float)
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


def score_episode(parts: list[tuple[Window, pd.DataFrame]]) -> dict[str, Any]:
    """Pooled error stats per method over the scorable hours of every window; also each method's output coverage."""
    errs: dict[str, list[np.ndarray]] = {m: [] for m in METHODS}
    have = {m: 0 for m in METHODS}
    total = 0
    for w, methods in parts:
        ref = w.ref.reindex(w.index).to_numpy(float)
        b0 = methods["B0"].to_numpy(float)
        ok = w.scored() & np.isfinite(ref) & np.isfinite(b0)
        total += int(ok.sum())
        for m in METHODS:
            f = methods[m].to_numpy(float)[ok]
            errs[m].append(1e4 * (np.where(np.isfinite(f), f, b0[ok]) - ref[ok]))
            have[m] += int(np.isfinite(f).sum())
    out: dict[str, Any] = {"hours": total, "methods": {}}
    for m in METHODS:
        st = error_stats(np.concatenate(errs[m]) if errs[m] else np.array([]))
        st["coverage"] = have[m] / total if total else float("nan")
        out["methods"][m] = st
    return out


def presence(windows: list[Window]) -> list[dict[str, Any]]:
    """Hours with a price inside each scored window (and in its warm-up), per market and item (diagnostic; real names)."""
    out = []
    for w in windows:
        win, warm = w.scored(), ~w.scored()
        rows = {}
        for name, f in sorted(w.markets.items()):
            f = f.reindex(w.index)
            rows[name] = {"BTC": int(f.loc[win, "BTC"].notna().sum()) if "BTC" in f else 0,
                          "ETH": int(f.loc[win, "ETH"].notna().sum()) if "ETH" in f else 0,
                          "warm_BTC": int(f.loc[warm, "BTC"].notna().sum()) if "BTC" in f else 0}
        rows["side"] = {c: int(w.side[c].reindex(w.index)[win].notna().sum()) for c in w.side.columns}
        rows["reference"] = {"BTC": int(w.ref.reindex(w.index)[win].notna().sum())}
        out.append({"hours": int(win.sum()), "rows": rows})
    return out


# ---------------------------------------------------------------- evaluation

def evaluate(markets: dict[str, pd.DataFrame], side: pd.DataFrame, ref: pd.Series, factory: FuserFactory, mode: str, seed: int,
             episodes: tuple[P.Episode, ...] = P.EPISODES, fuser_path: Path | None = FUSER_PATH) -> dict[str, Any]:
    t0 = time.time()
    eps = P.episodes_for(mode, episodes)
    res: dict[str, Any] = {"mode": mode, "seed": seed, "episodes": {}, "presence": {}}
    causal = perm = True
    worst_c = worst_p = 0.0
    for ep in eps:
        wins = episode_windows(markets, side, ref, ep)
        parts = []
        for w in wins:
            base = B.all_baselines(w.markets, w.side, w.index)
            full = call_fuser(factory, w, seed)
            parts.append((w, pd.DataFrame({"fuser": full, **base})))
            n = len(full)
            rng = np.random.default_rng(seed + 7)
            for cut in sorted(int(c) for c in rng.integers(int(0.2 * n), int(0.95 * n), N_CUTS)):
                d = _max_diff_bps(call_fuser(factory, w, seed, cut=cut), full.iloc[:cut])
                worst_c, causal = max(worst_c, d), causal and d <= TOL_BPS
            seed2 = seed + 1000
            while anonymise(w, seed2) == anonymise(w, seed):
                seed2 += 1
            d = _max_diff_bps(call_fuser(factory, w, seed2), full)
            worst_p, perm = max(worst_p, d), perm and d <= TOL_BPS
        res["episodes"][ep.name] = score_episode(parts)
        res["presence"][ep.name] = presence(wins)
    rel = {}
    for name, e in res["episodes"].items():
        base = e["methods"]["B0"]["mae"]
        for st in e["methods"].values():
            st["rel_e"] = st["mae"] / base if base > 0 else float("nan")
        rel[name] = e["methods"]["fuser"]["rel_e"]
    res["score"] = float(np.mean(list(rel.values()))) if rel else float("nan")
    placebo = [ep.name for ep in eps if ep.calm]
    res["placebo_ok"] = bool(all(rel[c] <= PLACEBO_MAX for c in placebo))
    res["coverage_ok"] = bool(all(e["methods"]["fuser"]["coverage"] >= COVERAGE_MIN for e in res["episodes"].values()))
    stat, hits = static_ok(fuser_path.read_text()) if fuser_path is not None and fuser_path.is_file() else (True, [])
    res.update(causal_ok=bool(causal), perm_ok=bool(perm), causal_max_diff_bps=worst_c, perm_max_diff_bps=worst_p,
               static_ok=bool(stat), static_hits=hits, placebo_episodes=placebo,
               all_checks=bool(causal and perm and stat and res["coverage_ok"] and res["placebo_ok"]),
               runtime_s=time.time() - t0)
    return res


def format_result(res: dict[str, Any], coverage: bool = False) -> list[str]:
    tag = "dev" if res["mode"] == "dev" else "test"
    f = lambda v: f"{v:.6f}"  # noqa: E731
    lines = [f"mode: {res['mode']}", f"seed: {res['seed']}", f"{tag}_score: {f(res['score'])}",
             f"causal_ok: {res['causal_ok']}", f"perm_ok: {res['perm_ok']}", f"static_ok: {res['static_ok']}",
             f"static_hits: {res['static_hits']}", f"coverage_ok: {res['coverage_ok']}", f"placebo_ok: {res['placebo_ok']}",
             f"all_checks: {res['all_checks']}", f"runtime_s: {res['runtime_s']:.1f}",
             f"causal_max_diff_bps: {res['causal_max_diff_bps']:.3g}", f"perm_max_diff_bps: {res['perm_max_diff_bps']:.3g}"]
    for ep, e in res["episodes"].items():
        lines.append(f"hours_{ep}: {e['hours']}")
        for m, st in e["methods"].items():
            lines += [f"mae_{ep}_{m}: {st['mae']:.4f}", f"rel_e_{ep}_{m}: {f(st['rel_e'])}", f"p95_{ep}_{m}: {st['p95']:.4f}",
                      f"n25_{ep}_{m}: {st['n25']}", f"n50_{ep}_{m}: {st['n50']}", f"cov_{ep}_{m}: {st['coverage']:.4f}"]
    if coverage:
        for ep, wins in res["presence"].items():
            for k, win in enumerate(wins):
                for name, items in win["rows"].items():
                    lines.append(f"present_{ep}[{k}]_{name}: " + " ".join(f"{a}={n}" for a, n in items.items()))
    return lines


def main(argv: list[str] | None = None, root: Path = REPO, factory: FuserFactory | None = None,
         panel_path: Path | None = None, episodes: tuple[P.Episode, ...] = P.EPISODES) -> int:
    ap = argparse.ArgumentParser(prog="www_stable.harness")
    ap.add_argument("--final", action="store_true", help=f"locked test; needs {UNLOCK}")
    ap.add_argument("--seed", type=int, default=None, help="anonymisation seed (default: random, printed)")
    ap.add_argument("--coverage", action="store_true", help="also print hours present per window and market")
    args = ap.parse_args(argv)
    mode = "final" if args.final else "dev"
    if args.final and not (root / UNLOCK).is_file():
        print(f"refused: --final requires {UNLOCK}, which does not exist", file=sys.stderr)
        return 2
    seed = args.seed if args.seed is not None else int.from_bytes(os.urandom(3), "big")
    try:
        markets, side, ref, _ = P.load_panel(mode, panel_path or P.PANEL_PATH, episodes)
        res = evaluate(markets, side, ref, factory or file_fuser_factory(), mode, seed, episodes,
                       FUSER_PATH if factory is None else None)
    except Exception:  # noqa: BLE001 - a crashing fuser is a failed run, not a harness bug
        traceback.print_exc()
        print("crash: true")
        return 1
    print("\n".join(format_result(res, args.coverage)))
    return 0 if res["all_checks"] and np.isfinite(res["score"]) else 1


if __name__ == "__main__":
    sys.exit(main())
