"""Independent validation of reproduced pool state (read-only, bounded).

1. Minimal-proxy resolution: decode EIP-1167 bytecode to its implementation address and
   hash the implementation's code at the same block.
2. Swap cross-check: find a historical TokenExchange in a short block range after each
   event block, keep one whose log is the pool's first log in its block (so the pool state
   at block-1 is exactly the pre-trade state), and verify get_dy(sold_id, bought_id,
   tokens_sold) at block-1 equals the tokens_bought actually emitted.
"""

from __future__ import annotations

import argparse
import json
import urllib.parse
from pathlib import Path
from typing import Any

from .archive_run import Budgeted, StopRun, endpoint_from_env
from .rpc import rpc_call
from .validation_plan import calldata, keccak256

EIP1167_PREFIX = "363d3d373d3d3d363d73"
EIP1167_SUFFIX = "5af43d82803e903d91602b57fd5bf3"
TOKEN_EXCHANGE = "0x" + keccak256(b"TokenExchange(address,int128,uint256,int128,uint256)").hex()
TOKEN_EXCHANGE_UNDERLYING = "0x" + keccak256(b"TokenExchangeUnderlying(address,int128,uint256,int128,uint256)").hex()


def proxy_implementation(code_hex: str) -> str | None:
    body = code_hex[2:].lower() if code_hex.startswith("0x") else code_hex.lower()
    if body.startswith(EIP1167_PREFIX) and body.endswith(EIP1167_SUFFIX) and len(body) == 90:
        return "0x" + body[len(EIP1167_PREFIX):len(EIP1167_PREFIX) + 40]
    return None


def _int(word: str, signed: bool = False) -> int:
    v = int(word, 16)
    return v - (1 << 256) if signed and v >= 1 << 255 else v


def decode_exchange(log: dict[str, Any]) -> dict[str, Any]:
    data = log["data"][2:]
    words = [data[i:i + 64] for i in range(0, len(data), 64)]
    kind = "underlying" if log["topics"][0].lower() == TOKEN_EXCHANGE_UNDERLYING else "direct"
    return {"kind": kind, "block": int(log["blockNumber"], 16), "tx": log["transactionHash"],
            "log_index": int(log["logIndex"], 16),
            "sold_id": _int(words[0], True), "tokens_sold": _int(words[1]), "bought_id": _int(words[2], True),
            "tokens_bought": _int(words[3])}


def first_clean_exchange(call: Any, pool: str, start_block: int, *, window: int = 10, max_windows: int = 150,
                         topics: list[str] | None = None) -> dict[str, Any] | None:
    """Scan forward in provider-sized windows (free tier: 10 blocks per eth_getLogs) for a clean swap."""
    topics = topics or [TOKEN_EXCHANGE, TOKEN_EXCHANGE_UNDERLYING]
    for k in range(max_windows):
        lo = start_block + k * window
        logs = call("eth_getLogs", [{"address": pool, "fromBlock": hex(lo), "toBlock": hex(lo + window - 1),
                                     "topics": [topics]}])
        found = _clean(call, pool, logs)
        if found:
            found["windows_scanned"] = k + 1
            return found
    return None


BASE_POOL = "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"


def _earlier_tx_touches(call: Any, address: str, block: int, tx_index: int) -> bool:
    logs = call("eth_getLogs", [{"address": address, "fromBlock": hex(block), "toBlock": hex(block)}])
    return any(int(entry["transactionIndex"], 16) < tx_index for entry in logs)


def _clean(call: Any, pool: str, logs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """A swap is clean if no earlier transaction in its block touched the pool (or, for underlying swaps,
    the base pool too), so block-1 state is exactly the state the swap executed against."""
    for log in logs:
        block, tx_index = int(log["blockNumber"], 16), int(log["transactionIndex"], 16)
        if _earlier_tx_touches(call, pool, block, tx_index):
            continue
        underlying = log["topics"][0].lower() == TOKEN_EXCHANGE_UNDERLYING
        if underlying and pool.lower() != BASE_POOL.lower() and _earlier_tx_touches(call, BASE_POOL, block, tx_index):
            continue
        return decode_exchange(log)
    return None


def cross_check(call: Any, pool: str, start_block: int, *, direct_only: bool = False) -> dict[str, Any]:
    swap = first_clean_exchange(call, pool, start_block, topics=[TOKEN_EXCHANGE] if direct_only else None,
                                max_windows=400 if direct_only else 150)
    if swap is None:
        return {"status": "NO_CLEAN_SWAP_FOUND", "searched_from": start_block}
    pre = hex(swap["block"] - 1)
    fn = "get_dy_underlying(int128,int128,uint256)" if swap["kind"] == "underlying" else "get_dy(int128,int128,uint256)"
    quoted = int(call("eth_call", [{"to": pool, "data": calldata(fn, swap["sold_id"], swap["bought_id"],
                                                                  swap["tokens_sold"])}, pre]), 16)
    swap["quote_function"] = fn
    return {"status": "CHECKED", **swap, "get_dy_at_prev_block": quoted,
            "abs_diff_raw": abs(quoted - swap["tokens_bought"]), "matches": abs(quoted - swap["tokens_bought"]) <= 2}


def run(validation: dict[str, Any], call: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"items": []}
    seen: set[tuple[str, int]] = set()
    for item in validation["items"]:
        key = (item["address"], item["block"]["number"])
        if key in seen:
            continue
        seen.add(key)
        block_hex = hex(item["block"]["number"])
        entry: dict[str, Any] = {"event_id": item["event_id"], "contract": item["contract"], "address": item["address"],
                                 "block": item["block"]["number"]}
        code = call("eth_getCode", [item["address"], block_hex])
        impl = proxy_implementation(code)
        if impl:
            impl_code = call("eth_getCode", [impl, block_hex])
            entry["proxy"] = {"standard": "EIP-1167", "implementation": impl,
                              "implementation_code_bytes": (len(impl_code) - 2) // 2,
                              "implementation_code_keccak": "0x" + keccak256(bytes.fromhex(impl_code[2:])).hex()}
        entry["swap_cross_check"] = cross_check(call, item["address"], item["block"]["number"] + 1)
        if entry["swap_cross_check"].get("kind") == "underlying" and not entry["swap_cross_check"]["matches"]:
            # get_dy_underlying can be approximate (base-pool leg); confirm the state with an exact direct swap.
            entry["direct_swap_cross_check"] = cross_check(call, item["address"], item["block"]["number"] + 1,
                                                           direct_only=True)
        out["items"].append(entry)
    out["all_swaps_match"] = all(i["swap_cross_check"].get("matches") or
                                 i.get("direct_swap_cross_check", {}).get("matches") for i in out["items"])
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation", type=Path, default=Path("reports/c2/archive_validation.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/c2/archive_checks.json"))
    parser.add_argument("--budget", type=int, default=1500)
    args = parser.parse_args()
    endpoint = endpoint_from_env()
    if not endpoint:
        raise SystemExit("WWW_ETH_RPC_URL not set (shell or git-ignored .env)")
    rpc = Budgeted(lambda m, p: rpc_call(endpoint, m, p), args.budget, 0.2)
    try:
        result = run(json.loads(args.validation.read_text()), rpc)
        result["status"] = "COMPLETED"
    except StopRun as exc:
        result = {"status": "STOPPED", "stop_reason": str(exc), "items": []}
    result.update(provider_host=urllib.parse.urlparse(endpoint).hostname, calls_used=rpc.used, call_log=rpc.log)
    text = json.dumps(result, indent=1)
    if endpoint in text:
        raise SystemExit("refusing to write output containing the endpoint")
    args.output.write_text(text + "\n")
    print(result["status"], "calls", rpc.used, "| all swaps match:", result.get("all_swaps_match"))
    for i in result["items"]:
        sc = i["swap_cross_check"]
        print(i["event_id"], i["contract"][:28], "| proxy:", (i.get("proxy") or {}).get("implementation"),
              "|", sc["status"], sc.get("block"), "sold", sc.get("tokens_sold"), "bought", sc.get("tokens_bought"),
              "quote", sc.get("get_dy_at_prev_block"), "diff", sc.get("abs_diff_raw"),
              "| direct:", (i.get("direct_swap_cross_check") or {}).get("status"),
              (i.get("direct_swap_cross_check") or {}).get("abs_diff_raw"))


if __name__ == "__main__":
    main()
