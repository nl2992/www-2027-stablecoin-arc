"""Bitstamp adapter on synthetic responses; no network."""

import json

import pandas as pd
import pytest

from www_events.bitstamp import fetch_month, load_months, month_bounds, save_month


def fake_api(lo, hi, gap=None):
    def get(url):
        start = int(url.split("start=")[1])
        bars = [{"timestamp": str(t), "open": "1.0", "high": "1.0", "low": "1.0", "close": "1.0",
                 "volume": "0" if gap and gap[0] <= t < gap[1] else "5"}
                for t in range(start, min(start + 60_000, hi + 600), 60)]
        return {"data": {"pair": "USDT/USD", "ohlc": bars}}
    return get


def test_fetch_month_pages_through_whole_month_without_duplicates():
    lo, hi = month_bounds("2023-02")
    frame, pages = fetch_month("usdtusd", "2023-02", get=fake_api(lo, hi), pause=0)
    assert len(frame) == 28 * 1440 and frame["timestamp"].is_unique
    assert frame["timestamp"].iloc[0] == lo and frame["timestamp"].iloc[-1] == hi - 60
    assert pages == 41  # 40,320 minutes at 1,000 bars per page, plus one partial page


def test_load_months_verifies_recorded_hash_and_masks_zero_volume(tmp_path):
    lo, hi = month_bounds("2023-02")
    frame, _ = fetch_month("usdtusd", "2023-02", get=fake_api(lo, hi, gap=(lo, lo + 600)), pause=0)
    path = tmp_path / "USDTUSD-1m-2023-02.csv"
    digest = save_month(frame, path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"records": [{"venue": "bitstamp", "status": "VERIFIED",
                                                 "file": f"data/raw/bitstamp/{path.name}", "sha256": digest}]}))
    grid, prov = load_months(tmp_path, "usdtusd", "bitstamp_usdtusd", manifest)
    assert grid.index[0] == pd.Timestamp("2023-02-01", tz="UTC")
    assert not grid["bitstamp_usdtusd_traded"].iloc[:10].any() and grid["bitstamp_usdtusd_traded"].iloc[10]
    assert prov["files"][0]["hash_kind"].startswith("self-recorded")
    original = path.read_text()
    path.write_text(original.replace("\n", "\n", 1)[:-2] + "9\n")  # tamper: change the last value
    assert path.read_text() != original
    with pytest.raises(ValueError, match="manifest hash"):
        load_months(tmp_path, "usdtusd", "bitstamp_usdtusd", manifest)
