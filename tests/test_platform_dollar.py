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


def test_decomposition_attributes_token_and_ledger_failures():
    from www_rescue.decompose import components, summarize
    idx = minutes("2023-03-11", 6 * 60)
    zero = pd.Series(0.0, idx)
    # token failure: coin -1000 bps on venue and on reference; BTC equal on both venues
    h = components(zero - 0.1, zero + np.log(20000), zero + np.log(20000), zero - 0.1)
    s = summarize(h)
    assert s["hours"] == 6 and abs(s["median_L"]) < 1e-9 and np.isclose(s["median_T"], -1000)
    assert s["median_ledger_share"] == 0 and s["median_abs_T_minus_D_ref"] < 1e-9
    # ledger failure: venue unit worth 5% more -> every venue price 5% lower; coin fine on reference
    h = components(zero - 0.05, zero + np.log(20000) - 0.05, zero + np.log(20000), zero)
    s = summarize(h)
    assert np.isclose(s["median_L"], -500) and abs(s["median_T"]) < 1e-9 and np.isclose(s["median_ledger_share"], 1)


def test_shifted_phases_move_internal_boundaries_only():
    from www_rescue.platform_dollar import shifted_phases
    ph = shifted_phases(1)
    assert ph[0][1] == PHASES[0][1] and ph[-1][2] == PHASES[-1][2]
    assert ph[1][1] == "2023-06-06" and all(ph[i][2] == ph[i + 1][1] for i in range(len(ph) - 1))


def test_liquidity_counts_traded_minutes_and_hourly_sums():
    from www_rescue.platform_dollar import liquidity
    idx = minutes("2023-05-01", 120)
    frame = pd.DataFrame({"trades": 2.0, "quote_volume": 10.0, "volume": np.r_[np.ones(60), np.zeros(60)]}, idx)
    row = liquidity(frame, [("p", "2023-05-01 00:00", "2023-05-01 02:00", "")])[0]
    assert row["traded_minute_share"] == 0.5 and row["median_hourly_trades"] == 120 and row["median_hourly_quote_volume"] == 600


def test_monitor_flags_ledger_only_when_assets_agree_and_token_on_external_move():
    from www_rescue.monitor import classify, label
    h = pd.DataFrame({"L": [-500.0, -500.0, 0.0, 5.0], "PD_USDT": [-480.0, -100.0, 0.0, 3.0],
                      "T_USDC": [0.0, 0.0, -300.0, 20.0]}, index=minutes("2023-03-11", 4))
    f = classify(h)
    assert list(f["ledger_flag"]) == [True, False, False, False]
    assert list(f["token_flag_USDC"]) == [False, False, True, False]
    assert list(label(pd.DatetimeIndex(["2023-03-11", "2023-05-01"], tz="UTC"))) == ["svb_run", "calm"]
