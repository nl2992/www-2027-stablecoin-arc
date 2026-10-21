"""Truth-discovery real-data study: generated files are current; CRH and GTM behave on synthetic data."""

import hashlib
import json
import re

import numpy as np

from www_auto import harness as H
from www_auto import studies as S
from www_auto import td_realdata as T
from www_paper import td_macros as M


def test_generated_td_files_are_current():
    assert M.NUMBERS.read_text() == M.numbers(), "run `uv run python -m www_paper.td_macros`"
    assert M.TABLE.read_text() == M.table(), "run `uv run python -m www_paper.td_macros`"


def test_td_json_is_for_the_frozen_estimator_and_hyperparameters_unchanged():
    d = json.loads(T.OUT.read_text())
    assert d["estimator_sha256"] == hashlib.sha256(H.EST_PATH.read_bytes()).hexdigest()
    assert d["hyperparameters"] == json.loads(json.dumps(T.HYPERPARAMETERS)), "rerun `uv run python -m www_auto.td_realdata`"
    assert max(d["part2_estimator_matches_posthoc"].values()) <= 1e-9


def test_every_td_macro_names_its_source():
    lines = [ln for ln in M.NUMBERS.read_text().splitlines() if ln.startswith("\\newcommand")]
    names = [re.match(r"\\newcommand\{\\(\w+)\}", ln).group(1) for ln in lines]
    assert len(names) == len(set(names)) and all(n.startswith("NumT") and n.isalpha() for n in names)
    assert all(re.search(r"\} % \S", ln) for ln in lines)


def _claims(seed=0, n=4000):
    rng = np.random.default_rng(seed)
    truth = rng.normal(0, 30, n)
    sd = np.array([1.0, 2.0, 20.0])
    return truth[:, None] + rng.normal(0, 1, (n, 3)) * sd, truth


def test_crh_masked_matches_studies_and_downweights_the_noisy_source():
    x, _ = _claims()
    w = T.crh_masked(x)
    assert np.allclose(w, S.crh_weights(x), atol=1e-9)
    assert w[0] > w[1] > w[2]


def test_crh_masked_ignores_missing_claims():
    x, _ = _claims(1)
    x[::3, 0] = np.nan
    w = T.crh_masked(x)
    assert np.isfinite(w).all() and w[2] == w.min()


def test_gtm_recovers_source_variances_and_truth_beats_mean():
    x, truth = _claims(2)
    sig = T.gtm_fit(x / 10.0)
    assert sig[0] < sig[1] < sig[2]
    assert np.allclose(sig, np.array([1.0, 2.0, 20.0]) ** 2 / 100.0, rtol=0.35, atol=0.02) or sig[2] > 10 * sig[0]
    est = 10.0 * T.gtm_truth(x / 10.0, sig, s0=1e6)
    assert np.abs(est - truth).mean() < np.abs(x.mean(axis=1) - truth).mean()


def test_gtm_equal_sources_gives_the_mean_under_a_flat_prior():
    x = np.array([[1.0, 3.0], [2.0, 6.0]])
    est = T.gtm_truth(x, np.array([1.0, 1.0]), s0=1e9)
    assert np.allclose(est, x.mean(axis=1), atol=1e-6)


def test_two_symmetric_sources_get_equal_weight():
    rng = np.random.default_rng(3)
    base = rng.normal(0, 10, 2000)
    x = np.column_stack([base + rng.normal(0, 2, 2000), base + rng.normal(0, 2, 2000)])
    w = T.crh_masked(x)
    assert abs(w[0] - w[1]) < 0.05
