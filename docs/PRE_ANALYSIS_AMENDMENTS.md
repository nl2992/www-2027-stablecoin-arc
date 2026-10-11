# Pre-analysis plan amendments

Each amendment must give: the date (UTC); the section changed; the reason; and whether any affected data had been seen. The plan file itself stays frozen; record changes here, never in the plan.

## A1 — 2026-10-11 (UTC), section 2, DV3

**Change.** The trailing 6-hour median that decides recovery is computed only over traded minutes from the event-window extreme onward, i.e. over (max(t − 6h, t_extreme), t].

**Reason.** The plan says DV3 is "computed forward from the extreme using trailing data only" but does not say whether pre-extreme minutes may enter the trailing window. If they do, calm minutes before the extreme can make recovery look instantaneous. A synthetic test showed recovery registering one minute after the extreme. The clipped definition matches the stated intent and still uses no future data.

**Data seen.** No non-anchor event data had been acquired or measured. The anchor (exploratory) had not been re-run under DV3 when this amendment was made.
