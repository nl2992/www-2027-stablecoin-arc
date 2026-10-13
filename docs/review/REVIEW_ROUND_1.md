# Simulated review, round 1 (2026-10-12)

**Draft reviewed:** "Which Dollar Broke?" (PR #8), with references starting on page 5 and 9 pages in total. Three adversarial reviewers, each with a separate brief.

**Severity:**
- **B**: blocking, rejection-level.
- **M**: major.
- **m**: minor.

Each finding lists its remediation and status after this round.

## Reviewer 1: Web economics and finance (novelty and claims)

**Summary.** An interesting natural experiment and a clean idea (attribute a dollar dislocation to the token or to the platform's unit). The ledger evidence is one case. The token half is a separate, weaker study stapled on. Score: weak reject → borderline if the ledger result is shown not to be a thin-market artifact.

| ID | Sev. | Finding | Remediation | Status |
|---|---|---|---|---|
| R1.1 | **B** | **Thin-market alternative.** After 06-22 most USD pairs were delisted. A −600 bps "premium" could be a handful of trades in an emptying book, not a price of the platform dollar. The paper shows no volume or trade counts. | Report per-phase liquidity: traded-minute share, median hourly trades and quote volume for USDT/USD. Show the dislocation is carried by active trading. | **Fixed:** liquidity columns added (`liquidity` in `platform_dollar.json`; Table 1) |
| R1.2 | M | **The identification statistic is weak.** Hourly correlation in levels over a phase with a trend (the mid-July dip) is inflated. Two series that both trend down correlate highly whatever their relation. | Report the median absolute USDT–BTC gap relative to the dislocation's size, and the correlation of hourly *changes*. | **Fixed:** gap ratio and first-difference correlation reported |
| R1.3 | M | **N = 1 for the headline.** GBP and EUR do not replicate the magnitude, so the generalisable claim is the *method*, not the effect. | Re-scope the contributions: the method plus one documented case; GBP and EUR as small-effect cases. | **Fixed:** wording in the abstract and contributions |
| R1.4 | M | The "one-way gate" account has an alternative: delisting mechanics, where users forced to convert USD sell into a thin USDT book. | Discuss explicitly; R1.1's liquidity evidence partly addresses it. | **Fixed:** paragraph revised |
| R1.5 | m | The Mt. Gox comparison rests on trade press. | Acceptable as motivation; keep the wording hedged. | Kept |

## Reviewer 2: measurement and data quality

**Summary.** A careful pipeline with good provenance. It has a single reference venue, phase boundaries chosen after inspecting daily medians, and last-trade candles. Score: borderline.

| ID | Sev. | Finding | Remediation | Status |
|---|---|---|---|---|
| R2.1 | **B** | **A single external reference.** If Bitstamp's BTC/USD were off, L would be wrong. | Second BTC reference without a new provider: Binance.com BTC/USDT × Bitstamp USDT/USD. Report L under both references. | **Fixed:** `pd_btc_alt_reference` added |
| R2.2 | M | Phase boundaries were fixed after the daily medians had been seen (disclosed). | Sensitivity: shift every boundary by ±1 day and report the range of each phase median. | **Fixed:** `boundary_sensitivity` added |
| R2.3 | M | **A method without an evaluation.** Does the decomposition raise false "ledger failure" flags in calm months? | Run the classifier hourly over every month where Binance.US and Bitstamp BTC/USD and USDT/USD overlap; report flag rates by period. | **Fixed:** monitor section and table added |
| R2.4 | m | The impaired phase (USDT −9 bps for 18 months) needs interpretation: the platform USD could neither enter nor leave. | One sentence: what PD means when the unit is non-redeemable in both directions. | **Fixed** |
| R2.5 | m | "corr 1.00" hides precision; the hyphen-minus in tables is not a typographic minus. | Three decimals for correlations ≥ 0.995; keep plain minus (generated). | Partly fixed: the phase table now reports correlation of changes |

## Reviewer 3: WWW scope, presentation and compliance

**Summary.** Web relevance is asserted on page 1 but not demonstrated; the paper uses only about 4.5 of 8 pages, so space is available. Score: weak reject on fit unless the Web-system angle becomes concrete.

| ID | Sev. | Finding | Remediation | Status |
|---|---|---|---|---|
| R3.1 | M | **Web consequences are only asserted.** Quantify what a price feed built on venue USD quotes would have shown. | Report the price-feed error, which equals PD_BTC, and run the decomposition as a **monitor** a feed or oracle could deploy, with flag rates (R2.3). | **Fixed:** monitor section |
| R3.2 | M | The two halves are loosely coupled. | Frame the token study as the method's evaluation on token failures (SVB decomposition), with the registry in the appendix. | **Fixed:** section intro revised |
| R3.3 | m | The ACM reference block reads "Conference'17". | Set `\acmConference` to WWW '27. | **Fixed** |
| R3.4 | m | Figure 1(b) omits USDC. | Add USDC to panel (b). | **Fixed** |
| R3.5 | m | The abstract carries too many numbers. | Trim. | **Fixed** |

## Verdict before fixes

**Borderline / weak reject**: blocking items R1.1 (thin market) and R2.1 (single reference). See `REVIEW_ROUND_2.md` for the re-score after the fixes.
