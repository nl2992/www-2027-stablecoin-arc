# Final evaluation of draft v13 (WWW 2027, Web Economics and Digital Society)

Date: 2026-10-24. Skills applied: `pre-submission-reviewer` (full audit plus review panel) and `idea-evaluator` (fatal-flaws audit, dimension scores), both updated against `HKUSTDIAL_PRESUB_V9.md` and `HKUSTDIAL_IDEA_EVAL_V10.md`. Sources read in full: `draft_v13.txt` (1,084 lines), `WWW2027_REQUIREMENTS.md`, both earlier evaluations. Also read: `paper/main.tex` (the GenAI comment, discussion), and rendered pages 1 to 8 of `paper/build/main.pdf` (12 pages). The PDF's page count is 12.

Scope notes. Paradigm: finance / empirical economics (identification, GMM, robustness) for contributions 1 and 2; benchmark / data fusion for 3 and 4. Retrieval: no new literature search was run for this pass. Novelty judgments below inherit V10's retrieval (section 3 of that file) and are labelled "inherited, not re-verified"; a hand check of WWW 2024-2026 proceedings is still outstanding. The banned-vocabulary scan was run in full on the whole draft text (not sampled), by case-insensitive search for every term in `forbidden-patterns.md`.

## 0. What changed since V9 and V10

| Earlier finding | Status in v13 |
|---|---|
| V9: no Conclusion (MAJOR) | **Not fixed.** The paper still ends with Discussion paragraphs "Limits", "Ethics", "Reproducibility". |
| V9: contribution 4 thin (MAJOR) | **Not fixed.** Still listed as contribution (4); §5.5 is now two short paragraphs pointing to Appendix F.1. The Q2 pre-registered tie is one sentence in Appendix F.2. |
| V9: leading sentences for §3 and §5 | Fixed ("This section sets up the model..."; "This section shows which exchanges...") and every subsection now opens with a one-line signpost. |
| V9: abbreviations (GMM, HAC, CRH) | Fixed. |
| V9: bold captions, unreferenced equations, 35-line paragraph | Fixed; verified in the render. |
| V10 flaw B: Q1 win scored against baselines that omit the dollar-quoted-only median | **Largely fixed in the body.** §5.4 and Figure 5 now report that rule: 6.2 bps against 5.5 for the fuser, "the edge was small (-0.07, -0.11 to -0.03)". The abstract was not updated to match (see C-1 below). |
| V10 flaw A: single identified episode; "mostly" overreads a covariance share | **Partly fixed.** §3.1 and §5.2 now define lambda as a covariance share, give the month-block interval as the headline, and say "close to one". The abstract still says "the offset moved mostly with Bitfinex's dollar". The single-regime limit is stated in "Limits". No independent USDT leg (E1) was added. |
| V10 flaw C: sprawl, Q2 data-refuted for the monitor | The Q2 null is reported (Appendix F.2, "tied"), and the paper does not claim early warning. Contribution 4 is still listed. |
| V10 flaw D: Web generalisation untested | Unchanged and acknowledged ("We have tested it only on crypto exchanges"). |
| V10: Related Work additions (Borri and Shakhnov, Choi et al., Guo et al.) | Added (refs [1], [2], [6]). |
| Readability | Clearly better: plain definitions, "Intuition:" lines, worked example in §3. |

Net: the draft is more honest and more readable than v9/v10. Its three structural weaknesses (one episode, a thin fusion contribution, no Web evidence beyond crypto) are unchanged, and none can be fixed without new data.

## 1. Pre-submission review

### Summary
- CRITICAL: 0
- MAJOR: 6
- MINOR: 9
- Top three fixes first: (1) bring the abstract's last sentences into line with §5.4 (the dollar-quoted-only median nearly ties the fuser, and beats it in two of the four STABLE cells); (2) add a short Conclusion and cut or demote contribution (4); (3) make the first eight pages self-contained by moving one decisive appendix result (simulation size and power, Table 5 top panel) into the body.
- Page budget: 8 body pages, references begin on page 8, 12 pages total. Within the limit.

### Step 0: paradigm and venue fit
Paradigm: finance / empirical economics. Weights go to identification credibility, robustness, and economic versus statistical significance. Venue fit: the track lists blockchain and decentralised finance, markets and exchanges; the paper's page one opens with Web services (aggregators, oracles, marketplaces), satisfying the Web-relevance rule. No mismatch. The residual risk is audience, not scope: truth-discovery and Web-data reviewers will read a one-domain crypto paper (see reviewer R2). Fallback venues if rejected: Finance Research Letters or Journal of Banking and Finance for the identification result; a data-management venue (VLDB, CIKM) only with non-crypto evidence added.

### Dimension 1: Macro logic
| # | Finding | Severity | Suggested fix |
|---|---|---|---|
| 1 | No Conclusion. The text ends: "Reproducibility. Every number is a macro generated from committed reports and logs..." | MAJOR | Replace the "Ethics" and "Reproducibility" paragraphs' space with a five-line Conclusion that restates the one robust finding and its boundary, with no new numbers. |
| 2 | Abstract's last sentence: "a frozen unit-aware method beat the median, stablecoin conversion and source-reliability weighting (CRH)". Body §5.4: the dollar-quoted median scored 6.2 against the fuser's 5.5 and "the edge was small"; Table 2 shows that median at 0.63 against the fuser's 1.33 on X2 (TUSD) and 0.65 against 0.72 on X1 (USDC). A reader who stops at the abstract is told the wrong story. | MAJOR | Add "and came within 0.7 bps of a dollar-quoted-only median" to the abstract, or name that median as the comparator that remains. This is the exact risk V10 flagged as flaw B. |
| 3 | Contribution (3) is titled "A fusion benchmark and a scope condition", but the paper's own result is "a plain median is hard to beat" and the unit-aware fuser loses to the median in 4 of 9 locked cells (T2 1.50, X2 1.33, X3 2.46, X4 1.32) and wins the other five only by 0.03 to 0.28 (T1 0.93, T3 0.95, T4 0.97, T5 0.97, X1 0.72). §6 then recommends "Keep the plain median by default." The contribution is a negative result presented as a positive one. | MAJOR | Say so in the contribution line: "a benchmark showing when a plain median suffices". Reviewers reward honest nulls only when the framing admits them. |
| 4 | Contribution (4), "A monitor with a fixed rule, scored on a small label set" is supported by two short body paragraphs and the paper itself says the "fee bands, monitor labels and oracle check are thin". Four contributions across identification, validation, benchmark and monitor (canonical F8). | MAJOR | Fold (2) into (1) as validation; demote (4) to "supporting results". Lead with (1) and (3). Two to three contributions is what a reviewer can hold. |
| 5 | Headline attribution. The abstract's "0.97 (95% interval 0.94 to 1.00)" is the month-block interval over "about six month-blocks", the grid was "specified before it was run but after the headline was seen", and lambda = 1 is rejected (p < 0.001). The paper discloses all of this. | MINOR | Disclosure is adequate. One more word in the abstract ("close to one" instead of "mostly") would match §5.2's own wording. |
| 6 | Chain integrity: background, limitation, key idea ("Our idea is that..."), challenge ("This is hard for two reasons"), figure, contributions. Contributions map to §3, §5.2, §5.3, §5.4, §5.5 to 5.6. The running example (Bitfinex 2018 to 2019) appears in §3's worked example, §5.2 and §6. | n/a | Intact. |
| 7 | First eight pages are not fully self-contained. The size and power evidence for the headline test is "Table 5" in Appendix C; per-asset scores (Table 6), the anchor-by-slice table (Table 4) and the fusion index table (Table 7) are appendix-only. The call says the first 8 pages "must be self-contained". | MAJOR | Move the top panel of Table 5 (seven rows) into §3.1 as a compact table; the text already quotes its numbers (0.92, 0.72, 0.06, 0.03, 0.48). Offset with a cut in §5.1 or §6. |

### Dimension 2: Writing details
| # | Finding | Severity | Suggested fix |
|---|---|---|---|
| 8 | The abstract is about 290 words and carries 12 numbers ("0.97 (95% interval 0.94 to 1.00), up from 0.71", "0.989", "0.353", etc.). It reads as a finance paper and buries the Web framing in its first three sentences. | MINOR | Cut the held-out numbers (0.989 and 0.353) and the Binance.US sentence from the abstract. |
| 9 | Topic sentences present for nearly every paragraph; several remain very dense. "Bitfinex: the dollar, net of Tether." is a single block of about 40 lines in two columns of §5.2, mixing two intervals, a grid, a regression on Kraken and a sample-size note. | MINOR | Split after "Netting the external price out raised the slope to 0.97." and after "We therefore treat the month-block interval as the headline". |
| 10 | Repetition: the 22 June to 31 July Binance.US window (530 hours, 557 bps) is stated in §5.2, §5.6 and Appendix F.3. Calm-year offsets restated in §5.5 and F.1. | MINOR | Point back. |
| 11 | Overclaim scan: "first" is ordinal; "solve" 0; "state-of-the-art" 0; "extensive/comprehensive" 0. §5.2 "Bitfinex's premium was therefore mostly a discount on the exchange dollar" is bounded by the next sentences (covariance share). | n/a | OK. |
| 12 | Binance.US in the abstract: "gave a slope of 1.00, as expected once its deposits closed". §5.2 calls it "close to mechanical" and says "We therefore do not say that Binance.US passed." The abstract version sounds like replication. | MAJOR | Rewrite: "Binance.US in 2023 gave 1.00, which is close to mechanical once deposits closed". Replication count is one; do not let the abstract imply two. |

### Dimension 3: English grammar
| # | Finding | Rule | Severity |
|---|---|---|---|
| 13 | "Whether that premium priced the exchange's dollar" (V9 item 9) now reads "reflected a discount on the exchange's dollar or on the coin" in the abstract and intro; the verb "priced" no longer appears. | G7 | Fixed. |
| 14 | Mixed tenses in Related Work ("TruthFinder and CRH estimate", "Flowerday et al. studied", "They read"). Present for methods, past for findings is defensible. | G3 | MINOR, leave. |
| 15 | Spelling is British ("generalised", "anonymised", "centred") and consistent; the ACM template allows it. "Dearer" in the Conventions paragraph ("quotes items dearer in its unit") is idiomatic British and may read as archaic to some reviewers. | G7 | MINOR: "at a higher price". |
| 16 | Article and agreement errors: none found in a full read. | n/a | OK. |

### Dimension 4: LaTeX format
| # | Finding | Severity | Suggested fix |
|---|---|---|---|
| 17 | Class `[sigconf, review, anonymous]`; 12 pages; references begin on p. 8 right column. Author block reads "Anonymous Author(s)". ACM reference format shows "12 pages". CCS concepts and keywords present. | n/a | OK. |
| 18 | The GenAI comment in `main.tex` (lines 501-504) marks an author decision not taken. The development process is described as "a bounded loop of 12 iterations, each editing only the estimator"; if an AI system proposed those edits or wrote any text, the disclosure question applies. ACM policy requires disclosure of generative-AI use that creates content; LLMs may rephrase. A reviewer or the PC chair who notices is a desk-rejection risk if the policy was missed. | MAJOR | Decide before 25 Oct AoE. If AI created any text or code that is in the paper, add a neutral one-line statement in the anonymised version or confirm the camera-ready credits plan. This is a compliance item, not a taste one. |
| 19 | Hyphenated labels, about 58 overfull-box warnings (V9: 41), all in generated tables and math. Equation numbers are all referenced. Equation (5) reuses `c` for the shrinkage constant while the anchor model uses `c_t` for the offset; both are defined, but the clash is visible on page 3 ("c = 1/2" in Eq. (5), "c_t = u_t + δ_t" in §3.1). | MINOR | Rename the shrinkage constant (for example `κ`). |
| 20 | Smallcaps extraction artefacts "PRoposition", "PRoof" appear in the text export only; they are a template effect, not an error. | n/a | OK. |

### Dimension 5: Figure quality
| # | Finding | Severity | Suggested fix |
|---|---|---|---|
| 21 | Figure 4 (the 360-cell robustness forest) is rendered at column width with row labels that are unreadable at print size (checked in the rendered page 6). The result it supports is a headline robustness claim. | MAJOR | Widen to the full page width, or cut it to the 8 to 10 most informative rows. |
| 22 | Figure 1 is vector (TikZ) and clear; the caption's first sentence is a label rather than a finding. Figure 2's caption likewise. Figure 3 and Figure 5 captions state the finding. | MINOR | Lead Figures 1 and 2 captions with the finding. |
| 23 | Table 1 has 11 columns; Table 2 has 10 numeric columns with bold and dagger marks. Both are dense at column width but legible in the render. | MINOR | Drop the "95% CI (weeks)" column from Table 1; the text uses month blocks. |
| 24 | Palette: default colours with line-style and marker dual encoding; colour-blind safety unchecked. | MINOR | Check once with a simulator. |

### Banned-vocabulary and em-dash scan (full text)
- Em dashes: 0 in the whole 1,084-line text.
- Banned AI-tone terms (innovative, pioneering, revolutionary, transformative, superior, surpass, excel, remarkable, unprecedented, breakthrough, general-purpose, capable of, notably, yielding, at its essence, encompass, differentiate, reveal, underscore, pave the way, highlight, profound, stems from, rigid, impede, yet): all 0. "exceed(ed)" appears 3 times as numeric comparison; not flagged.
- Result: clean. This is a genuine strength relative to typical drafts.

### Final score
**7 of 10.** Zero CRITICAL; six MAJOR (no Conclusion, abstract-versus-body mismatch on the fusion result, contribution framing and sprawl, self-containment, GenAI disclosure undecided, Figure 4 legibility; two of these, items 3 and 4, share one fix). The skill's rule limits "near-ready" to at most two MAJOR, so the draft does not qualify.

### Submission recommendation
Needs 1 to 2 days more work, all of it writing and layout, no new data. Items 1, 2, 3/4, 7, 12, 18 and 21 above fit in a day.

## 2. Review panel (WWW 1 to 5 scale)

Scale used: 5 strong accept, 4 accept, 3 borderline, 2 weak reject, 1 reject.

### R1: econometrician / empirical finance
Scores: soundness 3, novelty 3, significance 3, presentation 4. **Overall 3 (borderline)**.
Strengths: the identification argument is clean (Proposition 3.1, the worked example, the raw 0.731 versus netted 0.971 contrast), simulation of size and power with honest coverage numbers (HAC covers 0.72 in the mixture), a 360-cell grid with disclosure that it was specified after the headline, and Table 8, which separates pre-registered, locked and post hoc items. The writing about what lambda does and does not identify is better than most finance submissions.
Weaknesses: (i) one identified regime, six month-blocks, and lambda = 1 rejected at p < 0.001; (ii) the anchor is "close to an accounting identity" with Bitfinex's own USDT book, and the Tether leg is netted with Kraken under an unverifiable assumption (A3); (iii) calm years give 0.83 to 0.87 with intervals that exclude one and the paper "draws no conclusion", so the result has no external validity beyond stress; (iv) assumptions A1 to A4 are "not testable". Wants: an independent leg that reaches October 2018 (V10's E1, still not done).

### R2: Web data fusion / truth discovery
Scores: soundness 2, novelty 2, significance 2, presentation 3. **Overall 2 (weak reject)**.
Strengths: a clear articulation of an error type (a source-wide unit offset) that source-reliability methods do not model; frozen methods scored once; the honest "plain median is hard to beat".
Weaknesses: every dataset is a crypto exchange; the Web generalisation (platform credits, loyalty points, marketplaces) is an untested aside ("We have tested it only on crypto exchanges"); the proposed fuser loses to a dollar-quoted median in two of four STABLE cells and ties it in Q1; the baselines (CRH, GTM) are applied with a trailing 30-day window and two sources coincide with the median. The main method contribution reads as "use the median; correct only if you have an anchor". Asks for a non-crypto domain or a synthetic multi-domain study.

### R3: web economics / crypto markets
Scores: soundness 4, novelty 4, significance 3, presentation 4. **Overall 4 (accept)**.
Strengths: a testable answer to a question the literature itself says cannot be tested (Flowerday et al.), a clean split between the ledger-dollar leg and Tether's own discount, concrete episodes (Bitfinex 2018 to 2019, Binance.US 2023, the March 2023 USDC run), the Silvergate and Signature null, and the Chainlink check. Appreciates that the paper never claims early warning after Q2.
Weaknesses: the monitor is thin; the Korea application (anchor biased toward one, 0.90) is a half result; a reader would like the October 2018 Tether episode covered.

### R4: area chair (meta)
Scores: soundness 3, novelty 3, significance 3, presentation 4. **Overall 3 (borderline)**.
Reasoning: the split R1 3, R2 2, R3 4 is typical of an interdisciplinary track. The paper is carefully calibrated and unusually honest, which helps at rebuttal, but the headline rests on a single episode and the strongest generalisation claim is untested. The meta-reviewer weighs fit with the track (good) against evidence breadth (thin). The decision at a 20% acceptance rate would go to "reject unless a champion exists"; R3 is a potential champion.

**Panel mean: 3.0.** At WWW, a paper with panel scores 4, 3, 3, 2 sits in the bubble. Historically such a profile is accepted well below half the time.

## 3. Idea evaluation (updated for v13)

### 3.1 First impression
Paper type: New Setting with a Novel Problem framing, executed as finance identification. One-sentence story: a source's currency name can hide a different backing, one offset moves all its items, and an anchor priced outside the source's ledger tells a unit shift from demand; on Bitfinex 2018 to 2019 the offset's variation was about 0.97 unit shift once Tether's discount is netted. The story is clear in one sentence. It is still a crypto-exchange result with a Web generalisation asserted, not shown.

### 3.2 Fatal-flaws audit

| # | Flaw | Severity | Change since V10 | Defense |
|---|---|---|---|---|
| A | Headline rests on one identified episode through an anchor close to an accounting identity on Bitfinex's own books; demand confined to dollar-quoted legs is "indistinguishable from a unit shift" (the paper says so). | MAJOR (unchanged) | Disclosure improved; no new evidence. The paper now states lambda is a covariance share, that the level is not identified, and gives the month-block interval as the headline. | Cannot be repaired by writing alone. Lower the abstract's claim to "close to one" and state in one sentence that "unit" means everything specific to the venue's dollar-denominated claims. |
| B | Fusion contribution does not beat the deployable simple rule. | MAJOR; **now data-refuted as a method claim**, handled correctly as a negative result | The USD-only median is now reported: 6.2 against 5.5 in Q1, and it wins X1 and X2 in STABLE (0.65, 0.63 against 0.72, 1.33). Under the skill's rule a mechanism beaten by a simple control must not headline the story. The body does not headline it; the abstract still does ("beat the median, stablecoin conversion and CRH"). | Reframe contribution (3) as a benchmark and a negative finding; fix the abstract; keep Q1 as "the one pre-registered cell where a shared stablecoin unit moved, where all three named baselines lose and the dollar-quoted median nearly ties". |
| C | Sprawl and weak support for contributions 2 and 4 (F8). | MAJOR (unchanged) | Q2 tie is recorded in an appendix sentence; the paper no longer claims early warning. | Fold 2 into 1; demote 4. |
| D | Web generalisation untested (F2, F6). | MAJOR | Unchanged; acknowledged in §6. | Say "price fusion across venues with ledger currencies" and list platform credits as a prediction. Already half-done. |
| E | Missing Related Work | MINOR → resolved | Borri and Shakhnov, Choi et al. and Guo et al. are now cited. | None. |
| F | Timeline | MINOR | One day left. | Writing and layout changes only. |

No flaw is CRITICAL under the skill's rule (nothing is refuted outright and nothing is unfixable by narrowing the claim). The verdict is not "Reject and Pivot", but flaw B is the closest to the data-refuted boundary: the fuser is built, it lost to a simple control in most cells, and the paper responds by narrowing, not by claiming.

Novelty (inherited from V10, not re-verified in this pass): no directly overlapping WWW, KDD, VLDB, SIGMOD, FC or AFT paper retrieved under the V10 keywords; Flowerday et al. (2026) state the hypothesis and call it untestable; Borri and Shakhnov (2023) decompose exchange-currency discounts without a unit-of-account claim. "Not found" is not proof of novelty. A hand check of dl.acm.org for 2024 to 2026 WWW proceedings on stablecoin units and index methodology is still required before submission.

### 3.3 Lifecycle and capability

| Aspect | Input | Assessment |
|---|---|---|
| Idea category | Data-intensive empirical study | Mostly complete. |
| Lifecycle | Submission 25 Oct 2026 AoE; rebuttal 15 to 20 Dec | The remaining job is claim calibration. |
| Fit | Green for writing changes; Red for any new data download (needs the owner's yes) | |

### 3.4 Dimension scores

Start at 5; movement justified.

| Dimension (finance framing, contribution 1) | V10 | v13 | Evidence |
|---|---|---|---|
| Identification quality | 6 | 6 | Same design; clearer assumptions, simulation and inference caveats, but one regime and rejected lambda = 1. |
| Economic magnitude | 7 | 7 | A roughly 250 bps premium over months; lambda does not identify the level. |
| Mechanism novelty | 6 | 6 | Token and ledger split is new; the econometric device is standard. |
| Data contribution | 4 | 4 | Public candles and a Kraken archive; no released dataset. |
| Policy relevance | 5 | 5 | Index providers and oracles; one example cited. |

| STEM dimension | C2 | C3 | C4 | Evidence |
|---|---|---|---|---|
| Higher | 5 | 5 (was 6) | 3 | C3: Q1 5.5 against USD-only median 6.2 (the edge "small"); fuser loses to that rule in X1 and X2; C2 ties the median (0.000); C4 ties single-pair rules on lead time (Q2). |
| Faster | 5 | 5 | 5 | Not addressed. |
| Stronger | 6 | 6 | 4 | Per-year, per-asset and month-block intervals reported honestly; calm years 0.012 to 0.35. |
| Cheaper | 7 | 7 | 6 | Public data, hashes, generated numbers. |
| Broader | 4 | 4 | 4 | Crypto only; Korea anchor biased (0.90). |

Mechanism-based, not yet confirmed by data: none of the above is raised on mechanism alone.

### 3.5 Paradigm-shift probe
First Principles: yes (a unit is never quoted, so identify it). Elephant in the room: yes (aggregators treat a ticker's quote currency as a known unit). Technology cycle: no. Hamming's rule: partial (the paper's own benchmark says the median usually suffices). Disruptive potential: possible, not strong.

### 3.6 Feasibility
| Risk | Level | Mitigation |
|---|---|---|
| Compute | Low | None. |
| Data | Low for what is in hand; high for anything needing downloads | Binance January and February 2019 months need the owner's explicit yes. |
| Engineering | Low | Generated macros and tests exist. |
| Timeline | High | One day. Only writing and layout edits. |

### 3.7 Verdict
**Accept with Revisions** (unchanged from V10), with the fusion claim narrowed. The idea is worth pursuing as an identification-and-honest-null paper, not as a method paper. The dimension scores do not reach Strong Accept: no dimension is at 8 or above.

## 4. Acceptance judgement

**Estimated probability of acceptance at WWW 2027 research track: about 18 to 22%, central estimate 20%.** That is the base rate.

Reasoning. Against the base rate:
- Plus: the paper sits squarely in the track; the problem is clear in one sentence; the identification is more careful than most submissions (simulation of size and power, grid, Table 8's pre-registered, locked and post hoc ledger); the banned-vocabulary scan is clean and the readability pass worked; the paper never overclaims in the body, which survives rebuttal well. R3-type reviewers (web economics, crypto) are likely to champion it.
- Minus: one identified episode with a rejected lambda = 1 and about six month-blocks; the fusion contribution is a negative result; contribution 4 is thin and the paper says so; the "Web" generalisation is a sentence in the Discussion; there is no non-crypto data; a likely R2-type reviewer (truth discovery, data management) scores 2; there is no Conclusion; the abstract overstates the Q1 result relative to the body. Interdisciplinary tracks tend to reject papers whose strongest champion is one reviewer out of three.
- I do not adjust upward for the paper's honesty: PCs reward it only when the headline result is strong, and here the headline is the weakest link. I do not adjust downward for the missing Conclusion: it is cheap to fix.

**Single biggest risk.** The R2-type reviewer reading a crypto-only paper as a finance letter with a Web label. The abstract's claim that a frozen method "beat the median, stablecoin conversion and CRH" will be checked against Table 2, where a dollar-quoted median wins two of four STABLE cells, and the reviewer will conclude that the fusion contribution is not a contribution. If that reviewer also notices the single regime in the identification test, the paper is left with one champion.

**The three cheapest changes (each under a day, no new data):**

1. **Align the abstract and the contribution list with Table 2 and §5.4.** Rewrite the abstract's last sentence to name the dollar-quoted median as the comparator that nearly ties ("within 0.7 bps"), change "gave a slope of 1.00, as expected" to "close to mechanical", change "moved mostly with" to "moved close to one for one with", and retitle contribution (3) as a benchmark that shows when a plain median suffices. This removes the one place where the paper is easier to attack than it deserves, and turns the honest null into a stated contribution. Two paragraphs of edits.
2. **Cut to three contributions and add a Conclusion.** Fold contribution (2) into (1) as validation, reduce (4) to a supporting-results sentence, and write a five-line Conclusion (what was found, and the boundary: one regime, crypto only). Space comes from the abstract's held-out numbers, the Binance.US sentence, and one repeated Binance.US window description.
3. **Make the first eight pages self-contained and fix the one illegible figure.** Move the simulation size and power top panel (Table 5) into §3.1, since the headline inference depends on it ("HAC covers 0.72 in the mixture"), and widen Figure 4 to full width or cut it to its 8 to 10 informative rows. In the same pass, settle the GenAI disclosure line (a compliance item) before the 25 October AoE deadline.

Not recommended in the remaining day: new experiments, a new application, or any new claim. V10's E1 (an independent USDT leg reaching October 2018) would raise the odds most but needs a download the owner has not approved; if there is time after the writing changes, it is the one experiment worth attempting.

## 5. Items the authors must confirm outside this file
- Dual submission (no archival venue is considering this paper), OpenReview profiles for all authors, and the 25 October AoE deadline.
- CCS concept IDs were entered from memory in an earlier pass; verify at the ACM CCS site.
- The GenAI disclosure decision (item 18).
- The first-page Web-relevance statement is present; no check was made that the abstract registered on 18 October matches this title and abstract.
