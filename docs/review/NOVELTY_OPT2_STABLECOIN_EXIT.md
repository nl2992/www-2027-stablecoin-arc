# Novelty check: Option 2, "stablecoins as the escape valve"

Date: 2026-10-20. Method: web search only (WebSearch and WebFetch). No full-text PDF reads except abstracts and landing pages. Status tags: VERIFIED = title, authors, year and venue seen on a primary or index page. PARTIAL = existence confirmed, but venue or details come from secondary pages. UNVERIFIED = only news, blog or aggregator coverage. Nothing below is cited from memory alone.

Idea under test: when an exchange's ledger USD is impaired (fiat withdrawals blocked), users exit through on-chain stablecoins. The ledger-dollar discount is then bounded by the stablecoin exit cost. Three testable parts:
- (T1) the on-platform USDT/USD price tracks the ledger-dollar discount;
- (T2) the discount is smaller when a stablecoin exit exists;
- (T3) on-chain stablecoin outflows from exchange wallets rise during the discount.

## (a) Closest prior works

| # | Work | Status | What it shows | Overlap with the idea |
|---|------|--------|---------------|-----------------------|
| 1 | Flowerday, Gandal, Halaburda, Olson, Ardel, "Bitcoin arbitrage: The role of an exchange", Quantitative Finance and Economics 10(3):624-648, 2026, doi 10.3934/QFE.2026024. CEPR DP20567 (2025) is an earlier version, "Bitcoin Arbitrage: The Role of a Single Exchange". | VERIFIED (journal page). The CEPR page returned 403, so the DP details come from a search snippet. | Tick data for Bitfinex, Bitstamp, Coinbase and Kraken, 2017 to mid-2021. About 80% of hours with cross-exchange BTC/USD dispersion involve Bitfinex. Excluding Bitfinex cuts the upper tail and the volatility correlation (0.86 to 0.59). The Bitfinex premium is read as fiat redemption risk: on-exchange USD cannot be redeemed as reliably as off-exchange USD. Fiat gateways are the limit to arbitrage. Event studies cover banking stress and regulation. | PARTIAL, and the closest. It owns the claim "ledger USD is impaired, so there is a venue-specific discount/premium". USDT appears only in a figure caption (the Oct 2018 depeg). It does not model the stablecoin exit, does not use on-chain flows, and does not cover Binance.US or FTX. |
| 2 | Griffin and Shams, "Is Bitcoin Really Untethered?", Journal of Finance 75(4):1913-1964, 2020, doi 10.1111/jofi.12903. SSRN 3195066. | VERIFIED for JF, 2020, pp. 1913-1964, doi (index page). Volume and issue not seen on a page. | Uses blockchain data. Tether issuance follows BTC drops and coincides with BTC gains, which they attribute to a single actor on Bitfinex and read as supply-driven. | None on the exit idea. They treat USDT as a price-support instrument and do not study the USD discount or exit routes. Background only. |
| 3 | Lyons and Viswanath-Natraj, "What keeps stablecoins stable?", Journal of International Money and Finance 131 (2023), article 102777, doi 10.1016/j.jimonfin.2022.102777. NBER w27136 (2020). | VERIFIED. | Peg deviations of USDT (and DAI, WBTC) are explained by arbitrage design. The 2019 move to Ethereum and decentralised issuance roughly halved deviations. A NY Fed discussion reports USDT/USD deviation averaging about -28 bp, with a 6.5-day half-life, pre-Ethereum (average of Bitfinex, Bittrex and Kraken). | PARTIAL on T1's input. Gives the daily USDT/USD series and the redemption-arbitrage framework. It is not about exchange ledger-dollar impairment, and it uses a cross-exchange average, not venue-specific prices. |
| 4 | Ma, Zeng, Zhang, "Stablecoin Runs and the Centralization of Arbitrage", NBER w33882 (May 2025); earlier drafts 2023. | VERIFIED. | Only a few agents can redeem Tether at par in a given month. Efficient arbitrage stabilises price but raises run risk. | Slight. It supplies the "off-platform redemption cost" ingredient (who can redeem, at what cost). It is not about exchange fiat rails. |
| 5 | Wei, "The impact of Tether grants on Bitcoin", Economics Letters 171:19-22, 2018, doi 10.1016/j.econlet.2018.07.001. | VERIFIED (IDEAS listing). | VAR: Tether issuance does not predict BTC returns, but it moves volume. | None. |
| 6 | Gorton, Klee, Ross, Ross, Vardoulakis, "Leverage and Stablecoin Pegs", NBER w30796 (Dec 2022); JFQA version (listed on the JFQA site, 2025). | VERIFIED for NBER and SSRN. JFQA publication details PARTIAL. | Stablecoins hold their peg because holders earn indirect compensation by lending to leveraged traders. | None for this idea. |
| 7 | Makarov and Schoar, "Trading and arbitrage in cryptocurrency markets", Journal of Financial Economics 135(2):293-319, 2020. | VERIFIED for venue and year. Volume and pages come from a secondary article. | Large persistent cross-country gaps (Kimchi, and the like). Arbitrage is limited by capital controls and the need to settle in fiat. | PARTIAL. Sets the "capital controls cause gaps" frame. Cross-border, not exchange-ledger, and does not study stablecoins as the exit. |
| 8 | Auer, Lewrick, Paulick, "DeFiying gravity? An empirical analysis of cross-border Bitcoin, Ether and stablecoin flows", BIS Working Paper 1265, 8 May 2025. | VERIFIED. | Gravity model for 184 countries, 2017 to 2024. Stablecoin flows are driven by transactional motives and remittance costs. Capital flow management measures appear ineffective, and flows for some assets rise after they are introduced. | PARTIAL on the "stablecoins are the escape from controls" prior, at the country level. It does not look at exchange-level fiat-rail impairment. |
| 9 | Reuter, "Decrypting Crypto: How to Estimate International Stablecoin Flows", IMF Working Paper 2025/141, July 2025. | VERIFIED (IMF page). | Estimates stablecoin flows by geography with ML on wallets. Flows track dollar demand. The 2023 banking crisis disrupted North American outflows. | Slight. A methods precedent for on-chain flow data (T3). It does not study exchange impairment. |
| 10 | Patel and Rose, "A Retrospective on the Crypto Runs of 2022", Chicago Fed Letter No. 479, May 2023. | PARTIAL (index and news coverage; the PDF was not opened). | Runs on Celsius, Voyager, BlockFi, Genesis and FTX. Large accounts withdrew first. FTX saw about 25% (one account) to 37% (another account) of customer funds leave in a few days. | Slight. Run evidence on the FTX withdrawal side (T3-adjacent). It does not distinguish stablecoin exits and does not look at ledger-USD price discounts. |
| 11 | Industry on-chain commentary: Nansen figures reported by The Block (Nov 2022, about $950M USDC, $400M USDT and $195M BUSD leaving exchanges in 24h, industry-wide); Arkham via CoinDesk (FTX balances down 87% in 5 days); Glassnode "The Fall of FTX" (week 46, 2022). | UNVERIFIED as research (news and blog level). I did not find Kaiko, Chainalysis or Coin Metrics pieces on this. | Descriptive outflow charts. | PARTIAL on T3 for FTX only, descriptive, with no price link and no identification. |
| 12 | Contemporaneous commentary: Bitcoin Magazine ("Tether's peg slips, bitcoin price distorted across market", Oct 2018); Blockworks and Forklog on Binance.US, June 2023 (BTC/USD at a discount to BTC/USDT with arbitrage blocked, a thin USD book, and USD balances to be converted to USDT). | UNVERIFIED as research (journalism). I did not retrieve exact dates or magnitudes. | The USDT pair and the USD pair on one venue diverge when fiat rails fail. Journalists explain it with the same arbitrage-closure story. | PARTIAL on T1 as an observation. No test, no estimates, and no exit-cost bound. |
| 13 | Medium blog posts (A. Kruger, "Tether Arbitrage and the Dollar Peg"; Coinmonks "Second Tether Bubble") | UNVERIFIED (blogs). | Describe the loop "buy cheap USDT, deposit to Bitfinex, withdraw USD at par", and the end of 1:1 USDT-to-USD crediting on 27 Nov 2018. | Mechanism only, not evidence. |

Not found in any search:
- An academic paper on stablecoin P2P premia in Argentina, Turkey or Nigeria. All hits were blogs or promotional pieces. Treat that literature as unchecked.
- A paper on Kimchi premia via a KRW/USDT premium.
- An academic Mt. Gox 2013 USD-withdrawal-freeze price study. The news confirms the June 2013 suspension of USD withdrawals; no discount study turned up.
- Any paper that links an exchange's fiat-rail impairment to its own stablecoin-pair price AND to stablecoin outflows AND tests a bound.

Searches were broad but not exhaustive (no SSRN, NBER or conference-program crawls, and no search of FC, AFT, WWW or KDD proceedings). A miss is not proof of absence.

## (b) Verdict: PARTLY NOVEL

Already done:
- The core observation that a venue's ledger USD trades at a discount, or its BTC at a premium, because on-venue USD is hard to redeem. This is the Flowerday et al. paper (QFE 2026; CEPR 2025) for the Bitfinex case, and it is also journalism for Binance.US 2023.
- The background fact that USDT/USD deviations are governed by redemption arbitrage (Lyons and Viswanath-Natraj; Ma, Zeng, Zhang).

Not shown in anything I found (the new sub-claims):
- T2 (stablecoin-exit bound), the main new claim: an explicit cost-of-exit bound on the ledger-dollar discount, stated as a function of stablecoin on-platform price, on-chain withdrawal fees and queues, and off-platform redemption cost, together with the test that the discount is smaller when a stablecoin exit exists.
- T1 as a venue-specific, high-frequency quantitative result, with USDT priced on the impaired venue itself rather than as a cross-exchange average. Only journalism mentions it.
- T3 conditional on episodes: on-chain stablecoin outflows from exchange wallets tied to the discount, across several episodes (Bitfinex 2018-19, Binance.US 2023, FTX 2022, Mt. Gox 2014). Nansen-style descriptive charts exist for FTX only.

Risk: Flowerday et al. is close in spirit, and a reviewer could call the idea "their story plus a bound". The paper must lead with the bound and the exit-cost decomposition, not the discount itself.

Caveats on the claim as stated: in the Bitfinex 2018 case USDT was itself the vehicle by which USD was redeemed (USDT credited 1:1 for USD until 27 Nov 2018), so USDT is not an independent exit there. For FTX and Mt. Gox, no ledger-USD discount of the same kind is documented in the sources I found, and Mt. Gox predates USDT. Which episodes truly have a stablecoin exit is therefore a first question to settle with data.

## (c) New evidence needed to be publishable

1. A clean cross-episode design (staggered events): the same discount measure before, during and after, with and without a usable stablecoin exit (for example, Binance.US with USDT/USDC withdrawals open vs paused). Identification must separate exit availability from general panic.
2. A measured exit-cost bound, computed event by event, and a test that the observed discount stays inside it (or touches it when the exit is congested). This needs on-chain withdrawal fees and confirmation delays, plus the secondary-market USDT/USD and USDC/USD price off-platform.
3. T1 shown with venue-level data: the venue's own USDT/USD (or USDT/USDC) quote against the BTC/USD vs BTC/USDT basis, with lead-lag or cointegration evidence, not only plots.
4. T3 with labelled exchange wallets: net stablecoin outflow from the venue's hot and cold wallets, split by stablecoin, aligned to the discount at hourly resolution. Control for ordinary outflows on other exchanges that day.
5. Placebo and robustness: periods of no impairment, other venues in the same period, and a pre/post structural break (for example, Nov 2018 USDT redeemability at Tether).
6. A short theory or accounting identity for the bound, so the contribution is not purely descriptive.
7. Positioning against Flowerday et al., Lyons and Viswanath-Natraj, and Ma, Zeng, Zhang, with an explicit statement of what each does not do.

## (d) Data needed and cost

| Need | Source | Free? |
|------|--------|-------|
| Venue-level trade/quote data, BTC/USD, BTC/USDT, USDT/USD, 2017 onward (Bitfinex, Binance.US, FTX, Kraken, Coinbase) | Exchange public REST/WebSocket APIs (limited history); Kaiko, CoinAPI, Tardis.dev | Partial. Public APIs give coarse OHLCV (free). Tick history is paid. FTX data is available only through vendors/archives. Bitfinex and Binance.US candle history is free but limited depth. |
| Mt. Gox 2013-14 trade data | Public Mt. Gox trade dump (research mirrors) | Free if the dump is available. I did not check availability. |
| Stablecoin on-chain transfers (USDT on Ethereum/Tron, USDC) | Dune, Google BigQuery public crypto datasets, Etherscan API | Free tiers exist, with rate limits. Full Tron history is heavy. |
| Exchange wallet labels | Etherscan labels (limited free), Arkham (some free, ToS limits), Nansen and Chainalysis (paid) | Partly free. Labels are incomplete and are a measurement risk. Cold-wallet coverage is the main gap. |
| Withdrawal fees and queue/suspension notices | Exchange announcements, Wayback Machine, status pages | Free but manual. |
| Off-platform USDT/USD and USDC/USD | Kraken, Coinbase, Gemini public candles; Coin Metrics community data | Free (coarse) to paid (tick). |
| Event dating | News archives (CoinDesk, The Block, Forklog), court filings | Free. |

Bottom line on cost: a coarse daily or hourly version is feasible for free (exchange candles plus Dune/BigQuery plus manual notices). A publishable high-frequency version needs a paid tick vendor and a decision on wallet labels.
