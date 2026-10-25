"""Fusion panel: no-look-ahead FX alignment, a synthetic wedge that biases O but not A, determinism, and freshness of committed outputs."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from www_panel_fusion import fx  # noqa: E402
from www_panel_fusion import run as R  # noqa: E402
from www_paper import panel_fusion_macros as M  # noqa: E402


def ecb_frame() -> pd.DataFrame:
    idx = pd.to_datetime(["2024-03-01", "2024-03-04", "2024-03-05"])
    return pd.DataFrame({"USD": [1.0, 1.0, 1.0], "TRY": [30.0, 32.0, 99.0], "BRL": np.nan, "ZAR": np.nan, "KRW": np.nan, "RUB": np.nan}, index=idx)


def test_fx_alignment_has_no_look_ahead():
    h = pd.date_range("2024-03-01 12:00", "2024-03-05 20:00", freq="h", tz="UTC")
    s = fx.hourly_official(ecb_frame(), "TRY", h)
    assert np.isnan(s[:"2024-03-01 13:00"]).all()  # nothing published before 13:15 UTC; hour 13:00 starts before publication
    assert s["2024-03-01 14:00"] == 30.0 and s["2024-03-04 13:00"] == 30.0  # carried forward over the weekend
    assert s["2024-03-04 14:00"] == 32.0 and s["2024-03-05 13:00"] == 32.0
    assert (s[:"2024-03-05 13:00"] != 99.0).all() and s["2024-03-05 14:00"] == 99.0  # the 2024-03-05 rate is not used before its publication


def test_fx_is_cross_rate_and_rub_stops():
    e = ecb_frame()
    e["USD"] = 2.0
    assert fx.f_per_usd(e, "TRY").iloc[0] == 15.0
    idx = pd.to_datetime(["2022-02-28", "2022-03-01"])
    r = pd.DataFrame({"USD": 1.0, "RUB": [100.0, 120.0], "TRY": 1.0, "BRL": 1.0, "ZAR": 1.0, "KRW": 1.0}, index=idx)
    h = pd.date_range("2022-02-28 14:00", "2022-03-02 00:00", freq="h", tz="UTC")
    s = fx.hourly_official(r, "RUB", h)
    assert (s[:"2022-02-28 23:00"] == 100.0).all() and s["2022-03-01":].isna().all()


def synth(days: int = 40, seed: int = 3) -> tuple[pd.DataFrame, pd.DataFrame]:
    """TRY unit whose local currency trades at a persistent wedge (about 1.5%) to the official rate, plus noise; USDT is 5 bps off par."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-03-05 14:00", periods=24 * days, freq="h", tz="UTC")
    ecb = pd.DataFrame({"USD": 1.0, "TRY": 30.0, "BRL": np.nan, "ZAR": np.nan, "KRW": np.nan, "RUB": np.nan},
                       index=pd.date_range("2024-03-01", periods=days + 10, freq="D"))
    wedge = 150.0 + rng.normal(0, 20, len(idx))  # bps
    off = 1e4 * np.log(30.0)
    x = np.full(len(idx), -5.0)  # USDT trades 5 bps below a dollar, externally
    L = off + wedge  # log BTC/F minus log truth, in bps
    D = off + wedge + x + rng.normal(0, 2, len(idx))  # the local USDT market carries the same wedge and the USDT/USD deviation
    panel = pd.DataFrame({"L": L, "D": D, "X": np.nan, "XB": np.nan, "XS": x, "unit": "binance-TRY", "fiat": "TRY", "venue": "binance"}, index=idx)
    return panel, ecb


def test_wedge_biases_official_conversion_but_not_anchor():
    panel, ecb = synth()
    smp = R.sample_from_panel(panel, ecb)
    assert smp["e_O"].mean() == pytest.approx(150.0, abs=5.0)
    assert abs(smp["e_A"].mean()) < 2.0 and np.abs(smp["e_A"]).mean() < 4.0
    res = R.evaluate(smp)
    assert res["primary"]["success"] and res["primary"]["hi"] < 0
    assert res["x_source_hours"]["bitstamp"] == len(smp)


def test_external_usdt_priority_order():
    idx = pd.date_range("2024-01-01", periods=3, freq="h", tz="UTC")
    p = pd.DataFrame({"XS": [1.0, np.nan, np.nan], "XB": [2.0, 2.0, np.nan], "X": [3.0, 3.0, 3.0]}, index=idx)
    v, s = R.external_usdt(p)
    assert list(v) == [1.0, 2.0, 3.0] and list(s) == ["bitstamp", "binance_us", "kraken"]


def test_equal_errors_give_no_success():
    panel, ecb = synth()
    panel["L"] = 1e4 * np.log(30.0) + 3.0  # O errs by 3 bps
    panel["D"] = panel["L"] + panel["XS"] - 3.0  # A errs by 3 bps too
    smp = R.sample_from_panel(panel, ecb)
    assert np.allclose(smp["e_O"], 3.0) and np.allclose(smp["e_A"], 3.0)
    assert R.evaluate(smp)["primary"]["success"] is False  # equal errors: no improvement


def test_bootstrap_is_deterministic_and_pre_registered_constants():
    panel, ecb = synth()
    smp = R.sample_from_panel(panel, ecb)
    assert R.evaluate(smp) == R.evaluate(smp)
    assert (R.SEED, R.DRAWS) == (20261025, 1000)


def test_committed_outputs_are_fresh():
    assert M.NUMBERS.read_text() == M.numbers(), "run `uv run python -m www_paper.panel_fusion_macros`"
    assert M.TABLE.read_text() == M.table(), "run `uv run python -m www_paper.panel_fusion_macros`"
    assert all("reports/panel_fusion/results.json" in line for line in M.NUMBERS.read_text().splitlines()[1:])
    assert "/Users/" not in M.TABLE.read_text() and "reports/" not in M.TABLE.read_text()


@pytest.mark.skipif(not (ROOT / "data/raw/ecb/eurofxref-hist.zip").exists() or not (ROOT / "data/raw/panel/binance").exists(), reason="raw data not present")
def test_results_reproduce_from_raw_data():
    assert json.dumps(R.run(), indent=1, sort_keys=True) + "\n" == (ROOT / "reports/panel_fusion/results.json").read_text()
