"""Oracle audit pilot: offline tests (log decoding, error metrics, lag/staleness, budget enforcement)."""

import numpy as np
import pandas as pd
import pytest

from www_audit import pilot
from www_c2.archive_run import Budgeted, StopRun
from www_c2.rpc import RpcError


def word(n: int) -> str:
    return (n % (1 << 256)).to_bytes(32, "big").hex()


def make_log(answer: int, round_id: int, updated_at: int, block: int = 16_780_000) -> dict:
    return {"topics": [pilot.topic0(), "0x" + word(answer), "0x" + word(round_id)], "data": "0x" + word(updated_at),
            "blockNumber": hex(block), "transactionHash": "0x" + "ab" * 32, "logIndex": "0x7"}


def test_topic0_is_the_published_answer_updated_hash():
    assert pilot.topic0() == "0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f"


def test_decode_answer_updated_fixture():
    d = pilot.decode_answer_updated(make_log(99_876_543, (5 << 64) | 1234, 1_678_500_000))
    assert d == {"answer": 99_876_543, "round_id": (5 << 64) | 1234, "updated_at": 1_678_500_000, "block": 16_780_000,
                 "tx_hash": "0x" + "ab" * 32, "log_index": 7}


def test_decode_negative_answer_and_wrong_topic():
    assert pilot.decode_answer_updated(make_log(-5, 1, 2))["answer"] == -5
    bad = make_log(1, 1, 1)
    bad["topics"][0] = "0x" + "00" * 32
    with pytest.raises(ValueError):
        pilot.decode_answer_updated(bad)


def test_decode_string_and_round_data():
    text = "USDC / USD"
    payload = "0x" + word(32) + word(len(text)) + text.encode().hex().ljust(64, "0")
    assert pilot.decode_string(payload) == text
    res = "0x" + "".join(word(v) for v in (7, 99_999_000, 100, 200, 7))
    assert pilot.decode_round_data(res) == {"round_id": 7, "answer": 99_999_000, "started_at": 100, "updated_at": 200, "answered_in_round": 7}


def test_fetch_logs_halves_chunk_when_range_rejected():
    calls = []

    def call(method, params):
        f = params[0]
        lo, hi = int(f["fromBlock"], 16), int(f["toBlock"], 16)
        calls.append(hi - lo + 1)
        if hi - lo + 1 > 100:
            raise RpcError("range too large")
        return [make_log(1, lo, lo, block=lo)]

    logs = pilot.fetch_logs(call, "0x" + "11" * 20, 0, 399, chunk=400, min_chunk=50)
    assert [int(x["blockNumber"], 16) for x in logs] == [0, 100, 200, 300]
    assert calls == [400, 200, 100, 100, 100, 100]


def test_budget_enforced_and_endpoint_free_log():
    b = Budgeted(lambda m, p: "0x1", 3, 0)
    for _ in range(3):
        b("eth_chainId", [])
    with pytest.raises(StopRun):
        b("eth_chainId", [])
    assert b.used == 3


def test_error_metrics():
    ref = pd.Series(1.0, index=pd.date_range("2023-03-10", periods=4, freq="h", tz="UTC"))
    feed = ref * np.exp(np.array([0.0, 0.0060, -0.0120, 0.0020]))
    err = pilot.bps_error(feed, ref)
    assert err.round(6).tolist() == [0.0, 60.0, -120.0, 20.0]
    s = pilot.error_summary(err)
    assert s["n_ge_50"] == 2 and s["n_ge_100"] == 1 and s["max_abs_bps"] == pytest.approx(120.0)
    assert s["max_signed_bps"] == pytest.approx(-120.0) and s["median_abs_bps"] == pytest.approx(40.0)


def rounds_df(times, prices):
    return pd.DataFrame({"round_id": range(len(times)), "price": prices, "updated_at": times, "started_at": times})


def test_feed_as_of_and_lag():
    t0 = int(pd.Timestamp("2023-03-10", tz="UTC").timestamp())
    labels = pd.date_range("2023-03-10", periods=300, freq="1min", tz="UTC")
    true = pd.Series(np.where(np.arange(300) < 100, 1.00, 0.90), index=labels)
    # the reference drops in bar 100; the feed publishes at t0+130min, visible from the bar closing at that instant (bar 129)
    r = rounds_df([t0 - 10, t0 + 130 * 60], [1.00, 0.90])
    price, age = pilot.feed_as_of(r, labels)
    assert price.iloc[128] == 1.00 and price.iloc[129] == 0.90
    assert age.iloc[0] == 70 and age.iloc[129] == 0
    lag = pilot.best_lag(price, true, max_lag=60)
    assert lag["lag_min"] == 29 and lag["mae_at_best_bps"] < 1e-6


def test_staleness_counts_minutes_after_reference_move():
    t0 = int(pd.Timestamp("2023-03-10", tz="UTC").timestamp())
    labels = pd.date_range("2023-03-10", periods=120, freq="1min", tz="UTC")
    wide = pd.date_range("2023-03-09 23:00", periods=240, freq="1min", tz="UTC")
    ref = pd.Series(np.where(np.arange(240) < 120, 1.00, 0.98), index=wide)  # 200 bps drop at minute 60 of the window
    r = rounds_df([t0 - 60, t0 + 90 * 60], [1.00, 0.98])
    s = pilot.staleness(r, ref, labels)
    assert s["minutes_ref_moved_gt_50bps_since_last_update"] == 29
    assert s["age_max_min"] == pytest.approx(90.0, abs=1.5)


def test_ols_and_contamination_recovers_slope():
    idx = pd.date_range("2023-03-10", periods=48, freq="h", tz="UTC")
    D = pd.Series(np.linspace(0, 300, 48), index=idx)
    usdc = pd.Series(np.exp(-D / 1e4), index=idx)
    err = 0.8 * D + 3.0
    c = pilot.contamination(err, usdc)
    assert c["levels"]["slope"] == pytest.approx(0.8) and c["levels"]["r2"] == pytest.approx(1.0)
    assert c["hours_with_D_ge_100bps"] > 0


def test_infer_policy_from_rounds():
    t = np.cumsum([0, 3600, 3600, 600, 3600])
    r = rounds_df(t.tolist(), [1.0, 1.0, 1.0, 1.006, 1.006])
    p = pilot.infer_policy(r)
    assert p["heartbeat_max_gap_min"] == 60.0 and p["deviation_triggered_move_min_bps"] == pytest.approx(59.8, abs=0.1)
