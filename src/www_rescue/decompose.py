"""Which dollar broke? Token versus platform-ledger decomposition on one venue (Binance.US), two failures.

For stablecoin q on venue v:  D_q = 1e4 log P_v(q/USD_v)  (the observed dollar dislocation),
ledger component           L   = 1e4 [log P_v(BTC/USD_v) - log P_ref(BTC/USD)]   (= PD_BTC; BTC has no peg),
token component            T_q = D_q - L   (q's price in external dollars implied through BTC).
Check: T_q should match q's direct price on the reference venue, D_q^ref = 1e4 log P_ref(q/USD).
Reference venue: Bitstamp (USD rails open throughout). Windows are documented dates, fixed in WINDOWS.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from www_events.bitstamp import load_months
from www_events.runner import load_binance_months

from .platform_dollar import traded_log_close

WINDOWS = {
    "token_failure_svb": {"coin": "USDC", "start": "2023-03-10", "end": "2023-03-14",
                          "label": "USDC/SVB (registry reported window 2023-03-10 to 2023-03-13, inclusive)"},
    "ledger_failure_binanceus": {"coin": "USDT", "start": "2023-06-22", "end": "2023-08-01",
                                 "label": "Binance.US crypto-only transition (deposits closed, withdrawals open)"},
}


def components(d_q: pd.Series, venue_btc: pd.Series, ref_btc: pd.Series, ref_q: pd.Series) -> pd.DataFrame:
    """Hourly medians of D_q, L, T_q and D_q^ref (each from minutes traded on the legs it needs)."""
    ledger = 1e4 * pd.concat([venue_btc, ref_btc], axis=1, join="inner").dropna().pipe(lambda f: f.iloc[:, 0] - f.iloc[:, 1])
    d = 1e4 * d_q
    token = pd.concat([d, ledger], axis=1, join="inner").dropna().pipe(lambda f: f.iloc[:, 0] - f.iloc[:, 1])
    return pd.DataFrame({"D": d.resample("1h").median(), "L": ledger.resample("1h").median(),
                         "T": token.resample("1h").median(), "D_ref": (1e4 * ref_q).resample("1h").median()})


def summarize(h: pd.DataFrame) -> dict[str, Any]:
    h = h.dropna()
    if h.empty:
        return {"hours": 0}
    share = float((h["L"].abs() / (h["L"].abs() + h["T"].abs())).median())
    return {"hours": int(len(h)), "median_D": float(h["D"].median()), "median_L": float(h["L"].median()),
            "median_T": float(h["T"].median()), "median_D_ref": float(h["D_ref"].median()),
            "median_abs_T_minus_D_ref": float((h["T"] - h["D_ref"]).abs().median()),
            "median_ledger_share": share,
            "extreme_D": float(h["D"].loc[h["D"].abs().idxmax()])}


def run(binance_us: Path, bitstamp: Path, manifest: Path) -> dict[str, Any]:
    def bus(sym: str) -> pd.Series:
        return traded_log_close(load_binance_months(binance_us, sym, "x")[0], "x")

    def bst(pair: str) -> pd.Series:
        return traded_log_close(load_months(bitstamp, pair, "y", manifest)[0], "y")

    venue_btc, ref_btc = bus("BTCUSD"), bst("BTCUSD")
    out: dict[str, Any] = {"definition": __doc__.strip().splitlines()[0], "windows": {}}
    for name, w in WINDOWS.items():
        h = components(bus(f"{w['coin']}USD"), venue_btc, ref_btc, bst(f"{w['coin']}USD"))
        h = h[(h.index >= pd.Timestamp(w["start"], tz="UTC")) & (h.index < pd.Timestamp(w["end"], tz="UTC"))]
        out["windows"][name] = {**w, "summary": summarize(h),
                                "hourly": {str(k): [None if np.isnan(v) else round(float(v), 2) for v in row]
                                           for k, row in zip(h.index, h[["D", "L", "T", "D_ref"]].to_numpy())}}
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binance-us", type=Path, default=Path("data/raw/binance_us"))
    parser.add_argument("--bitstamp", type=Path, default=Path("data/raw/bitstamp"))
    parser.add_argument("--manifest", type=Path, default=Path("reports/events/acquisition_manifest.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/rescue/decomposition.json"))
    args = parser.parse_args()
    out = run(args.binance_us, args.bitstamp, args.manifest)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    for name, w in out["windows"].items():
        print(name, {k: round(v, 2) if isinstance(v, float) else v for k, v in w["summary"].items()})


if __name__ == "__main__":
    main()
