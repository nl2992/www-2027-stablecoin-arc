"""Exploratory placebo and comparator-C: synthetic checks, determinism and freshness of committed outputs."""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from www_explore import comparator as C  # noqa: E402
from www_explore import placebo as PL  # noqa: E402
from www_paper import explore_macros as M  # noqa: E402


def two_unit_panel(link: float, days: int = 60, seed: int = 5) -> pd.DataFrame:
    """Two Binance units. Unit F has a wedge process; unit G's local USDT price carries `link` times an independent wedge process, X = 0."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=24 * days, freq="h", tz="UTC")
    frames = []
    wf, wg = rng.normal(0, 30, len(idx)), rng.normal(0, 30, len(idx))
    for name, own, other in (("F", wf, wg), ("G", wg, wf)):
        L = own + rng.normal(0, 3, len(idx))
        frames.append(pd.DataFrame({"L": L, "L2": own + rng.normal(0, 3, len(idx)), "D": own + link * other * 0 + rng.normal(0, 3, len(idx)),
                                    "X": 0.0, "unit": f"binance-{name}", "status": "stress"}, index=idx))
    return pd.concat(frames)


def test_mismatched_placebo_is_near_zero_but_matched_is_near_one():
    panel = two_unit_panel(0.0)
    res = PL.mismatched(panel, True)
    assert res["n_pairs"] == 2 and abs(res["pooled"]["iv"]["lam"]) < 0.1  # independent wedges: no slope
    own = panel[panel["unit"] == "binance-F"].assign(unit="binance-F")
    matched = PL.P.estimate(PL.P.hourly_stats(own))
    assert matched["iv"]["lam"] == pytest.approx(1.0, abs=0.05)  # the same unit recovers 1


def test_mismatched_placebo_detects_a_mechanical_link():
    panel = two_unit_panel(0.0)
    g = panel["unit"] == "binance-G"
    panel.loc[g, "D"] = panel.loc[panel["unit"] == "binance-F", "L"].to_numpy() + 1.0  # G's USDT price tracks F's wedge: slope must be about one
    res = PL.mismatched(panel, True)
    assert res["pairs"]["F>G"]["iv"]["lam"] == pytest.approx(1.0, abs=0.1)


def test_calm_cross_venue_no_wedge_gives_zero_slope_and_small_variance():
    rng = np.random.default_rng(1)
    idx = pd.date_range("2022-10-01", periods=24 * 31, freq="h", tz="UTC")
    px = 20000 * np.exp(np.cumsum(rng.normal(0, 1e-3, len(idx))))
    btc_b = pd.Series(px * np.exp(rng.normal(0, 1e-4, len(idx))), index=idx)  # 1 bp noise only
    btc_s = pd.Series(px, index=idx)
    usdt_b = pd.Series(1 + rng.normal(0, 1e-4, len(idx)), index=idx)
    usdt_s = pd.Series(1 + rng.normal(0, 1e-4, len(idx)), index=idx)
    fr = PL.venue_frame(btc_b, btc_s, usdt_b, usdt_s)
    r = PL.calm_cross_venue(fr, ["2022-10"])
    assert abs(r["ols"]["lam"]) < 0.3 and r["var_L_within_day_bps2"] < 5
    assert PL.calm_cross_venue(fr, ["2022-05"])["n_days"] == 0  # months outside the list are excluded


def test_calm_cross_venue_wedge_gives_slope_one():
    rng = np.random.default_rng(2)
    idx = pd.date_range("2022-10-01", periods=24 * 31, freq="h", tz="UTC")
    wedge = rng.normal(0, 40, len(idx))
    px = pd.Series(20000.0, index=idx)
    btc_b = px * np.exp(wedge / 1e4)
    usdt_s = pd.Series(1.0, index=idx)
    usdt_b = pd.Series(np.exp(wedge / 1e4), index=idx)  # local USDT carries the same wedge
    r = PL.calm_cross_venue(PL.venue_frame(btc_b, px, usdt_b, usdt_s), ["2022-10"])
    assert r["ols"]["lam"] == pytest.approx(1.0, abs=0.01) and r["var_L_within_day_bps2"] > 500


def comp_sample(days: int = 40, seed: int = 4) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-03-05 14:00", periods=24 * days, freq="h", tz="UTC")
    n = len(idx)
    wedge = 150 + rng.normal(0, 20, n)
    x = np.full(n, -30.0)  # USDT trades 30 bps below a dollar externally: C ignores it, A corrects it
    L = 1e4 * np.log(30.0) + wedge
    D = 1e4 * np.log(30.0) + wedge + x + rng.normal(0, 2, n)
    ecb = pd.DataFrame({"USD": 1.0, "TRY": 30.0, "BRL": np.nan, "ZAR": np.nan, "KRW": np.nan, "RUB": np.nan}, index=pd.date_range("2024-03-01", periods=days + 10, freq="D"))
    panel = pd.DataFrame({"L": L, "D": D, "X": np.nan, "XB": np.nan, "XS": x, "unit": "binance-TRY", "fiat": "TRY", "venue": "binance"}, index=idx)
    return C.sample_from_panel(panel, ecb)


def test_comparator_c_ordering_on_synthetic_data():
    s = comp_sample()
    assert np.allclose(s["e_C"], s["e_A"] - (-30.0))  # C = A without the external USDT correction
    assert abs(s["e_A"].mean()) < 2 and s["e_C"].mean() == pytest.approx(30.0, abs=2)  # C inherits Tether's 30 bp discount
    r = C.evaluate(s)["pooled"]
    assert r["mae"]["A"] < r["mae"]["C"] < r["mae"]["O"]
    assert r["logdiff_A_minus_C"]["hi"] < 0 and r["logdiff_C_minus_O"]["hi"] < 0


def test_comparator_c_equals_a_when_tether_is_par():
    s = comp_sample()
    s["e_C"] = s["e_A"]
    r = C.evaluate(s)["pooled"]
    assert r["logdiff_A_minus_C"]["mean"] == 0.0 and r["mae_ratio_A_over_C"] == 1.0


def test_seeds_and_determinism():
    assert (C.SEED, C.DRAWS, PL.SEED, PL.DRAWS) == (20261026, 1000, 20261026, 1000)
    s = comp_sample()
    assert C.evaluate(s) == C.evaluate(s)
    p = two_unit_panel(0.0)
    assert PL.mismatched(p, True) == PL.mismatched(p, True)


def test_committed_outputs_are_fresh():
    assert M.NUMBERS.read_text() == M.numbers(), "run `uv run python -m www_paper.explore_macros`"
    lines = M.NUMBERS.read_text().splitlines()[1:]
    assert all(re.match(r"\\newcommand\{\\NumEX[A-Za-z]+\}\{.*\} % reports/explore/(placebo|comparator)\.json ", ln) for ln in lines)


@pytest.mark.skipif(not (ROOT / "data/raw/ecb/eurofxref-hist.zip").exists() or not (ROOT / "data/raw/panel/binance").exists(), reason="raw data not present")
def test_results_reproduce_from_raw_data():
    for mod, name in ((PL, "placebo"), (C, "comparator")):
        assert json.dumps(mod.run(), indent=1, sort_keys=True) + "\n" == (ROOT / f"reports/explore/{name}.json").read_text()
