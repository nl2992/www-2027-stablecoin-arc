# WWW 2027 submission checklist

Deadline: 25 October 2026 AoE. Track: Web Economics and Digital Society. Double-blind. Prepared by the final pass; nothing has been submitted or sent anywhere.

## 1. The file to upload

- PDF: `paper/build/main.pdf` (built from `paper/main.tex` with `acmart` `sigconf,review,anonymous`).
- Pages: 12 in total, 8 of them body (the Conclusion ends on page 8; references start on page 9; appendices A to F follow). Limits are 8 body and 12 total. `uv run python -m www_paper.gate` reports `gate_pass: 1`.
- Rebuild with `uv run python -m www_paper.gate` before uploading, and upload the PDF it leaves in `paper/build/`. The red line numbers on the margin are the `review` option and are expected.

## 2. OpenReview form fields

**Title:** Same Name, Different Unit: Identifying Source-Specific Units in Web Price Fusion

**Abstract** (273 words; the limit is 300; generated into `docs/review/ABSTRACT_SUBMISSION.md` from `paper/main.tex`; the minus signs are written as hyphens so that the form accepts plain text):

> Price services convert and fuse quotes across venues and units, and assume that every source's dollar is the same dollar. Often it is not: a crypto exchange's dollar balance is a claim on that exchange and can lose value when its banking fails, and a service then mistakes a change in the dollar for a change in price. We identify such a unit shift from public prices. What all assets on an exchange share in their price gaps measures its dollar offset, and a stablecoin traded there, corrected for its price elsewhere, separates a move in the dollar from demand for the assets. On Bitfinex from November 2018 to May 2019, net of Tether's own price on Kraken, its Tether price tracked the offset with slope 0.97 (95% interval 0.94 to 1.00); Binance.US in 2023 gave 1.00, close to mechanical. A pre-registered panel of eight currency units gave a pooled slope of 0.978 (0.962 to 0.989), just short of its pre-registered target of an interval that includes one; the slope partly reflects triangular arbitrage within each venue. A pre-registered Kraken slice, uninformative about a wedge, gave 1.005 (0.867 to 1.289). A plain median was hard to beat in three fusion tests and failed in two pre-registered ones. Where most trading shared a stablecoin that lost its peg, a frozen unit-aware method beat the median (log-error difference -1.08, -1.36 to -0.83). In six local-currency markets, converting at official rates erred by 128.1 bps against 6.8 through the venue's own stablecoin (8.30 with the stablecoin taken at par), and the median of officially converted markets by 107.4 bps against 5.4. We tested only crypto exchanges.

**Keywords** (paper, `\keywords`): price fusion, price services, unit of account, stablecoins, capital controls, exchange rates, identification, truth discovery, cryptocurrency exchanges.

**Keywords for the form** (shorter list suggested in `ABSTRACT_SUBMISSION.md`): exchange dollars; unit of account; truth discovery; price feeds and oracles; Web data quality; cryptocurrency markets; reproducibility. Pick one list and use it consistently; the paper's own list carries the economics terms that steer reviewer assignment.

**CCS concepts** (from `main.tex`):

| Significance | Concept | ID in the file |
|---|---|---|
| 500 | Applied computing, Electronic commerce | 10010405.10003550 |
| 300 | Applied computing, Economics | 10010405.10010455.10010460 |
| 300 | Information systems, Data mining | 10002951.10003227.10003351 |

**CHECK BEFORE SUBMISSION:** these IDs were entered from memory (the comment above the `CCSXML` block in `main.tex` says so). Look each concept up at https://dl.acm.org/ccs and replace the IDs and the exact concept strings with the ones the tool gives. Wrong IDs do not break the build but they print wrong metadata. They matter for camera-ready more than for review.

**Track:** Web Economics and Digital Society.

## 3. Items only the author can do

1. **GenAI disclosure.** Author decision (2026-10-25): no AI-use statement in the paper; the placeholder comment was removed. ACM's updated policy requires AI use in conducting the research to be described in the methods section; the author accepted that risk.
2. **Dual-submission confirmation.** Confirm in OpenReview that the paper is not under review elsewhere and that no overlapping version has been published. Check this against any other venue, workshop or preprint of the same material, including any journal version of the stablecoin or Korean-exchange work.
3. **OpenReview profiles and abstract registration.** Every author needs a complete OpenReview profile (institution, emails, DBLP or ORCID if asked) before submission, since profiles drive conflict-of-interest and reviewer assignment. The abstract registration step (due 2026-10-18 AoE according to `ABSTRACT_SUBMISSION.md`) has passed on the date of this pass. Check whether it was done; if not, check whether the form still accepts a full submission.
4. **The GitHub repository.** The repository holds the full paper, the code and the review notes, and the paper's text points to scripts that rebuild the data. If the repository is public, a reviewer or a search engine could find the paper and its authors. Consider making it private until decisions are out. The paper's text contains no repository link, and the anonymity scan of the rendered PDF finds no identifying string (see section 4).
5. Conflicts of interest and author ordering entered in OpenReview, and any required reviewer-volunteering or ethics fields.

## 4. Checks run in the final pass

| Check | Result |
|---|---|
| `uv run python -m www_paper.gate` | `gate_pass: 1` |
| Body pages at most 8, total at most 12 | 8 and 12 |
| Abstract at most 300 words (`uv run python -m www_paper.abstract_text`) | within the limit |
| Anonymity grep on `pdftotext paper/build/main.pdf -` for hex strings, `github`, `.json`, `.py`, `.md` | only DOIs and URLs in the references |
| Every empirical number is a `\Num...` macro | yes; the one literal that was found (721 hours, Appendix C) now has a macro |
| `uv run pytest -q -W error::DeprecationWarning` | 521 passed |
| All 12 pages rendered at 60 dpi | no clipped or overlapping content found; Figures 6 and 7 were enlarged because their labels were illegible |

See `docs/review/HKUSTDIAL_PRESUB_FINAL.md` for the review and `docs/review/draft_final.txt` for a text export of the submitted PDF.
