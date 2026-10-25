# Current state: submission freeze for WWW 2027 (draft v15)

**Updated:** 2026-10-24. **Workspace:** `WWW Paper`; origin `git@github.com:nl2992/www-2027-stablecoin-arc.git`.
**Branch:** `autoresearch/stable`, based on the work through commit `3a8542a` ("Integrate the pre-registered currency-wedge panel as a main result ... draft v15").
**Deadline:** WWW 2027 full paper due **25 October 2026 AoE**, strict. Results 15 December, rebuttal 15 to 20 December, notification 4 January 2027 (`docs/review/WWW2027_REQUIREMENTS.md`).
**Tests:** the offline suite runs with `uv run pytest -q -W error::DeprecationWarning` passes 497 tests, all offline (2026-10-24).

The previous version of this file (an audit dated 2026-10-11 under Implementation Specification v3) is superseded; it is in the git history. Evidence types below: **executed** (a report from real data), **locked** (run once, log committed), **pre-registered**.

## 1. The paper

"Same Name, Different Unit: Identifying Source-Specific Units in Web Price Fusion." Question: can a source's unit offset be identified from public prices, and when does correcting for it help a fused price? Method: shared cross-item offset, a netted stablecoin anchor, IV/GMM, simulation, and a causal unit-aware fuser (`README.md` has the overview).

Form: `paper/main.tex`, `[sigconf,review,anonymous]{acmart}`, 8 body pages and 12 in total, anonymous, no repository links. The gate (`uv run python -m www_paper.gate`) enforces page limits, undefined references, document class and an anonymity scan.

## 2. Status register

| Component | Status | Evidence |
|---|---|---|
| Unit probe, UNIT-TD benchmark | **Executed; locked test run** (`724455b`: 0.846 vs 0.847 for the median) | `reports/unit_td/`, `autoresearch/final_test_724455b.log` |
| Anchor and external anchor (Bitfinex, Binance.US) | **Executed.** Netted slope 0.97 (0.94 to 1.00) | `reports/unit_td/anchor*.json` |
| Anchored-test theory: GMM, simulation, 360-cell robustness grid | **Executed** | `reports/theory/` |
| FUSE | **Locked** (`914b3cb`); median hard to beat | `autoresearch/final_fuse_914b3cb.log` |
| STABLE | **Locked** (`ca38772`); wins USDC, loses TUSD, FDUSD and the placebo | `autoresearch/final_stable_ca38772.log` |
| Q1 | **Pre-registered; win** (3 events, 981 hours; beats B0, B2, B3 and narrowly the USD-only median) | `reports/q1/` |
| Q2 | **Pre-registered; tie**, with a disclosed calibration change (`55b50ed`) | `reports/q2/`, `docs/review/Q2_CALIBRATION_CHANGE.md` |
| Currency-wedge panel | **Pre-registered; P1 narrow fail, P2 pass.** Pooled IV 0.978 (0.962 to 0.989); 8 of 8 currencies in range | `reports/panel/` |
| Kimchi application | **Pre-registered; executed** (appendix) | `reports/kimchi/results.json` |
| Calm-year noise bounds, monitor, detector evaluation and sweep | **Executed** (detector rule pre-registered) | `reports/unit_td/noise_bounds.json`, `reports/rescue/` |
| Oracle audit pilot (USDC 2023) | **Executed** (D13, one episode) | `reports/audit/usdc_2023_pilot.json` |
| Event study, on-chain capacity (earlier phase) | **Executed** at candle level and on swap-validated pools; no capacity claim for CEX | `reports/events/`, `reports/c6/` |
| Resource-track release | Built; derived series only | `resource/` |
| Reproduction guide | Written from the code; **not re-run from an empty disk** | `REPRODUCE.md` |

## 3. Data

All downloads were user-authorized (D1 to D19) and are free public sources. The manifest `reports/events/acquisition_manifest.json` holds 2,179 VERIFIED records and 76 NOT_AVAILABLE. Raw files are git-ignored. No paid data, no CEX crisis-day order books, and no historical DEX state beyond the 84 read-only calls of D5. Panels are cached under `data/derived/` (git-ignored).

## 4. Open items

| # | Item | Owner | Note |
|---|---|---|---|
| 1 | **GenAI disclosure** | Author | Wording and place undecided; an anonymous version cannot carry a credits section. Placeholder comment in `paper/main.tex`. |
| 2 | **CCS concept IDs** | Author | Entered from memory; verify at https://dl.acm.org/ccs. |
| 3 | **Submission** | Author | OpenReview long-paper submission, profiles, dual-submission confirmation, check that the 18 October abstract registered. The assistant never submits. |
| 4 | Repository visibility | Author | Was public with the author's name on 2026-10-12; decide before submission (`docs/WWW2027_GOAL.md`, B1). |
| 5 | Overfull boxes (about 58) | Optional | Advisory metric in the gate. |
| 6 | Post-review release | Author | Archive `resource/` with a DOI for the Artifacts badge. |
| 7 | Reproduction from an empty disk | Optional | Two inputs lack scripts (D12 call list, D15 download), see `REPRODUCE.md`. |

## 5. Pre-registration ledger

Written before the result existed; none is re-run with changes.

| Study | Pre-registration | Outcome |
|---|---|---|
| Event study | `docs/PRE_ANALYSIS_PLAN.md` (hash-pinned) | descriptive |
| Detector evaluation | `docs/review/DETECTOR_PREREG.md` | P2 passes, P1 split, P3 and P4 fail |
| UNIT-TD / FUSE / STABLE | `autoresearch/program_{unit_td,fuse,stable}.md` | locked tests above |
| Kimchi | `docs/kimchi/PREREG.md` | appendix |
| Q1 | `autoresearch/program_q1.md` | win |
| Q2 | `autoresearch/program_q2.md` | tie |
| Panel | `autoresearch/program_panel.md` | P1 narrow fail, P2 pass |

## 6. Decision trail

`docs/status/DECISION_REGISTER.md`: D1 (paid data declined) through D19 (currency-wedge panel data, 2026-10-24). Scope: the capacity framing is retired; claims are on units, identification and fusion. D10 fixed the descriptive, pre-registered framing for the event study; later decisions are data authorizations for the new studies.

## 7. Next actions

1. The author resolves open items 1 to 4.
2. Run `uv run python -m www_paper.gate` on the final commit and read the PDF once end to end.
3. The author submits on OpenReview by 25 October 2026 AoE.
