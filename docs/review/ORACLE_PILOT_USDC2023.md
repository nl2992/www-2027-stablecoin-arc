# Oracle audit pilot: what the web served during the USDC depeg (March 2023)

Authorization: D13 (`docs/status/DECISION_REGISTER.md`). One episode, one oracle family. Code: `src/www_audit/pilot.py`; numbers: `reports/audit/usdc_2023_pilot.json`; raw data: `data/raw/audit/` (git-ignored).

## Verdict

- **Contamination of BTC/USD and ETH/USD by the USDC unit: not found.** Across the 78 hourly samples of the core depeg window (2023-03-10 12:00 to 03-13 18:00 UTC), the Chainlink BTC/USD error against our BTC reference regresses on the USDC depeg size with slope **0.007** (R2 0.02; ETH: 0.007, R2 0.03). Contamination would give a slope near 1. In the 46 hours when USDC was at least 100 bps below $1 (median 425 bps, peak 1,477 bps on Bitstamp), the median BTC error was **-5 bps** and the median ETH error **-3 bps**, not +425. The result is the same with the Binance.US-minus-L USDC series (slope 0.009 for both) and in first differences (slope 0.006 and -0.004).
- **Materiality: negligible for BTC, ETH and USDT; large but short and partly a reference artefact for USDC itself.** BTC/ETH hourly errors stayed under 55 bps in the depeg core (one hour at or above 50 bps each, none at or above 100), the same order as in the calm control (medians about 8 bps in both). The USDC/USD feed itself did diverge from our single-venue references by at least 100 bps in 7 of 212 hours (each reference), with a longest run at or above 100 bps of 150 minutes (Bitstamp reference) or 89 minutes (Binance.US minus L). The sign changes (feed below the reference at 03:59 on 03-11, above it at 06:59 to 10:59), and the references disagree with each other by a median 20 bps and a p95 of 285 bps in the same window, so this is mostly measurement noise and feed-versus-venue dispersion, not a stablecoin-unit finding.
- **What the unit lens adds here: a clean negative.** The USD feeds for BTC and ETH did not inherit the USDC unit during this episode. It does not show a benefit of unit correction for these feeds. The one use of the unit-corrected reference was to rule contamination out, and the ledger offset L was small (median -1.6 bps in the depeg window), so the correction itself barely mattered.

## What worked, what did not

| Source | Status |
|---|---|
| Chainlink on Ethereum (5 feeds) | Worked, via archive `eth_call` only. The RPC plan's free tier caps `eth_getLogs` at a 10-block range, so `AnswerUpdated` logs could not be pulled over a multi-day window within the 1,500-call budget. Rounds were read with `getRoundData(roundId)` instead (answer, startedAt, updatedAt, roundId). **Block number and tx hash per round were not recorded.** The log decoder is implemented and tested against a fixture. |
| Pyth Benchmarks | **Requires account.** The `/v1/shims/tradingview/*` paths return HTTP 404 (also `symbols`, `search`, `config`). `/v1/price_feeds` works and confirms the feed ids (BTC, ETH, USDC, USDT /USD), but `/v1/updates/price/{ts}` returns HTTP 401 "unauthorized". Stopped; no account created. |
| CryptoCompare histohour | **Requires account.** HTTP 401, "API key required" (now served by CoinDesk). Stopped; no account created. |

So the audit covers one published feed family. It is not a cross-provider comparison.

## Chainlink feeds verified on-chain

All five proxies matched the expected `description()` and returned `decimals() = 8`: USDC/USD `0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6`, USDT/USD `0x3E7d1eAB13ad0104d2750B8863b489D65364e32D`, DAI/USD `0xAed0c38402a5d19df6E4c03F4E2DceD6e29c1ee9`, BTC/USD `0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c`, ETH/USD `0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419`. Each proxy pointed to a single aggregator (phase) across both windows, so every pulled round is contiguous.

Deviation threshold and heartbeat: **not taken from documentation** (no documented source retrieved in this pilot). Inferred from the observed rounds: USDC/USD and USDT/USD update on moves of about 25 bps (smallest deviation-triggered move 25.0 to 25.1 bps) with a heartbeat of about 24 h (largest gap 1,440 to 1,441 min); BTC/USD and ETH/USD have a 60 min heartbeat (largest gap 61 min) and update on very small moves (5th percentile of deviation-triggered moves 0.7 to 6.7 bps), so no clean percentage threshold can be read off the data. DAI/USD was pulled only for a 5 h slice, too short to infer a policy.

## Reference (unit-corrected USD)

- USDC: Bitstamp USDC/USD (traded minutes, forward-filled up to 60 min). Cross-check: Binance.US USDC/USD minus the ledger-dollar offset L (Binance.US vs Bitstamp BTC/USD, 30-minute rolling median). L was small: median -1.6 bps (5th to 95th percentile -18 to +1.5) in the depeg window, -1.1 bps in the calm window.
- Agreement of the two USDC references on 2,416 common traded minutes in the depeg window: median difference +0.3 bps, median absolute difference 19.7 bps, p95 285 bps, level correlation 0.91. Minimum price: Bitstamp 0.810 (a thin print at 07:17 on 03-11), Binance.US minus L 0.864 (raw Binance.US 0.863), Chainlink 0.880 (07:51). In the calm window the Binance.US-based series sits 6.8 bps above Bitstamp.
- BTC and ETH: median of Bitstamp and Coinbase (the mean of two). Their disagreement is small: absolute gap median 2.2 bps, p95 12.9 bps, max 67 bps for BTC in the depeg window (ETH 2.7, 13.2, 110 bps), against 1.4 and 1.8 bps median in the calm window.
- USDT: Bitstamp USDT/USD. DAI: Binance.US DAI/USD minus L (thin; 30% of depeg-window minutes empty).

## Results

Errors are 1e4 times the log difference between the feed (last round published at or before the bar close) and the reference bar close; positive means the feed read above the reference. Hourly = the sample at each hour end. Windows: full depeg 2023-03-08 to 03-17 for USDC and USDT; "depeg core" is 2023-03-10 12:00 to 03-13 18:00 UTC (BTC, ETH, and USDC/USDT again for a like-for-like row); calm is 2023-02-20 to 03-01 for USDC and USDT and 2023-02-20 to 02-23 for BTC and ETH. The DAI row is a 5 h slice (2023-03-11 06:00 to 11:00). The budget did not allow BTC, ETH and DAI over the full windows.

| Feed | Window | Hours | Median abs bps | P95 abs bps | Max bps (signed) | Hours >=50 | Hours >=100 | Longest run >=50 / >=100 (min) | Per-round abs: median / p95 / max | Lag (min) | Updates | Stale (>50 bps moved): minutes / median age / max age (min) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| USDC/USD | depeg | 212 | 3.6 | 70.8 | -526 | 16 | 7 | 243 / 150 | 66.6 / 526.6 / 745 | 1 | 354 | 426 / 8 / 698 |
| USDC/USD | depeg core | 78 | 9.7 | 241.6 | -526 | 16 | 7 | 243 / 150 | 70.5 / 528.2 / 745 | 1 | 348 | 352 / 6 / 179 |
| USDC/USD | calm | 189 | 6.1 | 18.3 | 23 | 0 | 0 | 0 / 0 | 4.6 / 15.1 / 18 | 54 | 9 | 0 / - / - |
| USDT/USD | depeg | 215 | 3.4 | 19.5 | 53 | 1 | 0 | 15 / 3 | 2.5 / 20.8 / 50 | 9 | 39 | 100 / 276 / 410 |
| USDT/USD | depeg core | 78 | 6.4 | 29.4 | 53 | 1 | 0 | 15 / 3 | 3.4 / 26.1 / 50 | 9 | 34 | 99 / 277 / 410 |
| USDT/USD | calm | 208 | 0.6 | 3.0 | -21 | 0 | 0 | 3 / 1 | 0.2 / 1.0 / -1 | 120 | 9 | 5 / 1086 / 1088 |
| BTC/USD | depeg core | 78 | 8.7 | 36.7 | -52 | 1 | 0 | 15 / 1 | 8.3 / 34.7 / -101 | 3 | 224 | 243 / 13 / 57 |
| BTC/USD | calm (3 d) | 72 | 7.6 | 19.9 | -37 | 0 | 0 | 2 / 0 | 2.1 / 11.9 / -26 | 5 | 131 | 60 / 22 / 58 |
| ETH/USD | depeg core | 78 | 7.6 | 32.8 | -54 | 1 | 0 | 8 / 2 | 6.7 / 39.1 / 78 | 2 | 221 | 205 / 12 / 55 |
| ETH/USD | calm (3 d) | 72 | 8.1 | 25.5 | -36 | 0 | 0 | 2 / 0 | 2.2 / 16.7 / -34 | 5 | 133 | 40 / 11 / 52 |
| DAI/USD | trough 5 h | 5 | 37.1 | 125.2 | 145 | 1 | 1 | 26 / 13 | 41.9 / 174.1 / 219 | 8 | 85 | 49 / 4 / 12 |

Notes on reading the table:

- **Lag** is the shift that minimises mean absolute error. It is only identified when the error is not flat: BTC and ETH lag the reference by 2 to 5 minutes (mean absolute error falls from about 19 to 17 bps in the depeg core); the USDC feed lags by 1 minute in the depeg and the shift is meaningless in the calm window (values of 54 and 120 minutes come from noise around a constant).
- **Staleness** is measured against single-venue minute prints, so for USDT (24 h heartbeat, 25 bps threshold) it counts minutes in which one venue moved more than the feed's own threshold without the aggregate moving; it overstates real staleness. For BTC and ETH the oldest quote at a >50 bps move was about 57 minutes, bounded by the heartbeat.
- **Update counts in the depeg core:** USDC/USD 348 (against 9 in 10 calm days), USDT/USD 34, BTC/USD 224, ETH/USD 221. USDC updated every 4 minutes at the median during the depeg, so the feed was not frozen.
- BTC and ETH worst minutes (not hours): BTC -198 bps, ETH -188 bps, both on the way down in volatile minutes, signed negative (feed below the reference), the opposite of the contamination sign.

## Contamination detail (core window, hourly)

| Feed | Slope on D (levels) | R2 | Slope (first differences) | Median error when D >= 100 bps | D median in those hours |
|---|---|---|---|---|---|
| BTC/USD | 0.007 | 0.02 | 0.006 | -5.1 bps | 425 bps |
| ETH/USD | 0.007 | 0.03 | -0.004 | -2.7 bps | 425 bps |
| USDT/USD (placebo) | 0.010 | 0.07 | 0.001 | +4.4 bps | 425 bps |
| USDC/USD (the feed itself) | 0.140 | 0.24 | 0.418 | +4.7 bps | 425 bps |

D = -1e4 log(Bitstamp USDC/USD), so D is positive when USDC is below $1. The USDC feed row is a sanity check that the test has power: the feed responds to the depeg (first-difference slope 0.42, that is it tracks about 40% of the one-hour change in a thin single-venue reference and leads or lags it), whereas BTC, ETH and USDT do not respond at all. The peak hour (03-11 07:00 to 08:00 UTC, D = 1,477 bps) shows BTC +25 bps and ETH +11 bps, against a USDC feed error of +236 bps; the next hour has BTC -17.5 and ETH -4.6.

## Caveats

- One episode, one oracle family, one reference stack. A null result here does not generalise to other oracle designs or to depegs where the major feeds sourced from the affected stablecoin.
- BTC, ETH and DAI cover sub-windows (see above). The depeg core excludes 03-08 to 03-10 12:00 and 03-13 18:00 to 03-17 for these feeds; the USDC feed's own error is reported on the full window as well.
- The USDC reference is thin and venue-specific; the two references differ by a median 20 bps in the depeg window. The feed's apparent errors of several hundred bps in single hours are not separable from reference error. The reference minimum (Bitstamp 0.810) is a single thin print.
- The `getRoundData` pull gives each round's `updatedAt`, which Chainlink sets to the transmission time; block numbers and tx hashes were not retrieved (free-tier `eth_getLogs` is capped at 10 blocks).
- Hourly sample counts are small (78 in the core); the regression standard errors quoted in the JSON are naive (no serial-correlation correction), so the slopes are indicative. Their size (0.007 against an expected 1) makes the conclusion robust to that.
- Pyth Benchmarks and CryptoCompare could not be read without an account, so the audit does not compare providers.
- RPC calls: 1,456 of 1,500, including 100 charged conservatively for an initial attempt that crashed on the `eth_getLogs` cap before its count was saved (about 70 real calls). The endpoint URL was never printed or written; only call counts are stored.

## Raw-data manifest

SHA-256 of the files in `data/raw/audit/` at analysis time (full hashes in the JSON):

| File | Bytes | SHA-256 (first 16) |
|---|---|---|
| chainlink_state.json | 273,956 | c1b902e07060092b |
| http_probes.json | 1,696 | 22677721cc5d5c28 |
| probe_cryptocompare_histohour_usdc.txt | 273 | e54a34359ebeb424 |
| probe_pyth_price_feeds_search.txt | 1,504 | 3abc21b8af9e0962 |
| probe_pyth_tradingview_shim_history.txt | 0 | e3b0c44298fc1c14 |
| probe_pyth_tradingview_shim_symbols.txt | 0 | e3b0c44298fc1c14 |
| probe_pyth_updates_price_historical.txt | 12 | e9d83f01c9aff03a |
| rpc_calls_used.json | 1,403 | 6be62e63dea23173 |

Re-run: `uv run python -m www_audit.pilot --stage analyze` (offline, uses the saved raw data and local candle files).
