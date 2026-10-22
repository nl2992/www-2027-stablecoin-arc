"""Q1: frozen-bytes check, freshness of generated files, determinism, gate integrity."""
import json
import re
import subprocess

import pytest

from www_paper import q1_macros as M
from www_q1 import gate as G
from www_q1 import panel as P
from www_q1 import run as R

ROOT = P.REPO
needs_panel = pytest.mark.skipif(not P.PANEL_PATH.exists(), reason="derived Q1 panel not built")


def test_frozen_fuser_is_byte_identical_to_ca38772():
    try:
        committed = subprocess.run(["git", "show", "ca38772:src/www_stable/fuser.py"], cwd=ROOT, capture_output=True,
                                   check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("commit ca38772 not available")
    assert R.FROZEN.read_bytes() == committed


def test_generated_files_are_current():
    assert M.NUMBERS.read_text() == M.numbers()
    assert M.TABLE.read_text() == M.table()
    assert M.numbers() == M.numbers()


def test_every_macro_names_its_source_and_is_defined_once():
    lines = [ln for ln in M.NUMBERS.read_text().splitlines() if ln.startswith("\\newcommand")]
    names = [re.match(r"\\newcommand\{\\(\w+)\}", ln).group(1) for ln in lines]
    assert len(names) == len(set(names)) and all(n.startswith("NumQ") and n.isalpha() for n in names)
    assert all(re.search(r"\} % reports/q1/\S+\.json \S", ln) for ln in lines)


def test_gate_and_results_agree_with_prereg_rules():
    g = json.loads(G.OUT.read_text())
    assert g["kept_events"] == [e for e, v in g["events"].items() if v["s_hi_hours"] >= 40]
    assert g["proceed"] == (g["pooled_s_hi_hours"] >= 200 and g["n_kept"] >= 3)
    r = json.loads(R.OUT.read_text())
    assert r["bootstrap"] == {"draws": 1000, "seed": 20261022, "block": "event-UTC-day"}
    assert r["s_hi_hours"] == {e: g["events"][e]["s_hi_hours"] for e in g["kept_events"]}


@needs_panel
def test_gate_is_deterministic_and_matches_committed_file():
    assert G.run() == json.loads(G.OUT.read_text())


@needs_panel
def test_gate_never_loads_the_reference():
    markets, side, ref, _ = P.load_all(with_reference=False)
    assert ref is None and not any("kraken" in k for k in markets)


@needs_panel
def test_locked_run_reproduces_committed_results():
    assert R.run() == json.loads(R.OUT.read_text())
