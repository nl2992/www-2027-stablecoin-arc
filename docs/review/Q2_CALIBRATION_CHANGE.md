# Q2 calibration change after scoring (disclosure)

- `bfa5c8b` (2026-10-23 20:30) scored events with the original calibration: the smallest threshold whose pooled calm-hour episode count stays within the cap.
- `55b50ed` (20:34) corrected the rule. Episode counts are not monotone in the threshold (a tiny threshold gives one long run), so the threshold is now the smallest one for which every higher threshold also stays within the cap. The correction uses calm hours only.

| | tau_P (bps) | P misses | P median lead (h) | Outcome vs S1 | Outcome vs S2 |
|---|---|---|---|---|---|
| Original (`bfa5c8b`) | 162.3 | 2 | 0.5 | tie | tie |
| Corrected (`55b50ed`, reported) | 445.3 | 4 | 72.0 | tie | tie |

Both versions meet the pre-registered false-alarm target (4 false alarms in 4,320 calm hours). The correction made the pooled detector worse, not better. Values are from `git show <commit>:reports/q2/results.json` and `calibration.json`.
