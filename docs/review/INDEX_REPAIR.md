# Index repair: how much of the price-feed error can a methodology remove? (2026-10-19)

Code: `src/www_rescue/index_repair.py`. Tests: `tests/test_index_repair.py`. Output: `reports/rescue/index_repair.json`. Builds on `docs/review/FEED_BIAS.md` and reuses its loaders, benchmark and monitor flag.

## 1. Setup

**Error.** Hourly, in bps: 10,000 × (index − clean) in log prices. The clean benchmark is the volume-weighted mean over open-rail venues (Bitstamp and Coinbase; Bitstamp alone for Binance.US). It is the same benchmark as `feed_bias`.

**Methods.** The "platform" is Bitfinex or Binance.US.

| Method | Rule |
|---|---|
| naive | Volume-weighted mean of all venues. |
| equal | Equal-weight mean. |
| median | Cross-venue median. |
| excl-k (k = 50, 100, 200) | Drop a venue-hour more than k bps from the cross-venue median, then volume-weighted mean of the rest. If all venues are dropped, fall back to naive. |
| filtered | Naive, with flagged platform venue-hours dropped. The flag is the monitor rule (|L| ≥ 100 bps and the second asset agrees within 25%). |
| repaired | In flagged platform venue-hours, keep the venue but subtract PD_second from its log price. PD_second is PD_ETH for Bitfinex and PD_USDT for Binance.US. |

**The repair is not circular.** The amount subtracted is PD_second only. It never uses the platform's own BTC gap L and never the benchmark. L only decides where the adjustment is applied (through the flag). The leftover error is the part of the BTC gap that the second asset does not explain. A test (`test_repair_adjustment_does_not_depend_on_the_platforms_own_btc_gap`) checks that changing the platform BTC price leaves the subtracted amount unchanged.

**Only 3 venues, and 2 for Binance.US.** This is a narrow index, so these are small-index results. See section 5.

## 2. Results, all hours

Columns: hours with |error| ≥ 50 bps / ≥ 100 bps; median / p95 / max |error| in bps.

**Bitfinex 2017** (5,088 hours; 3 venues; Bitfinex median volume share 0.48)

| Method | ≥ 50 | ≥ 100 | Median | p95 | Max |
|---|---|---|---|---|---|
| naive | 1,642 | 931 | 23.7 | 238 | 634 |
| equal | 1,453 | 819 | 17.8 | 194 | 365 |
| median | 635 | 208 | 11.8 | 89 | 392 |
| excl-50 | 746 | 224 | 9.5 | 92 | 392 |
| excl-100 | 679 | 245 | 9.1 | 98 | 458 |
| excl-200 | 752 | 212 | 10.6 | 91 | 458 |
| filtered | 730 | 327 | 9.8 | 119 | 634 |
| repaired | 735 | 327 | 12.3 | 119 | 634 |

**Bitfinex 2018** (2,928 hours; 3 venues; share 0.52)

| Method | ≥ 50 | ≥ 100 | Median | p95 | Max |
|---|---|---|---|---|---|
| naive | 1,824 | 1,284 | 85.3 | 231 | 661 |
| equal | 1,589 | 708 | 59.1 | 130 | 280 |
| median | 1 | 1 | 1.3 | 5 | 168 |
| excl-50 | 1 | 1 | 0.0 | 13 | 207 |
| excl-100 | 46 | 1 | 0.0 | 36 | 207 |
| excl-200 | 533 | 144 | 2.1 | 100 | 207 |
| filtered | 49 | 5 | 0.0 | 36 | 291 |
| repaired | 49 | 5 | 4.8 | 37 | 291 |

**Bitfinex 2019** (3,672 hours; 3 venues; share 0.31)

| Method | ≥ 50 | ≥ 100 | Median | p95 | Max |
|---|---|---|---|---|---|
| naive | 933 | 469 | 12.6 | 170 | 471 |
| equal | 1,125 | 326 | 14.0 | 188 | 242 |
| median | 0 | 0 | 1.0 | 4 | 17 |
| excl-50 | 0 | 0 | 0.3 | 13 | 36 |
| excl-100 | 5 | 0 | 2.0 | 25 | 64 |
| excl-200 | 187 | 24 | 3.8 | 50 | 147 |
| filtered | 7 | 0 | 2.0 | 24 | 72 |
| repaired | 7 | 0 | 3.4 | 24 | 72 |

**Binance.US 2023** (2,207 hours; 2 venues; share 0.43). Median and exclusion are degenerate here.

| Method | ≥ 50 | ≥ 100 | Median | p95 | Max |
|---|---|---|---|---|---|
| naive | 280 | 142 | 5.5 | 114 | 1,366 |
| equal = median | 682 | 564 | 6.4 | 506 | 1,046 |
| excl-50, 100, 200 (= naive) | 280 | 142 | 5.5 | 114 | 1,366 |
| filtered | 24 | 3 | 0.0 | 20 | 316 |
| repaired | 24 | 3 | 0.8 | 22 | 316 |

**How to read it:**
- Hours ≥ 100 bps, totalled over the four episodes: naive 2,826; median 773; excl-50 367; excl-100 388; filtered 335; repaired 335. The Binance.US row alone contributes 564 to the median total and 142 to excl-100.
- On the three Bitfinex episodes with three venues, a median or an outlier rule does very well in 2018 and 2019 (at most 1 hour ≥ 100 bps). That is expected: one venue among three is the outlier, and the median ignores it. It needs no monitor.
- In 2017 the median beats the monitor (208 against 327 hours ≥ 100 bps). The monitor's 2017 residual comes from the reference disagreement between Bitstamp and Coinbase (see FEED_BIAS). A median does not use either as a reference, so it avoids that.
- On Binance.US with two venues, the median is worse than naive (564 against 142 hours ≥ 100 bps), because it gives the platform a weight of 0.5 instead of its volume share. The exclusion rule is identical to naive: both venues sit the same distance from the median, so it drops both or neither. These two methods cannot work with two venues. Only the monitor and the repair use information outside the price panel.
- Exclusion with k = 200 is worse than k = 50 or 100 on Bitfinex 2018 and 2019 because discounts below 200 bps are kept. The threshold has to be set below the damage you care about. That is a tuning problem the monitor does not have.
- Repair never beats filtering on the hours ≥ 100 count. The two differ only in flagged hours, where filtering is exact by construction (error 0). Repair leaves a small error from the part of the BTC gap that PD_second does not explain.

## 3. Flagged hours, and when the platform is the volume leader

Flagged hours are those the monitor flags. In them the filtered error is zero by construction, so the informative column is repaired.

| Episode | Flagged hours | Platform leads volume (hours) | Flagged and leads | Naive: ≥ 100 bps in flagged and leads | Median | Excl-100 | Repaired: median / max in flagged hours (bps) |
|---|---|---|---|---|---|---|---|
| Bitfinex 2017 | 1,012 | 3,708 | 537 | 361 of 537 | 3 | 4 | 7.2 / 78 |
| Bitfinex 2018 | 1,895 | 2,329 | 1,489 | 1,157 of 1,489 | 1 | 1 | 3.8 / 50 |
| Bitfinex 2019 | 1,213 | 1,001 | 423 | 295 of 423 | 0 | 0 | 1.8 / 20 |
| Binance.US 2023 | 677 | 782 | 59 | 46 of 59 | 30 | 46 (naive) | 0.3 / 46 |

**How to read it:**
- When the platform leads, a volume-weighted index is pulled the most. Naive error in flagged-and-leader hours has a median of 122 to 144 bps on Bitfinex.
- Three-venue medians still hold when the platform leads. The leader's volume does not matter to a median.
- For Binance.US, the leader case has only 59 hours that are both flagged and led by Binance.US. Binance.US led volume for 782 hours, but those were mostly not flagged hours. The count is small, so do not read much into it.
- Errors remain outside flagged hours: across all 2017 platform-leader hours, filtered still has 509 hours ≥ 50 bps and 222 ≥ 100 bps. These are hours the monitor did not flag, mostly the 2017 reference disagreement again.

## 4. Scaling: a platform with index weight w

Bias ≈ w × PD. Using the observed paths, the implied index error is w × |PD|. The table shows hours with implied error ≥ 50 bps (0.5%, a typical price-oracle deviation threshold; no specific oracle's parameters are claimed). The PD path is the platform BTC gap L against Bitstamp; the PD_second path gives similar counts (see the JSON).

| w | Bitfinex 2017 (of 5,088 h) | Bitfinex 2018 (of 2,928) | Bitfinex 2019 (of 3,672) | Binance.US 2023 (of 2,207) |
|---|---|---|---|---|
| 0.05 | 1 | 0 | 0 | 112 |
| 0.10 | 447 | 28 | 245 | 312 |
| 0.20 | 1,086 | 1,043 | 727 | 523 |
| 0.30 | 1,455 | 1,519 | 1,084 | 594 |

Max implied error at w = 0.1: 100 bps (2017), 84 (2018), 72 (2019), 209 (Binance.US).

**How to read it:**
- At a 5% share, only Binance.US, whose discount reached about 2,100 bps in one hour, breaks 50 bps in a material number of hours (112).
- At 10% to 30% all four episodes spend hundreds to over a thousand hours above 50 bps. A venue with a 20% to 30% share in an index with no filter would produce a deviation larger than 0.5% for hundreds of hours.
- This is arithmetic on the observed discount paths. It assumes the discount does not change with the platform's weight and that the other venues stay clean.

## 5. Limitations

- **Narrow index.** With three venues (two for Binance.US) the platform has a median volume share of 0.31 to 0.52. A wider index dilutes the bias (section 4) but also gives a median more clean venues to use. These results do not show how a median or exclusion rule behaves in a 10-venue index. Section 4 covers only the scaling of the naive bias.
- **Two venues is degenerate.** On Binance.US, median equals equal-weight and exclusion equals naive. The comparison is not informative for those methods. The Binance.US row shows only that the monitor and repair help and that "robust" averages cannot help when you have just one outside venue.
- **Benchmark.** The clean benchmark is built from Bitstamp and Coinbase. Where they disagree (2017), every index method inherits some error. The 2017 residual of roughly 200 to 330 hours ≥ 100 bps is this.
- **Repair is not better than filtering here.** It keeps the platform's volume and trades by a small leftover error, but it does not improve the hour counts. Its value would be in indexes where dropping the venue removes too much volume, which we do not test. It also needs a second-asset price on an external venue each hour.
- **The repair assumes the second asset sees the same dollar.** If the second asset moves for its own reasons (a token-specific shock), the subtraction is wrong. The flag condition (second asset agrees with L within 25%) guards against that but does not remove it.
- **Fallback.** If every venue is excluded, the hour falls back to naive. This happened for 0 to 3 hours per Bitfinex episode and 682 / 564 / 378 hours on Binance.US (k = 50 / 100 / 200).
- **Flag thresholds are those of the monitor** (100 bps, 25%); no tuning for this study.
- **Hours are hourly medians of traded minutes.** Hours with no trade on a venue use only the venues that traded.
- Oracle language: 50 bps is used only as an illustrative deviation level.
