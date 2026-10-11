# Implementation tracker

Persistent record of task status, decisions and validation across autonomous cycles. Update this at the end of every cycle.

**Research question:** does executable restoration capacity help explain the persistence of stablecoin price fragmentation during the March 2023 USDC crisis?

## Component status

| ID | Component | Status | Evidence |
|---|---|---|---|
| C0 | IAQF panel audit, corrected parity formula | DONE (conditional close) | `docs/c0_review_packet.md`, `reports/c0/panel_quality.json` |
| C1 | L2 replay prototype, crisis-date coverage probe | DONE; crisis cells ACCESS_BLOCKED | `docs/c1_review_packet.md`, `reports/c1/*` |
| C2 | Source access feasibility, contract registry | DONE (documentation level) | `docs/c2_review_packet.md` |
| C2-gate | CEX L2 source decision (ACCEPT/CONDITIONAL/REJECT) | DONE: CoinAPI CONDITIONAL; none selected | `docs/c2_source_decision.md`, `reports/c2/source_decision.json` |
| C3 | Observed fragmentation and persistence (candle panel) | DONE (first pass) | `docs/c3_fragmentation.md`, `reports/c3/*` |
| C4 | Executable restoration capacity (CEX L2 depth) | BLOCKED: no authorized L2 source | C2 gate |
| C5 | On-chain capacity (Curve/Uniswap/PSM state) | BLOCKED: no authorized archive endpoint | `docs/c2_ethereum_access.md` |
| C6 | Capacity → persistence inference | BLOCKED on C4/C5 | — |
| M | Manuscript | NOT STARTED in repo | — |

## Backlog (priority order)

1. **C3 robustness:** compare multiple horizons (5/15/60-minute medians, which reduce bid-ask bounce), test crisis-vs-pre differences with a block-bootstrap test, and run threshold sensitivity. Add Coinbase BTC-USD as a cross-venue dollar leg to check sensitivity to the leg.
2. **C3 activity controls:** relate wedge magnitude to observable trade activity (volume, zero-volume runs, `rv60`), describing association only, not capacity.
3. **Manuscript skeleton** (`paper/`): data, measurement and limitations sections written from C0–C3 evidence; results limited to C3; capacity sections as explicit placeholders that state what data is needed.
4. **Pipeline:** a generic raw-artifact manifest (path, bytes, SHA-256, source, licence note) covering the IAQF panel and the Tardis sample, with a validation test.
5. **C4 prep (no data):** a capacity estimator on L2 book states (depth within x bps, cost to move the wedge to parity) tested on synthetic books and the March 1 Tardis sample, labelled as a method demonstration only.

## Blockers needing the user

- Continuity standard for the paper (`PROVIDER_NORMALIZED` vs `NATIVE_SEQUENCE`). See `docs/c2_source_decision.md`.
- Authorization and spending cap for any gated L2 or archive-RPC access.

## Cycle log

| Cycle | Time (ET) | Branch @ commit | Work | Tests |
|---|---|---|---|---|
| 0 | 2026-10-11 ~03:50 | c2/data-access-feasibility @ 8610d57 | C2 source gate | 53 passed |
| 1 | 2026-10-11 ~04:20 | c3/fragmentation-persistence | C3 module, real-panel report, tracker | 62 passed |
