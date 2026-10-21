# Simulated WWW review of draft v5: synthesis (2026-10-20)

**Scores:** R1 2, R2 2, R3 3 (all confidence 4). For draft v3 they were 2, 2, 2.

## Fixed since v3 (no longer raised as major)

- The control is no longer mechanical. The multi-asset Coinbase–Bitstamp control scored +0.042 [0.009, 0.081], with a mean correction of 2.7 bps.
- Held-out results now carry confidence intervals and the baselines on the test assets.
- The fee band and lead-lag analysis answered "is the calm-year offset just microstructure?"
- The operating curve and exposure denominators are explicit.
- The 6.5-month claim is now framed neutrally as elapsed time (R2 still finds the wording awkward).

## Remaining issues, ranked

| # | Issue | Raised by | Fixable with the data we hold? | Action |
|---|---|---|---|---|
| 1 | **The USDT anchor is not exogenous on Bitfinex.** USDT shares Tether/Bitfinex parent and redemption risk. Unexplained points: slope 0.71, the 2018 slope of 2.06, the 2023 sign flip. | R1, R2, R3 | Partly | **Errors-in-variables ruled out:** the ETH-instrumented slope is 0.72 for the stress window (OLS 0.71) and 0.77 for 2019 (OLS 0.77). Add this. **Decisive next test:** an *external* USDT/USD price (Kraken, 2018–19). If the 29% residual equals USDT's own discount off Bitfinex, the anchor works once USDT's own price is accounted for. This needs a Kraken download (free OHLCVT bundle), which needs approval. |
| 2 | **The method is "a relabelled median" or a two-way fixed-effects model.** Its improvement over the median is 0; there is no truth-discovery baseline on real data. | R1, R2, R3 | Yes | Run CRH, TruthFinder-style weighting and the median on the real panel. Score them on held-out assets and on stress-window index error against an open-rail reference. Present the contribution as identification plus validation, and say plainly that the estimator is a median. |
| 3 | **Withheld assets, not withheld hours.** Weekly bootstrap blocks are too short for offsets that persist for months. | R1, R3 | Yes | Add a time-blocked split (for example 2017–2019 vs 2020–2023), and use monthly or quarterly blocks. Report the per-asset and per-year medians up front, not the pooled 85%. |
| 4 | **Monitor evidence is thin.** About two real episodes, the authors' own labels, no intervals on recall, z-score better at full recall, Coinbase 0/5. | R1, R2, R3 | Partly | Add exact binomial intervals. Define the matching window. Report a "label-free" check: alarms against the anchor-confirmed unit shifts. Move the monitor to a secondary contribution. |
| 5 | **"Bitfinex carried its own dollar throughout" is too strong for 2020–23.** Anchor slopes there are 0.16–0.61 on few hours. | R2 | Yes (wording) | Say the cross-asset common component persisted every year, and that the anchor confirms it only in the stress windows. |
| 6 | **Venue fit and generality.** Platform credits and loyalty points are claimed without data; the study is four crypto exchanges. | R1 | No new data | Keep one sentence on generality as motivation only, or drop it. Strengthen the web-data-fusion framing through issue 2. |
| 7 | **Specification search is not quantified.** | R3 | Yes | Add a short "what was fixed when" table: pre-registered, locked test, post hoc. |
| 8 | **Minor.** The James–Stein formula is unjustified; Chainlink's expected slope is not stated; the detector table runs into the margin. | R3 | Yes | Fix in text. |

## Assessment

These remaining issues are about identification and how much the method adds, not missing analyses. Issues 2, 3, 5, 7 and 8 can be done with the data we already hold. Issue 1 is the one experiment that could move scores, and it needs the external USDT price.
