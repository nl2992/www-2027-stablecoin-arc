import json
from pathlib import Path

from www_c2.contracts import validate_registry


def test_documented_candidate_registry_is_structurally_valid():
    path = Path(__file__).parents[1] / "reports/c2/contract_registry.json"
    entries = json.loads(path.read_text())["entries"]
    assert validate_registry(entries) == []
    assert all(item["deployment_status"] == "UNVERIFIED_AT_TARGET_BLOCK" for item in entries)


def test_duplicate_address_and_false_live_status_are_rejected():
    item = {"name": "candidate", "chain_id": 1, "address": "0x" + "a" * 40,
            "source": "https://example.org", "deployment_status": "UNVERIFIED_AT_TARGET_BLOCK",
            "verification": "LIVE_VERIFIED"}
    assert any("live verification" in issue for issue in validate_registry([item]))
    assert any("duplicate" in issue for issue in validate_registry([item, item]))


def test_malformed_address_and_unknown_status_are_rejected():
    item = {"name": "bad", "chain_id": 1, "address": "0xnot-an-address", "source": "https://example.org",
            "deployment_status": "unknown", "verification": "SOURCE_DOCUMENTED"}
    errors = validate_registry([item])
    assert any("20-byte" in issue for issue in errors)
    assert any("invalid deployment" in issue for issue in errors)


def test_every_contract_is_linked_to_existing_registry_events():
    reg = json.loads((Path(__file__).parents[1] / "reports/c2/contract_registry.json").read_text())
    events = {e["id"] for e in json.loads((Path(__file__).parents[1] / "configs/event_registry.json").read_text())["events"]}
    for entry in reg["entries"]:
        assert entry["event_ids"] and set(entry["event_ids"]) <= events, entry["name"]
    # Aggregator-only listings must not be labelled source-documented.
    for entry in reg["entries"]:
        if "dexpaprika" in entry["source"]:
            assert entry["verification"] == "UNVERIFIED"
