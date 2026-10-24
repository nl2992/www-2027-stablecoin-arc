"""Q2: causality, calibration on synthetic calm data, freshness of generated files, determinism."""
import json
import re

import numpy as np
import pandas as pd
import pytest

from www_paper import q2_macros as M
from www_q1 import panel as Q1P
from www_q2 import calibrate as K
from www_q2 import common as C
from www_q2 import detectors as D
from www_q2 import labels as L
from www_q2 import run as R

needs_panel = pytest.mark.skipif(not (Q1P.PANEL_PATH.exists()), reason="derived Q1 panel not built")


def _markets(n=400, seed=1, shift_at=None):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="h", tz="UTC")
    base = np.cumsum(rng.normal(0, 1e-3, n))
    out = {}
    for name, noise in (("a.USD", 1e-4), ("b.USD", 1e-4), ("c.USDT", 1e-4), ("d.USDT", 1e-4)):
        f = pd.DataFrame({"BTC": base + rng.normal(0, noise, n), "ETH": base + rng.normal(0, noise, n),
                          "BTC_vol": rng.uniform(1, 2, n)}, index=idx)
        if shift_at is not None and name.endswith("USDT"):
            f.loc[idx[shift_at:], ["BTC", "ETH"]] += 0.01
        out[name] = f
    return out


def test_detectors_are_causal():
    m = _markets(shift_at=250)
    full_p, full_g = D.pooled_statistic(m, "USDT"), D.single_pair_gap(m, "c.USDT")
    cut = 300
    m2 = {k: v.iloc[:cut] for k, v in m.items()}
    assert np.allclose(D.pooled_statistic(m2, "USDT").to_numpy(), full_p.iloc[:cut].to_numpy(), equal_nan=True)
    g2 = D.single_pair_gap(m2, "c.USDT")
    assert np.allclose(g2.to_numpy(), full_g.iloc[:cut].to_numpy(), equal_nan=True)
    a_full, s_full = D.cusum(full_g, 50.0)
    a_cut, s_cut = D.cusum(g2, 50.0)
    assert (a_full.iloc[:cut].to_numpy() == a_cut.to_numpy()).all()
    assert np.allclose(s_full.iloc[:cut].to_numpy(), s_cut.to_numpy(), equal_nan=True)


def test_detectors_fire_on_a_shift_and_not_before():
    m = _markets(shift_at=250)
    p = D.pooled_statistic(m, "USDT")
    assert p.iloc[:250].abs().max() < 20 and p.iloc[260:].abs().min() > 80
    assert D.cusum(D.single_pair_gap(m, "c.USDT"), 300.0)[0].iloc[:250].sum() == 0


def test_ewma_span3_recursion_and_nan_handling():
    x = pd.Series([0.0, 10.0, np.nan, 10.0])
    e = D.ewma(x)
    assert e.iloc[:2].tolist() == [0.0, 5.0] and np.isnan(e.iloc[2]) and e.iloc[3] == 7.5


def test_episodes_counts_runs():
    f = pd.Series([False, True, True, False, True, False, True, True, True])
    assert D.episodes(f) == 3


def test_calibration_hits_target_on_synthetic_calm_data():
    rng = np.random.default_rng(7)
    n = 20000
    idx = pd.date_range("2020-01-01", periods=n, freq="h", tz="UTC")
    x = pd.Series(rng.standard_t(4, n) * 10, index=idx)
    ncalm = n
    tau, cnt = K.calibrate_threshold([x], ncalm)
    assert cnt <= K.allowed(ncalm) == 20
    assert D.episodes(D.threshold_alarms(x, tau)) == cnt and cnt >= 15  # smallest tau: at or just under the target
    assert all(D.episodes(D.threshold_alarms(x, t)) <= 20 for t in np.linspace(tau, tau * 2, 20))
    h, hc = K.calibrate_cusum([x], ncalm)
    assert hc <= 20 and int(D.cusum(x, h)[0].sum()) == hc
    assert int(D.cusum(x, h - 1.0)[0].sum()) >= hc


def test_segments_split_on_gaps():
    idx = pd.date_range("2020-01-01", periods=10, freq="h", tz="UTC").delete([4, 5])
    assert [len(s) for s in K.segments(idx)] == [4, 4]


def test_onset_needs_three_consecutive_hours():
    idx = pd.date_range("2020-01-01", periods=10, freq="h", tz="UTC")
    d = pd.Series([0, 60, 60, 0, 0, 70, 70, 70, 0, 0], index=idx, dtype=float)
    assert L.onset(d, idx[0], idx[-1]) == idx[5]
    d.iloc[6] = np.nan
    assert L.onset(d, idx[0], idx[-1]) is None


def test_miss_and_verdict_rule():
    boot = {"differences_hours": {"P_minus_S1": {"point": -5, "ci95": [-9, -1]}, "P_minus_S2": {"point": -5, "ci95": [-9, 2]}}}
    v = R.verdict(boot, {"P": 1, "S1": 1, "S2": 1})
    assert v["S1"]["outcome"] == "win" and v["S2"]["outcome"] == "tie"
    assert R.verdict(boot, {"P": 2, "S1": 1, "S2": 1})["S1"]["outcome"] != "win"
    lost = {"differences_hours": {"P_minus_S1": {"point": 5, "ci95": [1, 9]}, "P_minus_S2": {"point": 5, "ci95": [1, 9]}}}
    assert R.verdict(lost, {"P": 1, "S1": 1, "S2": 1})["S1"]["outcome"] == "loss"


def test_bootstrap_is_deterministic_and_preregistered():
    leads = {"P": [-5.0, None, 0.0, 2.0], "S1": [1.0, 3.0, None, 4.0], "S2": [None, None, 5.0, 6.0]}
    assert R.bootstrap(leads) == R.bootstrap(leads)
    b = R.bootstrap(leads)
    assert b["draws"] == 1000 and b["seed"] == 20261023


def test_generated_files_are_current():
    assert M.NUMBERS.read_text() == M.numbers()
    assert M.TABLE.read_text() == M.table()
    assert M.numbers() == M.numbers()


def test_every_macro_names_its_source_and_is_defined_once():
    lines = [ln for ln in M.NUMBERS.read_text().splitlines() if ln.startswith("\\newcommand")]
    names = [re.match(r"\\newcommand\{\\(\w+)\}", ln).group(1) for ln in lines]
    assert len(names) == len(set(names)) and all(n.startswith("NumQT") and n.isalpha() for n in names)
    assert all(re.search(r"\} % reports/q2/\S+\.json \S", ln) for ln in lines)


def test_committed_reports_follow_the_rules():
    cal = json.loads(C.CALIBRATION.read_text())
    assert cal["realised_per_1000_calm_hours"] and all(v <= 1.0 for v in cal["realised_per_1000_calm_hours"].values())
    res = json.loads(C.RESULTS.read_text())
    assert res["bootstrap"]["draws"] == 1000 and res["bootstrap"]["seed"] == 20261023
    assert res["thresholds_bps"] == cal["thresholds_bps"]
    lab = json.loads(C.LABELS.read_text())
    assert res["scored_events"] == lab["scorable"]


@needs_panel
def test_pipeline_reproduces_committed_files():
    assert L.build() == json.loads(C.LABELS.read_text())
    assert K.build() == json.loads(C.CALIBRATION.read_text())
    assert R.run() == json.loads(C.RESULTS.read_text())


@needs_panel
def test_calm_hours_exclude_other_events_and_precede_window():
    ev = C.EVENTS
    for e in ev:
        idx = C.calm_index(e[0])
        lo, _ = C.bounds(e[2], e[3])
        assert idx.max() < lo and idx.min() >= lo - pd.Timedelta(days=30)
