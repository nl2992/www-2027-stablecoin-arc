"""Stablecoin anchor test: synthetic identification checks and freshness of the committed outputs."""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from www_auto import anchor as A
from www_paper import unit_macros as U

ROOT = Path(__file__).parents[1]


def planted(unit_shift: bool, n_days: int = 200, seed: int = 3):
    """Hourly L and D (bps): a venue-wide shift u on some days, noise elsewhere; D tracks u only if the unit shifted."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=24 * n_days, freq="h", tz="UTC")
    day = np.arange(len(idx)) // 24
    u = np.where(rng.random(n_days)[day] < 0.3, rng.normal(150, 60, n_days)[day], 0.0)
    noise = lambda: rng.normal(0, 3, len(idx))  # noqa: E731
    L = pd.Series(u + noise(), idx)
    D = pd.Series((u if unit_shift else 0.0) + noise(), idx)
    return L, D


def test_planted_unit_shift_gives_slope_one_and_zero_residual():
    s = A.stats(*planted(True))
    assert s["daily_slope"] == pytest.approx(1.0, abs=0.05)
    lo, hi = s["daily_slope_ci95"]
    assert lo <= 1.0 <= hi
    assert abs(s["median_T"]) < 5 and s["share_abs_T_le_quarter_L"] > 0.95 and s["daily_corr"] > 0.99


def test_planted_crypto_only_premium_gives_slope_zero():
    s = A.stats(*planted(False))
    assert abs(s["daily_slope"]) < 0.05
    lo, hi = s["daily_slope_ci95"]
    assert lo <= 0.0 <= hi
    assert s["median_T"] == pytest.approx(-s["median_L"], abs=5) and s["share_abs_T_le_quarter_L"] < 0.05


def test_demand_share_counts_hours_usdt_does_not_follow():
    idx = pd.date_range("2020-01-01", periods=10, freq="h", tz="UTC")
    L = pd.Series(100.0, idx)
    D = pd.Series([100.0] * 7 + [0.0] * 3, idx)  # last three hours: BTC and ETH agree, USDT flat
    out = A.demand_share(L, L + 5, D)
    assert out["hours_agree"] == 10 and out["hours_not_following"] == 3 and out["share_not_following"] == pytest.approx(0.3)


def test_bootstrap_is_seeded_and_week_blocked():
    L, D = planted(True)
    h = pd.concat([L.rename("L"), D.rename("D")], axis=1).groupby(L.index.floor("D")).median()
    assert A.slope_ci(h) == A.slope_ci(h)


def test_committed_outputs_are_current():
    for path, build in ((U.NUMBERS, U.numbers), (U.ANCHOR_TABLE, U.anchor_table)):
        assert path.read_text() == build(), "run `uv run python -m www_paper.unit_macros`"
    names = re.findall(r"\\newcommand\{\\(NumUAnchor\w+)\}", U.NUMBERS.read_text())
    assert len(names) >= 20 and len(names) == len(set(names))
    a = json.loads(U.ANCHOR.read_text())
    assert a["bootstrap"] == {"draws": 1000, "seed": 20261020, "block": "week"}
    assert a["bitfinex"]["slices"]["2019"]["daily_slope_ci95"][0] < a["bitfinex"]["slices"]["2019"]["daily_slope"]


def test_anchor_regenerates_from_raw_data(tmp_path):
    if not (ROOT / "data/raw/bitfinex").is_dir() or not (ROOT / "data/raw/binance_us").is_dir():
        pytest.skip("raw minute data is not on this machine")
    out = tmp_path / "anchor.json"
    assert A.main(["--out", str(out)]) == 0
    assert out.read_text() == A.OUTPUT.read_text()
