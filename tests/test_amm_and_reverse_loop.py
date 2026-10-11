"""Synthetic pool states and books; arithmetic validation only, not historical pool behavior."""

import pytest

from www_capacity.amm import stableswap_D, stableswap_get_dy, stableswap_y, uniswap_v2_amount_out
from www_capacity.orderbook import triangle_restoration_reverse

E18 = 10**18
RATES_3POOL = [E18, 10**30, 10**30]  # DAI 18 decimals; USDC, USDT 6 decimals normalized to 1e18
M = 1_000_000  # one million tokens


def balanced():
    return [M * E18, M * 10**6, M * 10**6]


def test_balanced_invariant_equals_sum_of_normalized_balances():
    xp = [M * E18] * 3
    assert abs(stableswap_D(xp, 2000) - 3 * M * E18) <= 3


def test_small_balanced_swap_is_near_par_minus_fee_and_respects_decimals():
    dy = stableswap_get_dy(1, 2, 1_000 * 10**6, balanced(), RATES_3POOL, amp=2000, fee=4_000_000)  # 4 bps fee
    assert 999.5e6 < dy < 1_000e6  # USDC -> USDT, 6-decimal output
    dai = stableswap_get_dy(1, 0, 1_000 * 10**6, balanced(), RATES_3POOL, amp=2000, fee=0)
    assert dai == pytest.approx(1_000 * E18, rel=1e-6)  # 18-decimal output


def test_imbalance_makes_the_abundant_coin_cheap():
    # Pool holds 70% USDT, like the June 2023 3pool imbalance reported in news (illustrative magnitudes only).
    skewed = [150_000 * E18, 150_000 * 10**6, 700_000 * 10**6]
    sell_usdt = stableswap_get_dy(2, 1, 10_000 * 10**6, skewed, RATES_3POOL, amp=2000, fee=0)
    buy_usdt = stableswap_get_dy(1, 2, 10_000 * 10**6, skewed, RATES_3POOL, amp=2000, fee=0)
    assert sell_usdt < 10_000 * 10**6 < buy_usdt


def test_higher_amplification_means_lower_price_impact():
    skewed = [150_000 * E18, 150_000 * 10**6, 700_000 * 10**6]
    low = stableswap_get_dy(2, 1, 50_000 * 10**6, skewed, RATES_3POOL, amp=10, fee=0)
    high = stableswap_get_dy(2, 1, 50_000 * 10**6, skewed, RATES_3POOL, amp=2000, fee=0)
    assert low < high < 50_000 * 10**6


def test_stableswap_y_preserves_invariant_and_rejects_bad_input():
    xp = [M * E18, M * E18, M * E18]
    x_new = xp[0] + 10_000 * E18
    y = stableswap_y(0, 1, x_new, xp, 2000)
    assert abs(stableswap_D([x_new, y, xp[2]], 2000) - stableswap_D(xp, 2000)) <= 10
    with pytest.raises(ValueError):
        stableswap_y(1, 1, x_new, xp, 2000)
    with pytest.raises(ValueError):
        stableswap_D([0, E18, E18], 2000)


def test_uniswap_v2_matches_hand_computed_amount_out():
    # 1,000 in against 100,000 / 100,000 reserves: 1000*9970*100000 // (100000*10000 + 1000*9970)
    assert uniswap_v2_amount_out(1_000, 100_000, 100_000) == 987
    assert uniswap_v2_amount_out(1_000, 100_000, 100_000, fee_bps=0) == 990
    with pytest.raises(ValueError):
        uniswap_v2_amount_out(0, 1, 1)


def test_reverse_loop_buys_cheap_stablecoin_then_btc_and_sells_btc_for_usd():
    # USDC at 0.98 USD, BTC/USDC 100, BTC/USD 100: each BTC costs 98 USD, sells for 100.
    q_usd_asks = [(0.98, 98.0), (1.0, 10_000.0)]
    btc_q_asks = [(100.0, 5.0)]
    btc_usd_bids = [(100.0, 5.0)]
    r = triangle_restoration_reverse(q_usd_asks, btc_q_asks, btc_usd_bids)
    assert r.restoration_btc == pytest.approx(0.98, abs=1e-6)  # cheap USDC (98 units) buys 0.98 BTC
    assert r.restoration_profit_usd == pytest.approx(0.98 * 100 - 98 * 0.98, abs=1e-4)
    assert r.initial_marginal_bps == pytest.approx(1e4 * (1 / 0.98 - 1))


def test_reverse_loop_inventory_cap_and_fee_elimination():
    q_usd_asks = [(0.98, 1_000.0)]
    btc_q_asks = [(100.0, 5.0)]
    btc_usd_bids = [(100.0, 5.0)]
    capped = triangle_restoration_reverse(q_usd_asks, btc_q_asks, btc_usd_bids, max_usd=49.0)
    assert capped.limited_by == "inventory" and capped.restoration_btc == pytest.approx(0.5, abs=1e-6)
    assert triangle_restoration_reverse(q_usd_asks, btc_q_asks, btc_usd_bids, fee_bps=100).restoration_btc == 0.0
