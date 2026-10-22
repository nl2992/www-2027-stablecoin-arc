# Terms of use for redistributing DERIVED series

Checked 2026-10-22 against the live pages named below. Quotes are at most 15 words. This is a research note, not legal advice. Where a page could not be read in full, or is silent, the verdict is "scripts only".

## What the release would contain

Hourly differences between venues (basis points), cross-asset medians and dispersions, and USDT/USD net of Kraken. It would contain no exchange price level, volume, or candle. Each series is nonetheless a work "based on" the venue's data, which is how several of the terms below define a derived work.

## Summary

| Source | What we used | Terms read | Derived series may be redistributed? | Verdict |
|---|---|---|---|---|
| Bitfinex | public 1-minute and 1-hour candles (API v2) | Market Data Terms, updated July 6, 2022 | No, not without written consent | Scripts only |
| Coinbase | Exchange public candles | Market Data Terms of Use, updated August 7, 2026 | No: bars derived works to third parties | Scripts only |
| Bitstamp | public OHLC endpoint | API page, "Commercial Use of Bitstamp's Exchange Data" | Yes: derived ratios and statistics are allowed | Derived series allowed (see caveat) |
| Binance (.com) | data.binance.vision monthly klines | Vision Dataset Terms v1.0, updated August 26, 2026 | Yes, non-commercially, with attribution and CC BY-NC-SA 4.0 | Derived series allowed under CC BY-NC-SA |
| Binance.US | data.binance.us public klines | Binance.US Terms of Use ("Materials" licence) | Unclear, leaning no: bars "derivative uses" | Scripts only |
| Kraken | OHLCVT bundle (USDTUSD, XBTUSD, ETHUSD) | Support page (silent) and Global Terms of Service, sections 8 and 9 | Unclear: no data licence is stated | Scripts only |

## Per-source record

### Bitfinex
- URL: https://www.bitfinex.com/legal/general/market-data/ (read in a browser; the page is client-rendered). Also https://www.bitfinex.com/legal/general/api-terms
- Permitted use: "personal and/or internal use"; "analysis of prices and markets" (Permitted Use).
- Redistribution: "Distribute, redistribute, disseminate, sell, resell, license, or sublicense Bitfinex Market Data" (Prohibited Use, item g), absent written consent.
- Benchmarks: "Create a financial benchmark, reference rate, or index" (Prohibited Use, item c). Relevant to the FUSE and STABLE tasks, which output a fused BTC/USD price.
- Data-use clause: "will not disclose, sell or transfer any Bitfinex Data without our prior written consent".
- Assessment: the terms define Bitfinex Market Data as "all data related to trading activity", and an offset series is such data in transformed form. Do not publish series that embed Bitfinex prices.

### Coinbase
- URL: https://www.coinbase.com/legal/market_data (Market Data Terms of Use; read in a browser; curl and fetch tools get HTTP 403). Developer docs point to it: https://docs.cdp.coinbase.com/exchange/introduction/welcome
- Licence: "personal or research purposes"; the licence is "non-sublicensable" and "revocable".
- Redistribution: "Redistribute, display, or disseminate the Market Data" or any "Derived Works" "to any third party outside of your organization".
- Derived Works include "works based on, referring to, or derived from the Market Data", among them charts, analytics and research.
- Benchmarks and indices: bars "indexes, fixings, or other benchmarks" and "generic or fair value prices", including for internal use.
- ML: bars using Market Data to "validate, benchmark, or otherwise improve" machine-learning models. A benchmark in which participants fit estimators on Coinbase-derived series is exposed to this clause.
- Assessment: clearly prohibits publishing derived series. This is the binding constraint for every table that contains Coinbase.

### Bitstamp
- URL: https://www.bitstamp.net/api/ (section "Commercial Use of Bitstamp's Exchange Data").
- Quote: "Bitstamp allows the incorporation and redistribution of our exchange data for commercial purposes."
- Scope: "the right to create ratios, calculations, new original works, statistics, and similar".
- Caveat: the same section sends companies using the data "for their own commercial purposes" to a Data License Agreement. The page is an API reference, not a full terms-of-use document. The general Bitstamp terms pages returned no text to our tools.
- Assessment: Bitstamp-only derived series could be released. Every table here mixes Bitstamp with another venue, so the permission does not carry over.

### Binance (.com), data.binance.vision
- URL: https://data.binance.vision/Binance_Vision-Terms_of_Use.pdf (Vision Dataset Terms, version 1.0, last updated August 26, 2026). Repository: https://github.com/binance/binance-public-data
- Licence: "provided to you under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0" (section 3.1).
- Commercial: "Commercial licensing is strictly excluded under this agreement" (3.4).
- Derived data: use of data "derived from, calculated with, or extracted from the Datasets" is governed by these terms (2.4).
- Redistribution: derivative works must give "appropriate attribution to Binance Vision" and carry the same CC BY-NC-SA 4.0 licence (4.5).
- Academic research is a listed permitted use (4.1). Naming Binance as sponsor or partner needs consent (8.2).
- Assessment: derived series may be released if the release is CC BY-NC-SA 4.0, attributed to Binance Vision, and does not imply endorsement. Our archives were fetched on 2026-10-11, after the version date, so the version we read applies.

### Binance.US, data.binance.us
- Data bucket: https://data.binance.us/ (an S3 listing, no terms on it). The repository above does not mention it. Governing terms: https://www.binance.us/terms-of-use
- Licence: "a limited, nonexclusive, and non-sublicensable license to access and use the Materials", "for your non-commercial personal or internal business uses".
- Excluded: "the distribution, public performance, or public display of any Materials" and "the modification or derivative uses of the Materials".
- Assessment: it is not certain that a kline archive is "Materials", but if it is, derived series are excluded. Unclear, so scripts only.

### Kraken, OHLCVT bundle
- Download page: https://support.kraken.com/hc/en-us/articles/360047124832-Downloadable-historical-OHLCVT-Open-High-Low-Close-Volume-Trades-data (last updated October 12, 2026). It states no licence and says the files can be "converted into other formats", which concerns format, not redistribution.
- Terms: https://www.kraken.com/legal/global-terms, sections 8 and 9 (read via a page summariser; the full text should be re-read by a human before any release).
- Section 8: "You do not have or acquire any rights to Our Content" beyond a permission "for your own benefit" that Kraken can withdraw.
- Section 9: no "license, sublicense, sell, resell, transfer, assign, distribute" of Our Content.
- Market data is not named in these sections, so it is unclear whether they cover the bundle.
- Third-party precedent, not authority: a Hugging Face repository republishes Kraken close prices and tells users to check Kraken's terms.
- Assessment: unclear. Do not publish Kraken-derived series (the anchor table) without written confirmation.

## Recommendation

1. **Public release: code and rebuild scripts only.** Publish `src/`, `configs/`, the manifest-hash lists (file names and SHA-256 of the raw archives, `reports/events/acquisition_manifest.json`), the benchmark definitions, and the locked-test results. Every released table that is a function of exchange data includes at least one venue (Coinbase, Bitfinex, Binance.US, Kraken) whose terms bar or leave unclear the redistribution of derived works, and the Coinbase and Bitfinex terms also bar index-like uses. Under the conservative rule, one such venue decides.
2. **Releasable now, with no exchange data in it:** `fiat_rail_labels` (compiled from public news; ship source URLs, not article text), `benchmark_splits` and the benchmark definitions, and the aggregate locked-test results. The aggregates are scores of our methods, not market data, but a reviewer may treat them as derived, so say so in the paper.
3. **Local package.** `resource/release/` (24.6 MB, git-ignored) is the full derived dataset for reviewers under artifact evaluation and for the authors. Do not post it publicly while any of the Coinbase, Bitfinex, Binance.US, or Kraken questions is open.
4. **Upgrade path.** Ask in writing: Coinbase and Bitfinex for permission to publish non-benchmark hourly offset series for research; Kraken and Binance.US for confirmation that their public kline and OHLCVT files allow derived research datasets. A Bitstamp-only subset and a Binance-only subset (the latter under CC BY-NC-SA) could be released without further consent, but the exchange-dollar benchmarks need the Coinbase and Bitfinex legs, so such subsets cannot carry them.
5. Keep the raw archives out of the repository, as now.

## Limits of this check

- Coinbase and Bitfinex were read in full in a browser. The Binance Vision PDF was read in full as text. Binance.US, Kraken, and Bitstamp pages were read through a summarising fetch tool or in part; quotes for those were checked against the summaries, not a verbatim copy of every clause.
- Terms change. The Binance Vision, Coinbase, and Kraken pages carry 2026 dates, so recheck before submission.
- Archive-node, Tardis, and Chainlink material in the repository is out of scope here.
