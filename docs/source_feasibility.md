# Historical source feasibility (C0)

## Ethereum and AMM state

Google Blockchain Analytics documents full-history Ethereum tables including blocks, transactions, logs, token transfers, traces, receipts and account state. These can support event extraction. Event logs alone do not answer arbitrary historical `eth_call`/swap-quote questions; state must be queried from an archive-capable RPC provider or reconstructed from complete state transitions. Query cost, retention, and account access need confirmation. Sources (accessed 2026-10-11): [schema](https://docs.cloud.google.com/blockchain-analytics/docs/schema), [overview](https://docs.cloud.google.com/blockchain-analytics/docs/overview).

Curve's legacy 3pool uses DAI, USDC and USDT. For March 2023, identify the exact deployed pool and implementation, historical balances, amplification parameter, fee and admin-fee semantics. Current StableSwap-NG documentation is not evidence of the historical deployment's configuration. Source: [Curve plain pools](https://docs.curve.finance/developer/stableswap/pools/plain-pools).

Uniswap v3 reconstruction requires exact March 2023 pool addresses and token ordering/decimals, plus complete swaps, mint/burn events and tick/liquidity state from deployment through each target block, or archive state. Maker's current LitePSM documentation cannot establish March 2023 PSM contracts or parameters; verify the historical deployment, direction-specific fee and capacity from contract history.

## CEX decision

The CEX verdict is **UNVERIFIED for crisis-period capacity**. A single March 1 Binance.US sample was downloaded and counted, but March 10–12 symbol/day coverage, continuity and commercial entitlement were not tested. See [`../CEX_L2_SOURCE_AUDIT.md`](../CEX_L2_SOURCE_AUDIT.md) for exact URLs and sample hash.

## C0 decision

| Requirement | Finding | Gate status |
|---|---|---|
| Extract historical swaps and block times | Documented tables support this | Feasible in principle; credentials/cost not tested |
| Reproduce historical arbitrary Curve/Uniswap quote | Needs archive state or validated full state reconstruction | Unverified |
| Recover March 2023 Maker PSM terms/capacity | Historical deployment and changing parameters not established | Unverified |
| Validate against historical on-chain quotes | No archive RPC or comparison fixtures available in C0 | Not tested |

Before C4, record chain ID, addresses, deployment blocks, ABI/code hashes, token decimals, provider, retention, and a block-specific state/quote validation fixture. No C0 result supports historical DEX execution capacity.
