# C2 follow-up — CoinAPI Flat Files for Binance.US L2

**Reviewed:** 2026-10-11. Public documentation only; no account, key, funded credit balance, LIST call, provider contact, purchase, or download was used.

## What is documented

- CoinAPI's Flat Files exchange table lists `BINANCEUS` (Binance US) as a distinct exchange identifier, separate from `BINANCE` (Binance.com). The vendor's static supported-exchange table reports `data_trade_start` for `BINANCEUS` from 2019-10-09, but this is trade coverage—not proof of historical order-book coverage.
- Flat Files broadly offers a `Full Limit Order Book` dataset with updates and snapshots. The general schema includes `time_exchange`, `time_coinapi`, side, update type, price, size and an order ID only for L3 records. The update types include `ADD`, `SUB`, `MATCH`, `SET`, `DELETE` and `SNAPSHOT`; snapshots are described as appearing at day start or after disconnects.
- The published normalized schema does **not** list Binance-native update sequence identifiers. The provider recommends sequential processing using timestamps; that is not equivalent to proving native exchange sequence continuity.
- The vendor describes `BINANCEUS` and the full-book product separately, but this public evidence does not establish that the six C1 target symbols have L2 files for each date 2023-03-10 through 2023-03-12. Per-symbol order-book date fields exist in market-data metadata responses, but no funded Flat Files listing or entitlement was used to inspect actual files.

## Published usage rates and cost boundary

The PAYG plan is advertised at $1 per usage credit with no commitment. For Full Order Book (L2/L3/L4) transfer, the pricing table lists, **per UTC day per SKU**, $8/GiB for the first 1 GiB, $4/GiB for the next 9 GiB, and $2/GiB above 10 GiB. The dataset estimator can help, but using it consumes credits. File listing also consumes usage credits. A $25 welcome-credit offer is documented only after payment verification and API-key creation; this is not anonymous access and was not used.

No total CEX acquisition cost is computed: exact files, file sizes, whether each of the six pairs is present, and listing/request charges are unknown. The helper in `www_c2.access` returns no estimate if transfer size is unknown and computes only the published data-transfer component when a measured size is supplied; it excludes LIST/API calls, taxes, and any contractual fees. Do not compare this incomplete cost with a Tardis subscription price or treat the stated rates as a quote.

## License and access

The vendor's current customer agreement says use of services is for internal business purposes, account registration is required for orders/API keys, usage credits are applied to PAYG, and customers are responsible for external data-source restrictions and additional licenses. The public terms do not clearly grant academic publication of outputs derived from exchange feeds or redistribution rights. Those matters require written clarification before acquisition or publication. No account has been created and no terms were accepted.

## Verdict

CoinAPI is a **potential usage-priced path, not a verified source solution**. Its per-GiB price model could fit a limited set of days if the files are small and present, but the published evidence does not establish exact Binance.US crisis-day L2 data or native sequence continuity. A funded listing request is a future access decision; it must not be run without authorization. The current classification for all 18 symbol/day cells remains `NOT_PUBLICLY_VERIFIED` for CoinAPI and C1 remains `ACCESS_BLOCKED` for crisis L2 overall.

## Sources

- [CoinAPI Flat Files overview and exchange identifiers](https://www.coinapi.io/products/flat-files/docs) — `BINANCEUS` entry and account/usage-credit requirements.
- [CoinAPI full limit-book schema and replay semantics](https://www.coinapi.io/products/flat-files/docs/datasets/limitbook) — update fields, operations and snapshot notes.
- [CoinAPI exchange metadata table, letter B](https://www.coinapi.io/products/market-data-api/docs/metadata-tables/supported-exchanges/exchanges_B) — exchange-level row contains trade dates; not order-book dates.
- [CoinAPI Flat Files pricing](https://www.coinapi.io/products/flat-files/pricing) and [transfer cost estimator](https://www.coinapi.io/products/flat-files/docs/estimation-guide) — dated PAYG unit rates and per-day/per-SKU tiers.
- [CoinAPI Flat Files FAQ](https://www.coinapi.io/products/flat-files/faq) — access steps and welcome credit conditions.
- [CoinAPI customer agreement](https://www.coinapi.io/legal) — effective 2025-08-18; internal-business-use scope and responsibility for external source restrictions.
