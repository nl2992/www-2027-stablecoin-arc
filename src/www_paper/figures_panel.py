"""Forest plot of the per-currency IV lambda-hat from the pre-registered currency-wedge panel (reports/panel/results.json).

    uv run python -m www_paper.figures_panel

Same deterministic conventions as figures_v9: fixed style, default rcParams at save, PDF metadata stripped.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from www_paper.figures_v9 import BLACK, BLUE, SINGLE, VERMILION, _rc, _save  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "reports/panel/results.json"
OUT = ROOT / "paper/figures/panel_forest.pdf"
ORDER = ("ARS", "BRL", "KRW", "NGN", "RUB", "TRY", "UAH", "ZAR")


def panel_forest(out: Path = OUT, path: Path = RESULTS) -> Path:
    """Supports: per-currency stress-month IV estimates against the unit-wedge (1) and crypto-demand (0) predictions."""
    r = json.loads(path.read_text())
    rows = [(c, r["by_currency"][c]["stress"]["iv"], r["by_currency"][c]["stress_months"]) for c in ORDER]
    pooled = r["pooled_stress"]["iv"]
    with _rc():
        fig, ax = plt.subplots(figsize=(SINGLE, 2.9))
        labels, ys = [], []
        y = 0.0
        for cur, e, n in rows:
            ax.plot([e["lo"], e["hi"]], [y, y], color=BLUE, linewidth=1.5, solid_capstyle="butt")
            ax.plot([e["lam"]], [y], marker="o", color=BLUE, markersize=3.8, markeredgewidth=0)
            labels.append(f"{cur} ({n})")
            ys.append(y)
            y += 1.0
        y += 0.4
        ax.plot([pooled["lo"], pooled["hi"]], [y, y], color=VERMILION, linewidth=1.5, solid_capstyle="butt")
        ax.plot([pooled["lam"]], [y], marker="D", color=VERMILION, markersize=4.4, markeredgewidth=0)
        labels.append("Pooled")
        ys.append(y)
        ax.set_yticks(ys, labels)
        ax.set_ylim(y + 0.7, -0.7)
        ax.tick_params(axis="y", length=0)
        ax.axvline(1.0, color=BLACK, linewidth=0.8, linestyle="--")
        ax.axvline(0.0, color=BLACK, linewidth=0.8, linestyle=":")
        lo = min(min(e["lo"] for _, e, _ in rows), pooled["lo"])
        ax.set_xlim(min(lo - 0.03, -0.05), 1.08)
        ax.set_xlabel("$\\hat\\lambda$ (IV, 95% moving-block bootstrap interval)")
        ax.plot([], [], color=BLACK, linestyle="--", linewidth=0.8, label="$\\lambda=1$ (unit wedge)")
        ax.plot([], [], color=BLACK, linestyle=":", linewidth=0.8, label="$\\lambda=0$ (crypto demand)")
        ax.legend(loc="lower left", frameon=False, handlelength=1.4, handletextpad=0.3, borderaxespad=0.2)
    return _save(fig, out)


def main() -> int:
    print(f"wrote {panel_forest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
