# UNIT-TD studies: T4 unit diagnostic and T2 fusion under injected unit bias

Code: `src/www_auto/studies.py` (`uv run python -m www_auto.studies all`). Outputs: `reports/unit_td/t4_unit_diagnostic.json|md` and `reports/unit_td/t2_breakdown.json|md`. Tests: `tests/test_www_auto_studies.py`.

Only dev assets are used (BTC, ETH, LTC, BCH, ETC, XLM, plus the Bitfinex USDT and ETHBTC feeds). The panel is read in dev mode, so the test assets XRP, LINK, SOL, DOGE and ADA are never loaded. Any estimator with the harness interface `estimate_units(panel, numeraire_venue)` can be passed in; the default is `www_auto.estimator`.

## Read this first: two estimators, because the default one is blind with a single asset

The current `www_auto.estimator` shrinks the median cross-asset gap by the cross-asset dispersion. With one visible asset the dispersion is undefined, the shrinkage keeps nothing, and the estimator returns exactly 0 for every venue. This matters in two places:

- T2 asks for offsets estimated from the *other* asset, so only one asset is visible. The default estimator therefore removes nothing, and "unit-aware fusion" with it is the plain median.
- Bitstamp lists only BTC and ETH, so in every Bitstamp pair the default estimator has at most one asset for Bitstamp.

So the T2 tables show two estimators side by side: `default` (the pluggable `www_auto.estimator`) and `b2_median_gap`, the same-hour median log gap to the numeraire with no shrinkage and no smoothing. The T4 table also reports the classification that the b2 baseline would give. The results for `b2_median_gap` are the informative ones for unit-aware fusion; the `default` rows document the limitation.

## T4: which venues have their own dollar, and when

Per venue pair and year, from the leave-one-asset-out harness formula, 1 - sum (g - u)^2 / sum g^2, where g is the pair's hourly gap in bps and u the estimator's pair offset with the held-out asset removed from every venue. Scored assets are the dev assets other than BTC that both venues list (ETH, LTC, BCH, ETC, XLM for Bitfinex-Coinbase; ETH only for the Bitstamp pairs, with BTC visible), the same scored set as the harness. The daily cross-asset gap correlation is the correlation over days of the BTC daily mean gap with each other shared asset's, averaged over assets (days need at least 12 hours; a year needs at least 30 days). The median |gap| is pooled over the scored assets.

Thresholds (constants in the code, fixed before looking, not tuned): "separate dollar" if explained share >= 0.5 and median |gap| >= 3 bps; "shared dollar" if explained share <= 0.1; "mixed" otherwise.

| Pair | Year | Hours | Explained (est) | b1 | b2 | Median abs gap (bps) | Corr BTC vs others | Class | Class if b2 used |
|---|---|---|---|---|---|---|---|---|---|
| bitfinex-coinbase | 2017 | 17539 | 0.77 | 0.79 | 0.79 | 65.4 | 0.96 | separate dollar | separate dollar |
| bitfinex-coinbase | 2018 | 29608 | 0.50 | 0.52 | 0.53 | 24.9 | 0.81 | separate dollar | separate dollar |
| bitfinex-coinbase | 2019 | 41169 | 0.66 | 0.68 | 0.68 | 41.7 | 0.88 | separate dollar | separate dollar |
| bitfinex-coinbase | 2020 | 43308 | 0.03 | 0.02 | 0.03 | 15.2 | 0.65 | shared dollar | shared dollar |
| bitfinex-coinbase | 2021 | 43703 | -0.00 | -0.00 | -0.00 | 9.0 | 0.57 | shared dollar | shared dollar |
| bitfinex-coinbase | 2022 | 43754 | 0.18 | 0.19 | 0.19 | 7.0 | 0.83 | mixed | mixed |
| bitfinex-coinbase | 2023 | 43362 | 0.36 | 0.38 | 0.38 | 8.5 | 0.94 | mixed | mixed |
| bitfinex-bitstamp | 2017 | 2928 | -1.42 | 0.87 | 0.87 | 30.2 | 0.99 | shared dollar | separate dollar |
| bitfinex-bitstamp | 2018 | 8759 | 0.93 | 0.98 | 0.98 | 19.2 | 1.00 | separate dollar | separate dollar |
| bitfinex-bitstamp | 2019 | 8751 | 0.95 | 0.99 | 0.99 | 40.9 | 1.00 | separate dollar | separate dollar |
| bitfinex-bitstamp | 2020 | 8773 | 0.39 | 0.70 | 0.70 | 12.1 | 0.98 | mixed | separate dollar |
| bitfinex-bitstamp | 2021 | 8745 | 0.33 | 0.51 | 0.51 | 5.6 | 0.93 | mixed | separate dollar |
| bitfinex-bitstamp | 2022 | 8754 | 0.56 | 0.72 | 0.72 | 5.1 | 0.97 | separate dollar | separate dollar |
| bitfinex-bitstamp | 2023 | 8757 | 0.80 | 0.84 | 0.84 | 6.7 | 0.99 | separate dollar | separate dollar |
| coinbase-bitstamp | 2017 | 2925 | 0.00 | 0.88 | 0.88 | 32.6 | 0.98 | shared dollar | separate dollar |
| coinbase-bitstamp | 2018 | 8754 | 0.00 | 0.43 | 0.43 | 10.1 | 0.94 | shared dollar | mixed |
| coinbase-bitstamp | 2019 | 8757 | 0.00 | -0.28 | -0.28 | 5.9 | 0.28 | shared dollar | shared dollar |
| coinbase-bitstamp | 2020 | 8776 | 0.00 | -0.14 | -0.14 | 4.4 | 0.20 | shared dollar | shared dollar |
| coinbase-bitstamp | 2021 | 8759 | 0.00 | -0.00 | -0.00 | 3.3 | 0.63 | shared dollar | shared dollar |
| coinbase-bitstamp | 2022 | 8757 | 0.00 | 0.31 | 0.31 | 2.6 | 0.60 | shared dollar | mixed |
| coinbase-bitstamp | 2023 | 8756 | 0.00 | 0.04 | 0.04 | 1.5 | 0.67 | shared dollar | shared dollar |

What the table says:

- Bitfinex has its own dollar relative to Coinbase in 2017 to 2019: explained share 0.5 to 0.8 with median gaps of 25 to 65 bps. In 2020 and 2021 the gap shrinks and the explained share falls to about zero (shared dollar), and in 2022 and 2023 it is mixed at 7 to 9 bps and 0.2 to 0.4.
- Bitfinex against Bitstamp tells the same story with a cleaner signal, because the gap is almost perfectly correlated across assets (0.93 to 1.00), but this pair has only ETH to score, and its "explained" share is of that one asset.
- Coinbase against Bitstamp is classified "shared dollar" in every year, but this is partly mechanical: the default estimator cannot estimate Bitstamp's unit from one asset, so its explained share is exactly 0.00 in every year. The b1/b2 baselines, which carry the other asset's gap, explain 0.88 of the 2017 gap and 0.43 in 2018 (the "Class if b2 used" column calls these separate and mixed). From 2019 on, b1 and b2 explain little or nothing, so the shared-dollar reading is supported for 2019 to 2023 but not for 2017 and 2018.
- The estimator never beats b1/b2 on any pair-year (for Bitfinex-Coinbase the estimator's shares are within 0.03 of b2, and slightly below it), so T4 does not show added value of the estimator over the simple same-hour gap in this table.
- Where the explained share is negative or the corr is low (Coinbase-Bitstamp 2019 and 2020, correlation 0.2 to 0.3), the gaps are venue-asset noise rather than a common unit.

## T2: fusion under injected unit bias

Setup. Calm window 2021-01 to 2023-12, venues Bitfinex, Coinbase and Bitstamp, assets BTC and ETH (the only assets on all three), on hours where all six series have a price and positive volume: 26,251 hours, 52,502 asset-hours per choice of biased venues. Truth is the cross-venue median of the uninjected log prices. A shared unit offset path is added to k venues on both assets; for k = 1 and k = 2 all 3 choices of venues are run and the errors are pooled (the "worst venue choice" is reported separately). Offsets: constant delta in {25, 50, 100, 200, 400, 800} bps, and a realistic path: Bitfinex's own BTC gap against Bitstamp, 2018-10 to 2019-05 (5,832 hours; median 231 bps, p95 |gap| 486 bps, max 1,069 bps), replayed by hour of episode (cycled to fill the window, gaps interpolated).

Fusers.

- `median`: median of the three venue prices.
- `vwap`: volume-weighted mean.
- `crh`: CRH-style source reliability (Li et al. 2014), weights = -log of each source's normalised squared loss, truth = weighted mean, iterated to convergence; causal, the weights used on day d are fitted on day d-1 (assets pooled), equal weights on day 1.
- `ua_median[est]`: unit offsets from the *other* asset (ETH for BTC, BTC for ETH) with estimator `est`, relative to a fixed reference venue (Coinbase); offsets removed, then median. The output is in the reference venue's unit.
- `ua_cluster[est]`: dependence-aware. Offsets are smoothed with a causal 24 h trailing median, venues whose offsets agree within 10 bps (single linkage) share a unit, each cluster casts one vote (the median of its members), the numeraire is the largest cluster (ties: most liquid), other clusters' votes are moved into its unit, and the median of the votes is taken. The 10 bps tolerance and the 24 h smoothing are fixed constants and were not tuned.

Error is the absolute fused-minus-truth log price in bps, pooled over assets and hours.

### p95 absolute error vs truth (bps)

k = 1 of 3 venues biased:

| Fuser | 25 | 50 | 100 | 200 | 400 | 800 | realistic |
|---|---|---|---|---|---|---|---|
| median | 13.3 | 13.3 | 13.3 | 13.4 | 13.4 | 13.4 | 12.9 |
| vwap | 22.9 | 45.7 | 91.7 | 183.7 | 367.8 | 736.2 | 265.2 |
| crh | 12.7 | 8.0 | 7.4 | 7.4 | 7.3 | 7.3 | 7.5 |
| ua_median[default] | 13.3 | 13.3 | 13.3 | 13.4 | 13.4 | 13.4 | 12.9 |
| ua_cluster[default] | 13.3 | 13.3 | 13.3 | 13.4 | 13.4 | 13.4 | 12.9 |
| ua_median[b2_median_gap] | 26.5 | 51.4 | 101.4 | 201.4 | 401.4 | 801.4 | 335.6 |
| ua_cluster[b2_median_gap] | 21.6 | 47.4 | 97.3 | 197.2 | 397.2 | 797.2 | 68.4 |

k = 2 of 3 venues biased:

| Fuser | 25 | 50 | 100 | 200 | 400 | 800 | realistic |
|---|---|---|---|---|---|---|---|
| median | 25.0 | 50.0 | 100.0 | 200.0 | 400.0 | 800.0 | 460.8 |
| vwap | 24.9 | 49.2 | 98.0 | 195.9 | 391.8 | 784.0 | 362.8 |
| crh | 30.0 | 55.9 | 106.1 | 206.2 | 406.2 | 806.2 | 463.7 |
| ua_median[default] | 25.0 | 50.0 | 100.0 | 200.0 | 400.0 | 800.0 | 460.8 |
| ua_cluster[default] | 25.0 | 50.0 | 100.0 | 200.0 | 400.0 | 800.0 | 460.8 |
| ua_median[b2_median_gap] | 27.9 | 52.9 | 102.9 | 202.9 | 402.9 | 802.9 | 403.2 |
| ua_cluster[b2_median_gap] | 29.7 | 54.7 | 104.7 | 204.7 | 404.7 | 804.7 | 449.3 |

The median errors and the share of asset-hours above 50 bps for every cell are in `reports/unit_td/t2_breakdown.md` and `.json` (for example, at k = 2 and 100 bps the median, CRH and both default unit-aware fusers are off by more than 50 bps in 100% of hours; at k = 1 and 400 bps the volume-weighted mean is above 50 bps in 56% of hours and the median in 0%).

### Breakdown delta* (smallest tested delta whose p95 error exceeds 50 bps)

| Fuser | k = 1 pooled | k = 1 worst venue choice | k = 2 pooled | k = 2 worst venue choice |
|---|---|---|---|---|
| median | none (to 800) | none | 50 | 50 |
| vwap | 100 | 100 | 100 | 100 |
| crh | none | none | 50 | 50 |
| ua_median[default] | none | none | 50 | 50 |
| ua_cluster[default] | none | none | 50 | 50 |
| ua_median[b2_median_gap] | 50 | 50 | 50 | 50 |
| ua_cluster[b2_median_gap] | 100 | 50 | 50 | 50 |

Note the grid is coarse: a delta* of 50 at k = 2 for the median means the p95 error is exactly 50.0 at 50 bps and crosses the threshold by a hair, so the true breakdown is a little under 50 bps. At k = 2 every fuser fails by the smallest tested deltas, as it must.

### What the numbers show

- With one biased venue the median and CRH are unaffected up to 800 bps: the median's 13 bps floor is the spread between the two clean venues (the truth is the middle price, the fused value is one of the outer ones). The volume-weighted mean moves in proportion to the biased venue's weight and breaks down at 100 bps. CRH down-weights the outlier source and ends up slightly better than the median here.
- Unit-aware fusion with the default estimator equals the median in every cell, for the single-asset reason above.
- Unit-aware median with the `b2_median_gap` estimator is *worse* than the plain median at k = 1: it moves every venue into the fixed reference venue's unit, and when that reference (Coinbase) is the biased one, the whole fusion inherits the bias. That happens in 1 of the 3 venue choices, which is the 33% of hours above 50 bps. The clustering fix is only partly successful: choosing the largest cluster as the numeraire repairs this (the venue partition is recovered in 87% of asset-hours), but the remaining 13% of hours, where one asset's idiosyncratic cross-venue basis exceeds the 10 bps tolerance, still produce a wrong partition, so `ua_cluster[b2]` has 2 to 6% of hours above 50 bps at k = 1 and a p95 error that tracks delta. It never beats the plain median or CRH at k = 1, and with the realistic path it is much better than `ua_median` (68 vs 336 bps) but still worse than the median (13 bps).
- Neither a sharper estimator nor the clustering makes unit-aware fusion beat the median in this panel. The value of unit awareness is information, not accuracy in the numeraire unit, as the next section shows.

### k = 2 of 3: no method can know which dollar is "true"

If two of the three venues share a biased dollar, then the two-venue majority and the one-venue minority are symmetric from the data alone. Nothing in the price panel says which unit is the real USD; that needs outside information (a bank-rail, a stablecoin redemption anchor or a trusted reference). Every fuser above, including unit-aware fusion, therefore ends up in the majority's unit, which is the biased one, and its error against the uninjected truth is the full delta. Unit-aware fusion does not fix this and the doc does not claim that it does.

What it does recover at k = 2 (delta = 200 bps, errors pooled over the three venue choices; "vs majority unit" scores the fused price against truth plus the injected offset):

| Fuser | p95 error vs truth | p95 error of the ETH/BTC ratio | Median error vs majority unit | p95 error vs majority unit |
|---|---|---|---|---|
| median | 200.0 | 6.8 | 0.9 | 9.6 |
| vwap | 195.9 | 50.0 | 30.8 | 184.7 |
| crh | 206.2 | 5.1 | 1.4 | 7.3 |
| ua_median[b2_median_gap] | 202.9 | 7.1 | 2.5 | 202.6 |
| ua_cluster[b2_median_gap] | 204.7 | 10.0 | 1.7 | 198.5 |

Two things are recovered, honestly stated:

1. **Cross-asset ratios.** A unit offset shared by an asset pair's venues cancels in the ETH/BTC ratio, and the fused ETH/BTC is within about 5 to 10 bps (p95) of the truth ratio for the median, CRH and the unit-aware fusers, but not for the volume-weighted mean, whose weights flip with the venue (50 bps). The synthetic test checks the exact case: with exact offsets, the unit-aware cluster fuser returns the price in the majority's unit and the ratio is exact to floating point. This is also true for the plain median, so it is a property of a *shared* offset, not an advantage of unit awareness.
2. **Which venues share a dollar.** The venue partition from the offsets is the real extra output: against the injected partition, `b2_median_gap` clustering is right in 85 to 87% of asset-hours at every delta, for k = 1 and k = 2, and the realistic path gives 85%. The default estimator recovers it 0% of the time (it reports one cluster, since all its offsets are 0). Cluster membership is what lets a downstream user say "Bitfinex and Coinbase quote different dollars in 2018" without knowing which one is right. The median error against the majority unit is 1.7 to 2.5 bps for the `b2` unit-aware fusers, so in the hours when the partition is right they land in the majority's dollar. The p95 vs majority unit is 198 to 203 bps because in the remaining 13 to 15% of hours the partition is wrong.

## Caveats

- Unit-aware fusion here uses one asset at a time (the other of BTC and ETH), so the estimator never sees more than one asset. This is the specified setup, but it is the setting where the default shrinkage estimator is inoperative. A fair test of a good estimator needs more shared assets than are on all three venues.
- Ratio and cluster recovery use only BTC and ETH. The cluster tolerance (10 bps) and smoothing (24 h) are fixed and were not tuned; the partition accuracy is sensitive to the tolerance relative to the cross-asset basis noise (no separate sweep over tolerances was run).
- T4 uses one numeraire (Coinbase) for all pairs and the harness's scored set, so for the Bitstamp pairs the explained share rests on ETH only. Venue-years with fewer than 500 scored hours would be "insufficient"; none in the table are.
- The realistic path is a single episode (Bitfinex against Bitstamp BTC) applied to whichever venues are hit, including pairs it did not occur in; it is cycled to cover three years.
- Truth is the median of the uninjected venues, so the "truth" itself carries the clean-venue spread (the 13 bps median floor at k = 1).
- The calm window is the only window; breakdown points in stress periods will be lower.
- `tests/test_www_auto.py::test_planted_unit_recovered_in_control_pair_too` was already failing on the merged `autoresearch/unit-td` estimator for the same single-asset reason (it asserted the control score of the loop-edited estimator); it now uses the plain median-gap estimator, which tests the harness rather than the estimator being edited.
