"""Post-hoc uncertainty and baseline evaluation of the FROZEN estimator (commit 724455b); scoring only, never tuning.

    uv run python -m www_auto.posthoc_eval        # writes reports/unit_td/posthoc.json

Authorized by the author after the single locked test had run. It does not use the harness ``--final`` CLI; it loads the
panel with the test assets and reuses the harness scoring functions by import. Sections:
  (a) Bitfinex--Coinbase, dev and test assets, leave-one-asset-out; b0/b1/b2/estimator, pooled, per asset, per year;
      reproduction of the logged test score (autoresearch/final_test_724455b.log) to 1e-6 first.
  (b) 95% block-bootstrap intervals (blocks = ISO weeks, 1,000 draws, fixed seed) incl. the estimator-minus-b2 difference.
  (c)/(d) multi-asset controls over 2019-2023: Coinbase--Bitstamp (shared dollar) and Bitfinex--Bitstamp, held-out assets
      ETH, LTC, BCH, XLM, LINK, XRP (BTC is visible-only). Extra Bitstamp hourly series come from data/raw/bitstamp_1h.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import harness as H
from . import panel as P

REPO = P.REPO
OUT = REPO / "reports" / "unit_td" / "posthoc.json"
FINAL_LOG = REPO / "autoresearch" / "final_test_724455b.log"
SEED = 20261020  # the anonymisation seed of the logged final run
BOOT_SEED = 20261021
N_BOOT = 1000
REPRO_TOL = 1e-6
BITSTAMP_ALTS = ("LTC", "XRP", "XLM", "LINK", "BCH")
CONTROL_ASSETS = ("ETH", "LTC", "BCH", "XLM", "LINK", "XRP")
CONTROL_PAIRS = {"coinbase-bitstamp": ("coinbase", "bitstamp"), "bitfinex-bitstamp": ("bitfinex", "bitstamp")}
METHODS = ("b0", "b1", "b2", "est")


# ---------------------------------------------------------------- data

def load_raw(with_bitstamp_alts: bool, root: Path = REPO) -> dict[str, pd.DataFrame]:
    """Panel including test assets; optionally with the Bitstamp hourly altcoin series added (cleaned like all series)."""
    panel, _ = P.load_panel("final")
    panel = {v: f.copy() for v, f in panel.items()}
    if with_bitstamp_alts:
        records = P._manifest_records(P.MANIFEST)
        for asset in BITSTAMP_ALTS:
            frame, _h = P.read_hourly_csv(root / "data" / "raw" / "bitstamp_1h" / f"{asset}USD-1h-2017-2023.csv",
                                          "bitstamp-1h", records)
            cleaned = P.clean_series(frame, {})
            panel["bitstamp"][asset] = cleaned["p"]
            panel["bitstamp"][asset + "_vol"] = cleaned["v"]
    return panel


def parse_log(path: Path = FINAL_LOG) -> dict[str, float]:
    out = {}
    for line in path.read_text().splitlines():
        m = re.match(r"(\w+): (-?\d+\.\d+)$", line.strip())
        if m:
            out[m.group(1)] = float(m.group(2))
    return out


# ---------------------------------------------------------------- cells and bootstrap

def gather(raw, outs, assets, pair, kind=None, start=None):
    gs, us = {}, {}
    for a in assets:
        g = H.pair_gap(raw, a, pair)
        u = (outs[a][pair[0]] - outs[a][pair[1]]) if kind in (None, "est") else H.baseline_pair_u(raw, a, pair, kind)
        if start is not None:
            g, u = g[g.index >= start], u[u.index >= start]
        gs[a], us[a] = g, u
    return gs, us


def cells(gs: dict[str, pd.Series], us: dict[str, pd.Series]) -> pd.DataFrame:
    """One row per (asset, hour with g): same fill rule as the harness (missing u counts as 0)."""
    rows = []
    for a, g in gs.items():
        m = g.notna()
        u = us[a].reindex(g.index)[m].fillna(0.0).to_numpy()
        iso = g.index[m].isocalendar()
        rows.append(pd.DataFrame({"asset": a, "year": g.index[m].year, "wk": (iso["year"] * 100 + iso["week"]).to_numpy(),
                                  "g2": g[m].to_numpy() ** 2, "e2": (g[m].to_numpy() - u) ** 2, "abs_u": np.abs(u)}))
    return pd.concat(rows, ignore_index=True)


def _sums(d: pd.DataFrame, widx: np.ndarray, n: int, col: str, mask: np.ndarray) -> np.ndarray:
    return np.bincount(widx[mask], weights=d[col].to_numpy()[mask], minlength=n)


def bootstrap(parts: dict[str, pd.DataFrame], diff: tuple[str, str] | None = ("est", "b2"), n_boot: int = N_BOOT,
              seed: int = BOOT_SEED) -> dict[str, Any]:
    """Block (ISO-week) bootstrap. parts: method -> cells (identical g cells). Returns {group: {method: stat}} with
    groups 'pooled', 'asset:X', 'year:Y'; stat = {point, lo, hi}; the difference appears as method 'diff'."""
    ref = next(iter(parts.values()))
    weeks = np.array(sorted(ref["wk"].unique()))
    widx = np.searchsorted(weeks, ref["wk"].to_numpy())
    n = len(weeks)
    counts = np.random.default_rng(seed).multinomial(n, np.full(n, 1.0 / n), size=n_boot).astype(float)
    groups: dict[str, np.ndarray] = {"pooled": np.ones(len(ref), bool)}
    groups.update({f"asset:{a}": (ref["asset"] == a).to_numpy() for a in sorted(ref["asset"].unique())})
    groups.update({f"year:{y}": (ref["year"] == y).to_numpy() for y in sorted(ref["year"].unique())})
    out: dict[str, Any] = {}
    for gname, mask in groups.items():
        G = _sums(ref, widx, n, "g2", mask)
        point, draws = {}, {}
        for m, d in parts.items():
            E = _sums(d, widx, n, "e2", mask)
            point[m] = 1.0 - E.sum() / G.sum() if G.sum() > 0 else float("nan")
            with np.errstate(invalid="ignore", divide="ignore"):
                draws[m] = 1.0 - (counts @ E) / (counts @ G)
        if diff:
            point["diff"], draws["diff"] = point[diff[0]] - point[diff[1]], draws[diff[0]] - draws[diff[1]]
        out[gname] = {m: {"point": float(point[m]), "lo": float(np.nanpercentile(draws[m], 2.5)),
                          "hi": float(np.nanpercentile(draws[m], 97.5))} for m in point}
    return out


def mean_abs_correction(d: pd.DataFrame) -> dict[str, float]:
    out = {"pooled": float(d["abs_u"].mean())}
    out.update({a: float(x["abs_u"].mean()) for a, x in d.groupby("asset")})
    return out


# ---------------------------------------------------------------- sections

def run_estimator(raw, assets, seed=SEED):
    factory = H.file_estimator_factory()
    return {a: H.call_estimator(factory, raw, a, "final", seed) for a in assets}


def section_a(raw) -> dict[str, Any]:
    outs = run_estimator(raw, P.DEV_SCORED + P.TEST_SCORED)
    res: dict[str, Any] = {}
    for split, assets in (("test", P.TEST_SCORED), ("dev", P.DEV_SCORED)):
        parts, points = {}, {}
        for kind in METHODS:
            gs, us = gather(raw, outs, assets, H.PAIR, kind)
            parts[kind] = cells(gs, us)
            points[kind] = H.score_parts(gs, us)
        boot = bootstrap(parts)
        res[split] = {"assets": list(assets), "n_hours": int(points["est"]["n"]), "bootstrap": boot,
                      "harness_points": {k: {"score": v["score"], "by_asset": v["by_asset"], "by_year": v["by_year"]}
                                         for k, v in points.items()}}
    return res


def reproduction(a: dict[str, Any], log: dict[str, float]) -> dict[str, Any]:
    pts = a["test"]["harness_points"]
    checks = {"test_score": (pts["est"]["score"], log["test_score"]), "b0_test": (pts["b0"]["score"], log["b0_test"]),
              "b1_test": (pts["b1"]["score"], log["b1_test"]), "b2_test": (pts["b2"]["score"], log["b2_test"])}
    checks.update({f"asset_{k}": (v, log[f"asset_{k}"]) for k, v in pts["est"]["by_asset"].items()})
    checks.update({f"year_{k}": (v, log[f"year_{k}"]) for k, v in pts["est"]["by_year"].items()})
    rows = {k: {"recomputed": float(x), "logged": float(y), "abs_diff": float(abs(x - y))} for k, (x, y) in checks.items()}
    return {"tolerance": REPRO_TOL, "ok": bool(all(r["abs_diff"] <= REPRO_TOL for r in rows.values())), "checks": rows}


def section_controls(raw) -> dict[str, Any]:
    outs = run_estimator(raw, CONTROL_ASSETS)
    res: dict[str, Any] = {}
    for name, pair in CONTROL_PAIRS.items():
        parts, points, mac = {}, {}, {}
        for kind in METHODS:
            gs, us = gather(raw, outs, CONTROL_ASSETS, pair, kind, H.CONTROL_START)
            parts[kind] = cells(gs, us)
            points[kind] = H.score_parts(gs, us)
            mac[kind] = mean_abs_correction(parts[kind])
        res[name] = {"pair": list(pair), "assets": list(CONTROL_ASSETS), "visible_only": ["BTC"],
                     "start": str(H.CONTROL_START.date()), "n_hours": int(points["est"]["n"]),
                     "n_by_asset": {a: int((parts["est"]["asset"] == a).sum()) for a in CONTROL_ASSETS},
                     "bootstrap": bootstrap(parts), "mean_abs_correction_bps": mac,
                     "harness_points": {k: {"score": v["score"], "by_asset": v["by_asset"]} for k, v in points.items()}}
    return res


def build(root: Path = REPO) -> dict[str, Any]:
    raw_a = load_raw(False, root)
    a = section_a(raw_a)
    repro = reproduction(a, parse_log())
    if not repro["ok"]:
        raise SystemExit("reproduction of the logged final test failed:\n" + json.dumps(repro, indent=1))
    ctrl = section_controls(load_raw(True, root))
    est_src = (Path(H.EST_PATH)).read_bytes()
    return {"estimator_sha256": hashlib.sha256(est_src).hexdigest(), "anonymisation_seed": SEED,
            "bootstrap": {"block": "ISO week", "draws": N_BOOT, "seed": BOOT_SEED, "interval": "95% percentile"},
            "reproduction": repro, "bitfinex_coinbase": a, "controls": ctrl}


def main() -> int:
    res = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
