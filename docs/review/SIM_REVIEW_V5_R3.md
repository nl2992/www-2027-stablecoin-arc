# Review of "Same Name, Different Unit: Identifying Source-Specific Units in Web Price Fusion" (WWW 2027, simulated Reviewer 3, methodology / statistics / evaluation / presentation / reproducibility)

## Summary

The paper argues that a web source can quote in its own unit. Examples are an exchange's "USD" ledger balance or a platform credit. A drift in that unit moves every item on the source together, and a fuser then reports it as a price change.

- **Model.** Source prices equal true prices plus a source-hour offset shared across items (Eq. 1). The offset is estimated from cross-item agreement as a shrunken cross-asset median of gaps (Eq. 2).
- **Anchor.** An item fixed in the true unit, here the stablecoin USDT, separates a unit shift (slope 1) from source-wide demand (slope 0).
- **Evaluation.** Data are public candles from Bitfinex, Coinbase, Bitstamp and Binance.US, 2017–2023. The evaluation has these parts:
  - a dev/test split over assets;
  - positive and negative control pairs;
  - an anchor test on Bitfinex (2018–19) and Binance.US (2023);
  - noise bounds from fees, ticks and persistence;
  - an alarm monitor scored against 33 hand-compiled dated events, with operating curves;
  - a check of whether Chainlink feeds inherited the March 2023 USDC depeg.
- **Headline results.**
  - On held-out assets the offset removes 85% of the mean-square Bitfinex–Coinbase gap.
  - The estimator is statistically indistinguishable from the plain cross-asset median. The authors say so.
  - The anchor carries 71% of the Bitfinex offset in 2018–19.
  - The monitor has fewer false alarms than a plain gap rule.

## Strengths

- **Candour about the estimator.** The authors say the estimator ties the plain median (Table 3, Δ vs b2 ≈ 0.000) and locate the contribution in the unit model and its validation. Many papers would have hidden this.
- **Framing.** The unit-versus-demand distinction is crisp, the anchor idea is clear and falsifiable, and the framing for web data fusion is interesting.
- **Controls.** The design has a pair with a shared dollar and a pair with separate dollars (Table 3). Two things are reported against the first control: the ETH score of -0.298 and the placebo with an uninformative interval (Table 2). Both read as honest.
- **Binance.US.** The 2023 episode is a clean natural experiment. The slope is 1.00 [0.97, 1.01], and Table 7 gives a within-venue triangle check and a second reference.
- **Negative results reported.** The 2018 timeline concedes "This is not a lead over the market", and Appendix A concedes that unit awareness "adds information ... not accuracy".
- **Reproducibility practice.** Every number is a macro generated from committed reports, with stale-macro tests, input hashes, and a held-out split scored once from a recorded log. This is above the norm.
- **Operating curves.** Sweeping thresholds instead of reporting one operating point is the right instinct.

## Weaknesses

### Evaluation design and uncertainty quantification

**W1 (MAJOR). The block bootstrap does not match the dependence in the data.**
- §5.3 uses ISO-week blocks with 1,000 draws. The offsets are very persistent (Table 4, AC(1) of the daily gap 0.56–0.97), and the stress episodes last months (§5.5, "lasted 22 days", "172 of the 197 days").
- Weekly blocks treat consecutive weeks of one episode as nearly independent. The effective sample is a handful of episodes, so the intervals [0.662, 0.922] are almost certainly too narrow.
- The same bootstrap is used for the anchor slopes (Table 2), where the unit of independence is a stress episode, not a week.
- I would like block lengths chosen from the autocorrelation, or an episode-level or leave-one-episode-out analysis.

**W2 (MAJOR). The headline 85% is carried by one asset and one year.**
- §5.3: "pooled test figure is driven by XRP (97%) and by 2019 (99%)". The other four test assets score 27–40% and every year from 2020 scores 30–45%.
- A mean-square-share score is dominated by the largest gaps, so it effectively measures the 2018–19 Bitfinex episode.
- The abstract states 85% without this context. The honest summary is "high in one stress episode, about 30–45% otherwise".
- Please report a robust (median or absolute-error) score and a score excluding 2018–19.

**W3 (MAJOR). The score does not test the unit claim, and the held-out status of the test assets is partly compromised.**
- The score measures how much of a held-out asset's gap equals the cross-asset consensus gap. Any common factor produces this, including demand. Only §5.2 addresses unit versus demand, and it does so for a few windows.
- Test assets XRP and LINK reappear in the controls and in the "post-hoc" intervals. "Never loaded during development" holds for the estimator, but the evaluation choices (controls, pooling window 2019–2023, blocks) were made afterwards.
- The controls pool "withheld assets ETH, LTC, BCH, XLM, LINK and XRP". Four of these six are dev assets, so the "withheld" wording is misleading.

**W4 (MINOR). The "mean correction 2.7 vs 22.2 bps" statistic in the abstract is close to circular.**
- The correction is approximately the median gap, so the statistic restates that Bitfinex–Bitstamp gaps are larger than Coinbase–Bitstamp gaps.
- On the shared-dollar control, a mean correction of 2.7 bps exceeds the median gap of 0.7–2.3 bps in Table 1. That suggests the estimator adds noise on that pair, consistent with ETH at -0.298.

### The anchor test (identification)

**W5 (MAJOR). The anchor's exogeneity is assumed, not shown, and is dubious on exactly the venue where the claim matters.**
- §3 says an exchange-wide crypto boom "does not move" USDT's price. But a crypto exchange's USDT/USD price is a demand-sensitive, crypto-denominated claim.
- On Bitfinex, USDT was issued by an affiliate (cf. Griffin and Shams, cited by the authors). Funding-driven buying of crypto with USD can lift both the BTC premium and the USDT premium.
- A slope of 0.71 is therefore compatible with "demand that also hits USDT", not only with a unit shift. "Demand alone would not produce" it holds only if demand cannot touch the anchor.
- Table 2's own rows complicate the story:
  - Bitfinex 2018 has slope 2.06 [1.22, 2.95], outside both predicted values (1 and 0).
  - Bitfinex 2023 has median L of -66 and median D of +38, opposite signs.
  - Only 50% of stress hours satisfy |T| ≤ 0.25|L|.
- The paper reports only the pooled stress window in the abstract. I would like the per-year heterogeneity discussed.

**W6 (MAJOR). Errors-in-variables and a shared-noise issue are not addressed.**
- L is estimated from noisy gaps and is regressed on as a regressor, which attenuates the OLS slope toward 0. The 0.71 may understate the truth, or it may be inflated if L and D share microstructure noise.
- The paper needs a sensitivity analysis: an IV or reverse regression, a different split of assets for L, or L estimated from assets excluding anything USDT-linked.
- The slope uses daily medians over about 190 days from one episode. "Rejected" for a demand-only model is stronger than a single-episode slope supports.

**W7 (MINOR). The calm-year interpretation as a unit is untested.**
- Contribution (3) says "Bitfinex carried its own dollar throughout". For 2020–2023 the anchor evidence is 21–160 hours per year with slopes of 0.16–0.61.
- A persistent 4–7 bps cross-venue premium could be a funding cost, a withdrawal-fee wedge or a quoting convention. The term "unit" becomes unfalsifiable if any persistent cross-asset-common gap qualifies.
- The shared-dollar inference (Coinbase–Bitstamp) is likewise a failure to find a common component, not positive evidence of equal units.

**W8 (MINOR). Several identified quantities are circular.**
- §5.6 reports the ledger component accounting for "a median 99% of the Tether dislocation". With T = D − L and L estimated from BTC on the same venue, a 99% share follows when D ≈ L. It is a restatement of the Binance.US slope.
- The Binance.US figures are quoted for several windows (-413, -557, -600 bps in §5.2, §5.6 and Table 7). The window definitions must be reconciled.
- Table 7's note says BTC/USD did not trade while the rail was impaired. §5.6 says 530 hours "in which all legs traded", and Table 2 uses 721 hours. Please state which assets enter L in each case.

### Controls

**W9 (MINOR). Control power and design.**
- The positive control (separate dollars) scores 0.923 and the pair is not a negative result for the claim. It is simply the stress pair.
- The negative control (shared dollar) scores 0.042 [0.009, 0.081], not zero, and is significantly higher than b2 (Δ = 0.011 [0.007, 0.017]). The text should explain why a negative control has a significant positive effect.
- The placebo (Table 2, last row) has 15 hours and an interval of [-2.04, 1.84]. This carries no evidential weight, and the abstract and §5.2 should not cite it as a check.
- Only one pair is a shared-dollar control, and all controls are drawn from the same sources as the main findings. Controls on a different platform type (the paper's own generalisation claim) are absent.

### Monitor, baselines and operating curves

**W10 (MAJOR). The monitor claim in the abstract is stronger than Tables 5 and 6 support.**
- The abstract says the monitor "raised less than half the false alarms of a plain price-gap rule at equal recall". This holds on Bitfinex (3 vs 9 alarms at 7/9 recall) and nowhere else.
- On Coinbase the monitor has recall 0/5, the same as the plain gap rule.
- Table 6 shows the robust z-score dominating the monitor at ≥100% recall on Bitfinex (1.15 vs 3.44). The monitor is also worse than the gap-only rule there (3.44 vs 3.15).
- The pooled monitor never reaches 85% recall (the dash), so the "equal recall" comparison exists only on Bitfinex, with 9 positives.
- §5.5 says the monitor "matched or beat the two-asset rule at 7 of 7 thresholds". Table 6 shows three recall levels, and the monitor and the "matched two-asset rule" are not clearly distinguished (is the monitor the two-asset rule plus the USDT leg?). The 7-of-7 result is close to mechanical for nested rules.

**W11 (MAJOR). The label set is small, highly dependent, and compiled by the same authors.**
- Effective positives are about two episodes: Bitfinex 2018–19 and Binance.US 2023. Bitfinex "9" positives include restorations and several events on the same dates (BFX-2018-06 and BFX-2019-01 on 2019-04-25).
- The five Coinbase positives are all missed by every price-based method, and Kraken and Bitstamp are not evaluated (Table 5).
- There are no intervals on recall (7/9 has a Wilson interval of roughly 0.45–0.94) or on false-alarm rates. 0.86 vs 1.15 false alarms per venue-year is a difference of roughly two episodes.
- "Compiled ... without reference to prices" is unverifiable. Figure 1 shows the authors knew the price history, and the dates are inconsistent with the paper's own finding that the premium was visible 6.5 months before the loss was disclosed (§5.5). The matching window between an alarm and a report date is never defined. Per-event lead or lag times would help.
- Unlabelled alarms are counted as false, but §B admits the 2017 alarms may be real frictions. Incomplete labels penalise more sensitive rules unevenly.

**W12 (MINOR). Denominators and baseline fairness.**
- Table 5's false-alarm rates use different evaluated hours per method (Binance.US: 1 alarm gives 1.31 for the monitor and 1.26 for the gap rule). The text says the "denominator ... was 61,183 hours" only for Bitfinex.
- Baselines are swept over their best thresholds while the monitor's 100 bps and 0.25 were "fixed before". Say how they were fixed and whether the sweep range (25–300 bps) was chosen after seeing results. The USDT-premium baseline has no pooled version.

### Multiple comparisons and specification search

**W13 (MAJOR). The garden of forking paths is not quantified.**
- The authors had a 12-iteration development loop (3 kept, 9 discarded), then sliced results by year × pair × window × timing convention × fee tier × threshold. Stress windows were defined after the fact (2018-11-27 to 2019-05-31; June–July 2023; "all of 2023"; the "core window" of 3 days in Table 8).
- Table 3 is the only place with a held-out discipline. Tables 1, 2, 4, 5 and 7 are descriptive and not corrected for the many windows searched. There is no statement of how many windows and thresholds were tried in total.
- The held-out test was "scored once", but the intervals, controls and ETH diagnostics were computed afterwards ("Scores are post-hoc and descriptive").
- I would like a pre-registered list of primary comparisons, or at least a count of looks and a sensitivity of the headline conclusions to window choice. Because the estimator ties the median, the stronger test of overfitting would be showing the conclusions survive for any window.

### Clarity of the model and assumptions

**W14 (MAJOR). The model section is too compressed for the main object to be checked.**
- Eq. (2) is not derived or justified ("in the manner of James and Stein"), and the shrinkage form with n/(n−1) and σ̂²/2 has no stated loss, risk or properties. Since the estimator equals the median, the section either needs to be replaced by "median" or the shrinkage must be shown to do something (e.g. when it binds in calm years).
- The offset is identified only relative to a reference source, which is itself a venue with its own unit (Bitstamp has events in Table 10). The paper does not discuss reference contamination, or what "true unit" means when two of three venues are biased (the authors concede in §6 that prices cannot say).
- Additivity in log-bps, the assumption that e is independent across assets (the "unrelated residuals" premise), and the exact meaning of "item" are asserted. The BTC/ETH correlation due to common market factors is not separated from the unit.
- Triangular parity is asserted as a check but never shown.

### Figures and tables

**W15 (MINOR). Figures are cramped, and several tables duplicate each other.**
- Figure 1 (right) and Figure 2 are too small to read at column width, and Figure 3's axis labels are overlapping and unreadable. Figure 2 has no uncertainty bands and its legend hides the shape of the curves.
- Table 4's |L| and "Med" columns repeat Table 1's gap and share columns. They could be removed or the two tables merged.
- Table 4 (24 rows) and Table 10 (33 rows) use a large part of the page limit for details that could be in an appendix or supplement.
- Table 5's "Episodes" column (e.g. 12 for the Bitfinex monitor) does not obviously reconcile with recall plus false alarms (7 + 3 = 10) and needs a definition. Table 9's "Pooled / Worst / Replay" and the "none" entries are hard to interpret without the main text.
- Table 1 has six decimals in the text (0.949) but two in the table. Be consistent.

### Writing and claim–evidence match

**W16 (MAJOR). Several claims run ahead of the evidence.**
- "The same approach applies to platform credits, multi-currency marketplaces and loyalty points" (§6): there is no evidence beyond exchanges, and the paper acknowledges "the diagnostic rests on three USD exchanges".
- "The Chainlink check" (Table 8): the paper observes slopes of 0.007 vs 0.140 but never states the slope predicted if a share of sources inherited the depeg, so the test has no stated expectation. It covers 78 hours, one episode and one oracle family, so "did not inherit" cannot generalise to feeds.
- "These offsets are not arbitrage opportunities" (§5.4) rests on fee bands of which 4 of 8 entries are unverified, and ignores latency, inventory and transfer constraints. The conclusion is probably right but not shown.
- Contribution (2) claims "causal and permutation-style checks", but no permutation test is reported, and "causal" in the estimator section means "uses only the current hour". Rename it or add the test.
- The abstract's "Price feeds can state which unit each price is in" is a recommendation, not a finding.
- The Silvergate/USDC story (no alarms on Bitfinex, Coinbase or Binance.US in March 2023) is presented as success, but "no alarm" is also what the Coinbase recall of 0/5 would predict if the monitor is insensitive.

### Page use

**W17 (MINOR). Space is allocated unevenly.**
- Sections 5.4 (noise bounds) and 5.6 (three shocks, Chainlink) and Table 10 take roughly 2.5 of 8 pages, while the method (Eq. 1 and 2) and the identification argument get under one page.
- The paper bundles three topics (identification, a monitor, an oracle audit) where one topic would be deeper. I would cut 5.4 to a short paragraph and move Table 4 and Table 10 to an appendix, then use the space for the model derivation, a sensitivity analysis for the anchor, and larger figures.

### Reproducibility

**W18 (MINOR). The reproducibility statement is strong on process, weak on access.**
- The macro modules are named after repo files ("www_paper"), but no anonymous artifact link is given. For the review, I can neither check the macro tests nor inspect the label file.
- The label file (sources and notes) and the fee schedule (4 of 8 entries "unverified") are central and not available. Event dates are the "first public report" and need citations in the paper.
- Data coverage is inconsistent: the abstract and title say 2017–2023, but Binance.US uses 2022–2025 and Table 7 has a 2025 row. Exchange APIs revise or drop candles, so the hashes address only the authors' snapshot. State the retrieval date and say what to do if the endpoints change.
- Hourly "median of traded-minute closes" vs "last traded close" is a defined convention, but the mapping between them is not.

## Questions for the authors

1. What is the effective number of independent stress episodes behind the intervals in Tables 2 and 3? Please report an episode-level or leave-one-episode-out result for the 85%.
2. Can the USDT anchor be moved by Bitfinex-specific demand (e.g. USDT issuance or arbitrage with USD)? What does the 2018 slope of 2.06 mean in your model?
3. How do you reconcile Table 2's 2023 Bitfinex row (L = -66, D = +38) with "Bitfinex carried its own dollar throughout"?
4. Why is the negative-control score significantly above the plain median (Δ = 0.011)? Does the shrinkage in Eq. (2) ever bind?
5. How was the window used to match an alarm to a label, and how many windows, thresholds and sweep ranges were tried before the monitor was fixed?
6. What are intervals (e.g. Wilson or episode-level bootstrap) for recall and for false alarms per venue-year in Tables 5 and 6?
7. Which assets enter L in the Binance.US window when BTC/USD did not trade (Table 7 note vs §5.6)? How are -413, -557 and -600 bps related?
8. What slope would you expect for the Chainlink feeds if one source of N quoted USDC? What would be a failure of the null?
9. Does the conclusion survive a reference other than Bitstamp or Coinbase?
10. Is any of the 33 labels derived or dated with knowledge of the price series? Who compiled and checked them?

## Overall assessment

The idea is good, the writing is mostly clear, and the reproducibility process is unusually disciplined. The honesty about the estimator and the controls is a real strength.

The central identification claim (the offset is mostly a unit, 71% on Bitfinex) rests on one stablecoin anchor whose exogeneity is not established, on one episode, with intervals that probably understate dependence. The headline 85% is driven by one asset and one year. The monitor evaluation has about two effective episodes and no uncertainty, and the abstract states it more strongly than Tables 5 and 6 allow. The paper also bundles too many topics for eight pages, and the model section is the thinnest part.

**Overall score: 3 / 5 (borderline).** I would move to 4 if the identification and uncertainty issues are fixed.

**Confidence: 4 / 5.**

## The 3 changes that would most raise my score

1. **Redo the uncertainty and identification checks at the episode level.** Use episode-level or long-block resampling for Tables 2 and 3. Report scores without 2018–19 and without XRP. Address anchor endogeneity and attenuation (IV or reverse regression, an anchor-free L, sensitivity to which assets enter L) and explain the 2018 slope of 2.06 and the 2023 sign flip.
2. **Rescope and quantify the monitor claim.** State in the abstract that the evidence is one Bitfinex episode and one Binance.US episode. Add recall and false-alarm intervals, define the matching window, and acknowledge that the robust z-score dominates at high recall. Give the count of rules, windows and thresholds tried, with the label provenance, and release the label file.
3. **Rebalance the paper around the model.** Derive or drop Eq. (2), state the identifying assumptions and the reference-contamination limit, and show that "unit" is falsifiable in calm years. Move Table 4, Table 10 and the Chainlink check to an appendix, enlarge the figures, and provide an anonymous code and data link.
