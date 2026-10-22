"""Anchored-test theory: GMM correctness on synthetic data, determinism, and freshness of the committed outputs."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from www_paper import theory_macros  # noqa: E402
from www_theory import gmm, simulate  # noqa: E402


def test_chi2_sf_known_values():
    assert gmm.chi2_sf(3.841458820694124, 1) == pytest.approx(0.05, abs=1e-9)
    assert gmm.chi2_sf(11.070497693516351, 5) == pytest.approx(0.05, abs=1e-9)
    assert gmm.chi2_sf(2.0, 2) == pytest.approx(math.exp(-1.0), abs=1e-12)
    assert gmm.chi2_sf(0.0, 3) == 1.0
    assert gmm.norm_sf2(1.959963984540054) == pytest.approx(0.05, abs=1e-9)


def test_ols_equals_iv_without_measurement_error():
    rng = np.random.default_rng(1)
    n = 500
    x = rng.normal(size=n)
    y = 0.4 + 0.7 * x + 0.3 * rng.normal(size=n)
    r_iv = gmm.iv(y, x, x[:, None], lags=0, two_step=False)   # the regressor is its own instrument
    slope, icpt = np.polyfit(x, y, 1)
    assert r_iv.beta[0] == pytest.approx(slope, abs=1e-10)
    assert r_iv.beta[1] == pytest.approx(icpt, abs=1e-10)
    # a valid extra instrument with no measurement error: IV and OLS agree up to sampling noise
    z = x + 0.3 * rng.normal(size=n)
    assert gmm.iv(y, x, z[:, None]).beta[0] == pytest.approx(slope, abs=0.05)


def test_iv_corrects_attenuation_ols_does_not():
    rng = np.random.default_rng(2)
    n = 20000
    c = rng.normal(size=n)
    L = c + rng.normal(size=n)                         # reliability 0.5
    z = c + rng.normal(size=n)
    y = 0.6 * c + 0.2 * rng.normal(size=n)
    assert gmm.iv(y, L, L[:, None], lags=0, two_step=False).beta[0] == pytest.approx(0.3, abs=0.03)   # OLS
    r = gmm.iv(y, L, z[:, None], lags=0)
    assert r.beta[0] == pytest.approx(0.6, abs=0.03)
    lo, hi = r.ci(0)
    assert lo < 0.6 < hi


def test_proposition_pure_shift_pure_demand_and_mixture():
    rng = np.random.default_rng(3)
    n = 40000
    for share in (1.0, 0.0, 0.5):
        u = rng.normal(size=n) * math.sqrt(share)
        d = rng.normal(size=n) * math.sqrt(1 - share)
        c = u + d
        L = c + 0.5 * rng.normal(size=n)
        z = 2.0 * c + rng.normal(size=n)
        y = u + 0.3 * rng.normal(size=n)
        assert gmm.iv(y, L, z[:, None], lags=0).beta[0] == pytest.approx(share, abs=0.03)


def test_hansen_j_is_chi_square_under_the_null_and_has_power():
    rng = np.random.default_rng(4)
    n, m, reps = 400, 4, 400
    J = []
    for _ in range(reps):
        c = rng.normal(size=n)
        L = c + 0.3 * rng.normal(size=n)
        Z = c[:, None] + rng.normal(size=(n, m))
        y = 0.8 * c + 0.3 * rng.normal(size=n)
        r = gmm.iv(y, L, Z, lags=0)
        assert r.J_df == m - 1
        J.append(r.J)
    J = np.array(J)
    assert J.mean() == pytest.approx(m - 1, abs=0.4)            # chi-square mean = df
    assert np.mean([gmm.chi2_sf(j, m - 1) < 0.05 for j in J]) == pytest.approx(0.05, abs=0.035)
    # power: one instrument carries the anchor's own noise
    eta = rng.normal(size=n)
    c = rng.normal(size=n)
    L = c + 0.3 * rng.normal(size=n)
    Z = np.column_stack([c + rng.normal(size=n) for _ in range(3)] + [c + 3 * eta])
    y = 0.8 * c + eta
    assert gmm.iv(y, L, Z, lags=0).J_p < 0.001


def test_stacked_anchor_degrees_of_freedom_and_wald_tests():
    rng = np.random.default_rng(5)
    n = 5000
    c = rng.normal(size=n)
    L = c + 0.2 * rng.normal(size=n)
    Z = c[:, None] + rng.normal(size=(n, 3))
    Y = np.column_stack([c + 0.3 * rng.normal(size=n), 0.1 + c + 0.3 * rng.normal(size=n)])
    r = gmm.stacked_anchor(Y, L, Z, lags=0)
    assert r.J_df == 2 * 3 - 1
    assert r.beta[0] == pytest.approx(1.0, abs=0.03)
    assert r.wald(0, 1.0)[1] > 0.01 and r.wald(0, 0.0)[1] < 1e-6
    assert r.beta[2] == pytest.approx(0.1, abs=0.05)


def test_hac_widens_the_interval_for_persistent_errors():
    rng = np.random.default_rng(6)
    n = 3000
    x, e = np.zeros(n), np.zeros(n)
    for t in range(1, n):
        x[t] = 0.9 * x[t - 1] + rng.normal()
        e[t] = 0.9 * e[t - 1] + rng.normal()
    y = x + e
    se0 = gmm.iv(y, x, x[:, None], lags=0, two_step=False).se[0]
    se20 = gmm.iv(y, x, x[:, None], lags=20, two_step=False).se[0]
    assert se20 > 1.5 * se0
    assert gmm.hac(e[:, None], 5)[1] == 5 and gmm.hac(e[:, None], "nw")[1] == gmm.nw_lags(n)


def test_block_bootstrap_shapes_determinism_and_rule():
    rng = np.random.default_rng(7)
    idx = gmm.mbb_indices(100, 7, 50, rng)
    assert idx.shape == (50, 100) and idx.min() >= 0 and idx.max() <= 99
    assert (np.diff(idx[:, :7], axis=1) == 1).all()           # first block is contiguous
    assert gmm.block_length(rng.normal(size=1000)) <= 3        # iid score: short blocks
    ar = np.zeros(2000)
    for t in range(1, 2000):
        ar[t] = 0.95 * ar[t - 1] + rng.normal()
    assert gmm.block_length(ar) > 20                           # persistent score: long blocks
    x = rng.normal(size=800)
    y = 0.5 * x + rng.normal(size=800)
    a, b = gmm.mbb_iv(y, x, x, 99, 11), gmm.mbb_iv(y, x, x, 99, 11)
    assert a == b and a["ci95"][0] < 0.5 < a["ci95"][1]


def test_simulation_is_deterministic_and_pure_cases_behave():
    cal = json.loads((ROOT / "reports/theory/calibration.json").read_text())
    cal = {**cal, "hours": 800}
    a = simulate.run_scenario("S1", cal, 6, 2, 20, 123)
    b = simulate.run_scenario("S1", cal, 6, 2, 20, 123)
    assert a == b
    assert abs(a["estimators"]["iv"]["bias"]) < 0.05
    s2 = simulate.run_scenario("S2", cal, 6, 2, 20, 123)
    assert abs(s2["estimators"]["iv"]["bias"]) < 0.05


# ---- freshness of committed outputs -----------------------------------------------------------------------------------

def test_committed_outputs_are_consistent_and_fresh():
    sim = json.loads((ROOT / "reports/theory/simulation.json").read_text())
    app = json.loads((ROOT / "reports/theory/gmm_applied.json").read_text())
    cal = json.loads((ROOT / "reports/theory/calibration.json").read_text())
    assert sim["reps"] == 1000 and sim["seed"] == simulate.SEED
    assert sim["hours"] == cal["hours"] and sim["calibration"] == cal
    assert set(sim["scenarios"]) == set(simulate.SCENARIOS)
    # the netted ETH-instrument estimate reproduces the committed anchor_external IV slope
    ext = json.loads((ROOT / "reports/unit_td/anchor_external.json").read_text())
    ref = ext["slices"]["stress_2018-11-27_2019-05-31"]["iv_LDXE"]["hourly"]["iv_slope_D_minus_X_on_L"]["est"]
    assert app["bitfinex"]["specs"]["netted|eth"]["lam"] == pytest.approx(ref, abs=2e-3)
    # a pure unit shift is recovered and a pure demand shock is not
    assert abs(sim["scenarios"]["S1"]["estimators"]["iv"]["bias"]) < 0.01
    assert abs(sim["scenarios"]["S2"]["estimators"]["iv"]["bias"]) < 0.01
    assert sim["scenarios"]["S6"]["estimators"]["ols"]["bias"] < -0.3


def test_generated_tex_matches_reports():
    assert (ROOT / "paper/generated/theory_numbers.tex").read_text() == theory_macros.numbers()
    assert (ROOT / "paper/generated/theory_table.tex").read_text() == theory_macros.table()
    sec = (ROOT / "paper/generated/theory_section.tex").read_text()
    import re
    names = set(re.findall(r"\\(NumG[A-Za-z]+)", sec))
    defined = {n for n, _, _ in theory_macros.macros()}
    assert names and names <= defined, names - defined
