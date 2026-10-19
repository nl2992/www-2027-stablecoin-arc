# Ledger-side multi-event panel: plan and predictions (2026-10-18)

**User request (2026-10-18):** do not rest the ledger side on one event.

## What was seen before writing this file

A feasibility probe used the free public APIs of Bitfinex (`api-pub.bitfinex.com/v2/candles`) and Bitstamp (`/api/v2/ohlc`). It read five daily BTC/USD closes per episode, printed to the terminal, and saved nothing to disk. PD_BTC = 1e4 log(P_Bitfinex / P_Bitstamp):

| Day | PD_BTC (bps) |
|---|---|
| 2017-04-24 | 704 |
| 2017-04-27 | 785 |
| 2018-10-15 | 456 |
| 2019-05-01 | 568 |
| 2019-05-03 | 615 |

Because these values were seen first, the sign predictions below are **not blind** for BTC on those days. The predictions that remain blind are the ones for the other assets (ETH, USDT), the triangle, the phase medians, the reversion, and the dates outside the probe.

## Candidate ledger episodes

| ID | Venue, fiat | Rail event (documented date) | Gate state | Data |
|---|---|---|---|---|
| L1 | Bitfinex, USD | Wells Fargo stops outgoing wires; Taiwanese banks refuse incoming wires from 2017-04-18 | exit impaired, entry impaired | Bitfinex API (BTC, ETH, ETH/BTC); reference Bitstamp BTC; Coinbase ETH |
| L2 | Bitfinex, USD | Fiat deposits suspended for some users, withdrawal delays, solvency rumours (Oct 2018) | exit impaired | Bitfinex (BTC, ETH, USDT from late 2018?) ; Bitstamp BTC, ETH |
| L3 | Bitfinex, USD | NYAG filing on Crypto Capital, 2019-04-25 | exit impaired | Bitfinex (BTC, ETH, USDT); Bitstamp BTC, ETH, USDT? |
| L4 | Binance.US, USD | banks withdraw, June 2023 (existing R2) | exit threatened, then entry closed with exit open | on hand |
| L5 | Binance.com, GBP | Paysafe, 2023-05-22 (existing R6) | both closed | on hand |
| L6 | Binance.com, EUR | Paysafe, 2023-09-25 (existing R6) | both closed for Paysafe users | on hand |
| L7 | Binance.US, USD | 7 to 9 May 2023, cause undocumented (found by the token screen) | unknown | on hand |
| L8+ | Mt. Gox 2014, FTX 2022, QuadrigaCX 2018-19, CNY venues 2017 | to be checked | | free source not yet identified |

Event dates and gate states must be confirmed against dated primary or press sources before any minute data are inspected, and fixed in code before phase statistics are computed (as for R2).

## Predictions, recorded before any minute data are downloaded

- **Q1 (identification).** In L1 to L3, PD_ETH agrees with PD_BTC: hourly correlation ≥ 0.9 and median gap ≤ 50 bps in the impaired phase. Where Bitfinex USDT/USD trades, its PD has the same sign.
- **Q2 (coherence).** The within-Bitfinex triangle (ETH/USD against ETH/BTC × BTC/USD) has |phase median| ≤ 10 bps.
- **Q3 (gate sign).** Where exit is impaired and entry is not fully closed with exit open, the platform dollar trades at a discount (PD > 0). Only L4's second phase predicts PD < 0.
- **Q4 (reversion).** PD returns to within 50 bps of its pre-event level once the rail is restored or the episode resolves; the restoration date is taken from a dated source.
- **Falsification.** PD_ETH and PD_BTC disagreeing (corr < 0.5, or opposite signs) counts against the ledger reading for that episode, and the episode is reported as such.

## Output

A panel table: one row per episode (L1 to L7, plus the token-side episodes SVB, TUSD, FDUSD and UST), each classified as token failure, ledger failure, both or neither by the same decomposition and checks.

## Results (2026-10-18; `reports/rescue/ledger_panel.json`, data manifest `reports/events/acquisition_manifest.json`)

The download covered 101 month files (Bitfinex, Bitstamp and Coinbase), all VERIFIED with self-recorded SHA-256. The phase boundaries in `src/www_rescue/ledger_panel.py` were fixed before any statistics were computed.

### Fixed-phase medians, PD_BTC against Bitstamp (bps, hour-block 95% CI)

| Episode | pre | stress phase(s) | later |
|---|---|---|---|
| 2017 wires | 4 [2, 5] | outbound blocked 80 [69, 88]; inbound refused 297 [272, 322] | −31 [−36, −26] |
| 2018 deposits paused | 15 [14, 17] | 229 [221, 243] | 283 [276, 289] |
| 2019 NYAG | 173 [166, 178] | 32 [25, 44] | 0 [−1, 1] |

### Scored predictions

| | 2017 | 2018 | 2019 |
|---|---|---|---|
| Q1 identification (as written) | **FAIL** | pass | pass |
| Q2 triangle ≤ 10 bps | pass (max 8) | pass | pass |
| Q3 discount sign in stress phases | pass | pass | pass |
| Q4 reversion within the window | pass | **FAIL** (discount persisted) | pass |
| Falsified | no | no | no |

**Why Q1 failed for 2017.** As written, Q1 compares PD_BTC against Bitstamp with PD_ETH against Coinbase. In 2017 the two references themselves differed by tens of bps, and by up to about 190 bps in some weeks. Against the same reference (Coinbase), BTC and ETH agree: hourly corr 0.975, median gap 7.2 bps. That comparison was computed after the scored result and is reported as descriptive. The pre-registered verdict stays FAIL.

### Descriptive path (computed after the scored results)

- **2017:** the discount builds from mid-April to a daily peak of 844 bps (2017-04-23). It flips to a **premium** from late May (daily minimum −592 bps, 2017-05-28) and is back near zero by late July. This is the same discount-then-premium sequence as Binance.US in 2023.
- **2018 to 2019:** one long discount. It starts in the week of 2018-10-07, peaks at 610 bps (2018-10-15), stays at 100 to 350 bps through December, is still about 260 bps in March 2019 and narrows to about 50 bps in mid-April. After the NYAG filing it jumps back to about 600 bps (peak 627 bps, 2019-05-02), then collapses to about zero within a week around 2019-05-10. January and February 2019 were not downloaded. The fixed 2019 phases split the episode in a way that hides this: the "pre" phase is itself impaired, and the NYAG phase mixes two weeks at 600 bps with three weeks near zero.
- **Gate hypothesis:** the 2018 case had deposits closed and withdrawals officially open, which is Binance.US's premium configuration, yet it shows a discount. NYAG later alleged serious withdrawal problems in late 2018. The simple gate story is therefore not confirmed, and the paper must say so.

### Independence

The 2018 and 2019 windows are probably one episode (one Bitfinex banking crisis, October 2018 to May 2019). Counted conservatively, the panel has **three independent ledger-failure episodes on two platforms**: Bitfinex 2017, Bitfinex 2018–19 and Binance.US 2023. It also has two small-effect fiat cases (Binance GBP and EUR) and one unresolved case (Binance.US, May 2023).
