# Simulated review (Reviewer 3, methodology / statistics / evaluation / presentation / reproducibility)

Submission: "Same Name, Different Unit: Identifying Source-Specific Units in Web Price Fusion" (draft_v7)
Venue: WWW 2027

## Summary

The paper models each source's prices as true values plus a source-specific "unit offset" shared by all of its items. It proposes identifying the offset from cross-item agreement of gaps. A "unit anchor" (an item whose true price is fixed in the true unit, here USDT) is then used to separate a unit shift from source-wide demand. It adds an external-price correction (Kraken's USDT price) because the anchor is itself a claim. The paper gives a proposition (IV/GMM identification of the unit share lambda, with a Hansen J test) and a simulation of size and power. Empirically it uses public exchange candles (Bitfinex, Coinbase, Bitstamp, Binance.US, Kraken, 2017-2025). The main findings are:

- (i) Bitfinex's 2018-19 premium has an anchored slope of 0.97 (interval 0.94 to 1.00) once Tether's external price is netted out, up from 0.71, so the premium was mostly a discount on the ledger dollar.
- (ii) Binance.US's 2023 dislocation passes the same test.
- (iii) A one-offset-per-source-hour correction removes 0.989 of the mean-square gap on withheld assets in 2017-19 and 0.353 in 2020-23.
- (iv) In three "locked" fusion benchmarks, the plain median is hard to beat. Unit-aware fusion wins only when a large group of sources shares a unit that moves by more than venue noise (USDC, March 2023).
- (v) A rule-based alarm monitor with fewer false alarms than price-gap baselines.
- (vi) Accounts of three 2023 shocks and a Chainlink pilot.

## Strengths

- **Honest reporting of negative and weak results.** The estimator ties the plain median (difference 0.000). The calm-year held-out score is only about a third. The paper says "close to, not equal to, one". It reports that the J test cannot detect a depeg that loads equally across anchors. The Discussion states plainly that the scope condition is "a pattern in a small sample".
- **Clean identification idea.** The external-price netting that turns a contaminated anchor into one with slope 1 under a pure unit shift is a neat, transparent idea. Proposition 3.1 is short and checkable. The simulation scenarios S4/S5/S7 directly show when netting and J help and when they do not.
- **Better-than-usual evaluation hygiene.** There is a status table (Table 1) distinguishing pre-registered, locked and post hoc analyses. There are withheld assets, control pairs (shared-dollar Coinbase-Bitstamp), per-year, per-asset and asset-by-time breakdowns, and longer bootstrap blocks that visibly widen the intervals. Table 6 reports losses (T2 1.50, X3 2.46) next to wins.
- **Strong reproducibility intent.** Macro-generated numbers, hashed public inputs, a rebuild gate and tests for stale macros.
- **Real, dated, consequential case studies.** The Bitfinex 2018-19 timeline and the Binance.US and USDC episodes are concrete and useful.

## Weaknesses

Each item is tagged MAJOR or MINOR, with a fixability tag (FIXABLE-IN-TEXT, FIXABLE-WITH-ANALYSIS or STRUCTURAL).

**W1. MAJOR / STRUCTURAL: The central causal claim rests on essentially one episode, plus one more.**
Sec 5.2, Table 3. Bitfinex Nov 2018 to May 2019 (186 daily observations, one persistent regime) carries the headline. Binance.US June-July 2023 is the only replication. The calm years do not replicate: "0.83 in 2021 to 0.86 in 2023" (with an interval of [0.79, 0.94] in 2023). The authors decline to call them unit shifts or demand. The earlier banking episodes (2017-18, the onset on 10 Oct 2018) have no anchor, yet the abstract extrapolates to "Bitfinex's 2018 to 2019 premium". The 2018 subsample slope is 2.06 on 35 days. Effective sample size under a 0.995 hourly autocorrelation is tiny. The "unit shift versus demand" distinction therefore has n of about 2 regimes.

**W2. MAJOR / FIXABLE-WITH-ANALYSIS: Inference for the headline estimate is inconsistent and sensitive to the method.**
Sec 3.1 and 5.2. For one number (0.97) the paper reports a HAC interval of [0.961, 0.981], an hourly block-bootstrap interval of [0.962, 0.980] (Sec 3.1), a daily weeks-block interval of [0.95, 1.00] and a months-block interval of [0.94, 1.00]. The text then says the HAC interval "is narrower than the block-bootstrap interval" and treats the bootstrap as the headline. The simulation shows HAC covering only 0.92 (pure shift) and 0.72 (mixture), with size 0.08. Yet "lambda = 1 rejected (p < 0.001)" is quoted from HAC. Binance.US gets only an HAC interval (0.999, 1.007), with no bootstrap, and "passes" at p = 0.11. Please choose one pre-specified inference procedure, justify it by the simulation, and apply it uniformly (including to Binance.US).

**W3. MAJOR / FIXABLE-WITH-ANALYSIS: The held-out-asset score does not validate the unit interpretation.**
Sec 5.3, Tables 5, 9, 10. The score measures whether the median of other assets' gaps predicts a held-out asset's gap. That is cross-asset commonality, equally produced by common demand. The estimator equals the median baseline b2 (difference 0.000), so the validation is of "gaps are common across assets", not of "units". The headline numbers are also unrepresentative. The abstract's 0.989 (2017-19) comes from 7,388 hours of test assets that "list late", driven by XRP (97%) and 2019 (99%), against a median of 0.378 to 0.389 over test assets and years. The dev assets are near zero (0.012) in 2020-23, and ETC is 0.07. Heterogeneous loadings contradict A1 (equal unit loading for every non-anchor item). Report medians or per-asset results in the abstract, and test A1 directly (per-asset loadings on the offset).

**W4. MAJOR / FIXABLE-WITH-ANALYSIS: The fusion benchmark supports the "scope condition" with a single winning episode and no uncertainty.**
Sec 5.4, Table 6. The abstract's "won when a large group of sources shared a unit that moved ... and not otherwise" derives from X1 alone (0.72 vs 0.77 for a unit-conversion baseline; oracle 0.65). Everything else is a loss or a tie (T2 1.50, X2 1.33, X3 2.46, X4 1.32), and T1 is beaten by CRH (0.88) and by dropping a source (0.89). There are no intervals on any MAE ratio. The oracle is worse than the median in X3 (4.04) and X4 (2.02) and T4 (1.07), which is unexplained. The FUSE and STABLE fusers ("Method of this round", "Earlier unit-aware method (frozen)", "the method's own check") are never defined in the main text. Table 1 says they were tuned over 24 and 15 runs. As written the table cannot be assessed or reproduced from the paper. Add intervals (block bootstrap over hours or days), define the methods, and explain the oracle values.

**W5. MAJOR / FIXABLE-IN-TEXT: The pre-registration and "locked / unseen" claims are overstated relative to what Table 1 itself discloses.**
Sec 4 "Labels", Tables 1 and 6, Sec 5.2. The monitor is listed as "Pre-registered" while "the rule was fitted on Binance.US in 2022-23, and Bitfinex's event windows had been seen". Binance.US is then used as an evaluation venue (4/4 recall, in-sample). The 360-specification robustness grid is described as "fixed in advance", while Table 1 says the anchor tests are post hoc and "not registered". Table 6 says "episodes it had never seen", yet T1 (Bitfinex 2018-19) is the episode that motivated the whole project. The registration is not verifiable under anonymity. Relabel, and report Binance.US monitor results as development.

**W6. MAJOR / FIXABLE-WITH-ANALYSIS: Demand/placebo evidence is weak and mutually inconsistent.**
Sec 5.2 "Demand and placebo". The reverse placebo has 15 hours and a slope of 0.50 with interval [-2.04, 1.84]. It cannot reject either a slope of 0 or of 1, so it is not a placebo in any informative sense. The "21% of the 4,633 agreeing hours" in which the anchor did not follow is not defined (what counts as agreed or followed?), and it uses a different denominator from the 4,434-hour stress window. Table 11 shows only 50% of stress-window hours have |T| <= 0.25|L|, which suggests a much larger non-following share. A real placebo (shared-dollar pair with large gaps, or a permutation or time-shift test) is needed.

**W7. MAJOR / STRUCTURAL: Fit to the venue and generality.**
Title, abstract, Sec 6. The framing is "web price fusion" (loyalty points, marketplaces, platform credits), but every test is on crypto exchanges, and the headline test needs a specially available anchor with an external price. The only non-crypto extension (Kimchi/Upbit, Discussion) is a paragraph with unreported tables, a short 568-hour sample, slope 0.90 and an unexplained "won-unit wedge". The fusion value-add (the fused price) is no better than the median in 8 of 9 locked cells. The WWW contribution to web data fusion is thin. Either scope the title and claims to exchange ledger units or add a genuinely web-style application.

**W8. MAJOR / FIXABLE-WITH-ANALYSIS: The monitor evaluation has tiny counts and an unfavourable operating-point comparison.**
Sec 5.6, Table 7. On Bitfinex, 3 versus 9 false alarms and 7/9 recall come with no intervals. On Coinbase the monitor's recall is 0/5, on Binance.US it is in-sample, and Bitstamp and Kraken events are absent from the table. At matched recall of 0.85 or more, the z-score is the better rule at the high-recall end (1.15 vs 3.44 false alarms per venue-year), which undercuts contribution (4). The relation of the monitor rule (a 100 bps threshold plus a second-asset agreement) to the estimator of Eq. (2) is not explained, so it is not a test of the paper's model. Table 7 episode counts do not reconcile with hits plus false alarms (12 vs 7+3; 18 vs 7+9; 38 vs 9+20; USDT 6 vs 1+2). Explain how episodes map to labels.

**W9. MINOR / FIXABLE-IN-TEXT: Evidence the text relies on is not in the submission.**
Sec 5.2, 5.4, 7. "the full grid is in the artifact", "an injected-bias test in the artifact shows this", "committed tables hold the full sweep". The injected-bias appendix was cut for length yet the text still leans on it. No artifact or anonymous link is given. Reviewers cannot check the 360-spec grid, the operating curves or the label list.

**W10. MINOR / FIXABLE-IN-TEXT: Over-identification and assumptions are under-specified.**
Sec 3.1. The J degrees of freedom are given as "Km-1" but "5 df" in Table 4, with no K and m for each data row. The J test cannot detect the main threat (equal loading). Hansen's J of 2.94 (p = 0.40) is presented as supportive. For Binance.US, adding USDC fails (J = 26.28) and is dismissed as contamination, but the unnetted version passes (J = 2.4), so the J test is not behaving as the theory implies. A3 requires the netting venue to be independent, yet the Bitstamp reference is also the netting venue for USDC. lambda = Cov(u,c)/Var(c) equals 1 whenever Cov(delta,c) = 0, not only under delta = 0. If banking stress moves unit and demand together, the "unit share" label is not a variance share. The sentence that Kraken's BTC price staying close to Bitstamp's (2.8 bps) shows that Kraken is "outside Bitfinex's ledger" is a non sequitur for the USDT price.

**W11. MINOR / FIXABLE-IN-TEXT: Estimator and development process.**
Sec 3. "the unit moves from hour to hour" is given as the reason temporal smoothing failed, while the paper elsewhere stresses persistence (rho_c = 0.995, offsets "persist for months"). The shrinkage constant is typeset "c = 12" (presumably 1/2) but later "re-picked" as 0.25. The estimator is stateless, so the "held-out time" test (Table 5) tests only the one constant. Development counts (12/24/15 runs) are given but the search procedure is not described.

**W12. MINOR / FIXABLE-IN-TEXT: Presentation and structure.**
Empty or near-empty sections:
- Appendix C is one sentence.
- Appendix B has two sentences and no analysis.
- Page 9 is mostly blank.
- The "Three shocks in 2023" heading contains a no-alarm null and a Chainlink pilot.
- "Binance.US.." and "USDC.." have double periods.
- The reference line reads "Proceedings of Proceedings of".
- Sec 4 does not describe the data behind FUSE and STABLE (FTX, SVB, TUSD, FDUSD, 2024-25 quote units).
- GTM is attributed to a survey [8] rather than its original paper.
- The terms "share", "correlation" and "common share" are used interchangeably in Sec 5.5.
- "exchange-year" and "venue-year" are mixed.

## Questions for the authors

1. What is the effective number of independent observations in the stress window under the HAC and bootstrap procedures? Why does the HAC interval (about +/-0.01) differ roughly threefold from the daily months-block interval?
2. Can A1 (equal unit loading across items) be tested directly, for example by regressing each asset's gap on L? ETC (0.07) versus ETH (0.95) suggests otherwise.
3. How were "agreeing hours" and "anchor did not follow" defined (21% of 4,633), and why does this not match the 50% in Table 11?
4. Why does unit-aware fusion in Table 8 equal the open-rail venue alone (6.0 / 6.0; 8.8 / 8.5)? Does the fuser need the analyst to label which venue is "open-rail"? If so, the leave-one-venue-out design is not an independent test of unit identification.
5. What happens to the 0.97 result if the Binance.US data (used to fit the monitor) and the Bitfinex windows (seen before the pre-registration) are excluded from every selection step?
6. How is the oracle in Table 6 defined, and why is it worse than the median in X3 and X4?
7. What are the interval estimates for the FUSE and STABLE ratios?
8. Does the Upbit/Kimchi study appear in Table 1? Where are its tables?

## Score and confidence

**Score: 3 (borderline)**
**Confidence: 4**

The anchor idea and the candour of the reporting are real strengths. The empirical base is essentially one regime plus a replication. The held-out validation tests cross-asset commonality rather than units. The fusion benchmark yields one winning episode with no uncertainty. The pre-registration and locking language is stronger than Table 1 supports. The venue fit is uncertain, but the paper is within reach of an accept after revision.

## The 3 changes that would most raise my score

1. **Unify and defend the inference, and put honest intervals on everything.** Pick one procedure validated by the Table 4 simulation, apply it to Bitfinex and Binance.US alike, and add intervals to every Table 6 ratio and Table 7 count. Reconcile all the quoted intervals for the same estimate.
2. **Show that the unit interpretation, not just cross-asset commonality, is validated.** Test the equal-loading assumption by asset, replace the 15-hour placebo with a real one, define "agreeing hours", report medians instead of the best-case 0.989 in the abstract, and make clear which results lie outside the development and fitting windows (Binance.US monitor, Bitfinex events).
3. **Define the FUSE and STABLE methods and either widen or narrow the claims.** Describe the fusers and the oracle, and explain the oracle values above 1. Either add a non-crypto or additional crypto episode that supports the scope condition, or soften the abstract to "one winning episode of nine", and scope the title to exchange ledger units. Ship an anonymous artifact so the grid, injected-bias test and label list can be checked.

## Internal inconsistencies found

1. **Interval for 0.97.** Abstract: 0.94 to 1.00 (months blocks). Sec 5.2 "therefore mostly a discount": 0.95 to 1.00 (weeks). Sec 3.1: HAC 0.961 to 0.981, block bootstrap 0.962 to 0.980. Sec 5.2 says the HAC interval "is narrower than the block-bootstrap interval", which contradicts Sec 3.1.
2. **Hour counts.** Stress window 4,434 hours (Sec 5.2, Table 3, simulation) vs 4,433 (Table 4 bottom) vs 3,848 (Table 11). The "since the market opened" denominator for the demand check is 4,633. "35 days" for 2018 vs 823 hours (about 34 days).
3. **"Fixed in advance" vs post hoc.** The 360 specifications are "fixed in advance" (Sec 5.2), while Table 1 lists the anchor tests as post hoc and the external-price correction as "not registered".
4. **Pre-registered monitor vs fitting.** Table 1 lists the monitor rule as "Pre-registered" but states it "was fitted on Binance.US" and Bitfinex windows "had been seen". Binance.US is then used as an out-of-sample venue (4/4).
5. **Demand check vs Table 11.** 21% of agreeing hours without anchor following (Sec 5.2) vs only 50% of stress hours with |T| <= 0.25|L| (Table 11). The two are not reconciled and the terms are undefined.
6. **Persistence vs smoothing.** "the unit moves from hour to hour" (Sec 3, reason for no smoothing) vs hourly rho_c = 0.995 and "offsets that persist for months" (Sec 3.1, Sec 5.3).
7. **Table 7 counts.** Episodes do not equal hits plus false alarms in several rows (Bitfinex monitor 12 vs 7+3, price gap 18 vs 7+9, z 38 vs 9+20, Binance.US z 7 vs 4+2, Coinbase z 26 vs 3+24, USDT 6 vs 1+2). The implied years of coverage differ for the same venue across methods (1.31, 1.26 and 2.97 false-alarm rates for 1, 1 and 2 false alarms on Binance.US).
8. **Monitor vs baselines.** The headline comparison (0.43 vs 1.29 vs 2.88) is at a fixed setting. At matched recall the monitor's figure is 0.86, and the z-score is "the better rule at the high-recall end" (1.15 vs 3.44), so the contribution-(4) framing is stronger than the data.
9. **"Three shocks" vs Figure 2.** Sec 5.7 is titled "Three shocks in 2023" but its subsections are Binance.US, Silvergate/Signature (a null) and USDC, plus a Chainlink paragraph. Appendix C says "the two 2023 shocks". The Figure 2 caption says "Three unrelated assets", while the legend shows USDT, BTC and USDC (and the text says bitcoin and Tether).
10. **Binance.US magnitudes.** 557 bps over 530 hours (Sec 5.7) vs -413 bps over 721 hours in Table 11 (June-July). The residual is "-3.5 bps" in text vs "-4" in Table 11. The all-2023 slope 1.01 with interval [0.97, 1.01] has its point estimate on the interval edge.
11. **Abstract vs Table 4 on Binance.US.** The abstract says Binance.US "passed the same test (slope 1.00)". Table 4 shows the two-anchor netted version rejected lambda = 1 with p < 0.001 and J = 26.3. The unnetted version passes J (p = 0.50).
12. **"Indistinguishable from the median."** Sec 5.3 says the estimator is indistinguishable from b2 and "adds nothing measurable". Table 10 shows deltas with intervals that exclude zero (Coinbase-Bitstamp control +0.011 [0.007, 0.017]; Bitfinex-Bitstamp control -0.003 [-0.008, -0.001]; LINK -0.008 [-0.012, -0.001]).
13. **Test years.** "five test years" (Sec 5.3) is never identified (implicitly 2019-2023). The abstract's "2017 to 2019" score of 0.989 is essentially 2019 and XRP. Sec 5.3 lists 0.846 pooled but 0.378 to 0.421 medians.
14. **Block-bootstrap choice.** Sec 5.3 says week blocks "make short blocks too optimistic", yet the headline pooled interval (0.662 to 0.922, Tables 9, 10 and the 0.846) uses week blocks. Table 5 uses calendar months and Table 10 ISO weeks.
15. **Sec 5.2 calm-year slope range.** "0.83 in 2021 to 0.86 in 2023" omits 0.87 (2020) and 0.84 (2022); the 2023 interval [0.79, 0.94] is wider and the other years' intervals exclude 1.
16. **Simulation vs data.** The text equates the simulated depeg bias (-0.254) with the "gap between the data's 0.731 and 0.971" (that gap is 0.240). The raw OLS slope 0.71 (Table 3) and the 0.731 IV/GMM value are used interchangeably.
17. **Flowerday et al.** Abstract: could not test "with their data". Related work: they say it "cannot be tested directly". These are different claims about the same prior work.
18. **Shrinkage constant.** "c = 12" (Eq. 2, probably 1/2) and "re-picking it ... gave 0.25 with the same scores" (Table 5: 0.356 vs 0.353; control 0.052 vs 0.054).
19. **Discussion vs Table 6.** "correct instead of dropping the source" is recommended, but "Drop the most deviant source" (0.89) beats the fuser (0.93) in T1.
20. **Unit-aware equals open-rail alone.** Text: "Units add information about which source is off when prices cannot say". Table 8 shows unit-aware fusion tracks the open-rail venue alone, which presupposes the labelled "open-rail" venue.
21. **Terminology.** "share of the daily ether and bitcoin gaps that was common" equals the correlation (0.95 to 0.99), not the Table 2 "share" statistic. "Exchange-year" vs "venue-year".
22. **Missing evidence.** The injected-bias test "in the artifact" is cited as support after the appendix was removed. The full 360-spec grid, operating-curve tables and label list are not in the submission. There is no artifact link.
23. **Undefined items.** "Method of this round", "Earlier unit-aware method (frozen)", the method's own check ("at most 1.02"), and the oracle. FUSE and STABLE data (FTX, SVB, TUSD, FDUSD, 2024-25) are not described in Sec 4. The Upbit/Kimchi "pre-registered study" is not in Table 1, the abstract, the contributions or Sec 4.
24. **J degrees of freedom.** "chi-square with Km-1 df" vs "5 df" in Table 4 and no K or m for the data rows.
25. **Reference issues.** GTM is attributed to the Li et al. survey [8]. The ACM reference line reads "Proceedings of Proceedings of the ACM Web Conference 2027".
26. **Layout.** Page 9 is mostly empty. Appendix C is essentially a pointer to a figure, and Appendix B is two sentences.
27. **Claims stronger than evidence.**
    - "Bitfinex's 2018 to 2019 premium was thus mostly a ledger-dollar discount" (no anchor before 27 Nov 2018).
    - "Aggregators should correct when a shared unit can move" (one winning episode).
    - "directly" in "a direct test" (assumptions A3 and A4 untested; the J test cannot detect the main threat).
    - "episodes it had never seen" (T1).
    - "every bootstrap interval excluded zero" is a weak criterion when the relevant null is lambda = 1.
