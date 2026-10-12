"""Fixed evaluation harness for submission-readiness loops (adapted from the autoresearch pattern).

This is the read-only "prepare.py" of the loop described in autoresearch/program.md: an editing
loop may change the manuscript or presentation code, then runs this gate and keeps the change
only if the gate does not regress. The gate scores compliance and integrity only. It never reads
or scores empirical results (effect sizes, intervals, p-values), so a keep/discard loop cannot
turn into a specification search.

Prints a `key: value` summary block (grep-able like autoresearch's run log); exit code 0 iff
every hard check passes.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).parents[2]
PAPER = ROOT / "paper"
BUILD = PAPER / "build"
MAX_BODY_PAGES = 8      # WWW 2027 long paper: 8 pages of main text, references excluded
MAX_TOTAL_PAGES = 12    # including references and appendix
IDENTITY_FILE = ROOT / ".gate_identity"  # git-ignored; one identifying string per line (names, handles)
GENERIC_LEAKS = [r"github\.com/", r"\\author\{(?!Anonymous)", r"Acknowledg"]
REQUIRED_DOCCLASS = r"\documentclass[sigconf,review,anonymous]{acmart}"


@dataclass
class Gate:
    checks: dict[str, bool] = field(default_factory=dict)
    metrics: dict[str, object] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(self.checks.values())


def body_pages(page_texts: list[str]) -> int | None:
    """1-based index of the page whose text starts the REFERENCES section (that page included)."""
    for i, text in enumerate(page_texts, 1):
        if re.search(r"^\s*REFERENCES\s*$", text, re.M):
            return i
    return None


def identity_patterns(path: Path = IDENTITY_FILE) -> list[str]:
    if not path.exists():
        return []
    return [re.escape(s.strip()) for s in path.read_text().splitlines() if s.strip() and not s.startswith("#")]


def leaks(text: str, patterns: list[str]) -> list[str]:
    return sorted({p for p in patterns if re.search(p, text, re.I)})


def docclass_ok(tex: str) -> bool:
    return re.sub(r"\s", "", REQUIRED_DOCCLASS) in re.sub(r"\s", "", tex)


def first_page_mentions_web(page_texts: list[str]) -> bool:
    return bool(page_texts) and re.search(r"\bWeb\b", page_texts[0]) is not None


def _pdf_pages(pdf: Path) -> list[str]:
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True,
                                                         check=True).stdout).group(1))
    return [subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), str(pdf), "-"], capture_output=True, text=True,
                           check=True).stdout for i in range(1, n + 1)]


def run(skip_tests: bool = False) -> Gate:
    g = Gate()
    tex = (PAPER / "main.tex").read_text()
    g.checks["docclass_anonymous_review"] = docclass_ok(tex)
    if not skip_tests:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-W", "error::DeprecationWarning",
                            "-W", "error::FutureWarning"], cwd=ROOT, capture_output=True, text=True)
        tail = (r.stdout.strip().splitlines() or [""])[-1]
        g.checks["tests_pass"] = r.returncode == 0
        g.metrics["tests_summary"] = tail
    if not (shutil.which("tectonic") and shutil.which("pdfinfo")):
        g.checks["pdf_built"] = False
        g.notes.append("tectonic or poppler (pdfinfo/pdftotext) not found")
        return g
    BUILD.mkdir(exist_ok=True)
    r = subprocess.run(["tectonic", "-X", "compile", "main.tex", "--outdir", str(BUILD)], cwd=PAPER,
                       capture_output=True, text=True)
    pdf = BUILD / "main.pdf"
    g.checks["pdf_built"] = r.returncode == 0 and pdf.exists()
    if not g.checks["pdf_built"]:
        g.notes.append((r.stderr or r.stdout)[-2000:])
        return g
    log = r.stdout + r.stderr
    g.metrics["undefined_refs_or_cites"] = len(re.findall(r"undefined (?:reference|citation)|Citation .* undefined", log))
    g.metrics["overfull_boxes"] = len(re.findall(r"Overfull \\hbox", log))
    pages = _pdf_pages(pdf)
    body = body_pages(pages)
    g.metrics["total_pages"] = len(pages)
    g.metrics["body_pages"] = body
    g.checks["body_pages_le_8"] = body is not None and body <= MAX_BODY_PAGES
    g.checks["total_pages_le_12"] = len(pages) <= MAX_TOTAL_PAGES
    g.checks["no_undefined_refs"] = g.metrics["undefined_refs_or_cites"] == 0
    text = "\n".join(pages)
    found = leaks(text, identity_patterns()) + leaks(tex, GENERIC_LEAKS)
    g.checks["anonymity_scan_clean"] = not found
    g.metrics["anonymity_identity_patterns"] = len(identity_patterns())
    if found:
        g.notes.append(f"anonymity leaks: {len(found)} pattern(s) matched (patterns not echoed)")
    g.metrics["first_page_mentions_web"] = first_page_mentions_web(pages)  # advisory lint, not a hard check
    return g


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()
    g = run(skip_tests=args.skip_tests)
    print("---")
    for k, v in g.checks.items():
        print(f"{k + ':':32s}{int(v)}")
    for k, v in g.metrics.items():
        print(f"{k + ':':32s}{v}")
    print(f"{'gate_pass:':32s}{int(g.passed)}")
    for n in g.notes:
        print("note:", n)
    sys.exit(0 if g.passed else 1)


if __name__ == "__main__":
    main()
