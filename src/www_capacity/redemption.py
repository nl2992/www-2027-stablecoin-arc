"""Primary-market redemption availability windows.

The default schedule is a US banking-day window (America/New_York, DST-aware). It
is a modelling assumption for sensitivity analysis, not a documented issuer policy;
issuer-specific schedules must be sourced before historical use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class RedemptionSchedule:
    tz: str = "America/New_York"
    open_time: time = time(9, 0)
    close_time: time = time(17, 0)
    weekdays: frozenset[int] = frozenset({0, 1, 2, 3, 4})  # Monday=0
    closed_dates: frozenset[date] = field(default_factory=frozenset)
    source: str = "ASSUMPTION: generic US banking hours"

    def is_open(self, ts: datetime) -> bool:
        if ts.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        local = ts.astimezone(ZoneInfo(self.tz))
        return (local.weekday() in self.weekdays and local.date() not in self.closed_dates
                and self.open_time <= local.time() < self.close_time)

    def next_open(self, ts: datetime) -> datetime:
        """Earliest instant >= ts at which redemption is open (returned in UTC)."""
        if self.is_open(ts):
            return ts.astimezone(ZoneInfo("UTC"))
        zone = ZoneInfo(self.tz)
        local = ts.astimezone(zone)
        day = local.date()
        for _ in range(366):
            candidate = datetime.combine(day, self.open_time, tzinfo=zone)
            if candidate >= local and day.weekday() in self.weekdays and day not in self.closed_dates:
                return candidate.astimezone(ZoneInfo("UTC"))
            day += timedelta(days=1)
        raise ValueError("no opening within a year")

    def minutes_until_open(self, ts: datetime) -> float:
        return (self.next_open(ts) - ts).total_seconds() / 60
