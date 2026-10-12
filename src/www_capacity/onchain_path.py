"""Sample on-chain capacity along each event's windows (definition: docs/c6_onchain_capacity.md).

Read-only archive calls via the user's key (WWW_ETH_RPC_URL or git-ignored .env; never written out).
Only swap-validated pools are included (reports/c2/archive_checks.json).
"""

from __future__ import annotations

import argparse
import json
import urllib.parse
from pathlib import Path
from statistics import median
from typing import Any

import pandas as pd

from www_c2.archive_run import Budgeted, StopRun, block_at_or_before, endpoint_from_env
from www_c2.rpc import rpc_call
from www_c2.validation_plan import calldata
from www_events.registry import _parse_date, analysis_windows, load_registry

from .onchain import PoolState, capacity_table

THREEPOOL = "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"
MERGE_BLOCK = 15_537_394
ITEMS = [  # (event, pool address, n coins, stressed index, counterpart indices, metapool)
    ("E2023-03-USDC-SVB", THREEPOOL, 3, 1, (0, 2), False),
    ("N2023-06-USDT-3POOL", THREEPOOL, 3, 2, (0, 1), False),
    ("E2022-05-UST-COLLAPSE", "0xCEAF7747579696A2F0bb206a14210e3c9e6fB269", 2, 0, (1,), True),
]
SIX_HOURS = 6 * 3600


def _u(x: str) -> int:
    return int(x, 16)


def read_state(call, pool: str, n: int, block: int, decimals: list[int], metapool: bool) -> PoolState:
    tag = hex(block)
    eth = lambda sig, *a, to=pool: _u(call("eth_call", [{"to": to, "data": calldata(sig, *a)}, tag]))
    balances = [eth("balances(uint256)", i) for i in range(n)]
    rates = [10 ** (36 - d) for d in decimals]
    usd = [1.0] * n
    if metapool:
        vp = eth("get_virtual_price()", to=THREEPOOL)
        rates[1], usd[1] = vp, vp / 1e18
    return PoolState(balances, rates, decimals, eth("A()"), eth("fee()"), usd)


def sample_window(call, pool, n, s, cps, metapool, decimals, window, latest) -> list[dict[str, Any]]:
    start = int(pd.Timestamp(window["start"], tz="UTC").timestamp())
    end = int((pd.Timestamp(window["end"], tz="UTC") + pd.Timedelta("1D")).timestamp())
    blk = block_at_or_before(call, start, latest)["number"] + 1
    out = []
    while True:
        header = call("eth_getBlockByNumber", [hex(blk), False])
        ts = _u(header["timestamp"])
        if ts >= end:
            break
        st = read_state(call, pool, n, blk, decimals, metapool)
        total_usd = sum(b / 10 ** d * u for b, d, u in zip(st.balances, decimals, st.usd_per_token))
        out.append({"block": blk, "timestamp_utc": pd.Timestamp(ts, unit="s", tz="UTC").isoformat(),
                    "A": st.amp, "fee": st.fee, "share_of_stressed_coin":
                    (st.balances[s] / 10 ** decimals[s] * st.usd_per_token[s]) / total_usd,
                    "pool_usd": total_usd, "capacity": capacity_table(st, s, cps)})
        blk += SIX_HOURS // (12 if blk >= MERGE_BLOCK else 13)  # ~6h: 1,800 post-Merge / ~1,660 pre-Merge
    return out


def summarize(samples: list[dict[str, Any]]) -> dict[str, Any]:
    if not samples:
        return {"samples": 0}
    keys = samples[0]["capacity"].keys()
    out: dict[str, Any] = {"samples": len(samples),
                           "share_of_stressed_coin_median": median(x["share_of_stressed_coin"] for x in samples)}
    for k in keys:
        for m in ("absorption", "restoration"):
            vals = sorted(x["capacity"][k][m] for x in samples)
            out[f"{k}_{m}"] = {"median": median(vals), "min": vals[0], "p10": vals[max(0, int(0.1 * len(vals)) - 1)]}
    return out


def run(call, registry) -> dict[str, Any]:
    events = {e["id"]: e for e in registry}
    latest = _u(call("eth_blockNumber", []))
    results = []
    for eid, pool, n, s, cps, metapool in ITEMS:
        e = events[eid]
        windows = analysis_windows(_parse_date(e["reported_window_utc"]["start"]),
                                   _parse_date(e["reported_window_utc"]["end"]))
        coins = [call("eth_call", [{"to": pool, "data": calldata("coins(uint256)", i)}, "latest"]) for i in range(n)]
        decimals = [_u(call("eth_call", [{"to": "0x" + c[-40:], "data": calldata("decimals()")}, "latest"]))
                    for c in coins]
        per_window = {name: sample_window(call, pool, n, s, cps, metapool, decimals, w, latest)
                      for name, w in windows.items()}
        summary = {name: summarize(v) for name, v in per_window.items()}
        ratios = {}
        for k in (per_window["event"][0]["capacity"].keys() if per_window["event"] else []):
            base = summary["baseline"].get(f"{k}_absorption", {}).get("median")
            ev = summary["event"].get(f"{k}_absorption", {}).get("median")
            ratios[k] = (ev / base) if base else None
        results.append({"event_id": eid, "pool": pool, "stressed_index": s, "counterparts": list(cps),
                        "decimals": decimals, "windows": windows, "summary": summary,
                        "event_over_baseline_absorption_median": ratios, "samples": per_window})
    return {"definition": "docs/c6_onchain_capacity.md", "scope": "ON-CHAIN ONLY; not CEX-DEX restoration capacity",
            "deltas_bps": [10, 50, 100], "results": results}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reports/c6/onchain_capacity.json"))
    parser.add_argument("--budget", type=int, default=3000)
    parser.add_argument("--spacing", type=float, default=0.1)
    args = parser.parse_args()
    endpoint = endpoint_from_env()
    if not endpoint:
        raise SystemExit("WWW_ETH_RPC_URL not set (shell or git-ignored .env)")
    rpc = Budgeted(lambda m, p: rpc_call(endpoint, m, p), args.budget, args.spacing)
    try:
        out = run(rpc, load_registry(Path("configs/event_registry.json")))
        out["status"] = "COMPLETED"
    except StopRun as exc:
        out = {"status": "STOPPED", "stop_reason": str(exc)}
    out.update(provider_host=urllib.parse.urlparse(endpoint).hostname, calls_used=rpc.used,
               measured_utc=pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%MZ"))
    text = json.dumps(out, indent=1)
    if endpoint in text:
        raise SystemExit("refusing to write output containing the endpoint")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text + "\n")
    print(out["status"], "calls", rpc.used)


if __name__ == "__main__":
    main()
