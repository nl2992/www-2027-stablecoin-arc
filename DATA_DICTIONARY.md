# Data dictionary (upstream IAQF minute panel)

Source: `panel_1min.parquet` at IAQF SHA `b484e8bc75429e293c87f10a8856a5ce196b9df8`; 30,240 rows from 2023-03-01 00:00 UTC to 2023-03-21 23:59 UTC, on a one-minute grid.

| Column group | Columns | Meaning / caveat |
|---|---|---|
| Time | `timestamp_utc`, `hour_utc` | UTC minute label and UTC hour |
| Binance.US candles | `bnus_{btcusdt,btcusdc,btcusd,btcbusd,usdtusd,usdcusd,usdcusdt,busdusdt}_{open,high,low,close,volume}` | OHLC and base-asset volume; close may remain present during zero volume and is not necessarily a fresh quote |
| Coinbase candles | `cb_{btcusd,btcusdt}_{low,high,open,close,volume}` | Coinbase one-minute candles; BTC-USDC is absent in the March 2023 panel |
| Range-derived mid proxies | `mid_bnus_{btcusdt,btcusdc,btcusd,usdtusd,usdcusd}` | `(high + low)/2`; not the exchange bid/ask midpoint |
| Raw LOP | `lop_bnus_{usdt,usdc}_vs_usd` | `10,000 × (log(BTC/stable close) - log(BTC/USD close))`; unadjusted for stablecoin/USD parity |
| Stablecoin deviation | `log_{usdc,usdt}_usd_dev` | `10,000 × log(stablecoin/USD close)` |
| Range proxy | `spread_bnus_{btcusdt,btcusdc,btcusd}`, corresponding `rel_spread_*` | High-low range and range/close; neither is a quoted spread |
| Activity/volatility | `rv60_bnus_btcusd`, `vol_share_{usdt,usdc,usd,busd}_bnus` | Rolling return volatility and volume shares; inspect `generate_data.py` for exact window/scaling |
| Regime | `regime`, `regime_num` | Calendar labels, not estimated states |

## Corrected parity wedge

For price `P(BTC/q)` in quote tokens per BTC, stablecoin value `S(q/USD)` in dollars per token, and dollar BTC price `P(BTC/USD)`, use `10,000 × [log(P(BTC/q)) + log(S(q/USD)) − log(P(BTC/USD))]`. The upstream USDC LOP omits `S(q/USD)`, so it is not FX-corrected. The C0 utility implements the corrected formula, but same-minute closes remain candle proxies rather than executable synchronized quotes.
