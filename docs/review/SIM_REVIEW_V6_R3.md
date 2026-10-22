# Simulated review (Reviewer 3, methodology / statistics / evaluation / reproducibility), WWW 2027

Submission: "Same Name, Different Unit: Identifying Source-Specific Units in Web Price Fusion" (draft v6)

## Summary

The paper models each source's prices as true prices plus a source-wide "unit offset" (Eq. 1). A cross-item agreement estimator recovers the offset (Eq. 2). A "unit anchor" item, USDT, is used to separate a unit shift from source-wide demand. The anchor's exchange price is netted against an external venue's price (Kraken). Proposition 3.1 shows that an IV or GMM slope of the netted anchor on the offset equals a "unit share" lambda. Two-step GMM with a Hansen J-test and a simulation study (Table 4) back this up.

Empirically, Bitfinex's 2018 to 2019 premium is said to be "two discounts" (lambda about 0.97 after netting, 0.71 before). Binance.US in 2023 is said to be a "pure ledger-dollar shift" (slope 1.00). The paper then reports four further exercises:

- A held-out-asset evaluation. The estimator ties a plain cross-asset median.
- A locked three-test fusion benchmark (UNIT-TD, FUSE, STABLE) in which the plain median is hard to beat.
- A monitor scored on 33 labels.
- A discussion of the 2023 shocks and a Chainlink pilot.

The paper is unusually candid about null results and about what was fixed when (Table 1). Reproducibility tooling is strong. However, the identification argument rests on assumptions that conflict with the paper's own motivating story. The headline inference rests on essentially one episode with very persistent series. The estimator adds nothing over a median. The fusion benchmark is a small-sample negative result that is then turned into a "scope condition". Too many loosely connected exercises compete for the page budget.

## Strengths

1. **Honest reporting of nulls.** Examples include "The estimator adds nothing measurable to the plain median, which we report plainly." (§3), the dev-asset calm-year score of 0.012 (§5.3), and the failed J-test and X4 placebo. This is rare and valuable.
2. **Provenance discipline.** Table 1 separates pre-registered, locked and post hoc items. This is better than most applied fusion papers.
3. **The external-price correction is a sensible idea.** Netting an outside price from the anchor (Eq. 3) addresses a real confound. The raw-versus-netted contrast (0.71 versus 0.97) is clear and checkable.
4. **A simulation exists at all.** It includes uninformative, contaminated-anchor and noisy-regressor cases (Table 4, S4 to S7). It shows OLS attenuation and the bias from an un-netted depeg.
5. **Control pair.** Coinbase to Bitstamp (shared dollar) behaves like noise (Table 2, Table 11). This is a useful negative control for the diagnostic.
6. **Reproducibility.** Public data, hashed manifests, causal-estimator checks, and numbers generated from logs (§4, §7).

## Weaknesses

### Identification proposition and assumptions

**MAJOR 1. Exclusion (A4) conflicts with the demand alternative the paper tests.**

- The alternative reading in §5.2 is "stablecoin-funded buying". That is exchange-specific demand for the stablecoin anchor itself.
- Such demand moves D on the exchange. It is not removed by netting Kraken's X, because it is exchange-specific.
- It therefore enters eta and violates Cov(eta, c) = 0 in A4. It is also inconsistent with the setup statement that demand "enters every non-anchor item and not the anchor" (§3.1).
- Under this violation the slope of (D minus X) on L is biased toward 1. A "unit" reading and a source-wide funding or transfer-friction wedge then look the same.
- Related point: a source-wide wedge from blocked withdrawals (Binance.US 2023) also moves USDT on that venue one-for-one. The slope-1 result cannot distinguish "ledger-dollar unit" from "limits to arbitrage on that venue". "Unit" is effectively defined operationally as "whatever moves every item including the anchor". The paper should state this, or add an assumption and a test that would distinguish the two.

**MAJOR 2. Gaps in the proof and the assumption list.**

- Cov(Y, Z) = gamma Cov(u + eta, c) requires Cov(nu, u) = 0. A4 only states that nu is independent of (c, eta, epsilon). Independence from c = u + delta does not give independence from u alone.
- The instrument Z = gamma c assumes unit and demand load identically on the instrument item (e.g. the ETH gap). If demand has item-specific betas, so that Z = gamma_u u + gamma_delta delta + nu, IV identifies a gamma-weighted mixture, not lambda.
- Lambda = Cov(u, c)/Var(c) is a regression coefficient. It equals "the unit share" only if Cov(u, delta) = 0, and the paper does not say so. A "unit share of 0.971" is not interpretable as a share without that.
- A3 (the Kraken error xi independent of everything) and A2 (constant reference unit) are asserted, not tested. Kraken carries its own dollar. X = x + u_Kraken + xi, which A3 omits. Different reference venues are used for L (Bitstamp) and X (Kraken).
- The typesetting glitches "PRoposition" and "PRoof" suggest the section was edited late. A two-line proof for the central result is too thin; the full algebra should be in an appendix.

**MAJOR 3. The effective sample is roughly one episode.**

- The stress window is a single 22-day run plus a few months (§5.7), with hourly offsets at rho = 0.995 (§3.1). Daily or hourly regressions of one persistent series on another have very few effective degrees of freedom and a spurious-regression risk.
- Table 3 has "–" when there are fewer than five blocks for the monthly bootstrap.
- The paper itself shows that longer blocks widen intervals (§5.3).
- The HAC interval [0.961, 0.981] is much tighter than the bootstrap interval [0.94, 1.00] on the same data. Table 4 shows HAC under-covers in the mixture case (see below). The abstract should not lean on the tighter number.

### GMM, J-test and simulation calibration

**MAJOR 4. The J-test cannot support the weight put on it.**

- The paper admits J "has no power against a depeg that loads on c equally in every anchor" (§3.1).
- Table 4 shows J rejects only 0.03 of the time when every anchor's depeg loads alike. It rejects 0.48 when loadings differ, which is weak power.
- Observing J = 2.94 (p = 0.40) is therefore weak evidence of anything.
- The USDC extension fails J = 26.28, and the paper dismisses this as a contaminated second anchor. That reasoning is plausible but post hoc. A valid-anchor claim cannot be made from one passing and one failing specification.
- The degrees of freedom are inconsistent. The text gives chi-squared with Km-1 df. Table 4 says "5 df". Table 4's bottom block says "4 instruments" with J = 2.9 (p = 0.40), which matches 3 df. The instruments are never listed, so the reader cannot reproduce the test.

**MAJOR 5. The simulation is calibrated to the same window it validates, and size is off.**

- Wald size for lambda = 1 is 0.08 (S1) and 0.09 (S5), and for lambda = 0 it is 0.08 (S2), all nominal 0.05.
- HAC coverage in the mixture (S3) is 0.72, and the paper notes the block bootstrap is "no better there (0.77)". The real data are almost certainly a mixture, since the paper itself concludes lambda is not exactly 1 (§5.2).
- The simulation does not test violations of A3 and A4: a persistent Kraken offset, exclusion failure through exchange-specific USDT demand, or item-specific demand loadings. These are exactly the threats in Weaknesses 1 and 2.
- S7 varies only the loading of the depeg across anchors.
- The data-generating process (persistence, innovation distribution, how the "calibration" was done) is not described in the main text.
- There is no sensitivity of the headline estimate to a plausible violation, for example a bound on Cov(eta, c) for which lambda remains at least 0.9.

**MINOR 6. Sample counts are inconsistent.**

- Bitfinex stress hours are 4,434 (Table 3), 4,433 (Table 4) and 3,848 (Table 12).
- Binance.US is 4,582 hours (Table 4) against 797 or 721 hours (Table 12).
- The text says 4,461 of 4,464 hours for Kraken. A reader cannot tell which filter produces which sample.

**MINOR 7. The calm-year anchor results are left in an awkward place.**

- Netted slopes are 0.83 to 0.87 with narrow intervals excluding 1 (Table 3, 2020 to 2023). The text says "we do not read those years as unit shifts, nor as demand" (§5.2).
- Either the identification does not apply to calm years, which limits the method to large episodes, or it does and rejects pure units there. The paper cannot have it both ways. A threshold on gap size at which the test is informative should be stated and justified.
- The 2022 and 2023 rows of Table 3 list 8,753 hours, while Table 12 has 25 to 28 large-gap hours for the same years.

### Evaluation design and uncertainty

**MAJOR 8. The held-out-asset "validation" does not validate the unit model.**

- The score is the share of the Bitfinex to Coinbase gap that other assets' gaps remove. This is a common-factor fit. Any common wedge, demand or unit, would pass.
- The paper shows the estimator equals the plain cross-asset median b2 (difference 0.000, interval -0.003 to 0.002; Table 11). Contribution (2) in §1, "Held-out validation", therefore tests that a median predicts gaps, not that those gaps are a unit.
- The test and dev asymmetry is large and driven by composition. The pooled test score is 0.846 against 0.441 for dev. The test score is "driven by XRP (97%) and by 2019 (99%)" (§5.3). The abstract nonetheless quotes medians (0.389, 0.378) and "about a third to two-fifths in calm years". Calm-year dev assets score 0.012 and the interval includes 0.
- Test-asset 2017 to 2019 has only 7,388 hours. The "most of the gap" claim for stress years rests on a few assets and a few months.
- Intervals are bootstrap intervals over weeks. The paper itself shows month or quarter blocks widen them (0.484 to 0.933), yet the headline intervals still use weeks.

**MINOR 9. Several post hoc comparisons carry no multiplicity treatment.** Table 11 reports about 40 intervals. LINK has a negative delta with an interval excluding 0, and the shared-dollar control has a positive delta with an interval excluding 0. These are read informally, with no correction and no pre-specified effect size.

**MINOR 10. The monitor evaluation rests on very few events.** Recall is 7/9 on Bitfinex and 4/4 on Binance.US (Table 7). The monitor achieves 0/5 recall on Coinbase and raises 8 false alarms. The robust z-score reaches full recall with fewer false alarms at the high-recall end (1.15 against 3.44). On Binance.US the monitor's 1.31 per year is slightly above the price-gap alarm's 1.26. No intervals are given. The headline "removes two thirds of its false alarms" is 3 versus 9 episodes. The episode counts in Table 7 do not reconcile with recall plus false alarms (Bitfinex: 12 episodes, 7 caught, 3 false; price gap: 18, 7, 9; z-score: 38, 9, 20). The monitor has little to do with identification and could be cut (see page use).

### Fusion benchmark

**MAJOR 11. The benchmark is a negative result that is converted into a positive "scope condition" from a single win.**

- Across FUSE (5 episodes) and STABLE (4 episodes), the method wins on T1 (0.93, behind CRH at 0.88 and the drop-deviant rule at 0.89) and X1 (0.72). It loses on T2 (1.50), X2 (1.33), X3 (2.46) and X4 (1.32), and is near 1 elsewhere. The paper itself says "the scope condition is a pattern in a small sample, not an estimate" (§6).
- The abstract's "Unit-aware fusion won when a large group of sources shared a unit" is based on one event, USDC March 2023, with a gain of 0.72 against 0.77 for the simple convert-units baseline.
- Ratios of mean absolute errors are reported with no uncertainty. Hours within an episode are highly autocorrelated, so even the 0.93 in T1 has no interval.
- The "oracle" is worse than the median on X3 (4.04) and X4 (2.02), so it is not an oracle in any useful sense. This should be renamed or explained.
- Baselines are weak for this setting. CRH and GTM are applied to three or four sources with one continuous claim each, a regime where they degenerate (Table 9 shows they coincide with the median at two sources). The obvious stronger baselines are not run: a trailing per-source bias subtraction (median polish or two-way fixed effects, which the related-work section acknowledges as the same additive form), and a robust trimmed mean.
- The "Earlier unit-aware method (frozen)" row implies that earlier rounds were scored on the same episodes. If so, the episodes are not "never seen" for the method of this round.
- CRH and GTM rows on UNIT-TD are marked as post hoc, and the conclusion "a plain median was hard to beat" in the abstract blends locked and post hoc evidence.
- Truth is Kraken, but Kraken also supplies the anchor's external price X. The "never entered fusion" claim does not hold across the paper's two uses, and shared Kraken-specific errors would favour agreement.

### Specification search

**MAJOR 12. Researcher degrees of freedom around the central claim.**

- The anchor correction was introduced after the raw slope 0.71 was seen. Table 1 admits "the external-price test was specified before the Kraken file was downloaded, but not registered".
- The window (start 2018-11-27 and end 2019-05-31), anchor (USDT), reference (Bitstamp), instrument (the Bitfinex to Coinbase ETH gap), aggregation (daily medians), block lengths (weeks and months), and the "large-gap hours" threshold (50 bps) are all analyst choices on a single event, with no robustness grid.
- The development loops (12, 24 and 15 runs, with 3, 5 and 5 kept) are disclosed, which is good. But the shrinkage constant and estimator remain "fixed on development assets" while the downstream claims are post hoc on the same data.
- The monitor "rule was fitted on Binance.US in 2022 to 23, and Bitfinex's event windows had been seen" (Table 1), which weakens the claim of pre-registration for the monitor's recall on Bitfinex. The 33-event label set was "compiled from public sources without reference to prices" but the compiler had seen the Bitfinex windows.
- The label set is of the authors' own making, with no inter-rater check, and includes "confounders" whose classification affects false-alarm counts.

### Figures and tables

**MINOR 13. Presentation of figures and tables.**

- Figure 1 uses symmetric-log axes that are hard to read, and the shading ("labelled banking episodes") is not identifiable in the PDF text. The right panel's year colouring does not convey the main point.
- Figure 2 legends show raw variable names ("PDUSDT", "PDBTC", "PDUSDC"), and the dates on panel (b) are garbled.
- The central result, the netted slope, has no figure. A scatter of (D minus X) against L by regime (stress, calm years, Binance.US) with the 45-degree line would carry the paper's main claim in a glance.
- Table 3 has 11 columns of mixed units and is dense. Table 12 duplicates Table 3's first slope with different hours and a different interval (0.71 [0.56, 0.88]), which invites confusion.
- Table 6 mixes three tests, two metrics, and a "†" convention. Bold is not visible in the review copy. Table 5 repeats the same rows for the re-picked constant.
- Notation drifts. "L" is the offset estimate in §3 but the Bitfinex to Bitstamp BTC gap in Table 3. "T" is both a token residual and a test-episode label in Table 6. "b1, b2" are undefined in the main text.

### Clarity

**MINOR 14. The prose is clear sentence by sentence but the whole is hard to follow.**

- The abstract carries about 15 numbers and reads as a results log.
- Four contributions in §1 are heterogeneous: an identification test, held-out validation, a fusion benchmark, and a monitor.
- The shrinkage estimator (Eq. 2) is introduced with a James-Stein justification and then disowned ("We claim no optimality"). It could be dropped in favour of the median.
- Terms such as "unit", "ledger dollar", "unit share" and "demand" are used loosely. "Unit share" in particular is not a share (see Weakness 2).
- Related work on bias-aware truth discovery and sensor or measurement calibration is thin. The WWW-relevance of an exchange-specific application is asserted ("platform credits, multi-currency marketplaces and loyalty points") but untested (§6 concedes this).

### Claims versus evidence

**MAJOR 15. Several claims run ahead of the evidence.**

- "First test of a reading that Flowerday et al. (2026) say cannot be tested directly." This rests on one episode, one exchange and one anchor, with the assumptions above untested.
- "Bitfinex's 2018 to 2019 premium was therefore two discounts" is a point-estimate decomposition. The interval for the netted slope reaches 1.00, and the split relies on Kraken USDT being outside Bitfinex's ledger, an assumption supported only by price closeness (2.8 bps median gap).
- "Binance.US in 2023 was a pure ledger-dollar shift" is stated as a finding. The J-test fails when the second anchor is added, and the paper explains this away.
- The abstract says "slope close to one (0.97 ...)" while the formal test rejects lambda = 1 with p < 0.001. The text ("we say close to one, not equal to one") is more careful than the abstract.
- "Aggregators should correct when a shared unit can move and otherwise keep the median" (abstract) is a design recommendation from one winning episode, with unknown external validity.
- The fee-band section (§5.5) claims the offsets "are not arbitrage opportunities" using fee schedules of which "2 ... rest on dated news articles ... 4 are unverified". It also claims "The conclusion does not depend on the timing convention" on 12 lead-lag series. This is tangential.

### Page use and appendices

**MINOR 16. Page budget and appendix structure.**

- Key supporting evidence sits in the appendix while main-text claims lean on it: Table 12 (Binance.US slope), Figure 2, Appendix A (minority shifts are absorbed by a median), Appendix B (the 111.1 to 8.8 bps result), and Appendix D (the 2023 shocks).
- In the review copy, Appendices C and D carry headings only, with their content apparently relocated or missing. Page 9 has a large blank area.
- §5.5 (fee bands, timing), §5.6 (monitor) and §5.7 (2023 shocks, Chainlink) read as three additional papers. They dilute the identification contribution and could be cut or moved so that the simulation (Table 4), the key slope plot, and the sensitivity analysis fit in the main text.

### Reproducibility

**MINOR 17. Strong, but not self-contained for a reviewer.**

- §7 describes the infrastructure ("macro modules of www_paper", "fixed gate rebuilds the PDF") rather than telling a reader what to run. No anonymous artifact link is given in the text.
- The "4 instruments" list, GMM weight details, and simulation DGP parameters, seeds and replication counts per figure are not in the paper.
- The 33-event label list "ships with the artifact", and fee schedules come from "secondary sources". Anything that needs secondary sources, and the label list itself, should be in an appendix table.
- Data are free, but data-vendor candle quirks (for example Bitstamp ETH trades from September 2017, and Bitfinex pre-2018 candles) are not quality-audited in the main text.
- "Every number in this paper is a macro generated from committed reports" is good practice. It also means the reader cannot tell which numbers are rounded, filtered, or hand-picked slices.

## Questions for the authors

1. How does the netted slope change if exchange-specific USDT demand has a positive covariance with the BTC offset? Can you give a bound, or a bound-based sensitivity analysis, rather than assuming Cov(eta, c) = 0?
2. How do you distinguish a ledger-dollar unit from a venue-wide transfer or withdrawal friction (Binance.US 2023, Bitfinex 2018)? What observable would reject the friction reading?
3. Which four instruments, and what degrees of freedom, produce J = 2.94 (p = 0.40)? Why does the simulation say 5 df?
4. Why does the HAC interval (0.961 to 0.981) differ so much from the bootstrap (0.94 to 1.00) on the same data? Which do you consider correct, given 0.72 coverage in the mixture simulation?
5. Does the Coinbase to Bitstamp ETH-gap instrument have the same gamma for unit and demand components? What is the effect if not?
6. Were the FUSE and STABLE episodes scored by any earlier method ("Earlier unit-aware method (frozen)") before the method of this round was frozen?
7. Can you add intervals (for example, block bootstrap of hours within episodes) to the error ratios in Table 6, and run the median-polish or trailing per-source offset baseline?
8. Why is Kraken both the external anchor price and the ground-truth reference in FUSE and STABLE?

## Score

**2 of 5 (leaning reject, not unreasonable for a revised submission).** Confidence **4 of 5**.

## Three changes that would most raise my score

1. **Make the identification claim robust, or narrow it.** Give a complete proof. Relax or bound A3 and A4, especially exclusion under exchange-specific USDT demand and item-specific demand loadings. Extend the simulation to those violations and report sensitivity of the headline 0.97. Resolve the J-test df and instrument inconsistencies. Address the withdrawal-friction alternative directly.
2. **Report calibrated uncertainty on a small-n problem.** Replace tight HAC intervals with intervals (bootstrap with episode-level resampling, or a persistent-regressor-robust method) that match the simulated coverage. State the effective sample size per headline estimate. Add a robustness grid over window, anchor, reference, aggregation and block length, and one more independent anchor episode if available.
3. **Refocus the paper.** Present the benchmark honestly as "a median is hard to beat; here is one case where units help", with intervals on the ratios and stronger baselines (median polish or two-way fixed effects, trailing per-source offset). Drop or move the monitor, the fee bands and the Chainlink pilot. Use the freed pages for the simulation, a slope figure, and a self-contained reproducibility appendix.
