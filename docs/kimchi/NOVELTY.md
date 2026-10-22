# Novelty check: Kimchi premium decomposed with a USDT/KRW anchor (2026-10-22)

Question. Has anyone separated the Kimchi premium into a unit / capital-control wedge and a Korean crypto-demand component by
using the won price of USDT (or another stablecoin) as an anchor, tested with the slope of (D - X) on the cross-asset gap L?

## What exists (web search; ScienceDirect and SSRN pages returned HTTP 403, so those items are known from search snippets only)
1. Choi, Lehar and Stauffer, "Bitcoin Microstructure and the Kimchi Premium" (SSRN 3189051): capital controls magnify
   microstructure frictions and keep arbitrageurs from closing the Korea-US gap. No stablecoin anchor.
2. Makarov and Schoar, "Trading and arbitrage in cryptocurrency markets" (JFE 2020), from memory and not re-checked:
   documents large, persistent Korea-US gaps in BTC, ETH and XRP and links them to capital controls. No USDT/KRW anchor.
3. "Stablecoin and cross-border crypto market integration" (Economics Letters 2025, ScienceDirect S0165176525005415), snippet only:
   high-frequency BTC and USDT Kimchi premiums are cointegrated at parity with a half-life of about 24 minutes. This is the
   closest academic item: USDT's premium moves one-for-one with BTC's. It is a cointegration/parity test of two premiums, not a
   multi-coin common-component decomposition, not a net-of-external-USDT-price slope test, and not tied to episodes.
4. "Nonlinear dynamics of Kimchi premium" (Economic Modelling 2024, S0264999324000828), snippet only: capital controls still apply to
   crypto and create Kimchi premiums in BTC and USDT; tests long-run parity between them. Same family as item 3.
5. Informal, not peer reviewed: GitHub scotankboi/kimchi-premium splits the Upbit/Bithumb BTC premium multiplicatively into the USDT
   premium (USDT/KRW over USD/KRW) and a crypto-specific remainder, with covariance shares. It reports the USDT part explains
   about 99% of mean and variance, from 2023-12 onward (Bithumb USDT/KRW from Dec 2023, Upbit from Jun 2024), using FRED DEXKOUS
   and Binance BTC/USDT as the reference.
6. Lee and Oh (Finance Research Letters 2022): premium spikes (Jan 2018, May 2021) track remittances to China. Demand-side evidence.

## Verdict: PARTLY ANTICIPATED, NOT DONE IN THE SAME FORM
- The USDT-anchor idea (USDT/KRW premium carries the BTC premium) is anticipated for 2023-12 onward by item 5 (informal) and
  item 3 (parity of BTC and USDT premiums).
- Not found anywhere: (a) the same decomposition for the 2017-18 and 2021 high-premium episodes; (b) the cross-asset common
  component (BTC, ETH, XRP, ...) with a share-explained and per-year correlation; (c) the slope-of-(D - X)-on-L test with a
  block bootstrap and an instrument.
- Binding constraint, found by probing the free APIs: USDT/KRW does not exist on Upbit before 2024-06 and on Bithumb before
  2023-12-01. Our dollar-reference data end 2023-12. So the anchor test can run only in December 2023 (a calm month); a 2017-18 or
  2021 anchored test cannot be run with the authorized sources by anyone, which is why the literature has none.
- Consequence: the defensible contribution here is the 2017-2023 cross-asset common-component evidence (H1) plus a descriptive,
  low-power anchor check in 2023-12. The unit-versus-demand slope in high-premium windows is NOT TESTABLE and we will say so.
