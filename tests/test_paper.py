"""Structural consistency checks between the manuscript, generated numbers and bibliography."""

import re
from pathlib import Path

from www_paper.macros import (
    COVERAGE_TABLE_OUTPUT, OUTPUT, TABLE_OUTPUT, build, build_coverage_table, build_registry_table,
)

ROOT = Path(__file__).parents[1]
MAIN = (ROOT / "paper/main.tex").read_text()
RESCUE_OUTPUT = ROOT / "paper/generated/rescue_numbers.tex"
UNIT_OUTPUT = ROOT / "paper/generated/unit_numbers.tex"
EXTRA_OUTPUTS = [ROOT / f"paper/generated/{n}_numbers.tex" for n in ("posthoc", "sweep", "noise", "anchor_ext", "robust", "td", "bench", "theory", "robust_anchor", "kimchi", "q1", "q2", "panel")]


def test_generated_numbers_are_current():
    assert OUTPUT.read_text() == build(), "run `uv run python -m www_paper.macros`"
    assert TABLE_OUTPUT.read_text() == build_registry_table(), "run `uv run python -m www_paper.macros`"


def test_generated_tables_not_in_the_paper_are_still_current():
    from www_paper.macros import (COVERAGE_TABLE_OUTPUT, RESULTS_TABLE_OUTPUT, ROBUSTNESS_TABLE_OUTPUT, MECHANISM_TABLE_OUTPUT,
                                  CAPACITY_TABLE_OUTPUT, build_capacity_table, build_coverage_table, build_mechanism_table,
                                  build_results_table, build_robustness_table)
    assert COVERAGE_TABLE_OUTPUT.read_text() == build_coverage_table()
    assert RESULTS_TABLE_OUTPUT.read_text() == build_results_table()
    assert ROBUSTNESS_TABLE_OUTPUT.read_text() == build_robustness_table()
    assert MECHANISM_TABLE_OUTPUT.read_text() == build_mechanism_table()
    assert CAPACITY_TABLE_OUTPUT.read_text() == build_capacity_table()


def test_paper_includes_the_unit_tables_and_figure():
    for name in ("unit_diagnostic_table", "heldout_ci_table",
                 "anchor_table", "anchor_ext_table", "bench_table",
                 "td_realdata_table", "theory_table", "sim_table", "theory_section"):
        assert f"\\input{{generated/{name}}}" in MAIN, name
    assert "figures/unit_rate.pdf" in MAIN and "\\input{generated/unit_numbers}" in MAIN


def test_every_number_macro_used_is_defined_and_no_literal_bps_values_slip_in():
    defined = set(re.findall(r"\\newcommand\{\\(Num\w+)\}", OUTPUT.read_text() + RESCUE_OUTPUT.read_text() + UNIT_OUTPUT.read_text()
                                                                        + "".join(p.read_text() for p in EXTRA_OUTPUTS)))
    used = set(re.findall(r"\\(Num[A-Za-z]+)", MAIN))
    assert used <= defined, sorted(used - defined)
    body = MAIN.split("\\begin{document}", 1)[1]
    # Numbers attached to bps or % must come from macros. Only pre-specified design constants
    # (rule thresholds and the confidence level) may appear as literals.
    design_constants = {"100 bps", "25 bps", "500 bps", "95\\%"}
    # An explicitly marked illustrative block (toy numbers, never results) is exempt.
    body = re.sub(r"% BEGIN ILLUSTRATIVE.*?% END ILLUSTRATIVE", "", body, flags=re.S)
    literals = set(re.findall(r"\b\d+(?:\.\d+)?\s*(?:bps|\\%)", body))
    assert literals <= design_constants, sorted(literals - design_constants)


def test_every_citation_has_a_bib_entry_and_every_entry_is_cited():
    keys = set(re.findall(r"@\w+\{([^,]+),", (ROOT / "paper/references.bib").read_text()))
    cited = {k.strip() for group in re.findall(r"\\cite\{([^}]+)\}", MAIN) for k in group.split(",")}
    assert cited <= keys, sorted(cited - keys)
    assert keys <= cited, sorted(keys - cited)


def test_labels_resolve_and_no_em_dashes():
    generated = "".join(p.read_text() for p in (ROOT / "paper/generated").glob("*.tex"))
    labels = set(re.findall(r"\\label\{([^}]+)\}", MAIN + generated))
    refs = set(re.findall(r"\\ref\{([^}]+)\}", MAIN))
    assert refs <= labels
    assert "---" not in MAIN.split("\\begin{document}")[1]  # no em dashes anywhere in the manuscript


def test_braces_and_environments_balance_without_a_tex_compiler():
    """No TeX toolchain is installed, so check the cheapest structural invariants directly."""
    sources = [MAIN] + [p.read_text() for p in (ROOT / "paper/generated").glob("*.tex")]
    total_envs = 0
    for text in sources:
        stripped = re.sub(r"\\[{}%]", "", text)       # drop escaped braces and escaped percent signs
        stripped = re.sub(r"%.*", "", stripped)          # then drop comments
        assert stripped.count("{") == stripped.count("}")
        begins = re.findall(r"\\begin\{([^}]+)\}", stripped)
        ends = re.findall(r"\\end\{([^}]+)\}", stripped)
        assert sorted(begins) == sorted(ends)
        total_envs += len(begins)
    assert total_envs >= 8  # the check must actually see the document, figure, table and tabular environments


def test_rescue_numbers_and_tables_are_current():
    from www_paper.rescue_macros import (DECOMP_TABLE, FIAT_TABLE, NUMBERS, PHASE_TABLE, decomposition_table,
                                         fiat_table, numbers, phase_table)
    assert NUMBERS.read_text() == numbers() and PHASE_TABLE.read_text() == phase_table()
    assert DECOMP_TABLE.read_text() == decomposition_table()  # still generated; no longer in the manuscript
    from www_paper.rescue_macros import MONITOR_TABLE, SENS_TABLE, monitor_table, sensitivity_table
    assert MONITOR_TABLE.read_text() == monitor_table() and SENS_TABLE.read_text() == sensitivity_table()
    assert FIAT_TABLE.read_text() == fiat_table()


def test_submission_abstract_is_generated_from_the_paper():
    from www_paper.abstract_text import OUTPUT, build
    assert OUTPUT.read_text() == build(), "run `uv run python -m www_paper.abstract_text`"
    text = OUTPUT.read_text()
    assert "\\" not in text.split("**Abstract")[1] and "Num" not in text.split("**Abstract")[1]


def test_v6_structure_and_claims():
    from www_paper import bench_macros as B
    assert B.NUMBERS.read_text() == B.numbers() and B.TABLE.read_text() == B.table(), "run `uv run python -m www_paper.bench_macros`"
    body = MAIN.split("\\begin{document}", 1)[1]
    abstract = body.split("\\begin{abstract}")[1].split("\\end{abstract}")[0]
    assert len(re.sub(r"\\Num[A-Za-z]+\{\}", "1", abstract).split()) <= 300
    assert "one for one" not in abstract  # lambda = 1 is rejected on Bitfinex; say close to one
    assert "tab:fixed" in body and "tab:bench" in body
    stable = B.parse_log(B._one("final_stable_*.log"))
    assert stable["placebo_ok"] == "False"  # the paper says the STABLE method failed its own calm check
