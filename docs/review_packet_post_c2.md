# Independent review packet: work after C2 (C3, E1–E2, P1, C4–C5, M1–M4)

**Range:** `c48e714` (accepted CoinAPI follow-up) → `a6b77a8`. The work is on stacked branches; see `docs/RESEARCH_STATE.md`.
**Research boundary:** no purchases, accounts, credentials, provider contact, gated APIs or data downloads. Historical capacity has not been estimated.

## Decisions requested from the reviewer

1. Accept the multi-event design: the registry, rules R1–R4, independence clusters, and the out-of-sample and placebo roles.
2. Accept the frozen pre-analysis plan, including amendment A1, as the confirmatory protocol.
3. Confirm the descriptive framing while fewer than three independent confirmatory episodes exist.

## What was built and how to check it

| Checkpoint | Claim | Evidence | How to check |
|---|---|---|---|
| C2 gate | CoinAPI is CONDITIONAL; no L2 source is selected | `reports/c2/source_decision.json` | `tests/test_c2_decision.py` recomputes every decision |
| C3 | Anchor triangle-wedge levels and persistence; crisis vs pre-crisis differences | `reports/c3/*` | rerun section 2 of REPRODUCE.md; deterministic seeds |
| E1 | 16 sourced candidates in 13 clusters; only the anchor ACCEPTED | `configs/event_registry.json`, `docs/e1_event_registry.md` | `tests/test_events.py`, which includes mutation tests of the validator |
| E2 | Kline and USD-reference adapters, per-event runner, batch driver with rule-based status changes | `src/www_events/*` | `tests/test_binance_klines.py`, `test_event_runner.py`, `test_batch.py` (synthetic end to end) |
| P1 | Plan frozen by hash before any non-anchor measurement; DV1–DV5; mechanical cross-event decisions | `docs/PRE_ANALYSIS_PLAN.md`, `reports/events/cross_event_summary.json` | `tests/test_plan_freeze.py`, `test_plan_dvs.py`, `test_summary.py` |
| C4 | Offline capacity method: book walk, cost-bounded K(δ), both loop directions, StableSwap, Uniswap v2/v3, redemption window | `src/www_capacity/*` | hand-computed fixtures in `tests/test_capacity.py`, `test_amm_and_reverse_loop.py`, `test_v3_and_redemption.py` |
| C5 | Event-linked contract registry; offline block-pinned request plan | `reports/c2/contract_registry.json`, `reports/c2/validation_plan.json` | `tests/test_c2_contracts.py`, `test_validation_plan.py` (Keccak vectors) |
| M1–M4 | Provisional manuscript with generated numbers, tables and figures; 16 verified references | `paper/` | `tests/test_paper.py`, `test_figures.py` (byte-identical regeneration) |

## Evidence status (what is and is not established)

- **Measured (anchor only, exploratory):**
  - USDC/USD peg dislocation: +208 bps event-minus-baseline (95% CI 92–336); recovery about 68 h.
  - Triangle wedge: +6.5 bps (CI 4.6–9.4).
  - Half-life ratio D/W ≈ 95.
  - BTC volatility roughly doubled, which is a competing explanation.
- **Not established:** any other event, any confirmatory hypothesis test, executable capacity, or historical on-chain state.
- **Cross-event decisions (generated):** H1 INSUFFICIENT_EVENTS; H2 INSUFFICIENT_EVENTS; H3 NOT_TESTABLE; framing DESCRIPTIVE.

## Known limitations a reviewer should weigh

1. The anchor was measured before the plan was frozen. It is labelled exploratory and excluded from confirmatory counts.
2. Candle closes are last trades. Minute-level persistence is biased by bid-ask bounce, which is why the plan's persistence measure uses 15-minute bins.
3. The candidate public archives are quoted in USDT, so acceptance depends on a USD reference leg.
4. No BTC/USDe market is listed on Binance, so DV4/DV5 are undefined for the USDe event there.
5. AMM math and pool ABIs have not been validated against block-pinned on-chain calls.
6. The PDF build is unverified (no TeX installed). Structural LaTeX checks stand in for it.

## Acceptance gates for this packet

- The full suite passes offline with deprecation warnings treated as errors (165 pytest items at `a6b77a8`; 167 once this packet's own tests are included).
- Every manuscript number, table and figure regenerates from committed reports.
- No registry status changes except through `apply_status`. The plan file is unchanged since the freeze.
- No claim in `paper/main.tex` goes beyond the evidence status above.
