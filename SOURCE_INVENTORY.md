# Source inventory (C0)

| Asset | Location / revision | C0 status | Use and limitation |
|---|---|---|---|
| IAQF research checkout | `IAQF-2026-Submission`, Git SHA `b484e8bc75429e293c87f10a8856a5ce196b9df8` | Audited, clean `main` | Reusable upstream code and derived panels; separate project, not modified |
| One-minute panel | `data/parquet/panel_1min.parquet` | Present; 30,240 × 74; SHA-256 in `reports/c0/panel_quality.json` | OHLCV plus derived features; not quote/book observations |
| Harmonized one-minute copy | `data/parquet/harmonized_raw_1min.parquet` | Present; equals `panel_1min.parquet` cell-for-cell | Despite its name, includes derived columns |
| Raw exchange pulls | `data/raw/` | Absent in upstream checkout | Raw source-row provenance and exact refetch comparison unavailable |
| Hourly/daily panels | `data/parquet/panel_1hour.parquet`, `panel_daily.parquet` | Present | Aggregates; not canonical for minute-level event analysis |
| Legacy harmonization output | `iaqf_harmonized_1m.parquet` | Not present | Script exists, but artifact cannot be compared |
| Legacy feature output | `iaqf_features_1m.parquet` | Not present | Script exists, but artifact cannot be compared |
| L2-labelled upstream outputs | `l2_*_1min.parquet` | Not present | Inputs are aggTrades and candles, not book ladders |
| Binance.US L2 sample | Tardis normalized `binance-us/BTCUSD`, 2023-03-01 | Sample downloaded; 7,264,627 rows | Hash and schema in `CEX_L2_SOURCE_AUDIT.md`; licence applies |
| Ethereum history | Google Blockchain Analytics documentation | Schema/source capability reviewed | Logs and transactions do not provide arbitrary historical EVM state by themselves |

No licensed source data beyond the single documented L2 sample are included. Users need their own IAQF checkout to reproduce the parquet audit.
