"""Post-hoc uncertainty/baseline evaluation: generated files are current, the logged score reproduces, bootstrap is deterministic."""

import hashlib
import json
import re

import numpy as np
import pandas as pd
import pytest

from www_auto import harness as H
from www_auto import posthoc_eval as X
from www_paper import posthoc_macros as M


def test_generated_posthoc_files_are_current():
    assert M.NUMBERS.read_text() == M.numbers(), "run `uv run python -m www_paper.posthoc_macros`"
    assert M.TABLE.read_text() == M.table(), "run `uv run python -m www_paper.posthoc_macros`"


def test_posthoc_json_is_for_the_frozen_estimator_and_reproduced_the_log():
    d = json.loads(X.OUT.read_text())
    assert d["estimator_sha256"] == hashlib.sha256(H.EST_PATH.read_bytes()).hexdigest()
    assert d["reproduction"]["ok"] and max(r["abs_diff"] for r in d["reproduction"]["checks"].values()) <= 1e-6
    assert d["bootstrap"]["draws"] == 1000


def test_every_posthoc_macro_names_its_source():
    lines = [ln for ln in M.NUMBERS.read_text().splitlines() if ln.startswith("\\newcommand")]
    names = [re.match(r"\\newcommand\{\\(\w+)\}", ln).group(1) for ln in lines]
    assert len(names) == len(set(names)) and all(n.startswith("NumP") and n.isalpha() for n in names)
    assert all(re.search(r"\} % \S", ln) for ln in lines)


def test_logged_final_score_reproduces_live():
    pytest.importorskip("pyarrow")
    if not X.P.PANEL_PATH.exists():
        pytest.skip("panel cache not built")
    a = X.section_a(X.load_raw(False))
    rep = X.reproduction(a, X.parse_log())
    assert rep["ok"], rep
    assert abs(a["test"]["harness_points"]["est"]["score"] - 0.846410) <= 1e-6


def _synthetic_cells(seed):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=24 * 7 * 40, freq="h", tz="UTC")
    gs, us = {}, {}
    for a in ("AAA", "BBB"):
        g = pd.Series(rng.normal(0, 5, len(idx)), index=idx)
        gs[a], us[a] = g, g * 0.5 + rng.normal(0, 1, len(idx))
    return X.cells(gs, us), gs, us


def test_bootstrap_is_deterministic_and_matches_harness_points():
    d, gs, us = _synthetic_cells(1)
    other = d.assign(e2=d["g2"])  # b0-like method
    first = X.bootstrap({"est": d, "b2": other}, n_boot=200, seed=3)
    second = X.bootstrap({"est": d, "b2": other}, n_boot=200, seed=3)
    assert first == second
    assert X.bootstrap({"est": d, "b2": other}, n_boot=200, seed=4) != first
    pooled = first["pooled"]["est"]
    assert abs(pooled["point"] - H.score_parts(gs, us)["score"]) < 1e-12
    assert pooled["lo"] < pooled["point"] < pooled["hi"]
    assert first["pooled"]["diff"]["point"] == pytest.approx(first["pooled"]["est"]["point"] - first["pooled"]["b2"]["point"])


def test_bitstamp_hourly_fetch_skips_pre_listing_pages_and_pages_ascending():
    from www_events.bitstamp import month_bounds
    from www_events.bitstamp_hourly import fetch_bitstamp_hourly
    lo, hi = month_bounds("2017-01")[0], month_bounds("2017-03")[1]
    listed = lo + 1500 * 3600

    def get(url):
        start = int(url.split("start=")[1])
        ts = [t for t in range(max(start, listed), min(start + 1000 * 3600, hi), 3600)]
        return {"data": {"ohlc": [{"timestamp": str(t), "open": "1", "high": "2", "low": "0.5", "close": "1.5",
                                   "volume": "3"} for t in ts]}}
    frame, pages = fetch_bitstamp_hourly("ltcusd", "2017-01", "2017-03", get=get, pause=0)
    assert frame["timestamp"].iloc[0] == listed and frame["timestamp"].iloc[-1] == hi - 3600
    assert frame["timestamp"].is_unique and list(frame.iloc[0, 1:]) == [1.0, 2.0, 0.5, 1.5, 3.0]
