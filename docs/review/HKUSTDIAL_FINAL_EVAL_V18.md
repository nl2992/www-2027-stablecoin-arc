# Final evaluation of draft v18 (WWW 2027, Web Economics and Digital Society)

Date: 2026-10-25 (deadline 25 Oct 2026 AoE). Skills applied: `pre-submission-reviewer` and `idea-evaluator`, with their references. Sources read in full: `draft_v18.txt` (1,168 lines of text export, body, appendices, Tables 1 to 8), `HKUSTDIAL_FINAL_EVAL_V17.md`, `WWW2027_REQUIREMENTS.md`, the Ethics, Reproducibility and GenAI lines of `paper/main.tex`, and rendered page 7 of `paper/build/main.pdf` (12 pages; the body ends on page 8, references begin on page 9).

Scope notes. Paradigm: finance / empirical economics (IV, GMM, panel, robustness) for contributions 1 and 3; benchmark for contribution 2. Retrieval: none this pass, so the novelty judgment stays "unverified; no directly overlapping work retrieved" (carried from v15; closest works Flowerday et al. 2026, Borri and Shakhnov 2023, Makarov and Schoar 2020, Guo et al. 2025, Choi et al. 2019; differing axes: object = the exchange's unit, mechanism = an externally priced anchor, setting = price fusion). A manual dl.acm.org check of WWW 2024 to 2026 remains outstanding. The banned-vocabulary and em-dash scan was run in full on the whole export: zero em dashes; zero banned terms ("first" occurs only as an ordinal or in "first-order", never as a novelty claim).

## 0. What changed since v17

| v17 finding | Status in v18 |
|---|---|
| Item 1, panel may not discriminate (MAJOR) | **Mostly fixed.** Two post hoc placebos in §5.3: mismatched-currency pairs, "median 0.145 over 34 pairs, none reaching one"; no-wedge period (Binance.US against Bitstamp, October 2022), slope 0.009. The test can return something other than one. Gaps: no intervals, no sample sizes, "34 pairs" unexplained (8 units give 56 ordered pairs), and the median is 0.145, not zero (a shared component remains). Binance's seven currencies still share one X and one instrument. |
| Item 2, abstract omits panel reservations (MAJOR) | **Partly fixed.** The abstract now says "partly reflecting triangular arbitrage within each venue" and calls Kraken "uninformative about a wedge". It still does not say that P1 failed narrowly (the body says so). |
| Item 3, straw-man comparator (MAJOR) | **Partly fixed.** Post hoc comparator C (venue's USDT at one dollar): 8.30 bps against 6.8 for A and 128.1 for O. The paper says "most of the gain comes from the stablecoin market, and Tether's correction adds a little more". Honest, but it is one sentence with no interval, not in Figure 4b, and the abstract and Figure 4 caption ("about 19 times") still headline O against A. The real contribution is therefore "convert through the venue's own stablecoin market", not the netted anchor. |
| Item 4, pre-registration unauditable (MAJOR) | **Not fixed.** §5.3 now defines P1, P2 and the falsification rule (three terms), but Table 8 still says "P1 to P3", and the time-stamp location is still "a time-stamped document" with no archive, commit hash or chair-access statement. |
| Item 18, GenAI disclosure (MAJOR) | **Not fixed.** `main.tex` line 462 still reads "% AUTHOR DECISION REQUIRED (GenAI disclosure)". Appendix B still describes "A bounded loop of 12 iterations, each editing only the estimator". |
| Item 10/22, headline results not in body figures | **Fixed.** Figure 4 (page 7) is the two-panel figure: forest by currency (panel and Kraken groups, different colours, 0.72 axis, AUD cut marked) and official against anchor errors per unit on a log axis. Legible at 70 dpi; the caption leads with the finding. |
| Ethics and reproducibility in the first pages (Patch 6) | **Fixed in the body** (§6, page 8): Ethics and Reproducibility paragraphs. Weakness: "scripts that rebuild them ... are provided" but there is no anonymous artifact link and the raw files are not shared. |
| Abstract about 300 words, ambiguous last sentence | **Fixed.** About 230 words; the last sentence gives both numbers (128.1 against 6.8; 107.4 against 5.4) and "We tested only crypto exchanges." Still about 22 numbers. |
| Economics positioning and keywords | **Fixed.** The introduction now opens on a Web practice (price pages converting at official rates, aggregators, oracles); keywords include stablecoins, capital controls, exchange rates. |
| Literature (17 references, Patch 9) | **Not fixed.** Still 17 entries; the newest truth-discovery reference is 2015; no IMF or P2P-premium source, no cross-currency-basis source. |
| Mechanical items (Eq. 5 `c`, "Its market traded", "dearer", "supports") | **Not fixed.** All four remain (lines 249 and 314, 444, 225, 138). |
| Kraken caveat and "supports" | The body now calls Kraken "weak evidence of a venue-specific wedge" and the abstract "uninformative"; consistent. |

## 1. Pre-submission review

### Summary
- CRITICAL: 0
- MAJOR: 3 (items 1, 2, 3)
- MINOR: 12
- Top three fixes first: (1) decide and write the GenAI statement and remove the `main.tex` comment; (2) state in the abstract that P1 failed narrowly and give the comparator C number next to O and A (8.3, 6.8, 128.1), so the headline is not a straw man; (3) give the pre-registration time-stamp location, reconcile "P1 to P3" with the three terms in §5.3, and add an interval and a count to each placebo.
- Page budget: 12 of 12 pages; body ends on page 8 (the conclusion). Any addition needs an equal cut.

### Step 0: paradigm and venue fit
Finance / empirical economics: identification credibility, robustness and economic against statistical size carry the weight. Venue fit is now better than in v17: the introduction opens on a Web practice and the keywords carry the economics terms, which should steer assignment toward economics reviewers. The residual risk is a fusion reviewer who sees a crypto-only paper ("We tested only crypto exchanges."). Fallbacks if rejected: Finance Research Letters, Journal of International Money and Finance.

### Dimension 1: Macro logic
| # | Finding | Severity | Suggested fix |
|---|---|---|---|
| 1 | GenAI disclosure undecided, and the paper describes an automated edit loop. `main.tex`: "% AUTHOR DECISION REQUIRED (GenAI disclosure)"; Appendix B: "A bounded loop of 12 iterations, each editing only the estimator"; Table 8: "The estimator (12 runs, 3 kept)". ACM requires disclosure of generative-AI use to create content. | MAJOR (compliance) | Author decision today: one neutral sentence in the Acknowledgements position if any text, code or analysis was AI-created, or confirm it is not required; delete the comment either way. |
| 2 | Headline comparison still leans on O. Abstract and Figure 4 caption: "128.1 against 6.8", "about 19 times"; body: "Converting through the venue's USDT at one dollar (post hoc) erred 8.30 bps". The reader learns of C only in §5.5. The abstract also omits that P1 failed ("P1 failed narrowly"). | MAJOR | Abstract: "...128.1 bps at official rates, 8.3 through the venue's stablecoin at par, 6.8 with Tether's price netted out". Add "the primary prediction failed narrowly". Add C to Figure 4b or give its interval in the text. |
| 3 | Pre-registration cannot be audited. Table 8: "in a time-stamped document written before any of its prices were listed or downloaded"; "P1 to P3" against §5.3, which defines "P1 ... P2 ... and a falsification rule". | MAJOR | State where the time-stamp lives ("an anonymised archive with commit dates, available to the chairs on request") and claim no more than a commit date proves. Use "P1, P2 and the falsification rule" in Table 8. |
| 4 | Placebos are thin. "Pairing a currency's gap with another currency's USDT price gave slopes well below one (median 0.145 over 34 pairs, none reaching one); with no wedge ... the slope was 0.009." No interval, no hours, no reason for 34 pairs, and 0.145 is not zero. | MINOR (upgrades to MAJOR if a reviewer reads it as selective) | Add the range of the 34 slopes, one interval for the pooled placebo, the hours for the no-wedge case, and one clause on why 34 of 56 pairs (and why a median of 0.145). |
| 5 | The Kraken slice and caveat (a) still say the slope near one is partly an identity ("A slope near one therefore partly reflects triangular arbitrage within the venue"). The placebo helps but the identified result is still one Bitfinex window plus a panel that is partly mechanical. | MINOR (reviewer risk, see §5) | Keep the honest framing. One sentence tying the no-wedge placebo (0.009) to caveat (a): the test is not an identity where no wedge exists. |
| 6 | Calm Bitfinex years: "it was lower (0.87 to 0.86 in 2020 to 2023, Table 1) ... we draw no conclusion". Table 1 gives 0.87, 0.83, 0.84, 0.86, so the quoted range is wrong ("0.83 to 0.87"). | MINOR | Correct the range. |
| 7 | Web practice asserted without evidence. Introduction: "A price page quotes a local-currency market in dollars at an official exchange rate"; "a loyalty point can all carry the name of a common unit". The loyalty and platform-credit examples are speculation. | MINOR | Either one citation or screenshot-level evidence of a price service converting at official rates, or "for example, a service may". Drop the loyalty point or mark it as hypothetical. |
| 8 | Fusion framing. "A plain median was hard to beat in three fusion tests and failed in two pre-registered ones." In Q1 the median fails but the USD-quoted median is within 0.07 of the fuser, a baseline the paper says any aggregator can run. | MINOR | One clause in the abstract or Discussion separating the plain median from the dollar-quoted median. |
| 9 | Chain integrity. Background, limitation, key idea, challenge, Figure 1, three contributions mapped to §3, §5.2 to §5.5, §5.6; running example (Bitfinex 2018 to 2019) in §3, §5.2 and the Conclusion; the official-rate result now closes the introduction. Contribution (3) is still a bag. | n/a | Intact. |
| 10 | Literature thin for the venue: 17 references, none on cross-currency basis, none newer than 2015 on truth discovery; capital controls rest on Borri and Shakhnov and Choi et al. | MINOR (MAJOR to R3) | Add 4 to 6 verified references if space allows (the body is full, so they must replace lines in §2). |

### Dimension 2: Writing details
| # | Finding | Severity | Suggested fix |
|---|---|---|---|
| 11 | Abstract: about 230 words and about 22 numbers across six results. Each sentence has a result, but the density will tire a skim reader. | MINOR | Drop the Binance.US 1.00 sentence or the two interval bounds on the Kraken slice. |
| 12 | §5.2 "Bitfinex: the dollar, net of Tether" is about 35 lines and mixes the headline, hourly intervals, the grid and per-year results. | MINOR | Split after "close to one" and put the grid in its own paragraph. |
| 13 | Repetition: the Binance.US window appears in §3.1, §5.2, §5.6 and Appendix C; Kraken coverage in §4 and Appendix C. | MINOR | Point back. |

### Dimension 3: English grammar
| # | Finding | Rule | Severity |
|---|---|---|---|
| 14 | "Its market traded in 99.93% of the hours of the Bitfinex stress window": "Its" has no clear antecedent (Kraken). Unfixed since v15. | G6 | MINOR |
| 15 | "the source quotes items dearer in its unit": unidiomatic. Unfixed since v13. | G7 | MINOR |
| 16 | "the unit anchor 𝑘 is an item whose true price is fixed" is fine; no article or agreement errors found elsewhere in a full read. | n/a | OK |

### Dimension 4: LaTeX format
| # | Finding | Severity | Suggested fix |
|---|---|---|---|
| 17 | `[sigconf, review, anonymous]`, 12 pages, anonymous block, CCS and keywords present. | n/a | OK. CCS IDs still unverified at dl.acm.org/ccs. |
| 18 | Eq. (5) uses `c = 1/2` for shrinkage while §3.1 uses `c_t = u_t + δ_t` for the offset. Unfixed since v13. | MINOR | Rename the shrinkage constant (`κ`). |
| 19 | Pointers: §5.5 says "Q1 (Table 8; Figure 6, Appendix F)" but Figure 6 prints on page 10 beside Appendix C; Related Work cites "(§5.5, Appendix E)" for validation (held-out is §5.4); Table 1 reports 4,434 hours and Table 4 3,848 for the same stress window while the caption says Table 4 is reproduced "up to the hours in which Kraken traded" (Kraken coverage cannot add hours). | MINOR | Fix the pointers; one clause on the hour counts. |
| 20 | Figure 6 caption uses "B0, B2, B3, oracle"; the text uses "median, conversion, CRH, USD-quoted median"; panel labels "Q-E2 to Q-E4" without explanation of Q-E1 and Q-E5. | MINOR | Label with method names. |
| 21 | Table 1 still carries the "95% CI (weeks)" column (11 numeric columns); Table 2 has 10. Captions of Tables 1 and 2 lead with definitions, not findings. | MINOR | Drop the weeks column; lead the captions with the finding. |

### Dimension 5: Figure quality
| # | Finding | Severity | Suggested fix |
|---|---|---|---|
| 22 | Figure 4 (two-panel, page 7) is good: the finding leads the caption; panel (a) marks groups by colour and by label, panel (b) uses solid and hatched bars (dual encoding); the log axis is stated. Panel (b) omits C. | MINOR | Add C as a third bar or say in the caption that C is 8.3 pooled. |
| 23 | Figures 1 to 3 legible; Figure 5 and 6 are appendix figures with fine tick labels. | MINOR | Check font size after scaling in the final PDF. |

### Banned-vocabulary and em-dash scan (full text)
- Em dashes: 0.
- Banned terms: all 0 across the whole export (case-insensitive search for innovative, pioneering, revolutionary, transformative, superior, surpass, excel, remarkable, unprecedented, breakthrough, general-purpose, capable of, notably, yielding, encompass, differentiate, reveal, underscore, pave the way, highlight, profound, stems from, rigid, impede, yet).
- Overclaim scan: "solve", "state-of-the-art", "extensive", "novel" all 0. "supports the one-offset model (§5.4)" in the introduction is the one live softness (v17 item 5, unfixed).
- Result: clean.

### Final score
**7 of 10** (v17: 7). Zero CRITICAL, three MAJOR (GenAI, the headline against O, the unauditable pre-registration). Content is stronger than v17 (two MAJOR content items closed or reduced, body figure, ethics block), but the near-ready bar (zero CRITICAL and at most two MAJOR) is still one MAJOR short, and two of the three are text-only. With items 1 to 3 closed it is an 8.

### Submission recommendation
Ready to submit after about two hours of text-only edits (items 1 to 3, the abstract, the mechanical fixes). Nothing in the three MAJOR items needs a new run.

## 2. Review panel (WWW 1 to 5 scale)

Scale: 5 strong accept, 4 accept, 3 borderline, 2 weak reject, 1 reject.

### R1: econometrician / empirical finance
Scores: soundness 3, novelty 3, significance 3, presentation 4. **Overall 3 (borderline, upper)**.
Strengths: the netted-anchor identification with a stated proposition; size and power simulations (Table 5); a 360-cell grid disclosed as post hoc; the pre-registered panel with day fixed effects, currency-level resampling (0.957 to 0.987), leave-one-out (0.974 to 0.984) and an honest P1 failure; and now two placebos showing the test does not return one by construction (0.145 median for mismatched currencies, 0.009 with no wedge). Weaknesses: (i) the placebos have no intervals and no counts, and 0.145 is not zero; (ii) the Kraken slice is "weak evidence of a venue-specific wedge" and caveat (a) says the slope "partly reflects triangular arbitrage", so the panel is partly an accounting relation; (iii) 0.83 to 0.87 in calm Bitfinex years is set aside; (iv) lambda = 1 is rejected everywhere; (v) A1 to A4 untestable; (vi) pre-registration cannot be checked. Movement from v17: soundness stays 3, but the main objection (the test may not discriminate) is now answered in two sentences. A generous R1 gives 4.

### R2: Web data fusion / truth discovery
Scores: soundness 3, novelty 2, significance 3, presentation 3. **Overall 2 (weak reject, upper end)**.
Strengths: a clear error type (a source-wide unit offset) that reliability weighting and robust aggregation do not model; frozen methods scored once; two pre-registered tests where the median fails, one about what price services do; candid negative results; the introduction now states the Web practice. Weaknesses: everything is crypto exchanges; "a platform credit ... a loyalty point" is rhetoric, not a result; the fuser loses to a dollar-quoted median in two of four STABLE cells and edges it in Q1 by 0.07; the official-rate result is mostly "use the venue's own stablecoin market" (C 8.3 against A 6.8 against O 128.1), a simple deployable rule and not a method contribution; reference list thin on truth discovery after 2015. Movement: presentation 3 holds; the post hoc C comparator removes the straw-man charge but also removes the netted anchor as the cause of the gain. Overall unchanged.

### R3: web economics / crypto markets
Scores: soundness 4, novelty 4, significance 4, presentation 4. **Overall 4 (accept)**.
Strengths: a testable answer to what Flowerday et al. say "cannot be tested directly"; the ledger-dollar against Tether split; seven local-currency markets plus Korea with wedge sizes (63 to 112 bps monthly); a price-service error result with an applied hook; the new body figure makes the panel visible; an ethics block. Weaknesses: capital-control literature is still sparse, Korea is a half result (Upbit 1.032, Bithumb 0.833), Kraken dilutes rather than adds. Movement: none; R3 is firm, presentation slightly better.

### R4: area chair (meta)
Scores: soundness 3, novelty 3, significance 3, presentation 4. **Overall 3 (borderline)**.
Reasoning: R3 4, R1 3 (up to 4 if the placebos convince), R2 2. The AC now has two defensible sentences: "the median of officially converted markets erred by 107.4 bps against 5.4" and "the placebos return 0.145 and 0.009". The AC will note: crypto-only for a Web conference; the fuser ties the median; the panel is partly arbitrage; the comparator that a service could run (C) is close to A. The AC cannot defend an unresolved GenAI comment.

**Panel mean: 3.0** (v17: 3.0). Profile 4, 3, 3, 2 unchanged; the upside is slightly better (R1 has a path to 4).

## 3. Idea evaluation (updated for v18)

### 3.1 First impression
Paper type: New Setting with a Novel Problem framing, executed as finance identification plus a small benchmark. One-sentence story: a source's currency name can hide a different backing; an anchor priced outside the source's ledger identifies the unit; the netted slope is 0.97 at Bitfinex and 0.978 on a pre-registered panel (partly arbitrage, with placebos at 0.145 and 0.009), and converting through the venue's own stablecoin cuts the error of official-rate conversion from 128 bps to 7 to 8. The story is clear in one sentence.

### 3.2 Fatal-flaws audit

| # | Flaw | Severity | Change since v17 | Defense |
|---|---|---|---|---|
| A | Identification not shown to discriminate (finance: endogeneity; F6 unverifiable claim). | **MAJOR, reduced (towards MINOR)** | Two placebos now return well below one and about zero. Interval, counts and the 0.145 residual are missing. | Add intervals and counts; one sentence on why 0.145. |
| B | Fusion contribution does not beat a deployable simple rule (data-refuted as a method claim). | MAJOR, handled as a negative result | Slightly worse for the netted anchor: C at 8.3 is close to A at 6.8, so the gain is the stablecoin market, not the correction. The framing "when a plain median fails" survives. | State the finding as the paper does; put C in the abstract. |
| C | Web generalisation untested (F2, F6). | MAJOR | Unchanged in evidence; better positioned in the introduction and keywords. | Keep "We tested only crypto exchanges." |
| D | Pre-registration cannot be audited (F6). | MAJOR | Unchanged: no location, "P1 to P3" against three named terms. | Time-stamp location; fix the label. |
| E | Sprawl (F8). | MINOR | Three contributions; (3) a bag; the appendix is large but the body is clean. | Fine. |
| F | Literature thin (finance substitution 5). | MINOR (MAJOR to R3) | Unchanged (17 references). | Verified additions if space allows. |
| G | Compliance: GenAI disclosure undecided. | MAJOR (administrative) | Unchanged. | Author decision today. |

No flaw is CRITICAL and nothing is data-refuted as the identification claim (the panel and Bitfinex agree, and the placebos behave). Under the severity rule: Accept with Revisions. Novelty: unverified (see scope notes).

### 3.3 Lifecycle and capability
| Aspect | Input | Assessment |
|---|---|---|
| Idea category | Data-intensive empirical study | Complete as a submission. |
| Lifecycle | Deadline 25 Oct AoE; rebuttal 15 to 20 Dec | Text-only edits left; no new run needed. |
| Fit | Green for text; Red for anything needing a new download or an author decision not yet made (GenAI). | |

### 3.4 Dimension scores
Start at 5; movement justified by reported results.

| Dimension (finance framing) | v17 | v18 | Evidence |
|---|---|---|---|
| Identification quality | 7 | 7 | Placebos 0.145 (34 pairs) and 0.009 answer the discrimination question; caveat (a), the Kraken slice and the thin placebo reporting hold the score. |
| Economic magnitude | 7 | 7 | 128.1 bps against 6.8 (and 8.3 at par); wedges 63 to 112 bps per month; Bitfinex about 250 bps. |
| Mechanism novelty | 6 | 6 | Unchanged. |
| Data contribution | 5 | 5 | Hashed manifests, scripts, no release (raw files not shareable). |
| Policy relevance | 6 | 6 | Price services converting at official rates is actionable; C shows a one-line fix. |

| STEM dimension | v17 | v18 | Evidence |
|---|---|---|---|
| Higher | 6 | 6 | A beats O in 6 of 6 units; fuser narrowly beats the dollar-quoted median in Q1 (5.5 against 6.2 bps), loses in X1 and X2. |
| Faster | 5 | 5 | Not addressed. |
| Stronger | 6 | 7 | Placebos, currency resampling, leave-one-out, month-block intervals; P1 failure disclosed. |
| Cheaper | 7 | 7 | Public data, hashes, generated numbers. |
| Broader | 6 | 6 | Three venues, seven currencies, won, Kraken fiat; still crypto. |

All movements cite reported results. No dimension reaches 8, so Strong Accept is out.

### 3.5 Paradigm-shift probe
First Principles: yes (a unit is never quoted, so identify it). Elephant in the room: yes (aggregators treat a quote currency as one unit; price services convert at official rates). Technology cycle: no. Hamming's rule: partial. Disruptive potential: possible, not strong.

### 3.6 Feasibility
All needed edits are text. Timeline risk: high only if the author tries a new run now (not recommended).

### 3.7 Verdict
**Accept with Revisions** (unchanged). Worth pursuing as an identification paper whose fusion result is a clear pre-registered failure of conversion at official rates.

## 4. Acceptance judgement

**Estimated probability of acceptance at the WWW 2027 research track: about 30% (range 25 to 35%). v17 was 26% (21 to 31%), so it moved up about four points.**

Why up:
- The main R1 objection (the test returns about one on every population) is answered with two placebos, one of which (0.009 with no wedge) is cleanly near zero and the other (0.145, none reaching one) is far from one. This is the largest single reduction in rejection risk (about +2 points).
- The two headline results are now in a body figure (Figure 4) and the abstract is shorter and clearer (about +1).
- The introduction is aimed at web-economics readers, with economics keywords and an ethics and reproducibility block, which helps reviewer assignment and the AC's framing (about +1).
- The comparator C was added and honestly reported, which removes the straw-man charge even though it narrows the claim (net about 0).

Why not higher:
- R2 is still a 2 and the profile (4, 3, 3, 2) is unchanged; the fuser still ties the median.
- C shows that most of the gain is "use the venue's own stablecoin market", so the netted anchor is a second-order term for the price-service result.
- The GenAI comment, the unauditable pre-registration, the 17-reference list and the mechanical errors are all still open.
- Placebos are post hoc and thinly reported (no intervals, 34 of 56 pairs, 0.145 not zero).

**Single biggest risk.** R1 or the AC concludes that the identified evidence is one Bitfinex window plus a panel that is partly an identity, and the Web-fusion contribution is crypto-only.

**Scenarios.** Text fixes only (GenAI settled, abstract carries C and the P1 failure, pre-registration location, placebo intervals): about 32%. Nothing changed from the current text but the GenAI statement: about 30%. Nothing changed and GenAI open: about 27% with a small desk-rejection tail.

## 5. Remaining reasons a reviewer could reject

1. The panel and the Kraken slice have limited evidential value: a slope near one is "partly" triangular arbitrage ("Caveats (a)"), the Kraken slice is "weak evidence of a venue-specific wedge", and the placebos are post hoc, without intervals, and with a 0.145 median. The identified result is a single Bitfinex window (about six month-blocks) with lambda = 1 rejected.
2. Crypto-only for a Web conference: "We tested only crypto exchanges." Web relevance rests on an asserted practice (price pages converting at official rates) with no citation, and on speculative examples (platform credits, loyalty points).
3. The fusion contribution is weak: "The estimator ties the plain median"; the fuser loses to a dollar-quoted median in two of four STABLE cells; the official-rate gain is mostly the stablecoin market (8.3 against 6.8 against 128.1), with an anchor conversion that "is close to a triangular identity".
4. Pre-registration cannot be audited (no archive, "P1 to P3" against three defined terms), no artifact link, and ethics and reproducibility offer scripts that reviewers cannot see.
5. The GenAI disclosure is unresolved and the paper describes an automated edit loop (Appendix B, Table 8).
6. Calm Bitfinex years (0.83 to 0.87, intervals excluding one) are set aside with "we draw no conclusion", and the quoted range ("0.87 to 0.86") is wrong.
7. Thin reference list (17 entries; newest truth-discovery work is 2015), no cross-currency-basis or recent Web-venue crypto work.
8. Density and polish: about 22 numbers in the abstract, tables of 10 to 11 numeric columns, unfixed mechanical errors (Eq. 5, "Its market", "dearer", "supports"), one wrong figure pointer.

## 6. Bottom line

The paper is ready to submit once three text-only items are closed, and it is a materially better paper than v17: the placebos answer the discrimination objection, the two headline results are in a legible body figure, the abstract and introduction speak to web economics, and the comparator C is reported honestly. It is not a strong accept for anyone on the panel: R2 will stay a weak reject on crypto-only scope and on a fuser that ties the median, and the netted-anchor correction now looks like a second-order term in the official-rate result. The three things to do today, none needing a run: settle the GenAI statement and remove the `main.tex` comment; put C and the P1 failure into the abstract and give the pre-registration time-stamp location (and reconcile "P1 to P3"); and add intervals and counts to the two placebos. If those are done, submit; if the GenAI decision cannot be made, submit anyway but flag it to the chairs, since a desk-reject tail from an open compliance comment is the only avoidable catastrophic risk. Acceptance probability about 30% (range 25 to 35%).

## 7. Items the authors must confirm outside this file
- Dual submission (no archival venue is considering this paper), OpenReview profiles for all authors, and the 25 October AoE deadline.
- CCS concept IDs were entered from memory; verify at dl.acm.org/ccs.
- The GenAI decision.
- That the abstract registered on 18 October matches the current title and abstract; the panel, Kraken, official-rate and placebo sentences are new since then.
- That the pre-registration documents can be shown to the chairs without breaking anonymity.
