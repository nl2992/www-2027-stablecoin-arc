# Review of "Same Name, Different Unit: Identifying Source-Specific Units in Web Price Fusion" (WWW 2027, Web Economics and Digital Society)

Reviewer 1. Background: web data integration, truth discovery, data quality.

## 1. Summary

The paper argues that a fusion service can be wrong in a way that source reliability and robust aggregation cannot fix. A source may quote in a nominally shared unit ("USD") that is really a claim on the source itself, such as an exchange's ledger dollar. The paper models each source's log price as true price + a source-hour offset + an item residual (Eq. 1). It identifies the offset by agreement of gaps across unrelated items (BTC, ETH, altcoins). It then uses a "unit anchor", an item with a fixed true price (USDT), to separate a unit shift (slope 1) from source-wide demand (slope 0).

The data are public candles for Bitfinex, Coinbase, Bitstamp and Binance.US, 2017–2025. The main results are:

- A one-offset-per-source-hour correction removes 85% of the mean-square cross-exchange gap on five withheld assets.
- The anchor slope is 1.00 on Binance.US in 2023 and 0.71 on Bitfinex in 2018–19.
- A "monitor" (BTC gap ≥100 bps plus a second asset agreeing) raises fewer false alarms than a plain gap rule at equal recall.
- A case study separates the March 2023 USDC token failure from the June 2023 Binance.US dollar failure.

## 2. Strengths

- The framing is clean. A *source-wide* additive error that reliability weights cannot see is a real and under-discussed failure mode of fusion.
- The paper is unusually honest about negative results. Examples:
  - the estimator "is indistinguishable from the plain cross-asset median";
  - Appendix A admits "unit awareness adds information, not accuracy";
  - the demand placebo has a CI containing 0, and the paper says so;
  - Chainlink shows no inheritance of the depeg.
- The reproducibility discipline is excellent: hash-recorded inputs, generated macros, a test split scored once from a recorded log. Few submissions in this track match it.
- The Coinbase–Bitstamp shared-dollar control and the Bitfinex–Bitstamp separate-dollar control are sensible. The explicit noise-bound analysis (Table 4: fees, ticks, timing variants, lead-lag) is thoughtful.
- The Binance.US 2023 episode is a genuinely nice natural experiment.

## 3. Weaknesses

**W1 [MAJOR] The technical contribution is, by the authors' own account, empty.** Section 5.3: "A median suffices." Table 3 gives Δ vs b₂ = 0.000 [−0.003, 0.002] on test assets. Table 9 shows the "unit-aware median" and plain median give identical numbers. What remains is a labelling of the cross-asset median as a "unit". The abstract's headline ("one offset per source-hour removed 85%") therefore reports the performance of a baseline.

**W2 [MAJOR] The "held-out" result is much weaker than the abstract implies (§5.3, Table 3).**
- "Withheld" means withheld *assets* at the *same hour*. The offset for the scored asset is predicted from other assets' gaps in that very hour. If the generating story is "one common wedge per venue-hour", this prediction works nearly by construction and is not out-of-sample in any sense that matters to a deployed fusion system (new time, new venue).
- The 85% figure is driven by XRP (97%) and by 2019 (99%). The other four test assets score 27–40%, and 2020–23 years score 30–45%. The pooled lower bound is 0.66.
- Dev assets score 44%. The jump from 44% to 85% reflects which assets happen to have high gap variance, not generalisation. A mean-square score is dominated by a handful of extreme 2018–19 hours. A median-absolute-error or per-hour score would be more informative.
- The headline should be "30–45% in ordinary years", not 85%.
- The development loop (12 iterations, scored on dev assets and the control pair, §3) means the *controls were also inside the loop*. They are not independent controls.

**W3 [MAJOR] Identification by the anchor is not convincing (§3, §5.2, Table 2).**
- USDT is not "fixed in the true unit". It is a claim on Tether, and on Bitfinex it is a claim on a sister entity (the paper's own related work cites Griffin and Shams). The 2018–19 Bitfinex episode is exactly when Tether and Bitfinex solvency were entangled, so a slope below 1 or above 1 is uninterpretable. §6 acknowledges "up to its own redemption risk" but the identification claim in the abstract ("which demand alone would not produce") is not tempered.
- Table 2 reports a Bitfinex 2018 slope of 2.06 [1.22, 2.95], which is incompatible with "unit shift = slope 1". It is not discussed in the text. The same table shows slope 0.58–0.61 in 2020–21 and 0.23 and 0.16 in 2022–23. These are small-sample slices (21–28 hours) where the "unit" story does not hold, yet 2018–19 is treated as the finding.
- The slope regresses D on L where L is itself estimated with noise. This is an errors-in-variables problem, so attenuation toward 0 is expected. The "71%" could be a noise artefact in either direction, and no correction or sensitivity analysis is offered.
- Only 50% of stress hours satisfy |T| ≤ 0.25|L| (Table 2). That is a coin flip, not "mostly a unit shift".
- The demand placebo has 15 hours and a CI of [−2.04, 1.84]. It cannot reject anything and cannot support the claim that demand is ruled out.
- The Binance.US slope of 1.00 comes from a window in which BTC/USD and USDC/USD "did not trade" (Table 7 caption). L is evidently measured on a thin, one-sided market, probably via USDT. Dollar rails were closed, so USDT/USD and the BTC gap both reflect the same blocked-redemption friction. A slope of 1.00 is close to mechanical here and does not discriminate between a "unit" and any venue-level arbitrage friction.
- Observational equivalence is the deeper issue. The "unit offset" is any venue-level wedge common across assets (capital controls and withdrawal frictions in Makarov–Schoar terms, or funding constraints). The paper cannot distinguish "the dollar is a different unit" from "the venue is arbitrage-limited". Triangular parity (§3) is mentioned but never tested.

**W4 [MAJOR] Novelty and positioning relative to truth discovery and fusion are thin (§2).**
- No truth-discovery baseline is run on real data. CRH appears only in an injected-bias toy (Appendix A, Table 9), where all fusers fail at k=2.
- The related work omits directly relevant literature:
  - Li et al., "Truth finding on the deep web" (VLDB 2012), which studied stock and flight data with systematic source biases;
  - continuous-data truth discovery with source bias (GTM, CATD and similar);
  - source copy and dependence detection beyond Dong 2009;
  - unit and currency normalisation in schema matching and data integration;
  - the oracle-design literature on aggregation and manipulation resistance.
- Source-specific systematic bias is not new in truth discovery (many models have a per-source bias term), and the additive form is acknowledged as "not new". The remaining novelty is "an anchor", which is a domain-specific instrument and not a method.

**W5 [MAJOR] Venue fit and generality are not demonstrated.** The paper claims applicability to "platform credits, multi-currency marketplaces and loyalty points" (§6). There is no data on any of these. The entire evidence base is four crypto exchanges, two of which carry the identification. A WWW reader will see a crypto-microstructure paper with a web-fusion framing. The "price feeds should label the unit" recommendation is a design opinion with no evaluation of a feed that does so.

**W6 [MAJOR] The monitor evaluation is small, post hoc and mixed (§5.5, Tables 5–6, 10).**
- There are 9 Bitfinex, 4 Binance.US and 5 Coinbase positives. Recall is 7/9, 4/4 and 0/5. Coinbase recall is zero.
- The robust z-score "reached full recall with fewer false alarms, 1.15 … against 3.44". So at high recall the proposed monitor *loses* to a baseline, and the abstract's "less than half the false alarms … at equal recall" holds only at 85% recall chosen post hoc.
- Labels were compiled by the authors after seeing the Bitfinex gap (Figure 1 is in the intro). "Without reference to prices" is unverifiable.
- "False alarms" are episodes without a labelled event. The 8 Coinbase 2017 alarms and Bitfinex's alarms may be real unlabelled events, and the paper itself says it "did not test this".
- The monitor rule is "BTC gap ≥100 bps and a second asset agrees". That is the two-asset gap rule, and the "decomposition" (Eq. 2) plays no visible role. The Table 6 gains over the two-asset rule are mostly ties (0.00 at ≥60%, 1.86 vs 1.86).
- The 33 labels include 14 or so confounders, and the matching window and tolerance are not stated.

**W7 [MINOR] Uncertainty quantification is optimistic.** The ISO-week block bootstrap is applied to series with daily autocorrelation of 0.8–0.97 (Table 4) and multi-month episodes. Week blocks are far too short. Intervals on the pooled test score, the slopes and the Table 7 phases are likely too narrow.

**W8 [MINOR] The 2018 timeline (§5.5) overreaches.** "The prices therefore measured the impairment for about 6.5 months" presupposes the unit interpretation being tested. The paper itself says "This is not a lead over the market". Retrospective narration around a loss disclosure is anecdotal, n=1.

**W9 [MINOR] Table 7 and §5.6 are hard to reconcile.**
- Phase signs flip: +63.8 bps in the withdrawal-halt window versus −600.6 bps in "deposits shut, withdrawals open". The text explains the direction of the premium in one sentence only.
- The USDT-only rail-impaired phase has no BTC row.
- "ledger component accounted for a median 99% of the Tether dislocation" and "token component −95.8 bps" for the USDC run are single-event decompositions with no uncertainty.

**W10 [MINOR] Oracle check is a weak test (§5.6, Table 8).** One episode, 78 hours, and the "share of the feed's sources quoted in USDC" that fixes the predicted slope is never stated numerically. A slope of 0.007 against an undefined null is uninformative. The Chainlink feed is also not a primary source of exchange prices.

**W11 [MINOR] Data hygiene and scope.**
- The fee bands used in §5.4 rest on 4 unverified and 2 inferred schedule entries out of 8. "These offsets are not arbitrage opportunities" is therefore asserted more strongly than the inputs support.
- Kraken is labelled but never analysed.
- Binance.US is only in 2022–25 and enters only the anchor test.
- Bitstamp ETH availability changes sample composition across Table 1 rows.

**W12 [MINOR] Presentation.** The abstract carries about a dozen numbers and is hard to parse. The "development loop" paragraph (12 iterations, 3 kept, 9 discarded) reads as process log rather than science. Notation for L, D, T and PD overlaps across §3 and Table 7. The reproducibility section names an internal package (`www_paper`), which is mildly de-anonymising.

## 4. Questions for the authors

1. What is the identification content of the anchor *beyond* "the venue wedge and USDT dislocation co-move"? What would a demand-driven model with USDT-specific frictions predict differently?
2. How do you reconcile the Bitfinex 2018 slope of 2.06 with your reading? Do you correct for attenuation in L? Please give an errors-in-variables or IV estimate (e.g. L from odd assets, instrument from even).
3. Is the held-out result robust to holding out *time* (fit on 2017–19, score on 2020–23) and to holding out an entire venue?
4. Why is the unit-aware fuser not run, with the same anchor information, against CRH and CATD-type continuous truth-discovery models with per-source bias terms, on the real data and not only on an injected-bias toy?
5. What is the monitor's performance if labels are matched with a window tolerance of ±1 day, ±7 days and ±30 days? How many of the "false alarms" are verifiable events?
6. Can you show a non-crypto case (e.g. marketplace prices in a platform credit, regional-currency quotes) where the same machinery recovers a known unit?

## 5. Venue fit

Marginal. The track welcomes economics of the web, but the contribution is a crypto-exchange measurement study with a data-fusion motivation. The WWW-relevant claims (oracles, price aggregators, platform credits) are either asserted without data or reduced to one Chainlink episode. A finance venue (or a data-management venue with a real multi-domain evaluation) would be a more natural home. For WWW, the web-integration generality needs to be demonstrated, not asserted.

## 6. Novelty versus truth discovery and oracles

- Versus truth discovery: modest. Per-source additive bias and common-factor decompositions are standard, and the paper says as much. Treating a source-wide offset as a unit is a useful reframing, but no algorithmic advance is shown, and by the authors' own tests the estimator equals a median.
- Versus oracle work: the framing "which unit is the benchmark in?" is nice and arguably the strongest idea. It is, however, supported by one oracle episode with a null result.
- Versus finance (Makarov–Schoar, Flowerday et al.): the contribution is the stablecoin-anchor decomposition, which is new in application but rests on a contested anchor.

## 7. Are the held-out evaluation and controls convincing?

Partly.
- Good: the test assets were scored once, the estimator is frozen and causal, and the intervals are reported.
- Not convincing: the held-out split is across assets within the same hours (a weak form of out-of-sample), the pooled test is dominated by one asset and one year, the "controls" were inside the dev loop, and the estimator ties its own baseline. The shared-dollar control behaves as expected (score ≈ 0.04), but ETH alone scores −0.298 there, and the separate-dollar control (0.92) is not a falsification of anything specific to the paper's model. Two pairs are too few to call these controls.

## 8. Is the identification (the unit anchor) convincing?

Not yet. The idea (an instrument fixed in the true unit) is right, but the instrument is contaminated: USDT carries Tether and, on Bitfinex, affiliate risk. The attenuation problem is unaddressed and one slice has slope 2.06. The placebo is powerless (15 hours) and the Binance.US result occurs in a one-sided market where a slope of 1 is nearly mechanical. What the evidence supports is "the venue wedge is common across assets, and USDT co-moves with it". It does not support "the wedge is the unit as opposed to any venue-level friction".

## 9. Scores

- **Overall: 2 (weak reject; scale 1 = strong reject, 5 = strong accept).** The paper is carefully executed and honest, but the contribution is a relabelled median, the headline held-out number is misleading, and the identification and venue fit are weak.
- **Confidence: 4.**

## 10. Three changes that would most raise my score

1. **Strengthen identification.** Fix the anchor's contamination and attenuation. Add an errors-in-variables or IV slope with sensitivity to Tether-specific risk (e.g. a second anchor such as a fiat-redeemable asset, or an independent bank-dollar instrument). Explain the 2.06 slice. Replace the 15-hour placebo with a powered one, ideally several placebo venues and windows. Rule out venue-level arbitrage friction explicitly.
2. **Make the held-out evaluation honest and out-of-sample in time and venue.** Hold out time periods and whole venues, report median-based and per-year scores as the headline (30–45%, not 85%), keep the controls out of the dev loop, and use longer block bootstraps. Drop "contribution is a better estimator" language entirely or beat the median.
3. **Show it is a fusion result, not a crypto result.** Run real truth-discovery baselines with per-source bias (CRH, CATD, GTM, the Li et al. 2012 deep-web setting) on the real data, cite the missing literature, and add at least one non-crypto domain with a known unit (regional currencies, platform credits) where the method recovers the unit. Without this, the WWW framing is not supported.
