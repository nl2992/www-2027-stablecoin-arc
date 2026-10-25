"""Kraken fiat-panel slice: synthetic identification, determinism, pre-registered rules and freshness of committed outputs."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from www_panel_kraken import classify as C  # noqa: E402
from www_panel_kraken import run as R  # noqa: E402
from www_paper import panel_kraken_macros as M  # noqa: E402
from www_panel import run as PR  # noqa: E402


def synthetic(unit: bool, *, seed: int = 5, days: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-01", periods=24 * days, freq="h", tz="UTC")
    w = np.cumsum(rng.normal(0, 8, len(idx)))
    w = w - pd.Series(w).groupby(idx.floor("D")).transform("mean").to_numpy()
    fx = np.repeat(rng.normal(0, 300, days), 24)
    x = rng.normal(0, 3, len(idx))
    L = w + fx + rng.normal(0, 4, len(idx))
    L2 = w + fx + rng.normal(0, 4, len(idx))
    D = (w if unit else rng.normal(0, 8, len(idx))) + fx + x + rng.normal(0, 3, len(idx))
    return pd.DataFrame({"L": L, "L2": L2, "D": D, "X": x, "unit": "u"}, index=idx)


def est(f):
    return R.estimate(PR.hourly_stats(f))


def test_planted_slope_is_recovered_and_zero_is_rejected_when_absent():
    one, zero = est(synthetic(True)), est(synthetic(False))
    assert abs(one["iv"]["lam"] - 1.0) < 0.05 and one["iv"]["lo"] < 1.0 < one["iv"]["hi"]
    assert abs(zero["iv"]["lam"]) < 0.08 and zero["iv"]["hi"] < 0.3


def test_bootstrap_is_deterministic_and_uses_this_study_seed():
    f = synthetic(True)
    assert est(f) == est(f)
    assert (R.SEED, R.DRAWS, R.BLOCK) == (20261025, 1000, 7)
    assert PR.SEED == 20261024, "the panel's seed must be restored after estimation"


def test_stress_rule_constants():
    assert (C.COVERAGE_MIN, C.STRESS_BPS) == (0.80, 25.0)


def test_traded_hours_counted_by_month():
    idx = pd.date_range("2020-01-31 22:00", periods=5, freq="h", tz="UTC")
    assert C.traded_by_month(pd.Series(1.0, index=idx)) == {"2020-01": 2, "2020-02": 3}


def test_committed_outputs_are_fresh():
    assert M.NUMBERS.read_text() == M.numbers(), "run `uv run python -m www_paper.panel_kraken_macros`"
    assert M.TABLE.read_text() == M.table(), "run `uv run python -m www_paper.panel_kraken_macros`"
    lines = [line for line in M.NUMBERS.read_text().splitlines() if "newcommand" in line]
    assert all(line.split("}")[0].split("\\NumPK")[1].isalpha() for line in lines)
    assert all("reports/panel_kraken/results.json" in line for line in lines)
    assert "reports/" not in M.TABLE.read_text() and "data/" not in M.TABLE.read_text()


def test_preregistered_outcomes_match_results():
    r = json.loads((ROOT / "reports/panel_kraken/results.json").read_text())
    ps = r["pooled_stress"]["iv"]
    assert r["K1"]["pass"] == bool(ps["lo"] > 0 or ps["hi"] < 0)
    n = sum(0.8 <= v["stress"]["iv"]["lam"] <= 1.2 for v in r["by_currency"].values() if v["stress_months"] >= 3)
    e = sum(v["stress_months"] >= 3 for v in r["by_currency"].values())
    assert r["K2"]["pass"] == (n > e / 2) and (r["K2"]["n_inside"], r["K2"]["n_eligible"]) == (n, e)
    assert r["design"]["seed"] == 20261025 and r["design"]["draws"] == 1000
    months = json.loads((ROOT / "reports/panel_kraken/months.json").read_text())
    assert months["rule"]["stress_bps"] == 25.0 and months["rule"]["coverage_min"] == 0.8


@pytest.mark.skipif(not (ROOT / "data/raw/kraken_ohlcvt/XBTEUR_60.csv").exists(), reason="raw Kraken fiat files not present")
def test_months_and_results_reproduce_from_raw():
    assert json.dumps(C.classify(), indent=1, sort_keys=True) + "\n" == (ROOT / "reports/panel_kraken/months.json").read_text()
    assert json.dumps(R.run(), indent=1, sort_keys=True) + "\n" == (ROOT / "reports/panel_kraken/results.json").read_text()
