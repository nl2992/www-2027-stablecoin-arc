# Simulated WWW review of draft v3: synthesis (2026-10-20)

**Reviewers:** R1 web data / truth discovery (`SIM_REVIEW_V3_R1.md`), R2 crypto finance (`_R2`), R3 methods (`_R3`). All three scored 2/5 (weak reject) with confidence 4.

## Ranked issues

| # | Issue | Raised by | Severity | Fix | Data in hand? |
|---|---|---|---|---|---|
| 1 | **Identification.** A common BTC/ETH gap could be exchange-wide crypto demand (margin, USDT-funded buying), not a dollar shift. | R1, R2, R3 | Critical | Add a **stablecoin anchor test**. USDT is a dollar claim with no crypto exposure, so a dollar shift moves Bitfinex USDT/USD by the same amount as BTC, while crypto demand does not. **Checked:** Mar–Apr 2019 BTC gap +173 bps, Bitfinex USDT/USD +150 bps, residual −1 bps; daily correlation 0.92 in 2019. Make this a main result, and add the reverse placebo: high-demand hours on open-rail exchanges. | Yes (Bitfinex USTUSD from 2018-11) |
| 2 | **Held-out headline.** The 85% is driven by XRP and 2019. The estimator ties the median (0.846 vs 0.847). The control is mechanical because Bitstamp has only BTC and ETH. There are no confidence intervals and no per-asset baselines on the test set. | R1, R2, R3 | Major | Lead with the per-asset and per-year numbers, with block-bootstrap intervals. Present the decomposition, not the estimator, as the contribution, and the estimator as "a median suffices". Compute the b1/b2 baselines on the test assets (scoring baselines, not tuning). Replace the control with a pair that has several assets, which needs Bitstamp altcoin hourly data. | Partly (Bitstamp altcoins need approval) |
| 3 | **Monitor evidence.** Nine positives and one operating point; baselines not matched (no two-asset gap rule, no threshold sweep); Coinbase recall 0/5; per-year denominators unclear; "6.5 months before regulators" when the premium was public. | R1, R2, R3 | Major | Show a precision/recall sweep across thresholds against matched baselines. State the exposure denominators. Replace the 6.5-month framing with "the price measured the impairment for six months before it was disclosed", and credit the public premium. | Yes |
| 4 | **Venue fit and abstraction.** It reads as a crypto finance note, and the truth-discovery novelty is small (a two-way additive model, like median polish). | R1 (and the user) | Major | Reframe as **web data fusion with source-specific units**: a general problem, identification from cross-item agreement, and held-out validation. Make the abstract general, with 4–5 numbers. Name other domains with source-specific units (platform credits, multi-currency marketplaces). | n/a (writing) |
| 5 | **Economic meaning of calm-year gaps.** Calm-year gaps of 0.7–7 bps sit inside tick size, fees and latency. Hourly median and last close are mixed; trading is non-synchronous. | R2, R3 | Major | Add fee and tick bounds per exchange and year. Report the calm-year unit share relative to noise. Use one timing convention throughout. | Yes |
| 6 | **Appendix A contradicts the Discussion.** Unit-aware fusion doesn't beat the median, yet the Discussion says "correct, don't drop". | R1 | Minor | Say that correcting preserves the exchange's volume and labels the unit, rather than claiming better accuracy. | Yes |
| 7 | **Wrong oracle expectation.** The paper expects a contamination slope "near 1", but the positive control reaches only 0.14. | R1 | Minor | Say the expected slope is the USDC-quoted share of the feed's sources, and report it as a bound. | Yes |
| 8 | **Model specification.** The shrinkage formula, time conventions and the sign of the Binance.US move are unclear. | R2, R3 | Minor | Give the formulas and conventions, and one sentence on the sign. | Yes |
| 9 | **Presentation.** Figure 3 and Table 5 are redundant; page 8 is unused. | R3 | Minor | Drop the redundant figure and table, and use the space for issues 1 and 3. | n/a |

## Suggested order

1, then 4 (together they change the story: "the gap is the dollar, and here is the anchor test"), then 2, 3 and 5, then the minor items.
