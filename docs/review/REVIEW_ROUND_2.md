# Simulated review, round 2 (2026-10-12)

**Draft:** branch `g3/review-round1`. References start on page 6; 12 pages in total; gate passes; 209 tests.

## Round-1 findings re-checked

| ID | Round-1 sev. | Status | Evidence |
|---|---|---|---|
| R1.1 thin market | B | **Resolved (partly)** | With deposits shut, USDT/USD traded in 77% of minutes, with a median 254 trades/h and $55k/h (pre: 86%, 352, $155k). The market was active but about a third of normal volume. |
| R1.2 identification statistic | M | Resolved | Correlation of hourly changes: 0.95 (deposits shut), 0.83 (halt window); median gap 0.8% of the dislocation. The deposit-suspension phase is weak (0.50) and is not interpreted. |
| R1.3 N = 1 | M | Resolved in wording | The contributions state that the method generalises and the magnitude is one platform's. The monitor adds a second, undocumented ledger episode (May 2023). |
| R1.4 alternative account | M | Resolved | Delisting mechanics are discussed alongside the one-way gate; neither is claimed. |
| R2.1 single reference | B | **Resolved (partly)** | Second BTC reference (Binance.com BTC/USDT × Bitstamp USDT/USD): 60.8 / −556.6 bps. It still uses Bitstamp for USDT/USD, so it is not fully independent. |
| R2.2 boundaries | M | Resolved | ±1 day: deposits-shut median 573.6–620.9 bps in magnitude; halt window 37.2–70.9 bps. |
| R2.3 evaluation | M | Resolved | Hourly monitor over 5,988 hours: rail cut 67.7% flagged, SVB/FTX 0% ledger flags, calm 1.1% (0.15% outside the registry's unresolved window). The rail-cut rate is in-sample (stated). |
| R2.4 impaired phase | m | Resolved | Interpretation sentence added. |
| R2.5 precision | m | Partly | The phase table now reports correlation of changes; the minus sign is still a hyphen. |
| R3.1 Web consequences | M | Resolved | Monitor section, price-feed framing and Figure 3. |
| R3.2 coupling | M | Resolved | The token study is framed as the method's evaluation on rule-selected token failures. |
| R3.3–R3.5 | m | Resolved | WWW '27 metadata; USDC in Figure 1(b); shorter abstract. |

## New findings, round 2

| ID | Sev. | Finding | Action |
|---|---|---|---|
| N1 | M | **The May 2023 "second ledger episode" is post hoc and has no documented cause.** It must not be sold as replication. | Worded as "previously unexplained venue episode it classifies as a ledger failure"; the post-hoc split is disclosed. Keep. |
| N2 | M | **The monitor's thresholds (100 bps, agreement within a quarter) are single choices.** | Add a threshold sensitivity (50/100/200 bps; agreement 0.1/0.25/0.5) before the freeze. **Open.** |
| N3 | m | Floats cluster on pages 4–6, away from their text. | Layout pass in Phase E. **Open.** |
| N4 | m | `\acmConference` venue field is empty (city not verified). | Fill once the CFP venue is verified. **Open.** |
| N5 | m | Thirteen pages before trimming: the coverage heatmap and capacity-path figures were dropped from the PDF (kept as artifacts). | Done. |

## Scores (simulated)

| Reviewer | Round 1 | Round 2 | Remaining concern |
|---|---|---|---|
| R1 (finance / Web economics) | weak reject | borderline / weak accept | one strong case |
| R2 (measurement) | borderline | weak accept | threshold sensitivity (N2) |
| R3 (WWW fit) | weak reject | borderline / weak accept | page-1 framing works; the monitor needs N2 |

**Verdict: GO with NARROW scope.** No blocking findings remain. Next: N2 (threshold sensitivity), layout, and the abstract for the 10-18 submission.
