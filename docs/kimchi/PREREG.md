# Pre-registration: Kimchi premium, common component and USDT/KRW anchor
Written 2026-10-22 and committed BEFORE any price download. Authorization: D17. Only API availability probes (market listing and
first-candle dates) were made beforehand; no price series were inspected. Windows are chosen from literature and news, not data.

## Data and definitions
- KRW prices: Upbit hourly candles (/v1/candles/minutes/60, UTC hour starts; close = last trade of the hour; no fill of empty
  hours) for KRW-BTC, KRW-ETH, KRW-XRP, KRW-BCH (primary set), KRW-ETC (robustness), 2017-10 to 2023-12.
- USD reference (existing data, 2017-2023): BTC and ETH from Coinbase (hourly median of traded-minute log closes, as probe.py);
  XRP and BCH from Bitstamp 1h files (hour close); ETC from Coinbase 1h (from its listing, mid 2018). Mixed conventions are a
  caveat; statistics are on daily medians to damp them.
- FX: FRED DEXKOUS (KRW per USD, H.10 noon New York buying rate), forward-filled over weekends/holidays (days with NA). Timing
  caveat: noon New York is about 16-17 UTC, so the FX is stale for the rest of the UTC day, and the forward-fill is stale over
  weekends. FX noise is common to every coin's gap and to D, so it inflates correlations and biases the anchor slope toward 1.
  Sensitivity run: FX lagged one day.
- Premium (bps): g_i = 1e4 [log P_KRW,i - log P_USD,i - log FX]. Daily value = median over available hours of the UTC day (needs
  >= 12 hours). Sensitivity: the single hour starting 16:00 UTC.
- Common component: C = cross-sectional mean of g over BTC, ETH, XRP (BCH and ETC in robustness). L = C for the anchor test (and
  BTC-only gap as a second version).
- Anchor: D = 1e4 [log USDTKRW - log FX]; X = 1e4 log Kraken USDT/USD (data/raw/kraken_ohlcvt/USDTUSD_60.csv, plain CSV);
  slope of (D - X) on L by OLS, and IV with another coin's gap as instrument (ETH gap for L when L is the BTC gap; for the
  mean-of-three L, instrument = BCH gap). Slope 1 = unit/capital-control wedge; slope 0 = Korean crypto demand.

## Anchor availability (probed 2026-10-22, public API)
- Upbit KRW-USDT: first monthly candle 2024-06, i.e. after all reference data. Unusable.
- Bithumb KRW-USDT: first monthly candle 2023-12 (KST 2023-12-01). Used because Upbit lacks it (D17 allows Bithumb then).
  The listing day is a transient (range 1186 to 1396 KRW); we drop 2023-12-01 to 2023-12-07.
- Hence the anchor test runs only in window A0 = 2023-12-08 .. 2023-12-31 (hourly, 24 days). It is calm-regime and cannot
  test H2 in a high-premium window. In all other windows only the cross-asset part runs.

## Windows (from literature and news)
- High premium: E1 2017-12-01..2018-01-31 (Dec 2017 to Jan 2018 spike; Choi-Lehar-Stauffer, Lee-Oh); E2 2021-03-01..2021-05-31
  (2021 spike; Lee-Oh).
- Stress/reverse premium: E3 2022-05-01..2022-06-30 (Terra/Luna collapse, Korean-centred).
- Calm controls: C1 2019, C2 2020, C3 2023-01..2023-11 (full calendar years or months, no data selection).
- Per-year correlation tables for every calendar year 2017 (from Nov) to 2023.

## Hypotheses
- H1: the common component dominates. In each of E1 and E2, the Pearson correlation of daily gaps (levels) among BTC, ETH and XRP
  is >= 0.9 for all three pairs, and the leave-one-out share (R^2 of a coin's gap on the mean of the other two) is >= 0.8.
  Also reported: correlation of daily changes and the first-principal-component variance share.
- H2: in high-premium windows the anchor slope of (D - X) on L is near 1. Cannot be tested (no USDT/KRW). Status: NOT TESTABLE
  (neither supported nor failed). In A0 only, descriptive: slope with CI; read as unit if the CI contains 1 and excludes 0,
  as demand if it contains 0 and excludes 1, otherwise mixed/uninformative.

## Inference
Daily frames: moving-block (calendar week) bootstrap, 1,000 draws, seed 20261022, 95% percentile intervals, as the existing
anchor code. A0 hourly: calendar-day blocks, same draws and seed.

## What counts as failure
- H1 fails in a window if any of the three pair correlations is < 0.9 or the bootstrap lower bound of the median pair correlation
  is < 0.85, or the leave-one-out share < 0.8. H1 is "supported" only if it holds in both E1 and E2.
- The unit reading is not supported if the A0 slope CI excludes 1. If the A0 sample cannot reject both 0 and 1, we say the anchor
  is uninformative. Whatever the outcome, the paper claim is limited to: a common component dominates; its unit-versus-demand
  nature is unresolved by the available anchor.
- Data failure: an hour/day count below the thresholds above leaves the cell empty; no imputation.
