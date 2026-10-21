# Review (Reviewer 2): "Same Name, Different Unit: Identifying Source-Specific Units in Web Price Fusion"

Track: Web Economics and Digital Society, WWW 2027
Reviewer background: empirical crypto market microstructure (cross-exchange premia, Tether/Bitfinex, stablecoin runs)
Scale: 1 = strong reject, 3 = borderline, 5 = strong accept. Confidence: 1 = guess, 5 = expert and read in full.

## 1. Summary

The paper argues that a web price-fusion service silently assumes every source quotes in one unit. For crypto exchanges, "USD" is a ledger claim redeemed through banks. The authors model each exchange's log prices as a true price plus a source-hour "unit offset" shared across assets, plus an asset-specific residual (Eq. 1). The offset is identified by cross-asset agreement of gaps to a reference exchange (Bitstamp). Agreement alone cannot separate a unit shift from venue-wide crypto demand, so a "unit anchor" is added: USDT/USD priced on the same venue. A pure unit shift gives a slope of 1 for the anchor's gap on the offset. Demand for the venue's crypto gives a slope of 0.

The main empirical claims, from public hourly and minute candles for 2017–2023, are these:

1. Bitfinex has its own dollar in every year, while Coinbase and Bitstamp share one after 2018 (Table 1).
2. On five assets withheld from development, one offset per exchange-hour removes 85% of the mean-square Bitfinex–Coinbase gap (Table 3). This equals the plain cross-asset median, which the authors admit.
3. The USDT anchor follows the offset one for one on Binance.US in 2023 (slope 1.00). It carries 71% of it on Bitfinex in the 2018–19 stress window (CI 0.56–0.88).
4. Calm-year offsets (4–11 bps) are persistent and shared across assets but sit inside taker-fee bands (Table 4).
5. A rule-based monitor (BTC gap of at least 100 bps plus a second asset agreeing) has fewer false-alarm episodes than a plain price-gap rule at equal recall (Tables 5–6).
6. A timeline for Bitfinex 2018–19 and three 2023 shocks (Binance.US, Silvergate/Signature, USDC) is presented, with a Chainlink-feed check.

## 2. Strengths

- **The question is well posed.** The point that a venue's "USD" is a claim whose value can drift, and that price fusers treat that drift as price information, is clear and relevant to oracles and aggregators.
- **The anchor idea is the right kind of identification device.** It is the only part of the paper that goes beyond a two-way fixed-effects or median-polish decomposition.
- **The Binance.US June–July 2023 episode is a good natural experiment.** Deposits were shut while withdrawals stayed open, and the slope is 1.00 with a tight interval (Table 2, Table 7). The USDC-versus-Binance.US contrast (token component -95.8 bps, ledger component -2.4 bps) is a nice illustration of token versus exchange failure.
- **Honesty and hygiene are unusually high.** The estimator is reported as tying the plain median, the development/test split was scored once, and the 12-iteration loop is disclosed. The placebo is reported as underpowered and the 2017 Coinbase false alarms are listed. Fee-schedule provenance is disclosed, including "4 are unverified". Appendix A concedes that with k = 2 biased exchanges nothing in prices identifies the true dollar. The reproducibility apparatus (hashes, macros, stale-number tests) is excellent.
- **Table 4 is a welcome inclusion.** Timing variants (hourly median, last close, synchronous-only), lead-lag, ticks and autocorrelation address an obvious criticism up front.

## 3. Weaknesses

### Identification

**W1 (MAJOR). The anchor is not demonstrably "fixed in the true unit", so the headline separation of unit shift from demand does not go through (§3, §5.2, §6).**
- The paper states "an exchange-wide crypto boom does not move it". That is not true of USDT. USDT is the funding currency for crypto purchases. Its premium and discount on a venue is the standard measure of crypto demand in the Griffin–Shams, Kimchi-premium and stablecoin-premium literatures. It is itself a crypto asset whose venue-USD price responds to order flow.
- In a venue run (Binance.US, June 2023), holders trying to exit sell USDT for venue-USD in the same way they sell BTC. USDT/USD at -411 bps alongside BTC at -413 bps (slope 1.00) is exactly what a "venue-USD run" predicts. It is also what "all crypto-to-USD conversion is jammed on this venue" predicts. The authors treat these as one thing (a unit shift). A reader who wants the distinction between a unit and a limits-to-arbitrage shadow price on USD in/out of the venue gets nothing from the anchor.
- The anchor rejects only crypto-specific demand that spares USDT. This should be stated precisely and not framed as "demand alone would not produce" the 71%.
- Table 7 notes that BTC/USD did not trade on Binance.US while the rail was impaired. This raises the question of what L is made of in those hours. If L comes from BTC/USDT cross-rates or from the 530 "all legs traded" hours, then L and D may share a USDT leg mechanically. Please state precisely how L and D are constructed on Binance.US and show that they do not share a price.

**W2 (MAJOR). On Bitfinex the anchor shares counterparty risk with the thing it anchors (§5.2, §6).**
- The paper concedes "USDT is such an item only up to its own redemption risk" and then moves on. For Bitfinex this is not a footnote. Bitfinex and Tether share management, and Bitfinex's banking trouble and Tether's reserve and redemption problem are one corporate-group risk. This is the central Bitfinex/Tether history the paper itself cites (Griffin–Shams).
- A USDT/USD price on Bitfinex moving with the Bitfinex BTC premium (slope 0.71) therefore cannot be read as confirming a bank-dollar impairment. It can equally be a joint Tether/Bitfinex solvency discount.
- The 29% residual is not "a minority demand component". It may be Tether's own risk. The 2018 slope of 2.06 (Table 2) indicates a Tether-specific component of the opposite sign that the model cannot absorb.
- The anchor does not exist on Bitfinex before 2018-11-27. The October 10 to November 27 stretch, which contains the first breach of 100 bps, is therefore not anchor-tested at all.

**W3 (MAJOR). Statistical support for the Bitfinex slope is much weaker than the abstract implies (Table 2).**
- The 3,848 hours are daily-median regressions on highly persistent series (daily AC of about 0.95). A one-week block bootstrap understates uncertainty. The effective number of independent episodes is perhaps two or three.
- The slope is estimated on hours selected for |L| of at least 50 bps. L is a noisy BTC-gap measure, and classical measurement error attenuates the slope towards 0. Noise in L alone could produce a slope below 1 and does not require a "minority demand component".
- §3 defines L as the offset estimated from the other items, but Table 2's caption defines L as the BTC gap. Which one is used matters, because only the former is free of BTC-specific noise.
- The abstract reports the pooled 71% and omits the 2018 slope of 2.06 and the 2020–2023 slopes of 0.58, 0.61, 0.23 and 0.16 (n = 21–160 hours).

**W4 (MAJOR). The placebo has no power (§5.2, Table 2).**
- The authors say it themselves: "With only 15 large-gap hours the placebo is directional evidence". The slope is 0.50 with an interval from -2.04 to 1.84. That interval contains both 0 and 1, so it neither confirms the null nor discriminates between hypotheses.
- Coinbase has no USDT market, and the placebo uses Bitstamp's USDT as D. That tests a mismatch (the anchor is on a different venue from the gap) and not "demand on the venue with a USDT market".
- A convincing negative control would be a known pure-demand venue-wide shock on a venue that has USDT. Examples are the May 2021 crash and the December 2017 and early 2021 booms on Bitfinex or Kraken. Show the anchor slope near 0 there, where the offset is large and caused by demand.

**W5 (MAJOR). "Unit" is not separated from limits to arbitrage or segmentation, so the contribution is largely a relabelling of Makarov & Schoar (2020).**
- Any friction that blocks USD movement between a venue and the reference shifts all USD-quoted assets by the same amount. That friction includes wire limits, withdrawal fees, margin funding costs and settlement frictions. The "unit offset" is then the shadow price of venue-USD and not something that says "the dollar is a different unit".
- Calling the shared component a unit is a definition, not a finding. The model has no content that distinguishes "unit" from "common arbitrage friction". Redeemability through banks, the premise of the introduction, is never tested.

### Calm-year offsets: economic meaning

**W6 (MAJOR). The claim "Bitfinex carried its own dollar throughout" is not supported for the calm years (§1, §5.1, Tables 1 and 2).**
- The text says "Bitfinex had its own dollar rate throughout, in calm years as well as". For 2020–2023 this rests on cross-asset agreement alone, which the paper says cannot tell a unit shift from demand.
- The anchor, where it is available, gives slopes of 0.58, 0.61, 0.23 and 0.16 in the calm years (hours 160, 21, 28, 25). Slopes of 0.16 and 0.23 point at demand or noise, and nothing in the paper says otherwise.
- The abstract's "30% to 45% in each year from 2020" is a different statistic from the 0.63–0.80 in Table 1. The reader needs a reconciliation.

**W7 (MAJOR). The calm-year offsets of 4–11 bps are not interpreted.**
- §5.4 concludes they are "systematic but too small to trade" and that a feed "still cares about a persistent bias of a few basis points". That is not a finding about units. At this size a persistent shared gap is what one expects from venue-specific USD costs and frictions. These include funding and margin rates (Bitfinex lending), USD withdrawal and wire fees, and deposit conversion. They also include quote conventions, spread and tick, and different retail and institutional clienteles.
- A 5 bps persistent shared gap is not evidence of "a different dollar". It is what a transfer-cost wedge looks like. The paper gives no test that separates them.
- The fusion implication (a few bps) is also not shown to matter for any downstream use, such as oracle deviation thresholds. Chainlink deviation thresholds of 50 bps or more would swamp it.
- The controls undercut the value of the calm years. The mean correction is 22.2 bps (Bitfinex–Bitstamp) against 2.7 bps (Coinbase–Bitstamp). The abstract uses that comparison as evidence of a unit, but it mostly reflects that one pair's gaps are about 10 times larger than the other's. It is close to tautological.

### Timing and non-synchronous trading

**W8 (MAJOR). Non-synchronous trading can generate a cross-asset "unit" component, and the checks do not fully close it (§4, §5.4, Table 4).**
- If one venue's quotes update more slowly or are staler (low-liquidity alts, 1-minute candle closes, the hourly median of traded-minute closes), then in a volatile hour every asset's gap carries the common market return times the lag. That is a cross-asset-agreeing gap that is not a unit.
- The share statistic 1 - (gETH - gBTC)^2 / gETH^2 is high whenever both gaps are driven by the same market factor. On this evidence the noise-level pair gives share values from 0.02 to -0.34 (Table 4, Coinbase–Bitstamp), so the statistic is volatile when gaps are tiny. It is mechanically high when gaps are large, as in 2017–2019.
- The checks are good but limited. Lead-lag is at one-minute resolution and "peaked at zero minutes" cannot rule out sub-minute staleness. The "Sync" filter (all legs traded in the final minute) still permits stale prices within the minute. Candle closes on Bitfinex and Bitstamp are not time-aligned to the same clock.
- The reported Bitfinex–Bitstamp share range of 0.51–0.84 across timing variants is wide. For 2021 it falls to 0.51 (Last) against 0.63 (Med).
- The Table 3 scores use the last traded close, whereas the Table 1 diagnostic uses hourly medians. Show the whole analysis at one time convention and report sensitivity to a 5-minute grid.

**W9 (MINOR). Held-out assets test cross-item generalisation but not the generalisation that matters.**
- The "test" assets share exactly the same hours and venues, hence the same offset, as the development assets. Holding assets out is therefore close to guaranteed to work if any common factor exists. It says little about unseen regimes or venues.
- The pooled test score of 0.846 is "driven by XRP (97%)", per the text. The other four test assets score 27–40%.
- Since b1 (the BTC gap alone) and b2 (the plain median) match the estimator, the evidence is that gaps in alts follow BTC gaps. That is a (mostly BTC-beta) factor, not necessarily a unit.
- Please hold out time and venue, not only asset.

### Fees and the no-arbitrage band

**W10 (MAJOR). The no-arbitrage band is built to be wide and is not a band on arbitrage (§5.4, Table 4).**
- The band is "the sum of its two venues' base-tier taker fees", 50 to 100 bps. Base-tier retail taker fees are the worst case and not what a market maker or an arbitrage desk faces. Makarov & Schoar and the arbitrage literature use much lower effective costs. At 5–15 bps per side, several of the 2020–2023 Bitfinex–Bitstamp medians of 4–11 bps are at or beyond the band.
- The fee schedule rests on secondary sources: "2 schedule entries rest on dated news articles, 2 are inferred" and four are unverified. A table of bands to the basis point, built on that, is false precision. It is also called "round-trip" while it is the sum of one taker leg on each venue, which is a one-way cross-venue trade with pre-positioned inventory.
- It omits what matters most to the paper's own thesis. If the dollar is a ledger claim redeemed through banks, the cost of closing the gap includes USD transfer, wire and withdrawal fees and delays. This is circular: either the band includes redemption frictions, in which case the "unit" is inside the band by construction, or it does not.
- "Halving every band ... leaves the median gap inside it" is an admirable sensitivity check, but the tail share (">Band") is the object of interest and the paper does not give it under halving.
- Table 4 also shows that in 2017–2019 26–47% of hours are beyond the band, which would be a massive arbitrage violation in an ordinary market. This is consistent with Makarov & Schoar and is interesting, but it is not discussed.
- "These offsets are not arbitrage opportunities" is stated too strongly given the above.

### The monitor: evidence and timeline framing

**W11 (MAJOR). The monitor's evidence is too thin for the abstract's claim (§5.5, Tables 5–6).**
- "Raised less than half the false alarms ... at equal recall" rests on Bitfinex alone: 3 against 9 false-alarm episodes, with recall 7/9 on nine covered labels. There is no interval and no test.
- On Coinbase the monitor has recall 0/5 and 8 false alarms. In Table 6 the pooled monitor never reaches 85% recall, shown as "–". The pooled picture is therefore a failure for the monitor on one of the three labelled venues.
- The trailing robust z is shown as the better rule at high recall. At full recall it has 1.15 false alarms per venue-year against 3.44 for the monitor. The authors' own wording, "so it is the better rule at the high-recall end", makes the headline claim a low-alarm-end result only.
- The number of labelled events is small (33 labels, many of them confounders or pairs of near-simultaneous reports, e.g. 2019-04-25 and 2019-04-30). Label IDs are not chronological, which suggests the label file was reorganised after the fact. "Compiled from public sources without reference to prices" cannot be verified from the manuscript.
- A false alarm is defined as an alarm with no labelled event. Label sets are incomplete by construction, so some "false alarms" may be real unlabelled events. Bitfinex's Nov 2017 episode coincides with the Tether theft and Bitfinex troubles of the time. Appendix B concedes that the 2017 Coinbase alarms "may reflect dollar funding frictions ... we did not test this". Those could be exactly what the monitor is built to detect, which makes the false-alarm metric non-neutral.
- The rule is "fixed before" evaluation, but it is fixed after a development loop on the same data, and its parameters (100 bps, a quarter) are conventional. Please show the threshold sensitivity as an interval over events, not only a curve.
- The sentence "in 2023 it separated an exchange's dollar failure from a stablecoin run" rests on two episodes. In one of them the stablecoin (USDC) is the anchor by construction.

**W12 (MAJOR). The 2018 timeline framing is inconsistent (§5.5 "The 2018 timeline").**
- The paper says "The prices therefore measured the impairment for about 6.5 months" and also "This is not a lead over the market". If the premium was public, then the market knew, and the statement carries no information about whether a monitor adds value.
- It also assumes the premium measured the impairment. The anchor (W2) covers only 2018-11-27 onward, and 2018 has a slope of 2.06.
- The gap first exceeded 100 bps on 10 October 2018. That is ten days after the first bank-partner report and one day before the deposit pause. By the paper's own account the gap followed the news and did not precede it. The "6.5 months" is then a time-since-onset, and the loss of funds disclosed on 25 April 2019 is a distinct event. The Bitfinex/Tether loan disclosure of that day is also the Tether risk event in W2.
- Table 10 also lists labels that would have made the monitor's detection an early or late alarm, but "detection lag" is not reported. Report lag per event (hours from report to first alarm), which is the standard evaluation for a monitor.

**W13 (MINOR). The Chainlink check is a weak null (§5.6, Table 8).**
- A slope of 0.007 against 0.14 for the USDC feed is computed from 78 hours at one episode and one oracle family. It supports "feeds did not inherit the depeg", which is not related to the unit hypothesis.
- With no power calculation, it cannot be taken as supporting the paper's fusion claims.

### Novelty versus Flowerday et al. (2026) and Makarov & Schoar (2020)

**W14 (MAJOR). The incremental contribution is small and framed as larger than it is (§2).**
- The paper concedes that "The additive form is not new". The estimator "is indistinguishable from the plain cross-asset median", and "A median suffices" (§5.3). What remains is (i) the reading of the common component as a dollar unit and (ii) the USDT anchor test.
- Flowerday et al. discuss a Bitfinex dollar-balance discount as a reading of the premium on four exchanges. The authors say "They do not decompose it structurally. We do". But the decomposition is a cross-asset median. I do not see what is "structural" about the paper's version beyond relabelling. The extension to 2023 is real but modest.
- Makarov & Schoar already decompose gaps into a common within-country component and an exchange-specific one, and tie them to capital-control frictions and limits to arbitrage. "We identify an exchange-level component within USD" restates their segmentation result with the assumption that the cause is a "unit". The related literature on Bitfinex/Tether (Griffin–Shams), on the Bitfinex premium as a banking-access story, and on settlement-latency limits to arbitrage is not engaged beyond one-line mentions.
- The "web price fusion" framing carries the novelty claim for this venue, but the fusion content is thin. Appendix A is a synthetic injection that shows that "Unit awareness adds information (which exchanges share a dollar), not accuracy". The extension to "platform credits, multi-currency marketplaces and loyalty points" is asserted and not tested.
- A web-economics reader would want a second domain, or at least a statement of what the anchor would be there.

### Other

**W15 (MINOR). Sample, scope and presentation.**
- The scope is three USD exchanges plus Binance.US. The reference (Bitstamp) is assumed to be the true dollar. The k = 2 failure in Appendix A means that results rest on Coinbase–Bitstamp sharing a dollar, which is itself inferred.
- The abstract says "2017 to 2023", but Binance.US data run 2022–2025 and Table 5 starts it in Oct 2022. The Bitstamp ETH series starts in Sept 2017, and the six-asset hourly Bitstamp data start in 2019.
- The mean-square share is dominated by large-gap episodes (2019 scores 99%). Report the median or a trimmed share, or an episode-level score, for robustness.
- Table 3 has Δ intervals that exclude zero in both directions (LINK -0.008 [-0.012, -0.001] and the shared-dollar control +0.011 [0.007, 0.017]), yet the text says "indistinguishable". Be consistent.
- Figure 3a and the USDC statement "token moved, not the exchange dollar" compare a token component against a ledger component that is itself measured with the Bitstamp reference during a run in which Bitstamp's own USDC price was 1,477 bps below par. State that the reference USD is unaffected.
- The abstract is dense, and a reader cannot tell which result is on which sample.

## 4. Questions for the authors

1. How exactly are L and D computed on Binance.US in June–July 2023, given that BTC/USD did not trade on the impaired rail? Do they share any USDT leg?
2. Can you show the anchor slope in a venue-wide pure-demand episode (for example Bitfinex in December 2017 or Kraken in May 2021) where the offset is large and no rail was impaired? What does the slope do on Bitfinex in the first weeks of 2021?
3. On Bitfinex before 2018-11-27 (the 10 October to 27 November period), what evidence supports a unit reading, since the anchor is not available?
4. How do you separate Tether-specific risk from Bitfinex-bank risk, given the shared parent? Could Bitfinex's USDT/USD plus the BTC/USD premium both be the same Tether discount, and what in the data speaks against it?
5. What is your decision rule for calling a persistent 4–11 bps shared gap a "dollar" and not a transfer-cost wedge? Can you regress the calm-year offset on the known fee, withdrawal-cost and funding-rate series?
6. What does the analysis look like with institutional or high-tier fee schedules and with USD transfer costs added to the band? What share of hours would fall beyond it?
7. What are the exact lags (hours from first public report to first alarm) per labelled event? Which two Bitfinex positives were missed?
8. How sensitive are the Table 5 and 6 results to dropping the Bitfinex 2017 and Coinbase 2017 windows, and to adding the unlabelled but plausible events to the label set?
9. Why is a score for held-out assets, rather than held-out time or venue, the right test of the unit claim? Can you leave out 2018–2019 and test 2020–2023, or the reverse?
10. What would the anchor be, and what would the result be, for a non-crypto domain, so that the title's "Web Price Fusion" is not decorative?

## 5. Overall score and confidence

**Overall: 2 (weak reject; borderline for a revision).**
**Confidence: 4.**

The data work is careful and the Binance.US episode is genuinely interesting. The central inference is that the common component is a unit and not venue-wide demand or limits to arbitrage. It is supported by an anchor (USDT) that carries its own demand and counterparty risk, by one tight result on Binance.US that a run on the venue's USD also explains, and by an underpowered placebo. The calm-year claim and the monitor claims are the weakest. The contribution over Makarov & Schoar is the relabelling, and the estimator is, by the authors' own account, the median.

## 6. The three changes that would most raise my score

1. **Make the anchor test credible, or restate the claim.**
   - Add a negative control with a known pure-demand, no-rail-impairment shock on a venue that has USDT.
   - Add a second anchor with independent risk (e.g. USDC or DAI, or a fiat-pegged or non-crypto item) where possible, especially for Bitfinex.
   - Treat Bitfinex/Tether as a joint-risk case. Fix the L definition and correct for measurement error with a leave-BTC-out offset, and do inference on episodes and not hours.
   - Otherwise narrow the claim to "crypto-specific demand that spares USDT is rejected" and drop "unit shift" as the stated finding.
2. **Give the calm-year offsets and the no-arbitrage band an economic test.**
   - Use high-tier fees plus USD transfer and withdrawal costs.
   - Regress the 4–11 bps offset on observable cost and funding proxies.
   - Verify the fee schedules, or show results are robust to them.
   - Show the full analysis at one time convention and a 5-minute grid, to remove the non-synchronous-trading alternative.
3. **Strengthen and reframe the monitor and the novelty claim.**
   - Report detection lag per event with intervals, and show results with and without the Coinbase 2017 and Bitfinex 2017 windows.
   - Add labels for plausible unlabelled events, and say plainly that the robust z dominates at high recall.
   - Reframe the contribution relative to Makarov & Schoar and Flowerday et al. (the anchor test and the 2023 Binance.US episode are the new parts), and either test a second non-crypto domain or drop the general web-fusion claims.
