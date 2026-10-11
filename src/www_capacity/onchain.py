"""On-chain absorption and restoration capacity on StableSwap state (definition: docs/c6_onchain_capacity.md).

Par-relative, fee-inclusive, single-pool, single-hop upper bounds. Quantities are in
units of the stressed coin s (= USD at par). Never uses an exchange price of s.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .amm import stableswap_get_dy


@dataclass(frozen=True)
class PoolState:
    balances: Sequence[int]
    rates: Sequence[int]       # RATES-style multipliers (10**(36-decimals); metapool LP coin: virtual price)
    decimals: Sequence[int]
    amp: int
    fee: int
    usd_per_token: Sequence[float]  # valuation of each coin in USD per whole token (par = 1.0; 3CRV = vp/1e18)


def _dy(state: PoolState, i: int, j: int, dx_raw: int) -> int:
    if dx_raw <= 0:
        return 0
    try:
        out = stableswap_get_dy(i, j, dx_raw, state.balances, state.rates, state.amp, state.fee)
    except (ArithmeticError, ZeroDivisionError):
        return 0
    return max(out, 0)


def _largest_true(pred, start: int, max_doublings: int = 80) -> int:
    """Largest integer x >= start with pred(x) True (pred monotone True->False); 0 if pred(start) is False.

    ``start`` is one whole token in raw units: below that, integer rounding (not liquidity) decides the answer.
    """
    if not pred(start):
        return 0
    lo, hi = start, start * 2
    for _ in range(max_doublings):
        if not pred(hi):
            break
        lo, hi = hi, hi * 2
    else:
        return lo
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if pred(mid):
            lo = mid
        else:
            hi = mid
    return lo


def absorption(state: PoolState, s: int, c: int, delta_bps: float) -> float:
    """Largest quantity of s sellable for c with average USD value >= (1 - delta) per unit of s."""
    unit_s = 10 ** state.decimals[s]
    floor = 1 - delta_bps / 1e4

    def ok(x_raw: int) -> bool:
        value = _dy(state, s, c, x_raw) / 10 ** state.decimals[c] * state.usd_per_token[c]
        return value >= floor * x_raw / unit_s * state.usd_per_token[s]

    return _largest_true(ok, unit_s) / unit_s


def restoration(state: PoolState, s: int, c: int, delta_bps: float) -> float:
    """Largest quantity of s buyable with c at average USD cost <= (1 + delta) per unit of s."""
    unit_c = 10 ** state.decimals[c]
    cap = 1 + delta_bps / 1e4

    def ok(y_raw: int) -> bool:
        got = _dy(state, c, s, y_raw) / 10 ** state.decimals[s]
        spent = y_raw / unit_c * state.usd_per_token[c]
        return got > 0 and spent <= cap * got * state.usd_per_token[s]

    y = _largest_true(ok, unit_c)
    return _dy(state, c, s, y) / 10 ** state.decimals[s]


def capacity_table(state: PoolState, s: int, counterparts: Sequence[int],
                   deltas: Sequence[float] = (10, 50, 100)) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for c in counterparts:
        for d in deltas:
            out[f"c{c}_{int(d)}bps"] = {"absorption": absorption(state, s, c, d), "restoration": restoration(state, s, c, d)}
    return out
