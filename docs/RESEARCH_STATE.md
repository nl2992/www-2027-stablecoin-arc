# Research state (durable; read at the start of every iteration)

Cross-check against `git log` and the code before acting. Update at the end of every iteration.

**Objective:** test whether constraints on executable arbitrage restoration capacity help explain the magnitude, persistence and resolution of stablecoin price fragmentation, *across independent stress events and normal regimes*. March 2023 is the anchor, not the whole sample. No causal claims beyond what the evidence supports.

**Environment:** numpy is capped below 2.5, because NumPy 2.5 deprecates generic timedeltas that pandas 2.3 still creates. Run the suite with `-W error::DeprecationWarning`.

**Repository conventions:** commits, merges and PRs carry no AI/tool attribution. Never force-push or merge PRs without authorization. Licensed raw data stays out of Git.

## Branches and checkpoint commits (stacked)

| Checkpoint | Branch | Head | Status |
|---|---|---|---|
| C0 audit | merged into main line | 9157037 | accepted |
| C1 L2 replay prototype | c1/orderbook-validation | ad74f00 | accepted |
| C2 access feasibility + CoinAPI follow-up | c2/data-access-feasibility | c48e714 → 8610d57 (source gate) | PR nl2992/www-2027-stablecoin-arc#3 open |
| C3 fragmentation/persistence (anchor) | c3/fragmentation-persistence | 331ea9a | pushed, no PR |
| E1 multi-event registry + adapters | e1/multi-event-registry | ef2e29d | pushed, no PR |
| M1 manuscript skeleton | m1/manuscript-skeleton | 96b9a4d | pushed, no PR |
| C4 capacity method (offline) | c4/capacity-method | 9924197 | pushed, no PR |
| M2 literature + generated tables | m2/literature-and-tables | dac411f | pushed, no PR |
| C4b v3 swap + redemption window | c4b/v3-and-redemption-window | 15459bf | pushed, no PR |
| M3 figures | m3/figures | d4af74b | pushed, no PR |
| P1 pre-analysis plan (frozen) + plan DVs | p1/pre-analysis-plan | see iteration log | pushed, no PR |

## Component status

| ID | Component | Status | Evidence |
|---|---|---|---|
| C0 | IAQF panel audit, corrected parity formula | DONE | `docs/c0_review_packet.md` |
| C1 | L2 replay prototype (Tardis normalized CSV) | DONE; crisis cells ACCESS_BLOCKED | `docs/c1_review_packet.md` |
| C2 | Source feasibility + source gate | DONE; CoinAPI CONDITIONAL; no L2 source selected | `docs/c2_source_decision.md` |
| C3 | Anchor fragmentation + robustness | DONE (descriptive, candle-based) | `docs/c3_fragmentation.md` |
| E1 | Event registry, rules R1–R4, coverage matrix | DONE (first pass) | `docs/e1_event_registry.md` |
| E2a | Binance public-kline adapter (parse, checksum, ms/µs units, gaps, manifest) | DONE (offline, synthetic tests) | `src/www_events/binance_klines.py` |
| E2b | Event protocol runner (windows, quote-basis conversion, R1, diagnostics) | DONE; anchor run | `src/www_events/runner.py`, `reports/events/E2023-03-USDC-SVB_protocol.json` |
| E2 | Multi-event panel harmonization (download + R1 on each event) | BLOCKED: file-download authorization | E1 decision 1 |
| C4a | Capacity method: book walk, cost-bounded K(δ), triangle restoration (synthetic only) | DONE offline | `docs/c4_capacity_method.md` |
| C4 | CEX executable capacity (historical) | BLOCKED: no authorized L2 + capacity gate | C2 gate |
| C5 | On-chain capacity | BLOCKED: no authorized archive endpoint | `docs/c2_ethereum_access.md` |
| C6 | Capacity → persistence inference | BLOCKED on C4/C5 | — |
| M | Manuscript | SKELETON + related work (16 verified bib entries) + generated registry table + 3 generated figures (timeline, coverage heatmap, anchor D vs W); numbers generated from reports; PDF build unverified (no TeX installed) | `paper/` |

## Event coverage (from `configs/event_registry.json`)

- ACCEPTED: 1 cluster (CL-2023-03-SVB, anchor). The **multi-event criterion is not met**.
- SOURCE_DOCUMENTED primaries with listed free public minute data: UST 2022, TUSD 2024 (OOS), FDUSD 2025 (OOS), USDe 2025 (OOS), BUSD 2023 (placebo).
- SOURCE_DOCUMENTED primaries without identified data: DAI 2020, USDD 2022, USDT FTX 2022 (needs USD venue), USDT June 2023 (expected negative).
- UNRESOLVED: USDe 2024 (no evidence), USR 2026, MIM 2026 (weak sources).

## Authorization state

| Item | State |
|---|---|
| Paid data / accounts / credentials / provider contact | NOT authorized |
| Downloading free public data files (Binance data.binance.vision, Binance.US, Coinbase/Kraken public candles) | NOT YET authorized; requested in E1 |
| Historical capacity estimation | FORBIDDEN until execution-state data validated **and** separately authorized |
| Continuity standard for L2 (PROVIDER_NORMALIZED vs NATIVE_SEQUENCE) | open user decision; current default PROVIDER_NORMALIZED |

## Pre-analysis plan

Frozen 2026-10-11 (`docs/PRE_ANALYSIS_PLAN.md`, SHA-256 pinned in `configs/plan_freeze.json`). Amendments go only in `docs/PRE_ANALYSIS_AMENDMENTS.md`. The anchor is exploratory. Newly measured events must carry `measurement.measured_utc` after the freeze.

## Outstanding scientific issues

0. Anchor finding to test across events: the peg dislocation (stablecoin/USD) is far more persistent than the within-venue triangle wedge (half-life about 20 h vs minutes). Fragmentation measures must keep these separate.

1. Binance.com series are USDT-quoted. Deviations measured on them are relative to USDT, and USDT/USD verification is needed per window (critical for 2022 clusters).
2. Cross-event comparability. Venue, quote basis and data type differ across events, and this must be reported per event, not pooled blindly.
3. Minute last-trade closes include bid-ask bounce. Persistence should use horizon-aggregated measures (C3 robustness).
4. The anchor control window (February 2023) is not covered by the IAQF panel.

## Prioritized next tasks


1. **Cross-event report builder:** read all per-event protocol reports, apply the plan's decision rules (H1 Holm counts, placebo check, OOS replication, H2 sign count, mechanism-grouped random effects) and emit `reports/events/cross_event_summary.json` plus generated paper table; it must output 'insufficient events' honestly with the current single exploratory event.
2. **DV4/DV5 in the runner** (triangle wedge contrast and half-life ratio) where triangle legs exist.
2. **Capacity extensions (offline):** multi-range v3 tick crossing; two-venue transfer-delay bound.
3. **Ethereum:** extend the contract registry with event-specific deployments (Curve UST-3CRV for 2022; 3pool for June 2023; USDe pools for 2025). Source documentation only.

## Iteration log

| # | Time (ET) | Branch @ commit | Work | Tests |
|---|---|---|---|---|
| 0 | 2026-10-11 03:50 | c2 @ 8610d57 | C2 source gate | 53 passed |
| 1 | 04:20 | c3 @ 0e8f2df | C3 module + anchor report | 62 passed |
| 2 | 04:40 | c3 @ 331ea9a | C3 robustness (horizons, bootstrap diffs, Coinbase leg) | 66 passed |
| 3 | 05:10 | e1 @ 8a57c31 | E1 registry, rules, coverage matrix, anchor R1 | 82 passed |
| 4 | 05:00 | e1 @ eadccd7 | Binance kline adapter + manifest; pin numpy<2.5 (pandas 2.3 deprecation); reports regenerated byte-identical | 89 passed, -W error::DeprecationWarning clean |
| 5 | 05:25 | e1 @ ef2e29d | Event protocol runner; anchor protocol report | 95 passed |
| 6 | 05:55 | m1 @ 96b9a4d | Manuscript skeleton, generated number macros, verified bibliography, consistency tests | 99 passed |
| 7 | 06:20 | c4 @ a6af6f8 | Offline capacity method on synthetic books | 110 passed |
| 8 | 06:45 | c4 @ 9924197 | Reverse loop; Curve StableSwap + Uniswap v2 integer math (synthetic) | 118 passed |
| 9 | 07:10 | m2 @ dac411f | Related work with 7 newly verified references; generated registry table; paper tests extended | 119 passed |
| 10 | 07:35 | c4b @ 15459bf | Uniswap v3 single-range swap; DST-aware redemption window | 125 passed |
| 11 | 08:20 | m3 @ d4af74b | Deterministic figures (timeline, coverage heatmap, anchor D vs W) wired into the paper; matplotlib dependency | 130 passed |
| 12 | 08:50 | p1 @ c94425c | Frozen pre-analysis plan + hash test + amendments log; DL random effects, Holm, sign test | 137 passed |
| 13 | 09:25 | p1 @ (this commit) | Plan DVs (DV1 bootstrap test, DV3 trailing recovery, gates, covariates) in runner; amendment A1 (DV3 window clipped at extreme); anchor re-run EXPLORATORY | 144 passed |
