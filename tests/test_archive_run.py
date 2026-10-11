"""Archive executor against a mock JSON-RPC node; no network."""

import pytest

from www_c2.archive_run import Budgeted, StopRun, endpoint_from_env, run
from www_c2.rpc import RpcError
from www_c2.validation_plan import calldata
from www_capacity.amm import stableswap_get_dy

POOL = "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"
COINS = ["0x" + c * 40 for c in "abc"]
DECIMALS = [18, 6, 6]
BALANCES = [500_000 * 10**18, 400_000 * 10**6, 600_000 * 10**6]
A, FEE = 2000, 4_000_000
GENESIS, STEP = 1_600_000_000, 12


def word(n: int) -> str:
    return "0x" + n.to_bytes(32, "big").hex()


def mock_node(prune_below: int | None = None):
    rates = [10 ** (36 - d) for d in DECIMALS]
    answers = {calldata("A()"): word(A), calldata("fee()"): word(FEE)}
    for i in range(3):
        answers[calldata("coins(uint256)", i)] = "0x" + "0" * 24 + COINS[i][2:]
        answers[calldata("balances(uint256)", i)] = word(BALANCES[i])
    dx = 1_000 * 10**18
    answers[calldata("get_dy(int128,int128,uint256)", 0, 1, dx)] = word(
        stableswap_get_dy(0, 1, dx, BALANCES, rates, A, FEE))

    def call(method, params):
        if method == "eth_chainId":
            return "0x1"
        if method == "eth_blockNumber":
            return hex(1_000_000)
        if method == "eth_getBlockByNumber":
            n = int(params[0], 16)
            return {"timestamp": hex(GENESIS + STEP * n), "hash": "0x" + f"{n:064x}"}
        block = int(params[1], 16)
        if prune_below is not None and block < prune_below:
            raise RpcError("provider error code=-32603: state at block is pruned")
        if method == "eth_getCode":
            return "0x6001600055"
        to, data = params[0]["to"], params[0]["data"]
        if data == calldata("decimals()"):
            return word(DECIMALS[COINS.index(to)])
        return answers[data]
    return call


PLAN = {"items": [{"event_id": "E", "contract": "3pool", "address": POOL, "interface": "curve_stableswap_3",
                   "target_unix": GENESIS + STEP * 500_000 + 5}]}


def test_run_resolves_block_and_reproduces_quote_exactly():
    out = run(PLAN, mock_node(), provider_host="mock", budget=200, spacing=0)
    assert out["status"] == "COMPLETED" and out["all_reproduced"]
    item = out["items"][0]
    assert item["block"]["number"] == 500_000 and item["coins"] == COINS and item["decimals"] == DECIMALS
    assert item["abs_diff_raw"] == 0 and all(c.get("method") for c in out["call_log"])


def test_pruned_state_stops_the_run():
    out = run(PLAN, mock_node(prune_below=900_000), provider_host="mock", budget=200, spacing=0)
    assert out["status"] == "STOPPED" and "historical state unavailable" in out["stop_reason"]
    assert not out["all_reproduced"]


def test_budget_is_enforced():
    rpc = Budgeted(lambda m, p: "0x1", budget=2, spacing=0)
    rpc("eth_chainId", []), rpc("eth_chainId", [])
    with pytest.raises(StopRun, match="budget"):
        rpc("eth_chainId", [])


def test_endpoint_read_from_dotenv_without_printing(tmp_path, monkeypatch):
    monkeypatch.delenv("WWW_ETH_RPC_URL", raising=False)
    assert endpoint_from_env(tmp_path) is None
    (tmp_path / ".env").write_text('WWW_ETH_RPC_URL="https://example.invalid/v2/secret"\n')
    assert endpoint_from_env(tmp_path) == "https://example.invalid/v2/secret"


def test_real_rpc_error_carries_provider_message_so_pruning_is_detected(monkeypatch):
    import io
    import json
    import urllib.request
    from www_c2 import rpc

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    body = json.dumps({"jsonrpc": "2.0", "id": 1,
                       "error": {"code": -32603, "message": "state at block #14000001 is pruned"}}).encode()
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: Resp(body))
    with pytest.raises(RpcError, match="pruned") as exc:
        rpc.rpc_call("https://example.invalid/v2/secret", "eth_getCode", ["0x" + "a" * 40, "0x1"])
    assert "secret" not in str(exc.value)
    budgeted = Budgeted(lambda m, p: rpc.rpc_call("https://example.invalid/v2/secret", m, p), budget=5, spacing=0)
    with pytest.raises(StopRun, match="historical state unavailable"):
        budgeted("eth_getCode", ["0x" + "a" * 40, "0x1"])
