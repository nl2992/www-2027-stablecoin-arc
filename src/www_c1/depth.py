"""Depth metrics from replayed normalized L2 books (spec v3, Phase 2 CEX metrics).

Uses the C1 replay rules unchanged and samples the reconstructed book at fixed
clock intervals. These are measurements of the supplied normalized stream; they
inherit its sequence-continuity limitation. Normal-market samples must never be
used as substitutes for missing crisis-period depth.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np

from .reader import iter_local_timestamp_groups
from .replay import BookReplayer, timestamp_iso

BANDS_BPS = (10, 50, 100)


def book_metrics(bids: dict[Decimal, Decimal], asks: dict[Decimal, Decimal]) -> dict[str, Any] | None:
    if not bids or not asks:
        return None
    best_bid, best_ask = max(bids), min(asks)
    mid = (best_bid + best_ask) / 2
    out: dict[str, Any] = {"best_bid": float(best_bid), "best_ask": float(best_ask),
                           "spread_bps": float((best_ask - best_bid) / mid * 10_000), "crossed": best_bid >= best_ask}
    for band in BANDS_BPS:
        lo, hi = mid * (1 - Decimal(band) / 10_000), mid * (1 + Decimal(band) / 10_000)
        bid_depth = sum(p * q for p, q in bids.items() if p >= lo)
        ask_depth = sum(p * q for p, q in asks.items() if p <= hi)
        out[f"bid_depth_quote_{band}bps"] = float(bid_depth)
        out[f"ask_depth_quote_{band}bps"] = float(ask_depth)
        total = bid_depth + ask_depth
        out[f"imbalance_{band}bps"] = float((bid_depth - ask_depth) / total) if total else None
    return out


def depth_profile(path: Path, *, sample_minutes: int = 5) -> dict[str, Any]:
    replayer = BookReplayer()
    replayer._previous_exchange_timestamp = None
    replayer._previous_local_timestamp = None
    step = sample_minutes * 60_000_000
    next_sample, samples = None, []
    for group in iter_local_timestamp_groups(path):
        replayer.process_group(group)
        t = group[-1].local_timestamp
        if next_sample is None:
            next_sample = (t // step + 1) * step
        while t >= next_sample:
            if replayer.initialized:
                m = book_metrics(replayer.book.bids, replayer.book.asks)
                if m:
                    samples.append({"t": timestamp_iso(next_sample), **m})
            next_sample += step
    summary: dict[str, Any] = {"samples": len(samples), "sample_minutes": sample_minutes}
    if samples:
        for key in ["spread_bps"] + [f"{s}_depth_quote_{b}bps" for b in BANDS_BPS for s in ("bid", "ask")]:
            vals = np.array([s[key] for s in samples], dtype=float)
            summary[key] = {"median": float(np.median(vals)), "p10": float(np.percentile(vals, 10)),
                            "p90": float(np.percentile(vals, 90))}
        summary["crossed_samples"] = sum(s["crossed"] for s in samples)
    return {"summary": summary, "replay_counters": dict(replayer.counters)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, default=Path("reports/c1/normal_market_depth.json"))
    args = parser.parse_args()
    out = {"label": "NORMAL-MARKET first-of-month samples; not crisis-period depth", "files": []}
    for p in args.inputs:
        prof = depth_profile(p)
        out["files"].append({"file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), **prof})
        s = prof["summary"]
        print(p.name, s.get("samples"), "spread median", s.get("spread_bps", {}).get("median"))
    args.output.write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
