"""C6 robustness: re-solve SVB on-chain capacity with counterparts valued at observed exchange prices.

Uses the pool state stored per sample in reports/c6/onchain_capacity.json and Binance.US minute
closes (checksum-verified archives). The counterpart value is the last traded close at or before
the sample within 60 minutes; otherwise par is used and the sample is flagged. The stressed coin
stays at par (definition). No chain calls are made.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median
from typing import Any

import pandas as pd

from www_events.runner import load_binance_months

from .onchain import PoolState, capacity_table

EVENT = "E2023-03-USDC-SVB"
COUNTERPART_SYMBOL = {0: "DAIUSD", 2: "USDTUSD"}  # 3pool coin index -> Binance.US USD pair
STALE = pd.Timedelta("60min")


def price_lookup(directory: Path, symbol: str):
    grid, _ = load_binance_months(directory, symbol, "x")
    traded = grid[grid["x_traded"].astype("boolean").fillna(False).astype(bool)]["x_close"]

    def at(ts: pd.Timestamp) -> float | None:
        prior = traded[traded.index <= ts]
        if prior.empty or ts - prior.index[-1] > STALE:
            return None
        return float(prior.iloc[-1])
    return at


def revalue(result: dict[str, Any], lookups: dict[int, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for window, samples in result["samples"].items():
        rows = []
        for smp in samples:
            ts = pd.Timestamp(smp["timestamp_utc"])
            usd = list(smp["usd_per_token"])
            flags = {}
            for c, look in lookups.items():
                p = look(ts)
                flags[str(c)] = "observed" if p is not None else "par_fallback"
                usd[c] = p if p is not None else 1.0
            st = PoolState([int(b) for b in smp["balances"]], [int(r) for r in smp["rates"]], result["decimals"],
                           smp["A"], smp["fee"], usd)
            rows.append({"timestamp_utc": smp["timestamp_utc"], "valuation": usd, "flags": flags,
                         "capacity": capacity_table(st, result["stressed_index"], result["counterparts"])})
        out[window] = rows
    return out


def summarize(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    vals = [r["capacity"][key]["absorption"] for r in rows]
    return {"samples": len(vals), "absorption_median": median(vals) if vals else None,
            "par_fallbacks": sum(v == "par_fallback" for r in rows for v in r["flags"].values())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/c6/onchain_capacity.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/c6/onchain_capacity_cex_valued.json"))
    parser.add_argument("--binance-us", type=Path, default=Path("data/raw/binance_us"))
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    res = next(r for r in data["results"] if r["event_id"] == EVENT)
    lookups = {c: price_lookup(args.binance_us, sym) for c, sym in COUNTERPART_SYMBOL.items()}
    rows = revalue(res, lookups)
    summary = {}
    for c in res["counterparts"]:
        key = f"c{c}_50bps"
        summary[key] = {w: summarize(v, key) | {"par_valued_median": res["summary"][w].get(f"{key}_absorption", {}).get("median")}
                        for w, v in rows.items()}
    out = {"event_id": EVENT, "valuation": "counterparts at last traded Binance.US USD close within 60 min; s at par",
           "summary_50bps": summary, "samples": rows}
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    for key, per in summary.items():
        print(key, {w: (round((v["par_valued_median"] or 0) / 1e6, 1), round((v["absorption_median"] or 0) / 1e6, 1),
                        v["par_fallbacks"]) for w, v in per.items()})


if __name__ == "__main__":
    main()
