# C0 review packet: source audit and feasibility gate

## Decision requested

Review whether the evidence and gates below are sufficient to close C0. C0 does not estimate restoration capacity and does not advance into book replay or on-chain quote reconstruction.

## Reproducible evidence

- IAQF source revision: `b484e8bc75429e293c87f10a8856a5ce196b9df8`.
- Upstream minute panel is 30,240 × 74, covers March 1–21, 2023 at one-minute UTC cadence, and is value-identical to `harmonized_raw_1min.parquet`.
- Local input SHA-256, size, series coverage and timestamp diagnostics are in `reports/c0/panel_quality.json`.
- Synthetic tests exercise corrected FX parity, quote direction, UTC minute validation, explicit observation age, candle activity proxy, invalid prices, missing files and gaps. Command: `uv run pytest`.
- The eight synthetic tests run from repository-contained fixtures and require no external data. Re-running the measured panel report requires a user-provided IAQF checkout at the recorded revision; raw source pulls are absent upstream. The report retains the absolute input path from the original audit host as provenance, so it is not portable between hosts.
- Source URLs and provider documentation were reviewed on 2026-10-11; the sample request URL and compressed-file hash are recorded in the CEX audit.
- Tardis sample: Binance.US BTCUSD normalized incremental L2, 2023-03-01; 7,264,627 rows; SHA-256 `2061a9ff9898b24900692aae31d9c98cd547aa7e815223329b37a0834ebd8511`.

## Material limitations

1. Upstream raw API pulls are absent, preventing row-level provenance/refetch verification.
2. Candle closes, high-low ranges and zero-volume runs do not provide executable quotes, quoted spreads, or L2 depth.
3. Existing raw USDC wedge omits USDC/USD correction. Corrected formula is implemented, but candle timestamps are not executable synchronized quotes.
4. The single March 1 L2 sample validates format only. March 10–12 coverage, other symbols, licensing and exact paid access remain open.
5. Ethereum event tables do not alone yield arbitrary historical pool state or validated swap quotes. DEX/PSM deployment and state access remain open.
6. March 2023 is one stress event; eventual inference requires independent events or carefully limited claims.

## C0 exit criteria

Pass if the panel audit is reproducible, limitations are explicit, synthetic tests pass, the sample source/licensing constraints are documented, and open data gates carry forward. Recommendation: **conditional close of C0 for source auditing only**. CEX coverage and on-chain state are not cleared for capacity estimation. Before capacity work, verify crisis-date source access and implement validated book replay.
