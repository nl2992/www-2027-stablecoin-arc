"""Deterministic monitor operating-curve figure from reports/rescue/monitor_sweep.json.

False alarms per venue-year against episode recall, one line per method, for Bitfinex and pooled over venues.
Run ``uv run python -m www_paper.sweep_figure`` (conventions copied from figures.py: fixed PDF metadata, Agg backend).
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SWEEP = ROOT / "reports/rescue/monitor_sweep.json"
FIGURE = ROOT / "paper/figures/monitor_sweep.pdf"
PDF_METADATA = {"CreationDate": None, "ModDate": None, "Producer": None, "Creator": None}
LINES = (("detector_a0.25", "Monitor", "C3", "-", 1.3), ("b1", "Gap only", "C0", "-", 0.8),
         ("two_asset", "Two-asset gap", "C2", "--", 0.8), ("b2", "Robust z", "C1", "-", 0.8),
         ("b3", "USDT premium", "C4", ":", 0.8))
PANELS = (("bitfinex", "Bitfinex"), ("pooled", "Pooled"))


def _style() -> None:
    plt.rcParams.update({"font.size": 6, "axes.spines.top": False, "axes.spines.right": False,
                         "pdf.fonttype": 42, "svg.hashsalt": "www2027"})


def monitor_sweep(sweep: Path, out: Path) -> Path:
    _style()
    curves = json.loads(sweep.read_text())["curves"]
    fig, axes = plt.subplots(1, 2, figsize=(3.5, 1.7), sharey=True, gridspec_kw={"wspace": 0.12})
    for ax, (scope, title) in zip(axes, PANELS):
        for key, label, color, style, width in LINES:
            c = curves[key][scope]
            if c is None or (key == "b3" and scope == "pooled"):
                continue
            fr = c["frontier"]
            ax.plot([f["recall"] for f in fr], [f["fa_per_venue_year"] for f in fr], style, color=color, linewidth=width,
                    marker="o", markersize=2.2, label=label)
        ax.set_title(title, fontsize=6.5)
        ax.set_xlabel("Episode recall")
        ax.set_xlim(0.2, 1.02)
        ax.set_ylim(-0.1, 4.6)
    axes[0].set_ylabel("False alarms per venue-year")
    axes[0].legend(loc="upper left", fontsize=5, frameon=False, handlelength=1.6)
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, metadata=PDF_METADATA, bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> None:
    print(f"WROTE {monitor_sweep(SWEEP, FIGURE).relative_to(ROOT)}")


if __name__ == "__main__":
    main()
