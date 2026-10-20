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


def test_generated_numbers_are_current():
    assert OUTPUT.read_text() == build(), "run `uv run python -m www_paper.macros`"
    assert TABLE_OUTPUT.read_text() == build_registry_table(), "run `uv run python -m www_paper.macros`"


def test_registry_table_lists_every_event_and_marks_linked_legs():
    import json
    events = json.loads((ROOT / "configs/event_registry.json").read_text())["events"]
    table = TABLE_OUTPUT.read_text()
    assert all(e["id"] in table for e in events)
    linked_rows = [line for line in table.splitlines() if line.startswith("$\\hookrightarrow$ ")]
    assert len(linked_rows) == sum(e["role"] == "LINKED_LEG" for e in events)
    assert "\\input{generated/registry_table}" in MAIN


def test_every_number_macro_used_is_defined_and_no_literal_bps_values_slip_in():
    defined = set(re.findall(r"\\newcommand\{\\(Num\w+)\}", OUTPUT.read_text() + RESCUE_OUTPUT.read_text() + UNIT_OUTPUT.read_text()))
    used = set(re.findall(r"\\(Num[A-Za-z]+)", MAIN))
    assert used <= defined, sorted(used - defined)
    body = MAIN.split("\\begin{document}", 1)[1]
    # Numbers attached to bps or % must come from macros. Only pre-specified design constants
    # (rule thresholds and the confidence level) may appear as literals.
    design_constants = {"100 bps", "25 bps", "500 bps", "95\\%"}
    literals = set(re.findall(r"\b\d+(?:\.\d+)?\s*(?:bps|\\%)", body))
    assert literals <= design_constants, sorted(literals - design_constants)


def test_every_citation_has_a_bib_entry_and_every_entry_is_cited():
    keys = set(re.findall(r"@\w+\{([^,]+),", (ROOT / "paper/references.bib").read_text()))
    cited = {k.strip() for group in re.findall(r"\\cite\{([^}]+)\}", MAIN) for k in group.split(",")}
    assert cited <= keys, sorted(cited - keys)
    assert keys <= cited, sorted(keys - cited)


def test_labels_resolve_and_pending_sections_are_marked():
    generated = "".join(p.read_text() for p in (ROOT / "paper/generated").glob("*.tex"))
    labels = set(re.findall(r"\\label\{([^}]+)\}", MAIN + generated))
    refs = set(re.findall(r"\\ref\{([^}]+)\}", MAIN))
    assert refs <= labels
    assert "Executable Capacity: Method and Limits" in MAIN and "No exchange capacity figures are reported" in MAIN
    assert "descriptive" in MAIN.split("\\begin{abstract}")[1].split("\\end{abstract}")[0]


def test_coverage_table_is_current_balanced_and_included():
    table = COVERAGE_TABLE_OUTPUT.read_text()
    assert table == build_coverage_table(), "run `uv run python -m www_paper.macros`"
    assert table.count("{") == table.count("}")
    assert "\\input{generated/coverage_table}" in MAIN
    assert "BTCUSDE & N & N & N & N" in table  # the USDe triangle gap is shown, not hidden


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


def test_results_table_and_markdown_are_current_and_included():
    from www_paper.macros import RESULTS_MD_OUTPUT, RESULTS_TABLE_OUTPUT, build_results_markdown, build_results_table
    assert RESULTS_TABLE_OUTPUT.read_text() == build_results_table(), "run `uv run python -m www_paper.macros`"
    assert RESULTS_MD_OUTPUT.read_text() == build_results_markdown()
    assert "\\input{generated/results_table}" in MAIN
    protocols = list((ROOT / "reports/events").glob("*_protocol.json"))
    assert RESULTS_TABLE_OUTPUT.read_text().count("\\\\") == len(protocols) + 1  # header + one row per event


def test_robustness_table_is_current_and_included():
    from www_paper.macros import ROBUSTNESS_TABLE_OUTPUT, build_robustness_table
    assert ROBUSTNESS_TABLE_OUTPUT.read_text() == build_robustness_table()
    assert "\\input{generated/robustness_table}" in MAIN


def test_mechanism_table_is_current_included_and_labels_the_assumption():
    from www_paper.macros import (MECHANISM_MD_OUTPUT, MECHANISM_TABLE_OUTPUT, build_mechanism_markdown,
                                  build_mechanism_table)
    table = MECHANISM_TABLE_OUTPUT.read_text()
    assert table == build_mechanism_table() and MECHANISM_MD_OUTPUT.read_text() == build_mechanism_markdown()
    assert "\\input{generated/mechanism_table}" in MAIN and "emph{assumed}" in table
    assert "NumClosedBaseRate" in MAIN  # the base-rate caveat must accompany the redemption-hours column
    assert "{76}" in OUTPUT.read_text()  # 128 of 168 weekly hours fall outside 9:00-17:00 weekdays


def test_onchain_capacity_table_current_included_and_scoped():
    from www_paper.macros import CAPACITY_TABLE_OUTPUT, build_capacity_table
    table = CAPACITY_TABLE_OUTPUT.read_text()
    assert table == build_capacity_table() and "\\input{generated/onchain_capacity_table}" in MAIN
    assert "ON-CHAIN ONLY" in table and "not CEX--DEX capacity" in table


def test_rescue_numbers_and_tables_are_current():
    from www_paper.rescue_macros import (DECOMP_TABLE, FIAT_TABLE, NUMBERS, PHASE_TABLE, decomposition_table,
                                         fiat_table, numbers, phase_table)
    assert NUMBERS.read_text() == numbers() and PHASE_TABLE.read_text() == phase_table()
    assert DECOMP_TABLE.read_text() == decomposition_table() and "\\input{generated/decomposition_table}" in MAIN
    from www_paper.rescue_macros import MONITOR_TABLE, SENS_TABLE, monitor_table, sensitivity_table
    assert MONITOR_TABLE.read_text() == monitor_table() and SENS_TABLE.read_text() == sensitivity_table()
    assert "\\input{generated/monitor_sensitivity_table}" in MAIN and "---" not in MAIN.split("\\begin{document}")[1]
    assert FIAT_TABLE.read_text() == fiat_table()
    assert "\\input{generated/ledger_phase_table}" in MAIN and "\\input{generated/fiat_rail_table}" in MAIN


def test_submission_abstract_is_generated_from_the_paper():
    from www_paper.abstract_text import OUTPUT, build
    assert OUTPUT.read_text() == build(), "run `uv run python -m www_paper.abstract_text`"
    text = OUTPUT.read_text()
    assert "\\" not in text.split("**Abstract")[1] and "Num" not in text.split("**Abstract")[1]
