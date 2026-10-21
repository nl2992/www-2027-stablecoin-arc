"""Generated unit-side numbers, tables and figure must be current and reproducible."""

import hashlib
import re
from pathlib import Path

import pytest

from www_auto import panel as P
from www_paper import unit_macros as U
from www_paper.figures import FIAT_LABELS, PROBE_JSON, unit_rate

ROOT = Path(__file__).parents[1]
GENERATED = [(U.NUMBERS, U.numbers), (U.DIAG_TABLE, U.diagnostic_table), (U.HELDOUT_TABLE, U.heldout_table),
             (U.DETECTOR_TABLE, U.detector_table), (U.ORACLE_TABLE, U.oracle_table), (U.T2_TABLE, U.t2_table),
             (U.LABEL_TABLE, U.label_table), (U.ANCHOR_TABLE, U.anchor_table)]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("path,build", GENERATED, ids=lambda x: getattr(x, "name", None) or getattr(x, "__name__", ""))
def test_generated_unit_files_are_current(path, build):
    assert path.read_text() == build(), "run `uv run python -m www_paper.unit_macros`"


def test_unit_macros_regenerate_byte_identically(tmp_path, monkeypatch):
    first = [build() for _, build in GENERATED]
    second = [build() for _, build in GENERATED]
    assert first == second


def test_every_macro_names_its_source_and_is_defined_once():
    lines = [ln for ln in U.NUMBERS.read_text().splitlines() if ln.startswith("\\newcommand")]
    names = [re.match(r"\\newcommand\{\\(\w+)\}", ln).group(1) for ln in lines]
    assert len(names) == len(set(names)) and all(n.startswith("NumU") and n.isalpha() for n in names)
    assert all(re.search(r"\} % \S", ln) for ln in lines)


def test_required_macros_and_headline_values():
    text = U.NUMBERS.read_text()
    required = ["NumUBfxBstCorrMin", "NumUCbBstGapMax", "NumUCbBstShareMax", "NumUTestPct", "NumUControlScore", "NumUDevScore",
                "NumUTestBaseOne", "NumUTestBaseTwo", "NumUTestYearMinPct", "NumUTestYearMaxPct", "NumULoopIter", "NumULoopKept",
                "NumUDetFaBfx", "NumUBaseFaBfx", "NumUDetCaught", "NumUDetCovered", "NumUFirstAlarmDate", "NumUNyagDate",
                "NumUAlarmNyagMonths", "NumUCbLastAlarm", "NumUOracleSlopeBtc", "NumUOracleSlopeEth", "NumUUsdcPeakBps",
                "NumUUsdcHoursGeHundred", "NumUMarAlarmDays"] + [f"NumUTest{a.title()}Pct" for a in U.TEST_ASSETS]
    for name in required:
        assert f"\\newcommand{{\\{name}}}" in text, name

    def val(name):
        return re.search(rf"\\newcommand\{{\\{name}\}}\{{([^}}]*)\}}", text).group(1)

    assert val("NumUTestPct") == "85" and val("NumULoopIter") == "12" and val("NumUMarAlarmDays") == "0"
    assert val("NumUControlScore") == "0.000" and val("NumUAlarmNyagMonths") == "6.5"
    assert float(val("NumUBfxBstCorrMinExact")) >= 0.949  # the abstract's "0.95 or more" holds only after rounding


def test_probe_reproduces_the_reference_values():
    import json
    pairs = json.loads(PROBE_JSON.read_text())["pairs"]
    bb, cb = pairs["bitfinex-bitstamp"], pairs["coinbase-bitstamp"]
    assert [round(bb[str(y)]["daily_corr"], 2) for y in range(2017, 2024)] == [0.99, 1.00, 1.00, 0.97, 0.95, 0.96, 0.99]
    assert [round(cb[str(y)]["median_abs_gap_btc_bps"], 1) for y in range(2019, 2024)] == [2.3, 1.6, 1.3, 1.2, 0.7]
    assert [round(bb[str(y)]["explained_share"], 2) for y in range(2017, 2024)] == [0.95, 0.99, 0.99, 0.79, 0.63, 0.77, 0.80]


def test_probe_and_dev_record_regenerate_from_raw_data(tmp_path):
    raw = ROOT / "data/raw/bitfinex"
    if not raw.is_dir() or not P.PANEL_PATH.is_file():
        pytest.skip("raw minute data or the UNIT-TD panel cache is not on this machine")
    from www_auto import probe, record_dev
    out = tmp_path / "probe.json"
    assert probe.main(["--out", str(out)]) == 0
    assert out.read_text() == PROBE_JSON.read_text()
    assert "\n".join(record_dev.record()) + "\n" == record_dev.OUTPUT.read_text()


def test_dev_record_never_touches_the_locked_test():
    src = (ROOT / "src/www_auto/record_dev.py").read_text()
    assert '"final"' not in src.replace('"final" mode', "") and "TEST_SCORED" not in src and "--final" not in src.split('"""')[2]
    assert not (ROOT / "autoresearch/FINAL_UNLOCK").exists()


def test_unit_rate_figure_is_deterministic_and_committed(tmp_path):
    a, b = unit_rate(PROBE_JSON, FIAT_LABELS, tmp_path / "a.pdf"), unit_rate(PROBE_JSON, FIAT_LABELS, tmp_path / "b.pdf")
    assert digest(a) == digest(b)
    assert digest(a) == digest(ROOT / "paper/figures/unit_rate.pdf")
