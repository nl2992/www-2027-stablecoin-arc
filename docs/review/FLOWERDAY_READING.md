# Reading notes: Flowerday et al. (2026) and BitMEX "Pricing Bitfinex Default Risk"

## What was read

- **Flowerday, Gandal, Halaburda, Olson, Ardel, "Bitcoin arbitrage: The role of an exchange", Quantitative Finance and Economics 10(3): 624-648, DOI 10.3934/QFE.2026024.** Published 1 Sept 2026 (received 26 Mar, revised 13 Aug, accepted 24 Aug 2026). I read the full publisher PDF (https://www.aimspress.com/aimspress-data/qfe/2026/3/PDF/QFE-10-03-024.pdf), text-extracted, front page through the reference list. It has no appendix or online supplement in the PDF. A keyword search found no ETH, Ethereum, Binance.US, Silvergate, Signature, triangular, index/feed or forecasting content in the body.
- The CEPR DP20567 earlier version ("Bitcoin Arbitrage: The Role of a Single Exchange" per search result) was NOT read. Only its existence and title were seen in a search snippet. Differences between the DP and the journal version are unknown.
- **BitMEX blog "Pricing Bitfinex Default Risk"**: the live URLs (bitmex.com/blog/..., blog.bitmex.com/...) return 404. I read a Wayback Machine snapshot (web.archive.org/web/2020/https://blog.bitmex.com/pricing-bitfinex-default-risk/), full text. It is dated 9 Aug 2016 and bylined Arthur Hayes (not a BitMEX Research report in the usual sense).

## 1. Their data

- BTC/USD only, four venues: Bitfinex, Bitstamp, Coinbase, Kraken.
- Executed-trade ticks (timestamp, price, BTC volume, venue), from Coin Metrics. No quotes, depth, fees or transfer delays.
- 2017-01-01 to 2021-06-01. Hourly index, N = 38,504 hours; 1-minute sampling for episode lifetimes.
- No other assets, no USDT pairs (BTC/USDT is listed as future work), no non-Bitfinex venue stress other than a few placebo events.

## 2. Their method

- Hourly mispricing index A_t = (highest of the four venue-hour minima) / (lowest of the four venue-hour maxima). A_t > 1 only when the venues' hourly price ranges do not overlap, so it is a deliberately conservative, ex-fees gap proxy. It is a max-spread index, not a per-venue gap.
- Leave-one-exchange-out comparison (drop Bitfinex, then each of the others).
- Volatility (SD of 5-min returns in the hour), USD volume, VWAP premium, Amihud illiquidity as controls; OLS (robust SE) on hours with A_t > 1.
- Survival analysis: 1-minute episodes of A_t > 1, Kaplan-Meier, log-rank test, Cox proportional hazards.
- Event study: 13 dated shocks, 24h pre vs 24h post mean of max(0, A_t - 1), two-sided t-test; run with and without Bitfinex.

## 3. Main results with numbers

- Bitfinex is in the mispricing pair in about 80% of positive-dispersion hours. Leave-one-out reduction in positive-dispersion hours: Bitfinex 80.53%; Coinbase 5.80%; Kraken 10.41%; Bitstamp 7.07%.
- Sell-side: the dominant pair is buy elsewhere, sell on Bitfinex (a Bitfinex premium); the next three pairs have Bitfinex on the buy side. From 2018 on, "Bitfinex's elevated BTC/USD price appears to account for most measured arbitrage occurrences".
- Table 1 (A_t): all data mean 0.997, SD 0.016, kurtosis 11.06, 95th pct 1.025, max 1.094; no-Bitfinex mean 0.991, SD 0.011, 95th pct 1.000, max 1.057. 25% of hours show mispricing in the full sample; 5% exceed 2.5%. Max profit 9.4% falls to 5.7% without Bitfinex. With a 1% friction, the full-sample 90th percentile is still 0.8%, the no-Bitfinex 95th percentile is not positive.
- Table 2 (A_t > 1 hours): correlation of A_t with volatility 0.862 (all) vs 0.592 (no Bitfinex).
- Table 3 OLS: R2 for A_t 0.75 (9,632 obs) vs 0.39 (1,875 obs); volatility coefficient 2.73 vs 1.26. Extra controls add little (R2 0.75 -> 0.74 and 0.39 -> 0.35 when dropped).
- Survival: restricted mean duration 11.11 min (with Bitfinex) vs 3.64 min (without); median 2 min both; log-rank p < 0.001. Cox: volatility exp(coef) 0.79 / 0.81 (higher vol, longer episodes); concordance 0.656 vs 0.587.
- Event study (Table 5, excess max(0, A-1) in percentage points): all seven Bitfinex-linked events are significant with Bitfinex and not significant, or show no arbitrage at all, without it. Wells Fargo wire cut 2017-04-11 +0.243 (no-BF 0.010, p 0.473); CFTC subpoena news 2018-01-30 -1.021 (no arb. without BF); Noble Bank 2018-10-01 +0.140; HSBC freeze 2018-10-11 +0.476; Tether depeg 2018-10-15 +2.254; Deltec announcement 2018-11-01 +0.071 (p 0.054); NYAG suit 2019-04-25 +3.454. China events significant in both samples but larger with Bitfinex (ICO ban +1.536 vs +0.966). Placebos (CME futures, forks) near identical in both samples.
- Caveats they state: possible reverse causality; leave-one-out is a descriptive decomposition; the index is not executable profit; the fiat-withdrawal channel "cannot be tested directly".

## 4. How they interpret the Bitfinex premium

Two readings are set out explicitly: (a) expensive Bitcoin on Bitfinex, or (b) "a discount on Bitfinex USD balances"; they say the two are not mutually exclusive. They favour a **fiat redemption risk** reading: Bitfinex on-platform dollars are less redeemable than off-exchange dollars, so "BTC/USD quotes across venues no longer represent identical claims". The mechanism is trapped liquidity (users keep funds on the platform; exiting users buy BTC at the elevated price and withdraw coins). Importantly, they explicitly disclaim the decomposition: the paper does not claim "to have structurally decomposed the Bitfinex premium into a pure Bitcoin overpricing component versus a discounted USD component" (Conclusions). The reading is "consistent with", not identified. USDT is treated as background (a workaround for lost bank rails, with its own depeg risk), not measured as a premium.

## 5. Feature checklist

- ETH or other assets: No. BTC/USD only; BTC/USDT and later episodes are listed as future work.
- Unit/asset decomposition: No (explicitly disclaimed, see above). The index is a max-minus-min venue gap, with no per-venue unit rate.
- Early-warning test: No. The event study is ex post, 24h windows around dated news. Nothing on lead time, false-alarm rates or a monitor.
- Binance.US: No. Binance is mentioned once as a compliant exchange attracting traders.
- 2020-2023: Mostly no. The sample ends 2021-06-01; 2020-21 is in the data but not analysed separately. They say Bitfinex lost dominance by early 2020 and note Deltec rails were reliable by early 2020. FTX (2022) and the March 2023 banking crisis (Reuter 2025) appear only in the literature review and conclusion, not in data.
- Price-feed or aggregator implications: Barely. They note Bitfinex was dropped from the CME BRR in April 2017 over transfer restrictions (Section 4.1) and say researchers and participants should account for venue-specific frictions. No quantification of index or feed contamination.
- Silvergate/Signature: No analysis (March 2023 outside the sample).

## 6. Claim-by-claim overlap table

| # | Our claim | Status | Evidence in Flowerday et al. |
|---|---|---|---|
| 1 | Hourly decomposition of a venue's gap into a unit (ledger-dollar) and an asset component, identified by cross-asset agreement and triangular parity | NOT DONE (conceptual framing only) | Hourly BTC-only index. Sec. 1 raises the "discount on the fiat side of the pair" idea, but Conclusions say the paper does not claim a "structural" decomposition. |
| 2 | Bitfinex dollar is a separate unit throughout 2017-2023, even in calm years (daily BTC-ETH gap correlation 0.95-1.0) | PARTLY | Premium concentrated in Bitfinex, 80.53% leave-one-out effect, 2017-Jun 2021 (Sec. 3.1, Table 1). No ETH, no calm-year unit test, nothing after mid-2021. They say "From 2018 onward" the premium explains most measured gaps. |
| 3 | One unit rate estimated from other assets removes 85% of the gap on held-out assets | NOT DONE | Single asset; no held-out validation of any kind. |
| 4 | Monitor with about 0.4 false alarms per venue-year, firing before the Oct 2018 deposit-pause report and 8 weeks before the USDT premium | NOT DONE | Event study is ex post: Oct 2018 events (Noble, HSBC freeze, Tether depeg) show post-event widening (Table 5), with no lead-time or false-alarm analysis. Note their dated shock set is a useful reference for the Oct 2018 timing. |
| 5 | Silvergate/Signature 2023 rail losses left no discount | NOT DONE | Sample ends 2021-06-01; March 2023 appears only in the literature review (Reuter 2025). |
| 6 | Binance.US 2023 | NOT DONE | Not in data or text beyond a passing mention of Binance as a compliant venue. |
| 7 | Effect on multi-venue indices and price feeds | PARTLY (qualitative only) | Notes Bitfinex removed from the CME BRR in April 2017 for transfer restrictions (Sec. 4.1); a generic call to "account for venue-specific institutional frictions" (Sec. 1). No quantified feed or index bias. |

Closest overlap to flag: the economic story (Bitfinex premium as a discounted-dollar / segmented-claims phenomenon, with the Oct 2018 banking and USDT episodes as triggers) is stated and tested at the venue level by them. Our novelty therefore rests on the identified unit/asset split, cross-asset validation, the monitor, the post-2021 and 2023 episodes, and feed implications, not on the narrative.

## 7. BitMEX post (Arthur Hayes, 9 Aug 2016, read in full via Wayback)

Context: right after the Aug 2016 hack (36% haircut). Estimates minimum lender return of 58.91% pa (0.16% per day) from cold storage share of assets (58.91%), with USD lenders previously earning 30-40% pa. Key relevant passage: "Bitcoin will trade at a premium on Bitfinex, because traders are afraid that their USD withdrawals will not get processed", with premium "the five to seven day default risk of Bitfinex" and divide-by-5-to-7 to get a daily rate; Mt. Gox premium of 10-20% as precedent. Uses BTC only; no data, no test.

| # | Status | Note |
|---|---|---|
| 1 | NOT DONE | Verbal logic only, BTC only. It does treat the BTC premium as pricing USD-withdrawal risk, which is a precursor of the unit idea. |
| 2 | NOT DONE | Written Aug 2016, before the window. |
| 3 | NOT DONE | None. |
| 4 | PARTLY (idea only) | "traders should watch the Bitfinex Bitcoin premium closely" as a gauge of default risk. No test, no thresholds. |
| 5 | NOT DONE | |
| 6 | NOT DONE | |
| 7 | NOT DONE | |

Priority note: the BitMEX post (2016) and Flowerday et al. both predate or precede our claim that Bitfinex's dollar is a separate unit; we should cite both for the interpretation and distinguish ours as measurement and identification.
