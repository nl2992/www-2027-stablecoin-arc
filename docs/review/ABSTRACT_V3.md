# Abstract v3 (draft, 2026-10-20)

**Working title:** Which Dollar? Exchange Dollars as Exchange Rates in Web Crypto Prices

Crypto prices on the web are quoted in dollars, but an exchange's ledger dollar is a claim on that exchange and can trade away from a redeemable U.S. dollar. Prior work attributes cross-exchange bitcoin premia to such frictions without separating them from asset-specific movements. We develop an hourly decomposition that does. A shift in an exchange's dollar moves every asset there equally, so agreement across unrelated assets identifies the exchange's dollar exchange rate, and triangular parity checks it. Applied to Bitfinex, Coinbase and Bitstamp from 2017 to 2023, the decomposition showed that Bitfinex's dollar carried its own exchange rate throughout, with daily bitcoin and ether gaps against Bitstamp correlated at 0.94 or more in every year, while gaps between Coinbase and Bitstamp after 2018 were below 3 basis points (bps) and mostly asset-specific. A single rate per exchange-hour, estimated from other assets, removed 85% of the mean-square cross-exchange gap for five assets withheld from development (99% in 2019, 30% to 45% in each later year), and made no correction for an exchange pair that shared a dollar. A monitor built on the decomposition, with a rule fixed in advance, raised 0.4 false alarm episodes per exchange-year from 2017 to 2023, a third the rate of a plain price-gap alarm at equal recall, and flagged Bitfinex from October 2018, six and a half months before regulators disclosed its loss. In 2023 it separated three shocks. Binance.US's dollar stood a median 557 bps from the U.S. dollar for 530 hours after its banks withdrew. The loss of Silvergate and Signature banking left no discount on any monitored exchange. The USDC run moved the token, not an exchange dollar, and Chainlink's bitcoin and ether feeds did not inherit the token's depeg. Aggregators and oracles can thus state which dollar a price is in.

---

## Source for every number

| Claim | Source |
|---|---|
| Daily BTC–ETH gap correlation ≥ 0.94 against Bitstamp, every year | `reports/unit_td/probe.json` (minimum 0.949 in 2021) |
| Coinbase–Bitstamp after 2018: median gap below 3 bps, mostly asset-specific | hourly core panel probe: median BTC gap 2.3, 1.6, 1.3, 1.2 and 0.7 bps for 2019–2023; the BTC-implied correction removes at most 33% of the ETH gap in any of those years |
| 85% on held-out assets; no correction for the shared pair | `autoresearch/final_test_724455b.log` (test 0.846, control 0.000) |
| 0.4 vs 1.29 false alarms per venue-year, equal recall 7/9 | `reports/rescue/detector_eval.json` (Bitfinex, all months) |
| Flagged from 2018-10-08; NYAG disclosure 2019-04-25 | `reports/rescue/detector_eval.json`; `configs/fiat_rail_labels.json` |
| Binance.US median 557 bps, 530 hours | `paper/generated/rescue_numbers.tex` (`\NumDecBnusL`, `\NumDecBnusHours`) |
| Silvergate and Signature: no alarm | `reports/rescue/detector_eval.json` (Coinbase, Bitfinex, Bitstamp-referenced pairs, Mar 2023) |
| USDC moved the token; Chainlink BTC/ETH not contaminated (slope 0.007) | `reports/rescue/monitor.json` (SVB token flag); `reports/audit/usdc_2023_pilot.json` |

## Positioning

- **Flowerday et al. (2026)** use BTC only, through mid-2021, and state that they do not structurally decompose the Bitfinex premium. We do that decomposition, validate it on held-out assets, and extend it to 2023.
- **Makarov & Schoar (2020)** find a common component across countries. We identify the component *within* USD, per exchange and per hour, and use it to correct prices and to monitor them.

## Dropped from v2

- "Eight weeks before the USDT premium": Bitfinex's USDT/USD market only opened on 2018-11-27, so the comparison is invalid.
- "Three days before the deposit freeze was reported": this depends on the threshold.
- The "88% index error" figure: a cross-exchange median does most of that.
