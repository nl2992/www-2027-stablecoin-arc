"""Synthetic pool states and schedules; arithmetic and calendar validation only."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from www_capacity.amm import Q96, sqrt_price_x96_from_price, uniswap_v2_amount_out, uniswap_v3_swap_within_range
from www_capacity.redemption import RedemptionSchedule

UTC = ZoneInfo("UTC")
L = 10**24


def test_v3_small_swap_matches_constant_product_on_virtual_reserves():
    p = Q96  # price 1.0
    x_virtual, y_virtual = L * Q96 // p, L * p // Q96
    lower = sqrt_price_x96_from_price(0.9)
    used, out, _ = uniswap_v3_swap_within_range(10**18, p, L, 0, True, lower)
    assert used == 10**18
    expected = uniswap_v2_amount_out(10**18, x_virtual, y_virtual, fee_bps=0)
    assert abs(out - expected) <= 2


def test_v3_fee_reduces_output_and_direction_moves_price_correctly():
    p = Q96
    lower, upper = sqrt_price_x96_from_price(0.9), sqrt_price_x96_from_price(1.1)
    _, no_fee, p_down = uniswap_v3_swap_within_range(10**20, p, L, 0, True, lower)
    _, fee, _ = uniswap_v3_swap_within_range(10**20, p, L, 100, True, lower)  # 1 bp tier
    assert fee < no_fee and p_down < p
    _, out1, p_up = uniswap_v3_swap_within_range(10**20, p, L, 0, False, upper)
    assert p_up > p and out1 > 0


def test_v3_input_beyond_range_edge_is_left_unused():
    p, lower = Q96, sqrt_price_x96_from_price(0.999)
    used, out, p_after = uniswap_v3_swap_within_range(10**30, p, L, 0, True, lower)
    assert p_after == lower and used < 10**30 and out > 0
    with pytest.raises(ValueError):
        uniswap_v3_swap_within_range(1, p, L, 0, True, sqrt_price_x96_from_price(1.1))


def test_sqrt_price_roundtrip():
    s = sqrt_price_x96_from_price(4.0)
    assert (s / Q96) ** 2 == pytest.approx(4.0, rel=1e-12)


def test_saturday_svb_weekend_waits_until_monday_open_across_dst_change():
    sched = RedemptionSchedule()
    sat = datetime(2023, 3, 11, 12, 0, tzinfo=UTC)
    assert not sched.is_open(sat)
    # US DST began 2023-03-12, so Monday 09:00 New York is 13:00 UTC (not 14:00).
    assert sched.next_open(sat) == datetime(2023, 3, 13, 13, 0, tzinfo=UTC)
    assert sched.minutes_until_open(sat) == pytest.approx((24 + 25) * 60)


def test_open_hours_holidays_and_naive_timestamps():
    sched = RedemptionSchedule(closed_dates=frozenset({date(2023, 3, 13)}))
    assert sched.next_open(datetime(2023, 3, 11, 12, tzinfo=UTC)) == datetime(2023, 3, 14, 13, tzinfo=UTC)
    wednesday_noon_ny = datetime(2023, 3, 15, 16, 0, tzinfo=UTC)
    assert RedemptionSchedule().is_open(wednesday_noon_ny)
    assert RedemptionSchedule().minutes_until_open(wednesday_noon_ny) == 0
    with pytest.raises(ValueError):
        RedemptionSchedule().is_open(datetime(2023, 3, 15, 12))
