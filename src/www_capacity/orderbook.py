"""Order-book walking, cost-bounded capacity and triangle-loop restoration capacity.

Conventions: a level is (price, size) with price in quote per base and size in
base units. Buying walks asks upward; selling walks bids downward. Fees are a
proportional taker fee in bps applied to quote notional. Latency, queue
position, hidden liquidity and book changes during execution are NOT modeled;
results are upper bounds for a single instantaneous book state.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

Level = tuple[float, float]


def normalize_levels(levels: Iterable[Level], side: str) -> list[Level]:
    """Validate and sort: asks ascending, bids descending; aggregate duplicate prices."""
    if side not in {"ask", "bid"}:
        raise ValueError("side must be 'ask' or 'bid'")
    agg: dict[float, float] = {}
    for price, size in levels:
        if not price > 0 or size < 0:
            raise ValueError(f"invalid level {(price, size)}")
        if size > 0:
            agg[price] = agg.get(price, 0.0) + size
    return sorted(agg.items(), reverse=(side == "bid"))


def levels_from_book(book_side: Mapping, side: str, depth: int | None = None) -> list[Level]:
    """Convert a C1 ``Book.bids``/``Book.asks`` mapping (Decimal->Decimal) into sorted float levels."""
    levels = normalize_levels(((float(p), float(s)) for p, s in book_side.items()), side)
    return levels[:depth] if depth else levels


@dataclass(frozen=True)
class Fill:
    requested_base: float
    filled_base: float
    quote_notional: float  # before fees
    vwap: float | None
    worst_price: float | None
    levels_used: int

    @property
    def complete(self) -> bool:
        return self.filled_base >= self.requested_base - 1e-12


def walk(levels: Sequence[Level], base_qty: float) -> Fill:
    """Fill ``base_qty`` against already-sorted levels; partial if depth is exhausted."""
    if base_qty < 0:
        raise ValueError("quantity must be non-negative")
    remaining, notional, used, worst = base_qty, 0.0, 0, None
    for price, size in levels:
        if remaining <= 0:
            break
        take = min(size, remaining)
        notional += take * price
        remaining -= take
        used += 1
        worst = price
    filled = base_qty - max(remaining, 0.0)
    return Fill(base_qty, filled, notional, notional / filled if filled > 0 else None, worst, used)


def walk_quote(levels: Sequence[Level], quote_qty: float) -> Fill:
    """Spend (asks) or receive (bids) ``quote_qty`` of quote currency; returns base obtained/sold."""
    if quote_qty < 0:
        raise ValueError("quantity must be non-negative")
    remaining, base, notional, used, worst = quote_qty, 0.0, 0.0, 0, None
    for price, size in levels:
        if remaining <= 0:
            break
        take_quote = min(size * price, remaining)
        base += take_quote / price
        notional += take_quote
        remaining -= take_quote
        used += 1
        worst = price
    return Fill(base, base, notional, notional / base if base > 0 else None, worst, used)


def capacity_within_cost(levels: Sequence[Level], side: str, reference: float, max_cost_bps: float,
                         fee_bps: float = 0.0) -> float:
    """Largest base quantity whose all-in VWAP stays within ``max_cost_bps`` of ``reference``.

    Buy: vwap*(1+fee) <= ref*(1+cost). Sell: vwap*(1-fee) >= ref*(1-cost). Solved exactly per level,
    since cumulative VWAP is monotone in quantity.
    """
    if reference <= 0:
        raise ValueError("reference must be positive")
    f, c = fee_bps / 1e4, max_cost_bps / 1e4
    limit = reference * (1 + c) / (1 + f) if side == "ask" else reference * (1 - c) / (1 - f)
    qty = notional = 0.0
    for price, size in levels:
        better = price <= limit if side == "ask" else price >= limit
        if better:
            qty += size
            notional += size * price
            continue
        # Partial level: (notional + x*price)/(qty + x) == limit  ->  x = (limit*qty - notional)/(price - limit)
        x = (limit * qty - notional) / (price - limit)
        return qty + max(0.0, min(size, x))
    return qty


@dataclass(frozen=True)
class LoopResult:
    """Hypothetical triangle loop: USD -> BTC (BTC/USD asks) -> q (BTC/q bids) -> USD (q/USD bids)."""
    restoration_btc: float          # quantity at which the marginal loop return reaches zero
    restoration_profit_usd: float   # cumulative profit at that quantity, after fees
    limited_by: str                 # "marginal_parity", "depth" or "inventory"
    initial_marginal_bps: float     # top-of-book loop return after fees


def _loop_pnl(q: float, btc_usd_asks, btc_q_bids, q_usd_bids, f: float) -> tuple[float, bool]:
    buy = walk(btc_usd_asks, q)
    sell = walk(btc_q_bids, q)
    q_received = sell.quote_notional * (1 - f)
    conv = walk(q_usd_bids, q_received)
    complete = buy.complete and sell.complete and conv.complete
    return conv.quote_notional * (1 - f) - buy.quote_notional * (1 + f), complete


def triangle_restoration(btc_usd_asks: Sequence[Level], btc_q_bids: Sequence[Level], q_usd_bids: Sequence[Level],
                         *, fee_bps: float = 0.0, max_usd: float | None = None, tol_btc: float = 1e-9) -> LoopResult:
    """Quantity of BTC routed around the loop until the marginal unit no longer pays (positive-wedge direction).

    Marginal loop return is non-increasing in quantity (asks rise, bids fall), so bisection on the sign of
    a small forward difference finds the restoration point. ``max_usd`` caps USD inventory for leg 1.
    """
    f = fee_bps / 1e4
    if not (btc_usd_asks and btc_q_bids and q_usd_bids):
        raise ValueError("all three legs need at least one level")
    top = btc_q_bids[0][0] * (1 - f) * q_usd_bids[0][0] * (1 - f) / (btc_usd_asks[0][0] * (1 + f))
    initial_bps = 1e4 * (top - 1)
    if initial_bps <= 0:
        return LoopResult(0.0, 0.0, "marginal_parity", initial_bps)
    depth = min(sum(s for _, s in btc_usd_asks), sum(s for _, s in btc_q_bids))
    hi, limited = depth, "depth"
    if max_usd is not None:
        affordable = walk_quote(btc_usd_asks, max_usd / (1 + f)).filled_base
        if affordable < hi:
            hi, limited = affordable, "inventory"

    def marginal_positive(q: float) -> bool:
        step = max(tol_btc, 1e-12)
        a, ok_a = _loop_pnl(q, btc_usd_asks, btc_q_bids, q_usd_bids, f)
        b, ok_b = _loop_pnl(q + step, btc_usd_asks, btc_q_bids, q_usd_bids, f)
        return ok_a and ok_b and b > a

    if marginal_positive(hi - 2 * tol_btc):
        q_star = hi
    else:
        lo, top_q = 0.0, hi
        while top_q - lo > tol_btc:
            mid = (lo + top_q) / 2
            if marginal_positive(mid):
                lo = mid
            else:
                top_q = mid
        q_star = lo
        _, still_fillable = _loop_pnl(q_star + 4 * tol_btc, btc_usd_asks, btc_q_bids, q_usd_bids, f)
        limited = "marginal_parity" if still_fillable else "depth"
    profit, _ = _loop_pnl(q_star, btc_usd_asks, btc_q_bids, q_usd_bids, f)
    return LoopResult(q_star, profit, limited, initial_bps)
