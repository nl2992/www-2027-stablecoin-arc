"""Deterministic manuscript figures generated only from committed files.

- ``event_timeline``: registry events by date, status and role (configs/event_registry.json)
- ``coverage_heatmap``: best data status per event x analysis window (reports/events/coverage_matrix.json)
- ``anchor_series``: 15-minute medians of USDC peg dislocation and triangle wedge
  (reports/c3/anchor_15m_series.csv, itself derived from the audited IAQF panel)

Run ``uv run python -m www_paper.figures`` (add ``--iaqf-panel PATH`` to rebuild the anchor CSV).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from www_c3.fragmentation import build_wedges  # noqa: E402
from www_c3.robustness import horizon_medians  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = ROOT / "paper/figures"
ANCHOR_CSV = ROOT / "reports/c3/anchor_15m_series.csv"
PDF_METADATA = {"CreationDate": None, "ModDate": None, "Producer": None, "Creator": None}
STATUS_RANK = {"NOT_LISTED": 0, "ACCESS_BLOCKED": 0, "UNVERIFIED_SOURCE": 1, "LISTED": 2, "OBSERVED_LOCAL": 3}
STATUS_COLOR = {"ACCEPTED": "#1b7837", "SOURCE_DOCUMENTED": "#5aae61", "CANDIDATE": "#a6dba0",
                "UNRESOLVED": "#bababa", "REJECTED": "#d6604d", "DATA_VERIFIED": "#00441b"}
WINDOWS = ["control", "baseline", "event", "recovery"]


def _style() -> None:
    plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False,
                         "pdf.fonttype": 42, "svg.hashsalt": "www2027"})


def _save(fig: plt.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, metadata=PDF_METADATA, bbox_inches="tight")
    plt.close(fig)
    return path


def event_timeline(registry: Path, out: Path) -> Path:
    _style()
    events = json.loads(registry.read_text())["events"]
    events = sorted(events, key=lambda e: e["reported_window_utc"]["start"])
    fig, ax = plt.subplots(figsize=(7.0, 0.22 * len(events) + 0.8))
    for row, e in enumerate(events):
        start = pd.Timestamp(e["reported_window_utc"]["start"])
        end = pd.Timestamp(e["reported_window_utc"]["end"]) + pd.Timedelta("1D")
        color = STATUS_COLOR[e["status"]]
        marker = "D" if e["sample_role"] == "PLACEBO" else ("o" if e["role"] == "PRIMARY" else ">")
        ax.plot([start, end], [row, row], color=color, linewidth=4, solid_capstyle="butt")
        ax.plot([start], [row], marker=marker, color=color, markersize=4)
    ax.axvline(pd.Timestamp("2024-01-01"), color="black", linestyle=":", linewidth=0.8)
    ax.text(pd.Timestamp("2024-01-15"), len(events) - 0.5, "out-of-sample", fontsize=7)
    ax.set_yticks(range(len(events)), [e["id"] for e in events], fontsize=6)
    ax.invert_yaxis()
    handles = [plt.Line2D([], [], color=c, linewidth=4, label=s.replace("_", " ").lower())
               for s, c in STATUS_COLOR.items() if any(e["status"] == s for e in events)]
    ax.legend(handles=handles, loc="lower left", fontsize=6, frameon=False)
    ax.set_xlabel("Reported event window (UTC); o primary, > linked leg, D placebo")
    return _save(fig, out)


def coverage_matrix_grid(coverage: Path) -> tuple[list[str], np.ndarray]:
    """Rows: event|venue|symbol; columns: WINDOWS; value: mean status rank over the window's days."""
    rows = json.loads(coverage.read_text())["rows"]
    frame = pd.DataFrame(rows)
    frame["rank"] = frame["status"].map(STATUS_RANK)
    frame["key"] = frame["event_id"] + " | " + frame["venue"] + " " + frame["symbol"]
    grid = frame.pivot_table(index="key", columns="window", values="rank", aggfunc="mean").reindex(columns=WINDOWS)
    return list(grid.index), grid.to_numpy(dtype=float)


def coverage_heatmap(coverage: Path, out: Path) -> Path:
    _style()
    labels, grid = coverage_matrix_grid(coverage)
    fig, ax = plt.subplots(figsize=(4.8, 0.2 * len(labels) + 0.9))
    image = ax.imshow(grid, cmap="Greens", vmin=0, vmax=3, aspect="auto")
    ax.set_xticks(range(len(WINDOWS)), WINDOWS)
    ax.set_yticks(range(len(labels)), labels, fontsize=5.5)
    bar = fig.colorbar(image, ax=ax, ticks=[0, 1, 2, 3], shrink=0.6)
    bar.ax.set_yticklabels(["not listed", "unverified", "listed", "observed"], fontsize=6)
    return _save(fig, out)


def build_anchor_csv(panel_path: Path, out: Path = ANCHOR_CSV) -> Path:
    """Aggregate the audited panel to 15-minute medians (derived statistics only, no raw rows)."""
    wedges = build_wedges(pd.read_parquet(panel_path))
    panel = pd.read_parquet(panel_path)
    traded = pd.Series(pd.to_numeric(panel["bnus_usdcusd_volume"]).to_numpy() > 0, index=wedges.index)
    peg = horizon_medians(wedges["usdc_depeg_bps"], traded, 15, min_obs=3)
    wedge = horizon_medians(wedges["usdc_wedge_bps"], wedges["usdc_fresh"], 15, min_obs=3)
    frame = pd.DataFrame({"usdc_peg_dislocation_bps": peg, "usdc_triangle_wedge_bps": wedge})
    frame.index.name = "bin_start_utc"
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.round(4).to_csv(out, date_format="%Y-%m-%dT%H:%M:%SZ")
    return out


def anchor_series(csv_path: Path, out: Path) -> Path:
    _style()
    frame = pd.read_csv(csv_path, parse_dates=["bin_start_utc"], index_col="bin_start_utc")
    fig, ax = plt.subplots(figsize=(7.0, 2.2))
    ax.plot(frame.index, frame["usdc_peg_dislocation_bps"], linewidth=0.8, label="peg dislocation D (USDC/USD)")
    ax.plot(frame.index, frame["usdc_triangle_wedge_bps"], linewidth=0.8, label="triangle wedge W (BTC legs)")
    ax.axhline(0, color="black", linewidth=0.5)
    for day in ("2023-03-10", "2023-03-13"):
        ax.axvline(pd.Timestamp(day, tz="UTC"), color="grey", linestyle=":", linewidth=0.8)
    ax.set_ylabel("bps (15-min median)")
    ax.legend(fontsize=7, frameon=False, loc="lower right")
    return _save(fig, out)


def build_all(*, iaqf_panel: Path | None = None) -> list[Path]:
    if iaqf_panel is not None:
        build_anchor_csv(iaqf_panel)
    return [
        event_timeline(ROOT / "configs/event_registry.json", FIG_DIR / "event_timeline.pdf"),
        coverage_heatmap(ROOT / "reports/events/coverage_matrix.json", FIG_DIR / "coverage_heatmap.pdf"),
        anchor_series(ANCHOR_CSV, FIG_DIR / "anchor_series.pdf"),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iaqf-panel", type=Path, help="rebuild reports/c3/anchor_15m_series.csv from the panel")
    args = parser.parse_args()
    for path in build_all(iaqf_panel=args.iaqf_panel):
        print(f"WROTE {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
