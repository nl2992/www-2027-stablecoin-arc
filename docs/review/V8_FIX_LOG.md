# V8 fix log

Maps the items of `SIM_REVIEW_V7_R3.md` (inconsistency list 1-27), then the remaining R1/R2 items that were fixable in text, to the fix made in `paper/main.tex` (or the generated tables' modules) or to "not fixed: reason". Gate: 12 pages, body ends on page 8, abstract 295 words.

## R3 inconsistency list

| # | Item | Fix |
|---|------|-----|
| 1 | Interval for 0.97 | Headline interval is the month-block bootstrap everywhere (abstract, Sec 5.2). HAC, hourly block-bootstrap, week-block and month-block intervals for the same estimate are listed once, labelled, in Sec 3.1 "Evidence". The sentence saying HAC is narrower than the bootstrap now says the hourly intervals are narrower than the daily month-block interval. |
| 2 | Hour counts | Named by sample in Sec 5.2: Kraken traded in 4,461 of 4,464 hours; anchor regressions 4,434 (L, D, X all exist); GMM 4,433 (needs all four instrument gaps); Table 11 counts large-gap hours; 823 hours on 35 days for 2018. Binance.US windows are named in Sec 5.2 and Sec 5.7. |
| 3 | "Fixed in advance" vs post hoc | 360-spec grid described as specified before it was run but after the headline was seen; added to the post hoc row of Table 1. |
| 4 | Pre-registered monitor vs fitting | Table 1: monitor pre-registered only for venue-months it had not been fitted or checked on; Binance.US and Bitfinex marked development. Text and Table 7 caption say so. |
| 5 | Demand check vs Table 11 | Defined "agreeing" and "did not follow" (thresholds), and explained that Table 11's share is a different, stricter statistic. |
| 6 | Persistence vs smoothing | Sec 3: the hourly estimate is noisy although the offset persists; we did not diagnose why smoothing failed. |
| 7 | Table 7 counts | Caption and Sec 5.6 explain that several episodes can hit one label and that coverage years differ by method. No intervals added (see below). |
| 8 | Monitor vs baselines | Sec 5.6 keeps the matched-recall comparison and says the z-score is better at high recall; intro contribution 4 reworded; monitor stated to be a thresholded form of the agreement idea, not the shrunk estimator. |
| 9 | "Three shocks" vs Fig 2 | Section retitled "Two shocks and a null in 2023"; intro reworded; Figure 2 caption fixed to the plotted series (USDT, bitcoin, USDC); double periods removed. |
| 10 | Binance.US magnitudes | 557 bps / 530 hours (22 June to 31 July, deposits shut) vs -413 bps / 721 hours (all large-gap hours of June and July) named in Sec 5.2 and 5.7; -3.5 vs -4 explained as table rounding. The 1.01 [0.97, 1.01] edge case in the generated Table 11 is not changed (not fixed: pure rounding of a generated table). |
| 11 | Abstract vs Table 4 on Binance.US | Abstract no longer says "passed"; says the slope is near one, close to mechanical once deposits closed, and the two-anchor test rejected. Sec 5.2 and 3.1: single-anchor test consistent with a unit shift, two-anchor rejected (Bitstamp USDC leg depegged); netting changed nothing because Kraken's USDT was at par. |
| 12 | "Indistinguishable from the median" | Reworded to "ties on the pooled score"; small per-asset/control differences with intervals excluding zero acknowledged. |
| 13 | Test years | "five calendar years 2019 to 2023"; abstract adds the median over test assets next to the pooled score. |
| 14 | Block-bootstrap choice | Text says week blocks are the default in the tables but too optimistic; month and quarter intervals are the ones to read. |
| 15 | Calm-year slope range | All four years quoted (2020 to 2023) with the note that intervals exclude one. |
| 16 | Simulation vs data | Bias -0.254 described as of the order of the 0.731 to 0.971 gap; raw daily OLS 0.71 vs hourly GMM 0.731 distinguished. |
| 17 | Flowerday wording | Abstract and related work: "cannot be tested directly" with their data. |
| 18 | Shrinkage constant | Typeset c=1/2; "re-picking gave 0.25 with nearly the same scores". |
| 19 | Discussion vs Table 6 | Recommendation now says dropping did as well in T1 and to correct instead of dropping only if volume matters. |
| 20 | Unit-aware equals open-rail alone | Sec 5.4 and Discussion: result is close to the open venue; not claimed as independent evidence of identification from two sources. |
| 21 | Terminology | "common share" explained as a correlation, not the Table 2 explained share; "venue-year" used throughout. |
| 22 | Missing evidence | All "in the artifact" and "committed tables" phrases removed or replaced by "not reproduced here"; label list "summarised, not reproduced". |
| 23 | Undefined items | Sec 5.4 "Methods" paragraph defines the round-2 unit-aware fuser, the round-3 fuser and the oracle; table rows renamed; "method's own check" renamed; Data section describes the fusion-test data in one sentence; Kimchi study added to Table 1 as pre-registered. |
| 24 | J degrees of freedom | Sec 3.1 and the Table 8 caption give K, m and df per row (Km-1). |
| 25 | Reference issues | ACM reference line fixed (`\acmConference`); GTM now "described in the survey". Not fixed: adding the original GTM paper (cannot verify a new bib entry offline). |
| 26 | Layout | Page 9 no longer mostly blank; appendix tables flow; total 12 pages. Appendices B and C are still short. |
| 27 | Claims stronger than evidence | "2018 to 2019 premium" limited to the anchored window; "direct test" removed; "never seen" replaced; "every bootstrap interval excluded zero" replaced by the share of cells whose interval contains one; "Aggregators should correct" replaced by a hypothesis from one winning episode. |

## R1/R2 items fixed in text

- lambda interpretation (R2 W3): covariance share of the offset's time variation; intercepts free, so a level premium is not identified; delta = kappa u gives 1/(1+kappa); assumptions on epsilon and nu added to A1/A4; abstract and conclusion reworded.
- Binance.US power/mechanical concern (R2 W2, W8, W9): stated as near-mechanical; no bootstrap interval macro exists, so the text says only HAC is available and probably too narrow; J reporting rule: all J reported, not fixed in advance.
- Placebo (R3 W6): stated as uninformative (interval contains 0 and 1).
- Kimchi (R2 W10): FX netting (DEXKOUS), USDT/KRW carries the wedge, no earlier anchor, FX noise biases toward one.
- Fusion definitions, oracle values above 1 (R1 W2, R3 W4): defined and explained (fewer sources).
- Q1 follow-up integrated (Sec 5.4, Table 1, abstract) with the four required caveats.
- Process leakage (R1 W10): macro module list removed; "Method of this round" etc. renamed.

## Not fixed

- Intervals on Table 6 and Table 7: no per-episode inference is available; the text says why (one episode per cell).
- Single regime, title and venue fit (R3 W1, W7; R1 W1, W11): structural; claims were narrowed instead.
- Per-asset test of A1, identified demand shock, second anchor or external USDT venue, non-funding-asset placebo, Binance.US power calculation, bias-aware or fixed-effect baselines, non-crypto web data (R1/R2/R3): need new analysis.
- Binance.US bootstrap interval: no macro exists.
- Original GTM citation; Appendix B/C expansion: see above.
- Chainlink and Table 11 hour-count rows: unchanged beyond naming the windows.
