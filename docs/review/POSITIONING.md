# Positioning (T4), draft 2026-10-12, after the rescue search

## Candidate story: "Which dollar broke? Token failures versus platform-ledger failures in Web money"

**Problem (Web Economics).** Most retail crypto activity happens inside Web platforms whose "USD" is a ledger entry, convertible to bank money only through the platform's banking rails. When a dollar-quoted price dislocates, either the **token** broke (a stablecoin depeg) or the **platform's dollar** broke (a rail cut). The two have different victims and remedies, yet a single price series cannot tell them apart.

**Method.** A two-factor decomposition using public Web data only (exchange archives and APIs). It uses three comparisons:
- an external reference venue whose rails stayed open (cross-venue);
- a numeraire asset with no peg (BTC);
- the within-venue triangle.

The two failure types leave different signatures:
- **Token failure:** the stablecoin's D ≠ 0, while the platform-dollar dislocation of unrelated assets, PD_BTC, is ≈ 0.
- **Ledger failure:** PD_BTC ≈ PD_token ≠ 0 for every asset, with the within-venue triangle intact.

**Evidence.**
- *Token side:* the existing pre-registered multi-event study (4 accepted episodes: Terra, SVB, TUSD, FDUSD; plus negative and placebo cases).
- *Ledger side:*
  - Binance.US 2023 (R2): a discount while exit was threatened, then a **reversal to a 5–6% premium** once deposits closed but withdrawals stayed open;
  - replications on Binance GBP and EUR (R6, predictions pre-recorded).
- *On-chain capacity:* kept as a measurement appendix (how much par-restoring flow DEX pools could absorb), not a headline.

**Closest work and our difference:**
- Mt. Gox 2013–14 "escape buying" premium: news and folk evidence of the discount side only, with no identification.
- The Kimchi premium (Choi, Lehar & Stauffer): capital controls across countries, not within a platform.
- Makarov & Schoar: cross-exchange deviations in general.
- Stablecoin-run papers (Lyons & Viswanath-Natraj; Ma, Zeng & Zhang; Liu, Makarov & Schoar): the token side.
- CurveMetrics: on-chain depeg detection.

**Claims we will not make.** No causal effect sizes beyond the documented event dates, no prediction, and no generalisation beyond the measured platforms.

**Gate status (updated after R6).** R2 passes K1–K4 and the within-case reversal on restoration. R6 shows the same platform-ledger signature (USDT and BTC agree), but no comparable effect from the rail cut (GBP: +7.5 bps on a 30 bps base; EUR: the gap shrank). The claim is therefore narrowed to one documented natural experiment, plus the decomposition method, with GBP and EUR reported as small-effect cases. Story choice: PIVOT to this framing, subject to the user's approval.
