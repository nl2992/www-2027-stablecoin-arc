# Supervisor-Skills review, round 4: the multi-platform panel and the abstract (2026-10-19)

**Procedure:** HKUSTDial/Supervisor-Skills at commit `a20d76e` (CC BY-NC-SA 4.0). The skills were applied in place; no skill text is copied here.
- `idea-evaluator`: the finance and economics framework, chosen because the core method is event-based measurement. Fatal flaws were audited first, and the novelty flaw (F1) was grounded in retrieval.
- `pre-submission-reviewer`: the five-sentence abstract formula and the forbidden-pattern scan.
- `paper-polish`: calibration and faithfulness.
- `blader/humanizer`: a final pass over the prose.

## 1. Idea evaluation

**First impression.** This is a novel problem framed as a measurement problem. One-sentence story: *Web price feeds treat every exchange's "USD" as one dollar; when an exchange's banking rails fail its dollar drifts, and we separate that failure from a token failure using public data.*

### Fatal-flaws audit (no CRITICAL)

| Flaw | Severity | Status |
|---|---|---|
| F1 novelty versus closest work | MAJOR, defensible | Retrieval below. The differing axis is the decomposition into token and unit of account, plus the feed consequence. |
| F2 venue fit (WWW) | MAJOR, mitigated | The Web angle is now a failure mode of price aggregation, with a measured error and a filter. Residual risk: it reads as finance. |
| F10 failure cases | handled | The sterling and euro cuts show small effects. The deposits-versus-withdrawals story is contradicted by Bitfinex 2018 and stays undescribed as a mechanism. The 2017 filter is weaker. |

### Retrieval-grounded novelty (web search, 2026-10-19; metadata-level only)

| Closest work | What it does | Differing axis |
|---|---|---|
| Borri & Shakhnov, *J. Int. Money Finance* 139 (2023), "Cryptomarket Discounts" | Persistent BTC price gaps across exchange-currency pairs; segmentation and capital controls | Measures one asset's gap. We attribute the gap to the venue's unit of account, using agreement across unrelated assets and coherent cross-rates, and tie it to dated rail events. |
| Guo, Intini & Jahanshahloo, *Finance Research Letters* 71 (2025), "Bitcoin Arbitrage and Exchange Default Risk" | Arbitrage persistence across 16 exchanges, 2013 to 2024, conditioned on exchange default risk | Default risk is a covariate in their arbitrage analysis. We measure the ledger dislocation itself, separate it from token failure, and quantify the feed error. |
| Liu & Szalachowski, arXiv:2005.04377 (2020), "A First Look into DeFi Oracles" | Oracle prices deviate from market rates; operational anomalies | Their causes are operational. Ours is unit-of-account heterogeneity across the sources. |
| Makarov & Schoar (2020); Choi, Lehar & Stauffer (2019) | Cross-exchange and cross-country gaps | No token/ledger split. |
| Mt. Gox premium (arXiv:2109.10958; trade press, 2013–14) | Premium after fiat withdrawal delays | A single episode with no attribution test; this is our precedent. |

No directly overlapping work was retrieved under these keywords. "Not found" is not proof of novelty, so the abstract keeps the wording "we know of no measure". The paper must cite Borri & Shakhnov, Guo et al. and Liu & Szalachowski; the bib entries are added.

### Five dimensions (finance/economics framework; each starts at 5)

| Dimension | Score | Grounds |
|---|---|---|
| Identification quality | 7 | Dated rail events on two platforms; agreement across unrelated assets (hourly corr ≥ 0.975, gap ≤ 7.2 bps); cross-rates within 8 bps. Not causal; selection is disclosed. |
| Economic magnitude | 8 | Dislocations of 6–8%. A naive index is off by ≥ 100 bps for 2,826 hours. |
| Mechanism novelty | 6 | A new class of phenomenon (unit-of-account failure on a Web platform). Why the discount turns into a premium is unexplained. |
| Data contribution | 5 | Public data with a reproducible pipeline; no new dataset. |
| Policy relevance | 7 | A filter feeds can run (it removes 88% of the bad hours), and a signal that preceded disclosure of the loss by about 6.5 months in 2018. |

**Emphasise:** magnitude, the feed filter and the Web framing. **Verdict: Accept with Revisions.** The revisions are the novelty positioning against the three papers above, and a body rewritten around the panel.

## 2. Abstract review (five-sentence formula)

| Role | Before (draft 8c870e0) | Finding | Fix |
|---|---|---|---|
| 1 Problem | Feeds average incompatible dollars | OK | — |
| 2 Why existing work fails | "work on cross-exchange gaps does not ask whose unit of account moved" | **MAJOR, inaccurate.** Guo et al. (2025) attribute gaps to exchange default risk. | "links them to segmentation or exchange default risk"; the gap claim stays "we know of no measure that separates token failures from ledger failures" |
| 3 Challenges | ledger never quoted; asynchronous trades; asset shocks | OK, concrete | — |
| 4 Method | "We price ..." | MINOR: the method is unnamed | "Our decomposition prices ..." |
| 5 Results | "three platforms ... moved on Bitfinex and Binance.US" | **MAJOR, hidden failure case.** The reader cannot tell the third platform showed little. | "moved on two: Bitfinex and Binance.US" |

**Forbidden-pattern scan:** no em or en dashes, none of the banned vocabulary, no curly quotes.

**Calibration:** "we know of no measure" is kept, being an unverified first-claim. "removes 88%" is scoped to "these venues". The lead-time sentence is scoped to "on Bitfinex in 2018".

## 3. Remaining before the paper deadline

1. Rewrite the body around the panel:
   - introduction and contributions;
   - a results section with a panel table and figure;
   - a feed-error section;
   - a timeline table.
2. Related work: cite and differentiate the three papers above.
3. Complete Bitfinex January–February 2019; candidate further episodes are Mt. Gox 2014 and QuadrigaCX.
4. Present the Bitfinex results descriptively (single reference, full daily path), and do not describe those checks as pre-registered.

Sources: [Borri & Shakhnov 2023](https://ideas.repec.org/a/eee/jimfin/v139y2023ics026156062300164x.html) · [Guo, Intini & Jahanshahloo 2025](https://ideas.repec.org/a/eee/finlet/v71y2025ics154461232401393x.html) · [Liu & Szalachowski 2020](https://arxiv.org/html/2005.04377v3) · [Mt. Gox arbitrageurs](https://arxiv.org/pdf/2109.10958)
