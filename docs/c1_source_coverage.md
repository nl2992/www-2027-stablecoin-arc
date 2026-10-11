# C1 Binance.US source coverage and access

Coverage probes are performed without credentials. **Metadata presence is not treated as proof that a daily file was delivered.** The full per-symbol/day request URLs and outcomes are recorded in `reports/c1/coverage_matrix.json`.

## Advertised instruments

The Tardis Binance.US instrument metadata API lists all six C1 symbols with an `incremental_book_L2` data type and `availableTo` through 2026-10-11. Their advertised start dates predate the crisis window: BTCUSD and BTCUSDT 2019-09-25; USDCUSD 2020-07-24; BTCUSDC 2021-01-14; USDCUSDT 2021-12-24; USDTUSD 2019-09-25. These fields establish provider metadata coverage ranges, not per-day completeness or entitlement. The metadata response was fetched from [the Binance.US exchange endpoint](https://api.tardis.dev/v1/exchanges/binance-us) on 2026-10-11.

| Symbol | Mar 10 | Mar 11 | Mar 12 | Advertised start |
|---|---|---|---|---|
| BTCUSD | Metadata only | Metadata only | Metadata only | 2019-09-25 |
| BTCUSDC | Metadata only | Metadata only | Metadata only | 2021-01-14 |
| USDCUSD | Metadata only | Metadata only | Metadata only | 2020-07-24 |
| BTCUSDT | Metadata only | Metadata only | Metadata only | 2019-09-25 |
| USDCUSDT | Metadata only | Metadata only | Metadata only | 2021-12-24 |
| USDTUSD | Metadata only | Metadata only | Metadata only | 2019-09-25 |

## Access attempts and verdict

Tardis documents that unauthenticated downloadable CSV access is available for the first day of each month; other historical files require authenticated subscription access. For all 18 crisis symbol/day cells, the unauthenticated replay API returned HTTP 401 with provider code 10 and the message that only first-of-month historical data are available without an API key. Direct unauthenticated dataset-file HEAD probes for the same 18 cells returned HTTP 404. A 404 is not evidence that the licensed file does not exist. Exact responses for each requested symbol/day and both probe URLs are preserved in the machine-readable matrix.

Academic and Solo subscriptions are documented as CSV-only; Pro and Business include raw historical replay API access. Therefore, independent checking of Binance.US native `U`/`u` sequence continuity through Tardis raw depth messages may require a Pro/Business plan, while obtaining the normalized CSV files may be possible under a CSV-only plan. The correct plan, academic eligibility, current price, use rights, and exact per-day availability require provider confirmation before purchase.

**Verdict: METADATA_ONLY / ACCESS_BLOCKED for all 18 crisis symbol/day cells.** No crisis-day L2 file was obtained or replayed, so crisis-period reconstruction is not verified. No subscription was purchased and no API key was used. If later authorized to obtain data, use a plan that covers Binance.US Spot, CSV downloads and March 2023 historical range, and verify current price, academic eligibility and exact license before acquisition. Sources (reviewed 2026-10-11): [Binance.US market-data details](https://docs.tardis.dev/historical-data-details/binance-us), [CSV access and authentication](https://docs.tardis.dev/downloadable-csv-files/overview), [subscription scope/history](https://docs.tardis.dev/faq/billing-and-subscriptions).

## Licensing and redistribution

Tardis's [Terms of Service](https://docs.tardis.dev/legal/terms-of-service) grant a limited, non-transferable permitted-use license and restrict redistribution of source data; their terms describe a narrow exception for aggregated/calculated data at a minimum 10-minute resolution. The sample is retained only in the local ignored `data/external/` directory and is excluded from Git and the PR. Confirm current academic/research publication and derived-data rights with the provider before sharing any outputs based on licensed data.
