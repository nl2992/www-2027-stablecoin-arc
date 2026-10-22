# Simulated Review (Reviewer 2), WWW 2027, Web Economics and Digital Society

Submission: "Same Name, Different Unit: Identifying Source-Specific Units in Web Price Fusion" (draft v7)
Reviewer profile: empirical finance, crypto microstructure.

## Summary

The paper models each source's price as a true price plus a source-wide "unit offset" plus an item residual. It identifies the offset from cross-item agreement and uses a "unit anchor" to separate a unit shift from source-wide demand. The anchor is an item whose true price is fixed in the true unit.

The central application is Bitfinex's 2018-19 bitcoin premium. The raw slope of the USDT/USD price on Bitfinex against the Bitfinex-Bitstamp bitcoin gap is 0.71. Netting out Tether's price on Kraken raises it to 0.97. A GMM version gives lambda-hat = 0.971 with a Hansen J that does not reject. The paper concludes that the premium was mostly a ledger-dollar discount, and that Tether's own discount had contaminated the raw anchor.

Binance.US in 2023 passes the same test (slope 1.00). Further material:
- a held-out-asset validation of a one-offset-per-source-hour correction;
- three locked fusion tests in which a plain median is hard to beat;
- an alarm monitor;
- a three-shock account of 2023 and a Chainlink pilot;
- a short Kimchi application in the Discussion.

## Strengths

1. The question is real and sharply posed. Is the Bitfinex premium a price of the venue's dollar or of the coin? The existing literature (Makarov-Schoar, Griffin-Shams, Flowerday et al.) leaves it open, and a quantitative decomposition would be a useful contribution.
2. The paper sees the main threat to its own anchor. A stablecoin carries a token component, so the raw anchor is contaminated. Equation (3) and Proposition 3.1 handle this explicitly, and the simulation (S4 versus S5, S7) shows what goes wrong without the netting. This is more careful than most work in the area.
3. Candour about weak results. The estimator ties the median. The J test has no power against a common depeg. HAC intervals undercover in the mixture scenario (0.72). The calm-year anchor slopes (0.83 to 0.87) are reported rather than hidden. Table 1 separates pre-registered, locked and post hoc items, which is rare and helpful.
4. Held-out assets, held-out time, a shared-dollar control (Coinbase-Bitstamp), per-asset and per-cell scores, and a note that pooled scores are dominated by XRP and 2019. The reproducibility apparatus (hashes, generated macros) is excellent.
5. The USDC 2023 decomposition (token -95.8 bps, ledger -2.4 bps) is a clean illustration that a token move and a venue-dollar move can be told apart on one exchange.

## Weaknesses

### Identification, the Kraken netting and the meaning of lambda

**W1 [MAJOR, STRUCTURAL] The netting does all the work and rests on an untestable assumption (A3).**
- Section 3.1, A3: "X measures x on a venue whose error is independent of (u, delta, epsilon, eta)".
- The netted slope is algebraically the raw slope minus the slope of X on L. So 0.97 = 0.71 + 0.256, and the reported "result" is that Kraken's USDT price falls by 0.256 bps per bp of Bitfinex premium.
- That the shortfall is a Tether discount, not source-wide demand that also hits the funding asset, is an assumption. It is not a finding.
- Bitfinex and Tether are affiliated. USDT on Bitfinex had its own redemption and credit channel, so the token component on Bitfinex need not equal Kraken's. T - X has a median of 5.4 bps and a correlation of 0.99, which is reassuring, but it is a diagnostic on the same assumption.
- The paper states that the correction "was specified after the raw slope of 0.71 was seen" (Table 1). It moves the estimate from 0.71 towards the hypothesis and is not registered. That is a forking-path concern, even if a plausible one.

**W2 [MAJOR, FIXABLE-WITH-ANALYSIS] The anchor is not clearly insulated from demand.**
- The model assumes demand "enters every non-anchor item and not the anchor" (Section 3.1).
- USDT is the funding currency of crypto on these venues. A stablecoin-funded buying or selling wave, or a flow-constrained dollar leg, moves USDT/USD on the venue too.
- On Binance.US this is acute. With deposits shut, USDT cannot be bought with USD, so USDT behaves like any other crypto asset. A slope of 1.00 and T near zero are then what you would expect from a common flow shock as much as from a unit shift.
- The paper's own sentence illustrates the problem: a closed on-ramp is "the mechanism behind such a shift, not an alternative to it". That is a definition of "unit" that absorbs limits to arbitrage.
- Needed: a second anchor that is not a funding asset (a fiat-pegged or non-USD item), or a placebo showing that a non-anchor crypto asset does not also give slope 1. Otherwise lambda = 1 is nearly mechanical when a very large common shock swamps everything else.

**W3 [MAJOR, FIXABLE-IN-TEXT] The interpretation of lambda is still too loose.**
- lambda is Cov(u,c)/Var(c). It is the regression-attribution of the time variation of the common offset, with the intercepts mu_k left free in the GMM moments.
- It is not "the share of the premium that was a unit". A persistent level of demand premium is absorbed by the intercept and is not identified.
- The text says "so about 0.971 of the offset, not all of it, was a unit shift". The abstract says the premium "was thus mostly a ledger-dollar discount". Both read as statements about levels or total variance.
- If demand co-moves with the unit, as in a panic where delta = kappa*u, lambda = 1/(1+kappa). Then lambda is not a share of anything additive.
- Assumptions needed but not listed in A1-A4: Cov(epsilon, u) = Cov(epsilon, c) = 0 (used for the OLS attenuation formula), and nu independent of u separately, not only of c (used in the proof).
- Recommended reading: lambda is the covariance share of u in c. Then say explicitly what it does not identify (the level) and what a positive Cov(u, delta) does to it.

**W4 [MAJOR, FIXABLE-WITH-ANALYSIS] Inference is thinner than the headline suggests.**
- The headline 0.97 is an OLS slope on 186 daily medians. The paper declares the bootstrap interval the headline because "the offset is persistent".
- Monthly blocks over a roughly 6-month window mean about six blocks. The "[0.94, 1.00] over months" interval is not credible, and the 2018 row (35 days) has no monthly interval at all.
- The formal test is an hourly GMM with rho = 0.995. Its HAC interval [0.961, 0.981] excludes 1, and the paper's own simulation shows HAC coverage of 0.72 under a mixture. So p < 0.001 for lambda = 1 is likely anti-conservative.
- The simulation DGP is the paper's own model, calibrated to this window. It cannot reveal misspecification, and the J test is conceded to be powerless against the main threat.
- Four instruments are listed, yet "ETH gap only" returns the same 0.971 to three decimals. Please clarify what the four are and why the estimates are identical.

**W5 [MAJOR, FIXABLE-IN-TEXT] The calm-year anchor slopes are unresolved and cut against the abstract.**
- Table 3 gives netted slopes of 0.87, 0.83, 0.84 and 0.86 in 2020-23, with intervals excluding 1.
- Table 2 shows the Bitfinex-Bitstamp daily correlation at 0.95-0.97 and the BTC gap accounting for 0.63-0.80 of the ETH gap in those years. So a common component exists but is not fully a unit.
- The paper says "we do not read those years as unit shifts, nor as demand". That leaves the common component unexplained exactly where the unit story is silent.
- A reader should conclude that the netted slope near 1 is a feature of the stress window and not of Bitfinex's dollar generally. The abstract should say so.

**W6 [MINOR, FIXABLE-IN-TEXT] Sample and window inconsistencies.**
- Stress-window hours: 4,461 of 4,464 (Section 4), 4,434 (Table 3), 4,433 (Table 4), 3,848 (Table 11).
- Binance.US: 4,582 hours (Table 4) against 797 (Table 11).
- Table 3's caption says hours where L, D and X all exist, while its medians use |L| >= 50. Please define each sample once.
- The anchor exists only from 2018-11-27. The premium started on 10 October 2018 and the 2017-18 episodes have no anchor, so "Bitfinex's 2018 to 2019 premium" is covered for only part of its life.

**W7 [MINOR, FIXABLE-IN-TEXT] Held-out validation tests additivity, not unitness.**
- Withholding assets shows that offsets are shared across assets, which Makarov-Schoar already documented as a common component.
- It does not show that the common component is a unit. The score is dominated by XRP and 2019, and the estimator ties the plain median (difference 0.000).
- The Coinbase-Bitstamp control shows a shared dollar leaves nothing to remove, which is expected, but it does not discriminate unit from demand.

### The Binance.US evidence

**W8 [MAJOR, STRUCTURAL] One episode, about 721 hours, a shock of -413 bps, and no power calculation.**
- Section 5.2 reports a slope of 1.00 and a residual of -3.5 bps. A 4% dislocation of both BTC and USDT, with T near zero, is nearly mechanical when the common shock dwarfs every other source of variance.
- Table 4's power is calibrated to the Bitfinex window and does not say what the test would reject on Binance.US.
- The netted and unnetted slopes are 1.008 and 1.009 (Table 4, Feb-Jul 2023). The netting is irrelevant, so this episode does not show the method works. It shows only that an enormous common shock gives slope one.
- The tight HAC interval [0.999, 1.007] with p = 0.11 is not credible for a roughly 60-day effective sample.

**W9 [MAJOR, FIXABLE-IN-TEXT] Asymmetric treatment of the two-anchor J failure.**
- The USDT + USDC specification gives J = 26.3 (p < 0.001) and is dismissed: "We do not read this as evidence about Binance.US".
- The reason given is that Bitstamp's USDC price was depegged. That is plausible, but the same logic would let a failing J be waved away anywhere.
- Meanwhile a passing J (p = 0.19 to 0.40, from a test conceded to have no power against a common depeg) is read as support. State the rule for which J results count before looking.
- Also, the monitor was "fitted on Binance.US in 2022-23" (Table 1), and Binance.US is also used as validation. The episode is not independent.

### The Kimchi application

**W10 [MAJOR, STRUCTURAL] The Kimchi application is too thin to carry its claim, and the "unit" is conceptually muddled.**
- It is one paragraph in the Discussion with no table. It is labelled "pre-registered" but gives no registration details.
- The anchor, USDT/KRW, "existed only from December 2023". The Kimchi episodes that matter (an 18.4% premium in 2017-18, 2021) have no anchor test.
- The only anchored result is a slope of 0.90 [0.86, 0.93] on 568 hours, in a window when the premium is small. The text reads it as "mostly a won-unit wedge with some residual".
- A KRW price versus USD is by definition a currency-conversion wedge. The Makarov-Schoar content is that capital controls prevent arbitrage of that wedge. A won balance is not "the same name, different backing"; it is a different currency with imperfect convertibility.
- USDT/KRW is itself a Kimchi-affected price, because Korean USDT trades at a premium. So it is not an item "fixed in the true unit". The official KRW/USD rate must be netted, and it is not described here.
- The finding that three assets' gaps correlate at 0.989 or more is expected from any common FX or premium factor. It does not identify a unit.
- The slope's CI excludes 1, and the 0.10 remainder is exactly where capital-control or demand stories would live. No discussion.

### Novelty versus Flowerday et al., and positioning

**W11 [MAJOR, FIXABLE-WITH-ANALYSIS] The incremental contribution is narrower than the framing.**
- The abstract says the test is of "a reading that Flowerday et al. (2026) could not test with their data", and Section 2 quotes them as saying the channel "cannot be tested directly". That is a claim about their data and design that cannot be checked from this text. It reads as a strawman unless the authors show that Flowerday et al. had no stablecoin or external-price data.
- The ingredients are standard: a common exchange-level component (Makarov-Schoar), stablecoin prices as a measure of a token's own discount (Lyons and Viswanath-Natraj, Ma-Zeng-Zhang), and a triangular parity.
- There is a direct simpler test the paper never reports: Bitfinex's own BTC/USDT against BTC/USD, with USDT/USD, decomposes the premium on-venue. The authors invoke triangular parity in Section 3 but do not use it. Show why the anchor regression adds anything.
- The additive source-plus-item model is admitted to be "not new" (median polish, two-way fixed effects). The statistical novelty is therefore the anchor, which is a plain IV with an external-price control.

**W12 [MAJOR, STRUCTURAL] The web-fusion framing and the contribution list do not match the evidence.**
- Title and abstract promise "Web Price Fusion". The fusion benchmark says a plain median is hard to beat. The method loses 4 of 9 columns, with errors up to 2.46 times the median (Table 6, STABLE X3, FDUSD), including on its own calm placebo.
- The estimator "adds nothing measurable to the plain median".
- The scope condition is described as "a pattern in a small sample, not an estimate".
- The paper then adds a monitor, a Chainlink pilot, a three-shock account and a Kimchi paragraph. It reads as several projects merged under a fusion title. The finance contribution (W1-W5) is the real paper, and it is not what the title advertises.
- The two-source fusion result (111.1 to 8.8 bps, Table 8) is mostly circular: the held-out venue is an "open-rail" venue by construction, and the unit-aware fuser lands at "about that of the open venue alone (8.5)". It effectively discards Bitfinex, using a prior about which dollar is true.

**W13 [MINOR, FIXABLE-IN-TEXT] Monitor results.**
- Table 7: Bitfinex has 12 episodes, 7 caught, 3 false alarms, which does not add up (10). Please explain how episodes are counted.
- Coinbase recall is 0 of 5.
- Labels were "compiled from public sources without reference to prices", but Table 1 admits that "Bitfinex's event windows had been seen".
- 7 of 9 on a hand-built 33-event list is a small basis for comparing rules. The fee schedule is partly from secondary sources.

**W14 [MINOR, FIXABLE-IN-TEXT] Presentation.**
- The paper is dense, with many numbers per sentence.
- Table 1's taxonomy is useful, but many results are marked post hoc (the anchor tests, CIs, grid, and the CRH and GTM rows).
- Section 5.3 "Per year and per asset" repeats the pooled caveats several times.
- Typos: "Binance.US.." and "Silvergate, Signature and USDC.." (double period). "PRoposition" and "PRoof".
- Appendix B and the Kimchi material depend on artifact files not visible to reviewers.

## Questions for the authors

1. Slope of X on L is -0.256. What do you expect it to be under the alternative that Kraken's USDT price partly reflects crypto-wide flow (a stablecoin-funded selling wave) and not only Tether-specific redemption risk? What data would distinguish them (on-chain Tether redemptions or mints, Bitfinex's BTC/USDT versus BTC/USD)?
2. Can you give the formal definition of lambda in the presence of Cov(u, delta) != 0, and say what Binance.US's 1.003 and Bitfinex's 0.971 are bounds on?
3. For Binance.US, how much power does the test have against "the whole venue is flow-constrained, USDT included"? What does the same regression give for a non-anchor crypto asset?
4. Why does ETH-gap-only IV give 0.971, identical to the four-instrument GMM? Which four instruments, and are they independent enough for J to be informative?
5. What is the official FX rate adjustment in the Kimchi result, and how do you separate a "won-unit wedge" from capital-control-driven arbitrage limits? What is the anchored slope in the 2017-18 and 2021 episodes?
6. What did Flowerday et al. lack that you have? Is it Kraken USDT data? Please state it concretely.
7. Why is the weekly-block interval, not the monthly one, reported alongside "headline" in the abstract (0.94 to 1.00 is the monthly interval)?

## Score and confidence

**Score: 3 / 5 (borderline).** The central question is good, the anchor idea is sound, and the self-criticism is unusually honest. But the decomposition result depends on one untestable netting assumption, the Binance.US and Kimchi evidence are much weaker than described, and the fusion framing does not match the findings. A tighter finance paper would be a clear accept; this version is a weak submission to a web conference.

**Confidence: 4 / 5.**

## The three changes that would most raise my score

1. **Make the identification defensible, and state lambda correctly.**
   - Redefine lambda as a covariance share of time variation. Say it does not identify the level of a demand premium.
   - Add a robustness check on the netting: a second external USDT price (Coinbase or Bitstamp USDT where the unit is stable), a Bitfinex BTC/USDT triangular test, and a non-funding-asset placebo anchor.
   - Replace the monthly bootstrap with something valid for roughly 6 effective blocks.
2. **Fix or cut the weak supporting evidence.**
   - Binance.US: add a placebo, a power calculation and a non-anchor comparison, state the J rule ex ante, and reconcile the hour counts.
   - Kimchi: either give it a full section with a table, an FX-netted anchor and the 2017-21 episodes, or remove it and keep a one-line pointer.
3. **Refocus the paper and sharpen novelty.**
   - Drop or move to a short appendix the monitor, the Chainlink pilot and the three-shock account.
   - Retitle around "ledger dollars on crypto exchanges".
   - Say concretely what Flowerday et al. lacked, and why the anchor beats the on-venue BTC/USDT decomposition.
