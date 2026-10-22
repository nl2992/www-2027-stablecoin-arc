# Datasheet: exchange-dollar and stablecoin-unit series (release 1.0)

Follows the structure of "Datasheets for Datasets" (Gebru et al., 2018/2021). Counts are those of the build recorded in `resource/RELEASE_HASHES.json`.

**Status of distribution.** Read `resource/TERMS.md` first. The recommendation is to publish the code, the rebuild scripts and the exchange-free tables, and to keep the exchange-derived tables local until the Coinbase, Bitfinex, Binance.US and Kraken terms are settled. This datasheet describes the full local package.

## 1. Motivation

- **Purpose.** Cryptocurrency venues quote "USD" in units that are not the same thing: a fiat-rail failure at one venue, or a stablecoin quote unit, shifts every price on that venue by the same amount. The release provides hourly estimates of those offsets, an external USDT anchor, a labelled registry of fiat-rail episodes, and three benchmark tasks for methods that estimate or correct the offsets.
- **Gap filled.** No public table separates a venue's own dollar from crypto demand on a multi-year hourly grid, with out-of-sample test splits that were opened once.
- **Creators and funding.** The authors of the accompanying WWW 2027 submission (anonymised for review). No external funding is recorded in the repository.

## 2. Composition

Six tables, each as CSV and Parquet, described field by field in `schema.json`.

| Table | Rows | Span | Instance |
|---|---|---|---|
| `unit_offsets_pairs` | 183,933 | 2017-01-01 to 2023-12-31 | one venue pair in one hour |
| `unit_offsets_stablecoin` | 69,531 | 2022-04-01 to 2025-04-30 | one (venue, quote unit) market in one hour |
| `anchor_usdt` | 64,590 | 2018-11-27 to 2025-04-30 | one venue's USDT/USD in one hour, net of Kraken |
| `fiat_rail_labels` | 33 | 2017 to 2023 (Binance.US to 2025) | one labelled episode |
| `benchmark_splits` | 27 | n/a | one asset, control or episode of a benchmark |
| `benchmark_results` | 492 | n/a | one recorded locked-test or dev number |

Plus `benchmarks.json` (harness entry points and log hashes), `provenance.json` (hashes of the inputs), `manifest.json` and `MANIFEST.sha256`.

- **What a value is.** All market values are differences in basis points (1e4 times a log-price difference). Venue pairs are Bitfinex-Coinbase, Coinbase-Bitstamp and Bitfinex-Bitstamp, each "A minus B". For each pair-hour: the median gap over every asset listed on both venues (`b2_median_bps`), the committed shrinkage estimator's offset (`estimator_bps`), the cross-asset dispersion (1.4826 times the median absolute deviation) and the asset count. Stablecoin markets: gap against the median of the USD-quoted markets, for BTC and ETH, the B2 conversion rate, and the BTC-ETH spread of the gap. Anchor: `1e4 (log P_venue(USDT/USD) - log P_Kraken(USDT/USD))` for Bitfinex, Binance.US and Bitstamp.
- **Not included.** No price levels, volumes, trade counts or candles; no order books; no account, wallet or personal data. The tables carry no raw exchange price.
- **Coverage.** Pairs: 61,302 to 61,318 hours each, of 61,344 possible. The Bitfinex-Coinbase pair uses up to 11 assets (mean 7.2 shared per hour, since alts start later or have gaps); the two Bitstamp pairs use only BTC and ETH, so their dispersion is a two-point spread. Stablecoin markets: 13; some are short (UST: 1,008 hours before delisting; Bitstamp USDC and USDT only in short windows; FDUSD from 2023-12). The anchor has no Bitfinex values before 2018-11-27 (USDT listed under the ticker UST). The 2024-2025 span covers only Binance, Binance.US and Bitstamp, because Coinbase and Bitfinex candles were collected to 2023-12.
- **Missing data.** Hours without a traded minute are null, never imputed. A one-sided offset is null when fewer than two USD markets (stablecoin table) or fewer than two assets (dispersion) exist in the hour. The b2 conversion rate is carried forward at most 24 hours and is null beyond that.
- **Labels.** The 33 episodes (Bitfinex 12, Coinbase 8, Binance.US 6, Kraken 5, Bitstamp 2) are of types: confounder 11, banking_partner_loss 7, withdrawal_delay 5, deposit_pause 4, rail_shutdown 4, restoration 2. The registry is not exhaustive: "absence of an entry is NOT proof of no event".
- **Splits.** Defined in `benchmark_splits`: dev and test assets (UNIT-TD) and dev and test episodes (FUSE, STABLE). The test splits are spent (see `BENCHMARKS.md`).
- **Errors, noise, redundancy.** Hourly prices are the last traded close in each hour (anchor and stablecoin markets) or taken from candles (see below), so each carries bid-ask and last-trade noise of a few bps. The cleaning rule drops zero-volume hours and isolated one-hour spikes larger than 0.3 in log price. The three pair series are linked (A-B + B-C = A-C only up to the estimator and asset sets).
- **Confidential or sensitive content.** None. Source URLs in the label registry are public news and filings.

## 3. Collection process

- **Sources.** Public endpoints and bulk files, collected 2026-10-11 to 2026-10-21 with the project owner's authorisation (recorded in the `authorized` field of each acquisition plan in `configs/`): Bitfinex API v2 candles (1-minute 2017-2023 for BTC/ETH; 1-hour for alts); Coinbase Exchange candles; Bitstamp OHLC; Binance monthly klines from data.binance.vision; Binance.US monthly klines from data.binance.us; Kraken's OHLCVT bundle (USDTUSD, XBTUSD, ETHUSD). Verified files in `reports/events/acquisition_manifest.json`: Bitfinex 314 minute-months plus 11 hourly files, Coinbase 168 plus 9, Bitstamp 244 plus 5, Binance 115, Binance.US 245, Kraken 1 bundle (7 records). The manifest also lists 73 NOT_AVAILABLE months (no archive published), 0 checksum failures.
- **Integrity.** Binance and Binance.US archives are checked against the published `.CHECKSUM` files before use. API-sourced files have a SHA-256 recorded at acquisition (the providers publish none) that every panel build re-checks. The Kraken bundle was verified against Kraken's published SHA-256.
- **Time frame.** Collected in October 2026 for data from 2017 to April 2025. The release is a snapshot, not a feed.
- **Sampling.** No sampling: all available hours of the listed pairs in the span. Pair choice follows the research question (venues with a USD fiat rail; stablecoin quote units on Binance, Binance.US and Bitstamp).
- **Ethics.** Public market data only; no human subjects; no personal data; no authenticated or paid access.
- **Label collection.** Compiled from dated public sources blind to price data (no price file was opened), then frozen; the method note is in `configs/fiat_rail_labels.json`. Many pages could not be fetched (403 or timeout), and entries that rely on search-result summaries say so in their `notes`.

## 4. Preprocessing, cleaning, labelling

- Minute candles to hourly: the hour's last traded close, or the median of traded-minute closes for the Kraken anchor cross-checks in `reports/unit_td/` (the release anchor uses the last traded close for both legs). Hour labels are hour starts (empirically checked in the panel metadata).
- Fixed cleaning rule, decided before any estimator ran: (1) Bitfinex BCH splice across BCHUSD, BABUSD and BCHNUSD at fixed dates; (2) drop hours with zero or missing volume or a non-positive price; (3) drop an isolated spike (more than 0.3 in log price from both neighbours, same direction). Per-series counts are in `data/derived/*_meta.json`.
- Derived quantities are computed by `src/www_resource/build.py` from the cached panels; values are rounded to 4 decimals of a basis point (6 for benchmark scores). Rows are sorted by primary key.
- The raw files are not part of the release. `provenance.json` holds the SHA-256 of the cached panels and the Kraken file used.

## 5. Uses

- **Intended.** Evaluating estimators of venue or stablecoin units; stress-testing price indexes; labelled-episode detection of fiat-rail failures; teaching and replication.
- **Already used for.** The three benchmarks and the accompanying paper's UNIT-TD, anchor and stablecoin analyses.
- **Not suitable.** Trading or signal generation; live pricing; any financial benchmark or reference rate (the Coinbase and Bitfinex terms forbid it, and these series are hourly last-trade differences, not executable); legal or regulatory conclusions about a venue; inferring that an unlabelled period was event-free.
- **Known limits.** Offsets are relative, and the Coinbase numeraire has its own dollar. The cross-asset median assumes crypto-specific premia average out across assets, which fails when one venue moves all crypto together (the anchor table exists to test that). Last-trade prices on thin pairs are noisy. The test splits are no longer blind.
- **Do not.** De-anonymise or redistribute under terms that conflict with `TERMS.md`.

## 6. Distribution

- **Recommended public form:** code, `configs/`, manifest hashes, benchmark definitions and results, label registry; rebuild instructions in `REBUILD.md`.
- **Local package:** `resource/release/` (24.6 MB; 19.5 MB CSV and 6.3 MB Parquet). Git-ignored; its SHA-256 hashes are committed in `resource/RELEASE_HASHES.json`. CSV hashes are canonical (Parquet bytes can change with the pyarrow version).
- **Licence.** Code: to be set by the authors (no licence file exists in the repository at the time of writing). Label registry: our compilation could be CC BY 4.0, since it holds facts and links, not article text. Exchange-derived tables: depend on `TERMS.md`; if released, Binance-derived content carries CC BY-NC-SA 4.0 with attribution to Binance Vision.
- **Third-party restrictions.** See `TERMS.md`. Do not imply endorsement by any exchange.
- **DOI / hosting.** Not yet assigned. A Zenodo or OSF deposit of the exchange-free package is the natural route.

## 7. Maintenance

- **Maintainers.** The submission authors (contact withheld during review).
- **Updates.** Rebuilds are deterministic given the same inputs; a new build with new data gets a new `RELEASE_VERSION` and new hashes. There is no plan for a live feed.
- **Errata.** Track as repository issues; the label registry accepts additions with a dated public source.
- **Versioning.** `release_version` in `schema.json` and `manifest.json`. Past manifests are kept in git history through `RELEASE_HASHES.json`.
- **Extensions by others.** Allowed under the code licence once set; new benchmark episodes must be fixed before any result is seen (the harness' rule).
- **Obsolescence.** Exchange terms and endpoints change; API-sourced data may be revised by the provider, in which case a fresh download will not reproduce the recorded hashes (see `REBUILD.md`).
