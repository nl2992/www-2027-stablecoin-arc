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
