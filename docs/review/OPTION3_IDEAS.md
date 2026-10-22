# Option 3 ideas: where unit awareness should win out of sample (2026-10-22)

Read-only strategist note. Nothing was run. Probabilities are my subjective guesses.

## 1. What the three locked tests actually say

| Round | Test result | Reading |
|---|---|---|
| R1 UNIT-TD (`724455b`) | held-out assets: 0.846 of the gap removed; every asset and year positive (XRP 0.97, ADA 0.34, 2019 0.99, 2021 0.30). Control 0.000 | Wins, because the **target is a gap whose size is far above the noise** and the baseline B0 has no cross-asset information. |
| R2 FUSE (`914b3cb`) | test_score 1.063 (loss). T1 0.93, T2 **1.50**, T3 0.95, T4 0.97, T5 0.97. CRH (0.88 / 1.20 / 0.92) beat it on T1–T3. | The median already absorbs one broken dollar among 3–4 sources. |
| R3 STABLE (`ca38772`) | X1 USDC 2023 **0.72**, X2 TUSD 2024 1.33, X3 FDUSD 2025 **2.46**, X4 calm 1.32. Placebo check failed. | Wins only when the shifted unit is a large share of the sources. In 2024–25 the oracle (USD-only median) scored 2.02 (X4) and 4.04 (X3) against Kraken. USD-quoted venues were noisier than the USDT markets. |

Three lessons drive everything below.

1. **Signal-to-noise decides the outcome.** The wins (R1, X1) have unit shifts of 50–1,000 bps. The losses have shifts under about 10 bps against a Kraken truth that itself sits 3–5 bps from any other venue. Whole-window MAE vs Kraken is a noise-dominated metric. A method gets paid only in the tail hours.
2. **Do not tune a fuser against Kraken.** X3/X4 show that "the USD venues" is not a clean truth in 2024–25. Any task whose truth is one venue's USD price inherits that venue's noise.
3. **Unit awareness has a structural edge only where a baseline lacks the information.** That is the case when (i) the unit has no direct market (an exchange dollar, a capital-controlled fiat); (ii) the direct stablecoin/USD pair is thin or missing; (iii) most sources share the shifted unit, so voting fails; (iv) the output asked for (attribution, onset, exposure) cannot be produced from one series.

Case (iii) has a literature precedent. Truth discovery with **dependent sources** (Dong, Berti-Equille and Srivastava, "Truth Discovery and Copying Detection in a Dynamic World", PVLDB 2009) shows that majority voting and independent-source models fail when a majority copies the same upstream. A shared quote unit is such a dependency. This is from memory; I did not re-verify the citation. It gives the paper a Web-data framing for "when the majority shares a unit".

## 2. Ranking (one line each)

1. **Q1. Frozen-method test on untouched majority-unit events, tail-conditional** (b). Effort 3–4 d, P(win) about 0.45, WWW fit high.
2. **Q2. Cross-market depeg detection against single-pair thresholds, at hourly and minute resolution** (d, e). Effort 4–5 d, P(win) about 0.5, WWW fit high. It answers reviewer issue 4.
3. **Q3. Held-out-asset USD recovery for stable-quoted markets with no direct pair** (a). Effort 4–5 d, P(win) about 0.5, WWW fit medium. It is the R1 design in stablecoin units.
4. **Q4. Attribution: which unit moved (token, exchange dollar, asset)** (c). Effort 6–7 d, P(win) about 0.6 but high strawman risk, WWW fit high.
5. **Q5. Single-venue oracle and collateral mispricing (Binance USDe Oct 2025, Chainlink inheritance)** (a, f). Effort 6–8 d, P(strict win) about 0.25, but a good measurement paper. WWW fit medium to high.
6. **Q6. Capital-control FX wedge (KRW, ARS, TRY, NGN) for a held-out coin.** Effort 7–9 d, P(win) about 0.3, known ground (Makarov and Schoar), WWW fit medium.

**Recommendation: pre-register Q1 and Q2 together.** They share one data build, and Q2 fixes the weakest part of the paper (the monitor evidence). Q1 is the top pick and has the sketch in section 4.

## 3. The six formulations

### Q1. Frozen-method test on untouched majority-unit events

- **Task.** Do exactly the R3 task (BTC USD price from all markets, scored against Kraken BTC/USD), but with **zero further tuning**. Use the already-locked `ca38772` fuser and the frozen baselines B0–B4, and score only the hours where the hypothesis applies: the shifted unit carries at least half of the volume **and** the unit is measurably off.
- **Structural reason.** Voting, medians and volume weights break when the majority shares a depegged unit (the dependent-source result). R3 had this only in X1 (USDC), so it won only there. Selecting on the stated condition removes the calm and minority-unit hours that diluted X2–X4. This is stratification by a pre-stated mechanism, not tuning.
- **Events not yet used in dev or test** (S1 May 2022, S2 Nov 2022, S3 Feb 2023, X1–X4 are consumed):
  - Oct 2018: Tether wobble (USDT briefly far below 1 on Kraken);
  - Mar 2020: dash for dollars, with USDT at a premium;
  - Apr–May 2019: Bitfinex/NYAG episode, USDT-quoted majority;
  - Sep 2022: Binance USDC-to-BUSD auto-conversion;
  - Jun 2023: TUSD and FDUSD Binance fee changes;
  - Oct 2025: USDe, wBETH and BNSOL on Binance (verify dates and sizes first).
  Treat the list as candidates. The feasibility gate below decides which survive.
- **Data.** Binance `data.vision` monthly 1m klines for BTCUSDT, ETHUSDT and the other stable pairs (free; the 1s files exist for some pairs; 2025 timestamps are microseconds). Held: Kraken full OHLCVT (the archive is already on disk per `anchor_external.json`), Coinbase, Bitstamp and Bitfinex minutes to 2023. Free: Coinbase/Bitstamp public candles after 2023.
- **Strongest baseline.** B2 (CoinGecko-style conversion through a stablecoin/USD rate, Kraken excluded), CRH over all markets, and the oracle (USD-only median). On the stratum the oracle is the honest ceiling.
- **Metric.** `rel_e` on the stratum S_hi (defined below) pooled over events; MAE, p95 and hours of at least 25 bps. Day-block bootstrap CI on the log ratio.
- **Risk.** (1) Too few S_hi hours, since 2024–25 events were small. (2) The Kraken truth is noisy, and X3 showed the USD-only oracle losing to the median. (3) Ex ante strata can be gamed by choosing thresholds; fix them in the protocol. (4) Honest outcome may be "no gain", which is still a result worth stating: the median is adequate unless the majority shares the unit.
- **Effort.** 3–4 days (the harness exists; the work is data ingestion and the stratum rule).
- **WWW fit.** High. It is the dependent-source claim with a pre-stated scope, and it repairs the "rounds lost" story into "scope conditions".

### Q2. Cross-market depeg detection against single-pair thresholds

- **Task.** Per hour (and per 5-minute bar as a sub-arm), raise an alarm when a stable unit is off by at least X bps from the dollar. The method pools unit evidence from K markets: the offset of one unit estimated from BTC, ETH and alts quoted in it, versus the same assets on the USD venues. Baselines use one series: the stablecoin pair price or a Z-score on it.
- **Structural reason.** The cross-section estimate has noise of about sigma/sqrt(K) (K of 5–10 assets), so at a fixed false-alarm rate its threshold can sit lower, and it still works where the direct pair is thin, delisted, or itself pushed (no BTC-neutral manipulation of one pair moves all K assets). It also names the unit that moved. This is variance reduction, not a better model.
- **Data.** Held: Binance and Binance.US stablecoin markets in event months, Kraken BTC/ETH/USDT, Bitfinex/Coinbase/Bitstamp minutes to 2023. Free: Binance `data.vision` for the stable pairs (USDCUSDT, TUSDUSDT, FDUSDUSDT, USDEUSDT, BUSDUSDT) and more assets; Coinbase and Bitstamp public candles.
- **Labels (independent of the method).** Unit offset ground truth from a liquid USD-venue stablecoin price (Coinbase/Bitstamp/Kraken stablecoin-USD), event windows from `reports/events/*_protocol.json`, and a fixed calm-month set as negatives. Define "event hour" as `|offset| >= 25 bps` on the reference pair, and the lead time as the first alarm minus the first event hour.
- **Strongest baseline.** The pair threshold (the same pair, EWMA-smoothed and un-smoothed), a Z-score with the same calm-period calibration, and a CUSUM on the pair. Also a "median of K assets' own stablecoin crosses" version, which is the fair strong baseline.
- **Metric.** Median lead time at a matched false-alarm rate (per 1,000 calm hours); AUPRC; recall with exact binomial intervals. All thresholds are set on calm months and frozen.
- **Risk.** The liquid pair is usually the fastest instrument, so lead time may be zero. Few events (about six) make recall intervals wide; mitigate by counting every hour above threshold as a test unit with day-block bootstraps. If the pooled estimator only ties, report it as "same speed, names the unit, works without the pair".
- **Effort.** 4–5 days (minute data for the hourly arm is held; the 5-minute arm needs the Binance minute files).
- **WWW fit.** High. It is the monitor claim with intervals, which the simulated review (issue 4) called thin.

### Q3. Held-out-asset USD recovery for stable-quoted markets with no direct pair

- **Task.** Mask every USD market of an asset (say SOL, ADA, DOGE, XRP, LINK). Recover its USD price from its stable-quoted markets plus unit offsets learned only from other assets. This mirrors R1 (0.85 of the gap removed) in stablecoin units, and it is the situation of every Binance-only, perp-only or DEX-only study that treats USDT as 1.
- **Structural reason.** All sources of the masked asset share the shifted unit, so the median is useless and there is no redundancy to exploit. The direct stablecoin/USD pair is the only baseline source of information, and it has noise and gaps. The cross-asset estimate adds K further observations of the same unit.
- **Data.** Held: Coinbase and Bitfinex alts to 2023, Kraken (archive; other pairs need unzipping). Free: Binance `data.vision` alt/USDT pairs and Kraken alt/USD pairs as masked truth.
- **Strongest baseline.** (i) Assume 1 USD; (ii) convert with the stablecoin/USD pair from a non-truth venue (B2); (iii) the same with the median of several pairs; (iv) a naive estimate from BTC alone.
- **Metric.** Fraction of the stable-unit gap removed (R1's metric, 1 = perfect) and tail MAE, per asset, per year, per event; the calm placebo must be non-negative.
- **Risk.** Where the pair is clean and liquid (USDT/USD after 2021), (ii) already removes nearly all the gap, so the gain will concentrate in events and in thin stables (TUSD, FDUSD, USDe). The truth, a single USD venue, adds 3–10 bps for alts. Expected outcome: wins in events, ties in calm.
- **Effort.** 4–5 days.
- **WWW fit.** Medium. Good complement to the existing held-out-asset result, but it repeats R1's design.

### Q4. Attribution: which unit moved?

- **Task.** For each flagged dislocation, classify it as (a) token/stable unit, (b) exchange dollar (venue-specific USD), (c) asset-specific shock, or (d) venue-asset microstructure. Score against labels.
- **Structural reason.** No single series can separate these. The factor structure can: a unit shift is common across assets within a (venue, unit); an asset shock is common across venues within an asset; a venue-dollar shift is common across assets within a venue. The two-way structure identifies the class.
- **Labels.** (1) Real events with labels from the existing event protocols and the anchor-confirmed Bitfinex window (slope 0.97 after netting out the external USDT price, in `anchor_external.json`): USDC, TUSD, FDUSD, UST, Bitfinex 2018–19, Binance.US 2023, plus asset-specific negatives (single-coin delist or hack days). (2) **Semi-synthetic injection**: add a known shift of known class to real hourly data (real noise, known truth) at sizes from 10 to 300 bps. Report both separately and say plainly which is which.
- **Strongest baseline.** A multi-series, non-unit method, otherwise it is a strawman: PCA on the venue-by-asset gap matrix, robust two-way fixed effects, and a CRH residual attribution. The naive one-pair threshold goes in as the floor.
- **Metric.** Macro F1 and per-class recall at a fixed false-alarm rate; onset error.
- **Risk.** Circularity (labels derived from the same structure), and a reviewer saying that two-way fixed effects "is" the method. Mitigate with external labels, injection that is fixed before any estimator is run, and PCA/FE as named baselines. Real-label count is small (about 6 events), so the injection arm carries the statistics.
- **Effort.** 6–7 days.
- **WWW fit.** High (data-source attribution is a natural Web-data question), but it is the largest design risk.

### Q5. Single-venue oracles and collateral mispricing

- **Task.** In a setting with one source (a single venue's order book or a single DEX pool), measure how much of a unit or venue-local dislocation reaches the USD price used for collateral, and whether a cross-market unit estimate would have flagged the oracle value as unit-driven.
- **Cases.**
  - Binance USDe, wBETH and BNSOL, Oct 2025: as I recall, Binance's spot order book printed USDe far below 1 (about 0.65) while on-chain and other-venue prices stayed near 1, and Binance's own price fed collateral valuation. **Verify this from primary sources before using it.**
  - Chainlink USDC/USD and ETH/USD during Mar 2023 (the heartbeat and deviation-threshold lag): read via the free Alchemy key (historical `latestRoundData` or `getRoundData`, archive calls).
  - Uniswap v3 ETH/USDC against ETH/USDT pools (slot0 at hourly blocks).
- **Structural reason.** With one source there is no median and no redundancy. Whether a price is unit-driven can only be answered from outside it.
- **Data.** Free: Chainlink via Alchemy, Uniswap pool state via archive `eth_call`, Binance `data.vision` klines, Coinbase and Kraken candles. Held: the Chainlink reads already used.
- **Strongest baseline.** The oracle value itself; for the inheritance question, an OLS slope of oracle error on the cross-market unit offset with HAC intervals. A "strict win" needs a corrected value that beats Chainlink's own, which is unlikely.
- **Metric.** The inheritance slope with a CI; hours in which the oracle error exceeds a liquidation buffer (grid of LTV buffers; a hypothetical position grid, not real positions); correction error against a cross-venue reference.
- **Risk.** Chainlink is aggregated and probably already robust; the slope might be near 0, which is itself a finding but not a "win". Liquidation counts need on-chain data that is not free in bulk, so use a hypothetical position grid.
- **Effort.** 6–8 days.
- **WWW fit.** Medium to high, as measurement. Related work I found: "Safeguarding DeFi Smart Contracts against Oracle Deviations" (arXiv 2401.06044), "A First Look into DeFi Oracles" (arXiv 2005.04377), Nadler, Schuler and Schär on Chainlink accuracy (J. Corporate Finance 2025, 150M observations; found through a search result, not read), and an NDSS 2026 paper on Chainlink OCR price deviation under Byzantine behaviour. None of them treats the quote unit as a separate state, which is the gap.

### Q6. Capital-control FX wedge for a held-out coin

- **Task.** In markets quoted in a local currency under controls (KRW on Upbit and Bithumb, ARS, TRY, NGN, RUB 2022), estimate the unit wedge (the de facto local-currency dollar) from some coins and nowcast the wedge of a held-out coin, against the official FX rate.
- **Structural reason.** The wedge is tens to hundreds of bps to double digits of percent, far above noise, so the R1 regime (large signal) applies. The official FX rate is a bad baseline by construction.
- **Data.** Free: Upbit and Bithumb public candles, Binance `data.vision` for local-fiat pairs (BTCTRY, BTCBRL, and others where listed), official FX from FRED or central banks, parallel-market ARS from a free public API. Not held.
- **Strongest baseline.** The direct USDT/local pair, if one exists (it often does, so it will likely tie or beat the method); lagged wedge; official FX.
- **Metric.** Held-out-coin wedge error in bps; fraction of gap removed.
- **Risk.** Known results: Makarov and Schoar (JFE 2020) and Choi, Lehar and Stauffer on segmented markets. A direct stablecoin/local pair is the unit baseline, so the incremental claim is small. Scope creep from three to six currencies.
- **Effort.** 7–9 days.
- **WWW fit.** Medium.

## 4. Recommendation and pre-registration sketch

### Pre-register Q1 and Q2 on a shared data build

**Q1 (primary) sketch.** Write the protocol and commit it before downloading any new event month.

1. **Frozen objects.** Fuser at `ca38772` with no edits; baselines B0, B1, B2, B3, B4 and the oracle exactly as in `program_stable.md`; Kraken BTC/USD as truth, excluded from all fusion.
2. **Feasibility gate, volumes and stable/USD rates only, no price errors.** For each candidate event window, compute from volumes the share of BTC volume in the shifted unit, and from a **non-Kraken** stablecoin/USD price (Bitfinex, Bitstamp or Coinbase) the unit offset. Define the stratum S_hi as the hours where (share >= 0.5) and (|offset| >= 25 bps). Keep events with at least 40 S_hi hours; the study needs at least 200 S_hi hours pooled over at least 4 events. If it falls short, stop and report it as descriptive.
3. **Primary endpoint.** Mean log(`rel_e`) on S_hi versus B0 (fuser MAE over B0 MAE), pooled, with a day-block bootstrap (1,000 draws, seed fixed). Success requires the upper 95% bound below 0.
4. **Co-primary comparisons.** The fuser must also beat B2, B3 and CRH on S_hi (same test), because B2 is the real commercial baseline.
5. **Secondary, reported but not gating.** Calm months outside the events (the placebo must stay within 1.02), p95, hours at least 25 and at least 50 bps, per-event table, and the oracle gap.
6. **Fixed in advance:** event windows, thresholds (0.5, 25 bps), the 30-day warm-up, and the seed. Dated entries in the paper's "what was fixed when" table (review issue 7).
7. **Pre-stated failure reading.** If the primary endpoint fails, the paper claims only identification, detection and the scope condition "a median is adequate unless a majority shares the unit and the shift exceeds the venue noise". No new tuning round.

**Q2 (second) sketch.** Reuse the same events and the same non-Kraken reference pair for labels. Fix K assets, the EWMA span and the calm-month calibration before looking at events; report lead time at a false-alarm rate of 1 per 1,000 calm hours for the pooled estimator, the pair threshold and the pair CUSUM, with day-block bootstrap intervals. Pre-state: "success = lower median lead or equal lead with 10% or fewer false alarms; tie is reported as a tie."

**Not recommended for now.** Q5 and Q6 are separate studies, not additions. Q4 is attractive for the paper's story but needs a labelling protocol that survives a "strawman baseline" objection; do it only after Q1 and Q2 are locked.

## 5. Literature and sources consulted

The searches were shallow and returned few papers. I could not confirm the full text of any item.

- Safeguarding DeFi Smart Contracts against Oracle Deviations: https://arxiv.org/pdf/2401.06044
- A First Look into DeFi Oracles: https://arxiv.org/pdf/2005.04377
- Chainlink OCR deviation (NDSS 2026): https://www.ndss-symposium.org/wp-content/uploads/2026-f458-paper.pdf
- Nadler, Schuler, Schär on Chainlink accuracy (listing only): https://wwz.unibas.ch/de/newsdetails/new-publication-by-matthias-nadler-kathrin-schuler-and-fabian-schaer/
- Stablecoin depeg early-warning preprint (cusp catastrophe, Research Square): https://www.researchsquare.com/article/rs-11131248
- Aggregation methodologies (CoinGecko, CCData CADLI, Deribit/Coinbase index): https://www.coingecko.com/en/api/price-aggregation-methodology , https://downloads.coindesk.com/cd3/CDI/CADLI-Methodology.pdf , https://support.deribit.com/hc/en-us/articles/38373568169501
- Binance public data repository: https://github.com/binance/binance-public-data/
- Wash trading (Falk, Tsoukalas, Zhang): https://arxiv.org/pdf/2311.18717v1

Gaps: I found no WWW, KDD, FC or AFT paper that applies truth discovery to crypto reference prices or treats the quote unit as a latent state. That absence is encouraging for novelty, but it comes from a few keyword searches, not an exhaustive review. The practitioner indices (CoinGecko, CCData, Deribit) all use median or clip-to-band rules with USD conversion at a stablecoin rate. They are the real-world analogues of B0, B2 and trimmed baselines.

## 6. Data status summary

| Need | Held | Free, to fetch | Needs approval or a key |
|---|---|---|---|
| Minute candles, Bitfinex/Coinbase/Bitstamp, 2017–23 | yes | after-2023 from public APIs | no |
| Binance, Binance.US stable markets, event months | yes | other months from `data.vision` (check each pair's listing) | download approval |
| Kraken BTC/ETH/USDT 2013–2026 | yes | other pairs: the OHLCVT archive is already local (confirm and unzip) | no |
| Chainlink reads | free Alchemy key | historical rounds via archive calls | key rate limits |
| Uniswap pools, Upbit/Bithumb, FX | no | yes (archive RPC, public APIs, FRED) | download approval |
