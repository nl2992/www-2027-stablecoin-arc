# Kimchi application: notes on the run (2026-10-22)
Deviations from and clarifications to PREREG.md (the pre-registration itself is unchanged and was committed before any price download):
1. Bithumb's first hourly USDT/KRW candle is 2023-12-07 03:00 UTC (the monthly candle label 2023-12-01 aggregates it), so the listing
   date is 2023-12-07; the pre-registered exclusion of 2023-12-01..07 and the window A0 = 2023-12-08..2023-12-31 stand. Upbit KRW-USDT
   starts 2024-06.
2. PREREG called A0 a "calm-regime" month. That assumption was wrong: the common gap is about 4.3% (median 431 bps) and USDT/KRW is
   about 4.1% above the DEXKOUS dollar. A0 is therefore an informative premium regime, but still a single 24-day window.
3. Upbit has no KRW-LTC; the majors are BTC, ETH, XRP, BCH, ETC. Hourly data start 2017-10-01 (Upbit launched late Oct 2017), so
   E1 has 62 days.
4. H1 passes in the calm controls as well, so high correlation of the gaps does not by itself indicate a premium episode.
   Correlation in levels is also raised by the shared FX conversion; changes correlate 0.92-0.99.
5. 5-coin robustness: ETC's pairwise correlation is weak in some years (min 0.25 in 2020), reflecting Coinbase ETC data, not Upbit.
