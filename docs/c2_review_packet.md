# C2 independent review packet

**Checkpoint:** C2 — access feasibility and historical contract discovery
**As-of date:** 2026-10-11
**Starting point:** accepted C1 commit `ad74f00f0a284cb02f130be5bf6194e639ece8b4`
**Research boundary:** no data purchase, cloud-account creation, credential use, provider contact, external commitment, historical quote simulation, or capacity estimate.

## Decision summary

- C1 remains accepted; its March 10–12, 2023 coverage remains access-blocked, not absent.
- Tardis documents that Spot covers Binance.US and that yearly Academic/Solo/Pro access reaches four years; on 2026-10-11 the target period falls within that published window. Monthly and quarterly do not. Academic/Solo provide CSV only; raw replay is Pro/Business. Exact target files, prices, academic license, and native sequence/disconnect evidence were not provider-confirmed. Cost is recorded as `PRICE_NOT_VERIFIED_FROM_PRIMARY_SOURCE`.
- CoinAPI documents a distinct `BINANCEUS` exchange identifier, full-book products generally, and PAYG usage rates. Exact Binance.US target-symbol/date book files and sizes remain `NOT_PUBLICLY_VERIFIED`; total download cost and research/redistribution rights remain unresolved. See [`docs/c2_coinapi_flatfiles.md`](c2_coinapi_flatfiles.md).
- Binance.US advertises free historical candles, trades and aggregate trades back to 2019, but its official product description does not list historical L2; this is not a book-data alternative.
- Google Blockchain Analytics offers indexed historical event data; the first 1 TiB/month of on-demand query processing is documented free. It does not supply arbitrary historical contract state calls. Alchemy lists full archive data on its free tier but requires an account/API key. Cloudflare documents historical archive methods, but usable endpoint terms/configuration were not verified. No live RPC probe was run.
- Curve 3pool, Uniswap v3 factory and legacy Maker USDC PSM candidates are source-documented only. Their target-block deployment and state remain unverified; no pool set or historical parameters are claimed as measured.
- Source-selection gate ([`docs/c2_source_decision.md`](c2_source_decision.md), `reports/c2/source_decision.json`): CoinAPI is **CONDITIONAL** under the current provider-normalized continuity standard and **REJECT** under a native-sequence standard; no L2 source is selected and ingestion is deferred until one passes.
- The offline access evaluator, registry validator and read-only RPC probe have synthetic tests. Synthetic tests establish tool behavior only, not provider access or historical truth.

## Files

- `configs/c2_sources.yaml`, `configs/c2_contracts.yaml`
- `src/www_c2/access.py`, `src/www_c2/contracts.py`, `src/www_c2/rpc.py`, `src/www_c2/decision.py`
- `tests/test_c2_access.py`, `tests/test_c2_contracts.py`, `tests/test_c2_rpc.py`, `tests/test_c2_decision.py`
- `docs/c2_cex_access.md`, `docs/c2_ethereum_access.md`, `docs/c2_contract_registry.md`
- `docs/c2_coinapi_flatfiles.md`, `docs/c2_source_decision.md`
- `reports/c2/access_matrix.json`, `reports/c2/contract_registry.json`, `reports/c2/source_decision.json`

## Reproduction

Run `uv sync --group dev`, `uv run pytest -q`, `git diff --check`, and validate the three JSON reports with `python -m json.tool`. Tests use synthetic inputs and mocks; no network calls are part of the test suite. The `www-c2-rpc-probe` entry point is documented but not executed.

## Open decisions / next step

1. If the user wants historical L2, obtain a named provider offer confirming exact March 2023 files, a four-year annual lookback, the minimum Spot subscription/term/price, academic/research rights, and whether raw replay exposes native sequence IDs and disconnects. No purchase is authorized by this packet.
2. If archive-state validation should proceed, authorize a specific account/provider or an endpoint whose published terms allow the planned queries. Do not put credentials in chat. First run a minimal read-only historical block/code/call probe and independently verify block hashes.
3. C3 should begin only after actual licensed L2 and/or on-chain historical-state evidence is obtained and independently checked. Capacity estimation remains deferred to a later, separately reviewed checkpoint.

## Acceptance gates

- C0+C1 regression suite plus all new C2 tests pass.
- Access windows, delivery capabilities, price uncertainty, and data-versus-entitlement distinction are explicit.
- CoinAPI's venue identifier, data format, sequence limitations, usage-price tiers and account/license requirements are separated from exact file availability.
- Every contract candidate has a source and conservative verification status.
- No credentials, purchases, provider contact, live RPC calls or capacity calculations occurred.
- Remaining blockers and decisions are explicit.
