# WWW 2027, Web Economics and Digital Society: Review of "Same Name, Different Unit: Identifying Source-Specific Units in Web Price Fusion" (draft v7)

Reviewer 1. Background: web data integration, truth discovery, data quality.

## Summary

The paper argues that fusion services (price aggregators, indexes, oracles) assume all sources quote in one unit. Sources can instead carry a source-specific "unit offset", for example a crypto exchange whose "USD" is a ledger balance. The offset is shared by every item the source reports.

The paper models prices as true value plus source-unit offset plus item residual (Eq. 1). It identifies the offset through cross-item agreement (a median with a James-Stein-style shrinkage, Eq. 2). It separates unit shifts from source-wide demand using a "unit anchor": the stablecoin USDT, netted against its price on an outside venue (Kraken). Proposition 3.1 gives an IV/GMM identification result. A Hansen J test and a calibrated simulation (Table 4) accompany it.

Empirical findings:
- The Bitfinex 2018-19 stress window gives an anchored slope of 0.97 (0.71 before netting Tether's own discount). Binance.US 2023 gives 1.00.
- The correction removes a large share of the cross-exchange mean-square gap on withheld assets: 0.846 pooled, but only about 0.35 to 0.4 in calm years.
- Across three "locked" fusion tests, a plain median is hard to beat. Unit-aware fusion wins only on the USDC run (0.72 of the median's error).
- A threshold monitor for exchange-dollar dislocations, scored on 33 labelled events, plus a 2023 account of three shocks and a Chainlink pilot.

## Strengths

1. The question is well posed. The paper separates an error shared by all of a source's claims from per-claim noise and from reliability. It correctly notes that truth-discovery methods do not model this.
2. The external-price correction is a good idea. The anchor is itself a claim, so it carries its own error. Netting an outside price and showing the bias in simulation (S4 versus S5, Table 4) is careful, and the 0.71 to 0.97 movement is striking.
3. The honesty is unusual and welcome. The paper states that the estimator ties the median. It reports a null on the main fusion comparison, and the negative STABLE results (X2, X3, X4). It flags J's lack of power against a common depeg. Table 1 separates pre-registered, locked and post hoc results.
4. The empirical hygiene is high: hashed inputs, per-year and per-asset breakdowns, block lengths, a shared-dollar control (Coinbase-Bitstamp), and a placebo.
5. The scope condition in §6 ("keep the median unless a shared unit can move") is practical advice, even if thinly supported.

## Weaknesses

**W1. MAJOR, STRUCTURAL. The fusion contribution is not established, and the paper's own evidence cuts against it.**
- The title and venue pitch is "Web Price Fusion". Yet the estimator "adds nothing measurable to the plain median" (§3).
- In the locked tests (Table 6) the new method beats the median clearly in one of nine cells. That cell is X1 (USDC, 0.72), which is one episode. It loses on T2 (1.50), X2 (1.33), X3 (2.46) and X4 (1.32).
- The "narrow and positive scope condition" (§5.4) is a post hoc reading of that single win, stated as a finding. §6 admits it is "a pattern in a small sample, not an estimate."
- What remains is a diagnostic for one asset class, not a data-fusion advance.

**W2. MAJOR, FIXABLE-WITH-ANALYSIS. The fusion method is never defined.**
- §3 specifies only the offset estimator (Eq. 2). Table 6 and Table 8 score a "unit-aware fuser", a "Method of this round", an "Earlier unit-aware method (frozen)" and "Unit-aware, one vote per unit".
- None is described in the main text. How the offset enters the fused price, how weights are set and how the reference is chosen are all absent.
- The headline claim of a drop from "111.1 to 8.8 bps" (§5.4) cannot be evaluated or reproduced from the paper.
- Whether the estimate uses the scored reference venue's gaps is also unclear. If it does, that is leakage.
- A fusion paper needs an algorithm box and a complexity discussion.

**W3. MAJOR, FIXABLE-WITH-ANALYSIS. Identification rests on assumptions that the paper cannot test and partly acknowledges.**
- The anchor is assumed unaffected by source-wide demand δ. §5.2 itself raises "stablecoin-funded buying" as a demand channel, and that channel would hit USDT directly.
- The exclusion restriction Cov(η,c)=0 in A4 is similarly untestable. J has "no power against a depeg that loads on c equally" (§3.1).
- A3 requires Kraken's USDT error to be independent of Bitfinex's unit. Yet Tether's issuance and redemption are tied to Bitfinex (the paper cites Griffin and Shams), and Kraken has its own ledger dollar (A2 assumes a stable reference unit).
- The result "rests on Kraken's USDT price being outside Bitfinex's ledger" (§5.2). That is an assumption, not a test.
- The "true unit" is never defined. It is the reference venue's unit, so λ is a relative quantity.
- Please state precisely what λ = 0.97 means. It is a covariance share, not "97% of the premium".

**W4. MAJOR, FIXABLE-IN-TEXT. Inconsistent evidential standards across the key tests.**
- On Bitfinex, λ=1 is rejected at p<0.001 (HAC 0.961 to 0.981). The text then reads the result as "close to, not equal to, one". Yet the abstract and conclusion say the premium was "mostly" a ledger-dollar discount.
- Binance.US netted gives 1.008 with a CI excluding one (Table 4). The same table shows a 1.009 estimate un-netted, so the correction does nothing there.
- The abstract nonetheless says the offset "passed the same test (slope 1.00)".
- The second-anchor GMM (USDC) fails the J test (p<0.001). This is dismissed post hoc as a contaminated Bitstamp USDC price.
- A reader will count this as one pass, one failure explained away, and one test that is uninformative about the netting.

**W5. MAJOR, FIXABLE-WITH-ANALYSIS. The post hoc correction and the "360 specifications fixed in advance" claim sit uneasily together.**
- Table 1 states the external-price correction "was specified after the raw slope of 0.71 was seen". The headline result is therefore a researcher-degree-of-freedom outcome.
- The 360-specification grid then reports a range of 0.970 to 1.013. That range is stable across the grid, but the grid varies reference venues and windows, not the post hoc design choice itself. An alternative anchor, or none, is never tried.
- Calm-year slopes are 0.83 to 0.87 with intervals excluding one. §5.2 says "we do not read those years as unit shifts, nor as demand." That leaves the mechanism unexplained in 4 of 6 years.
- The 2018 slice is only 35 days, with a raw slope of 2.06.
- The simulation (Table 4) is calibrated to the same linear model it tests. Coverage is poor under realistic mixtures (HAC 0.72 in S3, 0.01 in S4, 0.72 in S7), so the stated precision is overstated.

**W6. MAJOR, FIXABLE-WITH-ANALYSIS. Held-out validation is weaker than it sounds.**
- The estimator has one tuned constant (c), so "held-out assets" tests almost nothing that is learned.
- The score is "indistinguishable from the plain cross-asset median" (§5.3, difference 0.000).
- The test result is driven by XRP (97%) and by 2019 (99%). Dev assets in calm years give 0.012.
- The assets are crypto tokens quoted on the same two exchanges, so they are not independent items. The "unrelated residuals" assumption in §3 is untested.
- The Coinbase-Bitstamp control scores 0.042, which supports "shared dollar", but that is a sanity check of the model, not validation of the method.

**W7. MAJOR, FIXABLE-WITH-ANALYSIS. Truth-discovery baselines are weak or strawmanned, and the related work is thin on the data-integration side.**
- CRH and GTM are applied to two sources, where "the median, CRH and GTM coincide" (§5.4, Appendix A). In the two-source setting that is the point, but it says nothing about the claim that CRH and GTM miss unit effects.
- No bias-aware or calibration-aware method is compared. Examples are source-bias models, multi-sensor calibration and unit or format harmonisation in data integration, or a simple per-source fixed-effects regression that estimates the shift jointly across items.
- The paper concedes that "the additive form is not new" and that it resembles median polish and two-way fixed effects. The truth-discovery, unit-harmonisation and schema-matching literatures are barely cited.
- On the finance side the paper is stronger than on the CS side.

**W8. MAJOR, FIXABLE-IN-TEXT. "Locked", "pre-registered" and "scored once" overstate.**
- Table 1 states the monitor rule "was fitted on Binance.US in 2022-23, and Bitfinex's event windows had been seen." That is not pre-registration.
- The fusion tests were chosen with prior knowledge of the events. FUSE, STABLE and the estimator went through 24, 15 and 12 development iterations on related episodes, and the withheld episodes were then selected after the 2023 events were known.
- Several of the reported contrasts (CRH and GTM rows, operating curves, fee bands) are post hoc, as the paper says. The abstract should not rely on the locked framing.

**W9. MINOR (borderline MAJOR), FIXABLE-WITH-ANALYSIS. The monitor evaluation is tiny.**
- There are 9 Bitfinex positives. Recall is 7 of 9, and 0 of 5 on Coinbase. The paper reports "fewest false alarms of the price-threshold rules" at matched recall of at least 0.85.
- With n of 9 and 5, no confidence intervals are given.
- The trailing robust z-score "is the better rule at the high-recall end" (§5.6), so there is no uniform winner.
- The monitor and the 2018 timeline are largely detached from the unit-identification thread, and the label list was compiled by the authors.

**W10. MINOR, FIXABLE-IN-TEXT. Scope creep and process leakage.**
- The paper contains an estimator, a GMM theory, three fusion tests, a monitor, a 2023 case study, a Chainlink pilot, fee bands, lead-lag checks and a Kimchi paragraph, all in 11 pages. Many are covered in two or three sentences.
- Internal labels leak into the text: "Method of this round", "Earlier unit-aware method (frozen)", "FUSE", "STABLE", "UNIT-TD", "The development loop kept 3 changes and discarded 9", and a macro-module list in §7. Reviewers should not have to decode a research log.
- The Kimchi application (§6) has a 568-hour anchor window and is not credible as evidence for generality.

**W11. MINOR, STRUCTURAL. Generality and venue relevance are asserted, not shown.**
- The claim that the approach "applies to platform credits, multi-currency marketplaces and loyalty points" is explicitly "tested only on crypto exchanges". Every dataset is exchange prices, mostly BTC/ETH, from three or four venues.
- A web-scale source-integration setting is absent: no many-source experiment, no non-financial data, no scalability analysis.

**W12. MINOR, FIXABLE-IN-TEXT. Presentation and statistics details.**
- The estimator constant c is "fixed on development assets" but re-picked at 0.25 on 2017-19 data "with the same scores".
- Table 5 gives intervals with calendar-month blocks, and the text notes that week blocks are "too optimistic". Please use the longer blocks as the default everywhere.
- Hour counts differ across Table 3 (4,434), Table 4 (4,433, 4,434) and Table 11 (3,848), for reasons given only in table captions.
- The conventions are confusing (u>0 means discount of the source's unit, gaps negative for premium).
- Fee bands rest on secondary sources: "2 are inferred from them and 4 are unverified."

## Questions for the authors

1. Please define the unit-aware fuser(s) completely. How many are there? Is the offset used to adjust a source's price or to reweight it? Which hours and which reference gaps enter it? Is the scored reference venue ever visible to the offset estimator?
2. If the claim is "a plain median is hard to beat", what is the practical case for the method over a median plus a monitor, especially when the monitor itself needs the same offset estimate?
3. How sensitive is the 0.97 to the choice of anchor? What happens with USDC on Bitfinex (if listed), with a different external USDT venue, or with an anchor that is explicitly not on the same ledger family? Why is the Kraken price outside Bitfinex's unit when Tether-linked flows connect them?
4. How do you rule out stablecoin-funded demand hitting the anchor (violating "demand enters non-anchor items only")? Could you show an identified demand shock, for example a Bitfinex margin or fee event, that moves BTC and not USDT?
5. For Binance.US, the un-netted and netted estimates agree. What does the correction add there? For USDC, J rejects. Do you retract the claim that the netting fixes the two-anchor case?
6. In what way are CRH and GTM given the offset structure? Would a source-fixed-effect model fit jointly across items, or a bias-aware truth-discovery method, change the comparison?
7. How was the label list protected from the author's knowledge of price gaps, given that "Bitfinex's event windows had been seen"? Please report recall confidence intervals.
8. Are there non-crypto datasets (e.g. marketplace prices across currencies, or FX-affected e-commerce) where the unit model can be tested even at small scale?

## Venue fit

Partial. The track covers web economics and digital society, and crypto-market integrity fits that description loosely. The connection to the web is thin, because the data are exchange candle prices, not web-extracted claims. The paper's CS contribution (fusion algorithm, truth-discovery comparison) is the weakest part. The identification and empirical-finance content would suit a finance venue, and a WWW audience would want either web-scale source integration or a clearer systems or data-quality angle.

## Novelty

Moderate on the identification side, and low-to-modest on fusion.
- The unit-anchor-with-external-price correction is a neat, not-entirely-obvious idea, and the formal treatment (IV/GMM with J, simulation) is more careful than most.
- The additive source-offset model is standard (the authors acknowledge this).
- The claim that Bitfinex's premium priced its dollar is a finance finding that substantially extends the cited Flowerday et al., but it is not a data-integration contribution.
- The fusion benchmark mostly yields a negative or near-null result.

## Score and confidence

**Overall score: 2 (weak reject; below the threshold for WWW as submitted).**
**Confidence: 4** (confident on the truth-discovery and fusion side, and reasonably confident on the econometrics).

## The three changes that would most raise my score

1. **Define the fusion method and show a real win.** Give a full algorithm and ablations. Then show it improves fused prices on a larger and more varied set of sources and episodes, with data chosen before the method. Alternatively, drop the "fusion" framing and sell the paper honestly as a unit-identification and diagnostic result. In that case, cut the benchmark and monitor material and reposition for a better-fitting venue.
2. **Make the identification case self-consistent and stress-tested.** Show an identified demand shock that leaves the anchor unmoved. Add at least one more independent anchor or external venue for Bitfinex. Apply one statistical standard across Bitfinex, Binance.US and USDC, covering rejected λ=1, failed J, and un-netted equals netted. Report the post hoc decision as a limitation of the headline number, not as a robustness grid.
3. **Strengthen baselines and the generality claim.** Add bias-aware or calibration-aware truth-discovery and fixed-effects baselines. Cover the data-integration literature on unit and schema harmonisation. Run at least one non-crypto web dataset with multiple sources and a known unit or currency shift, and ideally many more sources than three.
