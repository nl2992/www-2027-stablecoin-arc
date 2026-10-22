# Rebuilding the release from scratch

Run every command from the repository root. Python 3.11 or newer and [uv](https://docs.astral.sh/uv/) are the only prerequisites. Read `TERMS.md` before downloading anything: each provider's terms apply to the files you fetch.

## 0. Environment and tests (offline)

```sh
uv sync --group dev
uv run pytest -q -W error::DeprecationWarning
```

## 1. Fast path: you already hold the raw archives (or the cached panels)

If `data/derived/unit_td_panel.parquet`, `data/derived/stable_panel.parquet` and `data/raw/kraken_ohlcvt/USDTUSD_1.csv` exist:

```sh
uv run python -m www_resource.build --record resource/RELEASE_HASHES.json
(cd resource/release && shasum -a 256 -c MANIFEST.sha256 --quiet)   # verifies every file
```

The build takes a few seconds and writes `resource/release/` (24.6 MB). To check against the recorded hashes, compare the CSV and JSON entries of `resource/release/MANIFEST.sha256` with `resource/RELEASE_HASHES.json`; `tests/test_resource.py::test_committed_hashes_match_a_rebuild_when_data_present` does this. Parquet hashes can differ with the pyarrow version, so only CSV and JSON hashes are canonical.

## 2. From the committed scripts and public sources

The raw files (about 2.5 GB, git-ignored) come from public endpoints. Every download is listed with URL, size and SHA-256 in `reports/events/acquisition_manifest.json`.

```sh
# Binance.com and Binance.US monthly klines, checksum-verified against the published .CHECKSUM
uv run python -m www_events.acquire --plan configs/acquisition_plan.json
uv run python -m www_events.acquire --plan configs/acquisition_plan_stable.json
# Bitfinex, Coinbase and Bitstamp 1-minute candles (2017-2023)
uv run python -m www_events.acquire --plan configs/acquisition_plan_ledger.json
uv run python -m www_events.acquire --plan configs/acquisition_plan_continuous.json
# Bitstamp hourly alts (BTC/ETH are in the minute files)
uv run python -m www_events.bitstamp_hourly
```

Three inputs have no command-line entry point in the repository, and nothing here was re-run from an empty disk:

1. **Hourly alt candles** (Bitfinex and Coinbase, `data/raw/bitfinex_1h`, `data/raw/coinbase_1h`). Call `www_events.acquire.main_hourly` from Python with the (venue, provider symbol, note) items listed in the manifest records of venue `bitfinex-1h` and `coinbase-1h`, for example:
   ```sh
   uv run python -c "from pathlib import Path; from www_events.acquire import main_hourly; main_hourly(Path('.'), Path('reports/events/acquisition_manifest.json'), [('bitfinex-1h','LTCUSD',None),('coinbase-1h','LTC-USD',None)])"
   ```
   The venue strings are `bitfinex-1h` and `coinbase-1h` (see `acquire_hourly` in `src/www_events/acquire.py`); the provider symbols are in the manifest records (Bitfinex: LTCUSD, BCHUSD, BABUSD, BCHN:USD, ETCUSD, XRPUSD, XLMUSD, LINK:USD, SOLUSD, DOGE:USD, ADAUSD; Coinbase: LTC-USD, BCH-USD, ETC-USD, XRP-USD, XLM-USD, LINK-USD, SOL-USD, DOGE-USD, ADA-USD). Bitfinex BTC/ETH hourly series come from the minute files.
2. **Kraken OHLCVT.** Download the five parts `Kraken_OHLCVT_Full.zip.part00` to `part04` from `https://assets.kraken.com/marketing/institutions/` (linked from Kraken's support page, 9.5 GB), join them, check the SHA-256 `bc273e9027470b07d790a7fa4df9bb43f0dfc527c20c6ecae48402e123e7b1c7`, extract `USDTUSD_1.csv`, `XBTUSD_1.csv`, `ETHUSD_1.csv` and the `_60` files into `data/raw/kraken_ohlcvt/`, then `uv run python -m www_auto.anchor_external --register`.
3. **Fiat-rail labels** need no download: `configs/fiat_rail_labels.json` is committed.

**Hash caveat.** `www_events.acquire` skips any month that the manifest already marks VERIFIED, and every panel build refuses a file whose SHA-256 differs from the manifest. On a fresh clone, therefore: (a) Binance and Binance.US archives are immutable and re-download byte-identically; (b) files from the Bitfinex, Coinbase and Bitstamp APIs were hashed at acquisition because the providers publish no checksum, and a provider may since have revised history. For (b), either obtain the original files, or delete the manifest records of those venues, re-run the acquisition (which records new hashes), and accept that results may differ slightly from the recorded ones. In that case `RELEASE_HASHES.json` will not match and the comparison is by summary statistics, not bytes.

## 3. Build the panels and the release

```sh
uv run python -c "from www_auto import panel; panel.ensure(rebuild=True)"   # data/derived/unit_td_panel.parquet  (UNIT-TD, 2017-2023)
uv run python -m www_fuse.panel         # data/derived/fuse_panel.parquet     (FUSE, 2017-2023)
uv run python -m www_stable.panel       # data/derived/stable_panel.parquet   (STABLE, 2022-03 to 2025-04)
uv run python -m www_resource.build --record resource/RELEASE_HASHES.json
```

(Each panel is also built automatically on first use.) The release builder reads only the UNIT-TD and STABLE panels, the Kraken USDT/USD file and `configs/fiat_rail_labels.json`.

## 4. Re-run a benchmark

```sh
uv run python -m www_auto.harness       # UNIT-TD dev mode
uv run python -m www_fuse.harness       # FUSE dev mode
uv run python -m www_stable.harness     # STABLE dev mode
```

Add `--seed N` to fix the anonymisation. The `--final` flag refuses to run unless the benchmark's unlock file exists (`autoresearch/FINAL_UNLOCK`, `FINAL_UNLOCK_FUSE`, `FINAL_UNLOCK_STABLE`); the recorded locked-test runs are in `autoresearch/final_*.log`. Do not create an unlock file to tune against the test split: the committed tests are already spent. To evaluate a new method honestly, add new test episodes to the `EPISODES` tuple before running anything.

To reproduce the recorded result of a locked commit, check out that commit (`724455b`, `914b3cb`, `ca38772`), create the unlock file, run `--final --seed <seed in the log>`, and compare with the log (UNIT-TD seed 20261020; FUSE and STABLE seed 20261021).

## 5. What the release contains

`resource/release/`: `unit_offsets_pairs`, `unit_offsets_stablecoin`, `anchor_usdt`, `fiat_rail_labels`, `benchmark_splits`, `benchmark_results` (each `.csv` and `.parquet`), `benchmarks.json`, `schema.json`, `provenance.json`, `manifest.json`, `MANIFEST.sha256`. Field definitions: `schema.json` and `DATASHEET.md`.
