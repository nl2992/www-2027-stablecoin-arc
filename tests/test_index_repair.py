"""Synthetic, offline checks for the index-repair study (software validation, not research results)."""

import numpy as np
import pandas as pd
import pytest

from www_rescue.index_repair import case, exclusion_index, indexes, repaired_frames, scaling
from www_rescue.feed_bias import weighted

H = pd.date_range("2023-06-14", periods=2, freq="1h", tz="UTC")


def frame(p, v, idx=H):
    return pd.DataFrame({"p": np.asarray(p, float), "v": np.asarray(v, float)}, idx[: len(p)])


def three(a_p=(0.02, 0.0), a_v=(2.0, 0.5)):
    # hour 0: platform A 200 bps above B and C, A holds half the volume; hour 1: all venues agree
    return {"A": frame(a_p, a_v), "B": frame([0.0, 0.0], [1, 1]), "C": frame([0.0, 0.0], [1, 1])}


def bps(s):
    return list(np.round(1e4 * s.to_numpy(), 6))


def flags(*vals):
    return pd.Series(vals, H[: len(vals)])


def test_naive_equal_and_median_by_hand():
    f = three()
    assert bps(weighted(f)) == [100.0, 0.0]  # 0.02 * 2/4
    assert bps(pd.concat({k: v["p"] for k, v in f.items()}, axis=1).mean(axis=1))[0] == pytest.approx(200 / 3, abs=1e-4)
    idx, _ = indexes(f, "A", flags(False, False), pd.Series(dtype=float))
    assert bps(idx["median"]) == [0.0, 0.0]  # one outlier among three: the median ignores it


def test_exclusion_threshold_is_strictly_greater_and_uses_the_median():
    f = three()
    assert bps(exclusion_index(f, 100)[0]) == [0.0, 0.0]  # 200 > 100: A dropped
    assert bps(exclusion_index(f, 200)[0]) == [100.0, 0.0]  # 200 is not > 200: A kept, same as naive
    assert exclusion_index(f, 100)[1] == 0


def test_two_venues_make_median_and_exclusion_degenerate():
    f = {"A": frame([0.02, 0.0], [3, 1]), "B": frame([0.0, 0.0], [1, 1])}
    idx, fallback = indexes(f, "A", flags(False, False), pd.Series(dtype=float))
    assert bps(idx["median"]) == bps(idx["equal"]) == [100.0, 0.0]  # median of two is their mean
    assert bps(idx["naive"]) == [150.0, 0.0]  # 0.02 * 3/4
    # both venues sit 100 bps from the median: k=50 drops both and falls back to naive; k=100 drops neither
    assert bps(idx["excl_50"]) == bps(idx["excl_100"]) == bps(idx["naive"])
    assert fallback["excl_50"] == 1 and fallback["excl_100"] == 0


def test_filtered_drops_only_the_flagged_platform_hour():
    idx, _ = indexes(three(), "A", flags(True, False), pd.Series(dtype=float))
    assert bps(idx["filtered"]) == [0.0, 0.0]


def test_repair_subtracts_second_asset_dislocation_only_in_flagged_hours():
    f = three()
    second = pd.Series([150.0, 150.0], H)  # also present in hour 1, but hour 1 is not flagged
    out = repaired_frames(f, "A", flags(True, False), second)
    assert np.allclose(out["A"]["p"], [0.02 - 0.015, 0.0])
    assert np.allclose(out["B"]["p"], f["B"]["p"]) and np.allclose(out["C"]["p"], f["C"]["p"])
    idx, _ = indexes(f, "A", flags(True, False), second)
    assert bps(idx["repaired"]) == [25.0, 0.0]  # A at 50 bps, weight 2/4
    full, _ = indexes(f, "A", flags(True, False), pd.Series([200.0, 0.0], H))
    assert bps(full["repaired"]) == [0.0, 0.0]  # second asset explains the whole gap


def test_repair_adjustment_does_not_depend_on_the_platforms_own_btc_gap():
    second = pd.Series([150.0, 0.0], H)
    f1, f2 = three(), three(a_p=(0.05, 0.0))  # same flags and PD_second, platform BTC gap 500 bps instead of 200
    r1 = repaired_frames(f1, "A", flags(True, False), second)["A"]["p"]
    r2 = repaired_frames(f2, "A", flags(True, False), second)["A"]["p"]
    # the amount subtracted is identical (150 bps); the leftover gap is whatever the second asset does not explain
    assert f1["A"]["p"].iloc[0] - r1.iloc[0] == pytest.approx(0.015) and f2["A"]["p"].iloc[0] - r2.iloc[0] == pytest.approx(0.015)
    assert r2.iloc[0] - r1.iloc[0] == pytest.approx(0.03)


def test_scaling_reports_hours_above_50_bps():
    L = pd.Series([0.0, 100.0, 600.0, -1000.0], pd.date_range("2023-06-14", periods=4, freq="1h", tz="UTC"))
    rows = {r["w"]: r for r in scaling(L, L)}
    assert rows[0.05]["btc_gap"]["hours_ge_50"] == 1  # only |w PD| = 50 from the -1000 hour
    assert rows[0.1]["btc_gap"]["hours_ge_50"] == 2 and rows[0.1]["btc_gap"]["max_abs_bps"] == pytest.approx(100.0)
    assert rows[0.3]["btc_gap"]["hours_ge_50"] == 2 and rows[0.3]["btc_gap"]["share_ge_50"] == pytest.approx(0.5)


def test_case_reports_leader_and_flagged_subsets():
    f = three()
    clean_L = (1e4 * (f["A"]["p"] - f["B"]["p"]))
    second = pd.Series([200.0, 0.0], H)
    c = case("A", f, ["B", "C"], clean_L, second)
    assert c["flagged_hours"] == 1 and c["platform_volume_leader_hours"] == 1 and c["flagged_and_leader_hours"] == 1
    m = c["methods"]
    assert m["naive"]["all_hours"]["max_abs_bps"] == pytest.approx(100.0)
    assert m["naive"]["flagged_and_leader_hours"]["hours_abs_ge_100"] == 1
    assert m["median"]["all_hours"]["hours_abs_ge_50"] == 0
    assert m["repaired"]["flagged_hours"]["max_abs_bps"] == pytest.approx(0.0)
    assert c["degenerate_for_median_and_exclusion"] is False
