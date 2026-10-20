"""UNIT-TD harness on synthetic panels (no raw data needed)."""

import json

import numpy as np
import pandas as pd
import pytest

from www_auto import harness as H
from www_auto import panel as P
from www_auto.estimator import estimate_units

ASSETS = ["BTC", "ETH", "LTC", "BCH", "ETC", "XLM", "XRP", "LINK", "SOL", "DOGE", "ADA"]  # last five are test assets
INDEX = pd.date_range("2018-12-01", periods=3000, freq="h", tz="UTC", name="timestamp_utc")


def synthetic(unit_bf=True, unit_bst=False, noise=0.02, seed=0):
    rng = np.random.default_rng(seed)
    n = len(INDEX)
    u_bf = np.cumsum(rng.normal(0, 0.8, n)) if unit_bf else np.zeros(n)  # bps, random walk
    u_bst = np.cumsum(rng.normal(0, 0.8, n)) if unit_bst else np.zeros(n)
    latent = {a: np.log(100) + np.cumsum(rng.normal(0, 3e-3, n)) for a in ASSETS}
    raw = {}
    for venue, unit, assets in (("bitfinex", u_bf, ASSETS), ("coinbase", 0 * u_bf, ASSETS), ("bitstamp", u_bst, ["BTC", "ETH"])):
        cols = {}
        for a in assets:
            cols[a] = latent[a] + (unit + rng.normal(0, noise, n)) / 1e4
            cols[a + "_vol"] = rng.uniform(1, 2, n)
        if venue == "bitfinex":
            cols["USDT"], cols["USDT_vol"] = rng.normal(0, 1e-4, n), rng.uniform(1, 2, n)
            cols["ETHBTC"], cols["ETHBTC_vol"] = latent["ETH"] - latent["BTC"], rng.uniform(1, 2, n)
        raw[venue] = pd.DataFrame(cols, index=INDEX)
    return raw, u_bf, u_bst


def factory(fn):
    return lambda: fn


def run(raw, fn, mode="dev", seed=5):
    return H.evaluate(raw, factory(fn), mode, seed)


def test_planted_unit_is_recovered():
    raw, _, _ = synthetic()
    res = run(raw, estimate_units)
    assert res["main"]["score"] > 0.99
    assert res["all_checks"] and res["causal_ok"] and res["perm_ok"] and res["coverage_ok"]
    assert res["b0"] == 0.0 and res["b2"] > 0.99 and res["b1"] > 0.9


def test_planted_unit_recovered_in_control_pair_too():
    raw, _, _ = synthetic(unit_bst=True)
    # control pair coinbase vs bitstamp: bitstamp only has BTC and ETH, so BTC's gap carries the unit.
    # Uses the plain median-gap estimator: the loop-edited estimator shrinks to 0 when a venue has one visible asset.
    from www_auto.studies import b2_median_gap
    assert run(raw, b2_median_gap)["control"]["score"] > 0.99


def test_zero_unit_scores_about_zero_and_control_not_negative_for_no_op():
    raw, _, _ = synthetic(unit_bf=False)
    zero = lambda panel, num: pd.DataFrame(0.0, index=panel[num].index, columns=list(panel))  # noqa: E731
    res = run(raw, zero)
    assert res["main"]["score"] == 0.0 and res["control"]["score"] == 0.0
    # the median estimator only chases idiosyncratic noise here: bounded, not a big positive score
    res = run(raw, estimate_units)
    assert -1.0 < res["main"]["score"] < 0.1


def test_leaky_estimator_fails_causal():
    raw, _, _ = synthetic()
    leaky = lambda panel, num: estimate_units(panel, num).shift(-1)  # noqa: E731
    res = run(raw, leaky)
    assert not res["causal_ok"] and not res["all_checks"]


def test_full_sample_statistic_fails_causal():
    raw, _, _ = synthetic()
    leaky = lambda panel, num: estimate_units(panel, num) - estimate_units(panel, num).mean()  # noqa: E731
    assert not run(raw, leaky)["causal_ok"]


def test_venue_name_dependent_estimator_fails_perm():
    raw, _, _ = synthetic()

    def named(panel, num):
        out = estimate_units(panel, num)
        if "v0" in out.columns and num != "v0":
            out["v0"] = out["v0"] + 3.0
        return out
    res = run(raw, named)
    assert not res["perm_ok"] and not res["all_checks"]


def test_missing_output_cannot_inflate_score_and_fails_coverage():
    raw, _, _ = synthetic()

    def sparse(panel, num):
        out = estimate_units(panel, num)
        out.iloc[::10] = np.nan
        out[num] = 0.0
        return out
    res = run(raw, sparse)
    assert not res["coverage_ok"]
    assert res["main"]["score"] < 0.95  # NaN hours count as no correction


def test_estimator_never_sees_held_out_or_test_assets_in_dev():
    raw, _, _ = synthetic()
    seen = []

    def spy(panel, num):
        seen.append({c.removesuffix("_vol") for f in panel.values() for c in f.columns})
        return estimate_units(panel, num)
    run(raw, spy, mode="dev")
    allseen = set().union(*seen)
    assert not allseen & set(P.TEST_SCORED)
    # every call lacks at least its held-out asset; the first five calls are the dev assets (ETH first)
    assert all(len(s & set(P.DEV_SCORED)) <= 4 for s in seen)
    assert {"BTC", "USDT"} <= allseen


def test_final_mode_scores_test_assets_with_dev_information_set():
    raw, _, _ = synthetic()
    seen = []

    def spy(panel, num):
        seen.append({c.removesuffix("_vol") for f in panel.values() for c in f.columns})
        return estimate_units(panel, num)
    res = run(raw, spy, mode="final")
    assert set(res["main"]["by_asset"]) == set(P.TEST_SCORED)
    assert not set().union(*seen) & set(P.TEST_SCORED)


def test_ethbtc_removed_when_eth_held_out():
    raw, _, _ = synthetic()
    kept = H.estimator_input(raw, "ETH", "dev")
    assert "ETHBTC" not in kept["bitfinex"].columns and "ETH" not in kept["bitfinex"].columns
    assert "ETHBTC" in H.estimator_input(raw, "LTC", "dev")["bitfinex"].columns


def test_load_panel_dev_reads_no_test_columns(tmp_path, monkeypatch):
    raw, _, _ = synthetic()
    flat = pd.concat({v: f for v, f in raw.items()}, axis=1)
    flat.columns = [f"{v}|{c}" for v, c in flat.columns]
    path = tmp_path / "p.parquet"
    flat.to_parquet(path)
    path.with_name(P.META_PATH.name).write_text(json.dumps({"build_version": P.BUILD_VERSION}))
    dev, _ = P.load_panel("dev", path)
    assert not any(c.removesuffix("_vol") in P.TEST_SCORED for f in dev.values() for c in f.columns)
    final, _ = P.load_panel("final", path)
    assert "XRP" in final["bitfinex"].columns


def test_final_refuses_without_unlock(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(P, "load_panel", lambda *a, **k: pytest.fail("data must not be loaded"))
    assert H.main(["--final"], root=tmp_path) == 2
    assert "FINAL_UNLOCK" in capsys.readouterr().err


def test_main_cli_on_synthetic_panel_prints_keys(tmp_path, capsys):
    raw, _, _ = synthetic()
    flat = pd.concat({v: f for v, f in raw.items()}, axis=1)
    flat.columns = [f"{v}|{c}" for v, c in flat.columns]
    path = tmp_path / "p.parquet"
    flat.to_parquet(path)
    path.with_name(P.META_PATH.name).write_text(json.dumps({"build_version": P.BUILD_VERSION}))
    code = H.main(["--seed", "3"], factory=factory(estimate_units), panel_path=path)
    out = capsys.readouterr().out
    assert code == 0
    for key in ("dev_score:", "control_score:", "causal_ok: True", "perm_ok: True", "coverage_ok: True", "all_checks: True",
                "runtime_s:", "b0_dev:", "b1_dev:", "b2_dev:", "b1_control:", "b2_control:", "asset_ETH:", "year_2019:"):
        assert key in out


def test_cleaning_spike_and_zero_volume_rules():
    idx = pd.date_range("2020-01-01", periods=8, freq="h", tz="UTC")
    p = pd.Series([0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.5, 0.9], index=idx)  # hour 2 isolated spike; hour 6 is not (next jumps too)
    v = pd.Series([1.0, 1, 1, 1, 0, 1, 1, 1], index=idx)  # hour 4 has zero volume
    counts = {}
    out = P.clean_series(pd.DataFrame({"p": p, "v": v}), counts)
    assert counts["dropped_zero_volume_or_bad_price"] == 1 and counts["dropped_isolated_spike"] == 1
    assert np.isnan(out["p"].loc[idx[2]]) and np.isnan(out["p"].loc[idx[4]]) and out["p"].loc[idx[6]] == 0.5
