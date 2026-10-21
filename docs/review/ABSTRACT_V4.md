# Abstract v4 (draft, 2026-10-20): web data fusion with source-specific units

**Working title:** Same Name, Different Unit: Identifying Source-Specific Units in Web Price Fusion

Web services that fuse prices from many sources assume the sources quote in one unit. The assumption fails when a source's nominal unit is a claim on the source itself, such as a balance on a platform's ledger, whose value can drift from the unit it is named after. Fusion then reports the drift as a price change, and per-source reliability weights and robust aggregation cannot tell the two apart. Detection is hard: a source's unit is never quoted, and any item can move for its own reasons. We model each source's prices as true prices plus a unit offset shared by all its items. Agreement across unrelated items identifies the offset, and a unit anchor, an item whose value is fixed in the true unit, separates a unit shift from source-wide demand for the items. We test the approach on cryptocurrency exchanges, whose dollar balances are ledger claims, with public hourly prices from 2017 to 2023. On assets withheld from development, one offset per source-hour removed {TEST}% of cross-source price gaps pooled and {YMIN}% to {YMAX}% in each year from 2020, and it applied no correction between sources that shared a unit. The anchor, the dollar stablecoin USDT, followed the exchange's offset one for one on Binance.US in 2023 (slope {BNUS_SLOPE}) and carried {STRESS_SLOPE_PCT}% of it on Bitfinex in 2018 and 2019 (95% interval {LO}% to {HI}%), which a gap driven only by crypto demand would not produce. A monitor built on the offsets flagged unit failures at a third of the false-alarm rate of a plain price-gap rule at equal recall, and in 2023 it separated an exchange's dollar failure from a stablecoin run. The approach applies wherever web sources quote in units that share a name but not a backing, and it lets price feeds state which unit each price is in.

---

**Placeholders**, all filled by macros:
- `{TEST}`, `{YMIN}`, `{YMAX}`: the held-out results (`\NumUTestPct`, `\NumUTestYearMinPct`, `\NumUTestYearMaxPct`).
- `{BNUS_SLOPE}`: `\NumUAnchorBnusSlope` (1.00).
- `{STRESS_SLOPE_PCT}`, `{LO}`, `{HI}`: `\NumUAnchorStressSlope` and its interval (0.71 [0.56, 0.88]), shown as percentages. Add percent macros.

**What changed from v3:**
- It opens with the general web-fusion problem.
- The method is stated generally: offset, agreement across items, and the anchor.
- Crypto appears as the test domain.
- There are four numeric results instead of about 12, with exchange names only where a result needs them.
- The anchor test answers the main identification objection. Binance.US passes fully. On Bitfinex, USDT carried 71% of the gap, which rules out a demand-only explanation but not a minority demand component.
- The Silvergate/Signature, Chainlink and 6.5-month details move to the body.
