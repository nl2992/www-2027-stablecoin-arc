"""External-price anchor test: synthetic identification check and freshness of the committed outputs."""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from www_auto import anchor_external as AX
from www_paper import anchor_ext_macros as M

ROOT = Path(__file__).parents[1]
STRESS = "stress_2018-11-27_2019-05-31"


def planted(residual_is_x: bool, n_days: int = 200, seed: int = 5):
    """Hourly L, D, X, E (bps): D = L + X (+ noise) when the residual is USDT's own deviation; E is a noisy copy of L."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=24 * n_days, freq="h", tz="UTC")
    day = np.arange(len(idx)) // 24
    u = np.where(rng.random(n_days)[day] < 0.3, rng.normal(150, 60, n_days)[day], 0.0)
    L = pd.Series(u + rng.normal(0, 3, len(idx)), idx)
    X = pd.Series((-0.3 * u if residual_is_x else 0.0) + rng.normal(0, 10, len(idx)), idx)  # USDT's own deviation, partly co-moving with the stress
    D = (L + X + rng.normal(0, 2, len(idx))) if residual_is_x else (0.5 * L + rng.normal(0, 2, len(idx)))
    E = pd.Series(u + rng.normal(0, 3, len(idx)), idx)
    return L, D, X, E


def test_planted_d_equals_l_plus_x_gives_adjusted_slope_one():
    s = AX.slice_stats(*planted(True))
    for fr in ("hourly", "daily"):
        a = s["adjusted_LDX"][fr]
        assert a["slope_D_minus_X_on_L"]["est"] == pytest.approx(1.0, abs=0.03)
        for blk in ("ci95_week", "ci95_month"):
            lo, hi = a["slope_D_minus_X_on_L"][blk]
            assert lo <= 1.0 <= hi
        assert a["slope_D_on_L"]["est"] == pytest.approx(0.7, abs=0.05)  # D alone is not slope one: X co-moves with L
        assert s["iv_LDXE"][fr]["iv_slope_D_minus_X_on_L"]["est"] == pytest.approx(1.0, abs=0.03)
    assert abs(s["median_T_minus_X"]) < 5 and s["corr_T_X_hourly"] > 0.95


def test_planted_unrelated_residual_does_not_give_slope_one():
    s = AX.slice_stats(*planted(False))
    assert s["adjusted_LDX"]["daily"]["slope_D_minus_X_on_L"]["est"] < 0.9
    assert abs(s["corr_T_X_hourly"]) < 0.5


def test_block_bootstrap_is_seeded_and_monthly_needs_five_blocks():
    L, D, X, E = planted(True)
    h = pd.concat([L.rename("L"), D.rename("D")], axis=1).groupby(L.index.floor("D")).median()
    f = lambda m: AX._ols(m[:, 0], m[:, 1])  # noqa: E731
    assert AX.block_ci(h, f, "W") == AX.block_ci(h, f, "W")
    assert AX.block_ci(h.iloc[:60], f, "M") is None  # two months only


def test_iv_recovers_slope_despite_noise_in_l():
    rng = np.random.default_rng(1)
    z = rng.normal(0, 1, 5000)
    x = z + rng.normal(0, 1, 5000)
    y = 1.0 * x + rng.normal(0, 1, 5000)
    assert AX._iv(z, x, y) == pytest.approx(1.0, abs=0.1)


def test_committed_outputs_are_current():
    assert M.NUMBERS.read_text() == M.numbers(), "run `uv run python -m www_paper.anchor_ext_macros`"
    assert M.TABLE.read_text() == M.table(), "run `uv run python -m www_paper.anchor_ext_macros`"
    names = re.findall(r"\\newcommand\{\\(NumK\w+)\}", M.NUMBERS.read_text())
    assert len(names) >= 100 and len(names) == len(set(names))
    r = json.loads(M.REPORT.read_text())
    assert r["bootstrap"] == {"draws": 1000, "seed": 20261020, "blocks": ["week", "month"]}
    a = json.loads((ROOT / "reports/unit_td/anchor.json").read_text())["bitfinex"]["slices"][STRESS]
    rep = r["slices"][STRESS]["reproduce_anchor_daily"]
    assert rep["slope"] == pytest.approx(a["daily_slope"])
    assert rep["ci95_week"] == pytest.approx(a["daily_slope_ci95"])


def test_manifest_records_cover_the_extracted_files():
    m = json.loads(AX.MANIFEST.read_text())
    recs = [r for r in m["records"] if r["venue"] == AX.VENUE]
    assert len(recs) == 1 + len(AX.PAIRS) * len(AX.INTERVALS)
    assert any(r["sha256"] == AX.ARCHIVE_SHA256 and r["bytes"] == AX.ARCHIVE_BYTES for r in recs)
    assert all(len(r["sha256"]) == 64 and r["status"] == "VERIFIED" for r in recs)
    assert sum(r["status"] == "VERIFIED" for r in m["records"]) == m["summary"]["VERIFIED"]


def test_anchor_external_regenerates_from_raw_data(tmp_path):
    if not (AX.KRAKEN / "USDTUSD_1.csv").is_file() or not (ROOT / "data/raw/bitfinex").is_dir():
        pytest.skip("raw Kraken or minute data is not on this machine")
    out = tmp_path / "ae.json"
    assert AX.main(["--out", str(out)]) == 0
    assert out.read_text() == AX.OUTPUT.read_text()
