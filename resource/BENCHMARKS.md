# Benchmarks

Three tasks share one idea: exchange "dollars" are not interchangeable, so a pooled price must first find each venue's or each quote unit's own dollar. Each benchmark is a fixed read-only harness, a single file that a method may edit, a dev split that the method can see and tune against, and a test split that is opened once. All numbers below are copied from the committed logs `autoresearch/final_*.log` and loop logs `autoresearch/results_*_run1.tsv`; they are also in `resource/release/benchmark_results.csv`.

## Finding that applies to all three

**Methods tuned on the dev splits did not beat the median-style baseline out of sample.** On UNIT-TD the tuned estimator scored 0.8464 on the locked test against 0.8468 for the plain cross-asset median (b2): a loss, by 0.0004. On FUSE the tuned fuser had a relative error of 1.0629 against the plain median (a score above 1 is worse), after 0.9010 on dev. On STABLE it had 1.4559 against B0, after 0.6598 on dev, and it failed the placebo check. The dev gains were real in-sample and did not transfer. We report this as a result about the benchmarks, not a defect to fix: they are built so that over-tuning shows.

Caveats that go with it: each test was run once, on one seed per benchmark; there are 5 test episodes (FUSE), 4 (STABLE), and 5 test assets (UNIT-TD); the tuning loops were short (12, 24 and 15 logged iterations). The failure is a statement about these methods and splits, not about all possible methods.

## Common rules (the fixed harness)

- The harness code (`src/www_*/harness.py`, `panel.py`, `baselines.py`) is read-only for the method author. A method edits one file: `src/www_auto/estimator.py` (UNIT-TD), `src/www_fuse/fuser.py` (FUSE), `src/www_stable/fuser.py` (STABLE).
- Dev mode reads only dev rows. Test columns or rows are never loaded, so a dev run cannot see them. Test mode needs an unlock file (`autoresearch/FINAL_UNLOCK`, `..._FUSE`, `..._STABLE`) and was run once per benchmark, by the author's session and not by the loop.
- Each call gets deep copies and a freshly loaded module. Source (venue, market, unit) labels are anonymised with a random permutation per run (the seed is printed). Reference prices are held by the harness and are not passed to the method.
- Checks, all required (`all_checks`): `causal_ok` (outputs on three random truncations match the full run before each cut, 1e-6 bps), `perm_ok` (re-anonymising changes nothing), `static_ok` (the file has no I/O, dates, venue or coin names, or imports other than numpy and pandas), `coverage_ok` (at least 99 percent of scorable hours have output). A missing output on a scorable hour counts as no correction, so withholding output cannot help.
- Commit discipline: one idea per commit; keep a change only if the dev score improves by at least 0.002 (UNIT-TD) or 0.005 (FUSE, STABLE); the logs show the discards. The loops are bounded in iterations and time.

## UNIT-TD: estimate each venue's dollar

- **Task.** From hourly log prices of several assets on Bitfinex, Coinbase and Bitstamp, estimate every venue's unit offset in bps relative to Coinbase, causally, without being told the venues. The estimator is `estimate_units(panel, numeraire) -> DataFrame` (hours x venues, numeraire column 0).
- **Data.** `data/derived/unit_td_panel.parquet`, 2017-01-01 to 2023-12-31, 61,344 hours; BTC, ETH, ETHBTC (Bitfinex only), USDT (Bitfinex only) and ten more assets built from 1-minute and 1-hour candles with one fixed cleaning rule.
- **Splits.** Visible assets: BTC plus the dev-scored ETH, LTC, BCH, ETC, XLM. Test-scored assets, never loaded in dev: XRP, LINK, SOL, DOGE, ADA. A control pair, Coinbase against Bitstamp on ETH, 2019-01 to 2023-12. Scoring is leave-one-asset-out: a scored asset's columns are removed before the estimator runs.
- **Metric.** With units `u`, the pair estimate is `u_hat = u_bitfinex - u_coinbase` against the gap `g = 1e4 (p_bitfinex - p_coinbase)` of the held-out asset. Score = `1 - sum (g - u_hat)^2 / sum g^2`, pooled over scored assets and hours. Higher is better; 0 is no correction. The control score must not fall below 0 (an open-rail pair should receive no correction).
- **Baselines.** b0: no correction (0). b1: same-hour BTC pair gap. b2: same-hour median over visible assets of the pair gaps, held-out asset excluded.
- **Locked test** (commit 724455b, seed 20261020; log `autoresearch/final_test_724455b.log`):

| Quantity | Value |
|---|---|
| Tuned estimator, test score | 0.846410 |
| b2 (cross-asset median) | 0.846830 |
| b1 (BTC gap) | 0.825795 |
| b0 | 0.000000 |
| Control score (estimator) | 0.000000 |
| Control score (b1 and b2) | -0.104272 |
| Dev score of the locked commit | 0.444783 (b2 on dev 0.4438, per the loop log) |
| All checks | pass; coverage 1.000000, control coverage 0.999932 |

Per test asset (estimator): XRP 0.9737, DOGE 0.4015, SOL 0.3775, ADA 0.3387, LINK 0.2731. Per year: 2019 0.9892, 2020 0.4484, 2021 0.3046, 2022 0.3609, 2023 0.3886.

Reading it. The tuned estimator ties b2 on test (0.0004 below) after leading it by 0.001 on dev. Its only reliable edge is on the control pair, where shrinkage correctly leaves an open-rail pair uncorrected and b1 and b2 get -0.104. The pooled score is dominated by 2019, the Bitfinex stress year; the other years score between 0.30 and 0.45.

## FUSE: fuse venue prices into one BTC and ETH price

- **Task.** `fuse(panel, items) -> DataFrame` of fused log prices for BTC and ETH from anonymised venue quotes (Bitfinex, Coinbase, Bitstamp, and Binance.US from 2022-10), called once per episode with a 30-day warm-up.
- **Data.** `data/derived/fuse_panel.parquet`, hourly, 2017-2023, with Kraken as the held reference.
- **Splits.** Fixed on 2026-10-21 before any result.

| Episode | Split | Window | Note |
|---|---|---|---|
| D1 | dev | 2017-03-01 to 2017-08-31 | |
| D2 | dev | 2020 | calm |
| D3 | dev | 2021 | calm |
| T1 | test | 2018-10-01 to 2019-05-31 | Bitfinex stress |
| T2 | test | 2023-05-01 to 2023-07-31 | |
| T3 | test | 2022-11-01 to 2022-11-30 | |
| T4 | test | 2023-03-08 to 2023-03-20 | |
| T5 | test | 2022-01-01 to 2023-12-31 | calm; T2, T3, T4 excluded |

- **Metric.** Error = `1e4 (fused - Kraken)` in bps over BTC and ETH hours, pooled. `rel_e` = method MAE / plain-median MAE per episode; `test_score` = mean `rel_e` over T1 to T5. Lower is better; 1 equals the median. Calm episodes must have `rel_e <= 1.02` (`calm_ok`).
- **Baselines.** median, vwap, trimmed (drop min and max if 4 or more quotes), drop_deviant, crh (Li et al. 2014), gtm, unit_aware (the UNIT-TD estimator, then median), and oracle (mean of Coinbase and Bitstamp; it knows which venues have an ordinary dollar, so it is a reference, not a method).
- **Locked test** (commit 914b3cb, seed 20261021; `autoresearch/final_fuse_914b3cb.log`). Dev score of the locked commit: 0.900961 (D1 0.7958, D2 0.9227, D3 0.9844).

| `rel_e` | T1 | T2 | T3 | T4 | T5 | mean |
|---|---|---|---|---|---|---|
| tuned fuser | 0.931 | 1.504 | 0.945 | 0.965 | 0.968 | **1.0629** |
| median | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| crh | 0.880 | 1.199 | 0.923 | 1.038 | 0.992 | 1.007 |
| drop_deviant | 0.890 | 0.936 | 1.008 | 1.126 | 1.034 | 0.999 |
| unit_aware | 1.024 | 1.025 | 1.119 | 1.228 | 1.171 | 1.113 |
| vwap | 15.197 | 1.387 | 0.959 | 1.261 | 1.041 | 3.969 |
| oracle | 0.881 | 0.790 | 0.921 | 1.074 | 0.958 | 0.925 |

(Baseline means are computed from the logged episode values; the logs print per-episode values and the fuser's mean only. gtm: 9.758, 5.983, 0.929, 1.028, 1.016.) All checks pass, including `calm_ok`.

Reading it. The tuned fuser beats the median in four of five episodes and loses badly in T2 (1.504, May to July 2023, where Binance.US enters and USDT/USD moves). A single episode flips the mean above 1. Plain `crh` and `drop_deviant` are about level with the median. Nothing but the oracle is clearly better.

## STABLE: find the dollar among stablecoin quote units

- **Task.** `fuse(markets, meta, side) -> Series` of fused log BTC/USD. A market is a (venue, quote unit) pair. Units and venues are anonymised, the fuser is not told which unit is the dollar, and stablecoin cross-rates are supplied as anonymised side information.
- **Data.** `data/derived/stable_panel.parquet`, hourly, 2022-03 to 2025-04, 13 markets across Binance (USDT, BUSD, TUSD, FDUSD, UST, USDC), Binance.US (USD, USDT), Bitstamp (USD, USDT, USDC), Coinbase (USD) and Bitfinex (USD). Kraken BTC/USD is the held reference.
- **Splits.** Fixed on 2026-10-21 before any result.

| Episode | Split | Window(s) | Note |
|---|---|---|---|
| S1 | dev | 2022-05 | |
| S2 | dev | 2022-11 | |
| S3 | dev | 2023-02 | placebo |
| X1 | test | 2023-03-08 to 2023-03-20 | |
| X2 | test | 2024-01 | |
| X3 | test | 2025-04 | |
| X4 | test | 2023-12 and 2025-02 to 2025-03 | placebo |

- **Metric.** Error = `1e4 (fused - Kraken)` bps. `rel_e` = fuser MAE / B0 MAE per episode; `test_score` = mean over X1 to X4. Lower is better. Placebo rule: `rel_e <= 1.02` on every placebo episode.
- **Baselines.** B0: median of all markets, every stablecoin at 1 USD. B1: volume-weighted mean. B2: convert each market by its unit's USD rate, then median. B3: CRH. B4: the FUSE fuser frozen at 914b3cb. Oracle: median of the USD-quoted markets (knows the dollar).
- **Locked test** (commit ca38772, seed 20261021; `autoresearch/final_stable_ca38772.log`). Dev score of the locked commit: 0.659802 (S1 0.6343, S2 0.4188, S3 0.9264).

| `rel_e` | X1 | X2 | X3 | X4 (placebo) | mean |
|---|---|---|---|---|---|
| tuned fuser | 0.717 | 1.326 | 2.459 | 1.322 | **1.4559** |
| B0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| B1 | 6.256 | 1.459 | 3.050 | 1.875 | 3.160 |
| B2 | 0.768 | 1.955 | 2.660 | 2.185 | 1.892 |
| B3 | 2.183 | 0.821 | 1.148 | 0.980 | 1.283 |
| B4 | 1.673 | 0.901 | 1.045 | 1.133 | 1.188 |
| oracle | 0.652 | 0.625 | 4.044 | 2.020 | 1.835 |

`placebo_ok` is False (X4 1.322 > 1.02), so `all_checks` is False; causal, permutation, static and coverage checks pass. The other columns of the log (p95, n25, n50, coverage) are in `benchmark_results.csv`.

Reading it. The tuned fuser wins only in the March 2023 USDC depeg window (X1), where unit conversion matters most, and loses to the plain median in the other three. Even the oracle loses to B0 in X3 (April 2025) and X4, which suggests that error against Kraken in those windows is not mainly a unit problem (not tested here). In the calm placebo X4 the tuned fuser, B2 and the oracle are all worse than B0, the over-tuning signature the placebo was built to expose.

## Using the benchmarks

Commands: `resource/REBUILD.md`. Release tables: `benchmark_splits` (definitions) and `benchmark_results` (the numbers above), plus `benchmarks.json` (entry points and log hashes). The locked tests are spent: the test splits of these three benchmarks should be treated as public from now on. A new submission to a Resource-track leaderboard would need new test episodes, which the harness supports by adding `Episode` entries before any result is seen.
