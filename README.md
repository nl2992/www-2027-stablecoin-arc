# Same Name, Different Unit: Identifying Source-Specific Units in Web Price Fusion

Research workspace for a WWW 2027 submission (Research Track, Web Economics and Digital Society; double-blind; full paper due 25 October 2026 AoE). The manuscript is `paper/main.tex` (ACM `acmart`, `sigconf,review,anonymous`; draft v15; 8 body pages, 12 in total). Every empirical number in it is a macro generated from a committed report or log.

## The question

Price aggregators, indexes and oracles fuse prices from many web sources and assume every source quotes the same unit. A crypto exchange's "dollar" is a balance in its own ledger, and it can lose value when the exchange's banking breaks down. A fuser then reads a change in the unit as a change in price. Can the unit offset of a source be identified from public prices alone, and when does correcting for it improve a fused price?

## The method

- **Shared offset.** If a source's unit shifts, every item on that source moves by the same amount, so the part of the price gaps that unrelated items share (BTC, ETH, altcoins) measures the source's offset.
- **Unit anchor.** Shared movement could also be demand for all of a source's items. A stablecoin traded on the source (USDT/USD), netted against its price on an outside venue (Kraken), is a quote of the unit itself. The slope of the netted anchor on the offset is about 1 for a unit shift and about 0 for demand. The estimator is IV/GMM with a Hansen J check; a simulation gives its size and power.
- **Fusion.** A causal, anonymised fuser removes estimated unit offsets before weighting. It is benchmarked against the plain median, volume weighting, CRH and GTM on frozen splits.

## Main results

| Finding | Result | Report |
|---|---|---|
| Bitfinex 2018-11 to 2019-05, anchor netted with Kraken USDT | slope 0.97 (95% interval 0.94 to 1.00), up from 0.71 raw | `reports/unit_td/anchor_external.json`, `reports/theory/` |
| Binance.US 2023 | slope 1.00, close to mechanical; the two-stablecoin version rejected | `reports/unit_td/anchor.json`, `reports/theory/gmm_applied.json` |
| **Currency-wedge panel (pre-registered)**: 8 units on 3 venues | pooled IV slope 0.978 (0.962 to 0.989), per-currency 0.91 to 0.99. **P1 narrow fail** (interval excludes 0, lies just below 1); **P2 pass** (8 of 8 in [0.8, 1.2]); falsification not triggered | `reports/panel/results.json` |
| Held-out assets (UNIT-TD, locked) | score 0.846 against 0.847 for the cross-asset median; the benefit is the unit model and its validation | `autoresearch/final_test_724455b.log`, `reports/unit_td/posthoc.json` |
| Fusion benchmarks (FUSE, STABLE, locked) | a plain median is hard to beat; the final fuser wins the USDC run (0.72 of the median's error) and loses on TUSD, FDUSD and the calm placebo | `autoresearch/final_*.log` |
| **Q1 (pre-registered) win** | on 981 hours of 3 USDT events where most volume shared a depegged stablecoin, the frozen fuser beat the median, stablecoin conversion and CRH, and narrowly beat a median of dollar-quoted markets | `reports/q1/` |
| **Q2 (pre-registered) tie** | pooled detection of unit shifts tied the single-pair rules. The calibration rule was corrected once after a scoring run and both versions tie (disclosed) | `reports/q2/`, `docs/review/Q2_CALIBRATION_CHANGE.md` |
| Calm years and monitor | calm-year offsets sit inside the round-trip fee band; a fixed-rule monitor raised fewer false alarms per venue-year than a price-gap alarm at the same recall | `reports/unit_td/noise_bounds.json`, `reports/rescue/` |
| Kimchi premium | Upbit gaps for BTC, ETH and XRP move together in every window; the USDT/KRW anchor exists only from December 2023 and its slope is biased toward one by common FX noise (appendix only) | `reports/kimchi/results.json` |

Limits are stated in the paper: the Bitfinex headline rests on one stress episode with few month-blocks, the Binance.US anchor is mechanical, the panel's stress classification is uninformative, and the Q1 events are all USDT.

## Pre-registrations and locks

Each study below was written down, and its splits or thresholds fixed, before the result existed. Locked tests were run once. `REPRODUCE.md` section 9 lists the commits, unlock files and logs.

| Study | Pre-registration |
|---|---|
| Event study | `docs/PRE_ANALYSIS_PLAN.md`, hash-pinned in `configs/plan_freeze.json` |
| Detector evaluation | `docs/review/DETECTOR_PREREG.md` |
| UNIT-TD, FUSE, STABLE | `autoresearch/program_unit_td.md`, `program_fuse.md`, `program_stable.md` |
| Kimchi application | `docs/kimchi/PREREG.md` |
| Q1, Q2, panel | `autoresearch/program_q1.md`, `program_q2.md`, `program_panel.md` |

## Reproduce

[`REPRODUCE.md`](REPRODUCE.md) is an ordered guide from an empty checkout to the PDF: environment, data acquisition by decision ID (D1 to D19), each analysis in dependency order, macros and figures, and the gate. In short:

```sh
uv sync --group dev
uv run pytest -q -W error::DeprecationWarning
uv run python -m www_paper.gate        # builds paper/build/main.pdf (needs tectonic) and checks submission compliance
```

## Repository map

| Path | Contents |
|---|---|
| `paper/` | manuscript (`main.tex`), `references.bib`, generated macros, tables and figures (`generated/`, `figures/`); see `paper/README.md` |
| `paper_frl/` | short companion letter on Bitfinex's ledger dollar and Tether discounts |
| `src/www_auto` | UNIT-TD benchmark: panel, fixed harness, frozen estimator, probe, anchor and anchor_external, noise bounds, post-hoc and robust evaluation, truth-discovery baselines |
| `src/www_theory` | anchored GMM, simulation study, robustness grid |
| `src/www_fuse`, `src/www_stable` | FUSE and STABLE fusion rounds: panels, harnesses, baselines, fusers |
| `src/www_q1`, `src/www_q2` | the Q1 gate and locked run (frozen fuser `ca38772`) and the Q2 detectors |
| `src/www_panel` | pre-registered currency-wedge panel: download, classify, estimate |
| `src/www_kimchi` | Upbit/Bithumb/FRED download and the Kimchi analysis |
| `src/www_rescue` | ledger-side studies: platform dollar, decomposition, fiat-rail cuts, index repair, monitor, detector evaluation and sweep |
| `src/www_events`, `src/www_c0` to `www_c3`, `src/www_capacity`, `src/www_audit` | earlier event study: acquisition, event protocol, audited panel, order-book replay, on-chain capacity, oracle pilot |
| `src/www_resource` | derived-series release for the Resource track (`resource/`) |
| `src/www_paper` | macros, figures and the submission gate |
| `autoresearch/` | pre-registrations (`program_*.md`), loop logs and the locked-test logs |
| `configs/` | acquisition plans, event registry, frozen plan hash, fee schedule, fiat-rail labels |
| `reports/` | committed analysis outputs (JSON), the evidence behind every macro |
| `docs/` | `status/` (decision register, current state), `review/` (reviews, novelty checks, pre-registrations), `theory/`, `kimchi/`, `RESEARCH_STATE.md` |
| `tests/` | offline, deterministic suite (including macro-freshness and figure-reproducibility checks) |
| `data/` | git-ignored: raw downloads, derived panels, external samples |

Other top-level notes: `DATA_DICTIONARY.md`, `SOURCE_INVENTORY.md`, `CEX_L2_SOURCE_AUDIT.md`.

## Data and licences

- Raw data are never committed. `data/raw/`, `data/derived/` and `data/external/` are git-ignored; only manifests (names, sizes, URLs, SHA-256) are in Git (`reports/events/acquisition_manifest.json`).
- Only free public sources are used (decision D1: paid data is declined): Binance and Binance.US public archives, Bitstamp, Bitfinex and Coinbase public candle endpoints, Kraken's free OHLCVT bundle, Upbit and Bithumb public candles, the FRED KRW/USD series, and Tardis free first-of-month samples. Each provider's terms apply, and none of the raw files is redistributed.
- Keys (a FRED key, an optional archive-node URL) live only in a git-ignored `.env` and are never printed, logged or committed.
- The Resource-track release (`resource/`) contains derived series only; see `resource/TERMS.md` and `resource/DATASHEET.md`.

## Project history

The repository began as a study of whether executable arbitrage-restoration capacity explains the persistence of stablecoin price fragmentation (USDC, March 2023). That plan stopped at the data: crisis-day order-book data are paid, and historical on-chain state needs an archive key. It became a descriptive multi-event study (decision D10), and then, after the unit-offset finding, the present paper on source-specific units in price fusion. The capacity work (`src/www_c0` to `www_c3`, `www_capacity`, `docs/c*_*.md`, `docs/RESEARCH_STATE.md` history) is kept as an appendix-level record; it claims no capacity estimate. The decision trail is in `docs/status/DECISION_REGISTER.md`.

## Open items

GenAI disclosure wording, CCS concept IDs (entered from memory, to verify), the dual-submission and OpenReview confirmations, and the submission itself, which only the human author makes. See `docs/status/CURRENT_STATE.md`.
