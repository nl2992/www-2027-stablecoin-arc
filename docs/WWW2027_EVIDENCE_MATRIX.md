# WWW 2027 evidence matrix

Version: 2026-10-12. The source of truth is the committed reports. Each paper number comes from `paper/generated/*.tex`.

**Classes:**
- **M**: measured on real data.
- **S**: synthetic or software validation only.
- **L**: literature claim (verified source).
- **H**: hypothesis, not tested.
- **I**: interpretation.
- **U**: unknown or not measurable with authorized data.

## Measured facts (M)

| # | Claim | Evidence | Caveat |
|---|---|---|---|
| M1 | The registry holds 19 sourced entries; 4 independent clusters are ACCEPTED (Terra 2022, SVB 2023, TUSD 2024, FDUSD 2025) | `configs/event_registry.json`, `reports/events/cross_event_summary.json` | Terra and SVB are exploratory (measured before the freeze, or post hoc). TUSD and FDUSD are the only confirmatory (OOS) events, and both are issuer-specific. |
| M2 | DV1 (median \|D\|, event minus control, bps, block bootstrap): UST 1,028 [723, 2,244]; SVB 208 [92, 336]; TUSD 113 [100, 121]; FDUSD 45 [34, 51] | `reports/events/cross_event_results.md` | Minute closes on one USD venue per event (A3) |
| M3 | DV4, within-venue triangle-wedge contrast (bps): SVB 6.53; TUSD −0.08; FDUSD 0.02. Small next to D. | same | Within-venue triangle no-arbitrage is the expected baseline (see F3) |
| M4 | Rejected and negative cases stay below R1: FTX 2022 (USDT), June 2023 (USDT, Bitstamp), BUSD-halt placebo | same | June 2023 on Binance.US was a venue artifact (A2) |
| M5 | A6 screen of Binance.US through 2023-05 | `reports/events/screen_A6.json` | Screen counts are in `numbers.tex` |
| M6 | On-chain state reproduced exactly (`get_dy` difference 0) and swap-validated for 3pool and the wormhole UST pool | `reports/c2/archive_validation.json`, `archive_checks.json` | 3 LIVE_VERIFIED contracts only |
| M7 | Par-relative absorption at δ = 50 bps, median baseline → event: SVB USDC→DAI 177.4M → 154.0M; USDC→USDT 157.5M → 0; June 2023 USDT→DAI 132.0M → 42.5M; UST→3CRV 379.9M → 0. Restoration rose in every case. | `reports/c6/onchain_capacity_summary.md` | On-chain only, Curve only; 6-hour sampling, with hourly sampling around the event (PR #5) |
| M8 | With observed counterpart prices, SVB event USDC→DAI absorption falls 154.0M → 0 (baseline 177.4M → 177.1M) | `reports/c6/onchain_capacity_cex_valued.json` (PR #5) | Absorption is valuation-sensitive in stress |
| M9 | June 2023: on-chain absorption contracted (USDT share 30% → 67%) with no qualifying USD depeg | M4 + M7 | Counterexample to "capacity contraction implies depeg" |
| M10 | Normal-market CEX depth bands | `reports/c1/normal_market_depth.json` | Not crisis-period depth |

## Synthetic or software validation (S)

| # | Claim | Evidence |
|---|---|---|
| S1 | The StableSwap solver is monotone in δ, respects the floor, gives zero capacity when fee > tolerance, and increases with A | `tests/test_onchain_capacity.py` |
| S2 | Order-book walk, Uniswap v2/v3 and redemption-window capacity are correct on fixtures | `tests/test_capacity*.py` |
| S3 | Keccak and calldata match standard vectors; RPC plans are read-only and tamper-checked | `tests/test_validation_plan.py` |
| S4 | The R1 screen and clustering rules behave as specified | `tests/test_screen.py` |

## Literature claims (L), verified

| # | Claim | Source |
|---|---|---|
| L1 | Persistent crypto cross-exchange price deviations; arbitrage capital is constrained | Makarov & Schoar 2020, JFE (`makarov2020trading`) |
| L2 | Primary/secondary market structure and arbitrage keep stablecoins near par | Lyons & Viswanath-Natraj (`lyons2023keeps`); Fed note (`watsky2024primary`) |
| L3 | Arbitrage is concentrated among a few authorized arbitrageurs, which links runs and peg stability | Ma, Zeng & Zhang (`ma2025runs`) |
| L4 | Pool-composition metrics on Curve (entropy, net swap flow, markout) plus BOCD flagged the SVB USDC depeg about 5 hours before it fell below $0.99 | Cintra & Holloway 2023, arXiv:2306.10612 (**not yet cited; add**) |
| L5 | The Terra run was led by large, sophisticated holders; on-chain transparency sped it up | Liu, Makarov & Schoar, NBER w31160 (**not yet cited; add**) |
| L6 | Non-atomic (CEX–DEX) arbitrage accounts for more than a quarter of volume on the top-5 Ethereum DEXes | Heimbach et al., arXiv:2401.01622 (**verify the author list before citing**) |

## Hypotheses (H), not tested or not testable

- H1 (pre-registered): the cross-quote wedge is smaller than the peg dislocation in confirmatory in-sample events. **Not testable**, because no accepted confirmatory in-sample event exists.
- H-cap: on-chain absorption contraction precedes the CEX dislocation. **Untested** (task T8); CurveMetrics (L4) pre-empts much of its novelty.

## Interpretations (I), to be labelled as such in the paper

- I1: cross-quote arbitrage stayed active while redemption or dollar arbitrage was impaired. Consistent with M3, but M3 is also expected under ordinary within-venue no-arbitrage.
- I2: the episodes split into market-wide and issuer-specific types (mechanism table). Rests on 4 clusters.
- I3: par-relative absorption contraction mainly reflects pool composition, which is mechanical for StableSwap with fixed A and fee.

## Unknowns (U)

- U1: crisis-period CEX L2 depth (paid only), so no CEX–DEX executable capacity.
- U2: realised arbitrage volumes and the identities of arbitrageurs.
- U3: redemption-queue state at the issuers.
- U4: whether the results hold for venues beyond the selected USD venue per event (partial robustness only).
