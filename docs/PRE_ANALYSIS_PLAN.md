# Pre-analysis plan (frozen)

**Frozen:** 2026-10-11, before any event other than the March 2023 anchor was measured. The SHA-256 of this file is pinned in `configs/plan_freeze.json`, and `tests/test_plan_freeze.py` fails if the file changes. Every later change goes in `docs/PRE_ANALYSIS_AMENDMENTS.md`, dated, with a reason, and marked as made either before or after the data it affects was seen.

The anchor (E2023-03-USDC-SVB) was measured before this plan was written. It is therefore **exploratory**, it is labelled as such in the paper, and it is excluded from every confirmatory count below.

## 1. Units of analysis

- **Independent episode:** a registry cluster whose PRIMARY event is ACCEPTED under rules R1–R4 (`src/www_events/registry.py`). Linked legs are reported descriptively and never counted.
- **Confirmatory in-sample set:** accepted primaries with start dates before 2024-01-01, excluding the anchor.
- **Out-of-sample set:** accepted primaries starting on or after 2024-01-01. They are run only after the in-sample results are committed, using the same code, and the commit SHA of each run is recorded.
- **Placebo / negative set:** registry `PLACEBO` entries and expected-negative entries, measured with identical code.

## 2. Primary dependent variables

These use the stablecoin's USD price where a USD leg exists. Otherwise the series is flagged `*_RELATIVE` and excluded from confirmatory tests.

| ID | Definition | Window contrast |
|---|---|---|
| DV1 | Median \|D\| over traded minutes, where D = 10⁴·log(S/peg) | event − control (event − baseline if the control is uncovered, flagged) |
| DV2 | Parity-anchored AR(1) half-life of D on 15-minute medians (min. 3 traded minutes per bin) | event window, descriptive |
| DV3 | Recovery time: minutes from the event-window extreme until the trailing 6-hour median \|D\| first falls below 25 bps. Computed forward from the extreme using trailing data only (no look-ahead). Right-censored at the end of the recovery window. | per event |
| DV4 | Median \|W\| of the within-venue triangle wedge, where all three legs exist | event − control |
| DV5 | Ratio of DV2 for D to the same half-life for W (15-minute bins) | event window |

## 3. Hypotheses and decision rules

- **H1 (stress raises fragmentation).** For each confirmatory event, DV1's 95% moving-block bootstrap interval excludes 0 (60-observation blocks, 1,000 draws, seed 20230310). P-values for the per-event H1 tests are Holm-adjusted across events. *H1 is supported in-sample* if at least two-thirds of confirmatory events satisfy it at Holm-adjusted 5%, **and** no placebo satisfies it. *H1 replicates out of sample* if a majority of out-of-sample events satisfy it. Every count is reported, including failures.
- **H2 (peg dislocation is more persistent than cross-quote wedges).** For each event with a triangle, compute DV5 > 1 (yes/no). Across independent clusters, report the count and the exact two-sided sign-test p-value. With fewer than six clusters, the sign test cannot reach 5% (for example, 3/3 gives p = 0.25), so H2 is then reported descriptively.
- **H3 (capacity).** Not testable until execution state has been validated and the capacity gate authorized. No proxy may be presented as a capacity test.

## 4. Cross-event aggregation

- Each event is estimated separately (estimate plus bootstrap standard error).
- Pooling uses DerSimonian–Laird random effects (`src/www_events/crossevent.py`). It is done **only within a mechanism group** with at least two independent clusters, and is always reported with τ², Q and I². A single overall pooled estimate across mechanisms is reported only as a secondary result, next to the per-mechanism results, never alone.
- Heterogeneity is a finding in its own right; it is not averaged away.

## 5. Inference details

- **Dependence:** moving-block bootstrap within each window (60-observation blocks), resampling each window independently.
- **Quote basis:** a USDT-quoted series enters confirmatory tests only once USDT/USD in the same window has passed a stability check: median \|USDT/USD dev\| < 10 bps on a USD venue. Otherwise it is relative-only.
- **Missing data:** windows with less than 50% of expected minutes present are reported but excluded from confirmatory tests. Gaps are never forward-filled.
- **Multiplicity:** Holm adjustment within each hypothesis family. DV2–DV5 are descriptive.

## 6. Alternative explanations reported alongside each event

- Market-wide volatility: BTC/USD 60-minute realized volatility, event vs control.
- Trading activity: the stablecoin leg's traded-minute share and volume.
- Venue disruption: missing-minute runs longer than 15 minutes.
- Quote-basis stress: USDT/USD deviation.
- Primary-market access: the redemption window per `src/www_capacity/redemption.py`, labelled as an assumption unless an issuer source exists.

These are reported as associations; no causal decomposition is claimed.

## 7. Robustness (pre-listed; all reported)

- R1 thresholds of 50 and 200 bps.
- 30- and 60-minute bins for DV2.
- Excluding the first and last 6 hours of the event window.
- An alternative USD venue where one is available.

## 8. Stopping and reporting

If fewer than three independent episodes qualify, the paper says so, gives the count, and frames the results as a descriptive multi-event comparison. Qualification rules are never relaxed to reach three without a dated amendment that explains why.
