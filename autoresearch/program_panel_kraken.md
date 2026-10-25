# A non-Binance slice of the currency panel: Kraken fiat markets (pre-registration)

Written 2026-10-25, before any Kraken fiat-pair data was downloaded or examined. It follows `program_panel.md` exactly, except for the venue and the reference choices stated here.

## Purpose

Seven of the panel's eight units trade on Binance and share one external price and one instrument. This slice tests the same anchored relation on a different venue, Kraken, with a different reference venue.

## Units

Every Kraken fiat currency F among {EUR, GBP, CAD, AUD, CHF, JPY} for which Kraken's OHLCVT data has XBT/F, ETH/F and USDT/F, all at 60-minute resolution, over every full month with all three pairs traded in at least 80% of hours, 2017-01 through 2025-03.

## Quantities (bps, hourly, Kraken currency F)

- L = 1e4·[log P_Kraken(XBT/F) − log P_Bitstamp(BTC/USD)]. Bitstamp is the reference: it is a different venue from Kraken, and its BTC/USD is held to 2025-03.
- L2 = the same for ETH (Bitstamp ETH/USD, held to 2023-12; the slice ends 2023-12 wherever ETH is needed).
- D = 1e4·log P_Kraken(USDT/F).
- X = 1e4·log P_Kraken(USDT/USD). This is Kraken's own USDT/USD; the slice tests whether the venue's F-unit offset moves its USDT/F price.
- Within-day estimation (day fixed effects), as in the panel. The official rate cancels.

## Estimation, months and hypotheses

These are the same as `program_panel.md`:
- **Estimators:** IV, with L2 as the instrument for L, as primary; OLS reported.
- **Inference:** a 7-day moving-block bootstrap, 1,000 draws, seed 20261025.
- **Months:** the stress and calm classification uses L only and is committed before D or X is loaded.

**Hypotheses:**
- **K1:** the pooled IV interval excludes 0.
- **K2:** for a majority of currencies with at least 3 months, λ̂ lies in [0.8, 1.2].
- **Expectation stated now:** these are freely convertible currencies on a regulated venue, so wedges should be small. Power may therefore be low and intervals wide, and a slope near one would show the relation holds outside Binance.

## Data (D21)

Kraken's downloadable OHLCVT archive (the same five-part `Kraken_OHLCVT_Full.zip` from assets.kraken.com, verified against its published SHA-256). Extract ONLY the XBT, ETH and USDT pairs quoted in the six currencies above, at 60-minute resolution, then delete the archive. Disk is limited (about 18 GB free), so join the parts while deleting each part after it is appended.
