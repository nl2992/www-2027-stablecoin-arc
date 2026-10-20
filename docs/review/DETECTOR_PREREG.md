# Detector evaluation: pre-registration (2026-10-19)

Written before any continuous 2017–2023 data was downloaded or examined. The download is authorized under D11 (`configs/acquisition_plan_continuous.json`). The ground-truth labels in `configs/fiat_rail_labels.json` are compiled from dated public sources only, without access to price data.

## 1. What has already been seen (honest disclosure)

- The hour rule (|L| ≥ 100 bps, second asset within 25% of L) was fixed in `src/www_rescue/monitor.py` (commit `7e40e67`, 2026-10-12). It was fixed on Binance.US 2022-10 to 2023-07. The 100 bps level is the pre-registered R1 severity level from `docs/PRE_ANALYSIS_PLAN.md`.
- The Bitfinex event windows (2017-02..08, 2018-09..12, 2019-03..07) were examined on 2026-10-18 with this rule unchanged. They are therefore **not** out of sample.
- Everything else in 2017-01..2023-12 at Bitfinex has not been examined, and nothing at Coinbase as a monitored venue has been examined. That is about 68 of 84 Bitfinex months. This is the out-of-sample set. Results are reported separately for the seen and unseen months.

## 2. Detector (frozen)

For a monitored venue v, reference r and hour h:

- `L` is the hourly median of 1e4 × [log P_v(BTC/USD) − log P_r(BTC/USD)], computed over minutes traded on both venues.
- `S` is the same quantity for the second asset: ETH/USD against Coinbase for Bitfinex, and USDT/USD against Bitstamp for Binance.US.
- **Hour flag:** |L| ≥ 100 and |S − L| ≤ 0.25 |L|.
- **Alarm day:** a UTC day with at least 6 flagged hours.
- **Alarm episode:** a run of alarm days. Runs separated by 3 or fewer non-alarm days are merged.

| Monitored venue | Reference r | Second asset | Months |
|---|---|---|---|
| Bitfinex | Bitstamp | ETH vs Coinbase | 2017-01..2023-12 |
| Binance.US | Bitstamp | USDT vs Bitstamp | 2022-10..2025-03 (held data) |
| Coinbase (control: open rails throughout, except as labelled) | Bitstamp | ETH vs Bitstamp | 2017-01..2023-12 |

## 3. Ground truth

- **Positive episodes:** entries in `configs/fiat_rail_labels.json` with type `deposit_pause`, `withdrawal_delay`, `banking_partner_loss` or `rail_shutdown` at a monitored venue.
- **Truth window:** from `first_public_report_date` − 30 days to `impairment_end` if documented, otherwise to `first_public_report_date` + 90 days.
- **Confounders:** episodes of type `confounder` (hacks, outages, non-fiat regulatory actions). They are used only to classify false alarms. They are not counted as positives.

## 4. Metrics

1. **Episode recall:** the share of positive episodes with data coverage whose truth window overlaps at least one alarm episode.
2. **Lead time:** the first alarm day inside [report − 30 d, report + 30 d], minus `first_public_report_date`, in days. A negative value means the alarm came first.
3. **False alarms:** alarm episodes that overlap no truth window, per venue-year of evaluated hours. Each is also classified as confounder-overlapping or unexplained.
4. **Hour-level precision and recall** of flagged hours against truth windows. This metric is secondary.

## 5. Baselines

All baselines use the same day and episode logic.

- **B1, gap only:** |L| ≥ 100, with no second-asset agreement.
- **B2, robust z-score:** |L − median₃₀d(L)| ≥ 4 × 1.4826 × MAD₃₀d(L), using a trailing window only.
- **B3, stablecoin premium:** |1e4 log P_Bitfinex(USDT/USD)| ≥ 100. This applies to Bitfinex from 2018-11, where the pair exists. It is the signal practitioners watched.

## 6. Predictions

These are recorded now and scored mechanically.

- **P1.** In the unseen months, the detector's unexplained false alarms are at most 1 episode per venue-year at Bitfinex and at Coinbase.
- **P2.** The detector has no more false-alarm episodes than B1 at the same or higher episode recall.
- **P3.** For every positive episode the detector catches, its lead time is at most +7 days. In other words, it never lags the first public report by more than a week.
- **P4.** At the Coinbase control, recall is not defined unless positives exist. The total alarm-days are less than 1% of covered days.

**Falsification:** P1 fails at both venues, or P2 fails.

## 7. Robustness

These checks are reported and not used to choose the headline.

- A grid of threshold {50, 100, 200} × agreement {0.1, 0.25, 0.5}.
- Leave-one-episode-out: choose the grid point that maximizes episode F1 on the other episodes, then score the held-out episode.
- Coinbase as the reference for Bitfinex instead of Bitstamp.
- A minimum of 3 or 12 hours per alarm day.

## 8. Not claimed

- This is not a causal claim about why rails failed.
- These are not trading returns.
- The detector is a monitor for which unit of account moved. Its index-error benefit over a plain cross-venue median is small when three or more venues are available (`docs/review/INDEX_REPAIR.md`).

## 9. Amendment D1 (2026-10-19, before any run on real data)

The label registry (`configs/fiat_rail_labels.json`, 33 episodes, `docs/review/FIAT_RAIL_LABELS.md`) arrived after sections 1–8 were committed. Applying section 3 to it literally exposed three problems. All three were fixed before the evaluation code had touched real data:

1. **Retrospective disclosures.** Some impairments were reported long after they began. For example, BFX-2018-02's 2018 withdrawal delays were reported in April 2019. Section 3 gives those episodes an empty window.
   - The window now runs from min(report, impairment_start) − 30 days to impairment_end, or to report + 90 days if no end is documented. It never ends before it starts.
   - A positive is *retrospective* if it was reported more than 30 days after it started. For these, no lead time is claimed and P3 skips them. The time from the first alarm in the window to the report is shown instead.
2. **Reference-side impairments.** A gap against Bitstamp cannot say whose dollar moved. Bitstamp's own labels (BST-2020-01, BST-2023-01) therefore count as positives for every venue monitored against it.
3. **Non-USD rails.** CB-2019-01 concerns the GBP rail and is excluded, because the monitored quantity is the USD ledger.

Added robustness: the detector scored against positives whose evidence quality is `primary_statement` or `major_outlet` only.

**Label caveats carried into the paper** (from the label note):
- The search for 2017–2022 Coinbase and Bitstamp events was shallow.
- Several 2018 Bitfinex entries rest on retrospective or secondary sources.
