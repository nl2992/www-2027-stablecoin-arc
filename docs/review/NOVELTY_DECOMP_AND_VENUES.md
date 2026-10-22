# Novelty of the Bitfinex-premium decomposition, and venues/deadlines

Prepared 2026-10-22. Every source below was opened or returned by search in this session. Items I could not open are flagged "UNVERIFIED".

Claim under test: the Oct 2018 - May 2019 Bitfinex BTC/USD premium (about 250 bps) splits into (i) a discount on Bitfinex ledger USD and (ii) USDT's own discount. Bitfinex USDT/USD net of Kraken's USDT price, regressed on the Bitfinex-vs-Bitstamp BTC gap, has slope 0.97 [0.94, 1.00], against 0.71 before netting. Binance.US 2023 was a pure ledger-dollar shift (anchor slope 1.00).

---

## Task A. Novelty

### Verdict: PARTLY NOVEL (the idea is anticipated verbally; the identification and numbers are not)

- The interpretation "Bitfinex premium = discount on exchange-credited USD" is already in print, in words only, and untested.
- No work found separates the premium into a ledger-USD part and a Tether part. None uses Bitfinex's own USDT/USD price, or an external USDT price (Kraken), for that purpose.
- No academic paper found on Binance.US 2023 USD. Only press coverage.

### Closest works (ranked)

1. **Flowerday, Gandal, Halaburda, Olson, Ardel (2026), "Bitcoin arbitrage: The role of an exchange"**, Quantitative Finance and Economics 10(3): 624-648, DOI 10.3934/QFE.2026024 (published 1 Sep 2026). Working-paper versions: SSRN 5162047 and CEPR DP20567 ("Bitcoin Arbitrage: The Role of a Single Exchange"). I read the full PDF (aimspress.com/aimspress-data/qfe/2026/3/PDF/QFE-10-03-024.pdf).
   - Data: BTC/USD trades only, on Bitfinex, Bitstamp, Coinbase and Kraken, Jan 2017 - Jun 2021. Hourly mispricing index, duration analysis, event studies.
   - It states our hypothesis in words: "what looked like expensive Bitcoin partly reflected a discount on Bitfinex USD balances ... a BTC/USD quote on Bitfinex embedded an implicit discount on the fiat side of the pair". It calls the two views "not mutually exclusive".
   - It says the channel "cannot be tested directly" with its data.
   - USDT appears only as narrative: Oct 2018 depeg to $0.88, and USDT as an alternative dollar path. It uses no USDT price and no regression.
   - Its future-work paragraph names "broaden the analysis to BTC/USDT pairs and later crisis episodes". That is exactly the gap our paper fills.
   - Action: cite as the nearest work. Frame ours as the first test of their "segmented-claims" reading, with the Tether leg separated out.

2. **Lyons and Viswanath-Natraj, "What Keeps Stablecoins Stable?"** NBER WP 27136 (May 2020); J. Intl Money and Finance 2023. I read the NBER PDF.
   - It uses USDT secondary-market prices (Bitfinex, Bittrex, Kraken via Coinapi) and has a case study of the Oct 2018 attack on Tether.
   - That case study finds a falling USD price of Tether, higher volume volatility and wider bid-ask spreads. It attributes the episode to "a move by its partner exchange Bitfinex to suspend convertibility of dollar deposits".
   - Footnote: Bitfinex states USD withdrawals take 7 to 15 days, with a 3% fee on more than two withdrawals a month.
   - It does not touch the Bitfinex BTC premium. It treats Tether, not the BTC/USD gap.

3. **Unverified, practitioner:** a Medium post, "Bitcoin: Welcome to Bitfinex's Second Tether Bubble" (coinmonks).
   - A search snippet says it argues that in Apr-May 2019 Bitfinex BTC/USD and BTC/USDT were not arbitrage-free through the Bitfinex USDT/USD cross rate.
   - If so, it is the closest use of Bitfinex's own USDT/USD price.
   - I could not open it (HTTP 403; archive fetch blocked). Author and date UNVERIFIED. Do not cite without reading it.

Runner-up practitioner items (news or blog, none is a decomposition):
- The Block, "Premiums on Bitfinex continue widening", 12 Oct 2018. It reports the Bitfinex premium of 1.5-1.7%, Tether-based venues at about 1.2% over fiat-pair venues, and Kraken USD/USDT at 1.9%. Descriptive only.
- Bloomberg, 17 Oct 2018, "Bitcoin trades at $300 premium on controversial crypto exchange". Seen via search only.
- Alex Kruger, "Tether Arbitrage & The Dollar Peg" (Medium). Search summary only; I could not open it (403). It argues that USDT redeemed only through Bitfinex fiat withdrawals until Nov 2018, and that a USDT price drop widens the BTC premium. UNVERIFIED in detail. A conceptual explanation, not a measurement.
- A Medium piece by "Austerity_Sucks" on why Bitfinex went from premium to discount. Blog, not opened.

### Checked, and not a decomposition

| Work | What it does | Why not a match |
|---|---|---|
| Griffin and Shams (2020), "Is Bitcoin Really Untethered?", J. Finance 75(4):1913-1964 | Tether issuance and flows vs. BTC price, 2017 | About manipulation, not the premium. Their data predate Nov 2018. I confirmed only the abstract (RePEc), not the full text. |
| Wei (2018), "The impact of Tether grants on Bitcoin", Economics Letters 171:19-22 | VAR of Tether grants vs. BTC returns | Not about the premium. Confirmed via RePEc and press only. |
| Grobys and Huynh (2022), "When Tether says JUMP! Bitcoin asks How low?", Finance Research Letters 47(A) | Tether price jumps on Bitfinex predict BTC drops, Nov 2018 - Jun 2021 | Starts after the premium episode begins to fade. Abstract only. |
| Kristoufek (2021), "Tethered, or Untethered?", Finance Research Letters 43, DOI 10.1016/j.frl.2021.101991 | Spillovers stablecoins to cryptoassets | No premium. Kristoufek (2022), Financial Innovation 8: 37 (stablecoin pricing dynamics) found only in a reference list, not read. |
| Saggu (2022), Finance Research Letters 49 | Intraday BTC response to Tether minting | Not about the premium. |
| Makarov and Schoar (2020), J. Financial Economics 135(2):293-319 | Cross-country arbitrage gaps | Capital controls; no Bitfinex-specific USD/Tether split. Search excerpts only. |
| Crépellière, Pelster, Zeisberger (2023), J. Financial Markets 64 | Arbitrage in crypto markets | Search snippet only. |
| Niu, arXiv 2410.22443 | LocalBitcoins premiums for 80 currencies | Abstract does not mention Bitfinex, Tether or Binance.US. |

### Specific searches that came back empty
- Kaiko, Coin Metrics, The Block, BitMEX Research: no piece that nets USDT's own price out of the Bitfinex BTC gap. BitMEX Research's "A Series on Tether" (Feb 2018) predates the episode. The Block and Bloomberg report levels only. Coin Metrics: nothing found on the premium; this absence is from search only.
- "Bitfinex premium" on SSRN/arXiv: only Flowerday et al. (SSRN 5162047).
- Kristoufek: no Tether paper on the premium.
- Binance.US 2023: no academic paper found. Press only:
  - CoinDesk, 9 May 2023: premium near $650.
  - CoinDesk, 9 Jun 2023: narrow discount.
  - CryptoSlate, Jun 2023: Kaiko data; USD pairs only, USDT/USDC pairs near normal.
  - Cointelegraph, Jul 2023: about -8.5% vs. global spot, USDT quoted at $0.915 on the venue, new USD deposits halted from 9 Jun.
  - Blockworks (undated in my notes): dollar shortage.

### Positioning advice
- Do not claim "first to say the premium is a USD discount". Flowerday et al. say it. Claim: first to test the claim and to split it into a ledger-USD leg and a Tether leg using Bitfinex USDT/USD net of an external (Kraken) USDT price; and the Binance.US 2023 anchor as an out-of-episode check.
- Reconcile with Lyons and Viswanath-Natraj: their Oct 2018 case study is the Tether leg alone.
- Caveat for the 0.97 vs. 0.71 comparison: the Kraken USDT price is itself the "external" Tether discount. Show robustness to Kraken vs. a multi-venue USDT price.
- Residual risk: the "Second Tether Bubble" post may already compare Bitfinex BTC/USD with BTC/USDT via the cross rate. Read it before submission.

---

## Task B. Venues and deadlines (today = 2026-10-22)

### WWW 2027 (The Web Conference 2027), Dublin, 10-14 May 2027
Source: www2027.thewebconf.org (important-dates, research-track-papers, resource-submissions). All deadlines are 23:59 AoE (UTC-12) unless noted. The research page says deadlines are strict and placeholder abstracts are forbidden. A second domain, acmweb2027.org, also appeared in search; I did not use it. Third-party aggregators (beri.net, mldeadlines) disagree with the official dates; use the official site. The site notes the research call was updated on 25 Sep 2026.

| Track | Abstract | Full paper | Limit and format | Status today |
|---|---|---|---|---|
| Research, Web Economics and Digital Society (one of 12 tracks) | 18 Oct 2026 (PASSED, 4 days ago) | 25 Oct 2026 (3 days left) | 8 pages of content plus references and appendix, max 12 total; first 8 self-contained. ACM sigconf, `acmart[sigconf, anonymous, review]`. Double-blind. OpenReview. Must state relevance to the Web on page 1. | Abstract deadline has passed. The page does not say plainly whether an abstract is mandatory for a full submission. It does say the author list is locked after the abstract deadline. Check OpenReview now for whether a paper with no abstract can still be submitted. |
| Research, Evaluation, Human Computation, and Resources (resource papers inside research tracks) | same | same | same as above | Same as above |
| Short papers | 9 Nov 2026 | 16 Nov 2026 | 4 pages including references and appendix; ACM sigconf; double-blind (research-call rules) | Open. About 18 days to abstract. |
| Resource Submissions (separate "Resource track") | none listed | 17 Dec 2026 | 4 pages including references. ACM sigconf, `review`. NOT anonymous (single-blind). Needs a stable access link, an open licence statement, documentation, an ethics section. OpenReview. Reviews due 13 Jan 2027; notification 20 Jan 2027; camera-ready 17 Feb 2027. Accepted papers go to the Companion Proceedings. | Open. Fit for a dataset/resource paper. |
| Industry | same as research | 25 Oct 2026 | counts as long or short | not relevant |
| Demos | n/a | 16 Nov 2026 | n/a | not relevant |

Other research-track facts:
- Results 15 Dec 2026, rebuttal 15-20 Dec, notification 4 Jan 2027, final version 31 Jan 2027.
- Track topics for Web Economics and Digital Society include "Blockchain and decentralized finance", "Advertising auctions, pricing, and exchanges" and "Mechanism and market design for platforms".
- Reviewer duty: every author must review, and failing to review can cause desk rejection.
- Preprints on arXiv are allowed if anonymised.
- 2027 only: subsidised ACM Open APC of $500 (members) or $750 (non-members), if the institution is not in ACM Open.

Fit and recommendation:
- Full paper (Web Economics): feasible only if the abstract can still be registered. If not, use the Short paper (abstracts 9 Nov, paper 16 Nov) or Resource (17 Dec).
- Web-relevance risk: desk rejection for papers that only use a Web artifact without a Web research question. Frame as Web economics of platform/ledger-dollar claims.

### Other venues

| Venue | Track / format | Deadline | Limit and format | Fit |
|---|---|---|---|---|
| **FC 2027** (Financial Cryptography and Data Security), Barbados, 8-12 Feb 2027 | Regular / Short / SoK | PASSED: 17 Sep 2026, firm extension 24 Sep 2026, 23:59 AoE (ifca.ai/fc27 and fc27.ifca.ai) | Regular 15 pp + refs and appendices; Short 8 pp + refs, no appendices (title starts "Short Paper:"); SoK 20 pp. LNCS PDF; anonymised. Topics list includes stablecoins and tokenized assets and economic aspects of cryptocurrencies. | Good topical fit; missed. Next edition (FC 2028) CFP not seen. |
| **ACM AFT 2027** (Advances in Financial Technologies) | n/a | NO 2027 CFP found. AFT 2026 (London, 6-9 Oct 2026) had abstract 20 May and paper 27 May 2026 AoE; AFT 2025 paper deadline was 28 May 2025. Expect about late May 2027 if the pattern holds (inference only). aft.ifca.ai lists editions only to 2026. | AFT 2026: up to 20 pages of text in LIPIcs, PDF, anonymised, open-access proceedings; SoK allowed; accepted authors may ask for a 3-page extended abstract in the proceedings. | Strong fit (measurement of exchanges, stablecoins). Plan for about May 2027. |
| **Finance Research Letters** (Elsevier) | Letter | Rolling; no deadline | Main text max 2,500 words (in-text citations and footnotes counted; abstract, references, tables, figures, appendices excluded); abstract max 250 words. Gold OA APC USD 3,540 excl. tax; subscription route has no author fee; no submission fee seen. | Fits the short, single-finding result. Source: ScienceDirect guide for authors (my direct fetch was 403; figures come from the search-tool summary of the Elsevier pages and from Wikipedia for the 2,500 words). Recheck live before submitting. "Rolling" is my inference from the absence of any call or deadline. |
| **ICWSM 2027** (AAAI), Edinburgh | Full papers; datasets; posters/demos | Round 3: 15 Jan 2027, 23:59 AoE (notification 15 Mar 2027). Earlier rounds 15 May and 15 Sep 2026 passed. | Full: 11 pages at initial submission (8 recommended), including references; AAAI two-column. Dataset papers: 2-10 pages, Round 3 only, need a DOI for the dataset. | Weak: scope is web/social-media data and societal relevance. Dataset-paper route possible, but exchange order books are not social media. |
| **ACM IMC 2027** | Two cycles in the 2026 pattern | NO 2027 CFP found. IMC 2026 (Karlsruhe, 12-16 Oct 2026) had cycle 1 paper deadline 20 Nov 2025 (registration 13 Nov) and cycle 2 on 29 Apr 2026 (registration 22 Apr). If 2027 repeats, cycle 1 would fall about mid-Nov 2026 (inference). | Not checked. | Moderate: measurement fit, but the Internet-infrastructure focus is a stretch. Check conferences.sigcomm.org/imc/2027/. |
| **KDD 2027** Applied Data Science track, San Jose, 1-5 Aug 2027 | ADS (one of four tracks) | First cycle deadline listed by aggregators as about 26 Jul 2026 (passed; notification 14 Nov 2026). Second-cycle date not found. | ADS page on kdd2027.kdd.org not retrievable. UNVERIFIED. | Weak: wants applied-ML systems. |
| **Journal of Financial Econometrics** (OUP/SoFiE) | No short-format article type found | Rolling | Papers typically no more than 40 double-spaced pages; abstract at most 100 words; USD 65 submission fee for non-SoFiE members; replication files required for empirical papers (from 13 Mar 2023). | Poor for a short result; full-length only. |

### Timing summary for the decision
1. Today: check on OpenReview whether the WWW 2027 abstract can still be registered. The full-paper deadline is 25 Oct 2026, AoE.
2. If it cannot: WWW short paper (9/16 Nov), or Resource (17 Dec; non-anonymous, needs an open dataset).
3. Journal route with no deadline: Finance Research Letters (2,500 words).
4. Conference route to plan for: AFT 2027 (about May 2027, unconfirmed) and FC 2028.
