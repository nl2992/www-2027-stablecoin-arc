"""The short letter in paper_frl/: it builds, every \\Num macro it uses is defined, every citation resolves."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
FRL = ROOT / "paper_frl"
GEN = ROOT / "paper/generated"
TEX = (FRL / "main.tex").read_text()
BIB = (ROOT / "paper/references.bib").read_text()


def _sources() -> str:
    """main.tex plus every generated file it inputs."""
    parts = [TEX]
    for name in re.findall(r"\\input\{\.\./paper/generated/([^}]+)\}", TEX):
        parts.append((GEN / (name if name.endswith(".tex") else name + ".tex")).read_text())
    return "\n".join(parts)


def test_every_num_macro_is_defined():
    used = set(re.findall(r"\\(Num[A-Za-z]+)", TEX))
    defined = set()
    for name in re.findall(r"\\input\{\.\./paper/generated/([^}]+)\}", TEX):
        defined |= set(re.findall(r"\\newcommand\{\\(Num[A-Za-z]+)\}", (GEN / (name + ".tex")).read_text()))
    assert used and not used - defined


def test_every_citation_resolves():
    keys = {k.strip() for grp in re.findall(r"\\cite[a-z]*(?:\[[^\]]*\])*\{([^}]+)\}", TEX) for k in grp.split(",")}
    bib = set(re.findall(r"@\w+\{([^,]+),", BIB))
    assert keys and not keys - bib


def test_length_limits():
    abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", TEX, re.S).group(1)
    assert len(re.sub(r"\\Num[A-Za-z]+", "1", abstract).split()) <= 100
    exhibits = len(re.findall(r"\\begin\{table\*?\}", _sources()))
    assert exhibits <= 4


def test_no_hand_typed_results():
    body = TEX.split("\\section{Introduction}")[1]
    body = re.sub(r"\\begin\{table\}.*?\\end\{table\}", "", body, flags=re.S)
    body = re.sub(r"\\(?:cite[tp]?|ref|label|input|bibliography\w*)\{[^}]*\}|\$[^$]*\$|\\Num[A-Za-z]+|\d{4}(?:-\d{2}-\d{2})?(?:--\d{2,4})?", "", body)
    # allow years, section numbers and the 1,000 bootstrap draws and "50"/"20" bps thresholds named in the design
    stray = re.findall(r"(?<![\w.])\d+(?:\.\d+)?%?", body)
    assert all(s in {"50", "20", "95", "1", "000"} for s in stray), stray


@pytest.mark.skipif(shutil.which("tectonic") is None, reason="tectonic not installed")
def test_paper_builds(tmp_path):
    r = subprocess.run(["tectonic", "--outdir", str(tmp_path), "main.tex"], cwd=FRL, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    assert (tmp_path / "main.pdf").stat().st_size > 10_000
