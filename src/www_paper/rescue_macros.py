"""Generate macros and tables for the ledger-failure side from reports/rescue/*.json.

Writes paper/generated/rescue_numbers.tex, ledger_phase_table.tex and fiat_rail_table.tex.
Run: ``uv run python -m www_paper.rescue_macros``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "paper/generated"
NUMBERS = GEN / "rescue_numbers.tex"
PHASE_TABLE = GEN / "ledger_phase_table.tex"
FIAT_TABLE = GEN / "fiat_rail_table.tex"
DECOMP_TABLE = GEN / "decomposition_table.tex"
MONITOR_TABLE = GEN / "monitor_table.tex"
SENS_TABLE = GEN / "monitor_sensitivity_table.tex"
DECOMP = ROOT / "reports/rescue/decomposition.json"
PLATFORM = ROOT / "reports/rescue/platform_dollar.json"
FIAT = ROOT / "reports/rescue/fiat_rail.json"
MONITOR = ROOT / "reports/rescue/monitor.json"
LEDGER = ROOT / "docs/review/RESCUE_SEARCH.md"
PANEL = ROOT / "reports/rescue/ledger_panel.json"

PHASE_LABEL = {"pre": "Before SEC complaint", "sec_complaint": "SEC complaint", "deposits_suspended": "Deposits suspended",
               "withdrawal_halt_window": "Withdrawal-halt window", "crypto_only_transition": "Deposits shut, withdrawals open",
               "impaired": "Rail impaired (USDT only)", "restored": "Rails restored"}
MACRO_PHASE = {"pre": "Pre", "sec_complaint": "Sec", "deposits_suspended": "Dep", "withdrawal_halt_window": "Halt",
               "crypto_only_transition": "Trans", "impaired": "Impaired", "restored": "Restored"}


def _f(v: float, d: int = 1) -> str:
    s = f"{v:,.{d}f}"
    return s[1:] if s.startswith("-") and not s.strip("-0.,") else s  # no negative zero


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def directions_tried() -> tuple[int, int]:
    """Count ledger rows R1..Rn in the rescue-search log and how many were discarded."""
    rows = [line for line in LEDGER.read_text().splitlines() if line.startswith("| R") and line[3].isdigit()]
    return len(rows), sum("DISCARD" in r for r in rows)


def numbers() -> str:
    dec, plat, fiat = _load(DECOMP)["windows"], _load(PLATFORM), _load(FIAT)["cases"]
    m: list[tuple[str, str, str]] = []
    for tag, key in (("Svb", "token_failure_svb"), ("Bnus", "ledger_failure_binanceus")):
        s = dec[key]["summary"]
        m += [(f"NumDec{tag}D", _f(s["median_D"]), f"{key}/median_D"),
              (f"NumDec{tag}L", _f(s["median_L"]), f"{key}/median_L"),
              (f"NumDec{tag}T", _f(s["median_T"]), f"{key}/median_T"),
              (f"NumDec{tag}Dref", _f(s["median_D_ref"]), f"{key}/median_D_ref"),
              (f"NumDec{tag}Gap", _f(s["median_abs_T_minus_D_ref"]), f"{key}/median_abs_T_minus_D_ref"),
              (f"NumDec{tag}Share", f"{100 * s['median_ledger_share']:.0f}", f"{key}/median_ledger_share"),
              (f"NumDec{tag}Hours", f"{s['hours']:,}", f"{key}/hours"),
              (f"NumDec{tag}Extreme", _f(s["extreme_D"], 0), f"{key}/extreme_D")]
    for asset, rows in (("Usdt", plat["pd_usdt"]), ("Btc", plat["pd_btc"]), ("Usdc", plat["pd_usdc"])):
        for r in rows:
            if r.get("minutes"):
                m.append((f"NumPd{asset}{MACRO_PHASE[r['phase']]}", _f(r["median_bps"]), f"pd_{asset.lower()}/{r['phase']}"))
    tri = [abs(r["median_bps"]) for r in plat["within_venue_triangle"] if r.get("minutes")]
    m.append(("NumTriMaxAbs", _f(max(tri)), "within_venue_triangle/max |phase median|"))
    m.append(("NumIdentUsdcCorrTrans", f"{plat['identification_usdt_vs_usdc']['crypto_only_transition']['corr_hourly']:.2f}",
              "identification_usdt_vs_usdc/crypto_only_transition/corr"))
    daily = plat["daily_median_pd_usdt"]
    worst = min(daily.values())
    m.append(("NumPdUsdtWorstDay", _f(worst, 0), "daily_median_pd_usdt/min"))
    corr = [v["corr_hourly"] for k, v in plat["identification_usdt_vs_btc"].items()
            if "corr_hourly" in v and k not in ("deposits_suspended", "restored")]
    m.append(("NumIdentCorrMin", f"{min(corr):.3f}", "identification (all phases except deposits_suspended, restored)/min corr"))
    m.append(("NumIdentCorrDep", f"{plat['identification_usdt_vs_btc']['deposits_suspended']['corr_hourly']:.2f}",
              "identification/deposits_suspended/corr"))
    for fx, c in fiat.items():
        for asset in ("usdt", "btc"):
            rows = {r["phase"]: r["median_bps"] for r in c[f"pd_{asset}"] if r.get("minutes")}
            m.append((f"NumFiat{fx.title()}{asset.title()}Pre", _f(rows["pre"]), f"{fx}/pd_{asset}/pre"))
            m.append((f"NumFiat{fx.title()}{asset.title()}Post", _f(rows["post_4w"]), f"{fx}/pd_{asset}/post_4w"))
            m.append((f"NumFiat{fx.title()}{asset.title()}Change", _f(rows["post_4w"] - rows["pre"]), f"{fx}/pd_{asset}/post-pre"))
        m.append((f"NumFiat{fx.title()}Corr", f"{c['identification']['post_4w']['corr_hourly']:.2f}", f"{fx}/identification/post_4w"))
    liq = {r["phase"]: r for r in plat["liquidity_usdtusd"]}
    for ph, tag in (("pre", "Pre"), ("crypto_only_transition", "Trans")):
        m += [(f"NumLiq{tag}Share", f"{100 * liq[ph]['traded_minute_share']:.0f}", f"liquidity_usdtusd/{ph}/traded_minute_share"),
              (f"NumLiq{tag}Trades", f"{liq[ph]['median_hourly_trades']:,.0f}", f"liquidity_usdtusd/{ph}/median_hourly_trades"),
              (f"NumLiq{tag}VolK", f"{liq[ph]['median_hourly_quote_volume'] / 1e3:,.0f}",
               f"liquidity_usdtusd/{ph}/median_hourly_quote_volume (thousands)")]
    alt = {r["phase"]: r for r in plat["pd_btc_alt_reference"]}
    m.append(("NumPdBtcAltTrans", _f(alt["crypto_only_transition"]["median_bps"]), "pd_btc_alt_reference/crypto_only_transition"))
    m.append(("NumPdBtcAltHalt", _f(alt["withdrawal_halt_window"]["median_bps"]), "pd_btc_alt_reference/withdrawal_halt_window"))
    sens = plat["boundary_sensitivity_pd_usdt"]
    m += [("NumSensTransLo", _f(abs(sens["crypto_only_transition"]["max"])), "boundary_sensitivity/transition/|max|"),
          ("NumSensTransHi", _f(abs(sens["crypto_only_transition"]["min"])), "boundary_sensitivity/transition/|min|"),
          ("NumSensHaltLo", _f(sens["withdrawal_halt_window"]["min"]), "boundary_sensitivity/halt/min"),
          ("NumSensHaltHi", _f(sens["withdrawal_halt_window"]["max"]), "boundary_sensitivity/halt/max")]
    ib = plat["identification_usdt_vs_btc"]
    m += [("NumIdentChgTrans", f"{ib['crypto_only_transition']['corr_hourly_changes']:.2f}", "ident/transition/corr of changes"),
          ("NumIdentChgHalt", f"{ib['withdrawal_halt_window']['corr_hourly_changes']:.2f}", "ident/halt/corr of changes"),
          ("NumIdentChgDep", f"{ib['deposits_suspended']['corr_hourly_changes']:.2f}", "ident/deposits_suspended/corr of changes"),
          ("NumIdentGapTrans", f"{100 * ib['crypto_only_transition']['gap_to_size']:.1f}", "ident/transition/gap_to_size (%)"),
          ("NumIdentGapHalt", f"{100 * ib['withdrawal_halt_window']['gap_to_size']:.1f}", "ident/halt/gap_to_size (%)")]
    mon = _load(MONITOR)
    bp, cd = mon["by_period"], mon["calm_detail"]
    pct = lambda v, d=1: f"{100 * v:.{d}f}"  # noqa: E731
    m += [("NumMonHours", f"{mon['hours_evaluated']:,}", "monitor/hours_evaluated"),
          ("NumMonMonths", str(len(mon["months_covered"])), "monitor/months_covered"),
          ("NumMonRailLedger", pct(bp["binanceus_rail_cut"]["ledger_flag"]["flag_share"]), "monitor/rail/ledger"),
          ("NumMonSvbUsdc", pct(bp["svb_run"]["token_flag_USDC"]["flag_share"]), "monitor/svb/token USDC"),
          ("NumMonSvbUsdt", pct(bp["svb_run"]["token_flag_USDT"]["flag_share"]), "monitor/svb/token USDT"),
          ("NumMonSvbLedger", pct(bp["svb_run"]["ledger_flag"]["flag_share"]), "monitor/svb/ledger"),
          ("NumMonFtxLedger", pct(bp["ftx_collapse"]["ledger_flag"]["flag_share"]), "monitor/ftx/ledger"),
          ("NumMonCalmHours", f"{bp['calm']['hours']:,}", "monitor/calm/hours"),
          ("NumMonCalmLedger", pct(bp["calm"]["ledger_flag"]["flag_share"]), "monitor/calm/ledger"),
          ("NumMonCalmOutside", pct(cd["ledger_flag_share_outside_unresolved_window"], 2), "monitor/calm outside unresolved"),
          ("NumMonUnresolvedHours", str(cd["ledger_flag_hours_inside_unresolved_window"]), "monitor/calm inside unresolved"),
          ("NumMonFalseHours", str(sum(cd["ledger_flag_hours_by_day"].values()) - cd["ledger_flag_hours_inside_unresolved_window"]),
           "monitor/calm flags outside unresolved window")]
    sens = mon["sensitivity"]
    col = lambda k: [r[k] for r in sens]  # noqa: E731
    m += [("NumSensRailMin", pct(min(col("binanceus_rail_cut_ledger_flag")), 0), "monitor/sensitivity/rail ledger min"),
          ("NumSensRailMax", pct(max(col("binanceus_rail_cut_ledger_flag")), 0), "monitor/sensitivity/rail ledger max"),
          ("NumSensCalmMin", pct(min(col("calm_ledger_flag"))), "monitor/sensitivity/calm ledger min"),
          ("NumSensCalmMax", pct(max(col("calm_ledger_flag"))), "monitor/sensitivity/calm ledger max"),
          ("NumSensSvbUsdcMin", pct(min(col("svb_run_token_flag_USDC")), 0), "monitor/sensitivity/svb USDC min"),
          ("NumSensSvbUsdcMax", pct(max(col("svb_run_token_flag_USDC")), 0), "monitor/sensitivity/svb USDC max"),
          ("NumSensTokenLedgerMax", pct(max(col("svb_run_ledger_flag") + col("ftx_collapse_ledger_flag"))),
           "monitor/sensitivity/max ledger flag share in SVB or FTX"),
          ("NumSensSettings", str(len(sens)), "monitor/sensitivity/settings")]
    signed = {name: value for name, value, _ in m}
    for name in ("NumPdUsdtTrans", "NumPdBtcTrans", "NumPdUsdcTrans", "NumPdBtcAltTrans", "NumPdUsdtWorstDay", "NumFiatEurUsdtChange", "NumFiatEurBtcChange"):
        m.append((name + "Abs", signed[name].lstrip("-"), f"absolute value of {name}"))
    tried, discarded = directions_tried()
    m += [("NumDirectionsTried", str(tried), "RESCUE_SEARCH.md ledger rows"),
          ("NumDirectionsDiscarded", str(discarded), "RESCUE_SEARCH.md ledger rows marked DISCARD")]
    m += panel_macros()
    lines = ["% generated by www_paper.rescue_macros from reports/rescue/*.json; do not edit"]
    lines += [f"\\newcommand{{\\{name}}}{{{value}}} % {src}" for name, value, src in m]
    return "\n".join(lines) + "\n"


def _ci(r: dict[str, Any]) -> str:
    if not r.get("minutes"):
        return "--"
    ci = r.get("ci95_bps")
    return _f(r["median_bps"]) + (f" [{_f(ci[0])}, {_f(ci[1])}]" if ci else "")


def phase_table() -> str:
    plat = _load(PLATFORM)
    cols = [{r["phase"]: r for r in plat[k]} for k in ("pd_usdt", "pd_btc", "pd_btc_alt_reference", "pd_usdc",
                                                        "within_venue_triangle")]
    liq = {r["phase"]: r for r in plat["liquidity_usdtusd"]}
    ident = plat["identification_usdt_vs_btc"]
    rows = []
    for ph in plat["phases"]:
        n = ph["phase"]
        corr = ident[n].get("corr_hourly_changes")
        cells = " & ".join(_ci(c[n]) for c in cols[:2])
        rest = " & ".join(_f(c[n]["median_bps"]) if c[n].get("minutes") else "--" for c in cols[2:])
        trades = liq[n]["median_hourly_trades"]
        rows.append(f"{PHASE_LABEL[n]} & {ph['start']} & {cells} & {rest} & {'--' if corr is None else f'{corr:.2f}'} & "
                    f"{'--' if trades is None else f'{trades:,.0f}'} \\\\")
    return ("% generated by www_paper.rescue_macros; do not edit\n\\begin{table*}[t]\n\\footnotesize\n"
            "\\caption{Binance.US dollar versus external dollars by documented rail phase. $PD_X$: median platform-dollar "
            "dislocation of asset $X$ in bps against Bitstamp (hour-block bootstrap 95\\% intervals for USDT and BTC); "
            "BTC$^\\ast$: against the second reference, Binance.com BTC/USDT $\\times$ Bitstamp USDT/USD; $W$: median "
            "within-venue triangle; $\\rho_\\Delta$: correlation of hourly changes of $PD_{\\mathrm{USDT}}$ and "
            "$PD_{\\mathrm{BTC}}$; trades: median trades per hour on Binance.US USDT/USD. BTC/USD and USDC/USD did not "
            "trade on Binance.US while the rail was impaired.}\n"
            "\\label{tab:phases}\n\\setlength{\\tabcolsep}{4pt}\n\\begin{tabular}{@{}llrrrrrrr@{}}\n\\toprule\n"
            "Phase & From & $PD_{\\mathrm{USDT}}$ & $PD_{\\mathrm{BTC}}$ & $PD_{\\mathrm{BTC}^\\ast}$ & "
            "$PD_{\\mathrm{USDC}}$ & $W$ & $\\rho_\\Delta$ & trades/h \\\\\n\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n\\end{table*}\n")


def monitor_table() -> str:
    mon = _load(MONITOR)
    names = {"calm": "Calm months", "ftx_collapse": "FTX collapse (2022-11)", "svb_run": "SVB run (2023-03)",
             "binanceus_rail_cut": "Binance.US rail cut (2023-06/07)"}
    rows = []
    for key in ("calm", "ftx_collapse", "svb_run", "binanceus_rail_cut"):
        r = mon["by_period"][key]
        rows.append(f"{names[key]} & {r['hours']:,} & {100 * r['ledger_flag']['flag_share']:.1f} & "
                    f"{100 * r['token_flag_USDT']['flag_share']:.1f} & {100 * r['token_flag_USDC']['flag_share']:.1f} \\\\")
    return ("% generated by www_paper.rescue_macros; do not edit\n\\begin{table}[t]\n\\small\n"
            "\\caption{Hourly monitor on Binance.US over every month with overlapping data: share of hours (\\%) flagged "
            "as ledger failure ($|L|\\ge$ R1 threshold and USDT agreeing within a quarter) or token failure "
            "($|T_q|\\ge$ R1 threshold).}\n\\label{tab:monitor}\n\\setlength{\\tabcolsep}{3pt}\n"
            "\\begin{tabular}{@{}lrrrr@{}}\n\\toprule\nPeriod & Hours & Ledger & Token USDT & Token USDC \\\\\n\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")


def fiat_table() -> str:
    cases = _load(FIAT)["cases"]
    rows = []
    for fx, c in cases.items():
        for asset in ("usdt", "btc"):
            r = {x["phase"]: x for x in c[f"pd_{asset}"]}
            rows.append(f"{fx} & {asset.upper()} & {_ci(r['pre'])} & {_ci(r['post_4w'])} & {_ci(r['later'])} \\\\")
    return ("% generated by www_paper.rescue_macros; do not edit\n\\begin{table}[t]\n\\small\n"
            "\\caption{Binance.com fiat ledgers versus Bitstamp around the 2023 Paysafe rail cuts (GBP 2023-05-22; EUR "
            "2023-09-25): median $PD_X$ in bps with 95\\% intervals, before, in the four weeks after, and later.}\n"
            "\\label{tab:fiat}\n\\setlength{\\tabcolsep}{2.5pt}\n\\begin{tabular}{@{}llrrr@{}}\n\\toprule\n"
            "Fiat & $X$ & Before & Four weeks after & Later \\\\\n\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")


def decomposition_table() -> str:
    dec = _load(DECOMP)["windows"]
    rows = []
    for key, label in (("token_failure_svb", "USDC, 2023-03-10 to 03-13"), ("ledger_failure_binanceus", "USDT, 2023-06-22 to 07-31")):
        s = dec[key]["summary"]
        rows.append(f"{label} & {s['hours']:,} & {_f(s['median_D'])} & {_f(s['median_L'])} & {_f(s['median_T'])} & "
                    f"{_f(s['median_D_ref'])} & {100 * s['median_ledger_share']:.0f} \\\\")
    return ("% generated by www_paper.rescue_macros; do not edit\n\\begin{table}[t]\n\\small\n"
            "\\caption{Decomposition on Binance.US (hourly medians, bps; hours with all legs traded). $D$: observed; $L$: "
            "ledger component (via BTC); $T=D-L$: token component; $D^r$: the token's direct price on Bitstamp; "
            "$L$ share: median $|L|/(|L|+|T|)$ in \\%.}\n\\label{tab:decomp}\n\\setlength{\\tabcolsep}{2.5pt}\n"
            "\\begin{tabular}{@{}lrrrrrr@{}}\n\\toprule\nCase & Hours & $D$ & $L$ & $T$ & $D^r$ & $L$ share \\\\\n\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")


def sensitivity_table() -> str:
    rows = []
    for r in _load(MONITOR)["sensitivity"]:
        rows.append(f"{r['threshold_bps']:.0f} & {r['agreement']:.2f} & {100 * r['binanceus_rail_cut_ledger_flag']:.1f} & "
                    f"{100 * r['calm_ledger_flag']:.1f} & {100 * r['svb_run_ledger_flag']:.1f} & "
                    f"{100 * r['ftx_collapse_ledger_flag']:.1f} & {100 * r['svb_run_token_flag_USDC']:.1f} \\\\")
    return ("% generated by www_paper.rescue_macros; do not edit\n\\begin{table}[t]\n\\small\n"
            "\\caption{Monitor sensitivity: share of hours (\\%) flagged under each severity threshold (bps) and "
            "agreement tolerance. The headline rule is the middle row.}\n\\label{tab:sensitivity}\n"
            "\\setlength{\\tabcolsep}{3pt}\n\\begin{tabular}{@{}rrrrrrr@{}}\n\\toprule\n"
            "Thr. & Agr. & Rail cut & Calm & SVB & FTX & SVB USDC \\\\\n"
            " & & ledger & ledger & ledger & ledger & token \\\\\n\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")


def panel_macros() -> list[tuple[str, str, str]]:
    """Bitfinex ledger panel (reports/rescue/ledger_panel.json)."""
    eps = _load(PANEL)["episodes"]
    short = {"L2017-04-BITFINEX-WIRES": "Seventeen", "L2018-10-BITFINEX-FIAT": "Eighteen", "L2019-04-BITFINEX-NYAG": "Nineteen"}
    m: list[tuple[str, str, str]] = []
    for eid, tag in short.items():
        d = eps[eid]["descriptive"]
        m += [(f"NumPan{tag}Max", _f(d["max_daily_pd_btc"], 0), f"{eid}/max daily PD_BTC"),
              (f"NumPan{tag}Min", _f(d["min_daily_pd_btc"], 0), f"{eid}/min daily PD_BTC")]
    same = [e["descriptive"]["btc_vs_eth_same_reference_coinbase"] for e in eps.values()]
    tri = [abs(r["median_bps"]) for e in eps.values() for r in e["triangle"]
           if r["phase"] not in ("pre", "later") and r.get("minutes")]
    m += [("NumPanCorrMin", f"{min(s['corr_hourly'] for s in same):.3f}", "panel/min hourly corr BTC vs ETH, same reference"),
          ("NumPanGapMax", _f(max(abs(s["median_gap_bps"]) for s in same)), "panel/max |median gap| BTC vs ETH, same reference"),
          ("NumPanTriMax", _f(max(tri), 0), "panel/max |stress-phase triangle median|"),
          ("NumPanSeventeenMinAbs", _f(abs(eps["L2017-04-BITFINEX-WIRES"]["descriptive"]["min_daily_pd_btc"]), 0),
           "absolute value of NumPanSeventeenMin")]
    return m


def main() -> None:
    for path, text in ((NUMBERS, numbers()), (PHASE_TABLE, phase_table()), (FIAT_TABLE, fiat_table()),
                       (DECOMP_TABLE, decomposition_table()), (MONITOR_TABLE, monitor_table()),
                       (SENS_TABLE, sensitivity_table())):
        path.write_text(text)
        print(f"WROTE {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
