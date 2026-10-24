# WWW 2027 (ACM Web Conference 2027) requirements and paper audit

Retrieved 2026-10-23. Primary source: https://www2027.thewebconf.org/research-track-papers/ (also ?p=296). Page content was read through a summarising fetch tool, so wording is paraphrased unless quoted; re-read the page once before submitting. Conference: Dublin, 10-14 May 2027.

## Rules (long paper, Web Economics and Digital Society track)

| Topic | Rule | Source |
|---|---|---|
| Submission site | OpenReview, https://openreview.net/group?id=ACM.org/TheWebConf/2027 (long papers: .../Conference_Long_Papers). All authors need an up-to-date OpenReview profile. Contact pcchairs-www2027@acm.org | research-track-papers |
| Deadlines | Abstract 18 Oct 2026; full paper 25 Oct 2026; all end of day Anywhere on Earth (AoE), strict, no extensions; placeholder abstracts forbidden. Results 15 Dec, rebuttal (written only) 15-20 Dec, notification 4 Jan 2027, final version 31 Jan 2027. (One search snippet said results 21 Dec; the official pages say 15 Dec.) | research-track-papers, important-dates |
| Page limit | Long: 8 pages of main content, plus references and an optional appendix, 12 pages maximum in total. The first 8 pages must be self-contained. Short: 4 pages including everything. | research-track-papers |
| Appendix | Optional; may hold reproducibility details, proofs, pseudo-code; counts toward the 12 pages. Submit a single PDF (so the appendix is in the same PDF). | research-track-papers |
| Template | ACM, English, double column. Recommended: `\documentclass[sigconf, anonymous, review]{acmart}`. Word interim template allowed. Files that do not view or print properly are desk-rejected. | research-track-papers |
| Anonymity | Double-blind. Omit author names, affiliations, acknowledgments, identifying information. Refer to own prior work in the third person. Organisations that provided data or hosted experiments may be named. Anonymised arXiv/SSRN preprints are allowed and need not be cited. (One fetch rendering said self-citations and prior-work references must also be omitted; the other said third person. Third person with no identifying link is the safe reading.) | research-track-papers |
| Dual submission | No paper under review at, or accepted by, another peer-reviewed venue with published proceedings. Oral, poster, abstract-only and non-archival prior presentations are allowed. | research-track-papers |
| Web relevance | Page one must state how the work is relevant to the Web and to the chosen track. Papers that only use a Web artifact without addressing a Web research challenge are desk-rejected. | research-track-papers |
| Ethics | Include an ethical use of data and/or informed consent section "when appropriate" (encouraged, not mandatory). Follow ACM policy on research with human participants; state IRB review if any. | research-track-papers |
| GenAI | LLMs cannot be authors. LLMs may be used to rephrase text; authors are solely responsible. ACM policy (secondary sources; acm.org returned 403 to the fetch tool): generative-AI use to create content must be disclosed, normally in the Acknowledgements; use for polishing existing text (like a grammar checker) need not be disclosed. Policy: https://www.acm.org/publications/policies/new-acm-policy-on-authorship and the ACM FAQ https://www.acm.org/publications/policies/frequently-asked-questions. | research-track-papers; ACM |
| Limitations | No required section. | research-track-papers |
| Reproducibility | Code and data release strongly encouraged after review; optional ACM "Artifacts Available" badge needs an archival repository with a DOI. No mandatory statement. | research-track-papers |
| CCS concepts, keywords | Not mentioned in the call. The acmart template emits them on request; including them is the ACM convention. | not in call |
| Abstract length | No word limit stated in the call. | not in call |
| Supplementary material | Not mentioned beyond the appendix and artifact badge. Treat as none allowed. | not in call |
| Authors | Max 7 submissions per author per type. Author list and order frozen at the abstract deadline. Authors may be asked to review; failure can lead to desk rejection. | research-track-papers |
| Track scope | Web Economics and Digital Society covers "Economic aspects of blockchains, cryptocurrencies, and decentralized finance", platforms, markets and exchanges. | research-track-papers |

Unverifiable: exact ACM GenAI wording (acm.org blocked); the CCS concept IDs below (acm.org CCS site blocked); any page limit applying to references beyond the 12 total; whether the abstract registered on 18 Oct was accepted (check OpenReview).

## Audit of paper/main.tex

| # | Requirement | Result | Evidence |
|---|---|---|---|
| 1 | Class `[sigconf,review,anonymous]{acmart}` | PASS | line 3; gate `docclass_anonymous_review` |
| 2 | Body at most 8 pages, 12 total | PASS | gate: body_pages 8, total_pages 12. References start on page 8; appendix follows |
| 3 | Appendix in same PDF, counted in 12 | PASS | `\appendix` in main.tex, 12 pages total |
| 4 | Anonymity (no names, github, acknowledgments) | PASS | gate `anonymity_scan_clean`. Author shows "Anonymous Author(s)". Unchanged by this edit |
| 5 | Web relevance on page 1 | PASS | gate `first_page_mentions_web`; title and abstract open with Web services |
| 6 | Track fit | PASS | crypto exchanges, markets, fusion for aggregators |
| 7 | Venue string | PASS | `\acmConference[WWW '27]` |
| 8 | CCS concepts and keywords | FIXED (was FAIL) | added `CCSXML`, `\ccsdesc`, `\keywords`; IDs to be verified |
| 9 | Ethics statement | FIXED (optional) | one-sentence Ethics paragraph in Discussion; no human subjects |
| 10 | Limitations, reproducibility | PASS | "Limits" and "Reproducibility" paragraphs exist (optional) |
| 11 | GenAI disclosure | AUTHOR DECISION | placeholder comment above the Ethics paragraph; no text written |
| 12 | Artifact links | PASS | none in the paper (github pattern in the gate) |
| 13 | Abstract length | PASS (no limit) | n/a |
| 14 | Dual submission | AUTHOR TO CONFIRM | no other archival submission of this paper |
| 15 | OpenReview profiles, deadline 25 Oct AoE | AUTHOR TO CONFIRM | outside the PDF |
| 16 | Overfull boxes | WARN | gate reports about 58 overfull boxes (a metric, not a hard check) |

## Notes on the edit
- Q2 sentence added to the monitor appendix (macros from q2_numbers); to keep 12 pages, the Alarm-windows heading kept, one redundant sentence each in the calm-year offsets and monitoring subsections of the appendix was cut.
- CCS concept IDs were entered from memory (acm.org CCS site returned 403); verify at https://dl.acm.org/ccs.
