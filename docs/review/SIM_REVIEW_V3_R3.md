# Review of "Which Dollar? Exchange Dollars as Exchange Rates in Web Crypto Prices" (WWW 2027) - Reviewer 3 (methodology, statistics, evaluation, presentation, reproducibility)

## Summary

The paper argues that an exchange's "USD" is a ledger claim that can trade away from a redeemable dollar. It proposes an hourly decomposition (Eq. 1): log price = common asset value + exchange-dollar rate u(v,t) + asset-specific residual. Agreement of cross-exchange gaps across unrelated assets identifies u, and ETH/BTC triangular parity is offered as a check. The empirical content has four parts.

1. A diagnostic on three exchanges, 2017-2023, concluding that Bitfinex has "its own dollar" every year and that Coinbase and Bitstamp share one after 2018 (Table 1).
2. A cross-sectional estimator (shrunk cross-asset median) evaluated by leave-one-asset-out on 5 dev and 5 locked test assets, with a reported 85% mean-square gap removal on test.
3. A rule-based monitor evaluated against 33 hand-compiled events, with false-alarm rates against three baselines.
4. A 2023 case study (Binance.US, Silvergate/Signature, USDC/Chainlink).

## Strengths

- The question is clear and well motivated for web data quality. Separating an exchange-unit shift from an asset-specific move is a sensible framing.
- The honesty is unusually good. The paper says the pooled test score is driven by XRP and 2019, says the estimator "matches the plain cross-asset median", and admits the zero correction on the control pair is partly mechanical. A reviewer can find the weaknesses because the authors disclosed them.
- The protocol discipline is good: a locked test split, a causal estimator, a relabelling-invariance check, a fixed monitor rule, and macro-generated numbers.
- Table 4 uses hour-block bootstrap intervals, and the Binance.US episode (557 bps over 530 hours, with three unrelated assets showing the same dislocation) is persuasive.
- Appendix A states plainly that with k=2 biased exchanges "nothing in prices says which dollar is true". Few papers volunteer this.

## Weaknesses

### Evaluation design

**MAJOR 1. The headline test number is not a representative estimate (Sec. 5.2, Table 2, abstract).** The abstract reports "removed 85% ... for five assets withheld from development." The paper itself says the pooled figure "is driven by XRP (97%) and by 2019 (99%)." The other four test assets score 0.27-0.40 on the paper's own account, which is about the dev level (0.445 pooled, with ETC at 0.07). The pooled score is a ratio of sums, so it is dominated by the highest-variance asset-periods. A single event year (2019, the Bitfinex episode) contributes most of the denominator.
- The honest statistic is per-asset and per-year, with the pooled figure as a footnote.
- The abstract mentions the 30-45% range for later years but leads with 85%. That is the wrong emphasis for a headline.
- Report a variance-robust metric alongside the ratio of sums. Examples are the median across assets, the mean of per-asset scores, or the mean of per-year scores with equal weight.

**MAJOR 2. No uncertainty quantification on the central result.** The paper has no confidence intervals on the 0.85, 0.445, or any Table 2 entry, and no block bootstrap.
- Hourly gaps are strongly autocorrelated, so naive intervals would be far too narrow. The tool exists, since Table 4 uses an hour-block bootstrap, but it is not applied to the main claim.
- With 5 test assets and one dominant event, I cannot tell whether 0.846 versus 0.847 (estimator versus baseline) or 0.40 versus 0.27 is signal.
- Use a block bootstrap over days or weeks, stratified by year, with assets as a second resampling level. Report the interval for each pooled and per-asset score.
- The same applies to the Table 1 correlations. Daily correlations of 0.95-1.00 within a year are reported without any interval. The 2019 Coinbase-Bitstamp correlation of 0.21 and the 0.28/0.44/0.53 values come from short series, with daily series that are themselves serially correlated.

**MAJOR 3. Leave-one-asset-out with a single reference pair, and no per-asset baselines on test.** Table 2 shows b1 and b2 only for the dev assets; for the test assets they are "not recorded (-)".
- The only test-set claim that matters is "does the estimator beat the obvious baselines?" It cannot be checked per asset on test.
- The pooled b2 = 0.847 is reported, but per-asset b2 is not. I therefore cannot verify that the estimator is not worse than the median asset by asset, or that the XRP effect is the same for the baselines.
- The cause is stated as a logging omission. That is a reproducibility problem for an evaluation described as "scored once". If the test logs do not contain the baseline per-asset scores, the baselines need to be re-scored, and the paper should say whether that breaks the "scored once" discipline.
- The scored object is a single pair (Bitfinex-Coinbase), because only two exchanges list the nine altcoins. This is closer to "does a cross-sectional median of gaps predict the held-out gap on this pair?" than a general test of unit estimation.
- The design also never tests the exchange-level claim "the rate is the same for every asset" against its alternative, such as an asset-specific premium that is correlated across assets because of common liquidity or common-market factors. Leave-one-asset-out removes the asset's own gap from the estimate, but any common factor in the other assets' gaps (market-wide stress, latency, funding cost) also gets labelled as "the dollar."

**MAJOR 4. The estimator is indistinguishable from a plain median baseline, so the method contribution is thin (Sec. 5.2).** The text says "The estimator matches the plain cross-asset median (b2: 0.847 ... 0.846)." On dev the three scores are 0.441 (b1), 0.444 (b2), 0.445 (Final).
- The James-Stein-style shrinkage therefore buys almost nothing on held-out assets, and Contribution 3 ("A held-out benchmark") reduces to "the median of other assets' gaps predicts a held-out asset's gap." That is a reasonable finding, but it is a different, smaller claim than "we develop an estimator."
- The paper claims the estimator's contribution is on the control pair (zero correction versus -0.104). See Major 5 for why that is weak.
- The same fact shows up in Table 7, where "Median" and "Unit-aware median" are identical in every cell. It also shows up in the Discussion, which notes that the rate "names which exchanges share a dollar, which a plain median or source weighting does not," but the shrinkage rule itself is not what does that.
- The related-work contrast with truth-discovery methods (CRH, TruthFinder) is asserted. The empirical comparison is only Appendix A, on injected constant biases, where the proposed method ties the median.

**MAJOR 5. The control pair's zero correction is partly mechanical, and so is the main support for the estimator's value (Sec. 5.2 and Limits).** The Limits section concedes that the zero "partly reflects the estimator's rule of applying none when fewer than two assets are visible."
- Bitstamp lists only BTC and ETH. With ETH withheld, only one asset is visible, so the rule fires and the output is exactly 0.000. The comparison to b1/b2 (-0.104) is then a comparison between a rule that abstains and rules that do not.
- A trivial estimator that says "do nothing unless at least two assets are visible" would score 0.000 on the control, and any pair with two listed assets is a coin flip on the shrinkage.
- The abstract says the estimator "made no correction for an exchange pair that shared a dollar", with no hedge, while the caveat is buried on page 4. That is a claims-versus-evidence mismatch.
- A real control needs a pair with at least two or three visible assets that nonetheless share a dollar. Candidates: Coinbase-Kraken, or Coinbase-Bitstamp restricted to BTC/ETH/LTC/BCH if Bitstamp lists LTC and BCH. Or construct a synthetic control in which assets' gaps are permuted across time or shifted in asset labels, which breaks the cross-asset common component while preserving marginals.
- The shrinkage factor's behaviour (does it actually shrink to near zero when the dispersion is high and the median is small?) should be shown in a mechanism plot on a control with enough assets, not inferred from a rule that abstains.

**MAJOR 6. The identification assumption is stated but not tested (Sec. 3).** "Assets that share no peg ... have unrelated residuals." This does the heavy lifting, since "the common part is u_v - u_r" follows only if residuals are cross-sectionally uncorrelated.
- Crypto assets are strongly correlated, and the exchange-asset residuals e(v,a,t) include latency, liquidity, local order-flow and funding-rate differences, which are common across all altcoins on a venue. Bitfinex funding and margin conditions, for example, would produce a common premium on every asset at Bitfinex that is not a "dollar" in any redeemability sense.
- The paper never distinguishes "unit shift" (the exchange's USD is worth less) from "common venue premium" (a venue-wide wedge in how every asset trades, for example from leveraged long demand). Both would show agreement across assets. The label "dollar" is then a conclusion that needs outside anchors, which are provided only for Binance.US (USDT and the second reference in Table 4) and for the event labels.
- ETH/BTC triangular parity is cited as a check. It tests a necessary condition (the ratio is unit-free), but it cannot reject the venue-premium alternative, because a venue-wide premium on every non-BTC asset would also leave the ratio near the same value.
- Please state the assumptions formally. Examples: whether u is common across assets with the same sign, whether the residual covariance is zero or merely small, and what happens when quote currencies other than USD exist. Then show a falsification test, such as a placebo using two exchanges known to share rails.

### The monitor

**MAJOR 7. The monitor evaluation rests on 9 positive Bitfinex episodes and 4-5 positives elsewhere (Sec. 5.3, Table 3).** The headline contrast is 3 versus 9 false alarms at 7/9 recall.
- The headline "a third the rate of a plain price-gap alarm" is a ratio of two small counts (3 and 9) from a single exchange. There is no interval and no significance test. A paired comparison would be needed, such as McNemar-style on matched windows or a block bootstrap over episodes.
- Recall 7/9 on a set of 9 has a binomial 95% interval of roughly 40% to 97%. Binance.US 4/4 has an interval from about 40% to 100%. Coinbase 0/5 for the monitor is not discussed beyond "no alarm after 2018", yet it is a total failure on its own exchange.
- "Equal recall" is not a fair comparison as presented, for three reasons.
  - Both methods have tunable thresholds, and the paper reports a single operating point per method. Equal recall at one point does not show dominance. A precision-recall or false-alarm-versus-recall curve over thresholds is needed, because the 100 bps threshold and the quarter-size agreement window may simply sit at a point favourable to the monitor.
  - The monitor requires a second asset to agree, while the price-gap baseline uses BTC alone. A fairer baseline is a two-asset rule without the unit-estimation step (for example "BTC and ETH both gap by 100 bps"), which isolates what the decomposition adds. Without it, the improvement is attributable to the second-asset-agreement filter, which is far simpler than the decomposition.
  - The trailing robust z-score has 100% recall on Bitfinex (9/9) and is dismissed for false alarms, but it has no tuned threshold either, and it is not compared at matched recall. If its threshold is raised until false alarms equal the monitor's, recall may match.
- The false-alarm rate is computed as "alarm episodes with no labelled event." That makes the false-alarm count depend entirely on label completeness. Real unlabelled events (the paper itself notes the 2017 alarms "may reflect dollar funding frictions ... we did not test this") count as false alarms. The false-alarm definition (how far an alarm may be from an event, which event types count as a match, how confounders are treated) is not given in the text. Whether the 8 confounders count as matches matters: Bitfinex's confounders are dated 2018-06, 2019-04-25, 2021-02, 2022-02, and Appendix B says the 3 false alarms are in 2017/2019/2022, so I cannot tell whether any are confounder-adjacent.
- The denominator is also unclear. The paper says "per exchange-year", but Binance.US (coverage from October 2022) has 1.31/yr on 1 false alarm, so the exposure period there is under a year and the rate is not comparable. Table 3 reports Bitfinex's 0.43 as 3 alarms over 7 years, a figure dominated by a quiet 2020-2023 period in which there are few events.
- The lead-time claim ("flagged the exchange from October 2018, 6.5 months before regulators disclosed") is a single anecdote. The monitor's first alarm on 2018-10-08 is matched with the 2018-09-30/10-11 labels (BFX-2018-03/04), so the 6.5-month figure is computed against a different event (2019-04-25) that happens to be the same ongoing episode. Calling this "early warning" is not supported, since the dislocation had by then persisted for months and was visible to anyone plotting the price gap (Figure 1 shows it). The paper shows that the same price-gap baseline also catches 7/9, so lead time should be compared across methods.
- Label construction: 33 events were "compiled from public sources without reference to prices," but who compiled them, how disagreements were resolved, and the choice of the first public report as the event date are not described. The event list includes dates with the same day for different types (BFX-2018-06 and BFX-2019-01 both 2019-04-25). Table 8 appears to be a label set built by the authors and the monitor tuned in a loop (see below), so independence is not established.

**MINOR 8. Mismatch between "9 positives" and "12 episodes".** Table 3 lists 12 episodes for Bitfinex with recall 7/9, which suggests 3 non-label episodes and 9 labelled, but the label table shows Bitfinex has 12 labels, with confounders and a restoration included. The text should explain which labelled events count as positives for recall (the labelled "rail impairments" only?) and which are excluded.

### Multiple comparisons and the development loop

**MAJOR 9. The development loop creates a selection and multiple-comparison risk that is not quantified (Sec. 3 "Development loop").** The paper reports "a bounded loop of 12 iterations kept 3 changes and discarded 9."
- The score driving selection was the leave-one-asset-out dev score on five assets, and the control pair was also scored in the loop. The monitor rule, thresholds and baselines were "fixed before the evaluation", but the paper does not say whether they were chosen using the same Bitfinex 2018-19 data and label set that they are later evaluated on. The Bitfinex 2018-19 dislocation is the single event that produced the 99% score, the Figure 1 narrative, the monitor's recall, and the labels.
- The test split protects the estimator from loop overfitting on assets, but not from overfitting on the single dominant event, since the test assets share the same exchange pair and the same years as the dev assets. "Never loaded during development" is a weaker guarantee than "independent in time and exchange pair."
- 12 iterations with a handful of design choices is a small search, but combined with the monitor thresholds, the baseline definitions, the choice of the hourly median versus last-close, the choice of reference exchange, and the choice of reporting pooled versus per-year numbers, the forking paths are numerous. The paper should list every degree of freedom and report the dev score of the discarded variants, in order to show the effect sizes were small (they are, given 0.441/0.444/0.445) and therefore the selection did little. That is consistent with Major 4: the loop produced nothing that moved the score.
- The several robustness-style statements in the abstract (for example "0.949 or more in every year", "at most 2.3 bps") are summaries of tables and are post-hoc. Please state which analyses were pre-specified and which were exploratory.

### Model clarity

**MAJOR 10. The decomposition model is under-specified (Sec. 3).** Eq. (1) is introduced with one sentence per symbol, and the following issues stay open.
- The model has p* indexed by asset and time, and u indexed by exchange and time, so u is identified only up to a constant per hour. A reference exchange fixes the normalisation, but the text says only that the estimator "names no exchange" and uses "the reference exchange." So what is u? It is a difference to the reference, and "the exchange's dollar rate" is then a misnomer: it is relative to the reference exchange's own dollar. The Limits section partly acknowledges this ("prices alone cannot say which unit is the U.S. dollar"), but the abstract and title speak of "exchange dollars as exchange rates" as if levels were identified.
- Measurement: p is a log price at hourly resolution built from either the hourly median of minute closes (diagnostic) or the last traded close (benchmark). The two constructions differ, which changes asynchronous-trading noise and stale-quote effects, and the paper does not say how the choice affects Table 1 versus Table 2.
- Stablecoin extension: D_q, L, and T_q = D_q - L are introduced in one sentence, and the claim "ledger component accounts for a median 99% of the Tether dislocation" (Table 5) requires the assumption that BTC is a clean proxy for L. L is "via BTC" in Table 5 but "from an unpegged asset" in Sec. 3, and the choice of BTC rather than the cross-asset median is not justified. Then 99% is not surprising, since the Tether dislocation and the BTC dislocation are both measured against Bitstamp over the same hours, and T is a residual that absorbs measurement noise. The reported "L share" metric, |L|/(|L|+|T|), is also bounded away from information when L is large (557 bps), so it would be 99% for any token with a small dislocation.
- The shrinkage is described verbally ("keeps the share of the squared median that the dispersion does not explain") with no formula, no definition of dispersion (MAD? standard deviation? across assets or across time?), and no justification for it being James-Stein-like. A reader cannot reimplement it from the paper. Give the formula.
- The model is time-varying and hourly, but the paper's own finding is that smoothing and Kalman filtering did not help "because the unit moves from hour to hour." That claim is a substantive finding about the dynamics of u (hour-to-hour jumps), and it is asserted without evidence. It also sits oddly with a 530-hour regime of nearly constant -557 bps.

### Claims versus evidence

**MAJOR 11. Several abstract and introduction claims go beyond the evidence.**
- "Bitfinex's dollar carried its own exchange rate throughout." Table 1 shows share = 0.63 in 2021, where about a third of the ETH gap is not explained by the BTC gap, and median gaps of 4 bps in 2021-2022 are in the range that ordinary frictions (fees, latency, withdrawal costs) produce. A correlation of 0.95 between daily median BTC and ETH gaps shows co-movement, not that the co-movement is a dollar rate rather than a venue-wide premium (Major 6). "Throughout" is a strong word for a correlation diagnostic on three exchanges.
- "Coinbase and Bitstamp shared a dollar after 2018" and "made no correction for an exchange pair that shared a dollar." The evidence is low correlation and a small gap, i.e. absence of evidence of a separate unit. Sharing a dollar is an inference, and the "pair" in the held-out control has only two assets (see Major 5). Table 1 also shows 2018 Coinbase-Bitstamp at rho = 0.95 and share = 0.58, which contradicts "after 2018" unless 2018 is treated as the transition, and the text says "more weakly, in 2018."
- "Raised 0.4 false alarm episodes per year, a third the rate of a plain price-gap alarm at equal recall" (Major 7).
- "In 2023 it separated three shocks." Of the three, one is a clean positive (Binance.US), one is a null (Silvergate/Signature: "raised no alarm"), and one is a feed check with a slope of 0.007 versus 0.140. A null result on March 2023 is presented as a separation. It is equally consistent with the monitor having insufficient sensitivity, since the 100 bps threshold is high relative to the 2023 gaps in Table 1 (0.7-6.6 bps). The paper cannot distinguish "no ledger failure" from "failure below threshold" without an independent measure of the Bitfinex, Coinbase and Binance.US rails in that month. Coinbase's 0/5 recall suggests the second reading deserves weight.
- "Chainlink's bitcoin and ether feeds did not inherit the token's depeg." The evidence is a regression slope of 0.007 on a 3-day window with 78 hours, versus 0.010 for the Tether feed. The 0.140 for the USDC feed is the only slope above noise, and it is not clear why 0.14 rather than 1 is the expected positive result for "responded as expected." No standard errors are given. A reader cannot tell if 0.007 differs from 0 or if 0.010 differs from 0.007.
- "Aggregators and oracles can thus state which dollar a price is in." This is the practical conclusion but no evaluation measures downstream accuracy of a labelled aggregator. Appendix A (injected bias) shows unit awareness "adds information, not accuracy," which undercuts the practical promise. This tension is not reconciled in the abstract.
- The abstract is dense, with 20+ numeric claims in 300 words. A reader cannot judge which is the main result.

**MINOR 12. Introduction contributions list.** Contribution (2) says Bitfinex "carried its own rate in every year", and (3) calls a ratio-of-sums score "a held-out benchmark." A benchmark is a dataset or task others can use. Nothing is released as such, and the test set has five assets on one pair.

### Presentation: figures, tables, and page use

**MINOR 13. Readability of figures.**
- Figure 1 (right panel, daily gaps by year) uses symmetric-log axes of +/-1000 with year colours that are hard to tell apart in print. The point of the figure (BTC and ETH gaps fall on the diagonal) is clear, but the left panel's banking-episode shading is not described beyond the caption. Reference and cross-reference are fine, but the claim in the text "stood apart for months" is not quantified in the figure.
- Figure 2b's date ticks are garbled in the extracted text and the three series PD_USDT, PD_BTC, PD_USDC overlap, and Figure 2a's y-axis runs to -1000 bps for a series whose interesting variation (ledger near zero) is invisible at that scale. The point of 2a (T tracks D, L is near zero) is made, but a table row (Table 5) already says it.
- Figure 3 (monitor output) is half a page of a y-axis clipped at an unreported value, and shows a monitor on a single exchange. It adds little beyond Figure 2b, which shows the same Binance.US series. It would be cut or merged into Figure 2.

**MINOR 14. Tables.**
- Table 1 is dense, with three pairs by three statistics by seven years (63 numbers) and no uncertainty. A reader needs one visual, such as a heatmap or the rho/share panel. It is needed, but should be reduced to the key rows or moved to a figure.
- Table 2 (per-asset scores) is necessary. Its dashes for b1/b2 on test undermine it (Major 3).
- Table 3 mixes counts and rates, and the "per year" column is blank for one row. Table 4 has nine columns with intervals. Table 5 is a two-row table that duplicates numbers in the text and could be merged into Table 4. Table 6 has four statistics per feed. Table 7 has three identical rows in every column (Median, Unit-aware median, Unit-aware cluster), which tells the reader nothing and could be collapsed. Table 8 (label list) is two-thirds of a page and could be a compact appendix or supplementary file, but it is key evidence for the monitor, so I would keep it and add source columns.
- Tables 5 and 4 are cited as "(Tables 5 and 4, Figure 2b)", out of order, and Table 7 is referred to in Appendix A without any pointer in the main text.

**MINOR 15. Page use.** The body ends on page 7 of 8 (page 8 holds references and appendices; references begin on page 7 and Figure 3 sits on its own page with a large blank area). A conference reviewer sees roughly a page of unused space and a half-empty figure page. The extra space should hold:
1. the formal model and assumptions, the shrinkage formula, and the identification argument (Major 10, Major 6);
2. uncertainty intervals and a per-asset, per-year breakdown of the test result, including test baselines (Major 2, Major 3);
3. a threshold-sweep (precision-recall style) comparison of the monitor against matched baselines, including a two-asset price-gap rule (Major 7);
4. a short threats-to-validity paragraph (venue premium versus dollar, label-set independence, single reference pair).

Figure 3 and Table 5 could make room for items 1-3.

**MINOR 16. Writing clarity.**
- "Dollar", "unit", "exchange dollar", "ledger component", "platform dollar", "rate" and "token component" are used interchangeably across sections (Sec. 3 says "unit shift", Table 4 uses "platform-dollar dislocation", the title says "exchange rates"). Define them once.
- "Second-asset test" and "second reference" are used in different senses.
- Related work is accurate but the Limits section is five lines long for what are real threats.
- Typographic points: "Binance.US.. In June 2023" has a doubled full stop. "Proceedings of Proceedings" in the ACM reference format. Appendix B is cited as "(Appendix B)" for the Coinbase claim.
- The Reproducibility section states "Every number in this paper is a macro generated from committed reports", yet the paper elsewhere says per-asset test baselines "were not recorded". It also mentions internal package names, www_paper.macros and so on, which is anonymity-fragile and unhelpful to a reader without the repository.

### Reproducibility

**MAJOR 17. Reproducibility claims are asserted but cannot be checked from the submission.**
- No artifact link (anonymous repository), no versioned data hashes, and no list of the exact endpoints. "All sources are free and unauthenticated" does not say which. Exchange public candles are revised and sometimes discontinued, and the Binance.US 2022-2025 candles may not be available later.
- Unspecified hyperparameters: the dispersion statistic for shrinkage, the reference exchange (Coinbase? Bitstamp?) for each pair, the minute-to-hour aggregation rules for gaps (candles with no trades), the minimum-trades filter for "hours with all legs traded", the alarm-merging gap for episodes, the "quarter of its size" tolerance rationale, the bootstrap block length in Table 4, and how Tether is mapped to the stablecoin D_q.
- A test split "scored once from a recorded log" is a procedure claim; the log is not shown.
- Time zone and candle-timestamp conventions (open or close time) matter at hourly resolution and for the Silvergate/USDC weekend windows, but are not stated.

## Questions for the authors

1. What are block-bootstrap intervals (blocks of days or weeks, resampling assets as well) for the 0.846 test score, for each test asset, and for each year? What is the pooled test score without XRP and without 2019?
2. What are b1 and b2 for each test asset? If they were not logged, will you re-score them, and does that count as a second use of the test split?
3. On the control pair, how many assets does the estimator see after withholding ETH? If one, then 0.000 is by construction. Can you provide a control with at least three visible assets, or a permutation or placebo control?
4. How do you separate a common exchange dollar from a venue-wide premium (leverage demand, funding, latency) that affects all altcoins on one venue? What would falsify the "dollar" reading on Bitfinex in 2021-2022, where gaps are 4 bps?
5. How was the quarter-of-size agreement window and 100 bps threshold chosen, and on what data? Please give a recall versus false-alarm curve for the monitor, the price-gap alarm, a two-asset price-gap rule, and the z-score.
6. How exactly are false alarms defined: matching window, treatment of confounders and restorations, overlapping events, and the exposure denominator for Binance.US?
7. Why do the Silvergate/Signature null and the Coinbase 0/5 miss not indicate low sensitivity? What is the monitor's detection limit in bps?
8. What is the reference exchange for each result, and is u normalised to a reference rather than identified in level? Please restate the claims in terms of relative units.
9. Are the Chainlink slopes accompanied by standard errors, and why is the expected slope for the USDC feed 1?
10. Which of the 12 loop iterations changed the score by more than the noise level? What were the discarded variants' dev scores?

## Scores

- **Overall score: 2 (weak reject; borderline if the evaluation is repaired).** The question is good and the paper is honest, but the main evidence does not currently support the headline claims. The 85% is one asset and one year, the estimator ties a median, the control is mechanical, the monitor comparison rests on 9 positives at one operating point, and the central "dollar" interpretation lacks a test against a venue-premium alternative. The 2023 Binance.US episode is the strongest and most convincing part and could carry a tighter paper.
- **Confidence: 4 of 5.** I am confident about the evaluation-design and statistics points. I am less sure about the market-microstructure explanation of Bitfinex gaps.

## The three changes that would most raise my score

1. **Repair the evaluation of the estimator.** Report per-asset and per-year scores with block-bootstrap intervals, including b1/b2/median baselines on every test asset, and report the pooled score with XRP and 2019 excluded. Replace the mechanical control with one where at least three assets are visible, plus a permutation placebo. Re-center the abstract on the honest figure (30-45%, about the same as the median baseline) and state that the contribution is the diagnostic and the abstention behaviour, not accuracy.
2. **Test the "dollar" interpretation and formalise the model.** Write the shrinkage formula and the identification assumptions (the residuals' covariance, the reference normalisation), show that the common component is not a venue-wide premium (for example with an independent anchor such as the USDT/USD or bank-rail event timing, or a placebo on a pair known to share rails), and give a bounded claim ("relative exchange-unit gap") in the title and abstract.
3. **Make the monitor comparison fair and powered.** Provide threshold sweeps against matched baselines (a two-asset price-gap rule, a tuned z-score), a precise false-alarm definition with the matching window and the exposure denominator, binomial or bootstrap intervals on recall and false-alarm counts, and a sensitivity analysis on the label set. Drop or soften "a third the rate", the "6.5 months before" lead-time claim, and the "separated three shocks" language where the evidence is a null.

A secondary request: use the unused page for these additions, cut Figure 3 and Table 5, and release an anonymous artifact with the label file, hashes and the test logs.
