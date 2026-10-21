"""Robust evaluation: generated files current, JSON for the frozen estimator, bootstrap deterministic, weekly blocks reproduce posthoc.json."""

import hashlib
import json
import re

import numpy as np
import pandas as pd
import pytest

from www_auto import harness as H
from www_auto import posthoc_eval as X
from www_auto import robust_eval as R
from www_paper import robust_macros as M


def test_generated_robust_files_are_current():
    assert M.NUMBERS.read_text() == M.numbers(), "run `uv run python -m www_paper.robust_macros`"
    assert M.TABLE.read_text() == M.table(), "run `uv run python -m www_paper.robust_macros`"


def test_robust_json_is_for_the_frozen_estimator():
    d = json.loads(R.OUT.read_text())
    assert d["estimator_sha256"] == hashlib.sha256(H.EST_PATH.read_bytes()).hexdigest()
    assert d["bootstrap"]["draws"] == 1000
    assert d["honest"]["chosen_constant"] in R.CANDIDATES


def test_every_robust_macro_names_its_source():
    lines = [ln for ln in M.NUMBERS.read_text().splitlines() if ln.startswith("\\newcommand")]
    names = [re.match(r"\\newcommand\{\\(\w+)\}", ln).group(1) for ln in lines]
    assert len(names) == len(set(names)) and all(n.startswith("NumR") and n.isalpha() for n in names)
    assert all(re.search(r"\} % \S", ln) for ln in lines)


def test_weekly_block_results_reproduce_posthoc_json():
    r = json.loads(R.OUT.read_text())["blocks"]["week"]
    p = json.loads(X.OUT.read_text())
    a, c = p["bitfinex_coinbase"]["test"]["bootstrap"], p["controls"]["coinbase-bitstamp"]["bootstrap"]
    for g, m in (("pooled", "est"), ("pooled", "diff"), ("asset:ADA", "est"), ("asset:XRP", "est")):
        for k in ("point", "lo", "hi"):
            assert r["test"][g][m][k] == pytest.approx(a[g][m][k], abs=1e-9)
    for m in ("est", "diff"):
        for k in ("point", "lo", "hi"):
            assert r["control"]["pooled"][m][k] == pytest.approx(c["pooled"][m][k], abs=1e-9)


def test_block_bootstrap_deterministic_and_block_ids():
    rng = np.random.default_rng(1)
    idx = pd.date_range("2019-01-01", periods=24 * 7 * 60, freq="h", tz="UTC")
    g = pd.Series(rng.normal(0, 5, len(idx)), index=idx)
    gs, us = {"A": g}, {"A": g * 0.5 + rng.normal(0, 1, len(idx))}
    d = R.add_blocks(X.cells(gs, us), {"A": idx})
    assert d["month"].nunique() == 14 and d["quarter"].nunique() == 5
    parts = {"est": d, "b2": d.assign(e2=d["g2"])}
    for blk in R.BLOCKS:
        assert R.boot(parts, blk) == R.boot(parts, blk)
    assert R.boot(parts, "week")["pooled"] == X.bootstrap(parts, n_boot=R.N_BOOT, seed=R.BLOCK_SEED)["pooled"]


def test_shrinkage_substitution_is_exact_at_the_frozen_constant():
    pytest.importorskip("pyarrow")
    if not X.P.PANEL_PATH.exists():
        pytest.skip("panel cache not built")
    raw = X.load_raw(False)
    a = H.call_estimator(R.estimator_factory(R.FROZEN_CONSTANT), raw, "LINK", "final", X.SEED)
    b = H.call_estimator(H.file_estimator_factory(), raw, "LINK", "final", X.SEED)
    assert H._max_diff(a, b) == 0.0
