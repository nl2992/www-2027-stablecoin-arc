# Current state: Phase 0 reconciliation (Implementation Specification v3)

**Audited:** 2026-10-11, 14:50 America/New_York.
**Workspace:** `WWW Paper`; origin `git@github.com:nl2992/www-2027-stablecoin-arc.git`.
**Branch / HEAD at audit start:** `p2/robustness` @ `e9a6780ead3dcbc89068760b540fd67aba809222`, clean working tree. PR #4 (`e4/bitstamp-usd-leg` → `c2/data-access-feasibility`) points at the same SHA.
**Since the last CoinAPI checkpoint** (`c48e714`, 2026-10-11 01:31 EDT): 31 commits on stacked branches (`c2` → `c3` → `e1` → `m1` → `c4` → `m2` → `c4b` → `m3` → `p1` → `c5` → `m4` → `c5b` → `r1` → `e3` → `e4` → `p2`).
**Tests:** `uv run pytest -q -W error::DeprecationWarning` collects and passes 175 tests, all offline.

Every statement below is classified by its evidence type: **executed** (a report produced from real data), **synthetic** (a code path tested only on constructed inputs), **documented** (an external source, nothing acquired), or **absent**.

## 1. Status register

| Component | Evidence | Status | Remaining work |
|---|---|---|---|
| Existing IAQF data ingestion | `panel_1min.parquet` SHA-256 `17704ff0…11b3`, IAQF repo `b484e8b` (clean); audit `reports/c0/panel_quality.json`; `docs/c0_review_packet.md` | **Verified (executed)** for the 2023-03-01..21 Binance.US/Coinbase one-minute candle panel | Upstream raw pulls are absent, so the panel cannot be regenerated from source. Candles are last trades, not quotes. The control window for the anchor (February 2023) is not covered. |
| Historical CEX data sources: candles | `reports/events/acquisition_manifest.json`: 77 archives, all `VERIFIED`. These are Binance.com (31, provider checksums), Binance.US (23, provider checksums) and Bitstamp (23, self-recorded hashes). All downloads were user-authorized; no paid source was used. | **Verified (executed)** for one-minute klines over the event months listed in `configs/acquisition_plan.json` | Binance's UST pair stops at 2022-05-13 00:49. There is no BTC/USDe market on Binance. A corrupt Bitstamp USDT/USD print at 2022-11-08 09:42 UTC is documented and not filtered. |
| Historical CEX data sources: L2 order books | `docs/c2_source_decision.md`, `reports/c2/source_decision.json`. CoinAPI is CONDITIONAL (REJECT under a native-sequence standard). Tardis crisis-day files are paid. The only L2 held locally is the Tardis public first-of-month sample BTCUSD 2023-03-01, SHA-256 `2061a9ff…8511`. | **Blocked** (paid access declined by the user) | No crisis-day L2 for any event. The free Tardis first-of-month files could supply normal-market L2 days, but they have not been acquired and need approval. |
| Order-book reconstruction | `src/www_c1/replay.py`; `reports/c1/march01_sample_validation.json` (7,264,627 rows replayed); `tests/test_c1_*` | **Partial (executed on one normal-market day)** | Native sequence continuity cannot be verified from normalized CSV. No crisis-day replay. Depth, VWAP and slippage metrics from replayed books have not been computed. |
| Historical DEX state | `reports/c2/contract_registry.json`: 8 entries, of which 7 are `SOURCE_DOCUMENTED`. The USDe/USDC pool is `UNVERIFIED` (aggregator listing only). `reports/c2/validation_plan.json` holds 4 pool/event items and records 0 network calls. | **Blocked (documented only)** | No archive RPC has been authorized, so no code hash, coin order, balance or `get_dy` has been read at any historical block. ABI signatures are `ASSUMED`. |
| ARC measurement | `src/www_capacity/orderbook.py` (book walk, cost-bounded K(δ), forward and reverse triangle restoration); `amm.py` (StableSwap, Uniswap v2, Uniswap v3 single range); `redemption.py`; `docs/c4_capacity_method.md`; tests with hand-computed fixtures | **Synthetic only.** Formulas and numerical fixtures exist; no historical ARC value has been computed (gated). | No gas, latency, transfer delay, shared-liquidity, inventory across venues, or multi-range v3 modelling. AMM math has not been validated against on-chain calls. The spec's two-quantity separation (standardized capacity vs observed net arbitrage) is not yet formally documented. |
| Multi-event coverage | `configs/event_registry.json` (16 entries, 13 clusters); rules R1–R4 in `src/www_events/registry.py`; `reports/events/coverage_matrix.json`; `reports/events/status_log.json` | **Verified (executed) at candle level.** Three accepted independent clusters: SVB 2023 (anchor, exploratory), TUSD 2024 and FDUSD 2025 (both out-of-sample). Rejected: BUSD placebo, FTX-USDT (Binance.US), June 2023 USDT (Bitstamp). Data-verified only: UST 2022, USDe 2025. | No accepted confirmatory **in-sample** event. No separate non-crisis control periods beyond the per-event matched 7-day controls. DAI 2020 and USDD 2022 have no free USD-venue data identified. |
| Statistical experiments | Frozen plan `docs/PRE_ANALYSIS_PLAN.md` (SHA pinned in `configs/plan_freeze.json`); amendments A1 (pre-data), A2 (post-data), A3 (pre-Bitstamp analysis); `reports/events/*_protocol.json`; `reports/events/cross_event_summary.json`; robustness (plan section 7) in each protocol | **Partial (executed, descriptive).** Per-event DV1–DV5 with block-bootstrap CIs; mechanical H1 and H2 decisions. H1 in-sample is `INSUFFICIENT_EVENTS`; out-of-sample 2/2 satisfy it; H2 is descriptive only (the placebo ratio is also above 1, and DV5 is unstable). | **None of the spec's Phase 5 baseline comparisons exist:** no AR/OU, duration/hazard, volume/liquidity or nonlinear benchmarks, no chronological prediction evaluation, and no calibration. The design is descriptive, not predictive. |
| Manuscript | `paper/main.tex` (ACM sigconf, labelled provisional); 16 verified references; generated numbers, tables and figures (`tests/test_paper.py`, `tests/test_figures.py`) | **Partial (provisional draft)** | The PDF build is unverified (no TeX installed). The capacity sections are `[PENDING]`. Spec v3 asks for the manuscript only after the core results pass review, and this draft predates that review, so it must be treated as provisional. |

## 2. Data inventory (spec Phase 0, item 7)

| Class | Items |
|---|---|
| **Stored** | IAQF panel; Tardis Binance.US BTCUSD L2 2023-03-01; 77 kline archives (per the manifest), git-ignored under `data/` |
| **Verifiably reconstructible** | Every protocol report from stored inputs via `REPRODUCE.md`. Within-venue triangles for SVB, TUSD, FDUSD, BUSD, FTX and June 2023. |
| **Offered by a provider, not acquired** | Tardis crisis-day L2 (paid); CoinAPI full-book flat files (usage-priced); Tardis free first-of-month L2 for other months (free, not approved); Kraken OHLCVT bundle |
| **Historical availability unknown** | Archive-node access with acceptable public terms; USDD and DAI-2020 minute data on a USD venue; Bitstamp `usdtusd` before 2022-04 |
| **Confirmed unavailable** | Binance BTC/USDe klines; Binance UST after 2022-05-13 00:49 (continuation exists only as USTC/BUSD); Kraken REST history beyond 720 bars; Coinbase candles without credentials |

## 3. Executed experiments and numerical findings (spec Phase 0, item 8)

All values below are read from committed reports.

| Experiment | Input | Report | Headline |
|---|---|---|---|
| C3 anchor wedge levels and persistence | IAQF panel | `reports/c3/fragmentation_persistence.json`, `robustness.json` | Median USDC wedge rose from 2.06 to 8.13 bps (crisis minus pre: +6.08, 95% CI 3.75–9.16) |
| Anchor protocol (exploratory) | IAQF panel | `reports/events/E2023-03-USDC-SVB_protocol.json` | DV1 +208 bps (CI 92–336, baseline reference); recovery about 68 h; DV5 about 95 |
| Multi-event protocols | Binance, Binance.US and Bitstamp archives | `reports/events/*_protocol.json`, `cross_event_results.md` | TUSD DV1 +113 bps (CI 100–121); FDUSD DV1 +45 bps (CI 34–51); triangle wedges unchanged in both; placebo DV1 −3 bps |
| Robustness (plan section 7) | same | `plan.robustness` in each protocol | R1 classification invariant at 50/100/200 bps; half-lives fragile |
| L2 replay | Tardis sample | `reports/c1/march01_sample_validation.json` | 7.26 M rows replayed; 1 exchange-timestamp regression; no crossed books |

**Not executed:** any ARC or capacity value on real data, any DEX state read, any CEX depth metric on a crisis day, and any baseline model comparison.

## 4. Reconciliation with earlier plans

- **C0–C2** are accepted (PRs #1–#3, open). C3–C5, E1–E4, P1–P2, M1–M4 and R1 are new since `c48e714` and are bundled in PR #4.
- **C6–C9 and G0–G4:** no planning documents with these labels exist in this repository. The only occurrence is "C6" in `docs/RESEARCH_STATE.md`, which marks capacity-to-persistence inference as blocked. Reconciliation against those plans requires the reviewer to supply them.
- **Spec v3 departures to review:**
  1. The design so far is a descriptive event study, not the spec's ARC-versus-baseline predictive framework (Phase 5).
  2. A provisional manuscript exists ahead of the spec's review gate.
  3. Normal-market periods appear only as per-event matched control windows.

## 5. Highest-information unfinished task

**Decide whether event-day execution state is obtainable without paid data.** Every ARC claim, and the spec's Phase 1 exit test ("if historical CEX depth is unavailable across events, reassess whether an on-chain-only contribution remains defensible"), depends on it. Paid L2 has been declined, so the only route is historical on-chain state. The task:

- **Required inputs:** a user-approved, free, unauthenticated Ethereum archive endpoint whose published terms permit research use (none is approved today).
- **Work:** execute the existing offline plan (`reports/c2/validation_plan.json`). That is 4 pool/event items and about 36 read-only calls: Curve 3pool at the SVB and June 2023 start blocks, and the UST(Wormhole)/3CRV and legacy UST pools at the May 2022 start block. Resolve blocks by timestamp.
- **Expected outputs:** block-pinned code hashes, coin order, decimals, A, fee, balances and `get_dy` quotes, with block hashes recorded.
- **Acceptance tests:**
  - the bytecode is non-empty at each block;
  - `coins(i)` matches the documented tokens;
  - the offline `stableswap_get_dy` reproduces the on-chain `get_dy` to within 1 raw unit at each block;
  - every call is read-only (dry-run validator passes).
- **Approvals needed:** (1) the endpoint, with its terms reviewed; (2) whether the paper may proceed on an on-chain-only capacity contribution if CEX depth stays unavailable.

**A cheaper parallel option (also needs approval):** download the free Tardis first-of-month L2 files for the event months. These are normal-market days, so they would add CEX depth for normal-market comparisons (spec Study E) and further replay validation, but no crisis-day depth.

## 6. Pre-registration recorded in this audit (no measurement)

The user agreed on 2026-10-11 to pre-register the UST series rule before any measurement. It is recorded as amendment **A4** in `docs/PRE_ANALYSIS_AMENDMENTS.md`. Acquiring and measuring the USTC/BUSD continuation waits until after independent review.

## 7. Bounded feasibility checkpoint (after reviewer decisions 2, 4 and 5)

| Check | Commands | Outcome | Evidence |
|---|---|---|---|
| UST A4 preconditions and run | `uv run python -m www_events.acquire`; `uv run python -m www_events.ust_splice` | All preconditions **pass**. Chronology: Binance removed UST pairs at 2022-05-13 00:40; UST/BUSD reopened at about 14:30 the same day; USTC/BUSD opened 2022-05-30 09:30. **The registered USTCBUSD splice covers 0 of 10,080 recovery-window minutes, so R3 still fails and UST stays DATA_VERIFIED.** This is a negative result for the rule as registered. | `reports/events/E2022-05-UST-COLLAPSE_a4_splice.json`; status log entry; archives USTBUSD, USTCBUSD and BUSDUSDT for 2022-05 in the manifest |
| Ethereum archive (free) | 5 read-only calls in total (see probe) | **Stopped.** NodeFlare public tier: `state at block #14000001 is pruned`. Other candidates excluded on terms, archive or account grounds. No historical pool state was reproduced. | `reports/c2/archive_probe.json` |
| Tardis free first-of-month L2 | `uv run python -m www_events.acquire`; `uv run python -m www_c1.depth --inputs data/raw/tardis/*.csv.gz` | 3 files (60 KB–3 MB). Replay is clean: 0 timestamp regressions, 0 crossed samples, 0 invalid rows. Median depth within ±10 bps: Binance.US USDC/USD about $0.57 M bid / $1.54 M ask; Binance TUSD/USDT about 1.66 M / 1.67 M USDT; Binance FDUSD/USDT about 62 M / 52 M USDT. Spreads are at one tick (about 1 bp). **Normal-market only.** | `reports/c1/normal_market_depth.json`; manifest records `tardis:*` |

The decision register, including the CEX–DEX versus on-chain-only scope split, is in `docs/status/DECISION_REGISTER.md`.
