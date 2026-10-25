"""Two-panel main-text figure: the pre-registered currency panel and the official-rate fusion test.

Panel (a): per-currency IV lambda-hat with 95% intervals for the panel's eight currency units (reports/panel/results.json)
and for the Kraken slice, a second venue group (reports/panel_kraken/results.json). Panel (b): mean absolute error per unit of
official-rate conversion (O) against anchor-corrected conversion (A), log scale (reports/panel_fusion/results.json).
The caption macro is written to paper/generated/fig_caption_panel.tex with every number read from the reports.

    uv run python -m www_paper.figures_panel

Same deterministic conventions as figures_v9: fixed style, default rcParams at save, PDF metadata stripped.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from www_paper.figures_v9 import BLACK, BLUE, FULL, GREEN, VERMILION, _panel_tag, _rc, _save  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "reports/panel/results.json"
KRAKEN = ROOT / "reports/panel_kraken/results.json"
FUSION = ROOT / "reports/panel_fusion/results.json"
OUT = ROOT / "paper/figures/panel_figure.pdf"
CAPTION = ROOT / "paper/generated/fig_caption_panel.tex"
ORDER = ("ARS", "BRL", "KRW", "NGN", "RUB", "TRY", "UAH", "ZAR")
KRAKEN_ORDER = ("AUD", "CAD", "CHF", "EUR", "GBP")
UNITS = ("binance-BRL", "binance-RUB", "binance-TRY", "binance-ZAR", "bithumb-KRW", "upbit-KRW")
XLIM = (0.72, 1.40)


def _j(path: Path):
    return json.loads(path.read_text())


def _forest(ax, rows: list[tuple[str, dict, float, str, str]], x_max: float) -> list[tuple[str, float]]:
    """rows: (label, interval, y, colour, marker). Intervals beyond x_max are clipped with an arrow and their upper bound printed."""
    ticks = []
    for label, e, y, colour, marker in rows:
        hi = min(e["hi"], x_max)
        ax.plot([e["lo"], hi], [y, y], color=colour, linewidth=1.5, solid_capstyle="butt")
        if e["hi"] > x_max:
            ax.plot([x_max], [y], marker=">", color=colour, markersize=3.2, markeredgewidth=0, clip_on=False)
            ax.text(x_max - 0.012, y - 0.42, f"to {e['hi']:.2f}", fontsize=5.8, ha="right", va="bottom", color=colour)
        ax.plot([e["lam"]], [y], marker=marker, color=colour, markersize=4.6 if marker == "D" else 3.8, markeredgewidth=0)
        ticks.append((label, y))
    return ticks


def panel_figure(out: Path = OUT, panel: Path = RESULTS, kraken: Path = KRAKEN, fusion: Path = FUSION) -> Path:
    """Supports: the anchored slope is near one in every currency unit on both venue groups, and official-rate conversion errs by an order of magnitude more than anchor conversion."""
    p, k, f = _j(panel), _j(kraken), _j(fusion)
    with _rc():
        fig, (ax, bx) = plt.subplots(1, 2, figsize=(FULL, 2.2), gridspec_kw={"width_ratios": [1.0, 1.12], "wspace": 0.38})
        # (a) forest
        rows, y = [], 0.6
        for cur in ORDER:
            rows.append((f"{cur} ({p['by_currency'][cur]['stress_months']})", p["by_currency"][cur]["stress"]["iv"], y, BLUE, "o"))
            y += 1.0
        y += 0.35
        rows.append(("Panel pooled", p["pooled_stress"]["iv"], y, BLUE, "D"))
        y += 1.9
        k_start = y
        for cur in KRAKEN_ORDER:
            rows.append((f"{cur} ({k['by_currency'][cur]['stress_months']})", k["by_currency"][cur]["stress"]["iv"], y, GREEN, "s"))
            y += 1.0
        y += 0.35
        rows.append(("Kraken pooled", k["pooled_stress"]["iv"], y, GREEN, "D"))
        ticks = _forest(ax, rows, XLIM[1])
        ax.set_yticks([t[1] for t in ticks], [t[0] for t in ticks])
        ax.set_ylim(y + 0.7, -0.9)
        ax.tick_params(axis="y", length=0)
        ax.axvline(1.0, color=BLACK, linewidth=0.8, linestyle="--")
        ax.set_xlim(*XLIM)
        ax.set_xlabel("$\\hat\\lambda$ (IV, 95% block-bootstrap interval)")
        ax.text(XLIM[0] + 0.005, -0.45, "Binance, Upbit, Bithumb", fontsize=6.3, color=BLUE, va="center", ha="left", fontweight="bold")
        ax.text(XLIM[0] + 0.005, k_start - 1.05, "Kraken", fontsize=6.3, color=GREEN, va="center", ha="left", fontweight="bold")
        ax.plot([], [], color=BLACK, linestyle="--", linewidth=0.8, label="$\\lambda=1$ (unit wedge)")
        ax.legend(loc="upper right", frameon=False, handlelength=1.4, handletextpad=0.3, borderaxespad=0.1, bbox_to_anchor=(1.0, 0.93))
        _panel_tag(ax, "(a)")
        # (b) per-unit MAE, O against A, log scale
        venue = {"bithumb-KRW": "Bith.", "upbit-KRW": "Upbit"}
        labels = [f"{f['units'][u]['fiat']}\n{venue[u]}" if u in venue else f["units"][u]["fiat"] for u in UNITS]
        labels += ["Pooled"]
        o = [f["units"][u]["O"]["mae"] for u in UNITS] + [f["primary"]["O"]["mae"]]
        a = [f["units"][u]["A"]["mae"] for u in UNITS] + [f["primary"]["A"]["mae"]]
        xs = list(range(len(UNITS))) + [len(UNITS) + 0.35]
        w = 0.38
        bx.bar([x - w / 2 for x in xs], o, width=w, color=VERMILION, label="O: official-rate conversion")
        bx.bar([x + w / 2 for x in xs], a, width=w, color=BLUE, hatch="////", edgecolor="white", linewidth=0, label="A: anchor-corrected conversion")
        bx.set_yscale("log")
        bx.set_ylim(1.5, 4000)
        for x, ov, av in zip(xs, o, a):
            bx.text(x - w / 2, ov * 1.12, f"{ov:.0f}", ha="center", va="bottom", fontsize=5.6)
            bx.text(x + w / 2, av * 1.12, f"{av:.1f}", ha="center", va="bottom", fontsize=5.6)
        bx.set_xticks(xs, labels)
        bx.tick_params(axis="x", length=0)
        bx.set_ylabel("mean absolute error (bps, log scale)")
        bx.legend(loc="upper left", frameon=False, handlelength=1.3, handletextpad=0.4, borderaxespad=0.1, ncol=1)
        _panel_tag(bx, "(b)")
    return _save(fig, out)


def build_caption(panel: Path = RESULTS, kraken: Path = KRAKEN, fusion: Path = FUSION) -> str:
    p, k, f = _j(panel), _j(kraken), _j(fusion)
    ps, ks = p["pooled_stress"]["iv"], k["pooled_stress"]["iv"]
    text = (
        f"Pooled anchored slopes are near one on both venue groups, and official-rate conversion errs about "
        f"{f['primary']['O']['mae'] / f['primary']['A']['mae']:.0f} times more than anchor conversion. "
        f"Panel (a) gives the IV slope $\\hat\\lambda$ of $(D-X)$ on $L$ by currency (stress venue-months in brackets) "
        f"with 95\\% block-bootstrap intervals: the panel pools to {ps['lam']:.3f} ({ps['lo']:.3f} to {ps['hi']:.3f}) and "
        f"the Kraken slice to {ks['lam']:.3f} ({ks['lo']:.3f} to {ks['hi']:.3f}); the axis starts at 0.72 and the AUD interval is cut at the right edge. "
        f"Panel (b) gives the mean absolute error of converting at the official rate (O) against converting through the venue's own stablecoin market (A), "
        f"scored against Kraken BTC/USD, on a log scale: {f['primary']['O']['mae']:.1f} against {f['primary']['A']['mae']:.1f} bps pooled over {f['sample']['n_units']} units."
    )
    src = "reports/panel/results.json; reports/panel_kraken/results.json; reports/panel_fusion/results.json"
    return f"% generated by www_paper.figures_panel; do not edit\n\\newcommand{{\\CapPanelFigure}}{{{text}}} % {src}\n"


def write_caption(path: Path = CAPTION) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_caption())
    return path


def main() -> int:
    print(f"wrote {panel_figure()}")
    print(f"wrote {write_caption()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
