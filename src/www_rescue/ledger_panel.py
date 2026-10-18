"""Ledger-side multi-event panel: Bitfinex USD 2017, 2018 and 2019 (plan: docs/review/LEDGER_PANEL_PLAN.md).

For each episode, with Bitfinex as the platform venue (v):
  PD_BTC  = 1e4 [log P_v(BTC/USD_v) - log P_Bitstamp(BTC/USD)]   (the ledger component L; BTC has no peg)
  PD_BTC2 = same against Coinbase                                  (second reference)
  PD_ETH  = 1e4 [log P_v(ETH/USD_v) - log P_Coinbase(ETH/USD)]     (an unrelated asset; identification)
  TRI     = 1e4 [log P_v(ETH/USD) - log P_v(ETH/BTC) - log P_v(BTC/USD)]   (within-venue coherence)
  D_USDT  = 1e4 log P_v(USDT/USD_v), T_USDT = D_USDT - PD_BTC     (2019 only; Bitfinex lists USDT/USD from late 2018)
Only minutes traded on every leg a quantity needs are used. Phase boundaries are documented dates fixed here
before any phase statistic was computed (2026-10-18); sources are listed in the plan.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from www_events.candles import load_venue_months

from .platform_dollar import dislocation, identification, phase_table, traded_log_close

EPISODES: dict[str, dict[str, Any]] = {
    "L2017-04-BITFINEX-WIRES": {
        "months": ["2017-02", "2017-03", "2017-04", "2017-05", "2017-06", "2017-07", "2017-08"],
        "gate": "exit impaired (outbound wires), then entry closed too (inbound wires refused from 2017-04-18)",
        "phases": [
            ("pre", "2017-02-01", "2017-04-01", "baseline"),
            ("outbound_wires_blocked", "2017-04-01", "2017-04-18",
             "Wells Fargo blocks outbound wires from Bitfinex's Taiwanese banks; Bitfinex sues, first week of April"),
            ("inbound_wires_refused", "2017-04-18", "2017-06-01", "Taiwanese banks refuse all incoming wires (2017-04-18)"),
            ("later", "2017-06-01", "2017-09-01", "no documented restoration date; descriptive"),
        ],
        "usdt": False,
    },
    "L2018-10-BITFINEX-FIAT": {
        "months": ["2018-09", "2018-10", "2018-11", "2018-12"],
        "gate": "entry closed (fiat deposits paused), exit officially open; NYAG later alleged serious withdrawal problems in late 2018",
        "phases": [
            ("pre", "2018-09-01", "2018-10-11", "baseline"),
            ("deposits_paused", "2018-10-11", "2018-11-01", "all fiat deposits paused, reported 2018-10-11, confirmed 2018-10-12"),
            ("later", "2018-11-01", "2019-01-01", "no documented restoration date; descriptive"),
        ],
        "usdt": False,
    },
    "L2019-04-BITFINEX-NYAG": {
        "months": ["2019-03", "2019-04", "2019-05", "2019-06", "2019-07"],
        "gate": "exit threatened (NYAG: Crypto Capital lost or seized about $850M of Bitfinex funds)",
        "phases": [
            ("pre", "2019-03-01", "2019-04-25", "baseline"),
            ("nyag_filing", "2019-04-25", "2019-06-01", "NYAG court filing against Bitfinex and Tether (2019-04-25)"),
            ("later", "2019-06-01", "2019-08-01", "no documented restoration date; descriptive"),
        ],
        "usdt": True,
    },
}


def series(root: Path, manifest: Path, venue: str, pair: str, months: list[str]) -> pd.Series:
    grid, _ = load_venue_months(root / venue, pair, "x", manifest, venue, months)
    return traded_log_close(grid, "x")


def episode(raw: Path, manifest: Path, spec: dict[str, Any]) -> dict[str, Any]:
    ms = spec["months"]
    bfx = {p: series(raw, manifest, "bitfinex", p, ms) for p in ["BTCUSD", "ETHUSD", "ETHBTC"]}
    bst_btc = series(raw, manifest, "bitstamp", "BTCUSD", ms)
    cb_btc = series(raw, manifest, "coinbase", "BTCUSD", ms)
    cb_eth = series(raw, manifest, "coinbase", "ETHUSD", ms)
    pd_btc = dislocation(bfx["BTCUSD"], bst_btc)
    pd_btc2 = dislocation(bfx["BTCUSD"], cb_btc)
    pd_eth = dislocation(bfx["ETHUSD"], cb_eth)
    implied = pd.concat([bfx["ETHBTC"], bfx["BTCUSD"]], axis=1, join="inner").dropna().sum(axis=1)
    tri = dislocation(bfx["ETHUSD"], implied)
    phases = spec["phases"]
    out: dict[str, Any] = {
        "gate": spec["gate"],
        "pd_btc": phase_table(pd_btc, phases), "pd_btc_coinbase": phase_table(pd_btc2, phases),
        "pd_eth": phase_table(pd_eth, phases), "triangle": phase_table(tri, phases),
        "identification_btc_eth": {}, "references_btc": {},
    }
    for name, start, end, _ in phases:
        lo, hi = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
        cut = lambda s: s[(s.index >= lo) & (s.index < hi)]  # noqa: E731
        out["identification_btc_eth"][name] = identification(cut(pd_btc), cut(pd_eth))
        out["references_btc"][name] = identification(cut(pd_btc), cut(pd_btc2))
    daily = pd_btc.resample("1D").median().dropna()
    same_ref = identification(pd_btc2, pd_eth)
    out["descriptive"] = {  # added after the phase results were seen; descriptive, not scored
        "note": "daily path and same-reference agreement, computed after the fixed-phase results",
        "max_daily_pd_btc": float(daily.max()), "max_daily_date": str(daily.idxmax().date()),
        "min_daily_pd_btc": float(daily.min()), "min_daily_date": str(daily.idxmin().date()),
        "days_pd_btc_ge_100": int((daily >= 100).sum()), "days_pd_btc_le_minus_100": int((daily <= -100).sum()),
        "btc_vs_eth_same_reference_coinbase": same_ref,
    }
    if spec["usdt"]:
        d_usdt = 1e4 * series(raw, manifest, "bitfinex", "USTUSD", ms)
        t_usdt = (pd.concat([d_usdt, pd_btc], axis=1, join="inner").dropna()
                  .pipe(lambda f: f.iloc[:, 0] - f.iloc[:, 1]))
        out["d_usdt"] = phase_table(d_usdt, phases)
        out["t_usdt"] = phase_table(t_usdt, phases)
    return out


def predictions(result: dict[str, Any]) -> dict[str, Any]:
    """Score Q1 to Q4 of the plan on the stress phases (every phase except pre and later)."""
    scored: dict[str, Any] = {}
    for eid, ep in result.items():
        stress = [r["phase"] for r in ep["pd_btc"] if r["phase"] not in ("pre", "later") and r.get("minutes")]
        med = {t: {r["phase"]: r.get("median_bps") for r in ep[t]} for t in ("pd_btc", "pd_eth", "triangle")}
        q1 = all((ep["identification_btc_eth"][p].get("corr_hourly") or 0) >= 0.9
                 and abs(med["pd_btc"][p] - med["pd_eth"][p]) <= 50 for p in stress)
        q2 = all(abs(med["triangle"][p]) <= 10 for p in stress)
        q3 = all(med["pd_btc"][p] > 0 for p in stress)
        falsified = any((ep["identification_btc_eth"][p].get("corr_hourly") or 0) < 0.5
                        or med["pd_btc"][p] * med["pd_eth"][p] < 0 for p in stress)
        later = med["pd_btc"].get("later")
        q4 = None if later is None else abs(later - med["pd_btc"]["pre"]) <= 50
        scored[eid] = {"stress_phases": stress, "Q1_identification": q1, "Q2_triangle": q2,
                       "Q3_discount_sign": q3, "Q4_reversion": q4, "falsified": falsified}
    return scored


def run(raw: Path, manifest: Path) -> dict[str, Any]:
    result = {eid: episode(raw, manifest, spec) for eid, spec in EPISODES.items()}
    return {"episodes": result, "predictions": predictions(result)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--manifest", type=Path, default=Path("reports/events/acquisition_manifest_ledger.json"))
    parser.add_argument("--out", type=Path, default=Path("reports/rescue/ledger_panel.json"))
    args = parser.parse_args()
    out = run(args.raw, args.manifest)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["predictions"], indent=1))


if __name__ == "__main__":
    main()
