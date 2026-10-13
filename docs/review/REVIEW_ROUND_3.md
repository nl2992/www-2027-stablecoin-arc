# Simulated review, round 3: pre-submission review (2026-10-13)

**Procedure:** the `pre-submission-reviewer` skill from HKUSTDial/Supervisor-Skills (commit `5f9432d`; CC BY-NC-SA 4.0), applied to branch `g4/threshold-abstract`. The skill's checklists were used in place; no skill text is copied into this repository, and its bundled scripts (draw.io only) were not run.

**Draft:** references start on page 6; 10 pages in total; gate passes.

**Paradigm and venue (Step 0):** empirical measurement with finance and economics weighting (identification, robustness, economic magnitude). Venue: WWW 2027, Web Economics and Digital Society track. Fit is plausible because of the price-feed and oracle monitor and the Web-platform-money framing. Residual risk: a finance-only reading.

**Retrieval-grounded checks:** novelty and citation completeness were run with web search on 2026-10-12. The closest works are cited: Cintra & Holloway 2023; Choi, Lehar & Stauffer 2019; Makarov & Schoar 2020; Heimbach et al. 2024; Liu, Makarov & Schoar 2023; Mt. Gox trade press. No uncovered closest work was found. The search supports metadata-level judgments only.

## Summary

| Severity | Before fixes | After fixes |
|---|---|---|
| CRITICAL | 0 | 0 |
| MAJOR | 5 | 0 |
| MINOR | 6 | 4 |

The top three fixes, all applied:
1. Abstract: the challenges sentence was added (five-sentence formula).
2. Introduction restructured into the six-paragraph flowchart.
3. Em-dashes removed.

## Dimension 1: Macro logic

| # | Finding (quoted) | Severity | Fix | Status |
|---|---|---|---|---|
| 1 | Introduction lacked explicit "limitations of existing work" and "challenges" paragraphs; contributions followed the "Why this is a Web problem" paragraph directly | MAJOR | Six-paragraph flowchart: problem plus example; limitations (pegs and runs assume the venue dollar is a dollar; cross-venue gaps do not attribute; Mt. Gox untested); key idea; three challenges; solution mapped to the challenges; four contributions | Fixed |
| 2 | "The method generalises; the magnitude is one platform's" claims more than one venue supports | MAJOR | "The method needs only an unpegged asset and an open-rail reference" | Fixed |
| 3 | §7 "What On-Chain Pools Saw" was not mapped to any contribution | MAJOR | Folded into contribution (3) | Fixed |
| 4 | "no existing measure separates the two" is a first-claim | MINOR | "we know of no measure that separates the two" | Fixed |
| 5 | Attribution ablation: the decomposition depends on BTC as the unit probe | — | Already isolated: USDC as a third asset and a second BTC reference | No change needed |

## Dimension 2: Writing details

| # | Finding | Severity | Fix | Status |
|---|---|---|---|---|
| 1 | Paragraphs over 10 typeset lines: "Not a thin-market or reference artifact" and the monitor results paragraph (about 30 typeset lines each) | MAJOR | Split into "Boundaries and identification", "A unit with no anchor", "Calm-period flags", "Threshold sensitivity" and "Three assets, one unit" | Fixed |
| 2 | Abstract lacked a challenges sentence | MAJOR | Added: "The difficulty is that a ledger's value is never quoted directly, public prices are asynchronous last trades that thin out under stress, and any single asset may carry its own shock." | Fixed |
| 3 | The Decomposition Framework paragraph is long, but the length is mostly its itemize | MINOR | Leave | Open |

## Dimension 3: English grammar

| # | Finding | Severity | Rule | Status |
|---|---|---|---|---|
| 1 | "dearer in it" (British register) next to US spellings elsewhere | MINOR | consistency | Open (author's choice of US or UK spelling) |
| 2 | No article or agreement errors found in the sampled sections | — | — | — |

## Dimension 4: LaTeX format

| # | Finding | Severity | Fix | Status |
|---|---|---|---|---|
| 1 | Negative numbers are typeset with a hyphen (for example "-104.3 bps") rather than a minus sign | MINOR | Emit `$-$` from the macro generators | Open |
| 2 | Floats cluster on pages 4–6 | MINOR | Layout pass at freeze | Open |
| 3 | `\acmConference` venue field empty | MINOR | Fill once the venue is verified | Open |
| 4 | Page limits: body ≤ 8 and total ≤ 12 | — | Gate passes (references start on page 6; 10 pages in total) | OK |

## Dimension 5: Figure quality

| # | Finding | Severity | Fix | Status |
|---|---|---|---|---|
| 1 | Figure 3 draws L and T_USDC as solid lines distinguished only by colour (no dual encoding) | MINOR | Dash one series | Fixed |
| 2 | Figures are vector PDFs, captions lead with the finding, and the palette is colour-blind-safe (tab10 blue and orange) | — | — | OK |

## Banned-vocabulary and em-dash scan

**Attestation:** the whole of `paper/main.tex` after `\begin{document}` was scanned against the skill's list.

- **Before fixes:** 9 em-dashes, 1 "yet" and 1 "reveal" in the body; 1 "yet" in the abstract.
- **After fixes:** 0 of each. A test now fails if `---` appears in the body.

## Final score

**8 / 10.** Zero CRITICAL, zero MAJOR remaining, four MINOR. The score is capped by the substantive limits recorded in round 2: one strong ledger case, and a post-search ledger analysis.

## Submission recommendation

**Needs 1–2 days more work.** Clear the MINOR items (minus signs, layout, venue field), freeze on 10-23, and the human author registers the abstract by 10-18.
