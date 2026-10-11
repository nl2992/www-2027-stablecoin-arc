# Pre-analysis plan amendments

Each amendment must give: the date (UTC); the section changed; the reason; and whether any affected data had been seen. The plan file itself stays frozen; record changes here, never in the plan.

## A1 — 2026-10-11 (UTC), section 2, DV3

**Change.** The trailing 6-hour median that decides recovery is computed only over traded minutes from the event-window extreme onward, i.e. over (max(t − 6h, t_extreme), t].

**Reason.** The plan says DV3 is "computed forward from the extreme using trailing data only" but does not say whether pre-extreme minutes may enter the trailing window. If they do, calm minutes before the extreme can make recovery look instantaneous. A synthetic test showed recovery registering one minute after the extreme. The clipped definition matches the stated intent and still uses no future data.

**Data seen.** No non-anchor event data had been acquired or measured. The anchor (exploratory) had not been re-run under DV3 when this amendment was made.

## A2 — 2026-10-11 (UTC), section 5, validity of the USD leg (**made after seeing data**)

**Change.** A USD price, whether it is the stablecoin's own USD-quoted series or the USDT/USD reference leg, counts as USD only if the venue's USD was depositable and withdrawable throughout the event's control-to-recovery span. Documented impairment periods are listed, with sources, in `configs/usd_rail_impairments.json`. If the span overlaps an impairment, the event is not confirmatory-eligible and cannot be `ACCEPTED`; it is recorded as `DATA_VERIFIED`. Currently listed: Binance.US, 2023-06-09 → 2025-02-19 (USD deposits suspended, then restored).

**Reason.** The first batch run measured the June 2023 USDT candidate on Binance.US USDT/USD. It produced a +361 bps USDT *premium* that breached continuously from 2023-06-14. Reports of the June 2023 Curve event describe a small USDT *discount*. The sign, size and timing instead match the documented suspension of Binance.US USD services from 2023-06-09: that venue's "USD" was no longer redeemable dollars. The frozen plan's USDT-stability gate does not cover an impaired USD leg.

**Data seen.** Yes. This amendment was written **after** the batch run of 2026-10-11 18:02 UTC, prompted by the June 2023 result. It is applied mechanically to every event, and it can only remove eligibility, never add it. Status changes it causes are logged in `reports/events/status_log.json`, and the paper reports results both before and after A2.
