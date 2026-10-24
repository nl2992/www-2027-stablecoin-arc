# Readability pass: edits that could touch meaning (author to confirm)

Scope: body and appendices of `paper/main.tex` and `paper/generated/theory_section.tex`. The abstract is unchanged. No numbers, claims, citations or equations were added or changed. All other edits are sentence splits and word swaps.

1. Theory, Binance.US paragraph. Original: "the netting changes nothing there (two anchors, February to July: X netted, Y not)". Now: "In the two-anchor version (February to July), the netting changes nothing: the estimate is X netted and Y not netted." The parenthesis is read as describing the two-anchor test. Confirm the reading.
2. Theory, Setup. "The estimand" became "The quantity we estimate is lambda, the share of the offset's time variation that comes from the unit". Also split "lambda = 1 under a pure unit shift, whenever demand is uncorrelated with the offset" into "also whenever demand is uncorrelated with the offset". Same content.
3. Theory, Proposition. Added a one-sentence plain definition of "instrument" (another asset's gap that moves with the offset and is unrelated to the anchor's own noise) and spelled out OLS. This restates A4 in words; confirm it is accurate.
4. Theory, Over-identification. Added a plain definition of GMM and Hansen's J, and of HAC ("robust to changing variance and to correlation over time"). Check the wording of "Bartlett ... HAC estimate".
5. Theory, Inference. The block bootstrap is described as resampling runs of consecutive hours. Original gave only the block-length formula.
6. Theory, Simulation. Original "with noise in L as large as its signal, [bias]" is now "It is also unbiased when the noise in L is as large as its signal ([bias])". Original "J has size X" is kept as "J has size X". The sentence order is unchanged.
7. Section 4.2, month-block bootstrap. Added "A month-block bootstrap resamples whole calendar months, so that persistent offsets stay intact" at first use. The "so that" clause gives the purpose of the blocks.
8. Section 4.2, IV check. The sentence "Instrumenting L ... argues against measurement error" was split into a description and a separate conclusion. Same content.
9. Section 4.2, specification grid. "Across 138 specifications (...; specified before it was run but after the headline was seen)" became "We also ran N specifications ... We specified the grid before running it but after the headline was seen." Same content.
10. Section 4.3, protocol. Added "a block bootstrap resamples runs of consecutive hours" (the default block length stays described later as week blocks).
11. Section 4.3, held-out time. "Withholding assets is not withholding time" (a contrast construction) became "Withholding assets leaves time pooled". Confirm this says what you meant.
12. Section 4.4, UNIT-TD. Added "scored as a truth-discovery comparison" (TD expanded as truth discovery, as in Appendix C's title). Confirm that UNIT-TD stands for unit truth discovery.
13. Section 4.4, CRH. Now glossed as "source-reliability weighting" and linked to Related Work (new label `sec:related`).
14. Section 4.4, round 3. Body text now says "the final fuser (called round 3 in the tables)". Confirm that round 3 is the final fuser used everywhere.
15. Section 4.4, Q1 paragraph. "We call this follow-up Q1" and a pointer to the set S_hi of Appendix A are new. In the same paragraph the sentence on mean absolute errors was reordered so that each method sits beside its number; "USD-quoted median" is the oracle number as before.
16. Section 4.4, X4. "which failed the fuser's own placebo check" now starts its own sentence "X4 failed the fuser's own placebo check". Original attached it to X4; same reading.
17. Discussion, advice paragraph. The original sentence "Then report the estimated offset and, if the source's volume matters, correcting it keeps its volume" was ungrammatical. Now: "In that case, report the estimated offset. If the source's volume matters, correcting the source keeps its volume." Confirm. Also "may pay when ..." is now "may pay under three conditions" with the same three conditions.
18. Discussion, second application. "In a pre-registered study of Korean exchanges" is now "We pre-registered a study of Korean exchanges". Check that the authors did the pre-registration.
19. Limits. The three-way "rests on" chain is split into three sentences. Same content.
20. Appendix A. The Q1 definitions: "the primary endpoint is" now reads "the primary endpoint is the mean log-error difference", which restates Eq. (endpoint) in words. S_hi is introduced as "the hours with a large shared shift". Equation unchanged.
21. Appendix B, methods. The round-3 description is split into four steps in prose; content unchanged.
22. Appendix C. "Both were computed after the locked test" became "after the test assets were scored once".
23. Appendix F caption sentence. Added one-line definitions of pre-registered, locked and post hoc before the table (duplicate of the caption).
24. Page budget. To keep 8 body and 12 total pages, four figures were shrunk (anchor scatter to 0.88 of the column width, robustness forest and Q1 error figures to 0.6, the two-shock figure to 0.36 of the text width). Check that the figures stay legible.
25. Duplicates removed or cross-referenced. Appendix G.1 no longer repeats the median bitcoin gap of Bitfinex against Bitstamp and now says "As Section 5.5 says"; the body keeps the number. Section 5.4 no longer says "Two other events (Q-E1, Q-E5) failed the gate" (the same fact stays at the end of that paragraph) and no longer notes that T1 was known in advance (Appendix F keeps it). The Formal test paragraph in Section 5.2 is shortened and keeps every number. Appendix E no longer repeats the pointer to Table 9 for the large-gap hours.
26. Table order. The two appendix tables on the unit diagnostic and the robustness evaluation now sit before Appendix A in the source so that the floats fit in 12 pages. Only table numbers shift in the PDF.

Banned constructions: none remain in `main.tex` or `theory_section.tex` (checked by search for "rather than", "instead", "not ... but", ", not").
