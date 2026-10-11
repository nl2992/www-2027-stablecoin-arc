# Panel audit specification

The command `python -m www_c0.audit` emits `reports/c0/panel_quality.json`. It hashes the exact input parquet and checks timestamp timezone, ordering, uniqueness, minute alignment, expected study-window coverage, row counts, positive prices, non-null coverage and trade-activity diagnostics. Each `*_volume` field reports zero-volume minutes and age since the last positive-volume minute. This is deliberately named an activity proxy, not quote staleness.

The flat panel schema has one row per timestamp and no separate asset/venue key. Available instrument columns are enumerated in `DATA_DICTIONARY.md`; missing instrument columns are therefore visible from the column inventory, while duplicate timestamps are rejected. A source-frequency mismatch is flagged through minute-alignment and gap checks. The upstream artifact has no fill-provenance flags, so forward-filled values cannot be reliably detected from the parquet alone; source-code behavior is documented in `docs/iaqf_audit.md`.

`validation.invalid_prices_pass` and `validation.expected_grid_complete` distinguish passed checks from detected issues. The overall `status: AUDITED` means the diagnostics ran, not that every check passed. A missing input returns `NOT_AVAILABLE` without fabricating measurements.
