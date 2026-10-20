# Inspiration scan for the WWW 2027 paper

Scan date: 2026-10-20. Method: web search (WebSearch/WebFetch). Every reference below was returned by a search result, and the fetched page or abstract confirmed it exists. Items marked **[unverified detail]** were found but some detail (venue, page numbers, finding) is not confirmed by a primary page. Nothing is cited from memory alone, with one exception flagged in 4 (Hasbrouck 1995, Gonzalo-Granger 1995 are named in a verified paper's methods description). Verify BibTeX before submission.

Framing note from the repo: the median already removes most index error with 3 or more venues, the detector is specific, and Silvergate/Signature gave no discount. A positive contribution therefore has to be about cases where the median is not enough (a shared or majority unit bias, or a venue-specific bias with few venues) or about what the detector gives that a median cannot (a diagnosis, a lead time, an implied haircut).

---

## Angle 1. Unit-aware truth discovery for price feeds

### References
1. Yin, Han, Yu. "Truth Discovery with Multiple Conflicting Information Providers on the Web" (TruthFinder). KDD 2007 conference version; TKDE 2008 journal version. Iterates between source trustworthiness and fact confidence. (Search result carried a 2007 ACM copyright notice; confirm which version to cite.) **[unverified detail: venue year]**
2. Li, Li, Gao, Zhao, Fan, Han. "Resolving Conflicts in Heterogeneous Data by Truth Discovery and Source Reliability Estimation" (CRH). SIGMOD 2014. Joint optimization of truths and source weights over mixed categorical and continuous data; evaluated on weather, stock and flight data.
3. Li, Dong, Lyons, Meng, Srivastava. "Truth Finding on the Deep Web: Is the Problem Solved?" PVLDB 6(2), 2013 (arXiv 1503.00303). Stock and Flight domains; large inconsistency, some very low-accuracy sources, and a finding that fusion methods are not a solved problem. This is the closest "financial price conflicts across web sources" precedent.
4. Zhao, Rubinstein, Gemmell, Han. "A Bayesian Approach to Discovering Truth from Conflicting Sources for Data Integration" (Latent Truth Model). PVLDB 5(6), 2012 (arXiv 1203.0058). Separate source sensitivity and specificity; unsupervised.
5. Dong, Berti-Equille, Srivastava. "Integrating Conflicting Data: The Role of Source Dependence." PVLDB 2(1), 2009. Copy detection: correlated errors across sources must not be counted as independent votes. Relevant because venues sharing a stablecoin share an error.
6. Li, Li, Gao, Su, Zhao, Demirbas, Fan, Han (survey). "A Survey on Truth Discovery." SIGKDD Explorations 2015 (arXiv 1505.02463). Taxonomy; states the reliability-per-source assumption. Also: Ouellet et al., "Truth Discovery Algorithms: An Experimental Evaluation" (HAL hal-01856193, 12 algorithms; venue not confirmed) **[unverified detail]**.

### Gap
All of these model a source's error as random noise or as a scalar reliability weight. None models a systematic multiplicative **unit** bias that is (a) shared by all of a source's claims about different objects, (b) time-varying, and (c) possibly shared by a majority of sources (several venues quoting in the same impaired stablecoin). Reliability weighting down-weights a biased source but does not correct its other claims, and majority-style or median-style fusion breaks when the biased units are in the majority. Our cross-asset co-movement identification is exactly the missing identification device: the same source claims about two unrelated objects (BTC and ETH) must share the unit factor.

### Experiment
Model: log claim of source s on asset a at time t = log truth(a,t) + u(s,t) + e(s,a,t), with u shared across assets. Estimate u by the cross-asset common component per venue; subtract; then fuse.
- Baselines: median, mean, TruthFinder, CRH, LTM (adapt to continuous values), CRH with a venue-by-time weight, plus a "drop USDT-quoted venues" rule.
- Ground truth: a USD-settled reference not used in estimation (for example Coinbase or Bitstamp BTC/USD when evaluating the Binance.com/Bitfinex-affected windows), or the held-out venue; plus synthetic injection of unit bias on clean periods so the true unit is known.
- Metric: mean and 99th percentile absolute index error (bps) in stress windows (Bitfinex 2017-19, USDT Oct 2018, USDC Mar 2023, Binance.US 2023); **breakdown point**, the fraction of venues with a shared unit bias at which each method's error exceeds 50 bps (inject synthetic bias into k of n venues, vary k); unit-recovery RMSE against injected truth; false-correction rate in calm years (should be near zero given the detector's specificity).
- Positive claim to test: the method matches the median when units are clean and beats it by a quantifiable margin once 2 of 5 (or 2 of 4) venues carry the same shifted unit.

---

## Angle 2. How aggregators convert stablecoin- and exchange-quoted prices to USD

### References
1. CoinGecko, "Price Aggregation Methodology" (assets.coingecko.com PDF and coingecko.com/en/methodology). Documents that ticker data is held in BTC base with an internal Bitcoin Price Index; the USD leg is a VWAP of BTC/USD, BTC/USDT, BTC/USDC and BTC/EUR tickers on selected exchanges; USDT and USDC tickers are first converted to USD through a USD_ONRAMP_INDEX, EUR via Open Exchange Rates; tickers older than 30 minutes dropped; tickers more than 4% from the median excluded; manual outlier removal by operations staff.
2. CF Benchmarks, CME CF Bitcoin Reference Rate (BRR / BRRNY) documentation and suitability analyses (cfbenchmarks.com blog; docs.cfbenchmarks.com). USD pairs only, from constituent exchanges meeting criteria (BRRNY list reported as Bitstamp, Coinbase, Gemini, itBit, LMAX Digital, Kraken since Nov 2022; list is dated); volume-weighted median in 5-minute partitions averaged over the hour. This is a design that avoids stablecoin conversion by construction. Stablecoin handling was not confirmed in these sources.
3. CF Benchmarks USDT-Dollar Real Time Index (USDTUSD_RTI, cfbenchmarks.com/data/indices/USDTUSD_RTI): a once-per-second USDT price aggregated from USDT-USD markets of regulated exchanges.
4. Kaiko, Valour CDF index documentation (kaiko.com/kaiko-valour-cdf-index): Binance USDT-quoted futures converted to USD with Kaiko's USDT/USD reference rate. One documented stablecoin-adjustment practice.
5. Pyth Network and CoinMarketCap: **no methodology document found in this scan** for stablecoin-to-USD conversion. Pull Pyth docs (docs.pyth.network) and CoinMarketCap methodology directly before writing about them.
6. Chainlink oracle literature on stablecoin feeds: Chainlink, "Securing Stablecoin Price Feeds and Maintaining Peg Stability" (chain.link/article/stablecoin-price-feeds, vendor article). Yang, Klages-Mundt, Gudgeon, "Oracle Counterpoint: Relationships between On-chain and Off-chain Market Data," arXiv 2303.16331 (2023, preprint): argues USD pricing via a stablecoin pair shifts trust to the issuer, depeg events are hard to detect, and off-chain price information can be recovered from on-chain data to flag anomalies. For the March 2023 USDC depeg specifically, the Fed note (Angle 5 list: Du, Sonawane, Watsky, FEDS Note 2025-12-17) is the verified data-driven account; **no Chainlink post-mortem of the USDC/USD feed was found**.

### Documented failures
Verified in this scan: Oct 2018 USDT at about 0.92 with USDT-quoted BTC near 6,700 versus about 6,400 on Coinbase Pro/Kraken/Gemini USD pairs (Bitcoin Magazine, news); March 2023 USDC secondary-market lows around 0.87 (secondary sources). I did not find a published audit showing a specific aggregator printing a wrong USD price during these windows. That absence is the gap.

### Gap
Aggregator methodology documents exist, but no one has replayed them on historical stress windows to quantify the USD-index error they would have produced, nor separated errors from (i) the conversion stablecoin, (ii) a venue-specific ledger dollar (Bitfinex USD, Binance.US USD), and (iii) asset-specific noise. Our decomposition does exactly that separation, and our five-venue minute data lets us replay CoinGecko's published rules (4% median filter, 30-minute staleness, USDT/USDC to USD via an onramp index).

### Experiment
Implement from public documentation: (a) CoinGecko-style BPI (VWAP over USD, USDT, USDC tickers, USDT=onramp), (b) naive USDT=1, (c) BRR-style USD-only volume-weighted median, (d) our unit-corrected index. Replay on 2017-2025 hourly/minute data.
- Metric: index error in bps versus a USD-only clean reference, reported by window (stress versus calm); number of hours each design exceeds 25/50/100 bps; share of error attributable to unit versus asset component; whether the 4% outlier rule hides or admits the bias (4% = 400 bps, above the 2018-19 Bitfinex discount range of roughly 600-800 bps only at the extremes, so the rule would partly pass it).
- Caveat to state: this replays the published rule, not CoinGecko's production system, and manual interventions are not observable.

---

## Angle 3. Market-implied exchange solvency or credit risk from ledger-dollar discounts

### References
1. Gandal, Hamrick, Moore, Oberman. "Price Manipulation in the Bitcoin Ecosystem." Journal of Monetary Economics 95 (2018), 86-96. Mt. Gox leaked-transaction analysis; suspicious trades tied to price rises; roughly 600,000 BTC.
2. Moore, Christin. "Beware the Middleman: Empirical Analysis of Bitcoin-Exchange Risk." Financial Cryptography 2013, pp. 25-33. 40 exchanges, 18 closed, median lifetime 381 days (press-reported figures; one breakdown looked inconsistent in coverage).
3. Griffin, Shams. "Is Bitcoin Really Untethered?" Journal of Finance 75(4), 2020, 1913-1964. Tether issuance tied to BTC price increases, one entity on Bitfinex. Disputed by Tether/Bitfinex and by Kruger (The Block).
4. Lyons, Viswanath-Natraj. "What Keeps Stablecoins Stable?" Journal of International Money and Finance 131 (2023), 102777. Arbitrage design determines peg deviations; Tether's 2019 changes about halved deviations.
5. Makarov, Schoar. "Trading and Arbitrage in Cryptocurrency Markets." Journal of Financial Economics 135(2), 2020, 293-319. 34 exchanges, 19 countries; gaps larger across countries than within; **common component** across country gaps; widens when bitcoin rises. This is the nearest existing statement of a venue/country-level common component and the paper your decomposition most directly refines.
6. Liu, Makarov, Schoar. "Anatomy of a Run: The Terra Luna Crash." NBER WP 31160 (2023). Sophisticated holders exit first; blockchain transparency speeds runs. Also useful as a run-mechanics reference. Ma, Zeng, Zhang, "Stablecoin Runs and the Centralization of Arbitrage," NBER WP 33882 (2025): Tether permits only about 6 agents per month to redeem, so concentrated arbitrage trades price stability against run risk.

Context for the Bitfinex episode (news/legal, not academic): NY Attorney General action of 25 April 2019 alleging an $850M Crypto Capital loss covered from Tether reserves (TechCrunch, Finance Magnates, Orrick); Bitfinex says the funds were seized, not lost. Mt. Gox: reported spread to Bitstamp of about 20% in late January 2014 and Gox at $124 versus Bitstamp $566 on 21 Feb 2014 (CoinDesk, Bloomberg via search results; cause attributed to withdrawal failures). No peer-reviewed paper directly comparing the Bitfinex USD price with other venues during 2018 was found; this is a gap.

### Gap
No paper converts a venue's ledger-dollar discount into an implied recovery rate or default probability, or checks it against disclosure dates. The Mt. Gox and Bitfinex literature is about manipulation or venue risk without a unit-of-account decomposition. Makarov-Schoar find a common component across a country's gaps but do not interpret it as an exchange-credit claim.

### Experiment
Define haircut h(t) = discount of the venue's unit (after removing the asset component). Implied recovery = 1 - h, and a hazard-like quantity (h divided by assumed withdrawal delay).
- Metric 1: lead time of the first sustained alarm before disclosure (you have about 6.5 months for Crypto Capital); compare against alarms from the raw cross-venue gap, the USDT/USD premium, and a plain BTC/USD gap.
- Metric 2: ROC/precision on a small panel of venue-years (Bitfinex hits, Binance.US 2023, Silvergate/Signature no-hit, calm years), with the honest caveat that n of events is tiny; report exact binomial intervals.
- Metric 3: calibration, e.g. whether the discount's size ordering matches the eventual loss ordering (Bitfinex ~$850M versus venue size).
- Weakness: n of events is very small, Silvergate and Signature are negative controls that read as a boundary (the gap is a **bank-rail-to-exchange** signal only when the venue's own ledger is impaired, not when a banking partner fails but redemption continues). Frame as a scope result, not a failure.

---

## Angle 4. Price discovery and information share when one venue's dollar is impaired

### References
1. Brandvold, Molnar, Vagstad, Valstad. "Price Discovery on Bitcoin Exchanges." Journal of International Financial Markets, Institutions and Money, 2015 (seven exchanges, April 2013 - February 2014; Hasbrouck information share and Gonzalo-Granger; Mt. Gox and BTC-e highest information share per CFA digest). **[unverified detail: exact venue wording]**
2. Pagnottoni et al., extension of Brandvold to January 2014 - March 2017, finding a growing role of Chinese exchanges (as described in a secondary summary; full citation not confirmed). **[unverified detail]**
3. Hasbrouck (1995, Journal of Finance, "One Security, Many Markets") and Gonzalo-Granger (1995, Journal of Business and Economic Statistics): the information-share and permanent-transitory methods named in item 1's description. Not independently fetched; standard citations.
4. Makarov, Schoar (2020), as in Angle 3: segmentation across venues.
5. Gandal et al. (2018), as in Angle 3: Mt. Gox as a venue whose reported prices were distorted.

### Gap
Information-share estimators assume a common efficient price expressed in a common unit. If one venue's dollar is impaired, that venue's price series is cointegrated with the others only after the unit factor is removed, so information shares computed on raw prices attribute the unit shift to the "leader". Nobody appears to have recomputed information shares with and without unit correction around impairment episodes.

### Experiment
Compute Hasbrouck information shares and Gonzalo-Granger weights for BTC/USD across the five venues in Bitfinex stress windows, on (a) raw prices and (b) unit-corrected prices. Metric: change in Bitfinex's information share and its confidence interval; fraction of windows where the ranking of venues reverses; a Monte Carlo with injected unit shifts showing the raw estimator's bias in information share (percentage points) versus the corrected one. Positive claim: raw estimates are biased by an order of 10 or more percentage points in stress windows and the correction removes it.

---

## Angle 5. Early warning of exchange failure from public web data

### References
1. Vidal-Tomas, Briola, Aste. "FTX's downfall and Binance's consolidation: the fragility of centralised digital finance" (arXiv 2302.11371; LSE research online; journal venue not confirmed, found via search). On-chain evidence that FTX relied on FTT leverage, with Terra-Luna as the liquidity shock, and that Binance tweets accelerated the crash. **[unverified detail: journal]**
2. A Finance Research Letters paper on contagion from the FTT collapse across exchanges, finding contagion and flight to safety (title/authors not captured in the search; locate via the Wollongong repository entry "Financial contagion in cryptocurrency exchanges: Evidence from the FTT collapse"). **[unverified detail]**
3. Sapkota (2025), study of 845 exchanges, centralized/transparency/pairs as default predictors, random forest and ensembles; Journal of International Financial Markets, Institutions and Money (venue as reported by the search; osuva.uwasa.fi thesis/paper). **[unverified detail]**
4. Magomedov, Fantazzini (2025), Journal of Risk and Financial Management. 228 exchanges 2011-2024; volume, lifespan and cybersecurity scores as top predictors; forecast combinations. Also an earlier Fantazzini MPRA paper (144 exchanges, 2018-2021, MPRA 110391). Venue details per search listing.
5. Du, Sonawane, Watsky. "In the Shadow of Bank Runs: Lessons from the Silicon Valley Bank Failure and Its Impact on Stablecoins." FEDS Notes, Board of Governors, 17 Dec 2025, doi 10.17016/2380-7172.3958. Granular data on USDC stress and DAI PSM drain in March 2023.
6. Search-attention evidence: a Czech (VSB) study finding Google search volume leads cryptocurrency returns, mainly 2017-2018 (found via dspace.vsb.cz; authors/title not captured). **[unverified detail]** No study was found that tests Google Trends or Reddit as an early warning for FTX/Celsius-type exchange failure; the FTX attention evidence found is post-event (for example Crypto.com search increases after the collapse).

### Gap
Exchange-failure prediction papers use firm-level and governance features (age, volume, cybersecurity grade, number of pairs), not market-implied prices. No paper benchmarks a price-based signal against attention signals for lead time. Our detector is a ready, specific price-based signal.

### Experiment
Build event set: Bitfinex/Crypto Capital 2019, Mt. Gox, FTX, Celsius/Voyager (if your venues list them), Binance.US 2023. Baselines: Google Trends for "<exchange> withdrawal/insolvent", Reddit mention rate, on-chain outflow (where available), the Fantazzini-style static risk score. Metric: lead time (days) of first alarm before the freeze/disclosure date at a fixed false-alarm rate per venue-year; AUC for next-90-day failure. Limitation: only venues in your five-venue set can be scored; FTX and Celsius are not in your data, so the price test is restricted to Bitfinex and Binance.US unless you add FTX data. Be explicit about this; it makes this angle thinner than Angles 1-2.

---

## Angle 6. WWW/KDD/ICWSM/SIGMETRICS (2022-2026) and adjacent work on price feeds, oracles, data quality

I searched for WWW 2024/2025 papers on crypto price oracles, stablecoin depegs and data quality and found **no matching WWW proceedings entry** through web search. The search engine does not index the ACM proceedings well, so check dl.acm.org for The Web Conference 2022-2026 with keywords "oracle", "stablecoin", "price feed", "DeFi", "truth discovery" before claiming novelty. Positioning candidates found, with venue status:

1. Nadler, Schuler, Schär. "Blockchain price oracles: Accuracy and violation recovery." Journal of Corporate Finance 96 (2026), doi 10.1016/j.jcorpfin.2025.102908. Over 150 million observations, 40 Chainlink feeds on Ethereum over 18 months, benchmarked to a centralized exchange; regression on design and market conditions; recovery from target-corridor violations. Closest recent oracle-accuracy paper. Its benchmark is a single centralized exchange, which is exactly where your unit issue would bite.
2. Conti et al. "Analyzing Price Deviations in DeFi Oracles" (2022; University of Padua repository record, venue not confirmed). Measures deviation between sources and the final Chainlink ETH-USD output. **[unverified detail]**
3. Liu, Szalachowski, Zhou. "A First Look into DeFi Oracles." IEEE DAPPS 2021, pp. 39-48 (arXiv 2005.04377). Oracle prices regularly deviate from exchange rates and show anomalies. Pre-2022 but the standard reference.
4. Yang, Klages-Mundt, Gudgeon. "Oracle Counterpoint" (arXiv 2303.16331, 2023 preprint), as in Angle 2.
5. "Safeguarding DeFi Smart Contracts against Oracle Deviations" (arXiv 2401.06044, 2024). Uses Chainlink ETH/USD updates June 2020 - September 2022 to show deviation thresholds (for example 0.08) can leave Aave/dForce under-collateralized. (Authors not captured; preprint.) **[unverified detail: authors]**
6. Ormer (arXiv 2410.07893, Oct 2024), manipulation-resistant pricing oracle; reports 15.3% lower mean absolute price error and 49.3% lower delay versus TWAP on a WETH/USDT feed. Preprint. Note this evaluates against a USDT-quoted series, which is itself unit-exposed.
7. POMABuster, a price-oracle-manipulation attack detector, IEEE S&P 2024 (found via a UBC lab blog; authors not captured). **[unverified detail]**
8. Cong, Li, Tang, Yang. "Crypto Wash Trading." Management Science 69(11), 2023, 6427-6454. 29 exchanges; unregulated exchanges' wash trading above 70% of reported volume. Relevant because venue-level volume and price reliability is a data-quality theme the Web audience knows; also a caution for volume-weighting in aggregators.

Gap versus this literature: it treats the exchange feed as ground truth or treats deviation as noise or manipulation. Nobody models the benchmark's own unit of account as an unobserved, venue-specific, time-varying variable.

---

## Better angles found (outside the six)

A. **Unit-of-account drift as a data-quality dimension, with a released benchmark.** Package the 2017-2025 multi-venue stress windows with injected and real unit shifts as a labelled benchmark for truth discovery, as WWW has a resource/dataset culture. Metric: others' methods' breakdown points on it. Lower risk, and complements Angle 1.

B. **Streaming deployment guard.** A lightweight online filter to place in front of a price oracle or aggregator: compute per-venue unit factor from two unrelated assets on the fly, flag or correct, and report latency, throughput and alarm rate on minute data. WWW "web-scale systems" fit. Metric: detection delay in minutes at a fixed false-alarm budget; compute cost per venue-minute.

C. **Dependence-aware fusion for stablecoin-quoted sources.** Extend Dong et al.'s copy-detection idea: two venues that quote in the same stablecoin share an error, so they should be one vote on the unit, not two. Experiment: effective number of independent sources before and after; error versus the number of nominally independent but unit-correlated sources.

---

## Ranked recommendation (best positive-result potential and WWW fit)

1. **Angle 1 (unit-aware truth discovery), with benchmark A and dependence-aware fusion C folded in.** Best fit: it is an algorithmic contribution in a core WWW/VLDB/KDD area, it attacks a stated limitation of existing methods (reliability weights and median/majority fusion fail when a unit bias is shared by a majority of sources), and your cross-asset identification is a genuine new identification device. The positive result is a breakdown-point improvement over the median, which is where the median's limits are acknowledged, not a head-to-head in calm conditions where you would only tie. Risk: needs a trustworthy ground truth in real windows; mitigate with injection on clean data plus held-out USD-only venues.

2. **Angle 2 (aggregator conversion audit).** Strong web-systems/data-quality framing, concrete deliverable (error in bps by design under replay of publicly documented rules such as CoinGecko's USD_ONRAMP_INDEX, 4% median filter and 30-minute staleness), and it supplies the real-world motivation for Angle 1. Risk: it is a replay of public specs, not production systems; Pyth and CoinMarketCap methods were not found and must be sourced before inclusion.

3. **Angle 3 (market-implied solvency / lead-time), framed as a diagnostic output of Angle 1 rather than a standalone claim.** The 6.5-month Bitfinex lead and the specificity are a distinctive, quantifiable result and tie to a literature (Makarov-Schoar common component, Griffin-Shams) that has not interpreted the venue component as an exchange-credit signal. Rank below the first two because the event count is tiny (essentially Bitfinex and Binance.US; Silvergate/Signature are non-events) and FTX/Celsius are outside your data, so claims need exact intervals and a conservative scope statement. Angle 4 (information share bias) is a cheap add-on robustness exhibit; Angle 5 is the weakest because the public-attention baseline cannot be run on events your data does not cover.
