import json
from pathlib import Path

import pytest

from www_c2.validation_plan import (
    block_at_or_before, build_plan, calldata, dry_run, keccak256, requests_for, selector,
)

ROOT = Path(__file__).parents[1]


def test_keccak256_matches_standard_vectors():
    assert keccak256(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
    assert selector("transfer(address,uint256)") == "0xa9059cbb"
    assert selector("balanceOf(address)") == "0x70a08231"
    long = keccak256(b"a" * 200)  # crosses the 136-byte rate boundary
    assert len(long) == 32 and long != keccak256(b"a" * 199)


def test_calldata_encodes_32_byte_words_including_signed_ints():
    data = calldata("get_dy(int128,int128,uint256)", 0, 1, 10**6)
    assert data.startswith(selector("get_dy(int128,int128,uint256)")) and len(data) == 2 + 8 + 3 * 64
    assert calldata("A()") == selector("A()")
    neg = calldata("f(int128)", -1)
    assert neg.endswith("f" * 64)
    with pytest.raises(ValueError):
        calldata("coins(uint256)")
    with pytest.raises(ValueError):
        calldata("coins(uint256)", -1)


def test_block_search_finds_last_block_at_or_before_target():
    timestamps = [100, 112, 124, 124, 136, 148]
    get = timestamps.__getitem__
    assert block_at_or_before(124, get, 0, 5) == 3
    assert block_at_or_before(130, get, 0, 5) == 3
    assert block_at_or_before(1_000, get, 0, 5) == 5
    with pytest.raises(ValueError):
        block_at_or_before(50, get, 0, 5)


def test_requests_are_read_only_and_dry_run_rejects_tampering():
    reqs = requests_for("0x" + "a" * 40, "0x10", [{"purpose": "fee", "signature": "fee()", "args": []}])
    assert [r["method"] for r in reqs] == ["eth_getCode", "eth_call"]
    plan = {"items": [{"contract": "x", "requests": reqs}]}
    assert dry_run(plan) == []
    reqs[1]["params"][0]["data"] = "0xdeadbeef"
    reqs.append({"method": "eth_sendTransaction", "params": []})
    errors = dry_run(plan)
    assert any("selector mismatch" in e for e in errors) and any("disallowed" in e for e in errors)


def test_committed_plan_covers_documented_pools_and_made_no_network_calls():
    plan = json.loads((ROOT / "reports/c2/validation_plan.json").read_text())
    contracts = json.loads((ROOT / "reports/c2/contract_registry.json").read_text())["entries"]
    events = json.loads((ROOT / "configs/event_registry.json").read_text())["events"]
    assert plan == json.loads(json.dumps(build_plan(contracts, events)))
    assert plan["network_calls_made"] == 0 and dry_run(plan) == []
    planned = {(i["event_id"], i["address"]) for i in plan["items"]}
    assert ("E2022-05-UST-COLLAPSE", "0xCEAF7747579696A2F0bb206a14210e3c9e6fB269") in planned
    assert "Curve USDe/USDC pool (aggregator-listed)" in plan["not_planned"]  # UNVERIFIED sources are not planned
