"""Synthetic checks for the R2 platform-dollar measures (software validation, not research results)."""

import numpy as np
import pandas as pd

from www_rescue.platform_dollar import (
    PHASES, block_bootstrap_median, dislocation, identification, phase_of, phase_table,
)


def minutes(start, n):
    return pd.date_range(start, periods=n, freq="1min", tz="UTC")


def test_dislocation_uses_only_minutes_traded_on_both_venues():
    idx = minutes("2023-06-14", 4)
    plat = pd.Series(np.log([1.01, 1.02, np.nan, 1.0]), idx)
    ext = pd.Series(np.log([1.0, 1.0, 1.0]), idx[[0, 2, 3]])
    out = dislocation(plat, ext)
    assert list(out.index) == [idx[0], idx[3]]
    assert np.allclose(out.to_numpy(), [1e4 * np.log(1.01), 0.0])


def test_phases_are_contiguous_and_assignment_respects_boundaries():
    assert all(PHASES[i][2] == PHASES[i + 1][1] for i in range(len(PHASES) - 1))
    idx = pd.DatetimeIndex(["2023-06-08 23:59", "2023-06-09 00:00", "2025-02-19 00:00", "2022-01-01"], tz="UTC")
    assert list(phase_of(idx)) == ["sec_complaint", "deposits_suspended", "restored", None]


def test_platform_ledger_mispricing_shows_identically_in_unrelated_assets():
    idx = minutes("2023-06-22", 3 * 24 * 60)
    shock = pd.Series(-300.0, idx)  # platform USD worth 300 bps more than external USD
    rng = np.random.default_rng(0)
    usdt = shock + rng.normal(0, 2, len(idx))
    btc = shock + rng.normal(0, 8, len(idx))
    ident = identification(usdt, btc)
    assert ident["hours"] == 72 and abs(ident["median_gap_bps"]) < 2
    table = {r["phase"]: r for r in phase_table(usdt)}
    lo, hi = table["crypto_only_transition"]["ci95_bps"]
    assert lo <= -300 <= hi
    assert table["crypto_only_transition"]["share_abs_ge_50bps"] == 1.0
    assert table["pre"]["minutes"] == 0


def test_block_bootstrap_needs_enough_hours():
    assert block_bootstrap_median(pd.Series(1.0, minutes("2023-06-01", 120))) is None
    ci = block_bootstrap_median(pd.Series(np.arange(24 * 60, dtype=float), minutes("2023-06-01", 24 * 60)))
    assert ci[0] < 720 < ci[1]
