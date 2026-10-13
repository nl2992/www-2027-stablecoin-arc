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
DECOMP = ROOT / "reports/rescue/decomposition.json"
PLATFORM = ROOT / "reports/rescue/platform_dollar.json"
FIAT = ROOT / "reports/rescue/fiat_rail.json"
LEDGER = ROOT / "docs/review/RESCUE_SEARCH.md"

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
    signed = {name: value for name, value, _ in m}
    for name in ("NumPdUsdtTrans", "NumPdBtcTrans", "NumPdUsdcTrans", "NumPdUsdtWorstDay", "NumFiatEurUsdtChange", "NumFiatEurBtcChange"):
        m.append((name + "Abs", signed[name].lstrip("-"), f"absolute value of {name}"))
    tried, discarded = directions_tried()
    m += [("NumDirectionsTried", str(tried), "RESCUE_SEARCH.md ledger rows"),
          ("NumDirectionsDiscarded", str(discarded), "RESCUE_SEARCH.md ledger rows marked DISCARD")]
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
    cols = [{r["phase"]: r for r in plat[k]} for k in ("pd_usdt", "pd_btc", "pd_usdc", "within_venue_triangle")]
    ident = plat["identification_usdt_vs_btc"]
    rows = []
    for ph in plat["phases"]:
        n = ph["phase"]
        corr = ident[n].get("corr_hourly")
        cells = " & ".join(_ci(c[n]) for c in cols[:2])
        rest = " & ".join(_f(c[n]["median_bps"]) if c[n].get("minutes") else "--" for c in cols[2:])
        rows.append(f"{PHASE_LABEL[n]} & {ph['start']} & {cells} & {rest} & {'--' if corr is None else f'{corr:.2f}'} \\\\")
    return ("% generated by www_paper.rescue_macros; do not edit\n\\begin{table*}[t]\n\\small\n"
            "\\caption{Binance.US dollar versus Bitstamp dollar by documented rail phase. $PD_X$: median platform-dollar "
            "dislocation of asset $X$ in bps (hour-block bootstrap 95\\% intervals for USDT and BTC); $W$: median "
            "within-venue triangle; corr: hourly correlation of $PD_{\\mathrm{USDT}}$ and $PD_{\\mathrm{BTC}}$. Binance.US "
            "BTC/USD and USDC/USD did not trade while the rail was impaired.}\n"
            "\\label{tab:phases}\n\\begin{tabular}{@{}llrrrrr@{}}\n\\toprule\n"
            "Phase & From & $PD_{\\mathrm{USDT}}$ & $PD_{\\mathrm{BTC}}$ & $PD_{\\mathrm{USDC}}$ & $W$ & corr \\\\\n\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n\\end{table*}\n")


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


def main() -> None:
    for path, text in ((NUMBERS, numbers()), (PHASE_TABLE, phase_table()), (FIAT_TABLE, fiat_table()),
                       (DECOMP_TABLE, decomposition_table())):
        path.write_text(text)
        print(f"WROTE {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
