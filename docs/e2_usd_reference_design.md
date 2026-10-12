# E2 — USD reference leg for USDT-quoted events (design; no data requested)

**Checked:** 2026-10-11, from public documentation and public market-list metadata only. No candle data was requested.

## Why it is needed

Binance.com archives quote every stablecoin in USDT. Under the frozen plan (section 5) and the batch status rules, a USDT-relative series can never make an event `ACCEPTED`. A USDT/USD series on a USD venue, aligned on the UTC minute grid, is required. It is used for two things: (i) converting the stablecoin's price to USD, and (ii) the plan's USDT-stability gate (median \|USDT/USD dev\| < 10 bps in the window).

## Candidate sources

| Source | Access | USDT/USD | Granularity / history | Status for this project |
|---|---|---|---|---|
| **Binance.US historical market data** ([announcement](https://support.binance.us/en/articles/9843310-introducing-historical-market-data-from-binance-us-download-for-free), page `binance.us/institutions/market-history`) | Free `.zip` download or programmatic access; no account mentioned | `USDTUSD` (Binance.US pair; also present in the anchor panel) | Candlesticks, trades and aggregate trades "dating back to September 2019" for all pairs; interval list not stated in the announcement | **Primary.** It is the same venue family as the anchor. The archive layout and terms of use must be checked on the first file. Download permission needed. |
| **Bitstamp public OHLC** ([API docs](https://www.bitstamp.net/api/)), `GET /api/v2/ohlc/{pair}/` | Unauthenticated; `step` ≥ 60 s; up to 1,000 bars per request | `usdtusd` and `usdcusd` listed as *Enabled* in `trading-pairs-info` (checked 2026-10-11) | 1-minute bars; **how far back the pair goes is not verified** | **Secondary**, for a cross-venue robustness check. It needs paging (about 44 requests per month of 1-minute bars). Permission needed. |
| **Kraken downloadable OHLCVT** ([support article](https://support.kraken.com/hc/en-us/articles/360047124832-Downloadable-historical-OHLCVT-Open-High-Low-Close-Volume-Trades-data)) | Downloadable ZIP of CSVs | Per-pair files, "from the beginning of each market" | 1, 5, 15, 30, 60, 240, 720 and 1,440-minute files; only intervals with trades are included | **Tertiary.** It is a full-history bundle (large). Terms not reviewed. Permission needed. |
| Kraken REST `/public/OHLC` ([docs](https://docs.kraken.com/api/docs/rest-api/get-ohlc-data/)) | Public | — | "Returns up to 720 of the most recent entries" | **Unusable** for historical windows. |
| Coinbase Exchange candles ([docs](https://docs.cdp.coinbase.com/exchange/reference/exchangerestapi_getproductcandles)) | The current reference page documents API-key authentication headers | — | 300 candles per request | **Excluded** under the no-credentials rule. |

## Integration (implemented and tested)

A run spec may carry `quote_usd_source = {"venue", "path", "symbol"}`. `runner.run_from_spec` loads that archive separately, checks its checksums, puts it on the same UTC minute grid, and uses it as the USD leg. A minute counts as traded only if both legs traded. The batch driver skips the event, with the reason recorded, if the reference archive is absent. `tests/test_batch.py` shows a synthetic USDT-quoted depeg moving from `DATA_VERIFIED` (no USD leg) to `ACCEPTED` (with a Binance.US-style `USDTUSD` leg).

**Open check on first acquisition.** The adapter assumes Binance.US archives use the Binance.com kline CSV layout (12 columns, ms/µs timestamps) with `.CHECKSUM` files. This is **not verified**. The parser rejects any other layout loudly instead of guessing.

## Decision requested

Authorize downloading Binance.US `USDTUSD` 1-minute history for the event months: 2022-04/05, 2023-01/02, 2023-12/2024-01, 2025-03/04 and 2025-09/10, which also covers the control windows. Optionally also authorize Bitstamp `usdtusd` for the same windows as a robustness venue.
