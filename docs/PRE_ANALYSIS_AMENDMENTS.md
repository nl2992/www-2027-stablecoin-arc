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

## A3 — 2026-10-11 (UTC), section 5, USD venue priority (written **before** any Bitstamp data were analysed)

**Change.** The USD leg comes from a fixed priority order. First choice is Binance.US, the anchor's venue family, for any span that amendment A2 does not mark as impaired. The fallback is Bitstamp, used only when A2 excludes Binance.US. A result computed on any non-designated venue is a **robustness check**. It is written to `reports/events/<id>_robustness_<venue>.json`, reported alongside the primary result, and **never changes registry status or confirmatory counts**.

Consequences:
- June 2023 USDT and TUSD (January 2024) use Bitstamp as their designated USD venue, because A2 excludes Binance.US.
- FTX-period USDT keeps Binance.US as its designated venue (not impaired), so its R1 rejection stands. A Bitstamp run of FTX is robustness only.
- UST, the BUSD placebo, FDUSD and USDe keep Binance.US.

**Reason.** With two USD venues available, choosing between them after seeing results would allow venue shopping. This order follows from A2 and the plan's existing preference for the anchor's venue family. It is fixed before any Bitstamp-based measurement.

**Data seen.** Bitstamp archives were downloaded but **not analysed** when this was written. Earlier Binance.US results for all events had been seen (see A2).

## A4 — 2026-10-11 (UTC), sections 1 and 2, UST series continuation (written **before** any USTC data were acquired or measured; user-approved pre-registration)

**Rule.** The UST event series is built from Binance USTUSDT up to and including its last published minute (2022-05-13 00:49 UTC). From the first minute after that, it continues with Binance USTCBUSD, converted to USD as USTC/BUSD × BUSD/USDT (Binance) × USDT/USD (Binance.US, which is valid under A2 in 2022). A minute counts as traded only if every leg in use traded. Minutes between the two series stay missing; they are never interpolated. R1, R3 coverage and DV1–DV5 are then computed on this spliced series exactly as for every other event. Within-venue triangle measures (DV4, DV5) use only the pre-delisting BTCUST leg, and are undefined where it is absent.

**Preconditions,** checked from documentation and listing metadata before any price is read:
- (a) Binance documentation identifies USTC as the same Terra token previously listed as UST.
- (b) The USTCBUSD series starts at or after the USTUSDT series ends.
- (c) BUSDUSDT and Binance.US USDTUSD cover the recovery window.

If any precondition fails, the splice is not used and UST is recorded as not acceptable under R3. The decision is logged either way.

**Data seen.** USTUSDT through 2022-05-13 00:49 had been measured (status DATA_VERIFIED, recovery coverage 0%). No USTC, BUSDUSDT-2022-05 or spliced-series price had been acquired or analysed. Listing metadata showing USTCBUSD files from 2022-05 had been seen. Execution waits for independent review of the Phase 0 audit.

## A5 — 2026-10-11 (UTC), sections 1 and 2, UST continuation via UST/BUSD (**approved by the user after inspection of coverage, not prices**)

**Rule.** This replaces A4's continuation instrument. The UST series is Binance USTUSDT up to its last minute (2022-05-13 00:49 UTC), then Binance **USTBUSD** from its first minute after that. That pair is the same token under its original ticker; per Binance, it reopened against BUSD at about 14:30 UTC on 2022-05-13. Prices are converted to USD as UST/BUSD × BUSD/USDT (Binance) × USDT/USD (Binance.US, valid under A2 in 2022). A minute counts as traded only if every leg in use traded. The gap between the two segments stays missing. The registered event windows are unchanged.

**Why A4 was insufficient.** The A4 continuation (USTC/BUSD) opened on 2022-05-30 09:30 UTC, after the registered recovery window (May 14–20) had ended. Under A4 the recovery window had 0 covered minutes.

**Classification.** UST's event-window severity (R1 pass, from the USTUSDT segment) had already been measured when A5 was written. A5 only adds recovery-window coverage. UST is therefore labelled **EXPLORATORY (post-hoc eligibility)** and excluded from confirmatory H1 counts. Cross-event summaries are reported both with and without it.

**Data seen.** Seen: listing metadata and minute coverage for USTBUSD (2022-05-01 → 2022-05-26 14:59, including a 361-minute halt ending 2022-05-13 14:30), plus UST's earlier event-window results. **No** USTBUSD-based recovery-window values had been computed.

## A6 — 2026-10-11 (UTC), sections 1–3, systematic in-sample event screen (written **before** any screen data were downloaded or read)

**Purpose.** No accepted confirmatory in-sample event exists. Every in-sample registry candidate came from news selection and was either rejected, made exploratory, or lacks data. A rule-based screen discovers episodes without news selection, and it reports false positives and non-detections too.

**Universe.** Binance.US USD-quoted stablecoin pairs USDCUSD, USDTUSD, DAIUSD and TUSDUSD: every monthly 1-minute archive from the first available month through **2023-05**. That is the period before the A2 USD-rail impairment, entirely before the 2024 out-of-sample boundary. Archives must pass their published checksums. No other venue or pair is screened.

**Detection.**
1. Apply R1 unchanged to each series: at least 30 traded minutes with \|log deviation\| ≥ 100 bps within a rolling 24 h window.
2. A detection is a maximal run of breaching minutes belonging to R1-satisfying windows. Detections of the same coin less than 14 days apart are merged (R2).
3. Episode start and end are the UTC dates of the first and last breaching minute.

**Clustering and matching.**
- Episodes of different coins that overlap, or start within 14 days of each other, form one cluster. The primary is the coin with the largest \|extreme\|.
- A cluster overlapping an existing registry event's reported window ±14 days is assigned to that cluster and adds no new episode.

**Eligibility.**
- New clusters enter the registry as `CANDIDATE` with role `IN_SAMPLE`. R4 still applies: they become `SOURCE_DOCUMENTED` only if at least two independent publishers describe the episode.
- They are then measured by the unchanged batch protocol on the same Binance.US series. They are **confirmatory-eligible**, because this rule precedes the data.
- Detections without sources are reported as **unexplained detections** (possible venue-specific dislocations or data defects) and are never accepted.

**Reporting.** All detections, all clusters, months scanned, coverage per month, and non-detections are written to `reports/events/screen_A6.json`.

**Data seen.** Seen: only archive availability (HEAD requests: month ranges per pair). Previously measured on Binance.US: USDCUSD for March 2023 (the anchor panel) and USDTUSD for 2022-04/05, 2022-10/11, 2023-01/02 and 2023-05/06. No screen detection has been computed.
