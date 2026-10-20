# Fatal-flaws audit and adversarial reviewer dossier, v1 (2026-10-12)

**Scope:** the draft at `paper/main.tex` as of branch `g0/www2027-goal`, built with `uv run python -m www_paper.gate`.

**Build state:** compiles; 7 pages in total, with references starting on page 7; anonymity scan clean; 198 tests pass; 63 overfull boxes; the first page never mentions "Web".

**Severity:**
- **BLOCKING**: rejection-level if unaddressed.
- **MAJOR**: likely to draw a low score.
- **MINOR**: polish.

## 1. Four-axis evaluation (WWW reviewer lens)

| Axis | Current state | Finance novelty | Web relevance |
|---|---|---|---|
| Novel problem | "Stablecoin fragmentation in stress" is well studied (L1–L5), and a comparative event study of UST and SVB already exists. What is less studied: *executable* (quantity-denominated) capacity, and the dollar-price-versus-cross-quote decomposition measured across several events under one rule set. | Low–moderate | Weak as written. It needs a public-Web-data measurement angle. |
| Novel method | A pre-registered event protocol (rare in this literature); exact integer replay of StableSwap state from public archives; quantity solvers A_b(δ) and R_b(δ). CurveMetrics (arXiv:2306.10612) already turns Curve composition into depeg signals, so composition-based detection is *not* new. | Moderate (the protocol), low (the detection) | Moderate: open, reproducible measurement from public APIs and chain state |
| Nice story | Currently a list ("we built X, measured Y") with two exploratory events and two issuer-specific OOS events. | — | — |
| Nice presentation | Clean, macro-generated numbers. Dense tables, no motivating figure on page 1, no system diagram, 63 overfull boxes. | — | — |

## 2. Findings

| ID | Sev. | Finding | Evidence | Remediation |
|---|---|---|---|---|
| F1 | BLOCKING | **WWW scope.** Page 1 never states why this is a Web problem. A Web Economics reviewer will read it as a finance paper. | `run.log` gives `first_page_mentions_web: False` | Frame stablecoins as Web-native payment infrastructure whose prices and liquidity are observable only through public exchange APIs and public chain state. The contribution is an open, reproducible measurement methodology over public Web data. Put this on page 1 (T12). |
| F2 | BLOCKING | **Anonymity.** The public GitHub repo carries the author's name and the same title and text. | `WWW2027_GOAL.md` B1 | User decision: make it private during review, and/or retitle; use an anonymised artifact link. |
| F3 | MAJOR | **Headline finding may look expected.** A small within-venue triangle wedge is ordinary single-exchange no-arbitrage; that BTC was "worth more than $26,000 in USDC terms" during SVB was widely reported. A reviewer will say: of course the cross rate held, the token's price moved. | M3; press reports (Kraken, March 2023) | Turn the finding into a measurement of **unit-of-account pass-through**: how fast and how completely the stablecoin's dislocation propagated into every pair quoted in it, and where it did not (the cross-venue wedge). Report the wedge as a validated null with its precision, not as a discovery. |
| F4 | MAJOR | **Too few events for inference.** 4 accepted clusters: 2 exploratory, 2 OOS, and both OOS are issuer-specific. Mechanism heterogeneity cannot be separated from event idiosyncrasy. | M1 | State explicitly: descriptive, no predictive or causal claims (T10). Event-level uncertainty only. Present it as a case-study panel with a common protocol. |
| F5 | MAJOR | **On-chain absorption contraction is close to mechanical.** For StableSwap with fixed A and fee, par-relative absorption is a monotone function of the pool share of the stressed coin. "Capacity contracted in stress" amounts to "the pool became imbalanced", which practitioners and CurveMetrics already track. | `tests/test_onchain_capacity.py` (skewed pool absorbs less); I3; L4 | Claim measurement value, not discovery: the conversion from composition into executable dollar quantities at a tolerance, exact and swap-validated. Show the mapping is strongly non-linear (for example, a 1.5% USDT share leaves zero absorption). Cite CurveMetrics; make no leading-indicator novelty claim. |
| F6 | MAJOR | **Valuation sensitivity.** SVB USDC→DAI event absorption is 154.0M at par but 0 at observed prices. | M8 (PR #5) | Report both in the main text and define what each answers: capacity to restore par vs capacity at market prices. |
| F7 | MAJOR | **Stale or contradictory text.** Contribution (4) says data limits "prevent historical estimation", yet historical on-chain capacity is now estimated. The abstract says absorption "contracted in every stress episode examined", but June 2023 (not a stress event under R1) also contracted. | `paper/main.tex` §1, abstract | Rewrite both. Present June 2023 as an explicit counterexample: contraction without a depeg. |
| F8 | MAJOR | **Degenerate DV5 values:** TUSD half-life ratio 39,414.4; June 2023 3,420.6. | `cross_event_results.md` | Audit the estimator; report as censored or undefined rather than as numbers (T6). |
| F9 | MAJOR | **Researcher degrees of freedom.** A2 and A3 (USD venue validity and priority) were adopted after seeing data. | `docs/PRE_ANALYSIS_AMENDMENTS.md` | Already logged. Also show all-venue results side by side in the appendix and say so in the main text. |
| F10 | MINOR | **Missing closest work:** Cintra & Holloway 2023 (CurveMetrics); Liu, Makarov & Schoar (Terra run); non-atomic CEX–DEX arbitrage (arXiv:2401.01622). | `paper/references.bib` | Add after verification (T5). |
| F11 | MINOR | **Template.** The tectonic bundle ships acmart v1.83 (2022); the reference block reads "Conference'17". | PDF metadata | Set `\acmConference` for WWW '27; re-check with the current acmart before submission. |
| F12 | MINOR | **Layout.** 63 overfull boxes; no figure on page 1 or 2. | `run.log` | Phase E. One page of headroom remains (7 of 8 body pages used). |

## 3. Adversarial reviewer dossier (what each reviewer will write)

- **R-Novelty (finance/crypto).** "The SVB and Terra depegs are thoroughly documented. The cross-rate result is a no-arbitrage identity. On-chain pool imbalance as a depeg signal is known (CurveMetrics). With four events, nothing generalises." *Defence:* the protocol and its rejection discipline (negative, placebo and OOS cases under the same rules); quantity-denominated capacity rather than signals; honest nulls.
- **R-Measurement (systems/on-chain).** "Is the replay exact? Which pools were excluded and why? Six-hour sampling misses the dynamics. Par valuation is arbitrary." *Defence:* `get_dy` difference of 0 and swap cross-checks (M6); the inclusion rule in `docs/c6_onchain_capacity.md`; hourly event sampling and observed-price valuation (PR #5).
- **R-Scope (WWW).** "Why the Web Conference?" This is currently unanswered, which is F1.

## 4. Provisional positioning (for T4; final by the 10-16 gate)

**Preliminary verdict: NARROW.** Story **D/B-narrow**: *an open, pre-registered measurement methodology for stablecoin dislocation and executable on-chain capacity from public Web data, applied to every qualifying episode in 2020–2026.*

- Story A (peg vs cross-quote) is folded in as the descriptive anchor.
- Story C (combined causal mechanism) is rejected, because 4 events cannot support mechanism claims.
- Lead–lag (T8) is kept only as description, given CurveMetrics.
