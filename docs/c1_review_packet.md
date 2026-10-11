# C1 review packet: Binance.US L2 availability and replay integrity

## Decision requested

Independently review the source-coverage classification, replay implementation, tests, and actual March 1 sample report. C1 must stop before any execution-capacity or profitability estimate.

## Evidence files

- `configs/c1_symbols.yaml`: six requested instruments and March 10–12 window.
- `reports/c1/coverage_matrix.json`: provider metadata plus unauthenticated download/API probes per instrument/day.
- `reports/c1/march01_sample_validation.json`: full streaming replay diagnostics for the checksum-pinned public sample.
- `docs/c1_orderbook_validation.md`: algorithm, reproduction commands, limitations.
- `docs/c1_source_coverage.md`: evidence levels, access and license constraints.

## Validation status

The full March 1 BTCUSD sample was replayed after verifying the C0-pinned SHA-256. It contained 7,264,627 rows, two complete snapshot segments, no skipped updates, no invalid price/amount/side values, and no crossed or locked observations after message groups. One exchange-timestamp regression was reported and retained in source order; local-arrival timestamps remained monotonic. Detailed quantitative outputs are in `reports/c1/march01_sample_validation.json`.

All 18 crisis-period pair/day cells are `METADATA_ONLY` with `ACCESS_BLOCKED`: metadata advertises incremental L2 support and a date range covering March 2023, but unauthenticated CSV probes returned 404 and raw API probes returned 401/code 10. No crisis-day file was obtained. Full results are in `reports/c1/coverage_matrix.json`.

The normalized CSV omits Binance.US native sequence numbers and downloadable CSVs omit disconnect events. Tardis documents sequence validation during collection, but this replay cannot independently repeat that check or certify provider capture completeness. Pro/Business subscriptions include raw replay API access according to current provider docs; no subscription was purchased. The sample remains excluded from Git.

Final verification: `uv run pytest -q` — 19 passed (8 C0 and 11 C1); `git diff --check` passes. **C1 recommendation:** accept the prototype and source audit as a feasibility checkpoint, but keep March 10–12 capacity work blocked until licensed crisis files are supplied and native sequence/replay validation is performed. No capacity estimate was started.
