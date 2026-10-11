# C4 — Executable restoration capacity: offline method (no historical estimates)

**Gate:** historical capacity may be computed only after crisis-period L2 or on-chain execution state has been validated **and** the user has authorized the capacity step. This module is tested on synthetic, hand-computed books only. Its outputs are *hypothetical* fills against one instantaneous book state, never realized trades.

Code: `src/www_capacity/orderbook.py`. Tests: `tests/test_capacity.py`, which has exact hand-computed answers.

## Definitions

- **Walk:** fill a base quantity against sorted levels (asks ascending, bids descending). If depth runs out, the fill is reported as partial, never extrapolated.
- **Cost-bounded capacity** `K(δ)`: the largest base quantity whose all-in VWAP, including the taker fee, stays within δ bps of a reference price. Cumulative VWAP is monotone in quantity, so `K` is solved exactly within the boundary level: `x = (L·Q − N)/(p − L)`, where `L` is the fee-adjusted limit, `Q` and `N` are the cumulative quantity and notional, and `p` is the boundary level's price.
- **Triangle restoration capacity:** applies when the wedge is positive. The loop is USD → BTC (BTC/USD asks) → q (BTC/q bids) → USD (q/USD bids). The marginal loop return cannot increase with quantity, so the restoration quantity is the point where the marginal unit stops paying. It is found by bisection, together with the cumulative after-fee profit at that point. The binding constraint is reported as `marginal_parity`, `depth` (any leg exhausted) or `inventory` (a USD budget cap).

## Not modeled yet (must be added or bounded before any historical use)

- latency, and book changes during execution;
- queue position;
- hidden or iceberg liquidity;
- maker rebates and volume-tiered fees;
- withdrawal and transfer delays between venues;
- redemption limits and banking hours (the primary market);
- Uniswap v3 concentrated liquidity, gas, and MEV.

The C1 replay engine supplies book states through `levels_from_book`. Because normalized feeds lack native sequence IDs, any capacity computed from them inherits the disclosed continuity limitation.

## Added in iteration 8

- **Negative-wedge loop** (`triangle_restoration_reverse`). The loop is USD → q (q/USD asks) → BTC (BTC/q asks) → USD (BTC/USD bids), sized in BTC. It has the same bisection, binding-constraint labels and USD inventory cap as the forward loop.
- **AMM math** (`src/www_capacity/amm.py`), in integer arithmetic:
  - Curve StableSwap `get_D` / `get_y` / `get_dy`. These follow the structure of the legacy 3pool contract: balances normalized by RATES, `Ann = A·N`, the fee taken on output, and `FEE_DENOMINATOR = 1e10`.
  - The Uniswap v2 `getAmountOut` formula.

  Tests cover the invariant, decimals, imbalance pricing, sensitivity to the amplification parameter, and one hand-computed v2 output. **These are not yet validated against block-pinned on-chain `get_dy` calls**; that requires an authorized archive endpoint (C5). Until then they are reference implementations used on synthetic states only.
