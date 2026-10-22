# Review of "Same Name, Different Unit: Identifying Source-Specific Units in Web Price Fusion" (WWW '27, Web Economics and Digital Society)

Reviewer 1. Expertise: web data integration, truth discovery, data quality. I am not a market-microstructure specialist, so I judge the finance claims by their internal logic and not by who has said what.

## 1. Summary

The paper argues that fusion services (aggregators, indexes, oracles) assume every source quotes in one unit. Sources may in fact share a name ("USD") but not a backing. A crypto exchange's "dollar" is a ledger claim.

The authors model each source's log price as a true price, a source-wide unit offset and an item residual (Eq. 1). Agreement of gaps across unrelated items identifies the offset. A "unit anchor" (USDT) separates a unit shift from source-wide demand. Because USDT carries its own token discount, they net out its price on Kraken. They then estimate the slope of the corrected anchor gap on the cross-item offset by IV/GMM, with a Hansen J test, HAC inference and a simulation study.

The main empirical claims are:

- **Bitfinex 2018-19.** The slope rises from 0.71 to 0.97 after netting. The premium was therefore "two discounts", one on the ledger dollar and one on Tether.
- **Binance.US 2023.** The slope is 1.00, a pure ledger-dollar shift.
- **Held-out assets.** One offset per source-hour removes about 0.85 of the squared Bitfinex-Coinbase gap on withheld assets pooled, but only 0.35-0.45 in calm years, and about 0.01 on the dev assets.
- **Fusion.** Across three "locked" fusion tests the plain median is hard to beat. Unit-aware fusion won once clearly (USDC 2023, 0.72 of the median's error).
- **Extras.** A monitor, a Chainlink pilot, fee-band arguments and a 2023 shock narrative.

## 2. Strengths

- The central observation is real. A shared-by-all-claims source error is not what reliability-weighted truth discovery models. The distinction between an item-level error and a source-level unit is worth stating to the web-integration community.
- The paper is unusually honest about negative results. It says the estimator "adds nothing measurable" over the plain median, that CRH and GTM tie it, that the median wins on most episodes, and that J has no power against a common depeg. I rarely see this, and it should be kept.
- Pre-registration and locked-evaluation bookkeeping (Table 1) is good practice. Reporting held-out scores per year and per asset, with longer bootstrap blocks, is better than most applied papers.
- The external-price correction (Eq. 3) is a sensible idea. Showing in simulation that omitting it biases the slope by about -0.25 (S4 against S5) is a useful, clean demonstration.
- The reproducibility apparatus (hashes, manifests, scripted rebuild) is strong.

## 3. Weaknesses

### MAJOR

**M1. The contribution to web data integration is thin and overclaimed (title, abstract, §1, §6).**
The method is an additive source-effect (median-polish) model plus a placebo/IV test on crypto exchange quotes. The paper concedes "the additive form is not new" (§2). It concedes the estimator is "indistinguishable from the plain cross-asset median" (§5.3). Both fusion tests that matter then show the unit-aware fuser losing to the median on 6 of 9 episodes in Table 6. What remains is a diagnostic about three or four exchanges. The framing as "Web Price Fusion" with "platform credits, multi-currency marketplaces and loyalty points" (§6) is pure assertion: "we have tested it only on crypto exchanges."

**M2. Identification rests on assumptions the paper cannot test, and the one test it offers is admitted to be powerless on the key threat (§3.1).**
J "has no power against a depeg that loads on c equally in every anchor", so "the netting by X is what removes that bias, not the test."
- The correctness of the headline 0.97 therefore depends on A2 (reference unit constant) and A3 (Kraken's USDT error independent of the Bitfinex unit, demand and noise).
- A3 is implausible exactly in the episode studied. Tether redemption stress and capital flows hit Kraken's USDT/USD and Bitfinex's demand together. Griffin and Shams, which the paper cites, make that point.
- "Kraken's own bitcoin price stayed close to Bitstamp's" (§4) does not establish that Kraken's *USDT* price is unaffected by the common shock. The robustness check is on the wrong series.
- Cov(x,c) is allowed to be nonzero, yet X's measurement error is assumed independent of c. If Kraken's USDT price also absorbs part of Bitfinex's ledger stress, the netted slope is biased in an unknown direction.

**M3. The Bitfinex "two discounts" conclusion is not supported at the stated precision (§5.2, abstract).**
- The abstract says "slope close to one (0.97...)". The formal GMM test rejects λ=1 at p<0.001, with HAC interval 0.961-0.981. The block bootstrap gives 0.94-1.00 over months, and the Table 3 interval over weeks for 2018 is 0.91-1.04. The paper uses the bootstrap to say "includes one" and the HAC test to say "not all of it".
- The interpretation then draws a substantive economic split (ledger discount versus Tether discount) from the gap between 0.71 and 0.97. That gap is attributed to Tether's discount via an identity that holds approximately by construction. T≈X (corr 0.99) means the netting mechanically moves the slope toward one, since D-X ≈ L whenever T≈X.
- It is unclear what falsifiable alternative the 0.97 excludes.
- Calm years give 0.83-0.87 with intervals excluding 1, and the paper declines to interpret them: "we do not read those years as unit shifts, nor as demand" (§5.2). That is a hole in the story. The same machinery returns a number that is neither of the two hypotheses it was built to separate.

**M4. Persistence and the near-unit-root problem are not handled, and the simulation does not show that they are (§3.1, Table 4).**
- Hourly offsets have ρ̂=0.995, and the Table 3 regressions use 186 daily observations with overlapping regimes.
- HAC and moving-block bootstrap with ρ this high are known to under-cover. The paper's own S3 coverage of 0.72-0.78 against a nominal 0.95 confirms it. Yet the headline intervals are reported without a caveat.
- The text never says whether the simulation DGP reproduces the persistence, the regime heterogeneity or the fat tails of the real offsets.
- Size at S1 is 0.08, not 0.05. J has size 0.03 when depeg loadings are equal and power 0.48 when they differ (S7). So the key diagnostic is weak in the very scenario the paper is built around.

**M5. The simulation validates the estimator under its own model, not the model (§3.1, Table 4).**
Scenarios S1-S7 are all linear, additive, calibrated to the same stress window as the application, and generated from A1-A4. They show that IV is consistent when IV's assumptions hold.

What is missing:
- Violations of A3 (correlation between Kraken's error and c).
- Heterogeneous or time-varying item loadings (γ≠constant).
- Item-level demand that is correlated across assets (the obvious alternative: crypto-wide risk appetite acting on a leveraged venue).
- An anchor whose own error is correlated with demand.

Calibration to the target window also invites circularity. The "convincing" part of the simulation is mostly S4 versus S5 (netting removes a bias that was injected by hand).

**M6. The "locked" fusion benchmark does not support the scope condition drawn from it (§5.4, Table 6, Table 1).**
- There are nine episodes across three tests. The method of this round beats the plain median on 5 of 9 (T1 0.93, T3 0.95, T4 0.97, T5 0.97, X1 0.72). It loses on four, badly on T2 1.50, X3 2.46 and X2/X4 1.33/1.32.
- It is not the best method in most columns where it wins: CRH (0.88 in T1, 0.82 in X2) and the oracle beat it.
- On this evidence, "the scope condition is therefore narrow and positive" is a pattern read off one winning episode (USDC 2023). The text elsewhere calls it "a pattern in a small sample, not an estimate" (§6).
- The abstract nevertheless presents the USDC result as the finding.
- The "Earlier unit-aware method (frozen)" row and "Method of this round" show the fuser was revised after earlier locked runs (FUSE 24 runs, STABLE 15 runs). Each new round that reuses overlapping episodes spends the test set, and a single-pass lock per round is not a single-pass lock per paper.
- X4 "failed the method's own check", so the check did not protect the user. A scope condition the method cannot itself diagnose is of limited use to an aggregator.

**M7. Truth-discovery positioning and baselines are inadequate for this venue (§2, §5.4, App. B).**
- Only TruthFinder, CRH, a Gaussian truth model (GTM) and Dong et al. are cited.
- Missing are methods that model *source bias*, not just variance. These include biased-source and trend/offset models, copy detection, and the knowledge-fusion and entity-resolution line on unit/currency normalisation of numeric attributes.
- CRH/GTM are run with trailing 30-day reliabilities on 2-3 sources. With two sources they "coincide" with the median (App. B), so they are not a real test. A truth-discovery baseline with a per-source additive bias term is the obvious competitor, and it is absent.
- The paper compares against a straw version of "truth discovery" (variance-only) and then reports that nothing beats the median. That does not demonstrate a gap in the literature.

**M8. The held-out score measures commonality, not units (§5.3, Tables 5, 10, 11).**
- The score is the share of a withheld asset's Bitfinex-Coinbase squared gap predicted by other assets' gaps. A common crypto-demand factor (risk-on flow into a leveraged venue) gives exactly the same result.
- The shared-dollar control (Coinbase-Bitstamp) near zero shows that two US-banked venues have no common component, which is expected. It does not rule out demand as the common component for Bitfinex.
- The abstract reports "about a third to two-fifths in calm years" using the test assets (0.353) and median-of-years. The same table gives 0.012 for the dev assets in 2020-23. The paper discloses this in §5.3 but not in the abstract.
- The pooled 0.846 "is driven by XRP (97%) and by 2019 (99%)". The abstract headline of "most of the gap in the stress years" is largely a one-year, one-asset result, and month-block intervals (0.484-0.933) are wide.

**M9. Venue fit and scale (all).**
All evidence comes from 3-5 sources and 2-9 assets. The WWW audience will ask about web-scale integration, with hundreds of sources or items. The paper never shows the method on any non-crypto data, though it claims generality twice. See Section 5 below.

### MINOR

**m1. Dilution.** The monitor (§5.6), the 2023 shocks (§5.7), the Chainlink pilot, the fee bands (§5.5) and the 2018 timeline are separate mini-papers. The monitor's own evidence: recall 7/9 on Bitfinex, 0/5 on Coinbase, and the robust z-score "is the better rule at the high-recall end" (§5.6). The Chainlink slope bound is uninformative: "We did not measure s" (§5.7). They distract from the unit-identification argument and add unverified claims (secondary-source fee schedules: 4 "unverified").

**m2. Pre-registration is compromised in its own account.** Table 1: "the rule was fitted on Binance.US in 2022-23, and Bitfinex's event windows had been seen." The labels were compiled "without reference to prices", but the researcher had seen the windows. 33 events is a small base for the monitor claims.

**m3. Inconsistent sample sizes.** The same Bitfinex stress window has 4,434 hours (Table 3), 4,433 (Table 4 GMM) and 3,848 (Table 12), explained only by a table note ("up to the hours in which Kraken traded"). The Kraken market traded in 99.93% of hours, so 3,848 against 4,434 needs a clearer account.

**m4. Estimator (Eq. 2).** A James-Stein-style positive-part shrinkage with a constant (c=1/2, re-picked as 0.25) fixed on development assets, followed by "we claim no optimality" and "adds nothing", is baggage. Either drop it for the median or show when it matters.

**m5. Binance.US.** A slope of 1.00 over about 100 days with a -413 bps median offset is close to a mechanical identity. The BTC gap and the USDT price are both measured against the same Bitstamp dollar during a rail closure. The second-anchor test fails (J=26.3) and is waved away as "contaminated" by Bitstamp's USDC depeg. That is plausible but is an unverified excuse for a failed over-identification test on a positive result.

**m6. Appendices.** The headings for Appendix C (held-out scores by asset, full anchor table) and Appendix D (the 2023 shocks) have no body text in the review copy, though §5.7 refers to them ("Figure 2b, Appendix"). Tables 11 and 12 appear, but D does not. The submission is 11 pages, and I could not tell which is main text and which supplementary.

**m7. Reproducibility section.** Much of it describes build hygiene (macros, stale-number tests, page-limit gate) rather than data or code access for reviewers. "Ships with the artifact" is not an anonymous link.

**m8. Wording.** "Dollar" is used both for the unit and as a stand-in for the exchange. "Ledger dollar" versus "bank dollar" is never defined formally, so the central object (the unit u) is a fitted residual with a label, not an observed quantity.

## 4. Questions for the authors

1. Can you show A3 holds: how does Kraken's USDT/USD move with the Bitfinex offset in periods where Bitfinex banking is not in question? A placebo of the netted slope on a venue with a known intact ledger would help.
2. Which alternative hypothesis, if true, would give a netted slope well below 1 and is it excluded? What would a pure risk-on demand shock on a margin-heavy venue look like in Table 3? An anchor that is demand-insensitive but not Tether (for example a fiat-redeemable coin on a different issuer) would be informative.
3. Does the simulation reproduce ρ≈0.995 persistence and the realised coverage failure of HAC in the application? Why is S3 coverage 0.72 not a problem for the headline interval?
4. For the claim that unit-aware fusion "won when a large group of sources shared a unit that moved": is there any way to *predict* this from the data before scoring, since X4 failed the method's own check?
5. Please run a truth-discovery baseline with a per-source additive bias parameter. Does it recover the Bitfinex offset in T1 and USDC X1?
6. What would the method do on a non-crypto data set (for example product prices with currency conversion errors, or a multi-currency marketplace)? Even a small non-crypto experiment would test the "Web" claim.
7. Why is a three-venue panel enough to claim a "first test"? Flowerday et al. say the channel "cannot be tested directly"; the paper's test is direct only if A2-A3 hold.

## 5. Venue fit

The track is "Web Economics and Digital Society", which is a better home than the data-integration or web-mining tracks, but fit is still partial. The finance content (exchange premia, stablecoin runs, bank-partner events) is the actual subject. The "web" element is that the quotes are public and hourly. The proposed generalisation to platform credits and loyalty points is not studied. A web-data-integration audience will want multi-source scale and a baseline from the truth-discovery literature, neither of which is present. A finance audience will read the identification section as a standard IV argument and look for stronger institutional validation of the anchors. The paper sits between the two and satisfies neither.

## 6. Novelty versus the literature

**Truth discovery and data fusion.**
- The additive source-effect idea is acknowledged as old (median polish, two-way fixed effects).
- Source bias and heterogeneous-unit handling already exist in numeric truth discovery and in data-fusion work on unit and currency normalisation. The paper does not engage them.
- The new element is the anchor-based identification of the unit component. That is a reasonable idea, but as formalised (Proposition 3.1) it is a standard IV ratio. The proof is three lines, so the formal novelty is small.

**Oracles.** Liu et al., Nadler et al. and Schwenkler et al. are cited fairly, but the Chainlink analysis here is an upper-bound regression on one episode with unmeasured s. It adds little.

**Finance.**
- The Bitfinex premium and Tether channel are well studied (Griffin-Shams, Lyons-Viswanath-Natraj, Makarov-Schoar, Flowerday et al.).
- The claimed first test is the external-price netting, which is a modest, plausible refinement. Its strength depends on A2-A3 and the claim is stated more firmly than the evidence allows.
- The Binance.US 2023 and USDC-token versus ledger distinction is a nice illustration but a single-episode descriptive result.

## 7. Are the formal test and simulation convincing?

Partly.
- The algebra of Eq. (3) and Proposition 3.1 is correct under A1-A4, and the netting argument is clear.
- The problem is that A2 and A3 carry the entire empirical weight, are untestable by J, and are not stress-tested in the simulation. The simulation also shows poor coverage (0.72 for GMM HAC in S3, 0.05-0.11 under S4 and S7) and J power that collapses when loadings are equal.
- There are two independent inference procedures (HAC and block bootstrap) that disagree on whether 0.97 differs from one, and the paper does not reconcile them.
- No finite-sample check is given for near-integrated regressors.
- I would accept the identification result as a clean statement of conditions, not as evidence that the 0.97 and 1.003 are unbiased estimates of a unit share on real exchanges.

## 8. Overall assessment

**Score: 2 (weak reject; below the acceptance threshold).**
**Confidence: 4 (confident; I know the integration side well, the finance side less so).**

The idea is worth a short paper and the honesty is commendable. But the contribution to web fusion is limited by the authors' own admission, the main empirical claim leans on an untestable netting assumption, and the fusion benchmark yields one win and a lot of ties and losses. The paper reads as an economics application with a data-integration title, padded with side analyses.

## 9. The three changes that would most raise my score

1. **Stress-test the identification.** Add simulations and empirical placebos that violate A3 (a Kraken error correlated with c, a demand factor correlated across assets, time-varying loadings), calibrated to the real persistence. Reconcile the HAC and bootstrap results on 0.97, and either test or drop the "two discounts" decomposition. Use a second independent anchor or a venue-level placebo with a known-intact ledger to show the netted slope is not mechanically near 1.
2. **Make it a real data-integration contribution.** Add strong truth-discovery baselines with per-source additive bias (and source-dependence handling) and run them on several sources. Add at least one non-crypto, many-source dataset (for example multi-currency marketplace prices or commodity/FX quotes with unit errors) where the unit shift is verifiable. State a predictive rule for when to correct, and check it ex ante on fresh episodes.
3. **Cut and focus.** Remove or move the monitor, fee-band, Chainlink and timeline sections. State the abstract claims at the strength the evidence supports: GMM rejects both 0 and 1 for the Bitfinex slope; the held-out results are concentrated in XRP and 2019; the dev-asset calm-year score is about zero; the fusion winner is one episode. Report the unit share as an interval with the bootstrap and HAC reconciled, and complete the appendices.
