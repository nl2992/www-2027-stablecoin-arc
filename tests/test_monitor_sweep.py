"""Monitor operating-curve sweep: freshness, reproduction of the headline point, and figure determinism."""

import hashlib
import json
import re
from pathlib import Path

import pandas as pd
import pytest

from www_paper import sweep_macros as M
from www_paper.sweep_figure import FIGURE, SWEEP as SWEEP_JSON, monitor_sweep
from www_rescue import detector_eval as de
from www_rescue import monitor_sweep as ms

ROOT = Path(__file__).parents[1]
SWEEP = json.loads(SWEEP_JSON.read_text())
EVAL = json.loads((ROOT / "reports/rescue/detector_eval.json").read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_two_asset_rule_needs_both_gaps_with_the_same_sign_and_no_ratio():
    idx = pd.date_range("2020-01-01", periods=6, freq="h", tz="UTC")
    L = pd.Series([120, 120, -120, 120, 90, 500], index=idx, dtype=float)
    S = pd.Series([110, 300, -110, -300, 200, 101], index=idx, dtype=float)
    f = ms.two_asset_flags(L, S, 100.0)
    assert list(f) == [True, True, True, False, False, True]  # 300 vs 120 passes: no agreement ratio
    assert list(ms.two_asset_flags(L.iloc[:3], S.iloc[1:3], 100.0).index) == list(idx[1:3])  # evaluated where both exist


def test_frontier_is_the_cheapest_point_reaching_each_recall():
    pts = [(0.5, 1.0, "a"), (0.5, 0.2, "b"), (1.0, 3.0, "c"), (0.8, 2.0, "d"), (None, 0.1, "e"), (0.0, 0.0, "f")]
    fr = ms.frontier(pts)
    assert [(f["recall"], f["fa_per_venue_year"], f["at"]) for f in fr] == [(0.5, 0.2, "b"), (0.8, 2.0, "d"), (1.0, 3.0, "c")]
    assert ms.min_fa_at(pts, 0.6) == 2.0 and ms.min_fa_at(pts, 1.1) is None


def test_headline_point_reproduces_detector_eval_exactly():
    heads = {"detector": ("detector_a0.25", "100"), "b1": ("b1", "100"), "b2": ("b2", "4"), "b3": ("b3", "100")}
    for venue in ms.VENUES:
        for method, (key, p) in heads.items():
            ref = EVAL["metrics"]["all"][venue].get(method)
            got = SWEEP["sweep"][key][p][venue]
            if ref is None:
                assert got is None
                continue
            assert got["evaluated_hours"] == ref["evaluated_hours"] and got["n_episodes"] == ref["n_episodes"]
            assert got["alarm_days"] == ref["alarm_days"] and got["alarm_day_share"] == ref["alarm_day_share"]
            assert (got["caught"], got["covered_positives"], got["recall"]) == (ref["caught"], ref["covered_positives"], ref["recall"])
            assert got["false_alarm_episodes"] == ref["false_alarms"]["n"]
            assert got["fa_per_venue_year"] == ref["false_alarms"]["per_venue_year"]["total"]
            assert got["unexplained_per_venue_year"] == ref["false_alarms"]["per_venue_year"]["unexplained"]
            assert got["episode_precision"] == ref["episode_precision"] and got["episode_f1"] == ref["episode_f1"]


def test_pooled_counts_are_venue_sums_and_two_asset_shares_detector_hours():
    for key, rows in SWEEP["sweep"].items():
        for row in rows.values():
            parts = [row[v] for v in ms.VENUES if row[v] is not None]
            assert row["pooled"]["false_alarm_episodes"] == sum(p["false_alarm_episodes"] for p in parts)
            assert row["pooled"]["covered_positives"] == sum(p["covered_positives"] for p in parts)
    for t, row in SWEEP["sweep"]["two_asset"].items():
        for v in ms.VENUES:
            assert row[v]["evaluated_hours"] == SWEEP["sweep"]["detector_a0.25"][t][v]["evaluated_hours"]


def test_exposure_explains_the_binance_us_rate_difference():
    pv = SWEEP["exposure"]["per_venue_method"]["binance_us"]
    assert pv["detector"]["false_alarm_episodes"] == pv["b1"]["false_alarm_episodes"] == 1
    assert pv["detector"]["evaluated_hours"] < pv["b1"]["evaluated_hours"]
    assert pv["detector"]["fa_per_venue_year"] > pv["b1"]["fa_per_venue_year"]
    assert pv["detector"]["fa_per_venue_year"] == pv["detector"]["false_alarm_episodes"] / (pv["detector"]["evaluated_hours"] / de.HOURS_PER_YEAR)
    assert SWEEP["exposure"]["binance_us_note"]
    rec = SWEEP["exposure"]["recall_denominators"]
    assert all(r["reference_side_bitstamp_positives"] == 2 for r in rec.values())  # D1: BST labels at every venue


def test_timeline_facts_come_from_data_and_labels():
    tl = SWEEP["timeline"]
    assert tl["first_day_above_100bps_2018H2"] == tl["runs_above_100bps_2018H2"][0]["start"]
    assert tl["label_dates"]["nyag_disclosure"]["first_public_report_date"] == "2019-04-25"
    assert tl["label_dates"]["first_public_deposit_pause_report"]["first_public_report_date"] == "2018-10-11"
    assert tl["first_run_days"] == tl["runs_above_100bps_2018H2"][0]["days"]


@pytest.mark.parametrize("path,build", [(M.NUMBERS, M.numbers), (M.TABLE, M.table)], ids=["numbers", "table"])
def test_generated_sweep_files_are_current(path, build):
    assert path.read_text() == build(), "run `uv run python -m www_paper.sweep_macros`"
    assert build() == build()


def test_every_sweep_macro_names_its_source_and_is_defined_once():
    lines = [ln for ln in M.NUMBERS.read_text().splitlines() if ln.startswith("\\newcommand")]
    names = [re.match(r"\\newcommand\{\\(\w+)\}", ln).group(1) for ln in lines]
    assert len(names) == len(set(names)) and all(n.startswith("NumS") and n.isalpha() for n in names)
    assert all(re.search(r"\} % reports/\S+", ln) for ln in lines)


def test_sweep_figure_is_deterministic_and_committed(tmp_path):
    a, b = monitor_sweep(SWEEP_JSON, tmp_path / "a.pdf"), monitor_sweep(SWEEP_JSON, tmp_path / "b.pdf")
    assert digest(a) == digest(b) == digest(FIGURE)


@pytest.mark.skipif(not (ROOT / "data/raw/bitfinex").exists(), reason="raw candles not on disk")
def test_sweep_json_regenerates_from_raw_data():
    out = ms.run(ROOT / "data/raw", ROOT / "reports/events/acquisition_manifest.json",
                 ROOT / "configs/fiat_rail_labels.json", ROOT / ms.PROBE)
    assert json.dumps(out, indent=1) + "\n" == SWEEP_JSON.read_text()
