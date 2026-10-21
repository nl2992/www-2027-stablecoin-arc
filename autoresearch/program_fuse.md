# autoresearch round 2: FUSE (fused USD price against a held-out exchange)

This round has the same shape as `program_unit_td.md`: a fixed harness, one editable file, a dev score, keep or discard through git, and a locked test run once. Written 2026-10-21, before any FUSE result was computed.

## Task

For each hour, fuse the "USD" prices that several exchanges quote for the same asset into one U.S.-dollar price. The fused price is scored against **Kraken**. Kraken never enters fusion, the features or the weights, and its BTC gap against Bitstamp stayed small throughout 2018–19 (`reports/unit_td/anchor_external.json`).

- **Sources:** Bitfinex, Coinbase and Bitstamp in every episode, plus Binance.US where it has BTC/USD (2022-10..2023-07).
- **Fused targets:** BTC/USD and ETH/USD. Binance.US contributes BTC only.
- **Side information** a method may use, all from non-Kraken sources:
  - the hourly altcoin prices on Bitfinex, Coinbase and Bitstamp;
  - USDT/USD on Bitfinex (from 2018-11), on Bitstamp (from 2022-04) and on Binance.US;
  - volumes.
- **Price convention:** the last traded close in each hour, built from minute data. This matches the hourly candles.

## Episodes

The split is fixed now. The loop sees only the dev episodes.

| Split | Episode | Window (UTC) | What happened |
|---|---|---|---|
| dev | D1 Bitfinex wires | 2017-03-01 .. 2017-08-31 | Bitfinex's dollar dislocated |
| dev | D2 calm 2020 | 2020-01-01 .. 2020-12-31 | Includes the March 2020 crash |
| dev | D3 calm 2021 | 2021-01-01 .. 2021-12-31 | Calm |
| **test** | T1 Bitfinex fiat | 2018-10-01 .. 2019-05-31 | Bitfinex's dollar dislocated (the anchor-confirmed episode) |
| **test** | T2 Binance.US | 2023-05-01 .. 2023-07-31 | Binance.US's dollar dislocated; four sources |
| **test** | T3 FTX | 2022-11-01 .. 2022-11-30 | Market stress |
| **test** | T4 SVB/USDC | 2023-03-08 .. 2023-03-20 | Stablecoin stress; banks lost |
| **test** | T5 calm | 2022 and 2023, outside T2–T4 | Calm |

## Score

- **Episode error:** for each episode, the mean absolute error in bps of the fused log price minus Kraken's, pooled over BTC and ETH hours where both exist.
- **Relative error:** `rel_e` = the method's error ÷ the error of the plain cross-source median.
- **`dev_score`** = the mean of `rel_e` over D1–D3. Lower is better; the median scores 1.
- **Calm constraint:** `rel_e` must be at most 1.02 on D2 and D3, so a method may not buy stress gains with calm losses.
- **Also reported per episode:** p95 error, and hours with error ≥ 25 and ≥ 50 bps.

## Baselines

The baselines are fixed in the harness and not editable:
- median;
- volume-weighted mean;
- trimmed mean;
- drop-the-most-deviant-source;
- CRH (Li et al. 2014);
- GTM (Zhao & Han 2012);
- the frozen unit-aware fuser from `src/www_auto/td_realdata.py`;
- an **oracle** that uses only Coinbase and Bitstamp, i.e. it knows which exchanges are clean. The oracle is a reference point, not a method.

## Rules for the fuser (`src/www_fuse/fuser.py`, the only editable file)

- **Causal:** the output for hour t uses rows at or before t only.
- **Venue-agnostic:** keys are anonymised, so no names. It may not identify Kraken and never sees it.
- **Pure numpy/pandas** with static checks: no I/O, no dates, no venue names.
- **Keep** a change only if every check passes, the calm constraint holds, and `dev_score` falls by at least 0.005. On equal scores, keep the simpler code.
- **Budget:** 25 iterations or 3 hours.
- **Locked test:** run once by the author session after code review. It reports every baseline and the fuser on T1–T5.

## Ideas worth trying (for the loop)

- Unit offsets from many items at once, with robust numeraire selection (the majority-unit cluster).
- Using anchors (USDT/USD legs) when they exist.
- State-space smoothing of the offsets with asset-specific noise.
- Down-weighting sources whose cross-item unit evidence is strong, instead of correcting them.
- Hybrids that correct when the unit evidence is strong and fall back to the median otherwise.
- Reliability from trailing agreement *after* unit removal.
