# C6 — On-chain restoration capacity: definition (fixed before computation)

**Written:** 2026-10-11, before any capacity value was computed. Authorized by the user after reviewer decision 3. **Scope:** on-chain only. These measures are **not** comprehensive CEX–DEX restoration capacity: crisis-day exchange depth is unavailable.

## Objects

- **Pool and coin.** For an accepted or measured event, take a pool \(P\) whose state was reproduced exactly (C5c). Take a stressed coin \(s\) and a counterpart coin \(c\) in the same pool:

  | Event | Pool | \(s\) | \(c\) |
  |---|---|---|---|
  | SVB 2023 | 3pool | USDC | DAI, USDT |
  | June 2023 | 3pool | USDT | DAI, USDC |
  | UST 2022 | wormhole-UST/3CRV, legacy UST metapool | UST | 3CRV |

- **Valuation.** Every coin other than \(s\) is valued at par (1 USD). 3CRV is valued at the 3pool `get_virtual_price()` read at the same block. Capacity is therefore measured **relative to par from pool state alone**; it never uses the observed exchange price of \(s\). This keeps the explanatory measure from mechanically restating the dislocation it is meant to explain.

- **Absorption capacity** \(A_b(\delta)\): the largest quantity \(x\) of \(s\) such that selling \(x\) into the pool for \(c\) returns, after the pool fee, an average value of at least \((1-\delta)\) USD per unit of \(s\). Formally, \(\text{get\_dy}_{s\to c}(x)\cdot v_c / x \ge 1-\delta\). This is how much stress-selling the pool can take before the average realized discount exceeds \(\delta\).

- **Restoration capacity** \(R_b(\delta)\): the largest quantity of \(s\) that can be *bought* from the pool with \(c\) at an average cost of at most \((1+\delta)\) USD per unit of \(s\). This is how much the pool can supply to buyers bringing \(s\) back toward par.

- **Grid and computation.** \(\delta \in \{10, 50, 100\}\) bps. Both quantities are solved by bisection on the integer StableSwap arithmetic (`www_capacity.amm.stableswap_get_dy`), applied to state read at block \(b\): A, fee, balances, decimals, and the virtual price for metapools. They are reported in units of \(s\), which equal USD at par.

## Inclusion rule (added before any computation, after the swap cross-checks)

Only pools whose reproduced state was also validated against a real historical swap enter the capacity computation, per `reports/c2/archive_checks.json`. Included: 3pool (SVB, June 2023) and wormhole-UST/3CRV (UST 2022). **Excluded:** the legacy UST metapool, whose cross-check was inconclusive.

## Sampling path

- **Samples.** One block about every 6 hours, from the event's baseline start to its recovery end (R3 windows). Steps are 1,800 blocks after the Merge and 1,640 blocks before it. The actual timestamp of each sampled block is recorded.
- **Per sample:** the block header, and A, fee, balances and virtual price, all read at that block. A and fee are re-read every time, because they can change through governance ramps.

## Reported summaries (descriptive)

- Per window (baseline, event, recovery): median, minimum and 10th percentile of \(A_b(\delta)\) and \(R_b(\delta)\), plus the pool's share of \(s\).
- The event-to-baseline ratio of median absorption at each \(\delta\).

## Limitations (stated in advance)

- Each figure is a single-pool, single-hop upper bound. It ignores gas, MEV, latency, routing across pools, and the fact that pool state changes between samples.
- Valuing the counterpart at par assumes the counterpart did not depeg. That assumption fails for DAI during SVB; DAI and USDT counterparts are therefore reported separately.
- Metapool capacity uses 3CRV at virtual price, not underlying-coin execution.
- The results are associations between on-chain capacity and stress windows. They are not causal effects, and they are not CEX–DEX capacity.
