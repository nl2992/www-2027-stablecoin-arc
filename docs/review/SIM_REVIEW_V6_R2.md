# Simulated Review 2 (draft v6)

WWW 2027, track "Web Economics and Digital Society"
Reviewer 2: empirical finance, crypto market microstructure
Submission: "Same Name, Different Unit: Identifying Source-Specific Units in Web Price Fusion"

## Summary

The paper models each exchange's quoted prices as a common true price plus an exchange-specific "unit offset" (the value of that exchange's dollar) plus an item residual. It estimates the offset as a shrunken cross-asset median of exchange-to-reference gaps. To separate a unit shift from source-wide demand, it uses USDT as a "unit anchor". The anchor's price on the exchange is regressed on the offset. Kraken's USDT/USD price is netted out so that Tether's own discount does not contaminate the slope. A proposition and a Monte Carlo study back this with IV/GMM, HAC and block-bootstrap inference.

The headline empirical claims are these:

- Netting Kraken's USDT price raises the Bitfinex slope from 0.71 to 0.97 (stress window, 2018-11-27 to 2019-05-31). The paper reads this as "two discounts": one on Bitfinex's ledger dollar and one on Tether.
- Binance.US in 2023 is a "pure ledger-dollar shift" (slope 1.00).
- A one-offset-per-source-hour correction removes about a third to two-fifths of the cross-exchange gap on withheld assets in calm years.
- Across three locked fusion tests, a plain median is hard to beat. Unit-aware fusion wins only in the USDC 2023 test.
- A rule-based monitor of the offset is scored on 33 labelled events.

The paper is transparent about what is post hoc and what is locked, reports many null and negative results, and admits that the estimator "adds nothing measurable to the plain median". I appreciate that candour. But the core economic claim, that a Bitfinex premium was a ledger-dollar discount, rests on an exclusion restriction I do not find credible. The interpretation of 0.97 is not coherent with the signs in the paper's own tables. The Binance.US evidence cannot distinguish "unit" from "segmentation of the fiat on-ramp". The calm-year numbers are fragile and presented in the abstract more favourably than the dev-asset results justify. The novelty over Flowerday et al. (2026) is smaller than the abstract suggests.

## Strengths

1. The question is real and the data are public. Whether the 2018-19 Bitfinex premium priced the exchange's dollar or the coin has been argued since Griffin & Shams and Makarov & Schoar. A test, even a partial one, is welcome.
2. The distinction between a token move and a ledger move on the same exchange (USDC in March 2023 against Binance.US in June to July 2023, Fig. 2) is clean and well illustrated. Of the empirical findings, it is the one I find most convincing.
3. Explicit treatment of the Tether discount. The un-netted slope of 0.71 against the netted 0.97 shows why a naive anchor regression is biased. The simulation scenarios S4 and S5 make the same point.
4. Honest reporting. Examples are the Table 1 status taxonomy (pre-registered, locked, post hoc), the failed Hansen J with USDC, the 0.04 and 0.72 coverage problems in the mixture scenario, and the dev-asset score of 0.012 in 2020-23.
5. The held-out-asset protocol, with per-year and per-asset medians and longer blocks (Table 5), is more careful than most finance robustness sections. The shared-dollar control (Coinbase-Bitstamp) is a good idea.
6. Reproducibility: hashed manifests, macro-generated numbers, no hand-typed results.

## Weaknesses

### Identification of the anchor test (netting, GMM, Kraken)

**W1 (MAJOR). The exclusion restriction on the anchor is not credible for USDT on a crypto exchange (§3.1, Prop. 3.1; §3 "Unit anchor").**
- The identification needs the anchor to be untouched by source-wide item demand δ ("which moves the items and not the anchor"). In practice USDT is the crypto-side asset of the fiat-crypto boundary on every exchange.
- Source-wide demand for crypto funded in dollars (margin, on-ramp pressure, redemptions blocked by banking trouble) bids up USDT/USD on that venue just as it bids up BTC and ETH. USDT is a claim that settles in the crypto system, not an item fixed in the true unit.
- Hence Cov(η, δ) ≠ 0 is the natural case. The formal assumption is that Cov(η, c) = 0 with c = u + δ. This is stated, not argued, and it rules out exactly the alternative the test is designed to detect.
- A slope near 1 is then what you would see under a pure "scarce on-ramp / blocked arbitrage" story and under a pure "ledger dollar" story alike. The reverse placebo has 15 hours and an interval of −2.04 to 1.84, so it has essentially no power. It cannot be offered as evidence that the test discriminates on open rails.
- The distinction the paper draws, "unit" against "demand", collapses in the cases it cares about. A dollar that cannot be redeemed or deposited is, economically, a venue where fiat-crypto arbitrage is cut. I would expect the author to say what observable pattern would reject the unit reading with this anchor.

**W2 (MAJOR). Kraken as an independent reference requires more than "it traded" (§4, §3).**
- Assumption A3 needs the error of X to be independent of (u, δ, ε, η). The paper's support is 99.93% of hours traded and a 2.8 bps median gap between Kraken and Bitstamp bitcoin ("we take it as outside Bitfinex’s ledger").
- Neither addresses the relevant dependence. Tether redemption and issuance run through the iFinex/Tether nexus, and Kraken's USDT/USD price is pinned by arbitrage against Bitfinex's USDT/USD, which is the very market whose ledger is in question. So the x component in X is plausibly contaminated by Bitfinex's own shock through arbitrage flows. A3 would fail, and the sign of the bias is not obvious.
- "Traded" is not "liquid". USDT/USD on Kraken in 2018-19 was a thin fiat pair. Bid-ask bounce and stale last-trade prices enter ξ and are persistent at hourly frequency. The paper reports no spread, depth or volume statistics for the Kraken USDT book.
- The step from D − X = u + e requires u_Kraken = u_Bitstamp, because L is measured against Bitstamp while X lives in Kraken's dollar. Only the 2.8 bps bitcoin gap supports this. Kraken's own bank-rail risk is not discussed. A2 as stated covers only the reference.
- Only one outside anchor price exists. The second (USDC netted with Bitstamp) fails J at p < 0.001 (Table 4), and the author explains this away as Bitstamp's own USDC depeg. That dismissal is ad hoc: it was reasoned after the failure, and the same logic could apply to Kraken in an episode not yet noticed.

**W3 (MAJOR). Statistical evidence for "close to one" is thinner than the intervals suggest (§3.1 Inference, Tables 3 and 4).**
- The offset has ρ ≈ 0.995 hourly. The stress window is about 6.5 months and 186 days. The effective sample is a handful of independent regimes, and the 2018-11-27 start is dictated by data availability, not by design. The onset of the premium (October to November 2018) is not covered at all.
- The HAC interval of 0.961 to 0.981 is far narrower than the block-bootstrap interval of 0.94 to 1.00 on the same estimate. The simulation shows HAC covering at only 0.72 in the mixture scenario. Which interval should a reader believe? The paper reports both without reconciling them.
- The J test is stated to have size 0.03 when anchors load alike and "no power against a depeg that loads on c equally in every anchor". With K = 1 netted anchor in the headline case, the over-identification is across instruments, not anchors, so it tests the instrument set only. It says nothing about the exclusion restriction in W1. The headline J (p = 0.40) is thus weaker support than its prominence in the abstract suggests.
- The four-instrument and ETH-only GMM rows are identical to three decimals (0.971, [0.961, 0.981]). This is odd for a two-step GMM with different moment sets and needs explaining (collinear instruments? duplicated code path?).
- The instrument for L (Bitfinex-Coinbase ETH gap) shares the Bitfinex dollar by construction. If the Bitfinex-specific ETH quote has its own USDT-route component (ETH is largely quoted against USDT on Bitfinex), it also loads on the Tether component, and exclusion fails exactly as in W1.

**W4 (MINOR). Pre-registration claims are weaker than they read.** Table 1 admits that "the external-price test was specified before the Kraken file was downloaded, but not registered". The stress window, the choice of USDT, and the choice of bitcoin gap as L were all made after the Bitfinex episode and the prior 0.71 were visible. The anchor tests should be described as exploratory in the abstract, not just in Table 1.

### Economic interpretation of λ = 0.97

**W5 (MAJOR). λ is a variance-share regression coefficient, not "97% of the premium was a dollar discount" (§3.1, §5.2, abstract).**
- λ = Cov(u, c)/Var(c) is a covariance ratio on a persistent series dominated by a few large-gap weeks. It is not a decomposition of the level of the premium in basis points. Phrases like "about 0.971 of the offset, not all of it, was a unit shift" read it as one. A reader may take 0.97 as telling us Tether explained 3% of the premium. It does not.
- The "two discounts" conclusion appears to be inconsistent with the paper's own signs and magnitudes. Medians in the stress window are: L = +256 bps (Bitfinex dearer), D = +199 (Bitfinex USDT dearer in its dollar), T = −39, and X = −43 on Kraken. The Tether discount of about −43 bps works against D, not to widen it.
- Moreover, the netted slope of 0.97 says the Tether component contributes essentially nothing to the BTC/USD gap. The "Tether part" is read off as the shortfall between 0.71 and 0.97, which is by construction the covariance of X with L. It is not an additive contribution to the Bitfinex BTC/USD premium. The relevant level numbers (about 17% of 256 bps) do not match the 29% implied by 1 − 0.71 either. A decomposition table in basis points, with signs and standard errors, is needed before the claim "two discounts" can stand.
- The abstract says "slope close to one (0.97 ...)" and §5.2 says "we say close to one, not equal to one". Yet a rejection of λ = 1 at p < 0.001 under GMM is the paper's own result. The text oscillates between treating 0.97 as 1 and treating the 3% as meaningful. The author should commit to a tolerance.
- λ = 1 is an upper bound by assumption (no demand component). Any measurement or timing noise that is common to both L and D − X, such as simultaneous last-trade timing, would push λ toward 1 as well. §5.5's lead-lag checks are on the other pair and do not address this.

**W6 (MAJOR). Calm-year anchor slopes are unexplained (Table 3, §5.2).** The netted slopes for 2020 to 2023 (0.83 to 0.87) have intervals excluding 1 and excluding 0. The text says "we do not read those years as unit shifts, nor as demand". That leaves a large, statistically sharp, uninterpreted result inside a table meant to show the test works. Table 12 shows that in 2021 to 2023 only 21 to 28 hours have |L| ≥ 50 bps, so the slope is driven by tiny gaps, in which tick size, timing and Tether basis noise dominate. If the test has no meaning when gaps are a few basis points, say so and remove those rows from the argument. If it does, then the 0.83 to 0.87 values are evidence of a third component the model does not allow.

### Binance.US evidence

**W7 (MAJOR). Binance.US supports "segmented fiat rail", not specifically "unit" (§5.2, §5.7, Table 12).**
- With deposits suspended and withdrawals open (June to July 2023), the venue's dollar and its crypto were cut off from the arbitrage that keeps Binance.US prices tied to Bitstamp. A −413 bps gap in everything, USDT included, is exactly what a closed on-ramp implies. That is a limit-to-arbitrage result, not a result about what the "dollar" is.
- Calling it "a pure ledger-dollar shift" adds a label but no discriminating test. Slope = 1.00 is what both stories predict under W1.
- The sample is small: 721 hours at |L| ≥ 50, and 797 for all of 2023. The sample is thin, and depth on the BTC/USD and USDT/USD books of a US venue under regulatory stress is not documented. Candle prices from a market with wide spreads and sparse trades may not be informative.
- In this period Kraken's USDT price is near par, so X ≈ 0. The netting then does nothing, and the Binance.US row is just an un-netted regression of D on L. The "Formal test" estimate of 1.003 is therefore not independent confirmation of the netted method. Table 4 confirms this: the Feb to Jul 2023 estimate is 1.009 without netting and 1.008 with it.
- The one over-identification test that was run against a second anchor failed (J = 26.3, p < 0.001) and the reading was dismissed in a sentence. I would instead report that the Binance.US "pure unit" reading is supported by one anchor and rejected by a second, and let readers weigh it.
- The "USDT dislocation of −411 bps" next to L of −413 bps simply says USDT was priced like everything else on the venue. Under a "dollar scarce on a venue" reading that is an equilibrium outcome, not an identification of the dollar's backing.

### Calm-year results

**W8 (MAJOR). The calm-year headline selects favourable cuts and mixes stress and calm years (abstract, §5.3, Table 5).**
- The abstract says "by the median year (0.389) and median asset (0.378), about a third to two-fifths in calm years". But 0.389 is the median over five test years that include 2017 to 2019 (range 0.305 to 0.989), and 0.378 is a median across assets pooled over all years. Neither is a calm-year statistic. The calm-year numbers are in Table 5.
- Table 5, 2020 to 2023: test assets 0.353 (0.265 to 0.450), dev assets 0.012 (−0.001 to 0.082). The paper's own conclusion is "in calm years the correction helps on some assets and not on others". A pooled calm-year statement should be led by both numbers, and the dev-asset 0.012 should not be relegated to a footnote-level observation.
- The test-asset set (SOL, DOGE, ADA, LINK, XRP) trades differently from the dev set (ETH, LTC, BCH, ETC, XLM) in calm years and lists late. It is plausible that the gain reflects asset-specific microstructure (thin Bitfinex USD books for late-listed alts, Bitfinex's USDt-vs-USD routing) rather than a unit. The shared-dollar control scores 0.054 with CI [0.011, 0.102], so the "no unit" pair also gets a positive score. The control gap is about a sixth of the test-asset score, and the rest is unattributed.
- The estimator is indistinguishable from the plain cross-asset median b2 (Table 5: 0.353 against 0.356). So what is being validated is the existence of a common cross-asset component in a two-venue gap. A common component of a few basis points can arise from timing, from fee structures, and from quote-side effects. The "unit" label is attached by the stress-year story and not by calm-year evidence. In calm years the anchor, the only unit-specific evidence, gives 0.83 to 0.87 and an uninterpreted result (W6).
- Fee bands are from "secondary sources" (2 entries from dated news articles, 2 inferred, 4 unverified), and the claim that offsets "are not arbitrage opportunities" relies on them. Minor, but it should be in the limitations, not only in the data section.

### Novelty versus Flowerday et al. (2026)

**W9 (MAJOR). The "first test" claim is overstated relative to what is actually identified (abstract, §1, §2).**
- Flowerday et al. say the channel "cannot be tested directly" (§2, quoted). The present paper's test is not a direct test either. It is a test conditional on A1 to A4, in particular the anchor exclusion (W1) and Kraken's independence (W2). Claiming to deliver what the earlier paper called infeasible requires showing the added assumptions are weaker than the one that blocked them. The paper does not.
- The structural decomposition of a venue premium into a USD-side discount and a USDT-side discount through the same-exchange triangle (BTC/USD, BTC/USDT, USDT/USD) is an obvious arbitrage identity. Bitfinex trades all three legs. Prior work on Tether and Bitfinex (Griffin & Shams, Lyons & Viswanath-Natraj, the Tether-arbitrage literature) already treats the USDT basis as a separate price. The incremental step is netting by an outside venue, a single regression.
- The "Web price fusion" framing (additive source offsets, median polish, truth discovery) is, by the paper's own account, "not new". The fusion benchmark shows the estimator ties the plain median. Together, the net novelty is one regression in one application with a single outside venue, plus a negative result on fusion. A finance venue would ask for more. A web-track venue would ask what generalises beyond crypto, and the paper says "we have tested it only on crypto exchanges".
- Flowerday et al. cover four exchanges to mid-2021 and treat arbitrage at length. The paper does not show where its Bitfinex results differ from theirs or where its findings would change their conclusions for 2017-2021.

### Other points

**W10 (MINOR). The monitor evaluation is thin.** There are 9 Bitfinex positives, 7/9 recall, 0/5 on Coinbase, 4/4 on Binance.US (a rule fitted on Binance.US 2022-23). The trailing robust z-score has full recall on Bitfinex and the paper admits it "is the better rule at the high-recall end". The silence of the monitor around Silvergate and Signature is then read as support for the thesis ("only where rails closed with no substitute") from two episodes.

**W11 (MINOR). Causal language.** "The first test", "was therefore two discounts" and "was a pure ledger-dollar shift" read as established results, but they are conditional on assumptions the paper does not defend with data. Hedge accordingly.

**W12 (MINOR). Fusion scope.** The USDC 2023 win (0.72) is one episode. The same method loses on TUSD (1.33), FDUSD (2.46) and the calm placebo (1.32). "Scope condition" is a pattern in four episodes, as the Limits section admits.

## Questions for the authors

1. Please report, for the stress window, Kraken's USDT/USD median spread, depth and trade count per hour. Please also report the correlation of Kraken's USDT innovations with Bitfinex's USDT innovations at the minute level, to test arbitrage dependence (A3).
2. What observed pattern would have rejected the unit reading with USDT as the anchor? Can you give a case on a US venue with an open on-ramp where the slope is clearly not 1 and the placebo has power?
3. Use an anchor that is not a crypto-side claim: for example a gift-card or fiat-redeemable instrument, or EUR/USD-linked pairs, or a USD-quoted asset with an independent fiat price. Is there any, or is the test only valid for stablecoins?
4. Why are the four-instrument and ETH-only GMM estimates identical to three decimals? Which are the four instruments?
5. Reconcile the HAC interval (0.961 to 0.981) with the block-bootstrap interval (0.94 to 1.00). Which do you stand behind given the 0.72 coverage in the mixture scenario?
6. Please give the decomposition of the Bitfinex premium in basis points at its peak: ledger part, Tether part and residual, with signs and intervals.
7. What explains the 0.83 to 0.87 slopes in 2020 to 2023 if neither unit shift nor demand?
8. Re-estimate Binance.US with Kraken USDC or another independent outside venue for the second anchor. Does J still reject?
9. How does the calm-year score change if assets are matched on Bitfinex USD-book depth, or if hours are restricted to the highest-liquidity assets?
10. What is the specific claim of Flowerday et al. that you test, and does your result contradict any of their findings for 2017 to mid-2021?

## Score

**Overall: 2 of 5** (leaning reject; borderline for a finance venue, weak for a web venue). Confidence: **4 of 5**.

## Three changes that would most raise my score

1. **Defend or replace the anchor exclusion.** Show, on open-rail venues and in a placebo with real power, that a USDT-type anchor does not load on source-wide crypto demand. Better, find an anchor that is not a crypto-side claim. Without this, the "unit against demand" separation, the central claim, does not stand.
2. **Validate the Kraken netting and give a bps decomposition.** Report liquidity and dependence evidence for Kraken's USDT/USD price. Add a bps-level decomposition of the premium with signs and intervals, and reconcile it with the 0.71 and 0.97 figures and the HAC and bootstrap intervals. Also include the October to November 2018 onset.
3. **Reframe and narrow the claims.** Remove "first test", state the results as conditional on A1 to A4, and report calm-year results with the dev-asset 0.012 and the control 0.054 side by side. Treat Binance.US as consistent with a unit reading and with a segmented-rail reading, and explain the failed J. State clearly what is new relative to Flowerday et al. (2026).
