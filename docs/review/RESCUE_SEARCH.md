# Rescue search: brute-forcing directions, autoresearch-style (2026-10-12)

**User request (2026-10-12):** "brainstorm how we can save it, can we brute force it with different methods, in the spirit of the skill — and then find something that works." Anonymity is deprioritised by the user for now.

## Rules of the search: what keeps brute force honest

The autoresearch analogue is *propose → run → score → keep or discard → log everything*. Two changes keep it scientific.

1. **"Works" is scored on defensibility, not on significance.** Each direction gets a pilot and a fixed set of kill criteria:
   - **K1 (signal):** the effect is visible in raw data, well above the price tick and venue noise, without any model fitting.
   - **K2 (novelty):** no closest-work paper found that already reports it (search logged).
   - **K3 (Web relevance):** a clear Web or platform angle that fits *Web Economics*.
   - **K4 (data):** free, already-authorized sources; checksum-verified.
   - **K5 (replication):** a second case, venue or held-out period exists in which the same pattern can be checked once, without retuning.
2. **Every pilot is logged here, including failures** (the `results.tsv` analogue, but tracked so a reader can see the whole search). Directions chosen after the search are labelled *exploratory, post-search* in the paper, and the number of directions tried is reported.

## Ledger

| # | Direction | Pilot | K1 | K2 | K3 | K4 | K5 | Status |
|---|---|---|---|---|---|---|---|---|
| R1 | **Calendar and rail-hours effect in calm periods.** Do peg deviations last longer when bank rails are closed (weekends, off-hours)? | Binance.US USDC and USDT, 2019-09 to 2023-06, minute data. Share of minutes with \|D\| ≥ 10 and ≥ 25 bps, and excursion durations, split into business hours, off-hours and weekends. | ✗ The differences are small and change sign from year to year. Excursion medians are 2–4.5 minutes in every regime. Only stress years (2020, 2023) show weekend tails. | partial (industry notes on weekend volatility) | ✓ | ✓ | — | **DISCARD** as a headline. Possible supporting fact: rails matter in stress, not in calm periods. |
| R2 | **Platform-dollar dislocation: Binance.US loses its USD banking (June 2023).** What is a platform's internal "USD" ledger balance worth once its bank link is cut? | Binance.US USDTUSD versus the Bitstamp USDTUSD external reference, daily medians, May–June 2023 | ✓ Strong. Binance.US daily medians: +193 bps on 06-07 (two days after the SEC suit); +85 to +152 bps on 06-13 to 06-16 (withdrawal-halt window); then **−217 to −476 bps on 06-22 to 06-30**. Bitstamp stayed within ±11 bps throughout. | ✓ News coverage only; no study found (search logged) | ✓✓ platform-issued money and Web-platform balances; the "exit right" of a Web wallet | ✓ (same free sources) | Restoration in 2025-02 (does the gap close?); USDC on the same venue; BTC triangle (is it the platform USD or the token that is mispriced?) | **PURSUE**: full path being acquired |
| R3 | **Unit-of-account pass-through.** How fast does a stablecoin's depeg propagate into every pair quoted in it? | Planned: SVB, using BTC/USDC versus BTC/USD | ? | partial (press reports on BTC in USDC terms) | ✓ (Web price feeds and oracles) | ✓ | 4 events | **QUEUED** as a supporting measurement for the existing results |
| R4 | **Web price-feed bias.** Aggregators that treat USDT or USDC as $1 misprice every asset by D during depegs. | Analytical (bias = D), so it adds nothing beyond D | — | ✗ trivial | ✓ | ✓ | — | **DISCARD** as a contribution; one sentence of motivation at most |
| R5 | **On-chain capacity as a leading indicator** | Pre-empted by CurveMetrics (arXiv:2306.10612) | — | ✗ | ✓ | ✓ | — | **DISCARD**; capacity stays as measurement |
| R6 | **Platform fiat-rail shocks beyond Binance.US:** Binance.com GBP (Paysafe, 2023) and EUR (Paysafe, 2023-09), compared with a free official FX reference (ECB daily rates) | Not yet run | ? | ? | ✓✓ | needs approval for the ECB data (a new free official source) | serves as R2's replication set | **CANDIDATE**: run after R2 if R2 holds |

## Current pick

**R2 + R6: "When the platform dollar breaks."** The core is a natural experiment on Web-platform money. It turns the existing multi-event machinery and the A2 "rail impairment" (previously treated as a data artifact) into the main object of study. The existing stablecoin multi-event results become context: in token depegs the token breaks, whereas in rail cuts the platform's dollar breaks. The verdict is pending the full 2023–2025 path and the triangle check.

## R2 pilot result (2026-10-12; phase boundaries fixed in `src/www_rescue/platform_dollar.py` before computing)

PD = log price on Binance.US in platform USD − log price on Bitstamp in external USD, in bps. Phase medians with hour-block bootstrap 95% intervals:

| Phase | PD_USDT | PD_BTC | USDT vs BTC: hourly corr; median gap |
|---|---|---|---|
| pre (05-01 to 06-04) | 7.1 [6.0, 8.4] | 5.7 [5.0, 6.4] | 0.999; 0.2 |
| SEC complaint (06-05 to 06-08) | 20.5 [15.2, 33.1] | 22.1 [16.1, 41.8] | 0.981; −0.6 |
| deposits suspended (06-09 to 06-12) | 17.1 [10.6, 27.9] | 27.9 [21.8, 39.5] | 0.873; −10.6 |
| withdrawal-halt window (06-13 to 06-21) | 63.8 [48.9, 79.2] | 54.0 [45.4, 70.8] | 0.991; −0.2 |
| crypto-only transition (06-22 to 07-31) | **−600.6 [−644.2, −525.7]** | **−533.5 [−596.4, −507.5]** | 0.9996; −2.1 |

Within-venue triangle (BTC/USD vs BTC/USDT × USDT/USD): |median| ≤ 3 bps in every phase.

**Reading.** The platform's USD ledger, not the tokens, was mispriced: two unrelated assets carry the same dislocation. The sign tracks which gate was open:
- When **exit** was threatened, platform USD sat at a discount (PD > 0).
- When **entry** (deposits) was closed but exit stayed open, platform USD traded at a premium of about 5–6% (PD < 0). No inflow could arbitrage it, while crypto holders needed platform USD to reach a bank.

The pilot used a scratch loader for the Bitstamp months not yet in the manifest. The committed run uses the verified loader.

## R6 predictions, recorded BEFORE any R6 data is downloaded or inspected

Same definitions and code, with fiat F ∈ {GBP, EUR} on Binance.com. PD_X^F = log P_Binance(X/F) − log P_external(X/F), with X ∈ {USDT, BTC}; the external venue is Bitstamp.

- **P1 (GBP, Paysafe, all users suspended 2023-05-22; deposits and withdrawals both stopped):** after 05-22, PD^GBP > 0 (platform GBP at a discount), with |median| ≥ 25 bps over the following 4 weeks; USDT and BTC agree (hourly corr ≥ 0.9).
- **P2 (EUR, Paysafe users, from 2023-09-25):** same sign as P1, but smaller than GBP, because other EUR rails remained for some users.
- **P3 (directional gate):** where deposits close before withdrawals (Binance.US only), PD flips negative.
- **Falsification:** |median PD| < 10 bps after the suspension, or USDT and BTC disagreeing (corr < 0.5), counts against the platform-ledger interpretation for that case.

## R6 result (2026-10-12; verified data; `reports/rescue/fiat_rail.json`)

| Case | PD_USDT pre → post-4w → later (bps) | PD_BTC pre → post-4w → later | USDT–BTC hourly corr (post) | Pre-recorded verdict |
|---|---|---|---|---|
| GBP (05-22) | 30.3 → 37.8 → 34.6 | 29.5 → 33.2 → 32.6 | 0.97 | SUPPORTED (level ≥ 10 bps, positive) |
| EUR (09-25) | 16.6 → 10.6 → 8.9 | 15.3 → 9.0 → 4.2 | 0.92 | SUPPORTED (level ≥ 10 bps, positive) |

**Honest reading.** The pre-recorded rule tested the *level* after the cut, not the *change*. That was a design flaw: both venues already carried a positive basis before the cut. The rule is not changed after the fact; the substantive reading is stated here instead:
- **GBP:** a small rise (+7.5 bps for USDT, +3.7 bps for BTC) on top of a 30 bps pre-existing discount. New-user GBP rails had already been cut on 2023-03-13, so the "pre" window was partly treated.
- **EUR:** the gap **shrank** after the cut, the opposite of P2.
- USDT and BTC agree in both cases (corr ≥ 0.9), so the basis belongs to the platform's fiat ledger, not to the tokens. But the rail cut itself produced **nothing comparable** to Binance.US (50–600 bps).
- **P3 (directional gate)** cannot be tested on GBP or EUR, because deposits and withdrawals closed together.

**R2 robustness, within case.** After USD rails were restored on 2025-02-19, PD fell to −2.2 bps [−2.8, −1.7] for USDT and 0.0 bps [−2.2, 1.7] for BTC. The Binance.US dislocation appears with the rail cut and disappears with the restoration.

## Verdict of the rescue search (2026-10-12)

- **R2 is real, large, identified and reversible** on one platform:
  - USDT and BTC agree (identification);
  - the sign follows which gate was open;
  - the gap closes on restoration.
- **R6 does not replicate the magnitude** on the two other platform-fiat cuts (substantive null; formal pass under a flawed rule, disclosed).
- **Defensible claim:** a documented natural experiment, plus a decomposition method that tells token failures from ledger failures. It is not a general law of rail cuts. The "one-way gate" explanation for why Binance.US differs is a hypothesis: it fits the Binance.US sign flip, but GBP and EUR cannot test it.
- **Recommendation:** pivot the paper to "Which dollar broke?". The decomposition is the method. Token failures come from the pre-registered multi-event study; ledger failures from Binance.US, with GBP and EUR as honest small-effect cases. The search history (R1–R6, including discards and the flawed rule) is disclosed in the paper.
