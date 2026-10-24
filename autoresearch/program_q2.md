# Q2: early detection of stablecoin unit shifts from pooled cross-market offsets (pre-registration)

Written 2026-10-23, before any Q2 detector was computed. No detector has been run on any event. Nothing here is tuned after results.

## Question

When a stablecoin depegs, does pooling the unit offset across every market and asset quoted in that stablecoin detect the shift earlier than the single-pair rules a monitor would use, at the same false-alarm rate?

## Events and onset labels

| ID | Unit | Window (UTC) | Source (already held) |
|---|---|---|---|
| E1 | USDT | 2018-11-27 .. 2018-12-31 | Q1 panel (Q-E2) |
| E2 | USDT | 2019-04-20 .. 2019-05-31 | Q1 panel (Q-E3) |
| E3 | USDT | 2020-03-09 .. 2020-03-31 | Q1 panel (Q-E4) |
| E4 | USDC | 2023-03-08 .. 2023-03-20 | STABLE panel (X1) |
| E5 | TUSD | 2024-01-01 .. 2024-01-31 | STABLE panel (X2) |
| E6 | FDUSD | 2025-04-01 .. 2025-04-30 | STABLE panel (X3) |

- **Onset (the label):** the first hour in the window at which the stablecoin's deviation from the U.S. dollar has |deviation| ≥ 50 bps for 3 consecutive hours. The deviation is measured from the label source.
- **Label source** (never Kraken): the Q1 gate source order. That is Binance.US or Bitstamp stablecoin/USD where they exist; else the Bitfinex netted anchor T = D − L; else the stablecoin/USDT rate chained with USDT/USD from those sources.
- **Unscorable events:** if an event has no label source, or never reaches the onset rule, it is reported as unscorable and dropped. That decision is made from the label series alone, before any detector runs.
- **Detectors never see the label source series.**

## Detectors

All detectors are causal and hourly, and use the panel conventions of `www_stable` / `www_q1`.

- **P (pooled, the proposed rule):** for unit k, the offset is the median, over every (market in unit k, asset ∈ {BTC, ETH}) pair, of the gap to the median of the USD-venue prices of that asset. It is smoothed by an EWMA with a span of 3 hours. Alarm when |offset| ≥ τ_P.
- **S1 (single pair, threshold):** the BTC gap between the highest-volume market in unit k and the USD-venue median. Alarm when |gap| ≥ τ_S1.
- **S2 (single pair, CUSUM):** a two-sided CUSUM on the same single-pair gap, with reference value 5 bps. Alarm when the statistic ≥ h_S2.

## Calibration (fixed now)

- Each threshold (τ_P, τ_S1, h_S2) is set so the detector raises **1 false alarm per 1,000 calm hours**.
- **Calm hours:** the 30 days before each event window, excluding any hour within 7 days of another event, pooled across events.
- Calibration uses calm hours only and is done once, before any event is scored.

## Metrics

- **Lead time:** first alarm hour minus onset hour; negative means early. Only alarms within onset − 72 h to onset + 72 h count. Otherwise the event is a miss.
- **Per detector:** the median lead over scored events, the number of misses, and the false alarms per 1,000 calm hours realised (as calibrated).
- **Uncertainty:** an event-level bootstrap (1,000 draws, seed 20261023) for the median-lead difference P − S1 and P − S2.

## Success rule (stated now)

P succeeds against a comparator if its median lead is earlier, with the bootstrap 95% upper bound of (P − comparator) below 0, and it has no more misses. A tie (the interval includes 0) is reported as a tie. A loss is reported as a loss. There is no retuning.

## Data

All data is already held: the Q1 and STABLE panels and their raw files. No downloads.
