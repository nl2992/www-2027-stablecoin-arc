"""Anchored-test robustness grid: bootstrap correctness, determinism, reproduction of the headline, freshness of the outputs."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from www_paper import robust_anchor_macros as M  # noqa: E402
from www_theory import gmm, robustness as R  # noqa: E402


def test_block_means_match_explicit_resampling():
    rng = np.random.default_rng(3)
    x = rng.normal(size=(103, 3))
    got = R.block_means(x, 10, 7, np.random.default_rng(9))
    idx = gmm.mbb_indices(103, 10, 7, np.random.default_rng(9))
    assert got == pytest.approx(x[idx].mean(1), abs=1e-12)


def test_bootstrap_interval_covers_a_planted_slope_and_is_seeded():
    rng = np.random.default_rng(5)
    n = 2000
    z = rng.normal(size=n)
    x = z + rng.normal(size=n)
    y = 0.8 * x + rng.normal(size=n)
    a, B, W = R._moments(y, x, z[:, None])
    v1, v2 = R.boot_lams(a, B, W, 24, 300, 1), R.boot_lams(a, B, W, 24, 300, 1)
    assert np.array_equal(v1, v2)
    lo, hi = R._pct(v1)
    assert lo < 0.8 < hi


def test_estimators_match_gmm_module_on_synthetic_data():
    import pandas as pd

    rng = np.random.default_rng(2)
    n = 1500
    c = np.cumsum(rng.normal(size=n)) * 0.2
    h = pd.DataFrame({"L": c + rng.normal(size=n), "E": c + rng.normal(size=n), "LTC": c + rng.normal(size=n)})
    h["X"] = rng.normal(size=n)
    h["D"] = 0.9 * h["L"] + h["X"] + rng.normal(size=n)
    res = R.estimate(h[["L", "D", "X", "E", "LTC"]], "eth_ltc", {"week": 168}, 99)
    r = gmm.iv((h["D"] - h["X"]).to_numpy(), h["L"].to_numpy(), h[["E", "LTC"]].to_numpy())
    assert res["gmm"]["lam"] == pytest.approx(r.beta[0]) and res["gmm"]["J_df"] == 1
    assert res["ols"]["lam"] < res["iv"]["lam"] + 0.2 and abs(res["gmm"]["lam"] - 0.9) < 0.1
    assert R.estimate(h[["L", "D", "X", "E", "LTC"]], "eth_ltc", {"week": 168}, 99) == res  # deterministic


def test_grid_is_the_declared_one():
    rep = json.loads(R.OUT.read_text())
    assert rep["grid"]["cells"] == len(rep["cells"]) == 5 * 4 * 3 * 2 * 3
    assert rep["grid"]["blocks_hours"] == {"day": 24, "week": 168, "month": 720} and rep["grid"]["draws"] == R.DRAWS
    assert {(c["window"], c["instruments"], c["reference"], c["x"], c["block"]) for c in rep["cells"]} == {
        (w, i, r, x, b) for w in R.WINDOWS for i in R.INSTRUMENTS for r in R.REFERENCES for x in R.XKINDS for b in R.BLOCKS}


def test_headline_cell_reproduces_gmm_applied_and_states_the_j_test():
    rep = json.loads(R.OUT.read_text())
    app = json.loads(R.APPLIED.read_text())["bitfinex"]["specs"]["netted|eth_ltc_bch_etc"]
    h = rep["headline"]
    assert h["lam"] == pytest.approx(app["lam"], abs=1e-9) and h["J"] == pytest.approx(app["J"], abs=1e-9)
    assert (h["n"], h["J_df"], h["instrument_columns"]) == (app["n"], app["J_df"], ["E", "LTC", "BCH", "ETC"])
    cell = next(c for c in rep["cells"] if all(c[k] == v for k, v in R.HEADLINE.items()))
    assert cell["gmm"]["lam"] == pytest.approx(h["lam"]) and cell["gmm"]["boot_ci95"] == pytest.approx(h["boot_ci95_week"])
    assert max(rep["reproduces_gmm_applied_max_abs_diff"].values()) < 1e-8


def test_committed_report_is_current_for_the_headline_and_a3():
    pytest.importorskip("pandas")
    if not (R.data.PANEL.is_file() and (ROOT / "data/raw/kraken_ohlcvt/USDTUSD_60.csv").is_file()):
        pytest.skip("held data is not on this machine")
    rep = json.loads(R.OUT.read_text())
    f = R.build_frame()
    assert R.headline(f) == rep["headline"]
    assert R.a3_check(f) == rep["a3_falsification"]


def test_summary_is_consistent_with_the_cells():
    rep = json.loads(R.OUT.read_text())
    assert rep["summary"] == R.summarize(rep["cells"])
    g = np.array([c["gmm"]["lam"] for c in rep["cells"]])
    s = rep["summary"]["overall"]["gmm"]
    assert (s["min"], s["max"]) == (g.min(), g.max()) and s["median"] == pytest.approx(np.median(g))


def test_committed_macros_and_table_are_current():
    assert M.NUMBERS.read_text() == M.numbers(), "run `uv run python -m www_paper.robust_anchor_macros`"
    assert M.TABLE.read_text() == M.table(), "run `uv run python -m www_paper.robust_anchor_macros`"
    assert M.numbers() == M.numbers() and M.table() == M.table()
    lines = [ln for ln in M.NUMBERS.read_text().splitlines() if ln.startswith("\\newcommand")]
    names = [re.match(r"\\newcommand\{\\(\w+)\}", ln).group(1) for ln in lines]
    assert len(names) == len(set(names)) > 100 and all(n.startswith("NumRA") and n.isalpha() for n in names)
    assert all(re.search(r"\} % reports/theory/robustness\.json \S", ln) for ln in lines)
    text = M.NUMBERS.read_text()
    for name in ("NumRAGmmMin", "NumRAGmmMax", "NumRAHeadJDf", "NumRAHeadInstrumentList", "NumRAAThreeSlope", "NumRAGmmBootOnePct", "NumRAOutsideCells"):
        assert f"\\newcommand{{\\{name}}}" in text, name
