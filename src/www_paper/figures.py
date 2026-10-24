"""Deterministic manuscript figures generated only from committed files.

- ``event_timeline``: registry events by date, status and role (configs/event_registry.json)
- ``coverage_heatmap``: best data status per event x analysis window (reports/events/coverage_matrix.json)
- ``anchor_series``: 15-minute medians of USDC peg dislocation and triangle wedge
  (reports/c3/anchor_15m_series.csv, itself derived from the audited IAQF panel)
- ``unit_rate``: daily Bitfinex-vs-Bitstamp bitcoin and ether gaps with label windows, and their scatter
  (reports/unit_td/probe.json, configs/fiat_rail_labels.json)

Run ``uv run python -m www_paper.figures`` (add ``--iaqf-panel PATH`` to rebuild the anchor CSV).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
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


CAPACITY_JSON = ROOT / "reports/c6/onchain_capacity.json"
CAPACITY_SERIES = {"E2022-05-UST-COLLAPSE": ("c1_50bps", "UST -> 3CRV (wormhole metapool)"),
                   "E2023-03-USDC-SVB": ("c0_50bps", "USDC -> DAI (3pool)"),
                   "N2023-06-USDT-3POOL": ("c0_50bps", "USDT -> DAI (3pool)")}


def capacity_paths(path: Path, out: Path) -> Path:
    """On-chain absorption capacity at 50 bps over each event's windows (6h samples + hourly event window)."""
    _style()
    data = json.loads(path.read_text())
    results = [r for r in data["results"] if r["event_id"] in CAPACITY_SERIES]
    fig, axes = plt.subplots(1, len(results), figsize=(7.0, 1.8), sharey=False)
    for ax, res in zip(np.atleast_1d(axes), results):
        key, label = CAPACITY_SERIES[res["event_id"]]
        for window, style in (("control", ":"), ("baseline", "-"), ("event_hourly", "-"), ("recovery", "-")):
            pts = res["samples"].get(window, [])
            if not pts:
                continue
            t = pd.to_datetime([p["timestamp_utc"] for p in pts])
            y = [p["capacity"][key]["absorption"] / 1e6 for p in pts]
            ax.plot(t, y, style, linewidth=0.8, color="C1" if window == "event_hourly" else "C0")
        ev = res["windows"]["event"]
        ax.axvspan(pd.Timestamp(ev["start"], tz="UTC"), pd.Timestamp(ev["end"], tz="UTC") + pd.Timedelta("1D"),
                   color="grey", alpha=0.15, linewidth=0)
        ax.set_title(label, fontsize=7)
        ax.tick_params(axis="x", labelrotation=45, labelsize=6)
    np.atleast_1d(axes)[0].set_ylabel("absorption at 50 bps (M)")
    fig.suptitle("On-chain only; par-valued counterparts; shaded: event window", fontsize=7)
    return _save(fig, out)


DECOMP_JSON = ROOT / "reports/rescue/decomposition.json"
PLATFORM_JSON = ROOT / "reports/rescue/platform_dollar.json"


def which_dollar(decomp: Path, platform: Path, out: Path) -> Path:
    """(a) token failure: USDC/SVB on Binance.US; (b) ledger failure: Binance.US USD, May-July 2023."""
    _style()
    d = json.loads(decomp.read_text())["windows"]["token_failure_svb"]["hourly"]
    h = pd.DataFrame.from_dict(d, orient="index", columns=["D", "L", "T", "D_ref"])
    h.index = pd.to_datetime(h.index)
    p = json.loads(platform.read_text())
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.0, 1.8), gridspec_kw={"width_ratios": [1, 1.3]})
    a.plot(h.index, h["D"], linewidth=1.2, label="observed $D$ (USDC/USD$_{venue}$)")
    a.plot(h.index, h["T"], linewidth=1.2, linestyle="--", label="token component $T$")
    a.plot(h.index, h["L"], linewidth=1.2, label="ledger component $L$ (BTC)")
    a.set_title("(a) Token failure: USDC, March 2023", fontsize=8)
    a.set_ylabel("bps (hourly median)")
    for name, key, style in (("USDT", "daily_median_pd_usdt", "-"), ("BTC", "daily_median_pd_btc", "--"),
                             ("USDC", "daily_median_pd_usdc", ":")):
        s = pd.Series(p[key]).loc["2023-05-01":"2023-07-31"]
        b.plot(pd.to_datetime(s.index), s.to_numpy(), style, linewidth=1.2, label=f"PD$_{{{name}}}$")
    shade = {"sec_complaint": "#fdd49e", "deposits_suspended": "#fc8d59", "withdrawal_halt_window": "#d7301f",
             "crypto_only_transition": "#9ecae1"}
    for ph in p["phases"]:
        if ph["phase"] in shade:
            b.axvspan(pd.Timestamp(ph["start"]), pd.Timestamp(min(ph["end"], "2023-07-31")), color=shade[ph["phase"]],
                      alpha=0.35, linewidth=0)
    b.set_title("(b) Ledger failure: Binance.US dollar, 2023 (shaded: rail events)", fontsize=8)
    for ax in (a, b):
        ax.axhline(0, color="black", linewidth=0.5)
        ax.tick_params(axis="x", labelrotation=30, labelsize=7)
        ax.legend(fontsize=7, frameon=False, loc="lower left")
    return _save(fig, out)


MONITOR_JSON = ROOT / "reports/rescue/monitor.json"


def monitor_timeline(path: Path, out: Path) -> Path:
    """Hourly ledger component L and token component T_USDC over every covered month; ledger flags marked."""
    _style()
    m = json.loads(path.read_text())
    h = pd.DataFrame.from_dict(m["hourly"], orient="index", columns=m["hourly_columns"])
    h.index = pd.to_datetime(h.index)
    segments = [("2022-10-01", "2022-12-01"), ("2023-02-01", "2023-08-01"), ("2025-02-01", "2025-04-01")]
    widths = [(pd.Timestamp(b) - pd.Timestamp(a)).days for a, b in segments]
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 1.8), sharey=True, gridspec_kw={"width_ratios": widths})
    for ax, (a, b) in zip(axes, segments):
        g = h[(h.index >= pd.Timestamp(a, tz="UTC")) & (h.index < pd.Timestamp(b, tz="UTC"))]
        ax.plot(g.index, g["L"].astype(float), linewidth=0.6, label="ledger component $L$")
        ax.plot(g.index, g["T_USDC"].astype(float), linewidth=0.6, linestyle="--", label="token component $T_{USDC}$")
        fl = g[g["ledger_flag"].astype(bool)]
        ax.scatter(fl.index, np.full(len(fl), 450.0), s=2, color="C3", label="ledger flag")
        ax.axhline(0, color="black", linewidth=0.4)
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
        ax.tick_params(axis="x", labelrotation=30, labelsize=6)
    axes[0].set_ylabel("bps (hourly median)")
    axes[0].set_ylim(-1500, 600)
    axes[1].legend(fontsize=6, frameon=False, loc="lower left")
    fig.suptitle("Hourly monitor on Binance.US (covered months only; y-axis clipped)", fontsize=7)
    return _save(fig, out)


PROBE_JSON = ROOT / "reports/unit_td/probe.json"
FIAT_LABELS = ROOT / "configs/fiat_rail_labels.json"


def bitfinex_label_windows(labels: Path) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Union of the pre-specified truth windows of Bitfinex positive episodes (same rule as the detector evaluation)."""
    from www_rescue.detector_eval import load_labels
    spans = sorted((pd.Timestamp(e.window[0]), pd.Timestamp(e.window[1])) for e in load_labels(labels, "bitfinex") if e.positive)
    merged: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def unit_rate(probe: Path, labels: Path, out: Path) -> Path:
    """Left: daily Bitfinex-vs-Bitstamp bitcoin and ether gaps (symlog), label windows shaded. Right: bitcoin vs ether gap."""
    _style()
    plt.rcParams.update({"font.size": 6})
    daily = json.loads(probe.read_text())["daily_gaps_bps"]["bitfinex-bitstamp"]
    frame = pd.DataFrame({k: pd.Series(v) for k, v in daily.items()}).sort_index()
    frame.index = pd.to_datetime(frame.index)
    fig, (a, b) = plt.subplots(1, 2, figsize=(3.5, 1.9), gridspec_kw={"width_ratios": [1.5, 1], "wspace": 0.55})
    for lo, hi in bitfinex_label_windows(labels):
        a.axvspan(lo, hi, color="#bdbdbd", alpha=0.35, linewidth=0)
    a.plot(frame.index, frame["BTC"], linewidth=0.5, color="C0", label="BTC")
    a.plot(frame.index, frame["ETH"], linewidth=0.5, color="C1", alpha=0.8, label="ETH")
    a.axhline(0, color="black", linewidth=0.4)
    a.set_yscale("symlog", linthresh=10)
    a.set_yticks([-1000, -100, -10, 0, 10, 100, 1000], ["$-$1000", "$-$100", "$-$10", "0", "10", "100", "1000"])
    a.set_xlim(pd.Timestamp("2017-01-01"), pd.Timestamp("2024-01-01"))
    a.xaxis.set_major_locator(mdates.YearLocator(2))
    a.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    a.set_ylabel("daily median gap (bps)")
    a.set_title("Bitfinex vs Bitstamp", fontsize=6.5)
    a.legend(fontsize=5.5, frameon=True, framealpha=0.85, edgecolor="none", loc="upper right", handlelength=1.2)
    both = frame.dropna()
    years = both.index.year.to_numpy()
    points = b.scatter(both["BTC"], both["ETH"], c=years, cmap="viridis", s=2, linewidths=0, vmin=2016.5, vmax=2023.5)
    lim = 300
    b.plot([-lim, lim], [-lim, lim], color="black", linewidth=0.5, linestyle="--")
    b.set_xscale("symlog", linthresh=10)
    b.set_yscale("symlog", linthresh=10)
    ticks, names = [-100, -10, 0, 10, 100], ["$-$100", "$-$10", "0", "10", "100"]
    b.set_xticks([-100, 0, 100], ["$-$100", "0", "100"])
    b.set_yticks(ticks, names)
    b.set_xlim(-lim, lim)
    b.set_ylim(-lim, lim)
    b.set_xlabel("BTC gap (bps)")
    b.set_ylabel("ETH gap (bps)")
    b.set_title("Daily, by year", fontsize=6.5)
    bar = fig.colorbar(points, ax=b, ticks=[2017, 2019, 2021, 2023], fraction=0.07, pad=0.04)
    bar.ax.tick_params(labelsize=5.5)
    return _save(fig, out)


def build_all(*, iaqf_panel: Path | None = None) -> list[Path]:
    if iaqf_panel is not None:
        build_anchor_csv(iaqf_panel)
    return [
        event_timeline(ROOT / "configs/event_registry.json", FIG_DIR / "event_timeline.pdf"),
        coverage_heatmap(ROOT / "reports/events/coverage_matrix.json", FIG_DIR / "coverage_heatmap.pdf"),
        anchor_series(ANCHOR_CSV, FIG_DIR / "anchor_series.pdf"),
        *([capacity_paths(CAPACITY_JSON, FIG_DIR / "onchain_capacity_paths.pdf")] if CAPACITY_JSON.is_file() else []),
        *([which_dollar(DECOMP_JSON, PLATFORM_JSON, FIG_DIR / "which_dollar.pdf")] if DECOMP_JSON.is_file() else []),
        *([monitor_timeline(MONITOR_JSON, FIG_DIR / "monitor_timeline.pdf")] if MONITOR_JSON.is_file() else []),
        *([unit_rate(PROBE_JSON, FIAT_LABELS, FIG_DIR / "unit_rate.pdf")] if PROBE_JSON.is_file() else []),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iaqf-panel", type=Path, help="rebuild reports/c3/anchor_15m_series.csv from the panel")
    args = parser.parse_args()
    for path in build_all(iaqf_panel=args.iaqf_panel):
        print(f"WROTE {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
