# Fusion on the currency panel: official-rate versus anchor-corrected conversion (pre-registration)

Written 2026-10-25, before any official exchange-rate data was downloaded and before any conversion error was computed.

## Question

Price services turn local-currency crypto prices into U.S. dollars at the official exchange rate. When a venue's local currency sits at a wedge to the official rate (the Kimchi premium and its relatives), the converted price inherits the wedge. Does converting through the venue's own stablecoin market, corrected for the stablecoin's external price, give a better dollar price? And does a cross-market median of officially converted prices fail where several markets share a wedge of the same sign?

## Markets and data

- **Venue-currency units:** those from the pre-registered panel (`program_panel.md`) whose official rate is published in the ECB euro reference rates.
  - Binance TRY, BRL, ZAR, and RUB up to 2022-02-28 (the ECB stopped publishing RUB on 2022-03-01).
  - Upbit and Bithumb KRW.
- ARS, NGN and UAH are excluded: the ECB has no reference rate for them. This exclusion is stated now.
- **Official rate:** the ECB euro reference rate for F and USD, giving F per USD = (F per EUR) / (USD per EUR). It is daily, published at about 14:15 CET, and carried forward to every hour until the next publication (no look-ahead: an hour uses the latest rate published before it).
- **Truth:** Kraken BTC/USD hourly (already held).
- **Prices:** the same hourly panel and coverage rule as `program_panel.md`.

## Methods (each gives a log BTC/USD price per unit-hour)

- **O (official conversion):** log P_v(BTC/F) − log(official F per USD).
- **A (anchor-corrected conversion):** log P_v(BTC/F) − log P_v(USDT/F) + log P_ext(USDT/USD). The external USDT/USD is Bitstamp USDT/USD where available (from 2022-04); otherwise Binance.US USDT/USD (from 2019-09); otherwise Kraken USDT/USD. This means A never uses the truth series's own venue when another source exists.
- **Fused indices over all units observed in an hour:**
  - **MO:** the median of the O prices.
  - **MA:** the median of the A prices.

## Metrics and endpoints

- **Error:** e = 1e4·(method − truth), in bps.
- **Primary:** the pooled mean of log(|e_A| + 1 bp) − log(|e_O| + 1 bp) over all unit-hours. The test is a day-block bootstrap (1,000 draws, seed 20261025). **Success:** the upper 95% bound is below 0.
- **Secondary:** the same comparison per unit; MA against MO (log-error difference, day-block bootstrap); MAE, p95 and hours ≥ 50 bps per method and per unit.
- **Scope statement, fixed now:** A uses the venue's own stablecoin market, so by triangular arbitrage it partly reflects the venue's BTC/USDT price. The test measures the error a price service makes by using official rates for markets with a currency wedge. It is not a claim that A uses less information than O.

## Failure reading

If the primary endpoint fails, report that official conversion was as good as anchor-corrected conversion for these units.

## Data (D20)

ECB euro foreign exchange reference rates history, the single public file `eurofxref-hist.zip` from ecb.europa.eu. Nothing else new.
