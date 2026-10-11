# C1 order-book replay and validation

## Scope and verdict boundary

C1 evaluates whether a provider's historical Binance.US order-book stream is advertised and accessible for March 10–12, 2023, then validates a replay prototype on the locally available March 1 BTCUSD sample. It does not estimate trade costs, arbitrage capacity, or profitability.

## Source format and replay assumptions

Tardis normalized `incremental_book_L2` records contain exchange, symbol, exchange timestamp and local-arrival timestamp in epoch microseconds, `is_snapshot`, side, price and amount. Provider documentation says amount is the absolute size at that price level (not a delta), zero removes a level, a new snapshot replaces prior state, and rows before the first snapshot should be skipped. Rows are grouped by local timestamp to apply the levels from one captured message before checking the resulting best bid/ask. Source order is preserved for ties.

`src/www_c1/reader.py` streams gzip CSVs. `src/www_c1/replay.py` uses decimal price/size values, resets the book at each snapshot segment, skips updates until a complete two-sided snapshot is initialized, quarantines invalid updates until a later snapshot, reports exchange-timestamp regressions and local-arrival gaps, and records crossed/locked states after each message group. Tardis says rows are kept in original local-arrival order and notes that exchange timestamps can regress around reconnects; the replay therefore reports exchange-time regressions without reordering or automatically treating them as lost updates. A regression in local arrival ordering taints the current book until a later snapshot. These checks detect properties of the supplied rows. The normalized CSV does not expose Binance.US native `U`/`u` sequence identifiers, so sequence continuity between snapshots cannot be independently proven by this prototype.

The provider's [Binance.US feed documentation](https://docs.tardis.dev/historical-data-details/binance-us) says it validates raw `U`/`u` update sequences while collecting depth data and restarts a WebSocket connection when it detects missed messages. Its [normalized L2 schema](https://docs.tardis.dev/downloadable-csv-files/data-types) omits these exchange-native sequence fields. Its [ordering FAQ](https://docs.tardis.dev/faq/data) says daily datasets preserve local arrival order and exchange timestamps can regress on reconnect; CSV daily partitioning is by local timestamp. Tardis also states that disconnect events are not included in downloadable CSV files; those are exposed through raw replay (or normalized replay with disconnect messages enabled). Therefore, the sample's zero long local-arrival gaps is not proof that no disconnect or missing update occurred.

## Observed March 1 full-day sample replay

The pinned file hash matches C0 (`2061a9ff9898b24900692aae31d9c98cd547aa7e815223329b37a0834ebd8511`), and the full 42,552,886-byte compressed file was processed. The replay handled 7,264,627 rows in 737,562 local-timestamp message groups (651,849 multirow groups), with 4,019 snapshot rows and 7,260,608 update rows. It found two complete snapshot segments (one reset), no incomplete snapshots, no skipped pre-snapshot updates, and 3,563,122 zero-size removals. It reported one exchange-timestamp regression at CSV row 6,976,217, with no local-arrival regression. There were no local-arrival gaps over the configured 30 seconds, no invalid side/price/amount values, and no crossed or locked best-book observations after message groups.

The feed's exchange timestamps span `2023-03-01T00:00:00.692596Z` to `2023-03-01T23:59:59.934000Z`; observed local arrival lag ranged from 0 to 1,917,997 microseconds. Final replay state was two-sided with 1,170 bid and 904 ask levels; best bid was 23,630.3 (amount 0.185) and best ask 23,635.54 (amount 0.058397). These values are sample replay diagnostics, not capacity estimates. The single exchange-timestamp regression is retained as a data-quality warning; source-order replay follows the provider's documented ordering model.

## Reproduction

Install/update the project environment and run synthetic regression tests:

```sh
uv sync --group dev
uv run pytest -q
```

Replay the locally held first-of-month sample with the C0-pinned checksum:

```sh
uv run python -m www_c1.cli \
  --input data/external/tardis_binance-us_BTCUSD_2023-03-01_incremental_book_L2.csv.gz \
  --output reports/c1/march01_sample_validation.json \
  --expected-sha256 2061a9ff9898b24900692aae31d9c98cd547aa7e815223329b37a0834ebd8511
```

Reproduce unauthenticated crisis-date coverage probes:

```sh
uv run python -m www_c1.coverage --output reports/c1/coverage_matrix.json
```

The market-data sample is intentionally not in Git. The real-sample command requires the local sample file; ordinary `pytest` uses only committed synthetic fixtures.

## Integrity interpretation

The sample replay report records the SHA-256, compressed bytes, complete row count, record timestamps, snapshot/update counts, removal and anomaly counts, arrival-lag range, idle gaps, representative reconstructed best bid/ask, and final state. A completed replay establishes reconstruction of this normalized sample under the documented rules; it does not validate March 10–12 delivery, prove native sequence continuity, or independently certify that the provider captured every exchange message. See [`c1_source_coverage.md`](c1_source_coverage.md) and [`c1_review_packet.md`](c1_review_packet.md) for observed results and the decision.
