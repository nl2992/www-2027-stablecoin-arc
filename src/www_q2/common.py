"""Shared definitions for Q2 (autoresearch/program_q2.md): events, panels, calm hours. Kraken is never read here."""

from __future__ import annotations

import pandas as pd

from www_q1 import panel as Q1P
from www_stable import panel as SP

REPO = SP.REPO
OUT_DIR = REPO / "reports" / "q2"
LABELS = OUT_DIR / "labels.json"
CALIBRATION = OUT_DIR / "calibration.json"
RESULTS = OUT_DIR / "results.json"

# (id, unit, first day, last day, panel, source note) -- fixed by the pre-registration
EVENTS = (
    ("E1", "USDT", "2018-11-27", "2018-12-31", "q1"),
    ("E2", "USDT", "2019-04-20", "2019-05-31", "q1"),
    ("E3", "USDT", "2020-03-09", "2020-03-31", "q1"),
    ("E4", "USDC", "2023-03-08", "2023-03-20", "stable"),
    ("E5", "TUSD", "2024-01-01", "2024-01-31", "stable"),
    ("E6", "FDUSD", "2025-04-01", "2025-04-30", "stable"),
)
CALM_DAYS, EXCLUDE_DAYS = 30, 7
USD_UNIT = "USD"


def bounds(a: str, b: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    return pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC") + pd.Timedelta(hours=23)


def load(panel: str):
    """(markets, side) for 'q1' or 'stable'; the reference column is not read into the result."""
    if panel == "q1":
        markets, side, _, _ = Q1P.load_all(with_reference=False)
    else:
        SP.ensure()
        frame = pd.read_parquet(SP.PANEL_PATH)
        if "timestamp_utc" in frame.columns:
            frame = frame.set_index("timestamp_utc")
        markets = {}
        for c in frame.columns:
            head, item = c.split("|", 1)
            if head in ("kraken", "side"):
                continue
            markets.setdefault(head, pd.DataFrame(index=frame.index))[item] = frame[c]
        side = frame[[c for c in frame.columns if c.startswith("side|")]].rename(columns=lambda c: c.split("|", 1)[1])
    return markets, side


def calm_index(event_id: str, events=EVENTS) -> pd.DatetimeIndex:
    """Hours of the 30 days before the event window, minus any hour within 7 days of another event's window."""
    by = {e[0]: bounds(e[2], e[3]) for e in events}
    lo, _ = by[event_id]
    idx = pd.date_range(lo - pd.Timedelta(days=CALM_DAYS), lo - pd.Timedelta(hours=1), freq="h", tz="UTC")
    keep = pd.Series(True, index=idx)
    pad = pd.Timedelta(days=EXCLUDE_DAYS)
    for k, (a, b) in by.items():
        if k != event_id:
            keep &= ~((idx >= a - pad) & (idx <= b + pad))
    return idx[keep.to_numpy()]
