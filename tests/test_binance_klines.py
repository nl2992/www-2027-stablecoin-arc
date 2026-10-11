"""Synthetic kline archives only; no data are downloaded by these tests."""

import hashlib
import zipfile

import numpy as np
import pandas as pd
import pytest

from www_events.binance_klines import (
    gap_summary, infer_time_unit, manifest_entry, parse_kline_csv, read_kline_zip, to_minute_grid,
    verify_checksum,
)

T0_MS = 1_678_406_400_000  # 2023-03-10T00:00:00Z


def row(t, o=1.0, h=1.001, low=0.999, c=1.0, v=10.0):
    return f"{t},{o},{h},{low},{c},{v},{t + 59_999},{v * c},5,1,1,0"


def csv(times, **kw):
    return "\n".join(row(t, **kw) for t in times) + "\n"


def test_millisecond_and_microsecond_files_parse_to_the_same_times():
    ms = parse_kline_csv(csv([T0_MS, T0_MS + 60_000]))
    us = parse_kline_csv(csv([T0_MS * 1000, (T0_MS + 60_000) * 1000]))
    assert ms.time_unit == "ms" and us.time_unit == "us"
    assert ms.frame.index.equals(us.frame.index)
    assert ms.frame.index[0] == pd.Timestamp("2023-03-10T00:00:00Z")


def test_mixed_units_header_rows_and_misalignment_are_rejected():
    with pytest.raises(ValueError, match="mixed"):
        infer_time_unit(np.array([T0_MS, T0_MS * 1000]))
    with pytest.raises(ValueError, match="header"):
        parse_kline_csv("open_time,open,high,low,close,volume,close_time,qv,n,tb,tq,ignore\n" + csv([T0_MS]))
    with pytest.raises(ValueError, match="aligned"):
        parse_kline_csv(csv([T0_MS + 1_000]))


def test_identical_duplicates_dropped_conflicting_duplicates_rejected():
    out = parse_kline_csv(csv([T0_MS, T0_MS, T0_MS + 60_000]))
    assert out.duplicates_dropped == 1 and len(out.frame) == 2
    conflicting = row(T0_MS) + "\n" + row(T0_MS, c=0.9995) + "\n"
    with pytest.raises(ValueError, match="conflicting"):
        parse_kline_csv(conflicting)


def test_out_of_order_rows_are_sorted_and_reported():
    out = parse_kline_csv(csv([T0_MS + 60_000, T0_MS]))
    assert out.frame.index.is_monotonic_increasing and out.issues


def test_invalid_prices_and_ohlc_inconsistency_are_rejected():
    with pytest.raises(ValueError, match="non-positive"):
        parse_kline_csv(csv([T0_MS], c=0.0, low=0.0))
    with pytest.raises(ValueError, match="violate"):
        parse_kline_csv(csv([T0_MS], h=0.99))


def test_minute_grid_keeps_gaps_missing_and_flags_untraded_minutes():
    times = [T0_MS, T0_MS + 60_000, T0_MS + 4 * 60_000]
    k = parse_kline_csv("\n".join([row(times[0]), row(times[1], v=0.0), row(times[2])]) + "\n")
    start = pd.Timestamp("2023-03-10T00:00:00Z")
    grid = to_minute_grid(k.frame, start, start + pd.Timedelta(minutes=6), "binance_usdcusdt")
    assert grid["binance_usdcusdt_close"].isna().tolist() == [False, False, True, True, False, True]
    assert gap_summary(grid, "binance_usdcusdt") == {
        "grid_minutes": 6, "missing_minutes": 3, "longest_missing_run_minutes": 2,
        "present_untraded_minutes": 1, "traded_minutes": 2,
    }


def test_zip_reader_checksum_and_manifest(tmp_path):
    archive = tmp_path / "USDCUSDT-1m-2023-03.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("USDCUSDT-1m-2023-03.csv", csv([T0_MS, T0_MS + 60_000]))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = tmp_path / "USDCUSDT-1m-2023-03.zip.CHECKSUM"
    checksum.write_text(f"{digest}  {archive.name}\n")
    assert verify_checksum(archive, checksum) == digest
    assert len(read_kline_zip(archive).frame) == 2
    entry = manifest_entry(archive, source_url="https://data.binance.vision/x", listed_etag="e",
                           listed_bytes=archive.stat().st_size, checksum_verified=True, terms_note="test")
    assert entry["sha256"] == digest and entry["listed_bytes_match"] is True
    checksum.write_text(f"{'0' * 64}  {archive.name}\n")
    with pytest.raises(ValueError, match="mismatch"):
        verify_checksum(archive, checksum)
    checksum.write_text(f"{digest}  OTHER.zip\n")
    with pytest.raises(ValueError, match="names"):
        verify_checksum(archive, checksum)


def test_binance_us_11_column_header_layout_parses_to_the_same_frame():
    header = ("open_time,open,high,low,close,volume,close_time,quote_volume,count,"
              "taker_buy_base_volume,taker_buy_quote_volume")
    rows = [f"{t},1.0,1.001,0.999,1.0,10.0,{t + 59_999},10.0,5,1,1" for t in (T0_MS, T0_MS + 60_000)]
    us = parse_kline_csv(header + "\n" + "\n".join(rows) + "\n")
    com = parse_kline_csv(csv([T0_MS, T0_MS + 60_000]))
    assert us.layout == "binance_us_11col_header" and com.layout == "binance_com_12col_noheader"
    assert us.frame.index.equals(com.frame.index)
    assert (us.frame[["open", "high", "low", "close", "volume", "trades"]] ==
            com.frame[["open", "high", "low", "close", "volume", "trades"]]).all().all()
    with pytest.raises(ValueError, match="unrecognised"):
        parse_kline_csv(header.replace("count", "n") + "\n" + rows[0] + "\n")
