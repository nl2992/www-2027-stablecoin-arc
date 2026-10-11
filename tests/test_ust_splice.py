import numpy as np
import pandas as pd

from www_events.ust_splice import build_series, preconditions


def grid(start, end, price, traded=True):
    idx = pd.date_range(start, end, freq="1min", tz="UTC", inclusive="left")
    return pd.DataFrame({"close": price, "traded": traded, "present": True}, index=idx)


def test_splice_leaves_gap_missing_and_converts_each_segment_to_usd():
    ust = grid("2022-05-12", "2022-05-13", 0.5)
    ustc = grid("2022-05-15", "2022-05-16", 0.02)
    busd = grid("2022-05-12", "2022-05-17", 1.001)
    usdt = grid("2022-05-12", "2022-05-17", 0.999)
    s = build_series(ust, ustc, busd, usdt)
    assert s.loc["2022-05-12 12:00", "ust_close"] == np.float64(0.5 * 0.999)
    assert np.isclose(s.loc["2022-05-15 12:00", "ust_close"], 0.02 * 1.001 * 0.999)
    assert pd.Timestamp("2022-05-14 00:00", tz="UTC") not in s.index  # gap is never filled
    rec = (pd.Timestamp("2022-05-14", tz="UTC"), pd.Timestamp("2022-05-15", tz="UTC"))
    gates = preconditions(ust, ustc, busd, usdt, rec)
    assert gates["b_ustc_starts_after_ust_ends"]["passes"] and gates["c_conversion_legs_cover_recovery"]["passes"]


def test_untraded_leg_makes_minute_untraded():
    ust = grid("2022-05-12", "2022-05-13", 0.5)
    ustc = grid("2022-05-15", "2022-05-16", 0.02)
    busd = grid("2022-05-12", "2022-05-17", 1.0, traded=False)
    usdt = grid("2022-05-12", "2022-05-17", 1.0)
    s = build_series(ust, ustc, busd, usdt)
    assert s.loc["2022-05-12 12:00", "ust_traded"] and not s.loc["2022-05-15 12:00", "ust_traded"]
