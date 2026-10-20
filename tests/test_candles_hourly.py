"""Hourly Bitfinex and Coinbase paging and manifest merge, on synthetic data; no network."""

import pandas as pd

from www_events.acquire import merge_records
from www_events.bitstamp import month_bounds
from www_events.candles import fetch_bitfinex_hourly, fetch_coinbase_hourly

HOUR = 3600


def fake_bitfinex(skip=(), first=None):
    def get(url):
        start = int(url.split("start=")[1].split("&")[0]) // 1000
        end = int(url.split("end=")[1].split("&")[0]) // 1000
        start = max(start, first or start)
        return [[t * 1000, 1.0, 2.0, 3.0, 0.5, 4.0] for t in range(start, min(start + 10_000 * HOUR, end + 1), HOUR)
                if t not in skip]
    return get


def fake_coinbase(listed=None):
    def get(url):
        start = pd.Timestamp(url.split("start=")[1].split("&")[0]).value // 10**9
        end = pd.Timestamp(url.split("end=")[1]).value // 10**9
        return [[t, 0.5, 3.0, 1.0, 2.0, 4.0] for t in range(end, start - HOUR, -HOUR) if t >= (listed or 0)]
    return get


def test_bitfinex_hourly_pages_ascending_and_maps_columns():
    lo, hi = month_bounds("2017-01")[0], month_bounds("2018-12")[1]
    frame, pages = fetch_bitfinex_hourly("LTCUSD", "2017-01", "2018-12", get=fake_bitfinex(skip={lo + HOUR}), pause=0)
    assert len(frame) == (hi - lo) // HOUR - 1 and frame["timestamp"].is_unique
    assert frame["timestamp"].iloc[0] == lo and frame["timestamp"].iloc[-1] == hi - HOUR
    assert list(frame.iloc[0, 1:]) == [1.0, 3.0, 0.5, 2.0, 4.0]  # open, high, low, close, volume
    assert pages == 2  # 17,520 hours at 10,000 per page


def test_bitfinex_hourly_late_listing_starts_at_first_bar():
    lo = month_bounds("2017-01")[0]
    first = lo + 100 * HOUR
    frame, _ = fetch_bitfinex_hourly("XYZUSD", "2017-01", "2017-02", get=fake_bitfinex(first=first), pause=0)
    assert frame["timestamp"].iloc[0] == first


def test_coinbase_hourly_covers_range_once_and_respects_listing():
    lo, hi = month_bounds("2017-01")[0], month_bounds("2017-03")[1]
    frame, pages = fetch_coinbase_hourly("LTC-USD", "2017-01", "2017-03", get=fake_coinbase(), pause=0)
    assert len(frame) == (hi - lo) // HOUR and frame["timestamp"].is_unique
    assert list(frame.iloc[0, 1:]) == [1.0, 3.0, 0.5, 2.0, 4.0]
    assert pages == -(-((hi - lo) // HOUR) // 300)
    late, _ = fetch_coinbase_hourly("LTC-USD", "2017-01", "2017-03", get=fake_coinbase(listed=lo + 1000 * HOUR), pause=0)
    assert late["timestamp"].iloc[0] == lo + 1000 * HOUR


def test_merge_records_keeps_unrelated_and_replaces_same_key():
    old = [{"venue": "bitfinex", "symbol": "BTCUSD", "month": "2017-01"},
           {"venue": "bitfinex-1h", "symbol": "LTCUSD", "month": "2017-01..2023-12", "v": 1}]
    new = [{"venue": "bitfinex-1h", "symbol": "LTCUSD", "month": "2017-01..2023-12", "v": 2}]
    merged = merge_records(old, new)
    assert merged[0] == old[0] and merged[1]["v"] == 2 and len(merged) == 2
