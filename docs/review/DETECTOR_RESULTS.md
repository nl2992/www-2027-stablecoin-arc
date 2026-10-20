# Detector evaluation: results (2026-10-20)

- **Design:** `docs/review/DETECTOR_PREREG.md`, including amendment D1. Both were committed before this run (`7459c5a`, `265f6ee`).
- **Code:** `src/www_rescue/detector_eval.py`.
- **Outputs:** `reports/rescue/detector_eval.json`, plus the signs of the alarm episodes in `reports/rescue/detector_episode_signs.json`. The signs were added after the run and are descriptive only.
- **Data:** 528 newly verified public candle files (D11). The rule ran unchanged.

## 1. Scored predictions

| | Result | Detail |
|---|---|---|
| **P1** unexplained false alarms ≤ 1 per venue-year, unseen months | **Split** | Bitfinex 0.53 (PASS). Coinbase control 1.26 (FAIL): all 8 alarms fall in 2017-09 to 2018-01. |
| **P2** no more false alarms than the gap-only baseline, at the same or higher recall | **PASS** | Bitfinex 3 vs 9 (recall 7/9 for both). Coinbase 8 vs 20. Binance.US 1 vs 1. |
| **P3** never lags the first report by more than 7 days | **FAIL** (3 cases) | See section 3. |
| **P4** Coinbase alarm-days below 1% of days | **FAIL** | 29 of 2,313 days (1.25%), all in the 2017 bubble. |
| **Falsification** (P1 fails at both venues, or P2 fails) | **Not falsified** | |

## 2. Detector against baselines (all months)

| Venue | Method | Alarm episodes | Recall | False alarms | Per venue-year |
|---|---|---|---|---|---|
| Bitfinex (7.0 yrs) | **detector** | 12 | 7/9 | **3** | **0.43** |
| | B1 gap only | 18 | 7/9 | 9 | 1.29 |
| | B2 robust z | 38 | 9/9 | 20 | 2.88 |
| | B3 USDT premium | 6 | 1/3 | 2 | 0.39 |
| Coinbase (6.3–7.0 yrs) | **detector** | 8 | 0/5 | **8** | **1.26** |
| | B1 | 20 | 0/5 | 20 | 2.86 |
| | B2 | 26 | 3/5 | 24 | 3.45 |
| Binance.US (0.8 yrs) | **detector** | 5 | 4/4 | 1 | 1.31 |
| | B1 | 5 | 4/4 | 1 | 1.26 |

**How to read it:**
- The second-asset agreement test does its job. It keeps the gap-only baseline's recall and removes two-thirds of its false alarms.
- The robust z-score catches everything because it fires constantly.
- The USDT premium, the signal practitioners watched, misses the 2018–19 onset. It first fires on 2018-12-02, eight weeks after the detector (2018-10-08).

## 3. Timing against public reports

| Label | Report | First alarm | Days | Note |
|---|---|---|---|---|
| BFX-2017-01 Wells Fargo wires | 2017-04-09 | 2017-04-12 | +3 | |
| BFX-2017-02 inbound wires refused | 2017-04-18 | 2017-04-12 | −6 | |
| BFX-2018-03 Noble Bank loss | 2018-09-30 | 2018-10-08 | **+8** | P3 violation. The label rests on unconfirmed, secondary reporting. |
| BFX-2018-04 deposits paused | 2018-10-11 | 2018-10-08 | −3 | |
| BUS-2023-01 banking partner loss | 2023-04-09 | 2023-05-08 | **+29** | P3 violation. The report predates any price effect. |
| BUS-2023-02/03 deposits suspended | 2023-06-09 | 2023-06-07 | −2 | |
| BST-2023-01 (reference, matched to Binance.US) | 2023-03-02 | none within ±30 days | | P3 violation. The window was credited through the Binance.US episode; this is an artifact of D1. |
| **Retrospective disclosures** | | | | |
| BFX-2018-02 Crypto Capital withdrawal delays | 2019-04-30 | 2018-10-08 | **−204** | |
| BFX-2018-06 Crypto Capital loss | 2019-04-25 | 2018-11-01 | −175 | |
| BFX-2018-01 withdrawal delays | 2018-02-20 | 2017-12-25 | −57 | **Wrong sign:** L is negative, so Bitfinex BTC was *cheaper*. That is not a discount on the Bitfinex dollar. Do not claim it. |

## 4. What the unseen months add

1. **Specificity holds out of sample.**
   - From 2019-08 to 2023-12, Bitfinex had two one-day alarms: 2019-11-25, and 2022-05-12, the Terra/LUNA crash day.
   - Coinbase, measured against Bitstamp, had **zero alarms from 2018-02 to 2023-12**.
   - This is the clearest new result. Over about 4.5 and 6 calm venue-years respectively, the rule almost never fires.
2. **Not every banking loss moves the ledger dollar.**
   - The March 2023 Silvergate and Signature shutdowns hit Coinbase, Bitstamp and Kraken. They produced no alarm at any monitored pair.
   - A discount appeared only where fiat rails closed with no substitute: Bitfinex in 2017 and 2018, and Binance.US in 2023.
   - So the price measure separates material impairments from headline ones. News flow alone cannot.
3. **The 2017 bubble is the main failure.** The Coinbase alarms (+150 to +360 bps, Sep 2017 to Jan 2018) and Bitfinex's negative-sign alarms (May to July 2017, Nov 2017 to Jan 2018) are not in the label set. They may reflect real USD funding frictions on US venues, such as purchase limits and deposit backlogs. That reading was not pre-registered, so they count as false alarms here.
4. **Out-of-sample recall is not established.**
   - Unseen Bitfinex recall is 1/4. The one catch, BFX-2018-01, has the wrong sign.
   - The other three unseen positives are reference-side Bitstamp labels, which no Bitfinex alarm could have caught.
   - Recall evidence therefore rests on the seen episodes.

## 5. Robustness

- **Leave-one-episode-out:** the grid point chosen on the other episodes is 200 bps, with agreement 0.25 in 17 of 18 folds and 0.5 in one. LOEO recall equals headline recall (11/18).
  - Every held-out Bitfinex and Binance.US rail episode is still caught.
  - The higher threshold delays first alarms by up to 12 days.
  - **The 2018 deposit-pause lead flips from −3 to +3 days.** The "3 days before the report" claim therefore depends on the pre-registered 100 bps level. A threshold tuned on the data would not reproduce it.
- **Coinbase as Bitfinex's reference:** same recall (7/9), but 11 false alarms instead of 3. Bitstamp is the cleaner reference for Bitfinex.
- **High-quality labels only:** Bitfinex caught 5/5, with 6 unexplained alarms (0.86 per venue-year).

## 6. Implications for the paper

- **Claim:**
  - Specificity: about 0.4 false alarms per venue-year at Bitfinex, and none at Coinbase after the 2017 bubble.
  - The detector beats gap-only and z-score baselines on false alarms at equal recall.
  - It leads the USDT-premium signal by eight weeks in 2018.
  - It flagged the Crypto Capital impairment about 6.5 months before disclosure.
  - Silvergate and Signature in 2023 produced no discount.
- **Do not claim:**
  - Out-of-sample recall.
  - A uniform lead time; the detector lagged two reports by 8 and 29 days.
  - A threshold-robust 3-day lead in October 2018.
  - The January 2018 "early warning".
- **Disclose:** the 2017 bubble alarms, and that P3 and P4 failed.
