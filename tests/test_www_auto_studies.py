"""Synthetic checks for the UNIT-TD studies (T4 diagnostic and T2 fusion under injected unit bias). No real data needed."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from www_auto import panel as P
from www_auto import studies as S

DEV = ("BTC", "ETH", "LTC", "BCH", "ETC", "XLM")


def synth(start="2018-01-01", end="2021-03-01 23:00", bfx_offset=None, seed=0, assets=DEV, noise_bps=1.0):
    """Three venues sharing one set of true prices; bitfinex optionally has an hourly unit offset (bps) on every asset.
    Bitstamp only lists BTC and ETH, as in the real panel."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, end, freq="h", tz="UTC", name="timestamp_utc")
    t = len(idx)
    off = np.zeros(t) if bfx_offset is None else np.asarray(bfx_offset(idx), float)
    raw = {}
    base = {a: 5.0 + np.cumsum(rng.normal(0, 0.003, t)) for a in assets}
    for venue in S.T2_VENUES:
        cols = {}
        for a in assets:
            if venue == "bitstamp" and a not in ("BTC", "ETH"):
                continue
            p = base[a] + rng.normal(0, noise_bps / 1e4, t)
            if venue == "bitfinex":
                p = p + off / 1e4
            cols[a] = p
            cols[a + "_vol"] = rng.uniform(1, 2, t) * (3.0 if venue == "coinbase" else 1.0)
        raw[venue] = pd.DataFrame(cols, index=idx)
    return raw


# ---------------------------------------------------------------- injection and paths

def test_inject_shifts_only_chosen_venues_by_the_path():
    p = np.zeros((4, 3))
    out = S.inject(p, [0, 2], np.array([0.0, 100.0, 200.0, 400.0]))
    assert np.allclose(out[:, 1], 0)
    assert np.allclose(out[:, 0], [0, 0.01, 0.02, 0.04])
    assert np.allclose(out[:, 2], out[:, 0])
    assert np.all(p == 0)  # input untouched


def test_constant_and_replay_paths():
    assert np.allclose(S.constant_path(50, 5), 50)
    gap = pd.Series([10.0, np.nan, 30.0, 40.0])
    path = S.replay_path(gap, 10)
    assert path[1] == pytest.approx(20.0)  # interpolated
    assert np.allclose(path[:4], [10, 20, 30, 40])
    assert np.allclose(path[4:8], path[:4])  # replayed by hour of episode, cycled


def test_replay_gap_comes_from_the_bitfinex_bitstamp_btc_episode():
    raw = synth(bfx_offset=lambda idx: np.where(idx < pd.Timestamp("2019-06-01", tz="UTC"), 80.0, 0.0), noise_bps=0.0)
    gap = S.replay_gap_from_panel(raw)
    assert gap.index.min() >= pd.Timestamp(S.REPLAY_START, tz="UTC") and gap.index.max() <= pd.Timestamp(S.REPLAY_END, tz="UTC")
    assert gap.median() == pytest.approx(80.0, abs=1e-6)


# ---------------------------------------------------------------- fusers

def test_median_and_vwap():
    p = np.array([[0.0, 0.0, 0.01], [0.0, 0.003, 0.01]])
    assert np.allclose(S.fuse_median(p), [0.0, 0.003])
    v = np.array([[1.0, 1.0, 2.0], [1.0, 1.0, 2.0]])
    assert np.allclose(S.fuse_vwap(p, v), [0.005, (0.003 + 0.02) / 4])


def test_median_breaks_down_at_two_of_three_but_not_one():
    rng = np.random.default_rng(1)
    base = rng.normal(0, 0.01, 500)
    prices = np.column_stack([base, base, base])
    truth = S.truth_median(prices)
    one = S.fuse_median(S.inject(prices, [0], np.full(500, 800.0)))
    two = S.fuse_median(S.inject(prices, [0, 1], np.full(500, 800.0)))
    assert np.abs(one - truth).max() == 0
    assert np.allclose(1e4 * (two - truth), 800.0)


def test_crh_downweights_the_biased_source_and_is_causal():
    rng = np.random.default_rng(2)
    n = 24 * 6
    base = np.cumsum(rng.normal(0, 0.001, n))
    prices = {"A": np.column_stack([base + rng.normal(0, 1e-4, n) for _ in range(3)])}
    prices["A"][:, 0] += 0.05  # source 0 biased by 500 bps
    days = pd.date_range("2021-01-01", periods=n, freq="h", tz="UTC").normalize().asi8
    out = S.fuse_crh(prices, days)["A"]
    w = S.crh_weights(1e4 * prices["A"][:24])
    assert w[0] < w[1] and w[0] < w[2]
    assert np.allclose(out[:24], prices["A"][:24].mean(axis=1))  # day 1 uses equal weights
    later = prices["A"].copy()
    later[100:, :] += 1.0  # change the future only
    out2 = S.fuse_crh({"A": later}, days)["A"]
    assert np.allclose(out[:100], out2[:100])


def test_crh_weights_equal_when_all_sources_agree():
    x = np.tile(np.linspace(0, 1, 10)[:, None], (1, 3))
    assert np.allclose(S.crh_weights(x), 1.0)


def test_cluster_labels_chain_and_tolerance():
    off = np.array([[0.0, 5.0, 100.0], [0.0, 8.0, 16.0], [0.0, 50.0, 100.0]])
    lab = S.cluster_labels(off, tol=10.0)
    assert list(lab[0]) == [0, 0, 2]
    assert list(lab[1]) == [0, 0, 0]  # single linkage chains 0-8-16
    assert list(lab[2]) == [0, 1, 2]


def test_smooth_offsets_is_causal():
    x = np.random.default_rng(0).normal(size=(60, 3))
    y = x.copy()
    y[40:] = 99
    assert np.allclose(S.smooth_offsets(x, 10)[:40], S.smooth_offsets(y, 10)[:40])


def test_unit_aware_median_with_exact_offsets_returns_numeraire_unit():
    base = np.linspace(0, 0.1, 50)
    off = np.array([100.0, 0.0, 100.0])  # venues 0 and 2 share a biased dollar; venue 1 is the numeraire
    prices = base[:, None] + off[None, :] / 1e4
    offs = np.tile(off - 0.0, (50, 1))
    # offsets are relative to the numeraire (venue 1), so removing them puts every venue in venue 1's unit
    assert np.allclose(S.fuse_unit_aware_median(prices, offs), base)


def test_unit_aware_cluster_recovers_ratios_and_the_partition_when_two_share_a_bias():
    n = 200
    rng = np.random.default_rng(3)
    btc, eth = 10 + np.cumsum(rng.normal(0, 0.002, n)), 7 + np.cumsum(rng.normal(0, 0.002, n))
    bias = np.array([0.0, 0.0, 300.0])  # only venue 2 differs ... then the majority (0, 1) is the numeraire
    pb, pe = (btc[:, None] + bias / 1e4), (eth[:, None] + bias / 1e4)
    offs = np.tile(np.array([0.0, 0.0, 300.0]) - 0.0, (n, 1))
    vols = np.ones((n, 3))
    fb, lab = S.fuse_unit_aware_cluster(pb, offs, vols)
    fe, _ = S.fuse_unit_aware_cluster(pe, offs, vols)
    assert np.allclose(fb, btc) and np.allclose(fe, eth)
    assert (lab == np.array([0, 0, 2])).all()
    # two of three biased: the majority unit is the numeraire, the output is in the biased dollar, the ratio is exact
    bias2 = np.array([300.0, 300.0, 0.0])
    pb2, pe2 = btc[:, None] + bias2 / 1e4, eth[:, None] + bias2 / 1e4
    offs2 = np.tile(np.array([300.0, 300.0, 0.0]) - 0.0, (n, 1))
    # the estimator reports offsets relative to its own reference (venue 2 here); cluster alignment is relative anyway
    fb2, lab2 = S.fuse_unit_aware_cluster(pb2, offs2, vols)
    fe2, _ = S.fuse_unit_aware_cluster(pe2, offs2, vols)
    assert (lab2 == np.array([0, 0, 2])).all()
    assert np.allclose(fb2, btc + 0.03) and np.allclose(fe2 - fb2, eth - btc)
    assert S.partition_accuracy({"BTC": lab2}, [0, 1], 3) == 1.0
    assert S.partition_accuracy({"BTC": lab2}, [0], 3) == 0.0


def test_cluster_numeraire_tie_goes_to_the_most_liquid():
    base = np.zeros(5)
    offs = np.tile(np.array([0.0, 100.0, 200.0]), (5, 1))  # three singleton clusters
    prices = base[:, None] + offs / 1e4
    vols = np.tile(np.array([1.0, 5.0, 2.0]), (5, 1))
    fused, _ = S.fuse_unit_aware_cluster(prices, offs, vols)
    assert np.allclose(fused, 0.01)  # venue 1's unit (most liquid), all aligned there


def test_default_estimator_is_zero_with_a_single_asset_and_b2_gap_is_not():
    raw = synth(start="2021-01-01", end="2021-01-20 23:00", bfx_offset=lambda i: np.full(len(i), 60.0), noise_bps=0.0)
    one = {v: raw[v][["ETH", "ETH_vol"]] for v in raw}
    assert np.allclose(S.default_estimator()(one, "coinbase").to_numpy(), 0.0)
    u = S.b2_median_gap(one, "coinbase")
    assert u["bitfinex"].median() == pytest.approx(60.0, abs=1e-6) and (u["coinbase"] == 0).all()


# ---------------------------------------------------------------- T2 end to end

def test_run_t2_small_synthetic_panel():
    raw = synth(start="2018-09-01", end="2021-01-31 23:00", noise_bps=0.5)
    res = S.run_t2(raw, estimators={"b2": S.b2_median_gap}, deltas=(100, 800), ks=(1, 2), start="2021-01-01", end="2021-01-31 23:00")
    rec = {(r["k"], r["shape"], r["delta_bps"], r["fuser"]): r for r in res["records"]}
    # median is immune at k=1 and exactly off by delta at k=2
    assert rec[(1, "constant", 800, "median")]["p95_abs_err_bps"] < 5
    assert rec[(2, "constant", 800, "median")]["p95_abs_err_bps"] == pytest.approx(800, abs=1e-6)
    # the volume-weighted mean moves in proportion to the biased venue's weight
    assert rec[(1, "constant", 800, "vwap")]["p95_abs_err_bps"] > 100
    # cluster fusion repairs a single biased venue regardless of which venue it is
    assert rec[(1, "constant", 800, "ua_cluster[b2]")]["p95_abs_err_bps"] < 10
    # ... while unit-aware median with a fixed (possibly biased) reference does not always
    assert rec[(1, "constant", 800, "ua_median[b2]")]["worst_combo_p95_abs_err_bps"] > 700
    # at k=2 the ratio is intact for every fuser, and the output is in the biased (majority) unit
    for f in ("median", "ua_cluster[b2]"):
        assert rec[(2, "constant", 800, f)]["ratio_p95_abs_err_bps"] < 10
    assert rec[(2, "constant", 800, "ua_cluster[b2]")]["vs_majority_unit_p95_abs_err_bps"] < 10
    assert res["breakdown"]["k=1"]["median"]["pooled"] is None
    assert res["breakdown"]["k=2"]["median"]["pooled"] == 100
    assert res["breakdown"]["k=1"]["vwap"]["pooled"] == 100 or res["breakdown"]["k=1"]["vwap"]["pooled"] == 800
    assert any(c["partition_accuracy"] > 0.9 for c in res["cluster"])
    assert "| Fuser |" in S.t2_markdown(res)


def test_breakdown_picks_smallest_delta_over_50():
    recs = [{"k": 1, "shape": "constant", "delta_bps": d, "fuser": "f", "p95_abs_err_bps": e, "worst_combo_p95_abs_err_bps": e + 1}
            for d, e in ((25, 20.0), (50, 49.5), (100, 80.0), (200, 160.0))]
    recs.append({"k": 1, "shape": "realistic", "delta_bps": None, "fuser": "f", "p95_abs_err_bps": 999.0, "worst_combo_p95_abs_err_bps": 999.0})
    assert S.breakdown(recs)["k=1"]["f"] == {"pooled": 100, "worst_combo": 50}


# ---------------------------------------------------------------- T4

def test_classify_thresholds():
    assert S.classify(0.5, 3.0) == "separate dollar"
    assert S.classify(0.9, 2.9) == "mixed"
    assert S.classify(0.49, 50.0) == "mixed"
    assert S.classify(0.1, 50.0) == "shared dollar"
    assert S.classify(-0.3, 0.1) == "shared dollar"
    assert S.classify(float("nan"), 5.0) == "insufficient"
    assert (S.SEPARATE_SHARE_MIN, S.SEPARATE_GAP_MIN_BPS, S.SHARED_SHARE_MAX) == (0.5, 3.0, 0.1)


def test_explained_share_formula():
    g = np.array([10.0, -10.0, 10.0, -10.0])
    assert S.explained_share(g, g) == pytest.approx(1.0)
    assert S.explained_share(g, np.zeros(4)) == pytest.approx(0.0)
    assert S.explained_share(g, np.full(4, np.nan)) == pytest.approx(0.0)  # missing correction counts as none


def test_t4_separates_a_venue_dollar_from_a_shared_one():
    def off(idx):
        o = np.zeros(len(idx))
        o[idx.year == 2018] = 40.0 + 5 * np.sin(np.arange((idx.year == 2018).sum()) / 200)
        return o
    raw = synth(start="2018-01-01", end="2019-12-31 23:00", bfx_offset=off, noise_bps=1.0)
    res = S.t4_unit_diagnostic(raw, estimate_units=S.b2_median_gap, years=(2018, 2019))
    cls = {(r["pair"], r["year"]): r for r in res["rows"]}
    assert cls[("bitfinex-coinbase", 2018)]["classification"] == "separate dollar"
    assert cls[("bitfinex-coinbase", 2018)]["explained_share"] > 0.9
    assert cls[("bitfinex-coinbase", 2019)]["classification"] == "shared dollar"
    assert cls[("coinbase-bitstamp", 2018)]["classification"] == "shared dollar"
    assert cls[("bitfinex-bitstamp", 2018)]["classification"] == "separate dollar"
    # the gap of a shared common unit is perfectly correlated across assets in 2018, uncorrelated in 2019
    assert cls[("bitfinex-coinbase", 2018)]["corr_btc_mean"] > 0.9
    assert abs(cls[("bitfinex-coinbase", 2019)]["corr_btc_mean"]) < 0.3
    md = S.t4_markdown(res)
    assert "separate dollar" in md and "bitfinex-coinbase" in md


def test_t4_default_estimator_runs_and_short_years_are_insufficient():
    raw = synth(start="2018-01-01", end="2018-12-31 23:00", bfx_offset=lambda i: np.full(len(i), 30.0))
    res = S.t4_unit_diagnostic(raw, years=(2018, 2019))
    rows = {(r["pair"], r["year"]): r for r in res["rows"]}
    assert rows[("bitfinex-coinbase", 2019)]["classification"] == "insufficient"
    assert rows[("bitfinex-coinbase", 2018)]["n_hours"] > S.MIN_HOURS


def test_dev_only_guard_drops_test_assets():
    raw = synth(assets=DEV + P.TEST_SCORED)
    clean = S.strip_test_assets(raw)
    for f in clean.values():
        assert not any(c.removesuffix("_vol") in P.TEST_SCORED for c in f.columns)
    res = S.t4_unit_diagnostic(raw, estimate_units=S.b2_median_gap, years=(2019,))
    for r in res["rows"]:
        assert not set(r["assets"]) & set(P.TEST_SCORED)
