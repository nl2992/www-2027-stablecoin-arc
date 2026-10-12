"""Apply rule R1 to a stablecoin/USD minute series from an audited local panel."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from www_c0.quality import validate_utc_minutes
from www_c3.cli import sha256

from .registry import RULES, r1_severity


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--prefix", required=True, help="e.g. bnus_usdcusd (must be a stablecoin/USD pair)")
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    panel = pd.read_parquet(args.panel)
    times = validate_utc_minutes(panel["timestamp_utc"])
    result = r1_severity(times, panel[f"{args.prefix}_close"].to_numpy(), panel[f"{args.prefix}_volume"].to_numpy())
    result.update({
        "event_id": args.event_id,
        "series": args.prefix,
        "input_sha256": sha256(args.panel),
        "panel_first_utc": times[0].isoformat(),
        "panel_last_utc": times[-1].isoformat(),
        "rules": RULES["R1_severity"],
        "caveat": "Single venue last-trade closes; measures observed traded deviation, not executable quotes.",
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in ("r1_pass", "max_breach_minutes_in_window", "extreme_deviation_bps",
                                              "first_breach_utc", "last_breach_utc")}))


if __name__ == "__main__":
    main()
