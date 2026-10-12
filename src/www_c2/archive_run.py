"""Execute the offline validation plan against an authorized archive endpoint (read-only, bounded).

The endpoint comes from WWW_ETH_RPC_URL or a git-ignored .env file; it is never printed
or written, only its hostname is recorded. For each plan item: resolve the block at or
before the target timestamp, read bytecode, A, fee, coins, decimals, balances and
get_dy quotes, then reproduce each quote offline with www_capacity.amm.stableswap_get_dy.
Stops on pruned or missing historical state, wrong chain, or when the call budget is spent.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.parse
from collections.abc import Callable
from pathlib import Path
from typing import Any

from www_capacity.amm import stableswap_get_dy

from .rpc import RpcError, rpc_call
from .validation_plan import calldata, keccak256

THREEPOOL = "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"
Call = Callable[[str, list[Any]], Any]


class StopRun(RuntimeError):
    pass


def endpoint_from_env(root: Path = Path(".")) -> str | None:
    if os.environ.get("WWW_ETH_RPC_URL"):
        return os.environ["WWW_ETH_RPC_URL"].strip()
    env = root / ".env"
    if env.is_file():
        for line in env.read_text().splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "WWW_ETH_RPC_URL" and value.strip():
                return value.strip().strip('"').strip("'")
    return None


class Budgeted:
    """Wraps an RPC call function with a hard call budget, spacing, and a redacted log."""

    def __init__(self, call: Call, budget: int, spacing: float) -> None:
        self.call, self.budget, self.spacing, self.used, self.log = call, budget, spacing, 0, []

    def __call__(self, method: str, params: list[Any]) -> Any:
        if self.used >= self.budget:
            raise StopRun(f"call budget of {self.budget} exhausted")
        if self.used and self.spacing:
            time.sleep(self.spacing)
        self.used += 1
        try:
            result = self.call(method, params)
        except RpcError as exc:
            self.log.append({"method": method, "params": params, "error": str(exc)})
            message = str(exc).lower()
            if "prun" in message or "missing trie" in message or "header not found" in message:
                raise StopRun(f"historical state unavailable: {exc}") from exc
            raise
        self.log.append({"method": method, "params": params, "result": result})
        return result


def block_at_or_before(call: Call, target: int, latest: int, *, max_steps: int = 40) -> dict[str, Any]:
    """Interpolation search (with bisection fallback) for the last block with timestamp <= target."""
    def ts(n: int) -> int:
        block = call("eth_getBlockByNumber", [hex(n), False])
        if block is None:
            raise StopRun(f"block {n} unavailable")
        return int(block["timestamp"], 16)

    lo, hi = 1, latest
    t_lo, t_hi = ts(lo), ts(hi)
    if not t_lo <= target < t_hi:
        raise ValueError("target outside chain history")
    for _ in range(max_steps):
        if hi - lo <= 1:
            break
        guess = lo + int((target - t_lo) * (hi - lo) / max(t_hi - t_lo, 1))
        guess = min(max(guess, lo + 1), hi - 1)
        if hi - lo < 64:
            guess = (lo + hi) // 2
        t_g = ts(guess)
        if t_g <= target:
            lo, t_lo = guess, t_g
        else:
            hi, t_hi = guess, t_g
    block = call("eth_getBlockByNumber", [hex(lo), False])
    return {"number": lo, "hash": block["hash"], "timestamp": int(block["timestamp"], 16)}


def _uint(result: str) -> int:
    return int(result, 16)


def _addr(result: str) -> str:
    return "0x" + result[-40:]


def read_pool(call: Call, address: str, n_coins: int, block_hex: str, *, metapool: bool) -> dict[str, Any]:
    eth = lambda sig, *args, to=address: call("eth_call", [{"to": to, "data": calldata(sig, *args)}, block_hex])
    code = call("eth_getCode", [address, block_hex])
    if code in ("0x", "0x0", None):
        raise StopRun(f"no bytecode at {address} for block {block_hex}")
    state: dict[str, Any] = {"code_bytes": (len(code) - 2) // 2, "code_keccak": "0x" + keccak256(bytes.fromhex(code[2:])).hex(),
                             "A": _uint(eth("A()")), "fee": _uint(eth("fee()")), "coins": [], "decimals": [], "balances": []}
    for i in range(n_coins):
        coin = _addr(eth("coins(uint256)", i))
        state["coins"].append(coin)
        state["balances"].append(_uint(eth("balances(uint256)", i)))
        state["decimals"].append(_uint(call("eth_call", [{"to": coin, "data": calldata("decimals()")}, block_hex])))
    if metapool:
        state["base_virtual_price"] = _uint(eth("get_virtual_price()", to=THREEPOOL))
    dx = 1_000 * 10 ** state["decimals"][0]
    state["quote_dx_raw"] = dx
    state["onchain_get_dy"] = _uint(eth("get_dy(int128,int128,uint256)", 0, 1, dx))
    rates = [10 ** (36 - d) for d in state["decimals"]]
    if metapool:
        rates[1] = state["base_virtual_price"]
    state["offline_get_dy"] = stableswap_get_dy(0, 1, dx, state["balances"], rates, state["A"], state["fee"])
    state["abs_diff_raw"] = abs(state["offline_get_dy"] - state["onchain_get_dy"])
    state["reproduced"] = state["abs_diff_raw"] <= 2
    return state


def run(plan: dict[str, Any], call: Call, *, provider_host: str, budget: int, spacing: float) -> dict[str, Any]:
    rpc = Budgeted(call, budget, spacing)
    out: dict[str, Any] = {"provider_host": provider_host, "budget": budget, "items": [], "status": "RUNNING"}
    try:
        if rpc("eth_chainId", []) != "0x1":
            raise StopRun("wrong chain")
        latest = int(rpc("eth_blockNumber", []), 16)
        blocks: dict[int, dict[str, Any]] = {}
        for item in plan["items"]:
            target = item["target_unix"]
            if target not in blocks:
                blocks[target] = block_at_or_before(rpc, target, latest)
            blk = blocks[target]
            state = read_pool(rpc, item["address"], 3 if item["interface"] == "curve_stableswap_3" else 2,
                              hex(blk["number"]), metapool=item["interface"] == "curve_metapool_2")
            out["items"].append({"event_id": item["event_id"], "contract": item["contract"], "address": item["address"],
                                 "block": blk, **state})
        out["status"] = "COMPLETED"
    except StopRun as exc:
        out["status"], out["stop_reason"] = "STOPPED", str(exc)
    out["calls_used"] = rpc.used
    out["call_log"] = rpc.log
    out["all_reproduced"] = bool(out["items"]) and all(i["reproduced"] for i in out["items"])
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=Path("reports/c2/validation_plan.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/c2/archive_validation.json"))
    parser.add_argument("--budget", type=int, default=150)
    parser.add_argument("--spacing", type=float, default=0.5, help="seconds between calls")
    args = parser.parse_args()
    endpoint = endpoint_from_env()
    if not endpoint:
        raise SystemExit("Set WWW_ETH_RPC_URL in your shell or in a .env file (git-ignored). Never paste it in chat.")
    host = urllib.parse.urlparse(endpoint).hostname or "unknown"
    plan = json.loads(args.plan.read_text())
    result = run(plan, lambda m, p: rpc_call(endpoint, m, p), provider_host=host, budget=args.budget, spacing=args.spacing)
    text = json.dumps(result, indent=1)
    if endpoint in text:  # defence in depth: the secret must never reach disk
        raise SystemExit("refusing to write output containing the endpoint")
    args.output.write_text(text + "\n")
    print(f"{result['status']}: {len(result['items'])} items, {result['calls_used']} calls, "
          f"all reproduced={result['all_reproduced']} ({host})")


if __name__ == "__main__":
    main()
