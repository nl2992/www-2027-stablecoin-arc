"""Small read-only JSON-RPC probe; does not send transactions or log endpoint URLs."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from typing import Any


class RpcError(RuntimeError):
    pass


def rpc_call(endpoint: str, method: str, params: list[Any], *, timeout: float = 15) -> Any:
    if not endpoint.startswith("https://"):
        raise ValueError("RPC endpoint must use HTTPS")
    if method not in {"eth_chainId", "eth_blockNumber", "eth_getBlockByNumber", "eth_getCode", "eth_call",
                      "eth_getLogs", "eth_getTransactionReceipt"}:
        raise ValueError("only explicitly allowed read-only RPC methods are supported")
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "www-stablecoin-research/0.1 (read-only)"}
    request = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:200].decode("utf-8", "replace") if hasattr(exc, "read") else ""
        detail = detail.replace(endpoint, "<redacted>")
        raise RpcError(f"request failed (HTTP {exc.code}: {detail}); endpoint redacted") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RpcError(f"request failed ({type(exc).__name__}); endpoint redacted") from exc
    if "error" in payload:
        error = payload["error"]
        message = str(error.get("message", ""))[:200]
        raise RpcError(f"provider error code={error.get('code', 'unknown')}: {message}; endpoint redacted")
    if "result" not in payload:
        raise RpcError("malformed JSON-RPC response; endpoint redacted")
    return payload["result"]


def probe(endpoint: str, block_hex: str, contract: str, call_data: str | None = None) -> dict[str, Any]:
    if not block_hex.startswith("0x") or any(c not in "0123456789abcdefABCDEF" for c in block_hex[2:]):
        raise ValueError("block must be a hex quantity")
    if len(contract) != 42 or not contract.startswith("0x"):
        raise ValueError("contract must be a 20-byte hex address")
    chain_id = rpc_call(endpoint, "eth_chainId", [])
    if chain_id != "0x1":
        raise RpcError(f"wrong chain id: expected 0x1, received {chain_id}")
    block = rpc_call(endpoint, "eth_getBlockByNumber", [block_hex, False])
    if block is None:
        raise RpcError("requested historical block unavailable")
    if block.get("number", "").lower() != hex(int(block_hex, 16)):
        raise RpcError("provider returned a different block than requested")
    block_hash = block.get("hash")
    if not isinstance(block_hash, str) or len(block_hash) != 66 or not block_hash.startswith("0x") or any(
        c not in "0123456789abcdefABCDEF" for c in block_hash[2:]
    ):
        raise RpcError("provider returned an invalid block hash")
    code = rpc_call(endpoint, "eth_getCode", [contract, block_hex])
    if not isinstance(code, str) or not code.startswith("0x") or any(c not in "0123456789abcdefABCDEF" for c in code[2:]):
        raise RpcError("provider returned invalid contract bytecode")
    result = {"chain_id": chain_id, "block_number": block.get("number"), "block_hash": block_hash,
            "contract": contract, "code_bytes": max(0, (len(code) - 2) // 2),
            "status": "LIVE_VERIFIED" if code not in {"0x", "0x0"} else "NO_CODE_AT_BLOCK"}
    if call_data is not None:
        if not call_data.startswith("0x") or any(c not in "0123456789abcdefABCDEF" for c in call_data[2:]):
            raise ValueError("call data must be hex encoded")
        result["eth_call_result"] = rpc_call(endpoint, "eth_call", [{"to": contract, "data": call_data}, block_hex])
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block", required=True, help="Ethereum block as a hex quantity")
    parser.add_argument("--contract", required=True)
    parser.add_argument("--call-data", help="optional ABI-encoded read-only eth_call payload")
    args = parser.parse_args()
    endpoint = os.environ.get("WWW_ETH_RPC_URL")
    if not endpoint:
        parser.error("set WWW_ETH_RPC_URL locally; do not pass secrets on the command line")
    print(json.dumps(probe(endpoint, args.block, args.contract, args.call_data), indent=2))


if __name__ == "__main__":
    main()
