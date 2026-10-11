# Reproducing the WWW 2027 stablecoin study

Run every command from the repository root. The commands are executed by `tests/test_reproduce.py` only to the extent of checking that each module named below exists. Raw data are never committed.

## 0. Environment

```sh
uv sync --group dev
uv run pytest -q -W error::DeprecationWarning
```

The suite is offline and deterministic: fixed seeds, synthetic fixtures, no network calls. NumPy is capped below 2.5 because of a pandas 2.3 deprecation (see `docs/RESEARCH_STATE.md`).

## 1. Data inputs

| Input | Where | SHA-256 | Status |
|---|---|---|---|
| IAQF one-minute panel (Binance.US + Coinbase, 2023-03-01..21), revision `b484e8bc…` | external checkout, `IAQF-2026-Submission/data/parquet/panel_1min.parquet` | `17704ff01a86c3c678c690aeb7b9a9f2a86702bd69bbe5cceaf359c68c6711b3` | acquired, audited (C0) |
| Tardis Binance.US BTCUSD normalized L2, 2023-03-01 | `data/external/` (git-ignored) | `2061a9ff9898b24900692aae31d9c98cd547aa7e815223329b37a0834ebd8511` | acquired (public first-of-month sample) |
| Binance.com monthly 1-minute klines (stablecoins, BTC/stablecoin legs, BTCUSDT) | `data/raw/binance/` (git-ignored) | per file in `reports/events/acquisition_manifest.json` | acquired 2026-10-11 with user authorization; 31 archives, all checksum-verified |
| Binance.US USDT/USD, BTCUSD, BTCUSDT 1-minute history | `data/raw/binance_us/` (git-ignored) | per file in the acquisition manifest | acquired 2026-10-11 with user authorization; 23 archives, all checksum-verified |
| Archive-node state for documented Curve pools | via `WWW_ETH_RPC_URL` (never committed) | block hashes recorded per call | **not authorized** |

Listing metadata (sizes and ETags for the public archives) is recorded in `reports/events/coverage_matrix.json`.

## 2. Anchor-event analyses (needs the IAQF panel)

```sh
P=/path/to/IAQF-2026-Submission/data/parquet/panel_1min.parquet
uv run python -m www_c0.audit --panel "$P" --output reports/c0/panel_quality.json --source-revision b484e8bc75429e293c87f10a8856a5ce196b9df8
uv run python -m www_c3.cli --panel "$P" --output reports/c3/fragmentation_persistence.json --markdown reports/c3/fragmentation_tables.md --source-revision b484e8bc75429e293c87f10a8856a5ce196b9df8
uv run python -m www_c3.robustness --panel "$P" --output reports/c3/robustness.json
uv run python -m www_events.measure --panel "$P" --prefix bnus_usdcusd --event-id E2023-03-USDC-SVB --output reports/events/E2023-03-USDC-SVB_r1.json
```

## 3. Order-book replay prototype (needs the Tardis sample)

```sh
uv run python -m www_c1.cli --input data/external/tardis_binance-us_BTCUSD_2023-03-01_incremental_book_L2.csv.gz --output reports/c1/march01_sample_validation.json --expected-sha256 2061a9ff9898b24900692aae31d9c98cd547aa7e815223329b37a0834ebd8511
```

## 4. Multi-event protocol

```sh
uv run python -m www_events.acquire                                  # authorized public archives -> data/raw/*, manifest
uv run python -m www_events.coverage --checked-utc <UTC timestamp>   # listing metadata only
uv run python -m www_events.batch                                    # runs every event with local data
uv run python -m www_events.summary                                  # frozen-plan decisions
```

`www_events.batch` reads `configs/event_runs.json`. It skips any event whose archives are missing and records why. Registry statuses change only through the rules in `www_events.batch.apply_status`, and each change is logged to `reports/events/status_log.json`. The pre-analysis plan (`docs/PRE_ANALYSIS_PLAN.md`) is hash-pinned in `configs/plan_freeze.json`.

## 5. Manuscript artifacts

```sh
uv run python -m www_paper.macros     # paper/generated/*.tex from committed reports
uv run python -m www_paper.figures    # paper/figures/*.pdf; add --iaqf-panel "$P" to rebuild the anchor CSV
```

`paper/main.tex` uses ACM `acmart`. The PDF build has **not** been verified, because no TeX distribution is installed on the authoring machine.

## 6. On-chain validation (prepared, not executed)

```sh
uv run python -m www_c2.validation_plan                  # offline request plan; 0 network calls
WWW_ETH_RPC_URL=… uv run python -m www_c2.rpc --block <hex> --contract <address> --call-data <hex>   # only with an authorized endpoint
```

## What cannot be reproduced yet

- Independent re-download requires the same public archives. Hashes in the manifest let a reader confirm they hold identical files.
- Executable capacity. This is gated on validated order-book or on-chain state and explicit authorization.
- Regeneration of the IAQF panel from raw pulls. The upstream raw data are absent (C0 audit).
