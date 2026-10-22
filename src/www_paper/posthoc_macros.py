"""Macros and the held-out CI table from reports/unit_td/posthoc.json (``uv run python -m www_auto.posthoc_eval``).

Writes paper/generated/posthoc_numbers.tex (macro prefix NumP) and paper/generated/heldout_ci_table.tex.
Run: ``uv run python -m www_paper.posthoc_macros``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .unit_macros import GEN, HEADER, ROOT, _num

POSTHOC = ROOT / "reports/unit_td/posthoc.json"
NUMBERS = GEN / "posthoc_numbers.tex"
TABLE = GEN / "heldout_ci_table.tex"
SRC = "reports/unit_td/posthoc.json"
DEV_ASSETS = ("ETH", "LTC", "BCH", "ETC", "XLM")
TEST_ASSETS = ("ADA", "DOGE", "LINK", "SOL", "XRP")
CTRL_ASSETS = ("ETH", "LTC", "BCH", "XLM", "LINK", "XRP")
YEAR_WORD = {2017: "TwentySeventeen", 2018: "TwentyEighteen", 2019: "TwentyNineteen", 2020: "TwentyTwenty",
             2021: "TwentyTwentyOne", 2022: "TwentyTwentyTwo", 2023: "TwentyTwentyThree"}
METHOD_WORD = {"b1": "BOne", "b2": "BTwo", "est": "Est", "diff": "Diff"}
CTRL_WORD = {"coinbase-bitstamp": "CbBst", "bitfinex-bitstamp": "BfxBst"}
CTRL_LABEL = {"coinbase-bitstamp": "Control: Coinbase--Bitstamp (shared dollar)",
              "bitfinex-bitstamp": "Control: Bitfinex--Bitstamp (separate dollar)"}


def load() -> dict[str, Any]:
    return json.loads(POSTHOC.read_text())


def _s(v: float, d: int = 3) -> str:
    return _num(v, d)


def _stat_macros(prefix: str, stat: dict[str, float], where: str) -> list[tuple[str, str, str]]:
    return [(prefix, _s(stat["point"]), where), (prefix + "Lo", _s(stat["lo"]), where + " (95% lower)"),
            (prefix + "Hi", _s(stat["hi"]), where + " (95% upper)")]


def _block(tag: str, boot: dict[str, Any], path: str) -> list[tuple[str, str, str]]:
    out = []
    for gname, methods in boot.items():
        kind, _, key = gname.partition(":")
        label = "Pooled" if gname == "pooled" else key if kind == "asset" else YEAR_WORD[int(key)]
        group = "" if gname == "pooled" else ("Asset" if kind == "asset" else "Year")
        if kind == "year" and tag != "Test":
            continue
        for m, stat in methods.items():
            if m == "b0":
                continue
            out += _stat_macros(f"NumP{tag}{group}{label}{METHOD_WORD[m]}", stat, f"{SRC} {path}/{gname}/{m}")
    return out


def numbers() -> str:
    d = load()
    rows: list[tuple[str, str, str]] = []
    a = d["bitfinex_coinbase"]
    rows.append(("NumPBootDraws", str(d["bootstrap"]["draws"]), f"{SRC} bootstrap/draws"))
    rows.append(("NumPReproMaxDiff", f"{max(r['abs_diff'] for r in d['reproduction']['checks'].values()):.1e}",
                 f"{SRC} reproduction/checks abs_diff max against the logged final run"))
    rows += _block("Test", a["test"]["bootstrap"], "bitfinex_coinbase/test/bootstrap")
    rows += _block("Dev", a["dev"]["bootstrap"], "bitfinex_coinbase/dev/bootstrap")
    for name, c in d["controls"].items():
        w = CTRL_WORD[name]
        rows.append((f"NumPCtrl{w}Hours", f"{c['n_hours']:,}", f"{SRC} controls/{name}/n_hours"))
        for gname, methods in c["bootstrap"].items():
            kind, _, key = gname.partition(":")
            if kind == "year":
                continue
            label = "Pooled" if gname == "pooled" else key
            for m, stat in methods.items():
                if m == "b0":
                    continue
                rows += _stat_macros(f"NumPCtrl{w}{label}{METHOD_WORD[m]}", stat, f"{SRC} controls/{name}/bootstrap/{gname}/{m}")
        for m in ("b1", "b2", "est"):
            for label, v in c["mean_abs_correction_bps"][m].items():
                rows.append((f"NumPCtrl{w}{'Pooled' if label == 'pooled' else label}Abs{METHOD_WORD[m]}",
                             f"{v:.1f}", f"{SRC} controls/{name}/mean_abs_correction_bps/{m}/{label}"))
    names = [r[0] for r in rows]
    assert len(names) == len(set(names)) and all(n.isalpha() for n in names), "macro names must be unique letters"
    body = "\n".join(f"\\newcommand{{\\{n}}}{{{v}}} % {s}" for n, v, s in rows)
    return f"{HEADER}\n{body}\n"


def _fmt(stat: dict[str, float]) -> str:
    return f"{_s(stat['point'])} [{_s(stat['lo'])}, {_s(stat['hi'])}]"


def table() -> str:
    d = load()
    a = d["bitfinex_coinbase"]
    rows = []

    def row(label: str, m: dict[str, Any]) -> str:
        return f"{label} & {_fmt(m['b1'])} & {_fmt(m['b2'])} & {_fmt(m['est'])} & {_fmt(m['diff'])} \\\\"

    for split, assets, pooled in (("dev", DEV_ASSETS, "Dev, pooled"), ("test", TEST_ASSETS, "Test, pooled")):
        boot = a[split]["bootstrap"]
        rows += [row(x, boot[f"asset:{x}"]) for x in assets] + [row(pooled, boot["pooled"])]
        rows.append("\\midrule")
    for name, c in d["controls"].items():
        rows.append(row(CTRL_LABEL[name], c["bootstrap"]["pooled"]))
    return (f"{HEADER}\n\\begin{{table*}}[!tp]\n\\footnotesize\n"
            "\\caption{Share of the mean-square cross-exchange gap removed (Bitfinex versus Coinbase), by withheld asset, "
            "with 95\\% block-bootstrap intervals (blocks are ISO weeks; 1,000 draws). $b_1$: same-hour bitcoin gap; $b_2$: "
            "same-hour median gap of the visible assets; Estimator: the fixed estimator; $\\Delta$: Estimator minus $b_2$. "
            "Controls pool the withheld assets ETH, LTC, BCH, XLM, LINK and XRP over 2019--2023 for the pair named. "
            "Scores are post-hoc and descriptive; the estimator was not changed.}\n"
            "\\label{tab:heldout-ci}\n\\setlength{\\tabcolsep}{3pt}\n\\begin{tabular}{@{}lllll@{}}\n\\toprule\n"
            "Asset & $b_1$ & $b_2$ & Estimator & $\\Delta$ vs $b_2$ \\\\\n\\midrule\n" + "\n".join(rows)
            + "\n\\bottomrule\n\\end{tabular}\n\\end{table*}\n")


def main() -> None:
    GEN.mkdir(parents=True, exist_ok=True)
    NUMBERS.write_text(numbers())
    TABLE.write_text(table())
    print(f"wrote {NUMBERS} and {TABLE}")


if __name__ == "__main__":
    main()
