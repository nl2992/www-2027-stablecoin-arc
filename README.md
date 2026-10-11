# WWW 2027 stablecoin arbitrage capacity research

This repository is the separate research workspace for the C0 source and feasibility audit.
The current research question is whether executable restoration capacity helps explain the persistence of stablecoin price fragmentation during the March 2023 USDC crisis.

## C0 findings

- The IAQF checkout at revision `b484e8bc75429e293c87f10a8856a5ce196b9df8` contains a 30,240-row, 74-column Binance.US/Coinbase OHLCV panel for 2023-03-01 through 2023-03-21. Its `panel_1min.parquet` and `harmonized_raw_1min.parquet` are value-identical. Source data are referenced by path and hash in the audit report, not copied into this repository.
- Upstream `generate_data.py` documents the construction path, but raw pulls are absent, so exact regeneration of the parquet is not currently reproducible. Other legacy scripts describe different, absent outputs; see [`docs/iaqf_audit.md`](docs/iaqf_audit.md).
- Eight repository-contained synthetic quality tests pass with `uv run pytest`. They check timestamps, quote direction, parity arithmetic, activity age, and missing/invalid observations. They do not require the IAQF data or live services.
- A Tardis normalized Binance.US BTCUSD L2 sample for 2023-03-01 is present locally under `data/external/`, subject to its source licence, and deliberately excluded from Git. It has 7,264,627 rows. It demonstrates that the sample format can be inspected; it does not verify crisis-day coverage, full book replay, or other instruments. See [`CEX_L2_SOURCE_AUDIT.md`](CEX_L2_SOURCE_AUDIT.md).
- Historical Ethereum logs can support event extraction, but they do not alone establish arbitrary pool state or executable historical quotes. See [`docs/source_feasibility.md`](docs/source_feasibility.md).

## Reproduce

Install with `uv sync --group dev`, then run `uv run pytest`. To audit the original IAQF panel, provide your own IAQF checkout at the audited revision and run:

```sh
uv run python -m www_c0.audit \
  --panel "/path/to/IAQF-2026-Submission/data/parquet/panel_1min.parquet" \
  --output reports/c0/panel_quality.json \
  --source-revision b484e8bc75429e293c87f10a8856a5ce196b9df8
```

Read [`docs/c0_review_packet.md`](docs/c0_review_packet.md) before proceeding to C1. C0 deliberately stops before capacity estimation.

Reproducibility has three levels: (1) synthetic validation is fully repository-contained; (2) the measured panel report requires the external IAQF parquet and exact source revision; (3) CEX and Ethereum feasibility is documented from cited sources, while crisis-day L2 replay and historical contract-state validation remain unverified. The committed panel report preserves the original machine-specific input path as provenance, so that path will differ on another computer.

## C1 order-book validation

The C1 replay prototype is under `src/www_c1/`. Run `uv run pytest -q` for C0+C1 synthetic tests. The local first-of-month BTCUSD sample can be replayed with the command in [`docs/c1_orderbook_validation.md`](docs/c1_orderbook_validation.md); licensed source data are ignored by Git. Crisis-period Binance.US files for March 10–12 remain access-blocked without authenticated subscription access, so no crisis-day replay or capacity estimate is claimed. See [`docs/c1_review_packet.md`](docs/c1_review_packet.md).

## C2 access feasibility

C2 compares historical Binance.US access options, documents Ethereum indexed/archive-state capabilities, and registers source-documented contract candidates without claiming historical state verification. See [`docs/c2_review_packet.md`](docs/c2_review_packet.md). The offline RPC probe can be run only against a user-authorized endpoint by setting `WWW_ETH_RPC_URL` locally; C2 itself made no live RPC calls, purchased no data, and estimated no capacity. The CEX L2 source gate is recorded in [`docs/c2_source_decision.md`](docs/c2_source_decision.md): CoinAPI is CONDITIONAL (REJECT under a native-sequence standard) and no crisis-day L2 source is selected yet.

## C3 observed fragmentation

`src/www_c3/` measures FX-corrected USDC and USDT parity wedges, and how persistent they are, on the audited IAQF minute panel. See [`docs/c3_fragmentation.md`](docs/c3_fragmentation.md). These are trade-price measurements, not executable capacity. Task status lives in [`docs/RESEARCH_STATE.md`](docs/RESEARCH_STATE.md).

## E1 multi-event design

The study covers multiple events. `configs/event_registry.json` records candidate stablecoin stress episodes from 2020 to 2026 with sources, pre-specified qualification rules (R1–R4), independence clusters, out-of-sample and placebo roles, and a machine-readable coverage matrix. See [`docs/e1_event_registry.md`](docs/e1_event_registry.md). Only the March 2023 anchor is measured so far.
