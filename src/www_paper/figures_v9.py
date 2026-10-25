"""Draft-v9 figures and captions, drawn only from committed reports, configs and the committed scripts' functions.

- ``anchor_scatter``: netting Tether's own price (Kraken USDT) moves the daily slope of the Bitfinex USDT residual on the BTC gap from 0.71 to 0.97
- ``anchor_timeseries``: the Bitfinex USDT residual tracks the BTC gap once Kraken's USDT deviation is netted, through the NYAG and rail dates
- ``robustness_forest``: the netted slope stays near one across windows, instrument sets and references while the unnetted question is already answered
- ``simulation_power``: the test rejects the wrong null in the pure scenarios and the netting matters under an anchor depeg
- ``q1_errors``: the frozen fuser's error on stressed hours is a fraction of every baseline's and close to the oracle's
- ``kimchi_gaps``: the KRW premia of three coins move together in both premium episodes

Two figures need the raw exchange files that are not committed (``data/raw``); they are recomputed through the committed
functions ``www_auto.anchor_external`` and ``www_kimchi.analysis``. Captions are written to ``paper/generated/fig_captions_v9.tex``
with every number read from the reports.

    uv run python -m www_paper.figures_v9
"""

from __future__ import annotations

import contextlib
import json
from functools import lru_cache
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from www_paper.figures import PDF_METADATA  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = ROOT / "paper/figures"
CAPTIONS = ROOT / "paper/generated/fig_captions_v9.tex"
ANCHOR_EXT = ROOT / "reports/unit_td/anchor_external.json"
GMM_APPLIED = ROOT / "reports/theory/gmm_applied.json"
ROBUSTNESS = ROOT / "reports/theory/robustness.json"
SIMULATION = ROOT / "reports/theory/simulation.json"
Q1_RESULTS = ROOT / "reports/q1/results.json"
KIMCHI = ROOT / "reports/kimchi/results.json"
FIAT_LABELS = ROOT / "configs/fiat_rail_labels.json"
RAW = ROOT / "data/raw"

STRESS_SLICE = "stress_2018-11-27_2019-05-31"
NYAG_ID = "BFX-2019-01"
RAIL_TYPES = ("deposit_pause", "banking_partner_loss")
SINGLE, FULL = 3.3, 7.0

# Okabe-Ito: colour-blind safe; every series also differs in marker or line style.
BLUE, VERMILION, GREEN, ORANGE, SKY, PINK, BLACK, GREY = (
    "#0072B2", "#D55E00", "#009E73", "#E69F00", "#56B4E9", "#CC79A7", "#000000", "#7F7F7F")
LIGHT = "#BDBDBD"


def _j(path: Path):
    return json.loads(path.read_text())


def _style() -> dict:
    return {"font.size": 7, "axes.labelsize": 7, "axes.titlesize": 7, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
            "legend.fontsize": 6.5, "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6,
            "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
            "grid.color": "#E6E6E6", "grid.linewidth": 0.4, "pdf.fonttype": 42, "svg.hashsalt": "www2027",
            "axes.unicode_minus": False}


@contextlib.contextmanager
def _rc():
    """Matplotlib defaults plus this module's style, so state left in rcParams by other figure code cannot change the output."""
    with matplotlib.rc_context():
        plt.rcdefaults()
        plt.rcParams.update(_style())
        yield


def _save(fig: plt.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with matplotlib.rc_context():
        plt.rcdefaults()  # save under default settings whatever other figure code left in rcParams
        fig.savefig(path, metadata=PDF_METADATA, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return path


def _panel_tag(ax, tag: str) -> None:
    ax.text(0.0, 1.03, tag, transform=ax.transAxes, fontsize=7.5, fontweight="bold", va="bottom", ha="left")


# ---- derived daily series (recomputed through the committed functions) -------------------------------------------------

def raw_data_available() -> bool:
    return all((RAW / p).exists() for p in ("kraken_ohlcvt/USDTUSD_1.csv", "bitfinex", "bitstamp", "upbit"))


@lru_cache(maxsize=1)
def anchor_daily() -> pd.DataFrame:
    """Daily medians of L, D, X over hours where all three exist in the stress window, exactly as ``anchor_external.slice_stats``."""
    from www_auto import anchor, anchor_external as ae
    s = ae.load_series()["series"]
    L = 1e4 * (s["bitfinex|BTC"] - s["bitstamp|BTC"])
    D = 1e4 * s["bitfinex|USDT"]
    X = 1e4 * s["kraken|USDT"]
    h = pd.concat([anchor._cut(v, *ae.STRESS) for v in (L.rename("L"), D.rename("D"), X.rename("X"))], axis=1).dropna()
    d = h.groupby(h.index.floor("D")).median()
    d["DmX"] = d["D"] - d["X"]
    return d


@lru_cache(maxsize=1)
def kimchi_daily() -> pd.DataFrame:
    """Daily KRW premia (bps) of the core coins, as ``www_kimchi.analysis.run`` builds them (days with at least 12 hours)."""
    from www_kimchi import analysis as ka
    data = ka.load_all()
    h = ka.gaps_hourly(data["krw"], data["usd"], ka.fx_hourly(data["fx"]))
    return ka.to_daily(h)[list(ka.CORE)]


def _ols_line(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    slope, intercept = np.polyfit(x, y, 1)
    return float(slope), float(intercept)


def anchor_slopes() -> dict:
    """The daily slopes of D and of D - X on L that the paper reports, read from the committed report."""
    daily = _j(ANCHOR_EXT)["slices"][STRESS_SLICE]["adjusted_LDX"]["daily"]
    return {"n": daily["n"], "raw": daily["slope_D_on_L"], "netted": daily["slope_D_minus_X_on_L"]}


# ---- 1. anchor scatter ----------------------------------------------------------------------------------------------------

def anchor_scatter(out: Path, daily: pd.DataFrame | None = None) -> Path:
    """Supports: netting Tether's own price on Kraken moves the Bitfinex USDT slope on the BTC gap from 0.71 to 0.97."""
    d = anchor_daily() if daily is None else daily
    rep = anchor_slopes()
    with _rc():
        fig, axes = plt.subplots(1, 2, figsize=(SINGLE, 1.95), sharex=True, sharey=True, gridspec_kw={"wspace": 0.08})
        lo, hi = -450, 450
        grid = np.array([lo, hi])
        for ax, col, tag, key, color, title in (
                (axes[0], "D", "(a)", "raw", VERMILION, "$D$ on $L$"),
                (axes[1], "DmX", "(b)", "netted", BLUE, "$D-X$ on $L$")):
            ax.scatter(d["L"], d[col], s=5, color=color, alpha=0.7, linewidths=0, marker="o" if key == "raw" else "s", rasterized=False)
            ax.plot(grid, grid, color=BLACK, linewidth=0.7, linestyle="--", label="45° line")
            slope, icpt = _ols_line(d["L"].to_numpy(), d[col].to_numpy())
            ax.plot(grid, icpt + slope * grid, color=color, linewidth=1.2, label="fitted line")
            est = rep[key]
            ax.text(0.04, 0.96, f"slope {est['est']:.2f}\n[{est['ci95_week'][0]:.2f}, {est['ci95_week'][1]:.2f}]", transform=ax.transAxes,
                    va="top", ha="left", fontsize=7, color=color, fontweight="bold")
            ax.axhline(0, color=LIGHT, linewidth=0.4, zorder=0)
            ax.axvline(0, color=LIGHT, linewidth=0.4, zorder=0)
            ax.set_xlim(lo, hi)
            ax.set_ylim(lo, hi)
            ax.set_aspect("equal", adjustable="box")
            ax.set_xlabel("BTC gap $L$ (bps)")
            ax.set_title(title, fontsize=7, pad=2)
            _panel_tag(ax, tag)
        axes[0].set_ylabel("Bitfinex USDT, bps")
        axes[1].tick_params(labelleft=False)
        axes[1].legend(loc="lower right", frameon=False, handlelength=1.6, borderaxespad=0.2)
        for ax in axes:
            ax.set_xticks([-400, -200, 0, 200, 400])
            ax.set_yticks([-400, -200, 0, 200, 400])
    return _save(fig, out)


# ---- 2. anchor time series --------------------------------------------------------------------------------------------------

def rail_markers(labels: Path = FIAT_LABELS) -> dict:
    """Dates inside the stress window from the label file: the NYAG complaint and Bitfinex deposit pause / fiat-partner losses."""
    lo, hi = pd.Timestamp("2018-11-27"), pd.Timestamp("2019-05-31")
    eps = [e for e in _j(labels)["episodes"] if e["venue"] == "Bitfinex"]
    nyag = next(e for e in eps if e["id"] == NYAG_ID)
    rails = [e for e in eps if e["type"] in RAIL_TYPES and e["impairment_start"] and lo <= pd.Timestamp(e["impairment_start"]) <= hi]
    return {"nyag": pd.Timestamp(nyag["impairment_start"]),
            "rails": [(pd.Timestamp(e["impairment_start"]), e["id"], e["type"]) for e in rails]}


def anchor_timeseries(out: Path, daily: pd.DataFrame | None = None) -> Path:
    """Supports: the Bitfinex USDT residual D - X follows the BTC gap L through the NYAG and fiat-rail dates, while D and X alone do not."""
    d = anchor_daily() if daily is None else daily
    marks = rail_markers()
    with _rc():
        fig, (a, b) = plt.subplots(2, 1, figsize=(FULL, 3.1), sharex=True, gridspec_kw={"height_ratios": [2.2, 1], "hspace": 0.2})
        a.plot(d.index, d["L"], color=GREY, linewidth=2.2, alpha=0.55, label="$L$: BTC gap, Bitfinex vs Bitstamp")
        a.plot(d.index, d["D"], color=VERMILION, linewidth=0.9, linestyle="-", label="$D$: Bitfinex USDT/USD")
        a.plot(d.index, d["DmX"], color=BLUE, linewidth=0.9, linestyle="--", label="$D-X$: $D$ net of Kraken USDT")
        b.plot(d.index, d["X"], color=GREEN, linewidth=0.9, linestyle="-.", label="$X$: Kraken USDT/USD")
        for ax in (a, b):
            ax.axhline(0, color=BLACK, linewidth=0.4)
            ax.axvline(marks["nyag"], color=BLACK, linewidth=0.9, linestyle="-")
            for t, _, _ in marks["rails"]:
                ax.axvline(t, color=BLACK, linewidth=0.9, linestyle=":")
        top = a.get_ylim()[1]
        a.text(marks["nyag"] - pd.Timedelta("2D"), top, "NYAG complaint\n2019-04-25", ha="right", va="top", fontsize=6.5)
        for t, ident, kind in marks["rails"]:
            a.text(t + pd.Timedelta("2D"), top, f"{kind.replace('_', ' ')}\n{t:%Y-%m-%d}", ha="left", va="top", fontsize=6.5)
        a.set_ylabel("daily median (bps)")
        b.set_ylabel("bps")
        a.legend(loc="lower center", bbox_to_anchor=(0.5, 1.04), ncol=3, frameon=False, handlelength=2.0, columnspacing=1.2)
        b.legend(loc="upper center", frameon=False, handlelength=2.0)
        b.xaxis.set_major_locator(mdates.MonthLocator())
        b.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        a.text(-0.045, 1.0, "(a)", transform=a.transAxes, fontsize=7.5, fontweight="bold", va="top")
        b.text(-0.045, 1.0, "(b)", transform=b.transAxes, fontsize=7.5, fontweight="bold", va="top")
    return _save(fig, out)


# ---- 3. robustness forest -----------------------------------------------------------------------------------------------------

FOREST_FACTORS = (("window", "Window"), ("instruments", "Instrument set"), ("reference", "Reference"))


def forest_rows(path: Path = ROBUSTNESS) -> list[dict]:
    """GMM lambda with the weekly-block bootstrap interval, one factor varied at a time around the headline cell (summary rows)."""
    r = _j(path)
    head = r["headline"]["cell"]
    base = {k: head[k] for k in ("window", "instruments", "reference", "x", "block")}
    cells = {tuple(c[k] for k in ("window", "instruments", "reference", "x", "block")): c for c in r["cells"]}
    levels = {"window": list(r["grid"]["windows"]), "instruments": list(r["grid"]["instrument_sets"]), "reference": list(r["grid"]["references"])}
    rows = []
    for factor, _ in FOREST_FACTORS:
        for level in levels[factor]:
            cell = cells[tuple({**base, factor: level}[k] for k in ("window", "instruments", "reference", "x", "block"))]
            rows.append({"factor": factor, "level": level, "lam": cell["gmm"]["lam"], "lo": cell["gmm"]["boot_ci95"][0],
                         "hi": cell["gmm"]["boot_ci95"][1], "headline": level == base[factor], "n": cell["n"]})
    return rows


LEVEL_LABELS = {"stress": "stress window", "stress_to_mar": "to Mar 2019", "jan_to_may_2019": "Jan-May 2019", "year_2019": "year 2019",
                "stress_pm30d": "stress $\\pm$30 d", "eth": "ETH", "eth_ltc": "ETH, LTC", "eth_ltc_bch_etc": "ETH, LTC, BCH, ETC",
                "lags12": "2 lags of $L$", "bitstamp": "Bitstamp", "coinbase": "Coinbase", "mid": "mid of both"}


def robustness_forest(out: Path, path: Path = ROBUSTNESS) -> Path:
    """Supports: the netted unit-offset estimate stays close to one across windows, instrument sets and references, and is far from zero."""
    rows = forest_rows(path)
    with _rc():
        plt.rcParams.update({"ytick.labelsize": 8, "xtick.labelsize": 8, "legend.fontsize": 7.5})
        fig, (a0, a1) = plt.subplots(1, 2, figsize=(SINGLE, 3.5), sharey=True, gridspec_kw={"width_ratios": [1, 8], "wspace": 0.05})
        y, ticks, names, bold = 0.0, [], [], []
        for factor, title in FOREST_FACTORS:
            ticks.append(y)
            names.append(title)
            bold.append(True)
            y += 1.0
            for row in [r for r in rows if r["factor"] == factor]:
                color, marker = (VERMILION, "D") if row["headline"] else (BLUE, "o")
                a1.plot([row["lo"], row["hi"]], [y, y], color=color, linewidth=1.5, solid_capstyle="butt")
                a1.plot([row["lam"]], [y], marker=marker, color=color, markersize=4.4 if row["headline"] else 3.8, markeredgewidth=0)
                ticks.append(y)
                names.append("  " + LEVEL_LABELS[row["level"]])
                bold.append(False)
                y += 1.0
            y += 0.4
        a0.set_ylim(y - 0.6, -0.6)
        a0.set_yticks(ticks, names)
        for lab, bd in zip(a0.get_yticklabels(), bold):
            lab.set_fontweight("bold" if bd else "normal")
        a0.tick_params(axis="y", length=0)
        a1.tick_params(axis="y", length=0, labelleft=False)
        lo, hi = min(r["lo"] for r in rows), max(r["hi"] for r in rows)
        a1.set_xlim(lo - 0.005, hi + 0.005)
        a1.set_xticks([0.95, 1.0, 1.05] if hi > 1.04 else [0.95, 1.0])
        a1.axvline(1.0, color=BLACK, linewidth=0.8, linestyle="--")
        a0.axvline(0.0, color=BLACK, linewidth=0.8, linestyle=":")
        a0.set_xlim(-0.04, 0.04)
        a0.set_xticks([0])
        a1.spines["left"].set_visible(False)
        fig.supxlabel("$\\hat\\lambda$ (GMM, 95% weekly-block bootstrap interval)", fontsize=8, y=-0.03)
        a1.plot([], [], color=BLACK, linestyle="--", linewidth=0.8, label="$\\lambda=1$")
        a1.plot([], [], color=BLACK, linestyle=":", linewidth=0.8, label="$\\lambda=0$ (left scale)")
        a1.plot([], [], marker="D", color=VERMILION, linestyle="none", markersize=4.4, label="headline cell")
        a1.legend(loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=3, frameon=False, handlelength=1.4, handletextpad=0.3,
                  columnspacing=0.8, borderaxespad=0.2, fontsize=7)
    return _save(fig, out)


# ---- 4. simulation power ------------------------------------------------------------------------------------------------------------

SIM_SCENARIOS = tuple(f"S{i}" for i in range(1, 8))


def simulation_power(out: Path, path: Path = SIMULATION) -> Path:
    """Supports: the GMM test rejects the wrong null (lambda=0 or 1) in the pure scenarios, holds its size near 5%, and netting matters under a depeg."""
    sim = _j(path)["scenarios"]
    x = np.arange(len(SIM_SCENARIOS))
    w = 0.34
    with _rc():
        fig, ax = plt.subplots(figsize=(SINGLE, 2.0))
        r1 = [sim[s]["estimators"]["gmm"]["rej_lam1"] for s in SIM_SCENARIOS]
        r0 = [sim[s]["estimators"]["gmm"]["rej_lam0"] for s in SIM_SCENARIOS]
        o1 = [sim[s]["estimators"]["ols"]["rej_lam1"] for s in SIM_SCENARIOS]
        ax.bar(x - w / 2, r1, w, color=BLUE, label="GMM: reject $\\lambda=1$")
        ax.bar(x + w / 2, r0, w, color=ORANGE, hatch="////", edgecolor="white", linewidth=0, label="GMM: reject $\\lambda=0$")
        ax.plot(x - w / 2, o1, linestyle="none", marker="D", markersize=3, markerfacecolor="white", markeredgecolor=BLACK, markeredgewidth=0.7,
                label="OLS: reject $\\lambda=1$")
        ax.axhline(0.05, color=VERMILION, linewidth=0.9, linestyle="--", label="5% level")
        ax.set_xticks(x, [f"{s}\n$\\lambda$={sim[s]['truth']:g}" for s in SIM_SCENARIOS])
        ax.set_ylim(0, 1.0)
        ax.set_ylabel("rejection rate (1,000 draws)")
        ax.set_xlabel("scenario and true $\\lambda$")
        ax.yaxis.grid(True)
        ax.set_axisbelow(True)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.34), ncol=2, frameon=False, handlelength=1.4, columnspacing=1.0)
    return _save(fig, out)


# ---- 5. Q1 errors --------------------------------------------------------------------------------------------------------------------------

Q1_METHODS = (("fuser", "fuser", BLUE, "o"), ("B0", "B0", GREY, "s"), ("B2", "B2", ORANGE, "^"), ("B3", "B3", GREEN, "v"),
              ("oracle", "oracle", VERMILION, "D"))
Q1_VS = (("fuser_vs_B0", "vs B0"), ("fuser_vs_B2", "vs B2"), ("fuser_vs_B3", "vs B3"), ("fuser_vs_oracle", "vs oracle"))


def q1_errors(out: Path, path: Path = Q1_RESULTS) -> Path:
    """Supports: on stressed hours the frozen fuser's MAE is a fraction of B0, B2 and B3 and near the oracle, and the pooled log-error gap excludes zero."""
    q = _j(path)
    events = list(q["kept_events"])
    groups = [(e, {m: q["per_event"][e]["s_hi"][m]["mae"] for m, *_ in Q1_METHODS}) for e in events]
    groups.append(("pooled", {m: q["pooled_s_hi"][m]["mae"] for m, *_ in Q1_METHODS}))
    with _rc():
        fig, (a, b) = plt.subplots(2, 1, figsize=(SINGLE, 3.5), gridspec_kw={"height_ratios": [1.7, 1], "hspace": 0.62})
        k = len(Q1_METHODS)
        step = 0.15
        for gi, (name, maes) in enumerate(groups):
            for mi, (m, label, color, marker) in enumerate(Q1_METHODS):
                a.plot([gi + (mi - (k - 1) / 2) * step], [maes[m]], marker=marker, color=color, markersize=4.2 if m == "fuser" else 3.4,
                       markeredgewidth=0, linestyle="none", label=label if gi == 0 else None)
        a.set_yscale("log")
        a.set_ylim(3, 250)
        a.set_yticks([5, 10, 30, 100], ["5", "10", "30", "100"])
        a.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
        a.set_xticks(range(len(groups)), [f"{n}\n({q['s_hi_hours'][n]} h)" if n in q["s_hi_hours"] else f"pooled\n({q['pooled_s_hi']['fuser']['n']} h)"
                                         for n, _ in groups])
        a.set_ylabel("MAE on $S_{hi}$ (bps, log scale)")
        a.yaxis.grid(True)
        a.set_axisbelow(True)
        a.legend(loc="upper center", bbox_to_anchor=(0.5, 1.30), ncol=5, frameon=False, handletextpad=0.1, columnspacing=0.8)
        _panel_tag(a, "(a)")
        for i, (key, label) in enumerate(Q1_VS):
            e = q["primary"][key]
            color = VERMILION if key == "fuser_vs_oracle" else BLUE
            b.plot(e["ci95"], [i, i], color=color, linewidth=1.5, solid_capstyle="butt")
            b.plot([e["mean"]], [i], marker="o", color=color, markersize=3.6, markeredgewidth=0)
        b.axvline(0, color=BLACK, linewidth=0.8, linestyle="--")
        b.set_yticks(range(len(Q1_VS)), [lab for _, lab in Q1_VS])
        b.set_ylim(len(Q1_VS) - 0.5, -0.6)
        b.set_xlabel("pooled mean of log($|e|$+1 bp), fuser minus comparator (95% day-block CI)")
        b.xaxis.label.set_size(6.5)
        _panel_tag(b, "(b)")
    return _save(fig, out)


# ---- 6. kimchi gaps ------------------------------------------------------------------------------------------------------------------------

KIMCHI_WINDOWS = (("E1_2017-12_2018-01", "Dec 2017 to Jan 2018"), ("E2_2021-03_2021-05", "Mar to May 2021"))
KIMCHI_STYLES = (("BTC", BLUE, "-"), ("ETH", VERMILION, "--"), ("XRP", GREEN, "-."))


def kimchi_gaps(out: Path, daily: pd.DataFrame | None = None, path: Path = KIMCHI) -> Path:
    """Supports: the KRW premia of BTC, ETH and XRP move together in both high-premium episodes (common component)."""
    d = kimchi_daily() if daily is None else daily
    res = _j(path)["windows"]
    with _rc():
        fig, axes = plt.subplots(2, 1, figsize=(SINGLE, 3.3), gridspec_kw={"hspace": 0.5})
        for ax, (key, title), tag in zip(axes, KIMCHI_WINDOWS, ("(a)", "(b)")):
            lo, hi = res[key]["range"]
            w = d.loc[lo:hi]
            for coin, color, ls in KIMCHI_STYLES:
                ax.plot(w.index, w[coin], color=color, linestyle=ls, linewidth=1.0, label=coin)
            ax.axhline(0, color=BLACK, linewidth=0.4)
            c = res[key]["common"]
            ax.set_title(f"min pairwise corr. {c['min_corr_levels']:.3f}", fontsize=6.5, pad=2, loc="right")
            ax.set_title(f"{tag} {title}", fontsize=7, pad=2, loc="left", fontweight="bold")
            ax.set_ylabel("KRW premium (bps)")
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
            ax.margins(x=0.01)
        h, lab = axes[0].get_legend_handles_labels()
        fig.legend(h, lab, loc="lower center", bbox_to_anchor=(0.5, 0.93), ncol=3, frameon=False, handlelength=2.0)
    return _save(fig, out)


# ---- captions --------------------------------------------------------------------------------------------------------------------------------------

def _pct(x: float) -> str:
    return f"{100 * x:.0f}\\%"


def build_captions() -> str:
    """LaTeX caption macros, each number read from a report (source noted in the trailing comment)."""
    rep = anchor_slopes()
    raw, net = rep["raw"], rep["netted"]
    gmm = _j(GMM_APPLIED)["bitfinex"]["specs"]
    rob = _j(ROBUSTNESS)
    head = rob["headline"]
    sim = _j(SIMULATION)
    q = _j(Q1_RESULTS)
    k = _j(KIMCHI)["windows"]
    marks = rail_markers()
    og = rob["summary"]["overall"]["gmm"]
    sims = sim["scenarios"]
    caps = {
        "CapAnchorScatter": (
            f"Netting Tether's own price moves the Bitfinex daily slope from {raw['est']:.2f} to {net['est']:.2f}. "
            f"Each point is one of the {rep['n']} days of the Bitfinex anchored window. Panel (a) plots the Bitfinex USDT price $D$ against the BTC gap $L$; "
            f"the dashed line has slope one and the fitted slope is {raw['est']:.2f} (95\\% interval from a week-block bootstrap, {raw['ci95_week'][0]:.2f} to "
            f"{raw['ci95_week'][1]:.2f}). Panel (b) subtracts Tether's own deviation $X$ measured on Kraken and the fitted slope becomes "
            f"{net['est']:.2f} ({net['ci95_week'][0]:.2f} to {net['ci95_week'][1]:.2f}); hourly GMM gives "
            f"{gmm['not_netted|eth_ltc_bch_etc']['lam']:.2f} before and {gmm['netted|eth_ltc_bch_etc']['lam']:.2f} after netting. The headline interval in the text uses month blocks instead.",
            "reports/unit_td/anchor_external.json slices/stress/adjusted_LDX/daily; reports/theory/gmm_applied.json"),
        "CapAnchorTimeseries": (
            f"Daily medians over the same window: the Bitfinex BTC gap $L$ (wide grey line), Bitfinex USDT $D$, and $D$ net of Kraken USDT $X$ (dashed), "
            f"with $X$ alone in the lower panel. The netted line follows $L$ closely while $D$ falls short of it. The solid line is the New York "
            f"Attorney General complaint on {marks['nyag']:%Y-%m-%d}; the dotted line marks the start of the Crypto Capital fiat-partner loss on "
            f"{marks['rails'][0][0]:%Y-%m-%d}, the only deposit-pause or partner-loss start the label file places inside the window.",
            "reports/unit_td/anchor_external.json; configs/fiat_rail_labels.json"),
        "CapRobustnessForest": (
            f"Each row is the GMM estimate of the unit offset $\\lambda$ with its 95\\% weekly-block bootstrap interval, changing one choice at a time around the "
            f"headline cell (diamond: {head['n']:,} hours). The dashed line is $\\lambda=1$; $\\lambda=0$ (dotted) sits on a separate left scale. "
            f"Across all {og['cells']} cells of the grid the estimate ranges from {og['min']:.3f} to {og['max']:.3f}, and the bootstrap interval contains one in "
            f"{_pct(og['share_boot_ci_contains_1'])} of cells and never contains zero.",
            "reports/theory/robustness.json headline, cells, summary/overall/gmm"),
        "CapSimulationPower": (
            f"Bars show how often the GMM test rejects $\\lambda=1$ (solid) and $\\lambda=0$ (hatched) in {sim['reps']:,} simulated samples per scenario; "
            f"diamonds show the same rate for OLS against $\\lambda=1$. The dashed line is the 5\\% level. Where the truth is one (S1, S5, S6) the GMM rejection of one is "
            f"{_pct(sims['S1']['estimators']['gmm']['rej_lam1'])}, {_pct(sims['S5']['estimators']['gmm']['rej_lam1'])} and "
            f"{_pct(sims['S6']['estimators']['gmm']['rej_lam1'])}, but when the anchor depegs and is not netted (S4) it is "
            f"{_pct(sims['S4']['estimators']['gmm']['rej_lam1'])}.",
            "reports/theory/simulation.json scenarios/*/estimators/{gmm,ols}"),
        "CapQErrors": (
            f"On the stressed hours the fuser's error is far below the median's. Panel (a) gives the mean absolute error, on a log scale, of each method on the stressed hours $S_{{\\mathrm{{hi}}}}$ of the three kept events and pooled "
            f"({q['pooled_s_hi']['fuser']['n']} hours). The pooled error is {q['pooled_s_hi']['fuser']['mae']:.1f} bps for the fuser, "
            f"{q['pooled_s_hi']['B0']['mae']:.1f} for the median (B0), {q['pooled_s_hi']['B2']['mae']:.1f} for unit conversion (B2), {q['pooled_s_hi']['B3']['mae']:.1f} for CRH (B3) and "
            f"{q['pooled_s_hi']['oracle']['mae']:.1f} for the oracle. Panel (b) shows the pooled mean difference in log error against each comparator with a day-block "
            f"95\\% interval; negative values favor the fuser, and the intervals against B0, B2 and B3 lie entirely below zero.",
            "reports/q1/results.json per_event, pooled_s_hi, primary"),
        "CapKimchiGaps": (
            f"Daily premium of the Korean won price over the dollar price for BTC, ETH and XRP in the two high-premium episodes. The three lines rise and fall "
            f"together: the smallest pairwise correlation of levels is {k['E1_2017-12_2018-01']['common']['min_corr_levels']:.3f} in panel (a) "
            f"({k['E1_2017-12_2018-01']['common']['days']} days) and {k['E2_2021-03_2021-05']['common']['min_corr_levels']:.3f} in panel (b) "
            f"({k['E2_2021-03_2021-05']['common']['days']} days).",
            "reports/kimchi/results.json windows/*/common"),
    }
    lines = ["% generated by www_paper.figures_v9; do not edit"]
    for name, (text, src) in caps.items():
        lines.append(f"\\newcommand{{\\{name}}}{{{text}}} % {src}")
    return "\n".join(lines) + "\n"


def write_captions(path: Path = CAPTIONS) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_captions())
    return path


def build_all(out_dir: Path = FIG_DIR) -> list[Path]:
    paths = [robustness_forest(out_dir / "robustness_forest.pdf"), simulation_power(out_dir / "simulation_power.pdf"),
             q1_errors(out_dir / "q1_errors.pdf")]
    if raw_data_available():
        paths = [anchor_scatter(out_dir / "anchor_scatter.pdf"), anchor_timeseries(out_dir / "anchor_timeseries.pdf"), *paths,
                 kimchi_gaps(out_dir / "kimchi_gaps.pdf")]
    return paths


def main() -> None:
    for path in build_all():
        print(f"WROTE {path.relative_to(ROOT)}")
    print(f"WROTE {write_captions().relative_to(ROOT)}")


if __name__ == "__main__":
    main()
