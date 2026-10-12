# C2 — Binance.US crisis-period L2 access feasibility

**Checked:** 2026-10-11. This is a source-entitlement assessment, not confirmation that files exist in an account or were delivered.

## Findings

Tardis's Spot plan includes all spot instruments for Binance US. Its subscription table says every plan provides downloadable CSV, while raw replay API is available only on Pro and Business. The billing FAQ states that yearly Academic, Solo, and Pro plans provide a fixed four-year history; yearly Business provides all available history. Quarterly access is 12 months and monthly access is four months. If a plan began on 2026-10-11, March 10–12, 2023 falls within the four-year window (start 2022-10-11), but not monthly or quarterly access. This is a plan-window calculation, not provider confirmation of exact symbol/day availability.

Binance.US itself advertises free historical candlesticks, trades and aggregated trades back to September 2019. Its public historical-data announcement does not list historical order-book depth, snapshots, or incremental L2, so it is a useful no-cost price/trade source but not a substitute for the required L2 feed.

| Route | Target-date eligibility | Native sequence evidence | Cost/access conclusion |
|---|---|---|---|
| Existing first-of-month public CSV | No; March 10–12 are not first-of-month | Normalized CSV omits native Binance.US U/u IDs and disconnect events | No subscription, but not the crisis dates |
| Binance.US public historical downloads | Price bars, trades and aggregate trades available historically | No historical L2 product listed in the official announcement | Free, but does not satisfy the book requirement |
| CoinAPI Flat Files PAYG | The product lists `BINANCEUS` separately from `BINANCE` and documents full limit-book files generally | The normalized schema lists exchange/ingest timestamps and update operations, but not Binance-native update IDs; exact Binance.US symbol/day book data is not publicly verified | Public rate: $8/GiB first 1 GiB per UTC day per SKU, then $4/GiB for next 9 GiB and $2/GiB thereafter. Total remains unknown without exact files/sizes and LIST charges; funded account/key required |
| Academic/Solo annual Spot CSV | Four-year window would include March 2023 | No raw replay API; native sequence continuity cannot be checked from the normalized CSV | Exact price, eligibility, license and file availability not confirmed |
| Pro annual Spot | Four-year window would include March 2023 | Raw replay API is included, subject to confirming the feed's native IDs/disconnect representation | Exact price, eligibility, license and file availability not confirmed |
| Business annual Spot | Published as all available history | Raw replay API included | Likely broader than necessary; exact quote and files not confirmed |
| Monthly/quarterly Spot | No under current published lookback windows | Depends on delivery plan | Insufficient for March 2023 |

The current primary billing documentation does not give a specific price on the cited page. We therefore record `PRICE_NOT_VERIFIED_FROM_PRIMARY_SOURCE`; no third-party estimate is used to recommend a purchase. Tardis also says Academic eligibility must be confirmed and data-plan/exchange scope matters. Before acquisition, the provider would need to confirm, in writing, (1) exact Binance.US symbols and March 10–12 files, (2) annual plan start-date entitlement, (3) the raw feed's `U`/`u` and disconnect fields if continuity proof is required, (4) total price and minimum billing term, and (5) academic publication/derived-data rights. No provider contact or purchase was initiated.

## C2 decision

No verified no-cost source has been identified for the crisis-day files plus native sequence-level validation. The March 1 public sample remains the only acquired sample. All 18 crisis symbol/day cells remain `METADATA_ONLY / ACCESS_BLOCKED` from C1; metadata is not upgraded to observed data. A future paid route may be technically suitable, but exact suitability and price remain unconfirmed. Do not ingest paid files until the user approves a named offer and license.

## Sources

- [Tardis billing, subscription history and plan access](https://docs.tardis.dev/faq/billing-and-subscriptions) (reviewed 2026-10-11).
- [Tardis Binance.US market-data details](https://docs.tardis.dev/historical-data-details/binance-us) (reviewed 2026-10-11).
- [Tardis downloadable CSV overview and authentication](https://docs.tardis.dev/downloadable-csv-files/overview) (reviewed 2026-10-11).
- [Binance.US free historical market-data announcement](https://support.binance.us/en/articles/9843310-introducing-historical-market-data-from-binance-us-download-for-free) (reviewed 2026-10-11).
- [CoinAPI-specific flat-file assessment](c2_coinapi_flatfiles.md).
- [C1 coverage evidence](../c1_source_coverage.md) and [machine-readable access matrix](../reports/c1/coverage_matrix.json).
