from pathlib import Path

from www_paper.gate import body_pages, docclass_ok, first_page_mentions_web, identity_patterns, leaks

ROOT = Path(__file__).parents[1]


def test_body_pages_is_the_page_where_references_start():
    pages = ["1 INTRODUCTION\nWeb", "text", "11 REPRODUCIBILITY\n\nREFERENCES\n[1] x", "[9] y"]
    assert body_pages(pages) == 3
    assert body_pages(["no refs here", "in-text mention of references only"]) is None
    top = ["1 INTRODUCTION", "text", "Same Name, Different Unit\nWWW \u201927, 2027,\n12\nREFERENCES\n[1] x"]
    assert body_pages(top) == 2  # references open a fresh page: the body ends on the page before


def test_docclass_check_ignores_whitespace_and_requires_anonymous_review():
    assert docclass_ok(r"\documentclass[sigconf, review, anonymous]{acmart}")
    assert not docclass_ok(r"\documentclass[sigconf,review]{acmart}")
    assert docclass_ok((ROOT / "paper/main.tex").read_text())


def test_identity_patterns_are_escaped_and_skip_comments(tmp_path):
    f = tmp_path / "ids"
    f.write_text("# comment\nJane Q. Doe\n\nhandle123\n")
    pats = identity_patterns(f)
    assert len(pats) == 2
    assert leaks("by jane q. doe", pats) and not leaks("Jane Qx Doe", pats)
    assert identity_patterns(tmp_path / "missing") == []


def test_web_lint_reads_first_page_only():
    assert first_page_mentions_web(["the open Web", "x"])
    assert not first_page_mentions_web(["webhook only", "Web on page two"])
