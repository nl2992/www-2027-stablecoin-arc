import hashlib
import re
from pathlib import Path

import pytest

from www_paper import figures_v9 as f9

ROOT = Path(__file__).parents[1]
FIGS = ROOT / "paper/figures"
needs_raw = pytest.mark.skipif(not f9.raw_data_available(), reason="raw exchange files (data/raw) are not committed")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


REPORT_FIGURES = {"robustness_forest.pdf": f9.robustness_forest, "simulation_power.pdf": f9.simulation_power, "q1_errors.pdf": f9.q1_errors}
DATA_FIGURES = {"anchor_scatter.pdf": f9.anchor_scatter, "anchor_timeseries.pdf": f9.anchor_timeseries, "kimchi_gaps.pdf": f9.kimchi_gaps}


@pytest.mark.parametrize("name", sorted(REPORT_FIGURES))
def test_report_figures_are_byte_deterministic_and_fresh(tmp_path, name):
    a, b = REPORT_FIGURES[name](tmp_path / "a.pdf"), REPORT_FIGURES[name](tmp_path / "b.pdf")
    assert digest(a) == digest(b)
    assert digest(a) == digest(FIGS / name), f"{name} is stale: run `uv run python -m www_paper.figures_v9`"


@needs_raw
@pytest.mark.parametrize("name", sorted(DATA_FIGURES))
def test_data_figures_are_byte_deterministic_and_fresh(tmp_path, name):
    a, b = DATA_FIGURES[name](tmp_path / "a.pdf"), DATA_FIGURES[name](tmp_path / "b.pdf")
    assert digest(a) == digest(b)
    assert digest(a) == digest(FIGS / name), f"{name} is stale: run `uv run python -m www_paper.figures_v9`"


def test_every_v9_figure_is_committed_with_fixed_metadata():
    for name in [*REPORT_FIGURES, *DATA_FIGURES]:
        raw = (FIGS / name).read_bytes()
        assert raw.startswith(b"%PDF")
        assert b"/CreationDate" not in raw and b"matplotlib" not in raw


def test_captions_are_current_and_well_formed():
    text = f9.CAPTIONS.read_text()
    assert text == f9.build_captions(), "run `uv run python -m www_paper.figures_v9`"
    names = re.findall(r"\\newcommand\{\\(Cap\w+)\}", text)
    assert names == ["CapAnchorScatter", "CapAnchorTimeseries", "CapRobustnessForest", "CapSimulationPower", "CapQErrors", "CapKimchiGaps"]
    assert "---" not in text and "\u2014" not in text
    stripped = re.sub(r"\\[{}%]", "", text)
    stripped = re.sub(r"%.*", "", stripped)
    assert stripped.count("{") == stripped.count("}")


def test_caption_numbers_come_from_the_reports():
    import json
    text = f9.CAPTIONS.read_text()
    q = json.loads(f9.Q1_RESULTS.read_text())
    assert f"{q['pooled_s_hi']['fuser']['mae']:.1f}" in text and f"{q['pooled_s_hi']['oracle']['mae']:.1f}" in text
    rep = f9.anchor_slopes()
    assert f"{rep['raw']['est']:.2f}" == "0.71" and f"{rep['netted']['est']:.2f}" == "0.97"
    caption = re.search(r"\\newcommand\{\\CapAnchorScatter\}\{(.*)\} %", text).group(1)
    assert "0.71" in caption and "0.97" in caption


def test_forest_rows_are_summary_rows_and_include_the_headline():
    import json
    rows = f9.forest_rows()
    assert len(rows) == 5 + 4 + 3  # windows, instrument sets, references; not the 360 cells
    head = json.loads(f9.ROBUSTNESS.read_text())["headline"]
    hit = [r for r in rows if r["factor"] == "window" and r["headline"]][0]
    assert hit["lo"] == pytest.approx(head["boot_ci95_week"][0]) and hit["hi"] == pytest.approx(head["boot_ci95_week"][1])
    assert hit["lam"] == pytest.approx(head["lam"])
    assert sum(r["headline"] for r in rows) == 3


def test_rail_markers_come_from_the_label_file():
    marks = f9.rail_markers()
    assert str(marks["nyag"].date()) == "2019-04-25"
    assert [m[1] for m in marks["rails"]] == ["BFX-2018-06"]


@needs_raw
def test_recomputed_daily_series_reproduce_the_reported_slopes():
    d = f9.anchor_daily()
    rep = f9.anchor_slopes()
    assert len(d) == rep["n"]
    assert f9._ols_line(d["L"].to_numpy(), d["D"].to_numpy())[0] == pytest.approx(rep["raw"]["est"], abs=1e-9)
    assert f9._ols_line(d["L"].to_numpy(), d["DmX"].to_numpy())[0] == pytest.approx(rep["netted"]["est"], abs=1e-9)


@needs_raw
def test_recomputed_kimchi_premia_reproduce_the_reported_summary():
    import json
    d = f9.kimchi_daily()
    res = json.loads(f9.KIMCHI.read_text())["windows"]
    for key, _ in f9.KIMCHI_WINDOWS:
        lo, hi = res[key]["range"]
        w = d.loc[lo:hi]
        assert int(w["BTC"].notna().sum()) == res[key]["premium"]["BTC"]["days"]
        assert float(w["BTC"].median()) == pytest.approx(res[key]["premium"]["BTC"]["median_bps"])


def test_palette_is_the_okabe_ito_set():
    assert {f9.BLUE, f9.VERMILION, f9.GREEN, f9.ORANGE, f9.SKY, f9.PINK} <= {"#0072B2", "#D55E00", "#009E73", "#E69F00", "#56B4E9", "#CC79A7"}
