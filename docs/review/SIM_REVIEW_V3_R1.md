# WWW 2027, Web Economics and Digital Society: Review 1

Paper: "Which Dollar? Exchange Dollars as Exchange Rates in Web Crypto Prices" (8 pages plus appendices)

Reviewer background: web data integration, truth discovery, data quality. I am not a finance specialist, and I read the paper the way a data-integration researcher would.

Page numbers follow the 8-page layout of the submission PDF.

---

## 1. Summary

The paper argues that a crypto exchange's "USD" is a ledger balance that can trade away from a redeemable dollar. It models the log USD price of asset a on exchange v at hour t as p = p*_a + u_v + e_va (Eq. 1). Here u_v is an exchange-specific "dollar rate" shared by all assets on that exchange, and e is an asset-specific residual. The identifying idea is that gaps between two exchanges which agree across unrelated assets reveal u_v − u_r. Triangular parity (ETH/BTC on the same exchange) is offered as a check.

The estimator is the cross-asset median of gaps, shrunk toward zero by the cross-asset dispersion, with no correction when fewer than two assets are visible.

The empirical claims are these:

- (§5.1) Bitfinex had its own dollar rate in every year 2017–2023. Coinbase and Bitstamp "shared a dollar" after 2018.
- (§5.2) On five assets withheld from development, the estimator removes 85% of the mean-square Bitfinex–Coinbase gap. On a control pair it removes 0%.
- (§5.3) A monitor with a rule fixed in advance raises 0.43 false-alarm episodes per exchange-year on Bitfinex, against 1.29 for a plain price-gap alarm at equal recall. It flagged Bitfinex 6.5 months before the regulator disclosure.
- (§5.4) Three 2023 shocks are separated. The Binance.US dollar was at a ~557 bps premium for 530 hours. Silvergate and Signature produced no alarm. The USDC depeg moved the token, not the exchange dollar, and Chainlink BTC and ETH feeds did not inherit it.
- (App. A) A fusion experiment with injected unit bias.

## 2. Strengths

- The question is a real one. Aggregators and oracles do treat "USD" on different venues as the same unit. Framing a cross-venue gap as a shared-bias term plus an asset-specific term is clean.
- The paper is honest in several places. It reports that the headline 85% is driven by XRP and 2019, and that the estimator ties the naive cross-asset median. It reports that the control result partly reflects a "fewer than two assets" rule. It reports that every fuser fails when two of three venues share the bias. It reports the Coinbase 0/5 recall. This is better than most.
- Data are free and public. Acquisitions are hashed and the numbers are generated from logs. The reproducibility culture (§7) is a genuine plus.
- The Binance.US case (Tables 4–5) is carefully documented. It uses a second reference (Binance.com BTC/USDT × Bitstamp USDT/USD), hour-block bootstrap intervals, and a within-venue triangle check.
- The labelled-event file is published with the paper (Table 8). Labels were built without reference to prices, which is the right protocol.

## 3. Weaknesses

**W1 (MAJOR). The central identification does not separate an "exchange dollar" from any exchange-wide shock.**

- §3 states: "Assets that share no peg (bitcoin, ether and altcoins) have unrelated residuals." This is the whole identifying assumption, and it is false in crypto. Large-cap coins share a market factor and a common retail-demand factor.
- The same assumption fails for exchange-specific flows: premiums driven by US retail demand, per-exchange withdrawal or fee limits, and listing or delisting episodes. Any of these moves every asset on one venue at once.
- The paper's own Appendix B makes the point. Table 1 shows Coinbase–Bitstamp in 2017 with ρ = 0.98 and share = 0.92, so a common component is present. The Coinbase 2017 alarms are then scored as false alarms, with "we did not test this" (App. B) for the funding-friction explanation.
- Either the decomposition is right and 2017 Coinbase had a different dollar, in which case those are true detections, or those are demand premia and the method cannot distinguish them. Both readings are damaging.
- "Dollar" is a label for "common factor of cross-venue gaps". No independent evidence ties u_v to redeemability or banking access beyond event-date coincidences.
- Triangular parity is described as a check, but no result is shown. The identification section promises it and §5 never reports it.

**W2 (MAJOR). The diagnostic in §5.1 rests on two assets and on correlations dominated by level shifts.**

- Bitstamp lists only BTC and ETH. The "agreement across unrelated assets" is therefore agreement between BTC and ETH, the two most correlated large coins.
- The statistic is the correlation across days of daily-median gaps (Table 1). When one regime (e.g. 2019, median gap 41.7 bps) dominates a year, any two series sharing the regime correlate near 1.
- "Coinbase and Bitstamp shared a dollar" is inferred from the absence of a common component at 1–2 bps. That is a noise-floor statement, not evidence of a shared unit.
- The language is also confusing. "Shared a common component in 2017" means the two exchanges had different dollars, while "shared a dollar" later means the opposite.
- Three exchanges is a thin base for "evidence on which exchanges have their own dollar" (contribution 2).

**W3 (MAJOR). The held-out benchmark mostly shows that the estimator equals a median, and the control is vacuous by construction.**

- §5.2: "The estimator matches the plain cross-asset median." Final and b2 agree to within 0.002 on dev (0.445 vs 0.444) and test (0.846 vs 0.847). The 12-iteration loop, the shrinkage and the engineering added nothing measurable on this task.
- The claimed contribution is the control pair (0.000 vs −0.104). §6 concedes this "partly reflects the estimator’s rule of applying none when fewer than two assets". Bitstamp has only BTC and ETH, so with ETH withheld exactly one asset remains and the estimator returns zero by design. This is not evidence of discrimination.
- A real test would need a control pair with at least 3 assets visible (e.g. Coinbase and Kraken, or Coinbase and Gemini). Kraken is in the label set but is not used here.
- The headline 85% is "driven by XRP (97%) and by 2019 (99%)". The other four test assets lie between 27% and 40%. The test pool (0.846) is far higher than the dev pool (0.445), which suggests the test set is easier or period-confounded, not that the estimator generalises.
- Squared-error pooling over gap levels means one 2019 episode dominates the score. A median or per-year score would be more honest, and the per-year numbers (30–45%) are the real picture for 2020–2023.
- The "held-out" assets are held out only in the asset dimension. They are the same exchanges, the same time range, and the same events as development, and they are corrected using the same dev assets as inputs. Assets also share residual common factors (XRP, DOGE, SOL and ADA are the same altcoin beta). This is leave-one-asset-out, not out-of-sample.
- Per-asset b1 and b2 for the test assets "were not recorded", yet pooled values are reported. This is odd.

**W4 (MAJOR). The monitor's detection claims are weakly supported and partly internally inconsistent.**

- The monitor (§5.3) is a rule of a ≥100 bps BTC gap plus a second-asset agreement. It does not use the shrinkage estimator at all, so §5.3 does not test §3.
- The headline comparison (3 vs 9 false alarms, recall 7/9) rests on 9 labelled events and a handful of alarms. No confidence intervals are given, and "a third the rate" is a count ratio of 3/9.
- Table 3 on Coinbase shows recall 0/5 for the monitor. The monitor is therefore blind to every Coinbase event, and the abstract does not say so.
- Binance.US: both methods have 1 false alarm and 4/4 recall, with 1.31 vs 1.26 per year. The same count over the same exposure should give the same per-year rate. This looks like an exposure inconsistency to be explained.
- The label counts do not reconcile with Table 8. Table 8 lists 8 non-confounder Bitfinex rows (including a restoration), but recall denominators are 9. Coinbase has 4 non-confounder rows but the denominator is 5. The rule for how events become recall targets, and the matching window, are not defined.
- The "6.5 months before regulators disclosed" claim is framed as early warning. But Table 8 includes a Bitfinex "bank partner loss" dated 2018-09-30 and a deposit pause on 2018-10-11, bracketing the 2018-10-08 flag.
- The Bitfinex premium was publicly visible and widely discussed at the time. It is not shown that the plain price-gap alarm did not fire on the same date, and with equal recall it probably did. The lead time is not attributable to the decomposition.
- The "rule fixed in advance" (100 bps, a quarter of the size) was chosen by authors who had already seen the 2018–19 Bitfinex and 2023 Binance.US data. Fixed in advance of the evaluation code is not the same as fixed in advance of the data.

**W5 (MAJOR). The 2023 case studies are largely unfalsifiable or unneeded.**

- Binance.US with deposits shut and withdrawals open traded at a 557 bps premium. A plain BTC price gap, with no decomposition, shows this immediately. The decomposition adds only the statement that USDT and BTC move together, which is circular for a stablecoin priced in the same venue dollar.
- The Silvergate and Signature result is a null: "The monitor raised no alarm on Bitfinex, Coinbase or Binance.US in March 2023". The paper then treats the null as informative (the dollar did not dislocate where rails kept a substitute).
- But a monitor that fires means dollar failure, and one that does not fire also confirms the story. The narrative is not exposed to refutation. This is the same monitor that scored 0/5 on Coinbase.
- Each of the three shocks is one episode (N = 1). The §6 limits admit "The oracle check covers one episode and one oracle family."

**W6 (MAJOR). The oracle result does not support the framing, and the positive control undermines the test.**

- The null is a slope near zero (0.007) on the depeg size. The stated alternative is "a slope near one", but the positive control, the USDC feed itself, has slope 0.140, which "responded as expected". If the positive control reaches only 0.14, the criterion "near one" is not the right yardstick, and the 0.007 vs 0.14 contrast needs power or interval estimates.
- Feed errors are measured against "minute prices". It is unclear whether these come from the same venues the feed aggregates, in which case the error measures aggregation noise. Chainlink heartbeat and deviation thresholds create staleness that is not modelled.
- The finding that major feeds did not inherit the depeg is a robustness finding about Chainlink. It argues against the problem the paper motivates, not for the tool the paper proposes.
- The DAI feed rests on 5 hours.

**W7 (MAJOR). Appendix A contradicts the Discussion's recommendation.**

- §6 says a feed should "correct with the exchange’s rate rather than drop the exchange". Table 7 shows the unit-aware median and unit-aware cluster identical to the plain median (12.9 replay, same everywhere).
- With the b2-unit variants, errors are worse (335.6 vs 12.9 in replay). The appendix itself says "Unit awareness adds information (which exchanges share a dollar), not accuracy."
- The experiment uses a synthetic constant bias, BTC and ETH only, three exchanges, on development assets. It is not evidence for a deployed correction rule.
- A recommendation to "correct" with the estimated rate is therefore unsupported, and the fusion comparison with truth discovery is token (a "CRH-style" reimplementation).

**W8 (MINOR). Data handling choices are mismatched and under-explained (§4).**

- The diagnostic uses an hourly median of traded-minute closes, while the benchmark uses the last traded close in each hour. For thinly traded alts, a last close can be nearly an hour stale, so asynchronicity noise leaks into the "asset-specific residual".
- Two different price constructions are used for two parts of the same argument, and no sensitivity is shown.
- Quote-currency issues are not discussed (USD vs USDT or USDt pairs, particularly on Bitfinex in 2017–2019).

**W9 (MINOR). The paper is built around a few exchanges and mixes spans.**

- Binance.US data cover 2022–2025, while the headline exchanges cover 2017–2023. Kraken and Gemini feature in labels but not in analysis.
- Several claims ("throughout", "in every year") apply to one exchange pair.

**W10 (MINOR). Presentation.**

- The paper is packed to 8 pages with four contributions, three tables of results in the main text, and key support in appendices. Several definitions are missing from the text (matching window for recall, exposure for per-year rates, how the "ledger component" is computed for non-BTC legs).
- Table 5 uses "L (via BTC)" and "T = D − L" without the formula in the main text.
- The title promises "which dollar", but the paper concedes (§6) that prices alone cannot say which unit is the U.S. dollar.

## 4. Questions to the authors

1. What evidence distinguishes an exchange-dollar shift from an exchange-wide demand or flow shock that moves all assets at once? Can you show a case where all alts moved together on a venue and no banking event occurred?
2. Please report the triangular-parity check promised in §3 as a result, with numbers.
3. Why is the control pair Coinbase–Bitstamp, which has only two assets, given that the estimator makes no correction below two assets? Can you rerun on a pair with at least three shared assets?
4. How was the dev/test split of assets chosen, and by whom? Were the test assets' listing dates and volumes checked against the dev assets?
5. Why do the Binance.US monitor and plain price-gap rows have the same count (1 false alarm) but different per-year rates (1.31 vs 1.26)?
6. Please reconcile the recall denominators (Bitfinex 9, Coinbase 5) with the non-confounder rows in Table 8. Please also define the matching window.
7. Did the plain price-gap alarm also fire on 2018-10-08 or earlier? If so, the 6.5-month lead time is not a property of the decomposition.
8. If the 2017 Coinbase alarms are real dollar differences under your own Table 1, why are they scored as false alarms?
9. What is the power of the Chainlink test, given the positive control slope of 0.14 rather than one? What is the benchmark price source, and is it independent of the feed's source set?
10. Which 3 of the 12 loop iterations were kept, and what did each change in the estimator? What exactly is the estimator's gain over a plain median, other than the less-than-two-assets rule?

## 5. Venue fit

Weak to moderate for this track. The paper is a market-microstructure and monitoring study of three crypto venues. The "web" element is that the inputs are public candle feeds and that aggregators and oracles consume them.

- There is no web-scale data, no system, no data-integration algorithm evaluated on varied web sources, and no user or society dimension beyond a regulator-disclosure anecdote.
- The Web Economics and Digital Society framing would be stronger if the paper showed an operational aggregator or oracle consuming the output, or measured how many deployed feeds mix units.
- I would expect this paper to be at home in a finance or financial-technology venue. A fit argument for WWW would need to be made explicitly. The current text makes none.

## 6. Novelty versus truth-discovery and oracle literature

**Truth discovery.** The model p = p* + u_v + e is a two-way additive (source plus object) model. This is the classical row-plus-column fixed effects model, and the median-of-gaps estimator is essentially Tukey's median polish with James-Stein shrinkage. A per-source additive bias shared across all objects is a known notion in source calibration and sensor fusion.

- The truth-discovery citations (TruthFinder, CRH, Dong et al.) are used as a strawman: "These methods model reliability per source." Numeric truth discovery with source bias is a long-standing line. Examples are Gaussian truth models, confidence-aware methods, and systems that model per-source bias and variance and source copying.
- Dong et al. already treat source dependence. The paper's "structured special case" claim is not made precise. Appendix A shows the unit-aware fusers are no better than a median, so the comparison does not show an advantage over this literature.
- "Source bias across entities" is a modest generalisation of work on semantic or unit heterogeneity in data integration. It is not engaged with.

**Finance and oracles.** The unit-in-the-venue idea has strong precedents. These include the law-of-one-price and crypto-premia literature (Makarov and Schoar, Borri and Shakhnov, and the cited Flowerday et al., who explicitly discuss a discount on Bitfinex dollar balances). Triangular arbitrage in FX is another precedent. So is the "implied USD" computed from a stablecoin or crypto cross rate.

- The specific incremental step is the hourly cross-asset estimate and the monitor. That step is thin: the estimator ties a median.
- The oracle contribution is one null result on one oracle family, against Liu et al. and Nadler et al.

Net novelty: a nice conceptual framing, small technical novelty, and an empirical record that is partly descriptive.

## 7. Does the "autoresearch loop" add anything, or is it p-hacking?

In the submitted text, the loop appears as a single paragraph under "Development loop": a bounded loop of 12 iterations, 3 kept and 9 discarded, with smoothing, Kalman filtering, reliability weighting and liquidity weighting tried and rejected.

- Scientifically it adds little. It documents how the estimator was tuned, and the end product is statistically indistinguishable from the plain median (W3). A reader learns that sophistication did not help, which is the opposite of what a method contribution needs.
- It is not obviously p-hacking in the strong sense. The count of trials is small and disclosed, it was run on a dev split, the test split was scored once from a recorded log, and the control pair is a good idea in principle.
- The remaining forking paths are outside the loop. They include the 100 bps and quarter-size monitor thresholds, the choice of Bitstamp as the reference, the choice of which assets are dev and which are test, the choice of squared-error pooling, and the choice of a two-asset control.
- Test set scored once is a fine practice, but a "once" claim is self-attested and was run by the same authors who chose the split. No pre-registration or third-party commitment is offered.
- I would drop the process narrative from the main text, or turn it into an honest ablation table showing the estimator is a median plus one safeguard.

## 8. Is the held-out benchmark convincing?

No, not as presented.

- It holds out assets only, not time, exchange pairs or events.
- The headline is driven by one asset and one year.
- The estimator equals the naive baseline.
- The control is vacuous by construction.
- The dev-to-test difference (44% to 85%) is unexplained and may reflect period composition.
- A convincing version would hold out exchange pairs and time (train 2017–2019, test 2020–2023), report per-year and per-asset medians instead of pooled squared error, include a control pair with at least three shared assets, and compare with a fitted factor model, not just the naive median.

## 9. Scores

**Overall: 2 (weak reject)**, on the scale 1 (strong reject) to 5 (strong accept).

**Confidence: 4** (confident in the data-integration and truth-discovery assessment; less certain on finance-literature novelty).

## 10. The three changes that would most raise my score

1. **Fix the identification and the control.** Show that the common component is a unit, not an exchange-wide demand or flow shock. Report the triangular-parity result. Add a control pair with at least 3 visible assets so that the zero correction is earned. Resolve the 2017 Coinbase contradiction (alarm vs false alarm).
2. **Rebuild the held-out evaluation.** Hold out time and exchange pairs, not just assets. Report per-year and per-asset results in place of pooled squared error. Show the estimator beating a simple median or fitted factor baseline with intervals, or admit the contribution is the diagnostic, not the estimator.
3. **Make the monitor evidence rigorous and make the fit to WWW explicit.** Define the recall matching window and reconcile Table 3 with Table 8. Show whether the plain price-gap alarm also fired on 2018-10-08. Give confidence intervals on the false-alarm comparison. Either demonstrate a consuming aggregator or oracle where the unit label improves an outcome, or reposition the paper so that the web-data-quality contribution (an unit label for feeds) is argued, tested and not only asserted.
