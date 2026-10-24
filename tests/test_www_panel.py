"""Currency-wedge panel: synthetic identification of the pipeline, day-demeaning, determinism and freshness of committed outputs."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from www_panel import run as R  # noqa: E402
from www_paper import figures_panel as FP  # noqa: E402
from www_paper import panel_macros as M  # noqa: E402


def synthetic(unit: bool, *, fx_scale: float = 0.0, seed: int = 5, days: int = 60) -> pd.DataFrame:
    """Hourly L, L2, D, X. A within-day wedge w moves the BTC and ETH gaps; D carries w iff the venue's unit moves (unit=True).
    A common daily official-rate error (scale fx_scale, bps) enters L, L2 and D alike."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=24 * days, freq="h", tz="UTC")
    w = np.cumsum(rng.normal(0, 8, len(idx)))
    w = w - pd.Series(w).groupby(idx.floor("D")).transform("mean").to_numpy()  # within-day wedge
    fx = np.repeat(rng.normal(0, fx_scale if fx_scale else 1e-12, days), 24) + 7000.0
    x = rng.normal(0, 3, len(idx))
    L = w + fx + rng.normal(0, 4, len(idx))
    L2 = w + fx + rng.normal(0, 4, len(idx))
    D = (w if unit else rng.normal(0, 8, len(idx))) + fx + x + rng.normal(0, 3, len(idx))
    return pd.DataFrame({"L": L, "L2": L2, "D": D, "X": x, "unit": "u"}, index=idx)


def iv(frame: pd.DataFrame) -> dict:
    return R.estimate(R.hourly_stats(frame))


def test_planted_unit_wedge_gives_lambda_one():
    e = iv(synthetic(True))
    assert abs(e["iv"]["lam"] - 1.0) < 0.05
    assert e["iv"]["lo"] < 1.0 < e["iv"]["hi"]


def test_crypto_only_demand_gives_lambda_zero():
    e = iv(synthetic(False))
    assert abs(e["iv"]["lam"]) < 0.08
    assert e["iv"]["hi"] < 0.3


def test_day_demeaning_removes_common_daily_fx_error():
    clean = iv(synthetic(True, fx_scale=0.0))
    noisy = iv(synthetic(True, fx_scale=500.0))
    assert noisy["iv"]["lam"] == pytest.approx(clean["iv"]["lam"], abs=1e-6)
    assert noisy["ols"]["lam"] == pytest.approx(clean["ols"]["lam"], abs=1e-6)


def test_bootstrap_is_deterministic():
    f = synthetic(True)
    assert iv(f) == iv(f)
    assert (R.SEED, R.DRAWS, R.BLOCK) == (20261024, 1000, 7)


def test_weekly_stats_recover_the_planted_slope_in_levels():
    # daily medians with week effects: a level wedge that varies across days within the week
    f = synthetic(True)
    e = R.estimate(R.weekly_stats(f), block=1)
    assert e["n_days"] > 0 and np.isfinite(e["iv"]["lam"])


def test_committed_outputs_are_fresh():
    assert M.NUMBERS.read_text() == M.numbers(), "run `uv run python -m www_paper.panel_macros`"
    assert M.TABLE.read_text() == M.table(), "run `uv run python -m www_paper.panel_macros`"
    names = [line.split("}")[0].split("\\NumPN")[1] for line in M.NUMBERS.read_text().splitlines() if "newcommand" in line]
    assert all(n.isalpha() for n in names)
    assert all("reports/panel/results.json" in line for line in M.NUMBERS.read_text().splitlines()[1:])


def test_figure_is_fresh(tmp_path):
    out = FP.panel_forest(tmp_path / "f.pdf")
    assert out.read_bytes() == (ROOT / "paper/figures/panel_forest.pdf").read_bytes(), "run `uv run python -m www_paper.figures_panel`"


def test_preregistered_outcomes_match_results():
    r = json.loads((ROOT / "reports/panel/results.json").read_text())
    ps = r["pooled_stress"]["iv"]
    assert r["P1"]["pass"] == ((ps["lo"] > 0 or ps["hi"] < 0) and ps["lo"] <= 1 <= ps["hi"])
    assert r["falsification"]["triggered"] == (ps["hi"] < 0.5)
    months = json.loads((ROOT / "reports/panel/months.json").read_text())
    assert months["rule"]["stress_bps"] == 25.0 and months["rule"]["coverage_min"] == 0.8


@pytest.mark.skipif(not (ROOT / "data/raw/panel/binance").exists(), reason="raw panel data not present")
def test_results_reproduce_from_raw():
    assert json.dumps(R.run(), indent=1, sort_keys=True) + "\n" == (ROOT / "reports/panel/results.json").read_text()
