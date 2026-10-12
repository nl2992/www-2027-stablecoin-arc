"""Deterministic L2 book reconstruction for normalized Tardis CSV records."""

from __future__ import annotations

import heapq
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

from .reader import L2Row, iter_local_timestamp_groups


EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def timestamp_iso(microseconds: int) -> str:
    return (EPOCH + timedelta(microseconds=microseconds)).isoformat()


@dataclass
class Book:
    bids: dict[Decimal, Decimal] = field(default_factory=dict)
    asks: dict[Decimal, Decimal] = field(default_factory=dict)
    _bid_heap: list[tuple[Decimal, int, Decimal]] = field(default_factory=list)
    _ask_heap: list[tuple[Decimal, int, Decimal]] = field(default_factory=list)
    _versions: dict[tuple[str, Decimal], int] = field(default_factory=dict)
    _version: int = 0

    def reset(self) -> None:
        self.bids.clear()
        self.asks.clear()
        self._bid_heap.clear()
        self._ask_heap.clear()
        self._versions.clear()
        self._version = 0

    def apply(self, side: str, price: Decimal, amount: Decimal) -> bool:
        levels = self.bids if side == "bid" else self.asks
        heap = self._bid_heap if side == "bid" else self._ask_heap
        key = (side, price)
        self._version += 1
        self._versions[key] = self._version
        removed = amount == 0
        if removed:
            levels.pop(price, None)
        else:
            levels[price] = amount
            heapq.heappush(heap, (-price if side == "bid" else price, self._version, price))
        self._compact(side)
        return removed

    def _compact(self, side: str) -> None:
        levels = self.bids if side == "bid" else self.asks
        heap = self._bid_heap if side == "bid" else self._ask_heap
        if len(heap) > max(10_000, 5 * len(levels)):
            heap[:] = [
                (-price if side == "bid" else price, self._versions[(side, price)], price)
                for price in levels
            ]
            heapq.heapify(heap)

    def best(self, side: str) -> tuple[Decimal, Decimal] | None:
        levels = self.bids if side == "bid" else self.asks
        heap = self._bid_heap if side == "bid" else self._ask_heap
        while heap:
            _, version, price = heap[0]
            if self._versions.get((side, price)) == version and price in levels:
                return price, levels[price]
            heapq.heappop(heap)
        return None


class BookReplayer:
    """Apply complete snapshot segments and absolute-size level updates.

    The normalized CSV omits Binance.US sequence ids, so this reconstructs the
    provided record stream; it cannot independently prove native sequence
    continuity between provider snapshots.
    """

    def __init__(self, *, max_idle_gap_seconds: float = 30.0, max_quote_samples: int = 48):
        self.book = Book()
        self.max_idle_gap_us = int(max_idle_gap_seconds * 1_000_000)
        self.max_quote_samples = max_quote_samples
        self.initialized = False
        self.in_snapshot = False
        self.tainted = False
        self.counters: Counter[str] = Counter()
        self.anomalies: list[dict[str, Any]] = []
        self.first_timestamp: int | None = None
        self.last_timestamp: int | None = None
        self.min_timestamp: int | None = None
        self.max_timestamp: int | None = None
        self.first_local_timestamp: int | None = None
        self.max_local_timestamp: int | None = None
        self.last_local_timestamp: int | None = None
        self.min_arrival_lag_us: int | None = None
        self.max_arrival_lag_us: int | None = None
        self.negative_arrival_lags = 0
        self.quote_samples: list[dict[str, Any]] = []
        self._last_sample_hour: int | None = None

    def _anomaly(self, code: str, row: L2Row, **details: Any) -> None:
        self.counters[code] += 1
        if len(self.anomalies) < 100:
            self.anomalies.append({"code": code, "row_number": row.row_number, **details})

    def _finish_snapshot(self, row: L2Row) -> None:
        self.in_snapshot = False
        if self.book.bids and self.book.asks and not self.tainted:
            self.initialized = True
            self.counters["complete_snapshot_segments"] += 1
        else:
            self.initialized = False
            self.counters["incomplete_snapshot_segments"] += 1
            self._anomaly("incomplete_snapshot", row, bid_levels=len(self.book.bids), ask_levels=len(self.book.asks))

    def _parse_level(self, row: L2Row) -> tuple[Decimal, Decimal] | None:
        try:
            price = Decimal(row.price)
            amount = Decimal(row.amount)
        except InvalidOperation:
            self._anomaly("invalid_decimal", row)
            return None
        if not price.is_finite() or not amount.is_finite() or price <= 0 or amount < 0:
            self._anomaly("invalid_price_or_amount", row, price=row.price, amount=row.amount)
            return None
        if row.side not in {"bid", "ask"}:
            self._anomaly("invalid_side", row, side=row.side)
            return None
        return price, amount

    def _record_quote(self, timestamp: int, local_timestamp: int) -> None:
        if not self.initialized:
            return
        bid = self.book.best("bid")
        ask = self.book.best("ask")
        if bid is None or ask is None:
            self.counters["empty_side_after_initialization"] += 1
            return
        if bid[0] >= ask[0]:
            code = "locked_book" if bid[0] == ask[0] else "crossed_book"
            self.counters[code] += 1
            if len(self.anomalies) < 100:
                self.anomalies.append({"code": code, "timestamp": timestamp_iso(timestamp), "bid": str(bid[0]), "ask": str(ask[0])})
        hour = timestamp // 3_600_000_000
        if hour != self._last_sample_hour and len(self.quote_samples) < self.max_quote_samples:
            self.quote_samples.append({
                "timestamp": timestamp_iso(timestamp),
                "local_timestamp": timestamp_iso(local_timestamp),
                "best_bid": str(bid[0]),
                "best_bid_amount": str(bid[1]),
                "best_ask": str(ask[0]),
                "best_ask_amount": str(ask[1]),
                "bid_levels": len(self.book.bids),
                "ask_levels": len(self.book.asks),
            })
            self._last_sample_hour = hour

    def process_group(self, group: list[L2Row]) -> None:
        if not group:
            return
        self.counters["message_groups"] += 1
        self.counters["rows"] += len(group)
        if len(group) > 1:
            self.counters["multirow_message_groups"] += 1
        representative = group[0]
        local_timestamp = representative.local_timestamp
        for row in group:
            if row.exchange != representative.exchange or row.symbol != representative.symbol:
                self._anomaly("mixed_instrument_group", row)
                self.initialized = False
                self.tainted = True
                continue
            if self.first_timestamp is None:
                self.first_timestamp = row.timestamp
            if self.first_local_timestamp is None:
                self.first_local_timestamp = row.local_timestamp
            self.min_timestamp = row.timestamp if self.min_timestamp is None else min(self.min_timestamp, row.timestamp)
            self.max_timestamp = row.timestamp if self.max_timestamp is None else max(self.max_timestamp, row.timestamp)
            self.max_local_timestamp = row.local_timestamp if self.max_local_timestamp is None else max(self.max_local_timestamp, row.local_timestamp)
            self.last_timestamp = row.timestamp
            lag = row.local_timestamp - row.timestamp
            self.min_arrival_lag_us = lag if self.min_arrival_lag_us is None else min(self.min_arrival_lag_us, lag)
            self.max_arrival_lag_us = lag if self.max_arrival_lag_us is None else max(self.max_arrival_lag_us, lag)
            self.negative_arrival_lags += lag < 0
            if self._previous_exchange_timestamp is not None and row.timestamp < self._previous_exchange_timestamp:
                self._anomaly("exchange_timestamp_regression", row)
            if self._previous_local_timestamp is not None and row.local_timestamp < self._previous_local_timestamp:
                self._anomaly("local_timestamp_regression", row)
                self.initialized = False
                self.tainted = True
            self._previous_exchange_timestamp = row.timestamp
            self._previous_local_timestamp = row.local_timestamp
            if row.is_snapshot:
                if not self.in_snapshot:
                    if self.counters["snapshot_segments"] > 0:
                        self.counters["snapshot_resets"] += 1
                    self.book.reset()
                    self.initialized = False
                    self.tainted = False
                    self.in_snapshot = True
                    self.counters["snapshot_segments"] += 1
                self.counters["snapshot_rows"] += 1
            else:
                if self.in_snapshot:
                    self._finish_snapshot(row)
                self.counters["update_rows"] += 1
                if not self.initialized:
                    self.counters["updates_ignored_without_valid_snapshot"] += 1
                    continue
            parsed = self._parse_level(row)
            if parsed is None:
                self.initialized = False
                self.tainted = True
                continue
            price, amount = parsed
            removed = self.book.apply(row.side, price, amount)
            if removed:
                self.counters["zero_amount_removals"] += 1
            elif not row.is_snapshot:
                self.counters["applied_updates"] += 1
        if self.last_local_timestamp is not None:
            delta = local_timestamp - self.last_local_timestamp
            if delta > self.max_idle_gap_us:
                self.counters["local_arrival_gaps_over_threshold"] += 1
                self.counters["maximum_local_arrival_gap_us"] = max(
                    self.counters["maximum_local_arrival_gap_us"], delta
                )
        self.last_local_timestamp = local_timestamp
        if group[-1].is_snapshot:
            # The snapshot is not valid for output until the following update
            # group terminates the snapshot segment (or EOF finalizes it).
            return
        if self.in_snapshot:
            self._finish_snapshot(group[-1])
        if not self.initialized and not self.tainted and self.book.bids and self.book.asks:
            self.initialized = True
        self._record_quote(group[-1].timestamp, local_timestamp)

    def run(self, path: Path) -> dict[str, Any]:
        self._previous_exchange_timestamp: int | None = None
        self._previous_local_timestamp: int | None = None
        for group in iter_local_timestamp_groups(path):
            self.process_group(group)
        if self.in_snapshot:
            self._finish_snapshot(L2Row(0, "", "", self.last_timestamp or 0, self.last_local_timestamp or 0, False, "", "", ""))
        final_bid = self.book.best("bid") if self.initialized else None
        final_ask = self.book.best("ask") if self.initialized else None
        return {
            "status": "REPLAYED",
            "rows": self.counters["rows"],
            "message_groups": self.counters["message_groups"],
            "multirow_message_groups": self.counters["multirow_message_groups"],
            "first_timestamp": timestamp_iso(self.first_timestamp) if self.first_timestamp is not None else None,
            "last_timestamp": timestamp_iso(self.last_timestamp) if self.last_timestamp is not None else None,
            "exchange_timestamp_min": timestamp_iso(self.min_timestamp) if self.min_timestamp is not None else None,
            "exchange_timestamp_max": timestamp_iso(self.max_timestamp) if self.max_timestamp is not None else None,
            "first_local_timestamp": timestamp_iso(self.first_local_timestamp) if self.first_local_timestamp is not None else None,
            "last_local_timestamp": timestamp_iso(self.last_local_timestamp) if self.last_local_timestamp is not None else None,
            "maximum_local_timestamp": timestamp_iso(self.max_local_timestamp) if self.max_local_timestamp is not None else None,
            "timestamp_regressions": self.counters["exchange_timestamp_regression"],
            "local_timestamp_regressions": self.counters["local_timestamp_regression"],
            "snapshot_segments": self.counters["snapshot_segments"],
            "snapshot_resets": self.counters["snapshot_resets"],
            "complete_snapshot_segments": self.counters["complete_snapshot_segments"],
            "incomplete_snapshot_segments": self.counters["incomplete_snapshot_segments"],
            "snapshot_rows": self.counters["snapshot_rows"],
            "update_rows": self.counters["update_rows"],
            "applied_updates": self.counters["applied_updates"],
            "updates_ignored_without_valid_snapshot": self.counters["updates_ignored_without_valid_snapshot"],
            "zero_amount_removals": self.counters["zero_amount_removals"],
            "local_arrival_gaps_over_threshold": self.counters["local_arrival_gaps_over_threshold"],
            "maximum_local_arrival_gap_seconds": self.counters["maximum_local_arrival_gap_us"] / 1_000_000,
            "arrival_lag_us_min": self.min_arrival_lag_us,
            "arrival_lag_us_max": self.max_arrival_lag_us,
            "negative_arrival_lags": self.negative_arrival_lags,
            "crossed_book_observations": self.counters["crossed_book"],
            "locked_book_observations": self.counters["locked_book"],
            "anomaly_counts": dict(sorted((k, v) for k, v in self.counters.items() if k in {
                "invalid_decimal", "invalid_price_or_amount", "invalid_side", "incomplete_snapshot",
                "empty_side_after_initialization", "mixed_instrument_group", "exchange_timestamp_regression",
                "local_timestamp_regression", "crossed_book", "locked_book",
            })),
            "anomaly_examples": self.anomalies,
            "final_book_initialized": self.initialized,
            "final_book_two_sided": bool(final_bid and final_ask),
            "native_sequence_continuity": "UNVERIFIABLE_NOT_PRESENT_IN_NORMALIZED_CSV",
            "final_bid_levels": len(self.book.bids) if self.initialized else 0,
            "final_ask_levels": len(self.book.asks) if self.initialized else 0,
            "final_best_bid": {"price": str(final_bid[0]), "amount": str(final_bid[1])} if final_bid else None,
            "final_best_ask": {"price": str(final_ask[0]), "amount": str(final_ask[1])} if final_ask else None,
            "representative_quotes": self.quote_samples,
            "limitations": [
                "Replay validates the supplied normalized rows, not the provider's unexposed native sequence ids.",
                "Local-arrival gaps may reflect inactivity or capture gaps and are not proof of a lost exchange update.",
                "Crossed/locked checks are evaluated after each local-timestamp message group.",
            ],
        }


def replay_file(path: Path, *, max_idle_gap_seconds: float = 30.0) -> dict[str, Any]:
    return BookReplayer(max_idle_gap_seconds=max_idle_gap_seconds).run(path)
