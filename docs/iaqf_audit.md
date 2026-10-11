# IAQF construction audit

Audited checkout: `/Users/nigelli/Desktop/Academic/Columbia MAFN/20_Competitions/IAQF/IAQF-2026-Submission`, clean `main`, SHA `b484e8bc75429e293c87f10a8856a5ce196b9df8`.

## Artifact and construction

`generate_data.py` fetches Binance.US one-minute klines and Coinbase one-minute candles and merges them onto timestamps drawn from Binance.US BTCUSD and BTCUSDT. It derives range midpoints, raw log price differences, OHLC range proxies, volume shares, and regime labels. The stored `panel_1min.parquet` is 30,240 × 74, not the 126 columns claimed in the script header. `harmonized_raw_1min.parquet` is cell-for-cell equal to that panel. Upstream raw pulls are absent, so this audit cannot establish row-level API provenance or exact refetch equivalence.

The separate `scripts/03_harmonize.py` pipeline forward-fills some price columns for at most five minutes and then replaces missing volume with zero; its named output is absent. `scripts/04_compute_features.py` consumes `harmonized_raw_1min.parquet` but represents another feature pipeline; its output is also absent. These paths are not interchangeable. For the artifact actually present, `generate_data.py` is the closest reproducible construction, subject to raw input absence.

`scripts/06_download_l2_tick.py` downloads Binance.com BTCUSDT/BTCBUSD aggregate trades and one-second candles. `scripts/07_process_l2_metrics.py` estimates trade flow and derives `spread_hl` and `depth_proxy = 1 / rel_spread_hl` from candle ranges. These are trade/range-based proxies, not historical order-book ladders. L2 labels must not be treated as evidence of executable depth.

## Panel checks

Observed panel: 30,240 rows, UTC minute timestamps over the full stated interval, no duplicate timestamps and no missing minute. The artifact has 74 columns. Binance.US close coverage is full for inspected series, though zero-volume minutes are common; Coinbase BTCUSD has 29,950 closes (99.04%) and BTCUSDT 24,478 (80.95%). The audit JSON preserves detailed per-series coverage, zero-volume counts, and SHA-256. Close presence during zero volume does not prove a fresh executable quote; quote staleness cannot be inferred from candle rows.

The existing `lop_bnus_usdc_vs_usd` is `log(BTC/USDC) - log(BTC/USD)` in bps; it omits contemporaneous USDC/USD. It is a raw cross-quote difference, not the FX-corrected wedge. Candle high-low ranges are not quoted spreads. Capacity, slippage, and net profitability cannot be inferred from this panel.
