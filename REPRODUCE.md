# Reproducing "Same Name, Different Unit" (WWW 2027 submission, draft v15)

Run every command from the repository root, in the order below, from an empty checkout to `paper/build/main.pdf`.

How to read this guide:

- Commands are taken from each module's docstring and argument parser. The whole chain has **not** been re-run from an empty disk. `resource/REBUILD.md` covers the release-package subset in more detail.
- `tests/test_reproduce.py` checks that every module named after `python -m` below exists and has a command-line entry point, that the input files named here exist, and that no key value appears in this file.
- Raw data are never committed (`data/raw/`, `data/derived/`, `data/external/` are git-ignored). Only free public sources are used (decision D1: paid data is declined). Every download is recorded with URL, size and SHA-256 in `reports/events/acquisition_manifest.json`.
- **Locked and pre-registered steps** are marked **[LOCKED]** or **[PRE-REGISTERED]**. Section 9 lists them together. Do not re-run these with changed code, thresholds or data.

## 0. Environment

```sh
uv sync --group dev
uv run pytest -q -W error::DeprecationWarning
```

- Python 3.11 or newer; `uv` resolves the pinned environment from `uv.lock`.
- The suite is offline and deterministic (fixed seeds, synthetic fixtures, no network).
- NumPy is capped below 2.5 because of a pandas 2.3 deprecation.
- The PDF build needs `tectonic` (`brew install tectonic`); it is used by the gate in section 8.
- Secrets live only in a git-ignored `.env` at the repository root. Create it yourself and never commit it:

  ```
  FRED_API_KEY=<your own FRED key>
  WWW_ETH_RPC_URL=<your own archive-node URL>      # only for the optional on-chain steps in section 7
  ```

## 1. Data acquisition, by decision ID

`reports/events/acquisition_manifest.json` already lists every file. `www_events.acquire` skips any month the manifest marks VERIFIED, and every panel build refuses a file whose SHA-256 differs from the manifest.

**Hash caveat.** Binance and Binance.US archives are immutable and re-download byte-identically. The Bitfinex, Coinbase, Bitstamp, Upbit, Bithumb and Kraken files carry hashes recorded at acquisition, because those providers publish no checksum. A provider may since have revised history. To start over for those venues, delete their manifest records, re-run the acquisition (which records new hashes) and expect results to differ slightly from the committed reports.

| ID | What | Command or method |
|---|---|---|
| D2 | Binance (data.binance.vision), Binance.US (data.binance.us) 1-minute klines; Bitstamp minute candles; Tardis free first-of-month samples (D7) | `uv run python -m www_events.acquire --plan configs/acquisition_plan.json` |
| (2026-10-18, no D number) | Bitfinex, Coinbase, Bitstamp minute candles for the 2017-2019 Bitfinex windows | `uv run python -m www_events.acquire --plan configs/acquisition_plan_ledger.json` |
| D11 | Bitfinex, Coinbase, Bitstamp minute candles, 2017-01 to 2023-12 (about 530 files, 1.1 GB) | `uv run python -m www_events.acquire --plan configs/acquisition_plan_continuous.json` |
| D12 | Bitfinex and Coinbase hourly altcoin candles | no CLI; call `main_hourly` (below) |
| D14 | Bitstamp hourly candles for LTC, XRP, XLM, LINK, BCH | `uv run python -m www_events.bitstamp_hourly` |
| D15 | Kraken OHLCVT bundle (9.5 GB), keeping three pairs | no CLI for the download; manual steps (below), then `uv run python -m www_auto.anchor_external --register` |
| D16 | STABLE round: Binance ETH/BTC stablecoin-quoted klines, Bitstamp BTC/USDC | `uv run python -m www_events.acquire --plan configs/acquisition_plan_stable.json` |
| D17 | Upbit and Bithumb hourly KRW candles; FRED DEXKOUS | `uv run python -m www_kimchi.download` (needs `FRED_API_KEY` in `.env`) |
| D18 | Q1: Binance BTCUSDT, ETHUSDT, BTCBUSD, ETHBUSD klines for the five Q1 windows | `uv run python -m www_events.acquire --plan configs/acquisition_plan_q1.json` |
| D19 | Currency-wedge panel: Binance 1h klines in ten local currencies; Upbit and Bithumb 60-minute KRW candles | `uv run python -m www_panel.download` |

The Binance.com and Binance.US archives are verified against their published `.CHECKSUM` files. In all, 2,179 manifest records are VERIFIED; 76 are recorded NOT_AVAILABLE (months or symbols the providers do not list).

### D12: hourly altcoin candles (no CLI)

`www_events.acquire.main_hourly(root, manifest, plan)` is a function; there is no argument parser. It takes `(venue, provider symbol, note)` items. Run it with `uv run python -c`, for example for one pair on each venue:

```sh
uv run python -c "from pathlib import Path; from www_events.acquire import main_hourly; main_hourly(Path('.'), Path('reports/events/acquisition_manifest.json'), [('bitfinex-1h','LTCUSD',None),('coinbase-1h','LTC-USD',None)])"
```

Repeat for the full list in the manifest records of venues `bitfinex-1h` and `coinbase-1h`:

- Bitfinex symbols: LTCUSD, BCHUSD, BABUSD, BCHN:USD, ETCUSD, XRPUSD, XLMUSD, LINK:USD, SOLUSD, DOGE:USD, ADAUSD.
- Coinbase symbols: LTC-USD, BCH-USD, ETC-USD, XRP-USD, XLM-USD, LINK-USD, SOL-USD, DOGE-USD, ADA-USD.

Bitfinex and Coinbase BTC and ETH hourly series come from the D11 minute files. The exact list of calls used in the original run was not saved as a script; the symbol list above is read from the manifest.

### D15: Kraken OHLCVT (manual)

The repository holds no download script for this archive. Its only code is `www_auto.anchor_external`, which verifies the extracted files and registers them. The manual steps, from the manifest record, are:

1. Download `Kraken_OHLCVT_Full.zip.part00` to `part04` from `https://assets.kraken.com/marketing/institutions/` (linked from Kraken's support page; 9,546,553,626 bytes in all).
2. Join the parts (`cat Kraken_OHLCVT_Full.zip.part0* > Kraken_OHLCVT_Full.zip`) and check the SHA-256 `bc273e9027470b07d790a7fa4df9bb43f0dfc527c20c6ecae48402e123e7b1c7`.
3. Extract only `USDTUSD_1.csv`, `XBTUSD_1.csv`, `ETHUSD_1.csv` and the three `_60.csv` files into `data/raw/kraken_ohlcvt/`. Delete the archive. (The member names inside the zip are inferred from the output file names recorded in the manifest.)
4. Register the extracted files: `uv run python -m www_auto.anchor_external --register`.

### D17 and D19 notes

- `www_kimchi.download` reads `FRED_API_KEY` from the environment or `.env`. The key is never printed, saved or written to the manifest (URLs are recorded with `api_key=<redacted>`).
- `www_panel.download` first lists the Binance bucket, records NOT_AVAILABLE for missing symbol-months, then downloads and verifies the rest (about 1,000 archives, files under `data/raw/panel/`). EUR, GBP and AUD have no USDT market and are dropped by the pre-registered market-set rule (`configs/acquisition_plan_panel.json`).

## 2. Foundation: audited panel, events and descriptive tables

Needs the external IAQF panel (not in this repository) for the anchor event, plus the section 1 data. These steps produce the registry, coverage and event tables of the paper.

```sh
P=/path/to/IAQF-2026-Submission/data/parquet/panel_1min.parquet
uv run python -m www_c0.audit --panel "$P" --output reports/c0/panel_quality.json --source-revision b484e8bc75429e293c87f10a8856a5ce196b9df8
uv run python -m www_c3.cli --panel "$P" --output reports/c3/fragmentation_persistence.json --markdown reports/c3/fragmentation_tables.md --source-revision b484e8bc75429e293c87f10a8856a5ce196b9df8
uv run python -m www_c3.robustness --panel "$P" --output reports/c3/robustness.json
uv run python -m www_events.measure --panel "$P" --prefix bnus_usdcusd --event-id E2023-03-USDC-SVB --output reports/events/E2023-03-USDC-SVB_r1.json
uv run python -m www_c1.cli --input data/external/tardis_binance-us_BTCUSD_2023-03-01_incremental_book_L2.csv.gz --output reports/c1/march01_sample_validation.json --expected-sha256 2061a9ff9898b24900692aae31d9c98cd547aa7e815223329b37a0834ebd8511
uv run python -m www_events.batch       # every configured event whose data are held; reads configs/event_runs.json
uv run python -m www_events.summary     # frozen-plan decisions -> reports/events/cross_event_summary.json
uv run python -m www_events.screen      # amendment A6 screen -> reports/events/screen_A6.json
uv run python -m www_events.ust_splice  # amendment A4 UST continuation
```

- `www_events.coverage --checked-utc <UTC timestamp>` rebuilds the coverage matrix from listing metadata only.
- Provenance of the IAQF panel: SHA-256 `17704ff01a86c3c678c690aeb7b9a9f2a86702bd69bbe5cceaf359c68c6711b3`, revision `b484e8bc75429e293c87f10a8856a5ce196b9df8`. Upstream raw pulls are absent, so the panel itself cannot be regenerated (C0 audit).
- The Tardis BTCUSD sample (SHA-256 `2061a9ff9898b24900692aae31d9c98cd547aa7e815223329b37a0834ebd8511`) has no CLI. It was downloaded by hand from `https://datasets.tardis.dev/v1/binance-us/incremental_book_L2/2023/03/01/BTCUSD.csv.gz` (free first-of-month file, no key; see `CEX_L2_SOURCE_AUDIT.md`) and saved as the `data/external/` path above. The D2 plan fetches different Tardis files (USDCUSD 2023-03-01, TUSDUSDT 2024-01-01, FDUSDUSDT 2025-04-01) into `data/raw/tardis/`.
- The pre-analysis plan `docs/PRE_ANALYSIS_PLAN.md` is hash-pinned in `configs/plan_freeze.json` **[PRE-REGISTERED]**. Amendments are in `docs/PRE_ANALYSIS_AMENDMENTS.md`.

## 3. Unit evidence: probe, UNIT-TD, anchors, noise bounds

Panels are built automatically on first use and cached under `data/derived/`. To force a rebuild:
`uv run python -c "from www_auto import panel; panel.ensure(rebuild=True)"`.

```sh
uv run python -m www_auto.probe            # reports/unit_td/probe.json: unit diagnostic per venue pair and year
uv run python -m www_auto.harness          # UNIT-TD dev mode (test assets never read); add --seed N to fix anonymisation
uv run python -m www_auto.record_dev       # reports/unit_td/dev_724455b.txt (dev mode only)
uv run python -m www_auto.studies all      # T4 unit diagnostic and T2 injected-bias breakdown (dev assets only)
uv run python -m www_auto.posthoc_eval     # reports/unit_td/posthoc.json: intervals and baselines for the frozen estimator
uv run python -m www_auto.robust_eval      # reports/unit_td/robust_eval.json: assets-by-time holdout
uv run python -m www_auto.td_realdata      # reports/unit_td/td_realdata.json: CRH and GTM baselines on real data
uv run python -m www_auto.anchor           # reports/unit_td/anchor.json: USDT anchor test
uv run python -m www_auto.anchor_external  # reports/unit_td/anchor_external.json: anchor netted with Kraken USDT/USD (needs D15)
uv run python -m www_auto.noise_bounds     # reports/unit_td/noise_bounds.json: fee bands, tick sizes, persistence (reads configs/fee_schedule.json)
```

- The UNIT-TD estimator is `src/www_auto/estimator.py`, frozen at commit `724455b`. The locked test is the committed log `autoresearch/final_test_724455b.log` **[LOCKED]**. `posthoc_eval`, `robust_eval` and `td_realdata` score the frozen estimator after the lock and never tune it.
- The pre-registration is `autoresearch/program_unit_td.md`. The loop log is `autoresearch/results_unit_td_run1.tsv` (12 iterations).

## 4. Anchored-test theory

```sh
uv run python -m www_theory.applied        # reports/theory/gmm_applied.json and calibration.json
uv run python -m www_theory.simulate       # reports/theory/simulation.json (reads calibration.json)
uv run python -m www_theory.robustness     # reports/theory/robustness.json: the 360-cell robustness grid and the A3 falsification
```

Run `applied` before `simulate`, which takes its scales from `calibration.json`. The robustness grid was fixed on 2026-10-22, after the headline slope was seen and before the grid was run; the paper says so. Method notes: `docs/theory/ANCHORED_TEST.md`.

## 5. Fusion benchmarks (autoresearch rounds)

Each round has a fixed harness, one editable file, a dev score and one locked test. The pre-registrations are `autoresearch/program_fuse.md` (FUSE) and `autoresearch/program_stable.md` (STABLE), both written before any result existed.

```sh
uv run python -m www_fuse.panel            # data/derived/fuse_panel.parquet   (2017-2023; needs D11, D12, D14, D15)
uv run python -m www_fuse.harness          # FUSE dev mode
uv run python -m www_stable.panel          # data/derived/stable_panel.parquet (2022-03 to 2025-04; needs D16)
uv run python -m www_stable.panel --availability   # counts only, no scores
uv run python -m www_stable.harness        # STABLE dev mode
```

- Locked tests: `www_fuse.harness --final` and `www_stable.harness --final` refuse to run unless `autoresearch/FINAL_UNLOCK_FUSE` or `autoresearch/FINAL_UNLOCK_STABLE` exists. The runs are spent. The committed logs are the record: `autoresearch/final_fuse_914b3cb.log` (FUSE fuser `914b3cb`, seed 20261021) and `autoresearch/final_stable_ca38772.log` (STABLE fuser `ca38772`, seed 20261021) **[LOCKED]**. Both fusers in `src/` are byte-identical to those commits.
- Loop logs: `autoresearch/results_fuse_run1.tsv` (24 runs) and `autoresearch/results_stable_run1.tsv` (15 runs).
- `www_paper.bench_macros` (section 8) parses the final logs; it never re-runs the harnesses.

## 6. Pre-registered studies (run once, in this order)

### Q1: frozen fuser on untouched majority-unit events **[PRE-REGISTERED]** **[LOCKED]**

Pre-registration `autoresearch/program_q1.md`. Needs D18 and the STABLE and FUSE raw data.

```sh
uv run python -m www_q1.panel   # data/derived/q1_panel.parquet
uv run python -m www_q1.gate    # reports/q1/gate.json: feasibility gate (volumes and non-Kraken rates only)
uv run python -m www_q1.run     # reports/q1/results.json: the locked run; refuses unless the gate says the study proceeds
```

The gate kept 3 of 5 events (981 hours in the majority-unit stratum). The fuser is `src/www_q1/frozen_fuser_ca38772.py`, copied byte-for-byte from commit `ca38772`. Gate commit `e5e819c`; locked run commit `93d6f58`. Seed 20261022.

### Q2: early detection of stablecoin unit shifts **[PRE-REGISTERED]**

Pre-registration `autoresearch/program_q2.md`. All data are already held; there is no download. Needs the Q1 and STABLE panels.

```sh
uv run python -m www_q2.labels      # reports/q2/labels.json: onset labels from the label source only, before any detector runs
uv run python -m www_q2.calibrate   # reports/q2/calibration.json: thresholds on calm hours only
uv run python -m www_q2.run         # reports/q2/results.json: scoring and event bootstrap (seed 20261023)
```

Commit order: pre-registration `2189195`, labels `8abb4f0`, calibration `f9c6152`, scoring `bfa5c8b`. The calibration rule was then corrected in `55b50ed` after one scoring run. Both versions meet the false-alarm target and both tie; see `docs/review/Q2_CALIBRATION_CHANGE.md`. The committed outputs are the corrected ones. Do not re-tune.

### Currency-wedge panel **[PRE-REGISTERED]**

Pre-registration `autoresearch/program_panel.md` (commit `bfb6205`, decision D19). Needs D19 and the Kraken USDT/BTC/ETH hourly files (D15).

```sh
uv run python -m www_panel.download   # step 1 (also in section 1)
uv run python -m www_panel.classify   # step 2: 80% coverage rule and stress/calm months from L only -> reports/panel/months.json
uv run python -m www_panel.run        # step 3: OLS and IV, moving-block bootstrap (7-day blocks, 1,000 draws, seed 20261024) -> reports/panel/results.json
```

```sh
uv run python -m www_panel.cluster    # POST HOC (not pre-registered): unit-clustered bootstrap, leave-one-unit-out -> reports/panel/cluster.json; changes nothing in results.json
```

`months.json` was committed (`daa167b`) before D or X was loaded. Do not change the stress threshold, the netting or the instrument. Outcome: P1 narrow fail (interval excludes 0, lies just below 1), P2 pass (8 of 8 currencies in [0.8, 1.2]).

### Kimchi premium application **[PRE-REGISTERED]**

Pre-registration `docs/kimchi/PREREG.md` (written before any price download; novelty check `docs/kimchi/NOVELTY.md`; decision D17). Needs D17 and D15.

```sh
uv run python -m www_kimchi.download   # section 1; skips files already held
uv run python -m www_kimchi.analysis   # reports/kimchi/results.json: cross-asset common component and the USDT/KRW anchor
```

## 7. Ledger side: monitors, detector evaluation and ancillary studies

The detector rule was frozen in `docs/review/DETECTOR_PREREG.md` before the 2017-2023 evaluation **[PRE-REGISTERED]**. Labels are in `configs/fiat_rail_labels.json` (source-only; committed, no download).

```sh
uv run python -m www_rescue.platform_dollar   # Binance.US platform-dollar dislocation (exploratory)
uv run python -m www_rescue.decompose         # token versus ledger decomposition
uv run python -m www_rescue.fiat_rail         # Binance GBP and EUR rail cuts, 2023
uv run python -m www_rescue.ledger_panel      # Bitfinex 2017, 2018, 2019 panel
uv run python -m www_rescue.feed_bias         # naive index bias and signal timing
uv run python -m www_rescue.index_repair      # index repair comparison
uv run python -m www_rescue.monitor           # hourly monitor on Binance.US
uv run python -m www_rescue.detector_eval     # continuous detector evaluation, 2017-2023 (writes reports/rescue/detector_eval.json)
uv run python -m www_rescue.monitor_sweep     # operating-curve sweep; reads reports/unit_td/probe.json (run section 3 first)
```

Optional, ancillary studies (need a user-owned archive key in `.env` as `WWW_ETH_RPC_URL`; never printed or committed; the committed reports are sufficient to build the paper):

```sh
uv run python -m www_audit.pilot --stage fetch --fetch-stage boundaries   # D13 oracle pilot; hard cap of 1,500 RPC calls (--max-calls)
uv run python -m www_audit.pilot --stage analyze
uv run python -m www_c2.validation_plan       # offline request plan, 0 network calls
uv run python -m www_c2.archive_run           # D5 pool-state reproduction (84 read-only calls in the original run)
uv run python -m www_capacity.onchain_path    # on-chain capacity paths
uv run python -m www_capacity.revalue         # SVB capacity valued at exchange prices
```

The `--fetch-stage` values for the pilot are `boundaries`, `subbounds` and `rounds`; the original run's exact sequence of fetch stages was not recorded as a script.

## 8. Macros, figures, PDF and the gate

Every empirical number in `paper/main.tex` is a macro in `paper/generated/*.tex`, generated from a committed report or log. Regenerate in this order (`tests/test_paper.py` fails if a file is stale):

```sh
uv run python -m www_paper.macros
uv run python -m www_paper.rescue_macros
uv run python -m www_paper.unit_macros
uv run python -m www_paper.posthoc_macros
uv run python -m www_paper.robust_macros
uv run python -m www_paper.td_macros
uv run python -m www_paper.anchor_ext_macros
uv run python -m www_paper.theory_macros
uv run python -m www_paper.robust_anchor_macros
uv run python -m www_paper.noise_macros
uv run python -m www_paper.sweep_macros
uv run python -m www_paper.bench_macros     # parses autoresearch/final_*.log; never re-runs a locked test
uv run python -m www_paper.kimchi_macros
uv run python -m www_paper.q1_macros
uv run python -m www_paper.q2_macros
uv run python -m www_paper.panel_macros
uv run python -m www_paper.figures          # add --iaqf-panel "$P" to rebuild reports/c3/anchor_15m_series.csv
uv run python -m www_paper.figures_v9
uv run python -m www_paper.figures_panel
uv run python -m www_paper.sweep_figure
uv run python -m www_paper.abstract_text    # docs/review/ABSTRACT_SUBMISSION.md
```

Figures are deterministic (fixed style and PDF metadata); `tests/test_figures.py` checks that the committed PDFs are byte-identical to a regeneration. Then build the PDF and check compliance:

```sh
uv run python -m www_paper.gate
```

The gate runs the full suite (deprecation and future warnings as errors), builds `paper/build/main.pdf` with tectonic and checks: body at most 8 pages, 12 in total, no undefined references, `\documentclass[sigconf,review,anonymous]{acmart}`, and an anonymity scan (generic patterns plus an optional git-ignored `.gate_identity` list of strings). It reports `gate_pass`. It scores compliance only and never reads empirical results. Use `--skip-tests` to skip the suite.

The Resource-track release package is built separately (`uv run python -m www_resource.build --record resource/RELEASE_HASHES.json`); see `resource/REBUILD.md`.

## 9. Locked and pre-registered: do not re-run with changes

| Step | Status | Fixed by | Record |
|---|---|---|---|
| Pre-analysis plan (event study) | pre-registered | `configs/plan_freeze.json` SHA pin | `docs/PRE_ANALYSIS_PLAN.md`, `docs/PRE_ANALYSIS_AMENDMENTS.md` |
| Detector evaluation | pre-registered | `docs/review/DETECTOR_PREREG.md` | `reports/rescue/detector_eval.json` |
| UNIT-TD locked test | locked, run once | unlock `autoresearch/FINAL_UNLOCK`, estimator `724455b` | `autoresearch/final_test_724455b.log` |
| FUSE locked test | locked, run once | unlock `autoresearch/FINAL_UNLOCK_FUSE`, fuser `914b3cb` | `autoresearch/final_fuse_914b3cb.log` |
| STABLE locked test | locked, run once | unlock `autoresearch/FINAL_UNLOCK_STABLE`, fuser `ca38772` | `autoresearch/final_stable_ca38772.log` |
| Kimchi application | pre-registered before any price download | `docs/kimchi/PREREG.md` (`7c39655`) | `reports/kimchi/results.json` |
| Q1 | pre-registered (`7e45e0a`), locked run (`93d6f58`) | `autoresearch/program_q1.md` | `reports/q1/gate.json`, `reports/q1/results.json` |
| Q2 | pre-registered (`2189195`); calibration corrected once (`55b50ed`, disclosed) | `autoresearch/program_q2.md` | `reports/q2/*.json`, `docs/review/Q2_CALIBRATION_CHANGE.md` |
| Currency-wedge panel | pre-registered (`bfb6205`); classification committed before D, X (`daa167b`) | `autoresearch/program_panel.md` | `reports/panel/months.json`, `reports/panel/results.json` |
| Anchor robustness grid | fixed on 2026-10-22 after the headline slope, before the grid ran | `src/www_theory/robustness.py` | `reports/theory/robustness.json` |

- The three `FINAL_UNLOCK*` files do not exist in a clean checkout. Do not create them to tune against the test split; the committed tests are spent. To evaluate a new method honestly, add new test episodes to the harness's `EPISODES` tuple first.
- To audit a locked result, check out its commit (`724455b`, `914b3cb`, `ca38772`), create the unlock file, run `--final --seed <seed in the log>` (UNIT-TD seed 20261020; FUSE and STABLE seed 20261021) and compare with the log.
- Exploratory analyses (UST, the rescue-search studies, the post-hoc anchor correction) are labelled as such in the paper.

## What cannot be reproduced

- Regeneration of the IAQF panel from raw pulls: the upstream raw data are absent.
- Byte-identical re-download of files from providers that publish no checksum (see the hash caveat in section 1).
- Crisis-day order-book replay and executable capacity: the data are paid (declined, D1); no capacity number is claimed.
