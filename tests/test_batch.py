"""End-to-end batch run on synthetic archives in a temporary repository copy (no real data)."""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from www_events.batch import apply_status, run_batch

ROOT = Path(__file__).parents[1]


def _write_month(directory, symbol, start, days, price_fn):
    times = pd.date_range(start, periods=days * 1440, freq="1min", tz="UTC")
    ms = (times.asi8 // 1_000_000).astype(np.int64)
    prices = price_fn(times)
    name = f"{symbol}-1m-{start[:7]}.zip"
    rows = "\n".join(f"{t},{p},{p},{p},{p},5,{t + 59_999},5,3,1,1,0" for t, p in zip(ms, prices))
    path = directory / name
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(name.replace(".zip", ".csv"), rows + "\n")
    (directory / (name + ".CHECKSUM")).write_text(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {name}\n")


def _repo(tmp_path):
    for rel in ("configs/event_registry.json", "configs/plan_freeze.json"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)
    (tmp_path / "reports/events").mkdir(parents=True)
    registry = json.loads((tmp_path / "configs/event_registry.json").read_text())
    template = next(e for e in registry["events"] if e["id"] == "E2024-01-TUSD")
    for eid, start in (("SYN-DEPEG", "2024-06-10"), ("SYN-CALM", "2024-06-10")):
        e = json.loads(json.dumps(template))
        e.update(id=eid, cluster_id="CL-" + eid, reported_window_utc={"start": start, "end": "2024-06-11"},
                 data_candidates=[])
        registry["events"].append(e)
    (tmp_path / "configs/event_registry.json").write_text(json.dumps(registry))
    return tmp_path


def test_batch_accepts_usd_depeg_rejects_calm_and_skips_missing_data(tmp_path):
    root = _repo(tmp_path)
    data = root / "data/raw/synthetic"
    data.mkdir(parents=True)
    depeg = lambda t: np.where((t >= "2024-06-10 06:00") & (t < "2024-06-11 18:00"), 0.97, 1.0)
    _write_month(data, "DEPUSD", "2024-05-01", 31, depeg)
    _write_month(data, "DEPUSD", "2024-06-01", 30, depeg)
    calm = lambda t: np.full(len(t), 1.0)
    _write_month(data, "CALMUSD", "2024-05-01", 31, calm)
    _write_month(data, "CALMUSD", "2024-06-01", 30, calm)
    runs = [
        {"event_id": "SYN-DEPEG", "source": "binance", "path": "data/raw/synthetic", "stable": "DEPUSD", "quote_basis": "USD"},
        {"event_id": "SYN-CALM", "source": "binance", "path": "data/raw/synthetic", "stable": "CALMUSD", "quote_basis": "USD"},
        {"event_id": "E2024-01-TUSD", "source": "binance", "path": "data/raw/absent", "stable": "TUSDUSDT", "quote_basis": "USDT"},
    ]
    out = run_batch(root, runs)
    assert out["executed"] == ["SYN-DEPEG", "SYN-CALM"]
    assert out["skipped"][0]["reason"].startswith("data not acquired")
    registry = {e["id"]: e for e in json.loads((root / "configs/event_registry.json").read_text())["events"]}
    assert registry["SYN-DEPEG"]["status"] == "ACCEPTED" and registry["SYN-DEPEG"]["measurement"]["r1_pass"]
    assert registry["SYN-CALM"]["status"] == "REJECTED" and "R1 not met" in registry["SYN-CALM"]["reason"]
    assert registry["E2024-01-TUSD"]["status"] == "SOURCE_DOCUMENTED"  # untouched: no data
    log = json.loads((root / "reports/events/status_log.json").read_text())
    assert {r["event_id"] for r in log} == {"SYN-DEPEG", "SYN-CALM"}
    assert (root / "reports/events/cross_event_summary.json").is_file()


def test_relative_basis_can_never_be_accepted_and_anchor_is_never_reclassified():
    event = {"id": "X", "role": "PRIMARY", "status": "SOURCE_DOCUMENTED"}
    result = {"r1": {"r1_pass": True}, "price_basis": "USDT_RELATIVE", "plan": {"usdt_gate": {"passes": False}},
              "series": "s", "measured_utc": "2026-10-12T00:00Z", "coverage_ok": True, "provenance": {}}
    assert apply_status(event, result, "r.json", [])["new_status"] == "DATA_VERIFIED"
    anchor = {"id": "E2023-03-USDC-SVB", "role": "PRIMARY", "status": "ACCEPTED"}
    assert apply_status(anchor, result, "r.json", ["E2023-03-USDC-SVB"]) is None and anchor["status"] == "ACCEPTED"


def test_run_config_references_registry_events():
    runs = json.loads((ROOT / "configs/event_runs.json").read_text())["runs"]
    ids = {e["id"] for e in json.loads((ROOT / "configs/event_registry.json").read_text())["events"]}
    assert {r["event_id"] for r in runs} <= ids
