# CEX historical L2 source audit (C0)

## Tardis Binance.US sample

Provider documentation describes Binance.US incremental depth updates and generated depth snapshots. Exchange metadata lists BTCUSD, BTCUSDC, BTCUSDT, USDCUSD, USDCUSDT, and USDTUSD. Metadata establishes advertised symbol/date availability, not successful delivery for every crisis day or downloadable entitlement. Sources (accessed 2026-10-11): [Binance.US historical data](https://docs.tardis.dev/historical-data-details/binance-us), [Tardis CSV format](https://docs.tardis.dev/downloadable-csv-files/overview), [Binance.US exchange metadata](https://api.tardis.dev/v1/exchanges/binance-us).

One free first-of-month sample was obtained from `https://datasets.tardis.dev/v1/binance-us/incremental_book_L2/2023/03/01/BTCUSD.csv.gz` and stored under `data/external/` (ignored by Git as source data). Compressed size: 40.5 MiB. SHA-256: `2061a9ff9898b24900692aae31d9c98cd547aa7e815223329b37a0834ebd8511`. Schema: `exchange,symbol,timestamp,local_timestamp,is_snapshot,side,price,amount`. It contains 7,264,627 rows: 4,019 snapshot rows (2,016 bid, 2,003 ask), 7,260,608 update rows; timestamps span March 1 UTC. This normalized feed is not itself a validated replayed book.

Replay must respect ordering for equal timestamps and snapshot/update segments. Validate per-day completeness, update semantics, reset handling, crossed-book conditions, and independent observations. No March 10–12 crisis sample has been verified locally.

## Venue and symbol coverage

| Venue / source | Relevant March 2023 symbols | C0 conclusion |
|---|---|---|
| Binance.US / Tardis | BTCUSD, BTCUSDC, BTCUSDT, USDCUSD, USDCUSDT, USDTUSD listed in metadata | Promising common venue; verify files, licence and costs by symbol/day |
| Coinbase / Tardis metadata | BTC-USD, BTC-USDT listed; BTC-USDC ends 2022-07-14 | BTC-USDC unavailable in March 2023 per metadata |
| Kraken / Tardis metadata | XBT-USD, USDC-USD, USDC-USDT, USDT-USD | Possible complement; verify symbol mapping and daily files |
| IAQF Binance.com source | BTCUSDT/BTCBUSD aggregate trades and candles | Not Binance.US and not L2; not a substitute for Binance.US book |

## Cost and decision

Tardis documents CSV access for Academic/Solo subscriptions and replay API access for higher tiers. The billing FAQ describes historical lookback varying by billing term; the listed Academic tier is advertised at $450/month, but term, academic eligibility, current price, and exact March 2023 entitlement require provider confirmation. No paid order was placed. Sources (accessed 2026-10-11): [Tardis billing FAQ](https://docs.tardis.dev/faq/billing-and-subscriptions), [Tardis pricing](https://tardis.dev/).

**Verdict: UNVERIFIED for the crisis-period capacity study; sample format verified for Binance.US BTCUSD on March 1.** Crisis-period multi-symbol coverage, price, entitlement and licence are not verified. Do not make capacity claims until these checks and book replay validation pass. [`docs/source_feasibility.md`](docs/source_feasibility.md) links this source audit as the CEX detail.
