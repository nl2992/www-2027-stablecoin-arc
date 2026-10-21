"""Stablecoin anchor test: is a common BTC/ETH gap the exchange's dollar, or exchange-wide crypto demand?

USDT is a dollar claim with no crypto exposure. If a venue's dollar moves by u, the venue's USDT/USD price (USDT priced
in the venue's dollars) moves by u as well; if crypto demand lifts BTC and ETH instead, USDT/USD does not move. With
  L = 1e4 [log P_venue(BTC/USD) - log P_ref(BTC/USD)]    (the ledger gap, as in probe.py)
  D = 1e4 log P_venue(USDT/USD)                           (USDT in the venue's dollars)
  T = D - L                                               (what the gap leaves unexplained)
a unit shift gives slope(D on L) = 1 and T = 0; a crypto-only premium gives slope 0 and T = -L.

All series are hourly medians of traded-minute log closes (``www_auto.probe.hourly_median_log_close``). Binance.US uses
the rescue decomposition's hourly components (``www_rescue.decompose.components``). Statistics per slice:
  hours_both, daily/hourly corr(L, D), OLS slope of D on L over daily medians with a 95% block bootstrap over weeks
  (1,000 draws, seed 20261020), and, over hours with |L| >= 50 bps, the median L, D, T and the share with |T| <= 0.25|L|.

    uv run python -m www_auto.anchor           # writes reports/unit_td/anchor.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import probe

REPO = probe.REPO
OUTPUT = REPO / "reports" / "unit_td" / "anchor.json"
LEDGER_PANEL = REPO / "reports" / "rescue" / "ledger_panel.json"
BIG_BPS = 50.0
TOL = 0.25           # |T| <= TOL |L| counts as "the USDT price followed the gap"
DEMAND_TOL = 0.5     # |T| > DEMAND_TOL |L| counts as "USDT did not follow"
AGREE_TOL = 0.25     # BTC and ETH gaps agree when |g_ETH - L| <= AGREE_TOL |L|
PLACEBO_BPS = 20.0
TOKEN_EVENT_MONTHS = ("2022-05", "2023-03")
DRAWS, SEED = 1000, 20261020
MIN_DAYS = 30
STRESS = ("2018-11-27", "2019-05-31")
BFX_SLICES = {"stress_2018-11-27_2019-05-31": STRESS, **{str(y): (f"{y}-01-01", f"{y}-12-31") for y in range(2018, 2024)}}
BNUS_SLICES = {"jun_jul_2023": ("2023-06-01", "2023-07-31"), "year_2023": ("2023-01-01", "2023-12-31"),
               "rescue_window_2023-06-22_2023-07-31": ("2023-06-22", "2023-07-31"),
               "all_held_months": ("2022-10-01", "2025-10-31")}


def _cut(x: pd.DataFrame | pd.Series, lo: str, hi: str):
    return x[(x.index >= pd.Timestamp(lo, tz="UTC")) & (x.index < pd.Timestamp(hi, tz="UTC") + pd.Timedelta(days=1))]


def _slope(x: np.ndarray, y: np.ndarray) -> float:
    xc = x - x.mean()
    den = float((xc ** 2).sum())
    return float((xc * (y - y.mean())).sum() / den) if den > 0 else float("nan")


def slope_ci(daily: pd.DataFrame, draws: int = DRAWS, seed: int = SEED) -> list[float] | None:
    """95% interval for the OLS slope of D on L over days, resampling whole weeks."""
    weeks = [g[["L", "D"]].to_numpy() for _, g in daily.groupby(daily.index.tz_localize(None).to_period("W"))]
    if len(weeks) < 5:
        return None
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(draws):
        m = np.concatenate([weeks[i] for i in rng.integers(0, len(weeks), len(weeks))])
        out.append(_slope(m[:, 0], m[:, 1]))
    lo, hi = np.nanpercentile(out, [2.5, 97.5])
    return [float(lo), float(hi)]


def stats(L: pd.Series, D: pd.Series, big: float = BIG_BPS) -> dict[str, Any]:
    """Anchor statistics of hourly L and D (bps) on the hours where both exist."""
    h = pd.concat([L.rename("L"), D.rename("D")], axis=1).dropna()
    out: dict[str, Any] = {"hours_both": int(len(h))}
    if len(h) < 24:
        return out
    h["T"] = h["D"] - h["L"]
    daily = h.groupby(h.index.floor("D")).median()
    out["days"] = int(len(daily))
    out["hourly_corr"] = float(h["L"].corr(h["D"])) if h["L"].std() > 0 and h["D"].std() > 0 else None
    if len(daily) >= MIN_DAYS and daily["L"].std() > 0:
        out["daily_corr"] = float(daily["L"].corr(daily["D"]))
        out["daily_slope"] = _slope(daily["L"].to_numpy(), daily["D"].to_numpy())
        out["daily_slope_ci95"] = slope_ci(daily)
    b = h[h["L"].abs() >= big]
    out["hours_big"] = int(len(b))
    if len(b):
        out.update({"median_L": float(b["L"].median()), "median_D": float(b["D"].median()), "median_T": float(b["T"].median()),
                    "share_abs_T_le_quarter_L": float((b["T"].abs() <= TOL * b["L"].abs()).mean())})
    return out


def demand_share(L: pd.Series, g_eth: pd.Series, D: pd.Series, big: float = BIG_BPS) -> dict[str, Any]:
    """Among hours where BTC and ETH gaps agree, the share where USDT does not follow (|T| > 0.5|L|)."""
    h = pd.concat([L.rename("L"), g_eth.rename("E"), D.rename("D")], axis=1).dropna()
    agree = h[(h["L"].abs() >= big) & ((h["E"] - h["L"]).abs() <= AGREE_TOL * h["L"].abs())]
    if agree.empty:
        return {"hours_agree": 0}
    t = agree["D"] - agree["L"]
    nf = agree[t.abs() > DEMAND_TOL * agree["L"].abs()]
    return {"hours_agree": int(len(agree)), "hours_not_following": int(len(nf)),
            "share_not_following": float(len(nf) / len(agree)),
            "median_L_not_following": float(nf["L"].median()) if len(nf) else None,
            "median_D_not_following": float(nf["D"].median()) if len(nf) else None,
            "days_not_following": int(nf.index.floor("D").nunique())}


def placebo(gap: pd.Series, D: pd.Series, thr: float = PLACEBO_BPS) -> dict[str, Any]:
    """Open-rail pair: does Bitstamp USDT/USD move with a Coinbase-Bitstamp BTC gap?"""
    h = pd.concat([gap.rename("L"), D.rename("D")], axis=1).dropna()
    out: dict[str, Any] = {"hours_both": int(len(h)), "threshold_bps": thr}
    if len(h) < 24:
        return out
    out["median_D_all_hours"] = float(h["D"].median())
    hi = h[h["L"].abs() >= thr]
    out["hours_big"] = int(len(hi))
    out["days_big"] = int(hi.index.floor("D").nunique())
    if len(hi) >= 5:
        t = hi["D"] - hi["L"]
        out.update({"median_L": float(hi["L"].median()), "median_D": float(hi["D"].median()), "median_T": float(t.median()),
                    "share_abs_T_le_quarter_L": float((t.abs() <= TOL * hi["L"].abs()).mean()),
                    "share_abs_D_le_quarter_L": float((hi["D"].sub(h["D"].median()).abs() <= TOL * hi["L"].abs()).mean()),
                    "hourly_corr_big": float(hi["L"].corr(hi["D"])), "hourly_slope_big": _slope(hi["L"].to_numpy(), hi["D"].to_numpy())})
        for sign, sel in (("positive_gap", hi["L"] > 0), ("negative_gap", hi["L"] < 0)):
            s = hi[sel]
            out[sign] = {"hours": int(len(s)), "median_L": float(s["L"].median()) if len(s) else None,
                         "median_D": float(s["D"].median()) if len(s) else None}
        out["by_month"] = {str(k): int(v) for k, v in hi.groupby(hi.index.tz_localize(None).to_period("M")).size().items()}
    out["all_hours"] = stats(h["L"], h["D"], big=thr)
    # the daily slope is driven by USDT's own token events (Terra 2022-05, SVB 2023-03), so repeat without those months
    keep = ~h.index.tz_localize(None).to_period("M").astype(str).isin(TOKEN_EVENT_MONTHS)
    out["all_hours_excl_token_events"] = {"excluded_months": list(TOKEN_EVENT_MONTHS), **stats(h["L"][keep], h["D"][keep], big=thr)}
    return out


def phase_crosscheck(L: pd.Series, D: pd.Series, ledger: Path = LEDGER_PANEL) -> dict[str, Any]:
    """Hourly-median phase medians of D and T against ledger_panel (minute-level, minutes traded on every leg)."""
    ep = json.loads(ledger.read_text())["episodes"]["L2019-04-BITFINEX-NYAG"]
    h = pd.concat([L.rename("L"), D.rename("D")], axis=1).dropna()
    h["T"] = h["D"] - h["L"]
    rows = {}
    for key, col in (("d_usdt", "D"), ("t_usdt", "T")):
        for r in ep[key]:
            x = _cut(h[col], r["start"], (pd.Timestamp(r["end"]) - pd.Timedelta(days=1)).strftime("%Y-%m-%d"))
            mine = float(x.median()) if len(x) else None
            rows[f"{key}/{r['phase']}"] = {"ledger_panel_minute_median": r.get("median_bps"), "hourly_median": mine,
                                          "difference": None if mine is None or r.get("median_bps") is None else mine - r["median_bps"],
                                          "ledger_panel_minutes": r.get("minutes"), "hours": int(len(x))}
    return rows


def load_series() -> dict[str, pd.Series]:
    panel, meta = probe.build_panel()
    s = {f"{v}|{a}": panel[(v, a)] for v in probe.VENUES for a in probe.ASSETS}
    s["bitfinex|USDT"] = probe.hourly_median_log_close("bitfinex", "USTUSD")[0]
    s["bitstamp|USDT"] = probe.hourly_median_log_close("bitstamp", "USDTUSD")[0]
    return s


def bitfinex_minute_aligned(raw: Path, manifest: Path) -> dict[str, Any]:
    """Second timing convention (ledger_panel's): D and L from minutes traded on every leg, then hourly medians."""
    from www_rescue.decompose import components
    from www_rescue.ledger_panel import series

    ms = [m.strftime("%Y-%m") for m in pd.period_range("2018-11", "2023-12", freq="M")]
    ust, btc = series(raw, manifest, "bitfinex", "USTUSD", ms), series(raw, manifest, "bitfinex", "BTCUSD", ms)
    h = components(ust, btc, series(raw, manifest, "bitstamp", "BTCUSD", ms), ust)
    return {"definition": "minute-aligned L and D (traded on all legs), hourly medians; T = D - L on hours with both",
            "slices": {n: stats(_cut(h["L"], lo, hi), _cut(h["D"], lo, hi)) for n, (lo, hi) in BFX_SLICES.items()}}


def bitfinex(s: dict[str, pd.Series], raw: Path, manifest: Path) -> dict[str, Any]:
    L = 1e4 * (s["bitfinex|BTC"] - s["bitstamp|BTC"])
    E = 1e4 * (s["bitfinex|ETH"] - s["bitstamp|ETH"])
    D = 1e4 * s["bitfinex|USDT"]
    out: dict[str, Any] = {"definition": "L = Bitfinex BTC vs Bitstamp BTC; g_ETH = Bitfinex ETH vs Bitstamp ETH; D = Bitfinex USTUSD",
                           "slices": {}, "slices_eth_gap": {}}
    for name, (lo, hi) in BFX_SLICES.items():
        out["slices"][name] = stats(_cut(L, lo, hi), _cut(D, lo, hi))
        out["slices_eth_gap"][name] = stats(_cut(E, lo, hi), _cut(D, lo, hi))
    out["minute_aligned"] = bitfinex_minute_aligned(raw, manifest)
    out["phase_crosscheck_2019"] = phase_crosscheck(L, D)
    d_all = _cut(D, "2018-11-27", "2023-12-31")
    out["demand_alternative"] = {
        "all_usdt_hours_2018-11-27_on": demand_share(_cut(L, *("2018-11-27", "2023-12-31")), _cut(E, *("2018-11-27", "2023-12-31")), d_all),
        **{name: demand_share(_cut(L, lo, hi), _cut(E, lo, hi), _cut(D, lo, hi)) for name, (lo, hi) in BFX_SLICES.items()}}
    return out


def binance_us(raw: Path, manifest: Path) -> dict[str, Any]:
    from www_events.bitstamp import load_months
    from www_events.runner import load_binance_months
    from www_rescue.decompose import components, summarize
    from www_rescue.platform_dollar import traded_log_close

    bus = lambda sym: traded_log_close(load_binance_months(raw / "binance_us", sym, "x")[0], "x")  # noqa: E731
    bst = lambda pair: traded_log_close(load_months(raw / "bitstamp", pair, "y", manifest)[0], "y")  # noqa: E731
    h = components(bus("USDTUSD"), bus("BTCUSD"), bst("BTCUSD"), bst("USDTUSD"))
    out: dict[str, Any] = {"definition": "rescue decomposition hourly components (minute-aligned, hourly medians); T = D - L",
                           "slices": {n: stats(_cut(h["L"], lo, hi), _cut(h["D"], lo, hi)) for n, (lo, hi) in BNUS_SLICES.items()}}
    w = _cut(h, "2023-06-22", "2023-07-31")
    out["rescue_summary_window"] = summarize(w)
    return out


def placebo_open_rail(s: dict[str, pd.Series]) -> dict[str, Any]:
    gap = 1e4 * (s["coinbase|BTC"] - s["bitstamp|BTC"])
    D = 1e4 * s["bitstamp|USDT"]
    lo, hi = "2022-04-01", "2023-12-31"
    out = {"definition": "L = Coinbase BTC vs Bitstamp BTC; D = Bitstamp USDTUSD (held from 2022-04); both rails open",
           "window": [lo, hi], "bitstamp_usdt_hours": int(_cut(D, lo, hi).notna().sum()),
           "coinbase_has_usdt": False}
    out["thr20_2022-04_2023"] = placebo(_cut(gap, lo, hi), _cut(D, lo, hi), PLACEBO_BPS)
    out["thr20_2023"] = placebo(_cut(gap, "2023-01-01", hi), _cut(D, "2023-01-01", hi), PLACEBO_BPS)
    out["thr20_2022"] = placebo(_cut(gap, lo, "2022-12-31"), _cut(D, lo, "2022-12-31"), PLACEBO_BPS)
    return out


def build(series: dict[str, pd.Series], raw: Path = probe.RAW, manifest: Path = probe.MANIFEST) -> dict[str, Any]:
    return {"method": __doc__.strip().split("\n\n")[0], "big_bps": BIG_BPS, "follow_tol": TOL, "demand_tol": DEMAND_TOL,
            "agree_tol": AGREE_TOL, "bootstrap": {"draws": DRAWS, "seed": SEED, "block": "week"},
            "bitfinex": bitfinex(series, raw, manifest), "binance_us": binance_us(raw, manifest), "placebo": placebo_open_rail(series)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="www_auto.anchor")
    ap.add_argument("--out", type=Path, default=OUTPUT)
    args = ap.parse_args(argv)
    result = build(load_series())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(f"WROTE {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
