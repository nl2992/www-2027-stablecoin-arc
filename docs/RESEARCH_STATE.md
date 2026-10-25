# Research state (durable; read at the start of every iteration)

Last updated 2026-10-24 (paper draft v15, branch `autoresearch/stable`). Cross-check against `git log` and the code before acting. The loop is paused for the submission; see `docs/status/CURRENT_STATE.md` for the snapshot and `docs/status/DECISION_REGISTER.md` (D1 to D19) for the decision trail.

## Objective

**Paper:** "Same Name, Different Unit: Identifying Source-Specific Units in Web Price Fusion" (`paper/main.tex`). WWW 2027, Research Track, Web Economics and Digital Society; double-blind; **full paper due 25 October 2026 AoE** (abstract was due 18 October). 8 body pages, 12 in total.

**Question:** can the unit offset of a web source (a crypto exchange's ledger "dollar") be identified from public prices, and when does correcting for it improve a fused price?

**Earlier objective (superseded):** whether executable arbitrage-restoration capacity explains stablecoin fragmentation. It stopped for lack of crisis-day order-book and archive-state data (paid, declined) and became a descriptive multi-event study (D10), then this paper. The capacity code and reports remain, with no capacity claim.

**Rules:** commits, merges and PRs carry no AI/tool attribution. Never force-push. Raw data stays out of Git; free public sources only (D1). Credentials live only in the git-ignored `.env`. Locked and pre-registered results are never re-run with changes. NumPy is capped below 2.5 (pandas 2.3 deprecation); run the suite with `-W error::DeprecationWarning`.

## Method

Shared offset across unrelated items on a source, plus a stablecoin anchor netted against an outside price (Kraken USDT/USD). Slope near 1 means a unit shift; near 0 means demand. IV/GMM with HAC and a Hansen J check, plus a simulation of size and power (`www_theory`). Fusion: a causal, anonymised fuser that removes estimated offsets, benchmarked on frozen splits (`www_auto`, `www_fuse`, `www_stable`).

## Findings (all numbers are macros in `paper/generated/`, from `reports/`)

| Result | Outcome | Evidence |
|---|---|---|
| Bitfinex anchor, 2018-11 to 2019-05, netted | slope 0.97 (0.94 to 1.00), raw 0.71; 360-cell robustness grid, GMM estimates from 0.970 (median 0.984) | `reports/unit_td/anchor_external.json`, `reports/theory/` |
| Binance.US 2023 | slope 1.00, mechanical; two-stablecoin test rejects | `reports/unit_td/anchor.json`, `reports/theory/gmm_applied.json` |
| Held-out assets (UNIT-TD, locked 724455b) | 0.846 vs 0.847 for the cross-asset median (tie); contribution is the unit model | `autoresearch/final_test_724455b.log`, `reports/unit_td/posthoc.json` |
| FUSE (locked 914b3cb) | median hard to beat: wins Bitfinex T1 (0.93), loses Binance.US T2 (1.50) | `autoresearch/final_fuse_914b3cb.log` |
| STABLE (locked ca38772) | wins USDC X1 (0.72); loses TUSD X2, FDUSD X3 and the calm placebo X4 | `autoresearch/final_stable_ca38772.log` |
| Calm years | offsets inside the round-trip fee band; monitor has fewer false alarms than a price-gap alarm | `reports/unit_td/noise_bounds.json`, `reports/rescue/` |
| Kimchi (pre-registered) | common component in every window; USDT/KRW anchor only from 2023-12, biased toward 1 (appendix) | `reports/kimchi/results.json` |

## Pre-registrations and outcomes

| Study | Registered | Outcome |
|---|---|---|
| Event study plan | `docs/PRE_ANALYSIS_PLAN.md`, hash in `configs/plan_freeze.json` | candle-level, descriptive; three accepted clusters, two confirmatory |
| Detector evaluation | `docs/review/DETECTOR_PREREG.md` (2026-10-19) | P2 passes, P1 split, P3 and P4 fail; not falsified |
| UNIT-TD, FUSE, STABLE | `autoresearch/program_unit_td.md`, `program_fuse.md`, `program_stable.md` | locked tests as above |
| Kimchi | `docs/kimchi/PREREG.md` (before any price download, D17) | reported in the appendix |
| **Q1** | `autoresearch/program_q1.md` (`7e45e0a`, 2026-10-22; D18) | **Win.** Gate kept 3 of 5 events (981 hours). Frozen fuser beats B0 (-1.08 [-1.36, -0.83]), B2 and B3, and narrowly beats the USD-only median (-0.07 [-0.11, -0.03]). Calm placebo ok. |
| **Q2** | `autoresearch/program_q2.md` (`2189195`, 2026-10-23) | **Tie.** 6 events scored; pooled P median lead 72 h with 4 misses vs S1 37 h (3 misses) and S2 72 h (4 misses); bootstrap intervals include 0. Calibration rule corrected once after a scoring run (`55b50ed`); both versions tie (`docs/review/Q2_CALIBRATION_CHANGE.md`). |
| **Panel** | `autoresearch/program_panel.md` (`bfb6205`, 2026-10-24; D19) | **P1 narrow fail:** pooled IV 0.978 (0.962 to 0.989) excludes 0 and excludes 1. **P2 pass:** 8 of 8 currencies in [0.8, 1.2]. Falsification not triggered. P3: one venue-month at 0.30. |

## Open items

1. **GenAI disclosure.** Wording and place are an author decision (a credits section is not allowed in the anonymous version). A placeholder comment sits in `paper/main.tex`; nothing is written.
2. **CCS concept IDs** were entered from memory; verify at https://dl.acm.org/ccs.
3. **Submission.** Only the human author submits on OpenReview (profiles, dual-submission confirmation). Authors' list is frozen. Check that the 18 October abstract was accepted.
4. **Anonymity (B1).** As of 2026-10-12 (`docs/WWW2027_GOAL.md`) the GitHub repository was public and carried the author's name. Check its visibility and decide whether to make it private until after review. The gate scans the paper only.
5. **Layout.** The gate counts about 58 overfull boxes (advisory only).
6. After review: code and data release (`resource/` package); an archival repository with a DOI is needed for the Artifacts badge.
7. `REPRODUCE.md` has not been re-run from an empty disk. Two inputs have no script: the D12 hourly-candle call list and the D15 Kraken download (documented there).

## Timeline since 2026-10-19

| Date | Work | Commits (head) |
|---|---|---|
| 10-19 | continuous detector pre-registration and evaluation; fiat-rail labels (D1 amendment); D11 | `7459c5a` to `2e1b18d` |
| 10-20 | hourly candles (D12, D14); UNIT-TD harness, 12-iteration loop, locked test of `724455b`; oracle pilot (D13); Kraken anchor (D15); new framing and abstract v3 | `92d2f89` to `c211c25` |
| 10-21 | FUSE round (24 runs, locked `914b3cb`); STABLE pre-registration and data (D16); STABLE round (15 runs, locked `ca38772`) | `78d059e` to `6d6dc33` |
| 10-22 | Kimchi (D17); theory, simulation and robustness grid; Q1 pre-registration and data (D18) | `7c39655` to `7e45e0a` |
| 10-23 | Q1 locked run; Q2 pre-registration, labels, calibration, scoring and the calibration correction; v9 to v13 text, figures and WWW compliance | `93d6f58` to `7127325` |
| 10-24 | panel pre-registration (D19), download, classification, estimation, macros, tests; panel integrated as a main result; readability passes; draft v15 | `bfb6205` to `3a8542a` |

## Where things are

- Reproduction guide: `REPRODUCE.md`. Overview and repository map: `README.md`.
- Evidence matrix and requirements audit: `docs/WWW2027_EVIDENCE_MATRIX.md`, `docs/review/WWW2027_REQUIREMENTS.md`. Goal tracker with deadlines: `docs/WWW2027_GOAL.md`.
- Review history: `docs/review/` (simulated reviews v3 to v7, polish and readability flags, HKUSTDial evaluations, draft text v3 to v15).
- Earlier component history (C0 to C6, E1 to E4, P1 and P2, M1 to M4), with the original status tables, is in the git history of this file (`git log -p docs/RESEARCH_STATE.md`) and in `docs/c*_*.md`, `docs/e1_event_registry.md` and `docs/review_packet_post_c2.md`.
