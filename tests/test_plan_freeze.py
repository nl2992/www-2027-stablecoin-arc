import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_pre_analysis_plan_is_unchanged_since_freeze():
    freeze = json.loads((ROOT / "configs/plan_freeze.json").read_text())
    actual = hashlib.sha256((ROOT / freeze["file"]).read_bytes()).hexdigest()
    assert actual == freeze["sha256"], "plan changed: record the change in PRE_ANALYSIS_AMENDMENTS.md instead"
    assert (ROOT / freeze["amendments_file"]).is_file()


def test_measurements_after_freeze_are_timestamped_after_it():
    """Pre-freeze (exploratory) measurements are listed; any other measured primary must post-date the freeze."""
    freeze = json.loads((ROOT / "configs/plan_freeze.json").read_text())
    events = json.loads((ROOT / "configs/event_registry.json").read_text())["events"]
    measured = {e["id"]: e["measurement"] for e in events
                if e["role"] == "PRIMARY" and (e.get("measurement") or {}).get("input_sha256")}
    assert set(freeze["measured_before_freeze"]) <= set(measured)
    for event_id, m in measured.items():
        if event_id not in freeze["measured_before_freeze"]:
            assert m.get("measured_utc", "") > freeze["frozen_utc"], f"{event_id} lacks a post-freeze timestamp"
