"""Bounded-memory reader for Tardis normalized incremental L2 CSV files."""

from __future__ import annotations

import csv
import gzip
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


REQUIRED_COLUMNS = {
    "exchange", "symbol", "timestamp", "local_timestamp", "is_snapshot",
    "side", "price", "amount",
}


@dataclass(frozen=True, slots=True)
class L2Row:
    row_number: int
    exchange: str
    symbol: str
    timestamp: int
    local_timestamp: int
    is_snapshot: bool
    side: str
    price: str
    amount: str


def iter_l2_rows(path: Path) -> Iterator[L2Row]:
    """Yield records in source order; timestamps are integer microseconds UTC."""
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = set(reader.fieldnames or ())
        missing = REQUIRED_COLUMNS - fields
        if missing:
            raise ValueError(f"missing required L2 columns: {sorted(missing)}")
        for row_number, row in enumerate(reader, start=2):
            raw_snapshot = (row["is_snapshot"] or "").strip().lower()
            if raw_snapshot not in {"true", "false"}:
                raise ValueError(f"invalid is_snapshot at CSV row {row_number}")
            try:
                timestamp = int(row["timestamp"])
                local_timestamp = int(row["local_timestamp"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid timestamp at CSV row {row_number}") from exc
            yield L2Row(
                row_number=row_number,
                exchange=row["exchange"],
                symbol=row["symbol"],
                timestamp=timestamp,
                local_timestamp=local_timestamp,
                is_snapshot=raw_snapshot == "true",
                side=(row["side"] or "").strip().lower(),
                price=(row["price"] or "").strip(),
                amount=(row["amount"] or "").strip(),
            )


def iter_local_timestamp_groups(path: Path) -> Iterator[list[L2Row]]:
    """Group contiguous rows from one source message, preserving their order."""
    group: list[L2Row] = []
    current_timestamp: int | None = None
    for row in iter_l2_rows(path):
        if group and row.local_timestamp != current_timestamp:
            yield group
            group = []
        group.append(row)
        current_timestamp = row.local_timestamp
    if group:
        yield group
