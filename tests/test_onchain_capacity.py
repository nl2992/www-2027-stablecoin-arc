"""Synthetic StableSwap states; checks economics and monotonicity, not historical values."""

import pytest

from www_capacity.amm import stableswap_get_dy
from www_capacity.onchain import PoolState, absorption, restoration

E18, M = 10**18, 1_000_000
RATES = [E18, 10**30, 10**30]


def pool(dai=100 * M, usdc=100 * M, usdt=100 * M, amp=2000, fee=1_000_000):
    return PoolState(balances=[dai * E18, usdc * 10**6, usdt * 10**6], rates=RATES, decimals=[18, 6, 6], amp=amp,
                     fee=fee, usd_per_token=[1.0, 1.0, 1.0])


def test_absorption_is_monotone_in_delta_and_respects_the_floor():
    st = pool()
    a10, a50, a100 = (absorption(st, 1, 0, d) for d in (10, 50, 100))
    assert 0 < a10 < a50 < a100
    x = int(a50 * 10**6)
    avg = stableswap_get_dy(1, 0, x, st.balances, st.rates, st.amp, st.fee) / E18 / (x / 10**6)
    assert avg >= 1 - 50e-4
    over = stableswap_get_dy(1, 0, int(x * 1.01), st.balances, st.rates, st.amp, st.fee) / E18 / (x * 1.01 / 10**6)
    assert over < 1 - 50e-4 + 1e-6  # just beyond the solution, the floor binds


def test_pool_already_rich_in_the_stressed_coin_absorbs_less_and_restores_more():
    balanced, skewed = pool(), pool(dai=50 * M, usdc=200 * M, usdt=50 * M)
    assert absorption(skewed, 1, 0, 50) < absorption(balanced, 1, 0, 50)
    assert restoration(skewed, 1, 0, 50) > restoration(balanced, 1, 0, 50)


def test_fee_above_tolerance_gives_zero_capacity():
    st = pool(fee=2_000_000_00)  # 200 bps pool fee
    assert absorption(st, 1, 0, 10) == 0 and restoration(st, 1, 0, 10) == 0


def test_higher_amplification_increases_capacity():
    assert absorption(pool(amp=2000), 1, 0, 50) > absorption(pool(amp=50), 1, 0, 50)


def test_metapool_valuation_uses_virtual_price():
    vp = 1.02 * E18
    meta = PoolState(balances=[60 * M * 10**6, 55 * M * E18], rates=[10**30, int(vp)], decimals=[6, 18], amp=200,
                     fee=4_000_000, usd_per_token=[1.0, 1.02])
    a = absorption(meta, 0, 1, 50)
    assert a > 0
    x = int(a * 10**6)
    value = stableswap_get_dy(0, 1, x, meta.balances, meta.rates, meta.amp, meta.fee) / E18 * 1.02
    assert value / (x / 10**6) == pytest.approx(1 - 50e-4, abs=1e-4)
