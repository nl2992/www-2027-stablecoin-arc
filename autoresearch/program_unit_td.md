# autoresearch: unit-aware truth discovery (UNIT-TD)

This program has the same shape as karpathy/autoresearch:
- one fixed harness, the equivalent of `prepare.py`;
- one file the agent edits, the equivalent of `train.py`;
- one dev metric;
- keep or discard through git;
- a results log;
- a locked test split that the loop never sees.

## Claim the benchmark tests

A venue's USD prices share a venue-specific unit term, the exchange-dollar rate. If that rate is estimated from some assets, it should remove the cross-venue gap of an asset the estimator **never saw**. A venue with no separate dollar should get no correction.

## Data (built by the harness; read-only)

The panel is hourly, built from hour closes, for 2017-01..2023-12.
- **Bitfinex and Coinbase:** BTC, ETH, LTC, BCH, ETC, XRP, XLM, LINK, SOL, DOGE and ADA in USD.
- **Bitstamp:** BTC and ETH.
- **Extra Bitfinex feeds:** USDT/USD and ETH/BTC.

The minute files are reduced to the last traded close in each hour, so that they line up with the hourly candles.

## Splits

| | Assets scored | Assets visible to the estimator |
|---|---|---|
| **dev** (loop) | ETH, LTC, BCH, ETC, XLM | BTC plus the dev assets, never the scored asset itself |
| **test** (locked, run once) | XRP, LINK, SOL, DOGE, ADA | BTC plus the dev assets: the same information set as dev |

In dev mode the harness never loads the test assets at all.

## Interface (`src/www_auto/estimator.py`, the only file the loop edits)

```
estimate_units(panel: dict[venue -> DataFrame[asset log prices, volumes]], numeraire_venue: str) -> DataFrame[venue -> unit offset in bps]
```

The estimator must satisfy three rules:
- **Causal:** row t uses rows at or before t only.
- **Venue-agnostic:** no hard-coded venue names, and no trusted source.
- **Pure:** numpy and pandas only. It may smooth over time, weight by volume, use robust statistics, use state-space filters, or use the extra feeds.

## Metric (printed by `uv run python -m www_auto.harness`)

- `dev_score`: the share of the held-out mean-square gap that the correction removes, 1 − Σ(g − û)² / Σg², pooled over dev assets and hours. It is computed for the pair (Bitfinex, Coinbase), where the asset's own data is excluded from û.
- `control_score`: the same quantity for a pair with no separate dollar after 2018, Coinbase vs Bitstamp on ETH, over 2019–2023.
- `checks`:
  - `causal_ok`: outputs on random truncations match.
  - `perm_ok`: relabelling the venues permutes the outputs and nothing else.
  - `coverage_ok`: at least 99% of evaluable hours are scored.
- Also printed: per-year scores, `runtime_s` and the baselines (b0 no correction, b1 same-hour BTC gap, b2 same-hour median of visible-asset gaps).

## Keep / discard

Keep a change only if every check passes, `control_score` ≥ −0.02, and `dev_score` improves by at least 0.002. On equal scores, keep the simpler code.

## Loop

The loop is bounded, unlike upstream's "never stop".
1. Branch `autoresearch/unit-td`.
2. Make one idea per commit.
3. Run the harness and append `commit, dev_score, control_score, checks, status, description` to `autoresearch/results_unit_td.tsv` (untracked).
4. Keep, or `git reset --hard` to the last kept commit (on this branch only).
5. Stop after 20 iterations or 3 hours. The final test run is done once, by the author's session, not by the loop.

## Reported outside the loop (not optimized)

- **T2:** fusion under injected unit bias. This is a breakdown-point curve for the median, CRH-style source weighting and the unit-aware estimator.
- **T3:** stress-window index error with Bitfinex unit-corrected rather than dropped. Compare with `docs/review/INDEX_REPAIR.md`.
- **T4:** a unit diagnostic per venue-year, which tells which venues have their own dollar and when.
