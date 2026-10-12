import hashlib
import math
from pathlib import Path

import pandas as pd

from www_paper.figures import (
    ANCHOR_CSV, anchor_series, coverage_heatmap, coverage_matrix_grid, event_timeline,
)

ROOT = Path(__file__).parents[1]
REGISTRY = ROOT / "configs/event_registry.json"
COVERAGE = ROOT / "reports/events/coverage_matrix.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_figures_are_byte_deterministic(tmp_path):
    for build, src in ((event_timeline, REGISTRY), (coverage_heatmap, COVERAGE), (anchor_series, ANCHOR_CSV)):
        a, b = build(src, tmp_path / "a.pdf"), build(src, tmp_path / "b.pdf")
        assert digest(a) == digest(b)


def test_committed_figures_match_regeneration(tmp_path):
    pairs = {"event_timeline.pdf": (event_timeline, REGISTRY), "coverage_heatmap.pdf": (coverage_heatmap, COVERAGE),
             "anchor_series.pdf": (anchor_series, ANCHOR_CSV)}
    for name, (build, src) in pairs.items():
        assert digest(build(src, tmp_path / name)) == digest(ROOT / "paper/figures" / name), name


def test_coverage_grid_reflects_observed_versus_missing_windows():
    labels, grid = coverage_matrix_grid(COVERAGE)
    row = grid[labels.index("E2023-03-USDC-SVB | binance-us USDCUSD")]
    assert list(row) == [0.0, 3.0, 3.0, 3.0]  # control not covered; baseline/event/recovery observed
    assert all(not math.isnan(v) for v in grid.ravel())


def test_anchor_csv_holds_derived_15_minute_medians_only():
    frame = pd.read_csv(ANCHOR_CSV, parse_dates=["bin_start_utc"])
    assert list(frame.columns) == ["bin_start_utc", "usdc_peg_dislocation_bps", "usdc_triangle_wedge_bps"]
    assert len(frame) == 21 * 24 * 4  # 15-minute bins over 2023-03-01..21
    assert (frame["bin_start_utc"].diff().dropna() == pd.Timedelta("15min")).all()


def test_paper_includes_every_generated_figure():
    main = (ROOT / "paper/main.tex").read_text()
    for name in ("event_timeline", "coverage_heatmap", "anchor_series"):
        assert f"figures/{name}.pdf" in main
