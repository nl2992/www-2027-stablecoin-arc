# Abstract polish pass (2026-10-18)

**Procedure:** `paper-polish` and the pre-submission-reviewer five-sentence abstract formula from HKUSTDial/Supervisor-Skills, then the `humanizer` skill (blader/humanizer, commit `8c307f3`). Skill text is not copied here. The edit is in `paper/main.tex`; `docs/review/ABSTRACT_SUBMISSION.md` is regenerated from it (273 to 286 words).

## Language edits (meaning unchanged)

- The 70-word Binance.US sentence is split into three: attribution, the discount/premium phases, and the robustness checks.
- The method sentence is split so the acceptance conditions (assets agree, cross-rates hold) stand on their own.
- "June–July 2023" becomes "in June 2023"; the abstract now has no en or em dashes.
- The closing sentence that packed three limitations is split; "came from a disclosed search" now says explicitly that the ledger analysis was not pre-registered.

## Edits that touch meaning (author to confirm)

| Before | After | Why |
|---|---|---|
| "When a dollar price dislocates, either the token or the ledger has failed." | "When a dollar price moves away from par, users, price feeds and oracles need to know which of the two failed" | The original asserts the dichotomy is exhaustive; the new wording states the question without claiming that. |
| "flags ledger failure in 67.7% of rail-cut hours ... across 9 threshold settings" | "67.7% of rail-cut hours (in sample; 56 to 76% across 9 threshold settings)" | §6 says the rail-cut rate is in-sample; the old wording also implied 67.7% held at every setting. |
| (absent) | "in 1.1% of calm hours" | The calm-period rate is what §6 calls one of the informative numbers. Taken from `\NumMonCalmLedger`. |
