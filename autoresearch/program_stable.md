# autoresearch round 3: STABLE (fusing stablecoin-quoted feeds into U.S. dollars)

Pre-registered 2026-10-21, before any round-3 data was downloaded or any STABLE result was computed. The shape is the same as rounds 1 and 2: a fixed harness, one editable file, a dev score, keep or discard through git, and one locked test.

## Why this task

Round 2 showed that with three or more USD exchanges, a plain median already absorbs one broken exchange dollar. Real aggregators face a harder case. Most BTC volume is quoted in stablecoins (USDT, BUSD, TUSD, FDUSD, UST, USDC), and several markets share one stablecoin unit. When that unit depegs, a large group of sources moves together, which is exactly where median, volume weighting and reliability weighting are biased.

## Task

Each hour, produce the BTC price in U.S. dollars from every market that quotes BTC, scored against **Kraken BTC/USD**. Kraken never enters fusion.

- **Sources** are markets, i.e. (exchange, quote unit):
  - Binance BTC/USDT, BTC/BUSD, BTC/TUSD, BTC/FDUSD, BTC/UST and BTC/USDC, when listed and held;
  - Binance.US BTC/USD and BTC/USDT;
  - Bitstamp BTC/USD, BTC/USDT and BTC/USDC;
  - Coinbase and Bitfinex BTC/USD, to 2023-12.
- **Side information,** never Kraken:
  - ETH quoted in the same units;
  - stablecoin cross-rates on Binance (TUSDUSDT, FDUSDUSDT, BUSDUSDT, USTUSDT);
  - stablecoin/USD rates on Binance.US (USDT, USDC, TUSD) and Bitstamp (USDT, USDC);
  - volumes.
- The fuser receives each source's quote unit as an anonymised label, so it knows which sources share a unit but not which coin the unit is. It also gets anonymised exchange labels.
- **Price convention:** the last traded close in each hour, from minute data.

## Episodes

These are fixed now. The loop sees dev episodes only.

| Split | Episode | Window (UTC) | What happened |
|---|---|---|---|
| dev | S1 UST collapse | 2022-05-01 .. 2022-05-31 | Quote unit goes to zero |
| dev | S2 FTX | 2022-11-01 .. 2022-11-30 | USDT stress; one exchange collapses |
| dev | S3 BUSD halt | 2023-02-01 .. 2023-02-28 | Placebo: BUSD held its peg |
| **test** | X1 USDC run | 2023-03-08 .. 2023-03-20 | USDC depeg (needs the BTC/USDC markets) |
| **test** | X2 TUSD | 2024-01-01 .. 2024-01-31 | TUSD depeg |
| **test** | X3 FDUSD | 2025-04-01 .. 2025-04-30 | FDUSD depeg |
| **test** | X4 calm | 2023-12 and 2025-02..03 | No event |

Each call gets a 30-day warm-up before the window. Only the window is scored.

**Prior knowledge (disclosed):** the earlier stablecoin event study (`reports/events/*_protocol.json`) measured the depeg sizes of USDC, TUSD and FDUSD. No fusion method has been run on any of these windows.

## Score

- `rel_e`: per episode, the mean absolute error (bps) of the fused BTC/USD against Kraken, divided by the error of **B0, the naive aggregator**: the median of all markets with every stablecoin treated as exactly 1 USD.
- `dev_score`: the mean of `rel_e` over S1–S3. Lower is better.
- **Placebo constraint:** on S3, `rel_e` ≤ 1.02.
- **Also reported:** p95 error, and hours with error ≥ 25 and ≥ 50 bps.

## Baselines (fixed)

- **B0** naive median, stablecoins = 1 USD.
- **B1** naive volume-weighted mean, stablecoins = 1 USD. Volume-weighting is how most aggregators weight markets.
- **B2** conversion: each stablecoin price is converted at its stablecoin/USD rate from USD markets where one is available (chained through USDT/USD where needed; Kraken never used), then median. This is the CoinGecko-style USD on-ramp.
- **B3** CRH over all markets, stablecoins = 1 USD.
- **B4** the round-2 fuser, frozen at `914b3cb`.
- **Oracle:** the median of the USD-quoted markets only, i.e. it knows which units are dollars. This is a reference point, not a method.

## Rules for the fuser (`src/www_stable/fuser.py`, the only editable file)

These are the same as round 2:
- causal;
- anonymised exchange and unit labels;
- no I/O, dates, coin names or exchange names;
- numpy and pandas only.

**Keep** a change only if every check passes, the placebo constraint holds, and `dev_score` falls by at least 0.005. **Budget:** 25 iterations or 3 hours. **Locked test:** run once by the author session after code review.

**Claim to test:** the fuser beats B0, B1, B2 and B3 on the test episodes, and comes within about 5% of the oracle.
