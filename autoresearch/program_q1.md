# Q1: frozen stablecoin fuser on untouched majority-unit events (pre-registration)

Written 2026-10-22, before any Q1 event data was downloaded and before any Q1 error was computed. Nothing here is tuned.

## Question

Does the round-3 fuser beat the median and the commercial conversion baseline where a median structurally cannot work? That is the case where most BTC volume is quoted in one stablecoin whose value has moved by more than venue noise.

## Frozen objects

- **Fuser:** `src/www_stable/fuser.py` at commit `ca38772`, copied byte-for-byte into `src/www_q1/frozen_fuser_ca38772.py` (verified with `git show`) and never edited.
- **Baselines:** B0, B1, B2, B3 and B4, and the oracle, all exactly as in `autoresearch/program_stable.md` / `src/www_stable/baselines.py`.
- **Truth:** Kraken BTC/USD, never passed to any method.
- **Rules carried over from round 3:** the panel conventions (hourly last-traded close, a 30-day warm-up, anonymised market, unit and venue labels).

## Candidate events

None of these was used in rounds 1–3 as a stablecoin-market fusion episode.

| ID | Window (UTC) | Shifted unit | Why |
|---|---|---|---|
| Q-E1 | 2018-10-08 .. 2018-10-31 | USDT | October 2018 USDT depeg |
| Q-E2 | 2018-11-27 .. 2018-12-31 | USDT | Continued USDT discount; Bitfinex USDT/USD starts 2018-11-27 |
| Q-E3 | 2019-04-20 .. 2019-05-31 | USDT | USDT premium around the NYAG filing |
| Q-E4 | 2020-03-09 .. 2020-03-31 | USDT | COVID crash USDT premium |
| Q-E5 | 2022-09-05 .. 2022-10-05 | BUSD | Binance stablecoin auto-conversion |

## Feasibility gate

The gate uses only volumes and stablecoin/USD rates, never a fusion error, and never Kraken.

- **Volume share:** the share of BTC volume quoted in the shifted unit, from all held markets.
- **Unit offset:** the stablecoin's deviation from the U.S. dollar, from a non-Kraken source:
  - Binance.US USDT/USD (from 2019-09) or Bitstamp USDT/USD (from 2022-04), where they exist;
  - otherwise, the Bitfinex netted anchor T = D − L, i.e. Bitfinex's USDT/USD minus Bitfinex's BTC gap against Bitstamp, which removes Bitfinex's own dollar.
  - If none of these exists, the event fails the gate.
- **The stratum S_hi:** hours with volume share ≥ 0.5 and |offset| ≥ 25 bps.
- **Event rule:** keep an event only if it has ≥ 40 S_hi hours.
- **Study rule:** proceed only if ≥ 200 S_hi hours are pooled over ≥ 3 events. (The idea scan suggested ≥ 4 events; with five candidates, 3 is the minimum that still spans more than one stablecoin regime. This is fixed here, before any data.)
- **If the study falls short:** report a descriptive gate result and stop.

## Endpoints

- **Primary:** the mean over S_hi hours of log(|e_fuser| + 1 bp) − log(|e_B0| + 1 bp), pooled over kept events, where e is the fused price minus Kraken in bps. The test is a day-block bootstrap with 1,000 draws and seed 20261022. **Success** means the upper 95% bound is below 0.
- **Co-primary:** the same statistic against B2 (conversion through a stablecoin/USD rate) and against B3 (CRH). Each succeeds if its upper bound is below 0. The headline claim "beats existing methods" needs all three.
- **Secondary (reported, not gating):**
  - per-event MAE ratios;
  - p95 error, and hours with error ≥ 25 and ≥ 50 bps;
  - the gap to the oracle;
  - a calm placebo, in which all hours of each kept event's 30 days before the window that are *not* in S_hi must have a fuser/B0 MAE ratio ≤ 1.02.

## Failure reading, stated now

If the primary or co-primary endpoints fail, the paper claims no algorithmic contribution for fusion. It keeps the scope condition: a median is adequate unless a majority shares the unit and the shift exceeds venue noise. There will be no further tuning round.

## Data needed (requires approval, D18)

**Binance public monthly 1-minute klines** (data.binance.vision):
- BTCUSDT and ETHUSDT for 2018-09..2018-12, 2019-03..2019-05 and 2020-02..2020-03;
- BTCUSDT, ETHUSDT, BTCBUSD and ETHBUSD for 2022-08..2022-10.

**Already held:** Coinbase, Bitstamp and Bitfinex minute data for 2017–2023; Binance.US USDT/USD from 2019-09; Bitfinex USDT/USD from 2018-11-27; Bitstamp USDT/USD from 2022-04; Kraken BTC/USD.
