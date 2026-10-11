"""Offline, block-pinned validation plan for source-documented pools.

Builds the exact read-only JSON-RPC requests (eth_getCode, eth_call) that would
verify each pool's identity and state at an event's target block, plus the block
search that maps a UTC timestamp to a block. Nothing here touches the network:
``dry_run`` only constructs and checks requests. Executing them needs an
authorized archive endpoint (see ``www_c2.rpc``).

ABI signatures are assumed from the protocols' published source patterns and are
marked ``ASSUMED``; each must be confirmed against verified source before use.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# --- Keccak-256 (Ethereum's pre-standard SHA-3 padding) ------------------------------------------

_RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000, 0x000000000000808B,
    0x0000000080000001, 0x8000000080008081, 0x8000000000008009, 0x000000000000008A, 0x0000000000000088,
    0x0000000080008009, 0x000000008000000A, 0x000000008000808B, 0x800000000000008B, 0x8000000000008089,
    0x8000000000008003, 0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]
_ROT = [[0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61], [28, 55, 25, 21, 56], [27, 20, 39, 8, 14]]
_MASK = (1 << 64) - 1


def _rol(x: int, n: int) -> int:
    return ((x << n) | (x >> (64 - n))) & _MASK if n else x


def _keccak_f(a: list[list[int]]) -> None:
    for rc in _RC:
        c = [a[x][0] ^ a[x][1] ^ a[x][2] ^ a[x][3] ^ a[x][4] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rol(c[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                a[x][y] ^= d[x]
        b = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                b[y][(2 * x + 3 * y) % 5] = _rol(a[x][y], _ROT[x][y])
        for x in range(5):
            for y in range(5):
                a[x][y] = b[x][y] ^ ((~b[(x + 1) % 5][y]) & b[(x + 2) % 5][y])
        a[0][0] ^= rc


def keccak256(data: bytes) -> bytes:
    rate = 136
    padded = bytearray(data) + b"\x01" + b"\x00" * ((rate - (len(data) + 1) % rate) % rate)
    padded[-1] |= 0x80
    state = [[0] * 5 for _ in range(5)]
    for offset in range(0, len(padded), rate):
        block = padded[offset:offset + rate]
        for i in range(rate // 8):
            state[i % 5][i // 5] ^= int.from_bytes(block[8 * i:8 * i + 8], "little")
        _keccak_f(state)
    out = b"".join(state[i % 5][i // 5].to_bytes(8, "little") for i in range(25))
    return out[:32]


def selector(signature: str) -> str:
    return "0x" + keccak256(signature.encode()).hex()[:8]


def encode_word(value: int, *, signed: bool = False) -> str:
    if not signed and value < 0:
        raise ValueError("negative value for unsigned type")
    return (value % (1 << 256)).to_bytes(32, "big").hex()


def calldata(signature: str, *args: int) -> str:
    types = signature[signature.index("(") + 1:-1].split(",") if "()" not in signature else []
    if len(types) != len(args):
        raise ValueError(f"{signature} expects {len(types)} arguments")
    return selector(signature) + "".join(encode_word(a, signed=t.startswith("int")) for t, a in zip(types, args))


# --- Call sets per pool interface -----------------------------------------------------------------

def curve_stableswap_calls(n_coins: int) -> list[dict[str, Any]]:
    """Identity and state reads for a Curve StableSwap pool (signatures ASSUMED from published source)."""
    calls = [{"purpose": "amplification", "signature": "A()", "args": []},
             {"purpose": "fee (1e10 units)", "signature": "fee()", "args": []}]
    for i in range(n_coins):
        calls.append({"purpose": f"coin {i} address", "signature": "coins(uint256)", "args": [i]})
        calls.append({"purpose": f"coin {i} balance", "signature": "balances(uint256)", "args": [i]})
    calls.append({"purpose": "quote 10**6 raw units of coin 0 -> coin 1 (1 token only if coin 0 has 6 decimals; "
                             "read decimals from coins(i) before interpreting)",
                  "signature": "get_dy(int128,int128,uint256)", "args": [0, 1, 10**6]})
    return calls


INTERFACES = {"curve_stableswap_3": lambda: curve_stableswap_calls(3),
              "curve_metapool_2": lambda: curve_stableswap_calls(2)}


def requests_for(address: str, block_tag: str, calls: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if len(address) != 42 or not address.startswith("0x"):
        raise ValueError("address must be 20-byte hex")
    out = [{"method": "eth_getCode", "params": [address, block_tag], "purpose": "bytecode identity at block"}]
    for c in calls:
        out.append({"method": "eth_call", "purpose": c["purpose"], "signature": c["signature"],
                    "abi_status": "ASSUMED",
                    "params": [{"to": address, "data": calldata(c["signature"], *c["args"])}, block_tag]})
    return out


# --- Timestamp -> block ---------------------------------------------------------------------------

def block_at_or_before(target_ts: int, block_timestamp: Callable[[int], int], lo: int, hi: int) -> int:
    """Largest block number in [lo, hi] whose timestamp <= target_ts (timestamps are non-decreasing)."""
    if block_timestamp(lo) > target_ts:
        raise ValueError("target precedes the search range")
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if block_timestamp(mid) <= target_ts:
            lo = mid
        else:
            hi = mid - 1
    return lo


# --- Plan -----------------------------------------------------------------------------------------

POOL_INTERFACE = {
    "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7": "curve_stableswap_3",
    "0xCEAF7747579696A2F0bb206a14210e3c9e6fB269": "curve_metapool_2",
    "0x890f4e345B1dAED0367A877a1612f86A1f86985f": "curve_metapool_2",
}


def build_plan(contracts: list[Mapping[str, Any]], events: list[Mapping[str, Any]]) -> dict[str, Any]:
    by_id = {e["id"]: e for e in events}
    items = []
    for c in contracts:
        interface = POOL_INTERFACE.get(c["address"])
        if c["verification"] != "SOURCE_DOCUMENTED" or interface is None:
            continue
        for eid in c["event_ids"]:
            start = by_id[eid]["reported_window_utc"]["start"]
            ts = int(datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp())
            items.append({
                "event_id": eid, "contract": c["name"], "address": c["address"], "interface": interface,
                "target_utc": f"{start}T00:00:00Z", "target_unix": ts,
                "block": "TO_RESOLVE via block_at_or_before on an authorized archive endpoint",
                "requests": requests_for(c["address"], "<BLOCK_HEX>", INTERFACES[interface]()),
            })
    skipped = [c["name"] for c in contracts if c["verification"] != "SOURCE_DOCUMENTED"
               or c["address"] not in POOL_INTERFACE]
    return {"network_calls_made": 0, "items": items, "not_planned": skipped,
            "note": "Requests are constructed offline; ABI signatures ASSUMED until checked against verified source."}


def dry_run(plan: Mapping[str, Any]) -> list[str]:
    """Structural checks only: allowed methods, hex calldata, 4-byte selectors, 32-byte argument words."""
    errors = []
    for item in plan["items"]:
        for r in item["requests"]:
            if r["method"] not in {"eth_getCode", "eth_call"}:
                errors.append(f"{item['contract']}: disallowed method {r['method']}")
            if r["method"] == "eth_call":
                data = r["params"][0]["data"]
                body = data[2:]
                if not data.startswith("0x") or len(body) < 8 or (len(body) - 8) % 64:
                    errors.append(f"{item['contract']}: malformed calldata for {r['signature']}")
                if data[:10] != selector(r["signature"]):
                    errors.append(f"{item['contract']}: selector mismatch for {r['signature']}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reports/c2/validation_plan.json"))
    args = parser.parse_args()
    contracts = json.loads(Path("reports/c2/contract_registry.json").read_text())["entries"]
    events = json.loads(Path("configs/event_registry.json").read_text())["events"]
    plan = build_plan(contracts, events)
    errors = dry_run(plan)
    if errors:
        raise SystemExit("\n".join(errors))
    args.output.write_text(json.dumps(plan, indent=1) + "\n")
    print(f"WROTE {args.output}: {len(plan['items'])} pool/event items, dry run clean, 0 network calls")


if __name__ == "__main__":
    main()
