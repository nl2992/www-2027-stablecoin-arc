# Currency-wedge panel: a pre-registered replication of the anchored test (pre-registration)

Written 2026-10-24, before any data for this study was listed, downloaded or examined. Nothing below is tuned after results.

## Purpose

The paper's headline anchored test rests on one stress episode (Bitfinex, 2018-11-27..2019-05-31), plus Binance.US 2023. Reviewers objected to three things, and this study answers all three on new data:
- the test rests on one episode;
- the anchor correction was chosen after the raw slope was seen;
- the external reference may not be independent.

**The setting.** On many venues, crypto trades in a local currency: Binance markets in NGN, TRY, ARS, BRL, RUB, UAH, ZAR, EUR, GBP and AUD, and Upbit and Bithumb in KRW. A venue's local-currency balance is a unit that can sit at a wedge to the official currency, through capital controls or rail frictions. That is the same source-specific unit problem. The netting (D − X) and the instrument are fixed here *before* any data, so this is a genuinely pre-specified out-of-sample test.

## Markets

- **Binance:** every spot market set with BTC/F, ETH/F and USDT/F all listed, for F in {NGN, TRY, ARS, BRL, RUB, UAH, ZAR, EUR, GBP, AUD}.
- **KRW:** Upbit and Bithumb, with BTC, ETH and USDT in KRW.
- **Frequency:** hourly. For Binance, use the data.binance.vision 1h klines (monthly files). For Upbit and Bithumb, use the public 60-minute candles.
- **Coverage:** every full calendar month in which all three pairs traded at least 80% of hours, up to 2025-09.
- **USD reference and external USDT:** Kraken XBTUSD, ETHUSD and USDTUSD, hourly (`data/raw/kraken_ohlcvt/*_60.csv`), already held. The independence of X is relaxed by robustness, below.

## Quantities (bps, hourly, venue v, currency F)

- L_v(t) = 1e4·[log P_v(BTC/F) − log P_Kraken(BTC/USD)] (the BTC gap, with F's official rate NOT applied).
- L2_v(t) = the same for ETH (the instrument).
- D_v(t) = 1e4·log P_v(USDT/F).
- X(t) = 1e4·log P_Kraken(USDT/USD).
- **Why no official exchange rate is needed.** All three series contain the same unknown official exchange rate f_F(t). That rate is fixed within a UTC day, and its daily moves are common to all three. Estimation therefore uses **within-day variation only**: every series is demeaned by UTC day (day fixed effects), which removes f_F and any daily FX error.

## Estimand and estimator

- **Model:** D − X = λ·L + day effects + error, fitted on day-demeaned hourly data.
- **Prediction:** λ = 1 if within-day moves in the BTC gap are moves of the venue's currency unit, and λ = 0 if they are crypto-specific demand.
- **Estimators:** OLS, and IV with L2 as the instrument for L. IV is the primary estimator.
- **Inference:** moving-block bootstrap over days (blocks of 7 days, 1,000 draws, seed 20261024), giving 95% intervals.

## Stress and calm months (classification fixed before computing D)

- A month is **stress** if the median over its hours of |L − median_month(L)| ≥ 25 bps; otherwise it is **calm**. This uses L only, never D.
- Stress months are where the test has power. Calm months are reported separately.
- The classification is committed (`reports/panel/months.json`) BEFORE D or X is loaded.

## Hypotheses and success rules

- **P1 (primary):** the pooled IV λ̂ across all stress months has a 95% interval that excludes 0 and includes 1.
- **P2:** among the currencies with at least 3 stress months, the per-currency IV λ̂ lies in [0.8, 1.2] for a majority.
- **P3 (honesty check):** report every per-currency and per-month estimate, including any with λ̂ < 0.5.
- **Falsification:** the pooled 95% upper bound is below 0.5.

## Robustness (reported, not used to choose anything)

- OLS instead of IV.
- Daily rather than hourly within-week variation, i.e. week fixed effects on daily medians.
- An alternative X where available: Binance.US USDT/USD (2019-09 onward) or Bitstamp USDT/USD (2022-04 onward).
- KRW only: Upbit and Bithumb separately.

## Data (approved 2026-10-24, D19)

- **Binance:** public monthly 1h klines from data.binance.vision for {BTC, ETH, USDT}/F and the F listed above, over the months each pair existed, up to 2025-09. First check existence via the bucket listing; record NOT_AVAILABLE for anything missing.
- **Upbit / Bithumb:** public 60-minute candles for KRW-BTC, KRW-ETH and KRW-USDT, 2023-12..2025-09.
- No other sources.
