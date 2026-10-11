# C2 source-selection decision — historical Binance.US L2

**Decided:** 2026-10-11. Built only from evidence already recorded in C1/C2. No account, API key, credits, gated LIST call, provider contact, purchase or download was used, and none was authorized.

Machine-readable record: [`reports/c2/source_decision.json`](../reports/c2/source_decision.json). Gate logic: `src/www_c2/decision.py`. `tests/test_c2_decision.py` checks that every recorded decision matches what the code produces from the recorded evidence.

## Requirement (fixed before evaluating providers)

| Item | Requirement |
|---|---|
| Venue | Binance.US (`binance-us`; CoinAPI `BINANCEUS`). Binance.com is not a substitute. |
| Symbols | BTCUSD, BTCUSDC, USDCUSD, BTCUSDT, USDCUSDT, USDTUSD (`configs/c1_symbols.yaml`) |
| Dates (UTC) | 2023-03-10, 2023-03-11, 2023-03-12. That is 18 symbol-day cells. |
| Granularity | Full-depth L2: an initial snapshot, then incremental price-level updates |
| Reproducibility | Every observation traces back to a checksummed raw artifact, and replay is deterministic |
| Rights | Academic publication of derived book states, aggregates, manifests/hashes and reproduction instructions |

## Gates and rule

Each candidate must have a status for all six gates: `venue`, `symbol_day_availability`, `transfer_size_and_cost`, `snapshot_update_semantics`, `native_sequence_ids` and `research_rights`. Each status is `VERIFIED`, `UNVERIFIED` or `FAILED`. A gate that is missing raises an error; it never counts as a pass.

- **REJECT**: at least one required gate is `FAILED`.
- **CONDITIONAL**: no required gate failed, but at least one is still `UNVERIFIED`.
- **ACCEPT**: every required gate is `VERIFIED`.

`native_sequence_ids` is required only under the `NATIVE_SEQUENCE` continuity standard. Under `PROVIDER_NORMALIZED`, the provider's ordered stream is accepted. In that case the missing native-ID proof must be disclosed as a limitation; the decision does not hide it. The project standard is currently `PROVIDER_NORMALIZED`, because C1 accepted the Tardis normalized-CSV replay on the same terms. Raising the standard is an open decision for the paper (see below).

## Decisions

| Candidate | `PROVIDER_NORMALIZED` (current) | `NATIVE_SEQUENCE` | Gates still open |
|---|---|---|---|
| **CoinAPI Flat Files PAYG** | **CONDITIONAL** | **REJECT** (no native update id in published schema) | availability, size/cost, snapshot/update semantics, rights |
| Tardis Spot annual CSV | CONDITIONAL | REJECT (normalized CSV omits `U`/`u`) | availability, cost, rights |
| Tardis Spot annual Pro raw replay | CONDITIONAL | CONDITIONAL | availability, cost, raw semantics, native IDs, rights |
| Binance.US public history | REJECT (no L2) | REJECT | — |

**Selected empirical L2 source: none.** No candidate is ACCEPT. Every remaining route needs gated access or written provider confirmation, and neither has been authorized. The 18 crisis cells stay `ACCESS_BLOCKED` (C1).

### CoinAPI rationale

- *Verified:* `BINANCEUS` is a separate venue identifier from `BINANCE`.
- *Failed under the native standard:* the published normalized schema has exchange and ingest timestamps but no Binance update ID, and the provider recommends ordering by timestamp. Ordering by timestamp is not proof of exchange sequence continuity. This could be reversed only if CoinAPI documents, or an acquired file shows, an extra native-sequence field.
- *Open:* (1) whether all 18 symbol-day L2 files exist, and their SKUs. (2) Byte sizes, and therefore cost. The per-GiB tiers are published, but no estimate is computed, and sizes are not inferred from other markets or dates. (3) L2 replay semantics. The operations `ADD/SUB/MATCH/SET/DELETE/SNAPSHOT` are documented generically, but nobody has seen how they behave on Binance.US L2 (deltas or absolute sizes, how often snapshots occur, how disconnects are marked). (4) Publication and derived-output rights: the public agreement only covers internal business use.
- *Compared with Tardis CSV:* both are equivalent on continuity. Tardis is ahead only on replay semantics, which C1 verified on a real checksummed sample. CoinAPI's advantage is usage-based pricing for a small set of days, and that advantage can't be measured without a funded listing.

## Minimum gated validation (only if explicitly authorized)

This applies to whichever route is authorized. Run these steps in order and stop at the first failure:

1. List the exact target files for the 18 cells. Record SKU/file IDs, compressed and uncompressed bytes, and list charges. Compute transfer cost with `www_c2.access.estimate_orderbook_transfer_cost` from **measured** sizes only.
2. Get written confirmation of publication and derived-output rights before buying more than a sample.
3. Download **one** representative file (for example USDCUSD on 2023-03-11). Record the SHA-256, byte size, schema, row/event counts, timestamp range and any sequence-related fields.
4. Replay snapshot plus updates with a provider-specific adapter that feeds the C1 `BookReplayer` rules: reset at each snapshot, quarantine updates until a valid snapshot, flag timestamp regressions, duplicates, gaps, and crossed or empty books. Replay twice and require identical output.
5. Update the gate statuses in `reports/c2/source_decision.json` from the observed evidence. The tests then recompute the decision.

## What is deliberately not built yet

The production ingestion pipeline (raw manifest → checksum → parser → normalized event → snapshot sync → book → analysis output) is **deferred** until one source passes the gate. Writing a CoinAPI parser now would mean guessing at L2 operation semantics that haven't been observed. The existing C1 reader and replayer already cover the Tardis normalized format, together with its data-quality tests (malformed rows, ordering, snapshot resets, crossed/empty books).

## Decisions needed from the user

1. **Continuity standard.** Should the paper accept `PROVIDER_NORMALIZED` with a disclosed limitation, which keeps CoinAPI and Tardis CSV in play? Or require `NATIVE_SEQUENCE`, which leaves only Tardis Pro raw replay, and only if its raw output turns out to contain `U`/`u` and disconnect markers?
2. **Gated access.** Choose which route, if any, may spend money or create an account for steps 1–3 above, and set a spending cap.

## Paper boundary (draft wording for the data section)

> Crisis-period (2023-03-10 to 12) Binance.US L2 data were not acquired as of 2026-10-11. Candidate providers (CoinAPI Flat Files, Tardis) were evaluated against fixed venue, symbol, date, replay-semantics, sequence-continuity and publication-rights gates; none passed without gated verification. Reconstruction methodology was validated on one publicly available normalized sample (Tardis, BTCUSD, 2023-03-01, SHA-256 `2061a9ff…8511`). Provider-normalized streams do not expose Binance.US native update identifiers, so sequence continuity between snapshots cannot be independently proven from them.
