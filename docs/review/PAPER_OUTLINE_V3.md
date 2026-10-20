# Paper outline v3 (drives the rewrite of `paper/main.tex`)

**Title:** Which Dollar? Exchange Dollars as Exchange Rates in Web Crypto Prices

**Abstract:** `docs/review/ABSTRACT_V3.md`, verbatim, with every number replaced by its `\Num` macro.

**Limits:** 8 body pages and 12 in total (`www_paper.gate`). Tone: plain, short sentences, results stated positively and precisely. Write no defensive "limitations-as-virtue" passages; state each limitation once, factually, in the Discussion.

## 1. Introduction (about 1 page)

- **Hook:** web price feeds quote "USD" across exchanges whose dollars differ. Use one concrete example, Bitfinex.
- **Problem:** an exchange's dollar is never quoted directly, and any single asset can move for its own reasons.
- **Idea:** a dollar shift moves every asset on the exchange equally. Cross-asset agreement identifies it, and triangular parity checks it.
- **Contributions,** four bullets:
  1. an hourly unit/asset decomposition;
  2. evidence that Bitfinex's dollar carried its own exchange rate in every year 2017–2023, while Coinbase and Bitstamp did not after 2018;
  3. a held-out benchmark in which one rate per exchange-hour removes 85% of gaps on assets withheld from development;
  4. a monitor with a fixed rule, its false-alarm rate, and the 2023 episodes (Binance.US, Silvergate/Signature, USDC with the Chainlink check).
- **Figure 1:** `unit_rate.pdf`.

## 2. Related work (about 0.6 page)

- **Cross-exchange premia:**
  - Makarov & Schoar 2020 found a common component across countries. We identify it within USD, per exchange and per hour.
  - Flowerday et al. 2026 used BTC only, through mid-2021, and say explicitly that they do not structurally decompose the Bitfinex premium.
  - Choi et al. (the Kimchi premium), Borri & Shakhnov, and Guo et al.
- **Stablecoins:** Lyons & Viswanath-Natraj; Ma, Zeng & Zhang; Liu, Makarov & Schoar; Griffin & Shams.
- **Truth discovery and data fusion on the web:** TruthFinder, CRH, and Dong et al. on source dependence. They model per-source reliability, not a unit bias shared across a source's claims. Our setting is a structured case of that.
- **Oracles and aggregator data quality:** Liu & Szalachowski; Nadler, Schuler & Schär 2026, who benchmark against single venues; and Schwenkler et al.

## 3. Decomposition (about 1 page)

- **Model:** p_{v,a,t} = p*_{a,t} + u_{v,t} + e_{v,a,t}. The gap between venues v and r is g_{a,t} = (u_v − u_r) + (e_v − e_r).
- **Identification:**
  - Agreement across assets that share no peg (BTC, ETH and altcoins).
  - Triangular parity (ETH/BTC) as a check.
  - For a stablecoin, the token component is the stablecoin price minus the unit.
- **Estimator:** the same-hour cross-asset median, with shrinkage toward 0 by cross-asset dispersion (James–Stein style). Explain why it is causal and venue-agnostic.
- **The autoresearch loop:** 12 iterations against a fixed harness. Smoothing, Kalman filtering and reliability or liquidity weighting did not help, because the unit moves hour to hour. That is a finding about the object, not a weakness. One paragraph.

## 4. Data (about 0.5 page)

- **Coverage:** public minute candles for BTC and ETH on Bitfinex, Coinbase and Bitstamp, 2017–2023. Hourly candles for 9 more assets. Binance.US 2022–2025.
- **Integrity:** manifests with hashes; free and unauthenticated sources only; rebuild scripts.
- **Labels:** 33 rail episodes compiled from dated public sources, blind to prices (`configs/fiat_rail_labels.json`).

## 5. Results

### 5.1 Which exchanges have their own dollar

- Table `unit_diagnostic_table`.
- Bitfinex in every year. Coinbase vs Bitstamp only in 2017.

### 5.2 Held-out-asset benchmark

- Table `heldout_table`.
- The protocol: leave-one-asset-out scoring, a locked test set of 5 assets run once, the control pair, and the causal, permutation and static checks.
- Results: 85% pooled; 99% in 2019 and 30–45% in calm years; 0 false correction on the control.

### 5.3 Monitoring

- Table `detector_eval_table`: the rule fixed in advance; 0.43 vs 1.29 false alarms per venue-year at equal recall; Coinbase silent after 2018.
- **Timeline:** Bitfinex flagged from October 2018, 6.5 months before the NYAG disclosure.

### 5.4 Three shocks in 2023

- **Binance.US:** the dollar sat a median 557 bps away for 530 hours. Reuse the existing ledger-phase or decomposition table, but only if space allows.
- **Silvergate and Signature:** no alarm.
- **USDC:** the token moved, not an exchange dollar. Chainlink BTC and ETH feeds were not contaminated (`oracle_pilot_table`), which is the robustness section.

## 6. Discussion (about 0.4 page)

- **What price feeds should do:** label each price's unit and correct with the unit rate rather than dropping venues.
- **Limits:**
  - three USD venues;
  - few positive episodes;
  - the stablecoin exit route is not modelled;
  - Pyth and CryptoCompare need accounts.

## 7. Reproducibility (short)

## Appendix

- The T2 breakdown table.
- The label list.
- The 2017 detector windows, described neutrally.

## Remove from the body

These belong to the old stablecoin-capacity study:
- the on-chain capacity section;
- the token multi-event pre-registered study;
- the executable-capacity appendix.

Drop them from `main.tex`, and update the inclusion tests in `tests/test_paper.py` accordingly. Keep the freshness tests for the files that are still generated, but stop requiring their inclusion.
