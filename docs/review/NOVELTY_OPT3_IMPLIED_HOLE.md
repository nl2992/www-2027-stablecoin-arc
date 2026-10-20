# Novelty check, option 3: "Quantifying the hole from the price"

Date of check: 2026-10-20. Method: web search plus local text extraction of two PDFs. Verification status is marked per item:
VERIFIED = I opened the source and read the relevant text. SNIPPET = seen only in a search-result summary. UNVERIFIED = could not open it.

## (a) Closest prior works and overlap

| # | Work | Status | What it does | Overlap with the idea |
|---|------|--------|--------------|-----------------------|
| 1 | Flowerday, Gandal, Halaburda, Olson, Ardel, "Bitcoin arbitrage: The role of an exchange", Quantitative Finance and Economics 10(3): 624-648, DOI 10.3934/QFE.2026024, published 1 Sep 2026 | VERIFIED (full text read) | Tick data, Bitfinex/Bitstamp/Coinbase/Kraken, Jan 2017 to Jun 2021. About 80% of dispersion hours include Bitfinex. The Bitfinex premium is read as "fiat redemption risk": on-exchange USD is not the same claim as off-exchange USD. Event studies around banking stress and the NYAG action. | PARTIAL. It gives the same economic interpretation (the discount prices the quality of the ledger dollar) and uses the same episode. A text search of the paper finds no haircut, expected-loss or implied-loss calculation, no liability denominator and no comparison to the $850M. It mentions the $850M only as background. |
| 2 | BitMEX Research, "Pricing Bitfinex Default Risk" (bitmex.com/blog/pricing-bitfinex-default-risk) | SNIPPET only. The URL appeared in search results with a summary; a direct fetch returned 404, so I could not read it. Authors and date are unconfirmed. | Argues the Bitfinex premium proxies for short-horizon (about 5 to 7 day) default risk, using withdrawal delay and time value of money. Also notes Mt.Gox traded at a 10 to 20% premium before its collapse. | PARTIAL, possibly substantial. This is the same mapping from discount to default risk, in blog form and informal (per the summary, no formal pricing model). Whether it computes a dollar loss against $850M is unknown. Must be read via an archive copy before we claim novelty. |
| 3 | Guo, Intini, Jahanshahloo, "Bitcoin arbitrage and exchange default risk", Finance Research Letters 71 (2025) 106364, DOI 10.1016/j.frl.2024.106364 | Existence VERIFIED (ideas.repec and Cardiff ORCA listing). Abstract only; full text not read. | Minute data, 16 exchanges, Apr 2013 to Apr 2024. Arbitrage gaps persist longer when higher-risk exchanges quote higher prices; capital flows from high-risk to low-risk exchanges. | PARTIAL. It links price gaps to exchange default risk, but as a cross-sectional persistence and flow result, per the abstract. It does not appear to convert gaps into implied haircuts or dollar losses. Check the full text. |
| 4 | Gandal, Hamrick, Moore, Oberman, "Price manipulation in the Bitcoin ecosystem", J. Monetary Economics 2018, DOI 10.1016/j.jmoneco.2017.12.004 | VERIFIED via search summary and the QFE paper's citation | Suspicious Mt.Gox trading (about 600k BTC, about $188M) and its effect on the 2013 price spike. | NONE for this idea. It is about manipulation, not implied loss or the Gox/Bitstamp discount. |
| 5 | Flow-of-funds and contagion FTX papers: Conlon, Corbet, Hou (Int. Rev. Financial Analysis 2024); Galati et al. 2024 (cited in the QFE paper); arXiv 2302.11371; arXiv 2407.12683 | SNIPPET (titles, findings) | Contagion, price-discovery lead of FTT, leverage fragility, network effects. | NONE to PARTIAL. None uses an FTX-specific price discount to infer an expected haircut. FTT is an equity-like token, not a ledger-dollar claim. |
| 6 | Trade-press claims-market reports: The Block on Xclaim prices (FTX up to 15.5 cents, Celsius up to 18.5, Voyager 41, Jan 2023); Bloomberg via BNN (FTX 57 to 73 cents, Dec 2023); 2017 Mt.Gox claim bids at 15% of yen value (Cointelegraph) | SNIPPET | Price levels of bankruptcy claims. | PARTIAL for the "price of expected loss" concept, but these are claim prices after failure, not pre-failure ledger discounts. No academic paper on crypto claim-price-implied recovery was found in two searches (not exhaustive). |
| 7 | Contemporary commentary: Bitcoin Magazine (Oct 2018) on Tether and USDT-pair distortion; Alex Kruger on Bitfinex arbitrage mechanics; CoinDesk on the Gox 20% premium before the Jan 2014 freeze | SNIPPET | Qualitative description of premiums as reflecting trapped funds. | PARTIAL (qualitative). |

Searches did not find: an academic paper that converts the Bitfinex or Mt.Gox discount into an implied expected haircut and dollar loss using a liability denominator and compares it with the realized hole. This is a negative from a limited search (about 14 queries), not a proof. Not searched: SSRN full-text search by author, Kaiko, Coin Metrics and The Block research archives beyond the snippets above, and papers on deposit-insurance market discipline in the crypto setting.

## (b) Verdict: PARTLY NOVEL

- ALREADY DONE (do not claim): that the Bitfinex premium or discount reflects fiat redemption or default risk (Flowerday et al. 2026; BitMEX blog; Guo et al. 2025), and that Mt.Gox's pre-collapse premium reflected trapped fiat (CoinDesk, BitMEX).
- NOVEL, subject to reading BitMEX and Guo et al. in full: the quantitative step. That means converting the discount path into an implied expected haircut and dollar loss, using an explicit liability denominator and withdrawal-delay horizon, and comparing it with the realized hole across Gox, Bitfinex and (if data exist) FTX.
- Weakest part: FTX. FTX had no usable pre-failure ledger-dollar discount, so only claim prices (post-failure) exist there.
- Framing risk: the comparison to "$850M" is conceptually mismatched. Customers were ultimately made whole via the Tether line of credit and LEO, so the realized customer loss was about zero, while the $850M was the firm's hole. See (c).

## (c) Feasibility: the liability denominator and the back-of-envelope

### Public figures found (Bitfinex, 2018 to 2019)

All from the NYAG settlement agreement of 17 Feb 2021 (VERIFIED, text extracted and read; URL: ag.ny.gov/sites/default/files/2021.02.17_-_settlement_agreement_-_execution_version.b-t_signed-c2_oag_signed.pdf):
- Para 32: "By mid-2018, Crypto Capital held over $1 billion of funds that emanated from customer deposits at Bitfinex."
- Para 33: Poland froze a Crypto Capital account holding at least $340 million (reported April 2018).
- Para 34: about $150 million of client funds frozen in Portugal.
- Para 35: in July 2018 Bitfinex told "Oz" that over eighty percent of Bitfinex's client deposits were held at Crypto Capital-controlled bank accounts.
- Para 36: nearly $500 million of customer deposits "frozen" at that time.
- Para 38: Bitfinex borrowed $400 million from Tether in summer 2018.
- Para 46 (Bitfinex message to Oz, quoted): "We have 860m with you ... 350 in Poland, 150 in Portugal."
- Para 47: Bitfinex said it "processed over 700 withdrawals representing more than $1 [billion]" in October 2018 alone.
- Paras 43, 49: Tether transferred $475M (Nov 2018, five transfers), at least $625M in total, to Bitfinex; the line of credit closed end of March 2019 allowing draws up to $900M.
- Para 50: the NYAG application of 24 Apr 2019 disclosed about $850M lost access. Para 53: Bitfinex cannot say whether or when unrecovered funds return. Penalty $18.5M.
- Not found in it: a total of Bitfinex customer USD liabilities. No document I could open states one.

Derived (my arithmetic, not a public figure): if more than 80% of client deposits sat at Crypto Capital and Crypto Capital held over $1B (or about $860M at Nov 2018), then total client fiat deposits were roughly $1.1B to $1.3B or more in mid-2018 (860/0.8 = 1.08B; 1000/0.8 = 1.25B). This is a lower-bound-style inference from two loosely worded paragraphs, with an uncertainty of perhaps plus or minus 30%. Post-redemption in late 2018 (USDT became redeemable at Tether, USD withdrawals continued) the balance probably moved, so the denominator at the premium's peak is unknown.

Other sources (SNIPPET only, not opened): Hoegner affidavit of 30 Apr 2019 (Tether cash and equivalents about $2.1B, about 74% of tokens outstanding; Tether reserves, not Bitfinex customer liabilities); iFinex discovery application of Oct 2019 putting the Crypto Capital amount at about $880M (The Block, Decrypt, Cointelegraph).

LEO whitepaper (May 2019): reported via Bitcoin Magazine, Crowdfund Insider and Decrypt (SNIPPET) as raising about $1B and meant to cover the $850M loss; it commits at least 95% of recovered net Crypto Capital funds to LEO buyback and burn within 18 months of recovery. I did not open the whitepaper itself, so the exact wording is UNVERIFIED.

Friedman LLP: the NYAG settlement describes a 15 Sep 2017 verification of Tether's accounts (about $442M) and Friedman's departure on 27 Jan 2018 (search summary of the settlement, SNIPPET; I did not locate the paragraph). It is not a source for Bitfinex customer liabilities. No attestation of Bitfinex USD customer liabilities was found. None found.

Realized hole and recovery: no source found for the amount ultimately recovered from Crypto Capital. The settlement states (para 53) that as of Feb 2021 Bitfinex could not say whether or when unrecovered funds would return. A 2022 report of recoveries was not found in two searches.

### Back-of-envelope

Implied expected loss = d x B. Setting d x B = $850M gives B = 850 / d:

| d | B needed |
|---|----------|
| 2.5% | $34.0B |
| 3.0% | $28.3B |
| 4.0% | $21.3B |
| 5.0% | $17.0B |
| 5.5% | $15.5B |

So a 3 to 5% discount is consistent with an $850M expected loss only if USD balances were about $17B to $28B (about $15.5B to $34B across 2.5 to 5.5%).

Plausibility: not plausible. The derived Bitfinex client fiat deposits were about $1.1 to 1.3B, 13 to 25 times too small. The reverse calculation: d x B at B = $1.1 to 1.3B and d = 3 to 5% is $33M to $65M, i.e. 4 to 8% of the realized $850M. Equivalently, the realized hole was about 65 to 77% of USD client deposits (850/1.1 to 850/1.25 = 77% to 68%), while the market discounted only 3 to 5%. Interpretation options, none of which the data alone separates:
1. The discount is a marginal price for a delay-and-risk exit option, not a stock-weighted expected loss. Traders could escape by buying BTC and moving it off-exchange, so the discount is capped by the cost of that route and does not scale with B. This is the main reason the simple d x B identity fails.
2. The market priced a low probability of a large loss (roughly 5 to 7% probability of a 70% haircut would reproduce 3 to 5%) because it expected Tether or the owners to backstop customers; the later facts (Tether line of credit, LEO) bear that out. The realized customer loss was about zero, so "realized hole" for customers is not $850M.
3. The discount also contains a pure delay or carry component (BitMEX's 5 to 7 day horizon logic), which has to be netted out before reading an expected loss. At 3 to 5% over a 5 to 7 day horizon, the annualized hazard is extreme, which signals mostly a liquidity or carry premium, not an expected solvency loss.
4. The d range of about 250 to 560 bps is from the user's prompt; I did not independently reconstruct the Bitfinex spread series. Contemporary press cites BTC premiums of about $300 to $400 (about 6.7% peak) around the April 2019 filing (SNIPPET: Informer Post, Bitcoinist).

Mt.Gox: pre-freeze premium about 20% over Bitstamp (CoinDesk, SNIPPET), and a fiat-withdrawal halt dating from mid-2013. Gox owed customers mostly bitcoin; the claims register is about 18.6B USD-equivalent in BTC/BCH but only about 48.1M in USD (Blockchain Research Lab note, SNIPPET, unopened). With USD balances of about $48M (if that number is the right denominator) and a 20% discount, d x B is under $10M, tiny relative to the loss of roughly 650k to 850k BTC. For Gox the sign and the asset are also different: the stuck asset was USD, the premium appeared in BTC priced at Gox, and the later loss was in BTC. The denominator is directly checkable from the trustee's filings in this case, which makes Gox the cleanest test of the method.

FTX: no cross-venue ledger-dollar discount (FTX withdrawals were halted without a price history on a freezing venue worth using). Only post-petition claim prices exist (FTX claims at 15.5 cents in Jan 2023 per Xclaim via The Block; 57 to 73 cents in Dec 2023 per Bloomberg via BNN). A claim-price-implied haircut vs realized recovery (reported at 118 to 143%+ in dollar terms) is available but is a different object from the venue discount.

Conclusion: the identity d x B = hole does not reconcile for Bitfinex and should not be the headline. A defensible version is a bound: expected loss implied by the discount over the exit horizon is at most d x B, roughly $33M to $65M for Bitfinex, versus a firm-level hole of $850M, and the gap quantifies how much the market assumed a backstop. That is a result about the implied rescue probability, not a verification of the hole.

## (d) Data needed and whether free

| Item | Needed for | Free? |
|------|-----------|-------|
| Bitfinex BTC/USD vs Bitstamp/Kraken/Coinbase hourly or minute prices, Oct 2018 to May 2019 | Discount path d(t) | Largely free: exchange public APIs (Bitstamp, Kraken OHLC limited history; Coinbase candles). Bitfinex candles via public API. Full tick history is paid (Kaiko, CryptoCompare, Coin Metrics); the QFE authors used tick data. |
| Bitfinex USD (and fiat) customer liabilities, monthly | Denominator B | Not available. Only the NYAG paragraphs above allow a rough bound ($1.1 to 1.3B in mid-2018). A better source would be the NYAG exhibits to the 24 Apr 2019 Martin Act application and the Hoegner affidavit (court docket, public but not fully retrieved here; Amy Castor and Bitcoin Magazine summarize). Not free to obtain with precision. |
| Withdrawal delay (days) | Horizon T | Partly: BitMEX's 5 to 7 days is an assumption; Bitfinex status posts and the NYAG filings document the "temporary liquidity crisis"; no systematic series. |
| Realized recovery on Crypto Capital | Realized hole | Not found. Check Bitfinex/iFinex statements, the LEO burn announcements and court dockets (SDNY/CA subpoena cases) next. |
| Mt.Gox/Bitstamp prices Dec 2013 to Feb 2014 | Gox discount path | Free: Bitcoincharts-style historical data and Kaggle/GitHub mirrors, plus Gandal et al.'s data availability (check the paper's replication package). |
| Mt.Gox claims register and USD balances | Gox denominator | Free: Mt.Gox trustee (Kobayashi) filings and Blockchain Research Lab note. |
| FTX claim prices, FTX petition schedules | FTX | Partial: press/Xclaim snippets are free; Xclaim API and Stretto/Kroll schedules are free in part; academic-grade claim price histories are not. |

## Next steps before committing to the idea

1. Obtain and read the BitMEX post (archive copy) and the Guo et al. full text; if either already computes the implied dollar loss, downgrade to ALREADY DONE for Bitfinex.
2. Fetch the NYAG 24 Apr 2019 application exhibits and the Hoegner affidavit for any total client-fiat figure.
3. Reframe the headline from "the price reproduces the $850M" to "the price implies a bounded loss and a backstop probability", since the arithmetic above says the former fails by an order of magnitude.
