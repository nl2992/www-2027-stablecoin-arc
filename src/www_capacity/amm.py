"""Integer AMM swap math for offline capacity work.

``stableswap_*`` follows the structure of the legacy Curve 3pool Vyper source
(get_D / get_y / get_dy with RATES-normalized balances, Ann = A * N, fee on
output with FEE_DENOMINATOR = 1e10). ``uniswap_v2_amount_out`` follows the
Uniswap v2 router formula with the 0.3% fee. These have NOT yet been validated
against block-pinned on-chain calls (C5); until then they are reference
implementations exercised on synthetic states only.
"""

from __future__ import annotations

from collections.abc import Sequence

PRECISION = 10**18
FEE_DENOMINATOR = 10**10


def stableswap_D(xp: Sequence[int], amp: int) -> int:
    """Invariant D for normalized balances ``xp`` (Newton iteration, as in the 3pool contract)."""
    n = len(xp)
    s = sum(xp)
    if s == 0:
        return 0
    if any(x <= 0 for x in xp):
        raise ValueError("balances must be positive")
    d, ann = s, amp * n
    for _ in range(255):
        d_p = d
        for x in xp:
            d_p = d_p * d // (x * n)
        d_prev = d
        d = (ann * s + d_p * n) * d // ((ann - 1) * d + (n + 1) * d_p)
        if abs(d - d_prev) <= 1:
            return d
    raise ArithmeticError("D did not converge")


def stableswap_y(i: int, j: int, x: int, xp: Sequence[int], amp: int) -> int:
    """New normalized balance of coin j after coin i's normalized balance becomes ``x``."""
    n = len(xp)
    if i == j or not (0 <= i < n and 0 <= j < n):
        raise ValueError("invalid coin indices")
    d = stableswap_D(xp, amp)
    ann = amp * n
    c, s_ = d, 0
    for k in range(n):
        if k == i:
            xk = x
        elif k != j:
            xk = xp[k]
        else:
            continue
        s_ += xk
        c = c * d // (xk * n)
    c = c * d // (ann * n)
    b = s_ + d // ann
    y = d
    for _ in range(255):
        y_prev = y
        y = (y * y + c) // (2 * y + b - d)
        if abs(y - y_prev) <= 1:
            return y
    raise ArithmeticError("y did not converge")


def stableswap_get_dy(i: int, j: int, dx: int, balances: Sequence[int], rates: Sequence[int], amp: int,
                      fee: int) -> int:
    """Raw output units of coin j for ``dx`` raw units of coin i, after the pool fee (fee in 1e10 units)."""
    if dx < 0:
        raise ValueError("dx must be non-negative")
    xp = [b * r // PRECISION for b, r in zip(balances, rates, strict=True)]
    x = xp[i] + dx * rates[i] // PRECISION
    y = stableswap_y(i, j, x, xp, amp)
    dy = (xp[j] - y - 1) * PRECISION // rates[j]
    return dy - fee * dy // FEE_DENOMINATOR


def uniswap_v2_amount_out(amount_in: int, reserve_in: int, reserve_out: int, fee_bps: int = 30) -> int:
    """Uniswap v2 getAmountOut (integer, fee taken on input)."""
    if amount_in <= 0 or reserve_in <= 0 or reserve_out <= 0:
        raise ValueError("amount and reserves must be positive")
    keep = 10_000 - fee_bps
    amount_in_with_fee = amount_in * keep
    return amount_in_with_fee * reserve_out // (reserve_in * 10_000 + amount_in_with_fee)
