# Pre-submission review, final pass (WWW 2027, Web Economics and Digital Society)

Date: 2026-10-25. Skill: `pre-submission-reviewer` (HKUSTDial), all seven steps, with the humanizer pass of the same day. Material: `paper/main.tex`, `paper/generated/theory_section.tex`, the caption generators and the built `paper/build/main.pdf` (12 pages, 8 body), read in full; the text export is `docs/review/draft_final.txt`. This pass fixed text and layout only. No result, number or claim was changed.

Paradigm: empirical finance and economics (identification, robustness, economic against statistical size) plus a benchmark. Venue fit: the introduction opens on a Web practice (price pages and aggregators converting at official rates) and the keywords carry the economics terms, which is the right steer for the Web Economics track.

## Summary
- CRITICAL: 0
- MAJOR: 0 open after this pass (three were open before; each was a layout or label fault and is fixed, see the tables)
- MINOR: 4 open (listed under "Open items"; none is text-only fixable inside the page budget)
- The GenAI disclosure is an AUTHOR DECISION and is left untouched, as instructed. It is the only item that should block a submit button press.
- Page budget: 12 of 12 pages, body ends on page 8 (Conclusion). An earlier edit pushed the Conclusion onto page 9; three filler sentences were cut to restore it.

## Dimension 1: Macro logic
| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | Chain intact: background (price services assume one dollar), limitation (reliability weights and robust aggregation do not treat a shared source error), key idea (offset plus unit anchor, Figure 1), challenge, three contributions mapped to Sections 3, 5.2 to 5.5 and 5.6. Running example (Bitfinex 2018 to 2019) in Sections 1, 3, 5.2 and the Conclusion. | n/a | Intact |
| 2 | Abstract, introduction, body and Conclusion agree on the headline numbers. Checked by following each `\Num` macro to one source: 0.97 (0.94 to 1.00), 1.00, 0.978 (0.962 to 0.989), 1.005 (0.867 to 1.289), -1.08, 128.1, 6.8, 8.30, 107.4, 5.4. The abstract says P1 narrowly missed ("just short of its pre-registered target"). | n/a | Consistent |
| 3 | Abstract sentence "just short of its pre-registered target of an interval including one and partly reflecting triangular arbitrage within each venue" attached the arbitrage clause to the target, not to the slope. | MAJOR (reads as a claim error in the sentence reviewers read most) | Fixed: "...target of an interval that includes one; the slope partly reflects triangular arbitrage within each venue." |
| 4 | Abstract "a frozen unit-aware method beat it": "it" was the stablecoin, not the median. | MINOR | Fixed: "beat the median". |
| 5 | Section 5.2 "In the calm years it was lower (0.87 to 0.86 in 2020 to 2023)". Table 1 gives 0.87, 0.83, 0.84, 0.86, so the range read as a rise. | MINOR | Fixed: the four yearly values are listed. |
| 6 | Cross-references: Figure 6 (Q1 errors) was cited as "Appendix F" and sits in Appendix E; "monitor: Appendix F.1" pointed to the fee-band subsection. | MINOR | Fixed: Appendix E and Appendix F. |
| 7 | Figure 6 caption and legend use B0, B2, B3 with no definition in the paper. | MAJOR (undefined terms in a figure) | Fixed in the generator: "the median (B0), unit conversion (B2), CRH (B3)". |
| 8 | Pre-registration status, the one-episode caveat and the "panel partly reflects triangular arbitrage" caveat are all in the body and Table 8. | n/a | Consistent |

## Dimension 2: Writing details
| # | Finding | Severity | Status |
|---|---|---|---|
| 9 | Notation clash: `c` is the shrinkage constant in Eq. (5) and the source-wide offset `c_t` in Section 3.1 ("Var(c)", "Cov(u,c)"). | MAJOR (a reader of the identification proposition meets two meanings of `c`) | Fixed: the constant is now $\theta$ in Eq. (5), its text and Appendix D; `c_t` keeps its meaning. |
| 10 | "Its market traded in 99.93% of the hours" had no antecedent. | MINOR | Fixed: "Kraken's USDT/USD market traded in". |
| 11 | "supports the one-offset model" (contribution 1) overstated what a held-out score shows, and the body says the score shows only that offsets are shared. | MINOR | Fixed: "is consistent with". |
| 12 | "quotes items dearer in its unit". | MINOR | Fixed: "at higher prices". |
| 13 | Table 7 headers "Bitfinex 2017-04..07" and "2018-10..2019-05"; "Med", "P95" and ">50" were not defined in the caption. | MINOR | Fixed in the generator: "Apr--Jul 2017", "Oct 2018--May 2019", and the caption defines all three. |
| 14 | Hard-coded number: Appendix C "the 721 hours of June and July 2023". | MAJOR (rule: every number is a macro) | Fixed: new macro `\NumUAnchorBnusHours` in `unit_macros.py`, read from `reports/unit_td/anchor.json`. |
| 15 | Figure 3 caption opened on what a point is, not on the finding. | MINOR | Fixed: first sentence now gives the slope change from 0.71 to 0.97 on netting. Figure 6 caption likewise opens on the result. |
| 16 | Other literals left in the text are design constants, not results (threshold 25 bps, 0.5 share, 100 bps and 50 bps monitor thresholds, 1,000 draws, 1.4826, 24 and 72 hour windows). The test `test_every_number_macro_used_is_defined...` accepts these. | n/a | Left |

## Dimension 3: English grammar
| # | Finding | Rule | Severity | Status |
|---|---|---|---|---|
| 17 | Mixed spelling: "labelled", "anonymised", "Generalised", "realised", "favour" against American spelling elsewhere (ACM style). | Consistency of regional spelling | MINOR | Fixed everywhere, including generators. |
| 18 | "It is not independent evidence that units can be identified from two sources." (Appendix E) | Plain statement of scope | MINOR | Rewritten as "It adds no independent evidence...". |
| 19 | "...so about that share of the offset's variation was a unit shift and we say close to one." (Formal test) | Clause order | MINOR | Reordered. |
| 20 | Table 1 caption used "--" for an empty cell; the detector table caption likewise. | Typography | MINOR | "a dash marks fewer than five blocks"; "A dash means not evaluated." |

## Dimension 4: LaTeX format
| # | Finding | Severity | Status |
|---|---|---|---|
| 21 | `acmart` `sigconf,review,anonymous`; `Anonymous Author(s)`; no acknowledgements, no repository link, no identifying string in the PDF text. The anonymity grep returns only DOIs and URLs in the references. | n/a | Clean |
| 22 | Undefined references and citations: none. Overfull boxes: 50 (was 68), the remainder are wide equations, tables and URLs in the references; none is visible as a margin overflow in the 60 dpi renders. | MINOR | Left |
| 23 | Abstract 273 words (limit 300). Body 8 pages, total 12. | n/a | Within limits |
| 24 | CCS concept IDs were entered from memory (the comment in `main.tex` says so). | MINOR but author-only | Flagged in `SUBMISSION_CHECKLIST.md`; check at dl.acm.org/ccs. |

## Dimension 5: Figure quality
| # | Finding | Severity | Status |
|---|---|---|---|
| 25 | Figure 6 (Q1 errors) was set at 0.4 of the column and its tick labels, legend and panel labels could not be read. | MAJOR | Fixed: 0.85 of the column. |
| 26 | Figure 7 (two shocks) was set at 0.6 of the column and the legend overlapped the series. | MINOR | Fixed: 0.95 of the column. The legend text is still small at print size. |
| 27 | Figures 2 to 5 are vector PDFs with a colour-blind-safe palette and markers that differ by series; Figure 1 is TikZ. Captions are self-contained. | n/a | Pass |
| 28 | Figure 4 (panel forest and fusion errors) carries the two headline results and is on page 7, inside the body. | n/a | Pass |

## Banned-vocabulary and em-dash scan
Full scan of `main.tex` and `theory_section.tex` (no chunking needed): no em dash in either file; en dashes appear only in number and name ranges ("2017--2023", "Bitfinex--Bitstamp", "A1--A4", "James--Stein", "Newey--West"). None of the banned words occurs: no "innovative", "pioneering", "revolutionary", "transformative", "superior", "surpass", "excel", "remarkable", "unprecedented", "breakthrough", "general-purpose", "capable of", "notably", "yielding", "encompass", "differentiate", "reveal", "underscore", "pave the way", "highlight", "profound", "stems from", "rigid", "impede". "Robust" is used only as a technical term (robust aggregation, robust variance). "Yet" does not occur. "One for one" occurs twice in the body (Section 3, Section 3.1) and not in the abstract.

## Humanizer pass (summary)
- Contrast constructions: none of "not X but Y", "not only", "rather than", "instead of" in the paper. Four negative tails were restated directly: the "does not say ... does not split ... does not say" run in "Reading $\hat\lambda$" became one positive sentence about variation over the window; "does not claim that A uses less information than O" became "whether A uses less information than O is outside its scope"; "is not a stress-versus-calm comparison" became "makes no stress-versus-calm contrast"; "It is not independent evidence" became "It adds no independent evidence".
- Staging and filler: three sentences that only announced the section ("This section sets up the model...", "This section lists the public data we use.", "This subsection checks the estimator on withheld assets.") and one in the theory subsection were cut. The sentences in the other subsections that state what the subsection tests were kept.
- Abstract: the 40-word run-on about the panel was split into two sentences with the same numbers and caveats; "gave a pooled 0.978" now says "pooled slope of".
- No dash, bold label or forced triad was added; the italic "Intuition:" labels were kept because they are a deliberate device used the same way in Sections 3, 3.1 and Appendix A. Term definitions (offset, unit anchor, netting, dev assets, month-block bootstrap) were left as written.

## Open items (not fixed here)
1. GenAI disclosure wording: AUTHOR DECISION, comment left in `main.tex`.
2. CCS IDs unverified (author, dl.acm.org/ccs).
3. The mixed use of "venue", "exchange" and "source" is kept: "source" is the model's term, "exchange" is used for the crypto instance and "venue" for markets that are not exchanges in the strict sense (Binance's local-currency books, Kraken's slice). Making it uniform would change defined terms.
4. Table 8 and Section 5.3 still ask the reader to trust a time-stamped pre-registration that cannot be shown in an anonymous submission; say in the rebuttal where the time stamps live.
5. Literature is 17 references; the body has no room for more.
6. The monitor sentence "(0 alarm days at the bank closures)" in Appendix F.3 is a result the text does not interpret; it is a macro-driven number and was left.

## Final score (1-10)
8. No CRITICAL, no open MAJOR. The residual risks are scientific (one Bitfinex window, a panel that partly reflects triangular arbitrage, a thin fusion benchmark), and the paper states each of them.

## Submission recommendation
Ready to submit once the author writes the GenAI statement (or decides to defer it to camera-ready) and checks the CCS IDs.
