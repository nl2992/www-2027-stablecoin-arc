"""Noise bounds: synthetic checks of the timing variants and helpers, and freshness of the committed outputs."""

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from www_auto import noise_bounds as N
from www_paper import noise_macros as M

ROOT = Path(__file__).parents[1]


def minute_logs(n_hours=300, seed=5, traded_frac=0.3):
    """Four legs' traded-minute log closes: a common gap process u (bps) per hour plus per-minute noise."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=60 * n_hours, freq="min", tz="UTC")
    hour = np.arange(len(idx)) // 60
    u = rng.normal(0, 20, n_hours)[hour]  # bps, shared by BTC and ETH on venue a
    base = np.cumsum(rng.normal(0, 1e-4, len(idx)))
    logs = {}
    for venue in ("a", "b"):
        for asset in ("BTC", "ETH"):
            noise = rng.normal(0, 2e-4, len(idx))
            lp = base + noise + (u * 1e-4 if venue == "a" else 0.0)
            keep = rng.random(len(idx)) < traded_frac
            if (venue, asset) == ("b", "ETH"):
                keep &= idx.minute != 59  # b/ETH never trades in minute :59
            else:
                keep |= idx.minute == 59
            logs[(venue, asset)] = pd.Series(lp, idx)[keep]
    return logs, idx


def test_sync_variant_needs_all_four_legs_in_the_final_minute():
    logs, idx = minute_logs()
    hour_index = pd.date_range(idx[0], idx[-1].floor("h"), freq="h", tz="UTC")
    h = {k: N.series_hourly(v, hour_index) for k, v in logs.items()}
    gaps = N.pair_gaps(h, "a", "b")
    assert gaps["sync"].notna().sum().sum() == 0  # b/ETH is never traded at :59
    assert gaps["median"].notna().all(axis=1).mean() > 0.95 and gaps["last"].notna().all(axis=1).mean() > 0.95


def test_sync_variant_matches_final_minute_close_when_all_legs_trade():
    logs, idx = minute_logs()
    logs[("b", "ETH")] = pd.concat([logs[("b", "ETH")], pd.Series(0.0, idx[idx.minute == 59])]).sort_index()
    logs[("b", "ETH")] = logs[("b", "ETH")][~logs[("b", "ETH")].index.duplicated(keep="last")]
    hour_index = pd.date_range(idx[0], idx[-1].floor("h"), freq="h", tz="UTC")
    h = {k: N.series_hourly(v, hour_index) for k, v in logs.items()}
    g = N.pair_gaps(h, "a", "b")["sync"].dropna()
    assert len(g) == 300
    t = idx[idx.minute == 59][3]
    assert g.loc[t.floor("h"), "BTC"] == pytest.approx(1e4 * (logs[("a", "BTC")][t] - logs[("b", "BTC")][t]))


def test_median_and_last_conventions_differ_on_a_planted_hour():
    idx = pd.date_range("2020-01-01 00:00", periods=60, freq="min", tz="UTC")
    s = pd.Series(np.r_[np.zeros(55), np.full(5, 0.01)], idx)
    h = N.series_hourly(s, pd.DatetimeIndex([idx[0]]))
    assert h["median"].iloc[0] == 0.0 and h["last"].iloc[0] == 0.01 and h["sync"].iloc[0] == 0.01


def test_common_gap_is_detected_and_independent_gaps_are_not():
    rng = np.random.default_rng(1)
    common = rng.normal(0, 10, 2000)
    shared = pd.DataFrame({"BTC": common + rng.normal(0, 1, 2000), "ETH": common + rng.normal(0, 1, 2000)})
    indep = pd.DataFrame({"BTC": rng.normal(0, 10, 2000), "ETH": rng.normal(0, 10, 2000)})
    assert N.common_share(shared) > 0.95 and abs(N.common_share(indep)) < 0.1
    assert N.agreement(shared)["explained_share"] > 0.95 and N.agreement(indep)["explained_share"] < 0.1


def test_autocorrelation_of_an_ar1_series():
    rng = np.random.default_rng(2)
    x = np.zeros(4000)
    for i in range(1, len(x)):
        x[i] = 0.8 * x[i - 1] + rng.normal()
    s = pd.Series(x, pd.date_range("2020-01-01", periods=len(x), freq="D"))
    assert N.autocorr(s, 1) == pytest.approx(0.8, abs=0.05) and N.autocorr(s, 7) == pytest.approx(0.8 ** 7, abs=0.06)


def test_cross_correlation_peak_recovers_a_planted_lag():
    rng = np.random.default_rng(3)
    idx = pd.date_range("2022-06-01", periods=3000, freq="min", tz="UTC")
    x = pd.Series(rng.normal(size=len(idx)), idx)
    y = x.shift(4).fillna(0) + 0.1 * pd.Series(rng.normal(size=len(idx)), idx)  # y lags x by 4 minutes
    assert N.cross_corr_peak(x, y)["peak_lag_min"] == 4


def test_tick_ignores_float_noise_and_scales_to_bps():
    idx = pd.date_range("2020-01-01", periods=2000, freq="min", tz="UTC")
    rng = np.random.default_rng(4)
    px = pd.Series(10000 + 0.5 * rng.integers(-5, 6, len(idx)).cumsum() % 100, idx)
    px.iloc[10] += 1e-9
    t = N.tick_by_year(px)[2020]
    assert t["tick"] == pytest.approx(0.5) and t["tick_bps"] == pytest.approx(1e4 * 0.5 / px.median())


def test_fee_step_function_and_band():
    sched = {"venues": {"x": [{"effective_from": "2020-01-01", "taker_pct": 0.2}, {"effective_from": "2020-07-01", "taker_pct": 0.5}],
                        "y": [{"effective_from": "2019-01-01", "taker_pct": 0.1}]}}
    idx = pd.DatetimeIndex(["2020-06-30 23:00", "2020-07-01 00:00"], tz="UTC")
    assert list(N.band_bps(sched, "x", "y", idx)) == pytest.approx([30.0, 60.0])


def test_fee_schedule_entries_are_sourced_and_flagged():
    fees = json.loads(N.FEES.read_text())
    assert set(fees["venues"]) == {"bitfinex", "coinbase", "bitstamp"}
    for entries in fees["venues"].values():
        assert entries == sorted(entries, key=lambda e: e["effective_from"]) and entries[0]["effective_from"] <= "2017-01-01"
        for e in entries:
            assert e["status"] in {"secondary", "inferred", "unverified"} and e["note"] and isinstance(e["urls"], list)
            assert e["status"] == "unverified" or e["urls"]
            assert 0 < e["taker_pct"] < 1


def test_committed_outputs_are_current():
    assert M.NUMBERS.read_text() == M.numbers() and M.TABLE.read_text() == M.table(), "run `uv run python -m www_paper.noise_macros`"
    names = re.findall(r"\\newcommand\{\\(NumN\w+)\}", M.NUMBERS.read_text())
    assert len(names) > 60 and len(names) == len(set(names))
    b = json.loads(M.BOUNDS.read_text())
    assert b["fee_schedule_sha256"] == hashlib.sha256(N.FEES.read_bytes()).hexdigest(), "fee schedule changed; rerun noise_bounds"
    assert set(b["pairs"]) == {f"{a}-{c}" for a, c in N.PAIRS} and all(len(v) == 7 for v in b["pairs"].values())


def test_noise_bounds_regenerate_from_raw_data(tmp_path):
    if not (ROOT / "data/raw/bitfinex").is_dir():
        pytest.skip("raw minute data is not on this machine")
    out = tmp_path / "noise_bounds.json"
    assert N.main(["--out", str(out)]) == 0
    assert out.read_text() == N.OUTPUT.read_text()
