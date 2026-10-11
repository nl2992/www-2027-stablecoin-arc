# C3 — Observed stablecoin parity fragmentation and its persistence (candle panel)

**Data:** IAQF `panel_1min.parquet`, revision `b484e8bc75429e293c87f10a8856a5ce196b9df8`, SHA-256 `17704ff01a86c3c678c690aeb7b9a9f2a86702bd69bbe5cceaf359c68c6711b3`. The panel has 30,240 Binance.US one-minute candles, 2023-03-01 to 2023-03-21 UTC (audited in C0).
**Outputs:** [`reports/c3/fragmentation_persistence.json`](../reports/c3/fragmentation_persistence.json) and the generated tables in [`reports/c3/fragmentation_tables.md`](../reports/c3/fragmentation_tables.md).
**Scope:** this measures the *dependent-variable side* of the research question, i.e. how large and how persistent observed fragmentation was. It does not measure executable restoration capacity, which still requires crisis-day L2 data (see [`c2_source_decision.md`](c2_source_decision.md)).

## Definitions

- **Wedge:** w_t^q = 10,000 × [log P_t(BTC/q) + log S_t(q/USD) − log P_t(BTC/USD)] for q ∈ {USDC, USDT}. All three legs are Binance.US last-trade closes. This is the FX-corrected formula from `www_c0.quality.parity_wedge_bps`. The upstream `lop_bnus_*` columns omit S and are not used.
- **Observation rules.** `all_legs_traded` keeps minutes in which every leg printed positive volume; this is the primary rule. `all_minutes_last_close` keeps every grid minute and carries stale closes forward; it is reported in the JSON as a robustness view only.
- **Persistence.** OLS AR(1) is fitted on consecutive observed minutes only; a pair is never formed across an unobserved minute or a regime boundary. φ uses an intercept, so it measures reversion to the regime mean. *φ to parity* has no intercept and measures reversion to w = 0. Half-life = −ln 2 / ln φ. The 95% interval is a percentile interval from a moving-block bootstrap of adjacent pairs (block 60, 500 draws, seed 20230310).
- **Episodes.** An episode is a run of |w| above a threshold (10, 25 or 50 bps), judged at observed minutes only. It ends at the first later observed minute back inside the band. Episodes still open at a regime boundary are counted as censored.
- **Regimes:** the upstream calendar labels. `pre_crisis` is 1–9 March, `crisis` 10–12, `recovery` 13–15, `post` 16–21.

## Results (generated; 25 bps threshold, `all_legs_traded`)

| | pre_crisis | crisis | recovery | post |
|---|---:|---:|---:|---:|
| USDC median abs wedge (bps) | 2.06 | 8.13 | 6.40 | 5.10 |
| USDC P95 abs wedge (bps) | 8.6 | 77.8 | 32.5 | 16.1 |
| USDC share of minutes > 25 bps | 0.3% | 21.9% | 11.2% | 0.8% |
| USDC φ (95% CI) | 0.17 (0.05–0.26) | 0.27 (0.16–0.43) | 0.19 (0.09–0.61) | 0.43 (0.23–0.54) |
| USDT median abs wedge (bps) | 1.03 | 1.93 | 2.49 | 2.39 |
| USDT share of minutes > 25 bps | 0.0% | 0.1% | 0.1% | 0.0% |

The full tables, including the mean, the maximum, episode counts and durations, and φ to parity, are in `reports/c3/fragmentation_tables.md`. Every number above is copied from that generated file.

## What the evidence supports

1. **Fragmentation was USDC-specific and concentrated in the crisis window.** The USDC wedge's median magnitude roughly quadrupled from pre-crisis to crisis (2.06 → 8.13 bps). Its 95th percentile rose about ninefold (8.6 → 77.8 bps), and 21.9% of jointly traded crisis minutes exceeded 25 bps. The USDT wedge stayed small throughout: its 95th percentile was at most 8.5 bps.
2. **Elevated dispersion stayed elevated after the crisis window.** USDC magnitudes remained high in the recovery window and had not returned to pre-crisis levels by 16–21 March (median 5.10 vs 2.06 bps).
3. **At one-minute resolution the wedge is not a persistent one-signed gap.** Mean wedges are close to zero in every regime (|mean| ≤ 1.6 bps), and AR(1) half-lives toward parity are under about 1.5 minutes. So what persisted over days was a *regime of large, rapidly reverting deviations*, not a sustained price gap in one direction.

## What it does not support

- **No claim about executable arbitrage.** Last-trade closes on three legs are not synchronized quotes, and asynchronous prints alone create apparent wedges. Bid-ask bounce pushes minute-level φ downward. A short minute half-life therefore does **not** show that deviations were arbitraged away within a minute.
- **No capacity attribution.** Whether restoration capacity explains the persistence of elevated dispersion is untested until L2 depth (C2 gate) or on-chain state (C2 Ethereum access) is acquired.
- **Selection.** `all_legs_traded` keeps 2,570 of 4,320 crisis minutes for USDC, and the selection depends on activity. The stale-close rule gives the same qualitative ordering (see the JSON), but its AR(1) values are inflated by construction.
- **One event.** The results describe March 2023 only.

## Reproduce

```sh
uv run python -m www_c3.cli \
  --panel /path/to/IAQF-2026-Submission/data/parquet/panel_1min.parquet \
  --output reports/c3/fragmentation_persistence.json \
  --markdown reports/c3/fragmentation_tables.md \
  --source-revision b484e8bc75429e293c87f10a8856a5ce196b9df8
```

The run is deterministic: the bootstrap seed is fixed, and `tests/test_c3_fragmentation.py` checks that repeated runs give identical output. The input SHA-256 is recorded in the report and must match the value above.

## Robustness (`reports/c3/robustness.json`)

Reproduce with `uv run python -m www_c3.robustness --panel <panel_1min.parquet> --output reports/c3/robustness.json`. The bootstrap uses 1,000 draws, 60-observation blocks and seed 20230310. Values below are copied from the JSON.

- **Crisis vs pre-crisis (USDC, all-legs-traded).** The median absolute wedge rises by 6.08 bps (95% CI 3.75–9.16), the P95 by 69.2 bps (48.9–84.0), and the share of minutes above 25 bps by 21.6 percentage points (14.7–28.4). All three intervals exclude zero. For post vs pre-crisis, the median and P95 are still higher (+3.04 bps, CI 2.38–3.98), but the >25 bps share is not distinguishable from zero.
- **USDT.** The crisis increases are small (median +0.91 bps, CI 0.66–1.20), and the >25 bps share does not change detectably.
- **Horizon aggregation.** Medians over 5-, 15- and 60-minute bins reduce last-trade bounce. For USDC in the crisis, the 15-minute median |wedge| is 4.83 bps, against 1.32 bps pre-crisis. The parity-anchored half-life measured on bin medians is about 13–16 clock minutes in the crisis (12.6 min at 15-minute bins, 16.2 min at 60-minute bins), compared with 0.5 min on one-minute closes. Minute-level reversion therefore overstates how fast fragmentation cleared once microstructure noise is averaged out. Half-lives in calm regimes rest on wedges near zero and are imprecise.
- **Alternative dollar leg.** Replacing Binance.US BTC-USD with Coinbase BTC-USD gives the same ordering: the USDC crisis median is 10.78 bps vs 2.06 bps pre-crisis, and the >25 bps share is 28.1% vs 0.2%. This version includes a cross-venue BTC basis.
