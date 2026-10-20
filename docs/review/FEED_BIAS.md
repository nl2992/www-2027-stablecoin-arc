# Price-feed error and signal timing (2026-10-18)

Code: `src/www_rescue/feed_bias.py`. Output: `reports/rescue/feed_bias.json`. Macros: `\NumFeed*` in `paper/generated/rescue_numbers.tex`.

## 1. What a naive multi-venue BTC/USD index gets wrong

**Index construction.** Each hour, the index is the BTC-volume-weighted mean of the venues' BTC/USD log prices, treating every venue's "USD" as the same dollar. This is how aggregators average.

**Benchmark.** The same weighted mean over the open-rail venues only: Bitstamp and Coinbase. For Binance.US 2023 only Bitstamp is available.

**Filter.** The unchanged monitor rule drops a venue-hour when |L| ≥ 100 bps and a second asset agrees with L to within 25%. The second asset is ETH for Bitfinex and USDT for Binance.US.

| Episode | Platform volume share (median) | Naive: max error (bps) | Naive: hours ≥ 100 bps | Filtered: hours ≥ 100 bps |
|---|---|---|---|---|
| Bitfinex 2017 | 0.48 | 634 | 931 | 327 |
| Bitfinex 2018 | 0.52 | 661 | 1,284 | 5 |
| Bitfinex 2019 | 0.31 | 471 | 469 | 0 |
| Binance.US 2023 | 0.23 | 1,366 | 142 | 3 |
| **Total** | | | **2,826** | **335 (88% removed)** |

**How to read it:**
- The 2017 residual is the reference-disagreement problem again. In 2017 the rule compares BTC against Bitstamp with ETH against Coinbase, and those two venues disagreed with each other.
- In flagged hours the filtered error is zero by construction: once the platform is dropped, the index equals the benchmark. The informative numbers are the hours the rule fails to catch, together with the monitor's calm-hour false-flag rate of 1.1% on Binance.US.
- The index here has only two or three venues. In a wider index, the error scales with the platform's share: bias ≈ w × PD. At w = 0.1 and PD = 600 bps, that is about 60 bps.

## 2. When the signal appeared, against dated public reports

The monitor flags a day when it has at least 6 flagged hours.

| Episode | First flagged day | Dated public reports |
|---|---|---|
| Bitfinex 2017 | 2017-04-12 (daily PD 110 bps; 278 bps by 04-14) | 04-09 press reports that Bitfinex has sued Wells Fargo; 04-13 Bitfinex blog on USD withdrawal delays; 04-18 inbound wires refused |
| Bitfinex 2018–19 | 2018-10-08 (PD rising from about 23 bps on 09-28 to 73 bps on 10-07) | 10-02 Bloomberg on Noble Bank; 10-07 Bitfinex denies insolvency; **10-11 deposit pause first reported**; **2019-04-25 NYAG discloses the roughly $850M Crypto Capital loss** |
| Bitfinex 2019 | flagged continuously in Mar 2019; again 04-26 to 05-10 | 04-25 NYAG filing |
| Binance.US 2023 | 2023-05-08 to 05-09 (unexplained episode); then 06-07, 06-13 to 06-16, and 06-21 to 07-13 | 06-05 SEC complaint; 06-09 deposits suspended; 06-13 banks pause USD payments |

**What this supports:**
- The price signal never lags the public news by more than a few days.
- In 2018 it led the first report of the deposit pause by 3 days.
- The discount persisted from October 2018 until it collapsed around 2019-05-10, which is **about 6.5 months before** the NYAG disclosed the underlying loss.

**What it does not support:**
- In 2017 and in June 2023 the signal coincides with the news rather than leading it.
- The May 2023 Binance.US flag has no dated public explanation, so it cannot be called either a lead or a false alarm.

## Sources

- [SiliconANGLE, 2017-04-09](https://siliconangle.com/2017/04/09/bitcoin-exchange-bitfinex-sues-wells-fargo-suspended-wire-transfers/)
- [CoinDesk, 2017-04-11](https://coindesk.com/markets/2017/04/11/bitfinex-sues-wells-fargo-over-bank-transfer-freeze/)
- [Bitfinex tweet of the blog post, 2017-04-13, via Wikipedia](https://en.wikipedia.org/wiki/Bitfinex)
- [Bitcoinist on Bitfinex and Noble Bank, Oct 2018](https://bitcoinist.com/bitfinex-attempts-to-prove-solvency-denies-exposure-to-noble-bank-woes/amp/)
- [The Block, 2018-10-07](https://www.theblock.co/post/1325/bitfinex-is-not-insolvent-crypto-exchange-giant-bitfinex-responds-to-recent-rumors-in-new-blog-post)
- [The Block, 2018-10-11](https://www.theblock.co/news/markets/2018-10-11-bitfinex-suspends-all-fiat-deposits-1579)
- [The Block, NYAG, 2019-04-25](https://www.theblock.co/post/20978/ny-attorney-general-sues-bitfinex-and-tether)
- Binance.US 2023 dates: `src/www_rescue/platform_dollar.py` `PHASES`
