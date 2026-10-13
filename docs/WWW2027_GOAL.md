# WWW 2027 submission goal tracker (durable; read first in every session)

**Target:** ACM Web Conference 2027, Research Track, *Web Economics and Digital Society*.

**Official requirements** (verified 2026-10-12, https://www2027.thewebconf.org/?p=296):
- Abstract due **2026-10-18 AoE**; full paper due **2026-10-25 AoE**. Results 2026-12-21; rebuttal 2026-12-21 to 31; notification 2027-01-04.
- Long paper: **8 pages of main text** + references + optional appendix, **≤ 12 pages total**. The first 8 pages must be self-contained. Short-paper fallback: 4 pages including everything.
- Template `\documentclass[sigconf, anonymous, review]{acmart}`; **double-blind review**.
- No dual submission. LLMs cannot be authors. Code and data release is encouraged after review.

**Success condition:** an 8-page, anonymous, compiling, reproducible, WWW-relevant paper with verified evidence and bounded claims. If that is unattainable, the deliverable is an honest audited manuscript plus a precise blocker list.

**Gates:**
- 2026-10-16: GO / NARROW / PIVOT verdict.
- 2026-10-18: abstract ready for the human author to submit (no external submission without approval).
- 2026-10-23: data, analyses, figures and narrative frozen.
- 2026-10-24/25: PDF validation, independent review, handoff.

**Rules:** no force-push and no auto-merge. Frozen plan files are never edited; later analyses are dated exploratory extensions. Exploratory events stay exploratory. No credentials are logged or committed. Any new provider, purchase or bulk source needs explicit approval.

## Status snapshot

As of 2026-10-12 15:40 ET: branch `g0/www2027-goal`, based on `c6b/capacity-robustness` @ `8382da5`; main @ `d8045b9`; PR #5 open. 194 tests pass.

## Blocking issues

| # | Issue | Severity | Owner | Next action |
|---|---|---|---|---|
| B1 | **Anonymity.** The repo `nl2992/www-2027-stablecoin-arc` is public, its commits carry the author's name, and it contains the draft paper. A reviewer searching the title or text could deanonymise the submission. | Blocking for submission | User | Decide: make the repo private again until after review, or keep it public but never cite it, and use an anonymous artifact link (for example anonymous.4open.science) in the paper |
| B2 | No crisis-period CEX L2 depth (paid only; declined) | Scope limit | — | Claims stay on-chain-only. Never call results CEX–DEX capacity. |
| B3 | No accepted confirmatory in-sample event, so H1 cannot be tested | Scope limit | — | The paper stays descriptive (decision D10) |
| B4 | ~~PDF not compiled~~ Resolved: compiles at 7 pages | — | — | — |

## Prioritized tasks

Status: `[ ]` open, `[~]` in progress, `[x]` done (evidence required).

### Phase A/B — positioning and fatal-flaw audit
- [x] **T1.** Verify the official CFP requirements. *Evidence:* this file's header (source URL).
- [x] **T2.** Fatal-flaws audit and adversarial reviewer dossier v1. *Evidence:* `docs/review/FATAL_FLAWS_AUDIT.md`. *Acceptance:* each flaw has a severity, evidence path and remediation. Done: 12 findings, 2 BLOCKING (F1 WWW scope, F2 anonymity).
- [x] **T3.** Compile the PDF with tectonic; record page count, warnings and anonymity check. *Evidence:* `uv run python -m www_paper.gate` (fixed harness, `src/www_paper/gate.py`; PDF in the git-ignored `paper/build/`). Result: 7 pages with references starting on page 7; anonymity clean; 63 overfull boxes; no "Web" on page 1. *Acceptance:* compiles; main text ≤ 8 pages, or the overage is measured.
- [ ] **T4.** Positioning decision A/B/C/D with alternatives rejected. *Evidence:* `docs/review/POSITIONING.md`. *Depends on:* T2, T5.
- [ ] **T5.** Literature verification and closest-work comparison: crypto arbitrage, stablecoin pegs, runs, AMM microstructure, CEX–DEX. *Evidence:* `docs/review/RELATED_WORK_MATRIX.md` with verified URLs. *Acceptance:* ≥ 8 closest papers verified, each with a stated difference.
- [ ] **T6.** Re-audit data integrity: manifests and checksums, block hashes, the May 2023 Binance.US common premium, solver edge cases. *Evidence:* `docs/review/DATA_AUDIT.md`, tests.

- [x] **T3b.** Adopt the karpathy/autoresearch loop pattern (user request, 2026-10-12): fixed gate, editable files, keep/discard through git, bounded iterations, and no empirical metric as a target. *Evidence:* `autoresearch/program.md`, `src/www_paper/gate.py`, `tests/test_gate.py`.

### Phase C — core mechanism experiment (exploratory extension, dated)
- [ ] **T7.** Event-aligned panel per on-chain event (SVB, June 2023, UST) joining CEX D, W, pool composition, A(δ) and R(δ) at block timestamps. *Evidence:* `reports/c7/aligned_*.json` and a figure. *Acceptance:* no future state joined to past timestamps (as-of join, tested).
- [ ] **T8.** Descriptive lead–lag: does the capacity change precede, coincide with or follow D crossing R1, plus matched-control comparison. *Evidence:* `reports/c7/leadlag.json`. *Acceptance:* uses past-only data; reported per event with uncertainty; June 2023 counterexample included.
- [ ] **T9.** Sensitivity: price reference (par vs observed), DAI co-depeg, 6 h vs 1 h sampling, δ ∈ {10, 50, 100}. *Partial evidence:* PR #5.

### Phase D — baselines and robustness
- [ ] **T10.** Decide predictive versus descriptive. With 2–3 on-chain events and 4 accepted clusters, prediction at event level is not identifiable, so the expected outcome is to decline it explicitly and give the reason. *Evidence:* a section in `POSITIONING.md`.
- [ ] **T11.** Placebo dates for capacity (matched calm windows), alternative USD venue, data-gap checks. *Evidence:* reports.

### Phase E — paper
- [ ] **T12.** First-page rewrite (Web relevance, problem, difficulty, findings, contribution, limits) using the observed example. *Depends on:* T4, T8.
- [ ] **T13.** Figures: motivation (D vs W), measurement-system diagram, stress-vs-control capacity plot. *Evidence:* vector PDFs, generated.
- [ ] **T14.** Fit to 8 pages; move details to the appendix without hiding central results.

### Phase F — review
- [ ] **T15.** Three simulated reviewers (novelty; measurement/on-chain; WWW scope and compliance) with blocking, major and minor findings. *Evidence:* `docs/review/REVIEW_ROUND_*.md`.
- [ ] **T16.** Fix blocking findings, then re-review.
- [ ] **T17.** Abstract for human submission by 10-18. *Evidence:* `docs/review/ABSTRACT_SUBMISSION.md`.

### Pivot (user decision 2026-10-12): "Which dollar broke?"
- [x] **P1.** Rescue search R1–R6, logged in `docs/review/RESCUE_SEARCH.md` (PR #7).
- [x] **P2.** Decomposition (`src/www_rescue/decompose.py`) and the Binance.US natural experiment, with USDT, BTC and USDC plus the triangle (`src/www_rescue/platform_dollar.py`). GBP and EUR cases in `src/www_rescue/fiat_rail.py`.
- [x] **P3.** Paper rewritten around the new framing. Generated macros and tables: `www_paper.rescue_macros`. Figure: `which_dollar.pdf`. Token-side detail moved to the appendix. Gate passes: main body ends with references on page 5; 9 pages in total; page 1 mentions the Web.
- [ ] **P4.** Simulated reviewers on the new draft (T15); decide whether to use the remaining ~3 body pages (for example an on-chain view, or more ledger cases if any exist in free data).

## Next executable step

T5: verify the closest literature (CurveMetrics arXiv:2306.10612, Liu-Makarov-Schoar NBER w31160, non-atomic arbitrage arXiv:2401.01622) and write `docs/review/RELATED_WORK_MATRIX.md`; then T6: audit the degenerate DV5 values (F8). The user must decide B1 (anonymity).

## Iteration log

| Date (ET) | Branch @ commit | Task | Outcome |
|---|---|---|---|
| 2026-10-12 15:40 | g0/www2027-goal | T1 | CFP verified; blocking anonymity issue B1 raised |
| 2026-10-12 | g2/which-dollar | P1–P3 | Pivot: rescue search, decomposition, paper rewrite; 206 tests pass |
| 2026-10-12 | g0/www2027-goal | T2, T3, T3b | Audit v1 (12 findings); gate passes (198 tests, 7 pages); autoresearch pattern adapted |
