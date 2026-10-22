"""Kimchi application: synthetic identification check of the pipeline and freshness of the committed outputs."""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from www_kimchi import analysis as A  # noqa: E402
from www_paper import kimchi_macros as M  # noqa: E402


def synthetic(unit: bool, seed: int = 3) -> dict:
    """KRW prices = USD price x FX x exp(common wedge u(t) + idio). USDT/KRW carries the wedge iff unit (a dollar shift)."""
    rng = np.random.default_rng(seed)
    idx = A.hourly_index()
    n = len(idx)
    u = pd.Series(np.cumsum(rng.normal(0, 0.002, n)) * 0.2, index=idx)       # common wedge, log points
    fx_days = pd.date_range("2017-01-01", "2023-12-31", freq="D", tz="UTC")
    fx = pd.Series(np.log(1100.0) + np.cumsum(rng.normal(0, 0.0005, len(fx_days))), index=fx_days)
    fxh = A.fx_hourly(fx)
    usd = {c: pd.Series(np.cumsum(rng.normal(0, 0.003, n)) + 8, index=idx) for c in A.ALL}
    krw = {c: usd[c] + fxh + u + rng.normal(0, 0.0005, n) for c in A.ALL}
    usdt = fxh + (u if unit else 0.0) + rng.normal(0, 0.0003, n)
    return {"krw": krw, "usd": usd, "fx": fx, "usdt_krw": usdt, "kraken_usdt": pd.Series(rng.normal(0, 0.0003, n), index=idx)}


@pytest.fixture(scope="module")
def runs():
    return {k: A.run(synthetic(k)) for k in (True, False)}


def test_planted_unit_wedge_gives_slope_one(runs):
    b = runs[True]["anchor"]["mean3_vs_bch_iv"]
    assert b["slope_D_minus_X_on_L_ols"]["est"] == pytest.approx(1.0, abs=0.1)
    assert b["slope_D_minus_X_on_L_iv"]["est"] == pytest.approx(1.0, abs=0.1)
    assert b["reading"] in ("unit", "mixed (interval excludes 0 and 1)", "uninformative (interval contains 0 and 1)")
    ci = b["slope_D_minus_X_on_L_ols"]["ci95"]
    assert ci[0] <= 1.0 + 0.1 and ci[1] >= 1.0 - 0.1


def test_planted_demand_premium_gives_slope_zero(runs):
    b = runs[False]["anchor"]["mean3_vs_bch_iv"]
    assert abs(b["slope_D_minus_X_on_L_ols"]["est"]) < 0.15
    assert abs(b["slope_D_minus_X_on_L_iv"]["est"]) < 0.15
    assert b["slope_D_minus_X_on_L_ols"]["ci95"][1] < 0.5


def test_common_component_detected_and_h1_logic(runs):
    c = runs[True]["windows"]["E1_2017-12_2018-01"]["common"]
    assert c["min_corr_levels"] > 0.9 and c["H1_holds"]
    # no common wedge: gaps are independent noise, H1 must fail
    d = pd.DataFrame(np.random.default_rng(1).normal(size=(120, 3)), columns=list(A.CORE),
                     index=pd.date_range("2021-03-01", periods=120, freq="D", tz="UTC"))
    assert not A.common_block(d)["H1_holds"]


def test_block_bootstrap_is_seeded_and_needs_five_blocks():
    idx = pd.date_range("2021-01-01", periods=100, freq="D", tz="UTC")
    df = pd.DataFrame({"a": np.arange(100.0)}, index=idx)
    assert A.block_ci(df, lambda m: m.mean(), "W") == A.block_ci(df, lambda m: m.mean(), "W")
    assert A.block_ci(df.iloc[:20], lambda m: m.mean(), "M") is None


def test_iv_and_ols_helpers():
    rng = np.random.default_rng(0)
    z = rng.normal(size=5000)
    x = z + rng.normal(size=5000)
    y = x + rng.normal(size=5000)
    assert A._iv(z, x, y) == pytest.approx(1.0, abs=0.1)
    assert A._ols(x, y) == pytest.approx(1.0, abs=0.1)


def test_committed_outputs_are_current():
    assert M.NUMBERS.read_text() == M.numbers(), "run `uv run python -m www_paper.kimchi_macros`"
    assert M.TABLE.read_text() == M.table(), "run `uv run python -m www_paper.kimchi_macros`"
    names = re.findall(r"\\newcommand\{\\(NumKR\w+)\}", M.NUMBERS.read_text())
    assert len(names) >= 60 and len(names) == len(set(names))
    r = json.loads(M.REPORT.read_text())
    assert r["bootstrap"]["seed"] == A.SEED and r["bootstrap"]["draws"] == A.DRAWS
    assert "NOT TESTABLE" in r["anchor"]["H2_high_premium_windows"]


def test_manifest_records_and_no_secret():
    m = json.loads((ROOT / "reports/events/acquisition_manifest.json").read_text())
    recs = [r for r in m["records"] if r["venue"] in ("upbit", "bithumb", "fred")]
    assert len(recs) == 7 and all(len(r["sha256"]) == 64 and r["status"] == "VERIFIED" for r in recs)
    assert all("api_key=" not in r["url"] or "api_key=<redacted>" in r["url"] for r in recs)
    assert sum(r["status"] == "VERIFIED" for r in m["records"]) == m["summary"]["VERIFIED"]
    for p in [ROOT / "reports/events/acquisition_manifest.json", M.REPORT, ROOT / "data/raw/fred/DEXKOUS.csv"]:
        assert not re.search(r"api_key=(?!<redacted>)[0-9a-f]{20,}", p.read_text())


def test_analysis_regenerates_from_raw_data(tmp_path):
    if not (ROOT / "data/raw/upbit/KRW-BTC_60m.csv").is_file() or not (ROOT / "data/raw/coinbase").is_dir():
        pytest.skip("raw Upbit or Coinbase data is not on this machine")
    assert A.run(A.load_all()) == json.loads(M.REPORT.read_text())
