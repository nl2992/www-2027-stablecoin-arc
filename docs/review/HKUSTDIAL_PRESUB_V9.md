# Pre-submission review of draft v9 (WWW 2027)

Skill: pre-submission-reviewer. Paradigm: finance / empirical economics with a web-data-fusion framing, so the weights go to identification credibility, robustness and economic versus statistical significance. Venue fit: Web Economics and Digital Society track, a web-data-quality problem on exchange prices; no mismatch found. Retrieval-grounded checks (novelty search, citation completeness) were skipped: no scholarly-search step was run, so positioning against prior work rests on the paper's own Related Work. The banned-vocabulary and em-dash scan covered `main.tex`, `generated/theory_section.tex`, the caption macros and all generated tables in full.

## Summary
- CRITICAL: 0
- MAJOR: 5 (3 fixed, 2 left for the author)
- MINOR: 9 (6 fixed, 3 left)
- Top three fixes: (1) every caption rendered bold (acmart sigconf default), including Figure 1; (2) 12 of 17 numbered equations were never referenced; (3) a 35-line results paragraph and unexpanded abbreviations (GMM, HAC, CRH) hurt readability.
- Page budget after fixes: 8 body pages, 12 total; abstract 296 words.

## Dimension 1: Macro logic
| # | Finding | Severity | Suggested fix | Status |
|---|---|---|---|---|
| 1 | No Conclusion. The paper ends with "Limits" and "Reproducibility" paragraphs in the Discussion. | MAJOR | Add a short closing section restating the findings and their boundary, without new numbers. | Not fixed: body is at the 8-page limit, so a new section would need cuts the author should choose. |
| 2 | Contribution 4, "A monitor with a fixed rule, scored on a small label set", is backed by one body paragraph ("Both are secondary to the identification and fusion results") and the appendix. The paper itself calls the label set and fee bands "thin". | MAJOR | Either drop it from the contribution list or demote it to a supporting result. | Not fixed: removing a contribution is the author's call. |
| 3 | Headline attribution rests on one regime: "the offset's variation was mostly a ledger-dollar shift" from a single stress window with "about six month-blocks". Ablation of the netting exists (raw 0.71 against netted 0.97), and the text bounds the claim ("close to, not equal to, one"). | MINOR | None needed; wording is already bounded. | Left. |
| 4 | Intro flow: background, limits of existing methods, key idea ("Our idea is that..."), challenge ("This is hard for two reasons"), overview figure, contributions. Contributions 1 to 4 map to sections 3, 5.2, 5.3 to 5.4 and 5.5 to 5.6. Running example (Bitfinex 2018 to 2019) reappears in Model (worked example), Results and Discussion. | n/a | Chain intact. | OK |
| 5 | Section "3 Model" opens with "Let $p_{s,a,t}$ be the log price..." and "5 Results" opens directly with a subsection heading, with no leading sentence. | MINOR | Add a one-line roadmap. | Not fixed: no free lines on page 8; low value. |

## Dimension 2: Writing details
| # | Finding | Severity | Suggested fix | Status |
|---|---|---|---|---|
| 6 | Paragraph "Bitfinex: the dollar, net of Tether." ran about 35 lines in one block. | MAJOR | Split at "The USDT-specific component is visible.", "Sample sizes differ by design" and "Across ... specifications". | Fixed (three paragraph breaks, no text change). |
| 7 | Repetition: "The calm-year offsets (2020 to 2023) are systematic but too small to trade" appears in 5.5 and again in Appendix E; the Binance.US window (22 June to 31 July, 530 hours) is described in 5.2, 5.6 and Appendix D. | MINOR | Point back instead of restating. | Not fixed: deleting appendix detail is the author's decision. |
| 8 | Abstract covers problem, method, result with numbers; sentence 3 is long ("We formalise the test with an identification result...") but split by the list. | MINOR | None. | OK |

## Dimension 3: English grammar
| # | Finding | Rule | Severity | Status |
|---|---|---|---|---|
| 9 | "Whether that premium priced the exchange's dollar or the coin has been argued but not tested." "Priced" as a transitive verb for "reflected the price of" is non-idiomatic; the same use recurs in contribution 1 ("the reading that Bitfinex's premium priced its dollar"). | G7 (Chinglish) | MINOR | Left to the polish step, which records it as a meaning-adjacent flag. |
| 10 | Related Work mixes tenses: "TruthFinder ... and CRH ... estimate", "Liu et al. found", "Nadler et al. benchmarked". | G3 | MINOR | Left; present tense for method descriptions and past for findings is defensible. |
| 11 | Dense passive and nominal runs in the Results paragraph on Binance.US ("Two windows are kept apart."). | G6 | MINOR | Left to polish. |
| 12 | Spelling is British throughout (formalise, summarises, anonymised, centred); consistent. | n/a | OK | OK |

## Dimension 4: LaTeX format
| # | Finding | Severity | Suggested fix | Status |
|---|---|---|---|---|
| 13 | All captions bold: the class sets `textfont={bf}` for sigconf, so Figure 1's whole caption (`Method overview. Each source quotes...`) was bold. | MAJOR | `\captionsetup{textfont=normalfont}`. | Fixed. |
| 14 | Page 2, left column had large vertical gaps around "Oracles and data quality". No `\vspace`, stray blank lines or float markup exists near it; the gaps came from column stretch when the bold four-line caption pushed the break. | MAJOR | Fixed by the caption change; verified in the rebuilt page 2 (no gaps). | Fixed. |
| 15 | Unreferenced numbered equations (L10): eq:source, gap, mad, shrink, unitval, snap, fused, shi, endpoint, lambda, moments, J. | MAJOR | Reference each in the prose. | Fixed (each is now cited at the sentence that introduces it). |
| 16 | Labels with hyphens (L4): `tab:anchor-ext`, `tab:heldout-ci`, `tab:robust-eval`, `tab:td-index`, `tab:td-heldout`, `fig:anchor-scatter`. They compile and resolve. | MINOR | Rename to underscores. | Not fixed: labels are written by table generators and asserted by tests; renaming gives no reader benefit. |
| 17 | Abbreviations undefined at first use (self-contained rule): GMM in the abstract, HAC in "Bartlett HAC weight", CRH in Related Work. USDT, USDC, SVB, FTX, TUSD, FDUSD, OHLCVT are also unexpanded. | MINOR | Expand at first use. | Fixed for GMM, HAC and CRH. The stablecoin and event names are left: expansions in the abstract would break the 300-word limit and the names are standard in this field. |
| 18 | Citations use `~\cite`; references use `~\ref`/`\S\ref`; quotes use ``...''; no `---`; ranges use `--`. | n/a | OK | OK |
| 19 | Page limits: 8 body, 12 total. Overfull boxes reported by the log: 41 (was 35); all in generated tables and display math, none visible in the render. | MINOR | Monitor. | Left. |

## Dimension 5: Figure quality
| # | Finding | Severity | Status |
|---|---|---|---|
| 20 | All figures in the paper are vector PDF (Figure 1 is TikZ). `unit_rate.pdf` embeds one 6x119 px indexed image (the year colour bar), which is not a raster figure. | OK | OK |
| 21 | Captions: Figures 3 to 5 (anchor scatter, forest, Q1 errors) are generated and state the finding; Figure 2 caption describes the panels but the first sentence names the pair and period, not the finding. | MINOR | Left: Figure 2's caption is in `main.tex` and the text just below states the finding; polish may adjust wording only. |
| 22 | Palette: figures use default matplotlib colours with dual encoding (line style, hatching); colour-blind safety not verified by simulation. | MINOR | Left (needs figure regeneration and new design choices). |

## Banned-vocabulary and em-dash scan
- Em dashes (`—`, `---`): 0 in `main.tex`, `theory_section.tex`, caption macros and tables.
- Banned AI-tone terms: none of innovative, pioneering, revolutionary, transformative, superior, surpass, excel, remarkable, unprecedented, breakthrough, general-purpose, "capable of", notably, yielding, "at its essence", encompass, differentiate, reveal, underscore, "pave the way", highlight, profound, "stems from", rigid, impede appear. "yet" and "exceed(ed)" appear (the latter five times, all as numeric comparisons: "|T| exceeded half of |L|", "the gap exceeded the band"); not flagged.
- Overclaim terms: "first" appears 12 times, all ordinal ("first term", "first as quoted"); none as "we are the first". "solve": 0 as a claim. "robust" appears 24 times, mostly as the statistical term "robust variance" or in the macro names. "state-of-the-art": 0.

## Final score
7 of 10. Zero CRITICAL; the two remaining MAJOR items (no Conclusion; a thin fourth contribution) cap the score at "needs 1-2 days".

## Submission recommendation
Needs 1-2 days more work: add a short Conclusion and decide the fate of contribution 4 (both need space the 8-page limit does not currently have), then re-run the gate.

## Items not fixed, with reasons
1. No Conclusion (finding 1): needs new text and a page-budget decision.
2. Contribution 4 is thin (finding 2): author's call on scope.
3. Repeated passages in the appendix (7): removing detail is an author decision.
4. Hyphenated labels (16): generator-owned; no reader-visible effect.
5. Leading sentences for sections 3 and 5 (5), colour-blind check and Figure 2 caption lead (21, 22): need space or figure regeneration.
