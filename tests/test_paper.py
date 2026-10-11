"""Structural consistency checks between the manuscript, generated numbers and bibliography."""

import re
from pathlib import Path

from www_paper.macros import OUTPUT, TABLE_OUTPUT, build, build_registry_table

ROOT = Path(__file__).parents[1]
MAIN = (ROOT / "paper/main.tex").read_text()


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
    defined = set(re.findall(r"\\newcommand\{\\(Num\w+)\}", OUTPUT.read_text()))
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
    generated = TABLE_OUTPUT.read_text()
    labels = set(re.findall(r"\\label\{([^}]+)\}", MAIN + generated))
    refs = set(re.findall(r"\\ref\{([^}]+)\}", MAIN))
    assert refs <= labels
    assert "Executable Capacity [PENDING]" in MAIN
    assert "not yet met" in MAIN
