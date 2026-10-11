"""Run the event protocol for every configured event whose data are available locally.

Run specs live in ``configs/event_runs.json``. An event is run only if its data
path exists; otherwise it is skipped with the reason recorded. After each run the
registry status is updated by fixed rules (``apply_status``) and every change is
appended to ``reports/events/status_log.json``. Events measured before the plan
freeze keep their exploratory status and are never re-classified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .registry import validate_registry
from .runner import run_from_spec
from .summary import build_summary


def apply_status(event: dict[str, Any], result: Mapping[str, Any], report_path: str,
                 measured_before_freeze: list[str]) -> dict[str, Any] | None:
    """Update one registry entry from a protocol result; return a log record if anything changed."""
    if event["id"] in measured_before_freeze or event["role"] != "PRIMARY":
        return None
    r1 = result.get("r1") or {}
    if "r1_pass" not in r1:
        return None
    relative = str(result.get("price_basis", "")).endswith("_RELATIVE")
    usd_verified = not relative and bool(result["plan"]["usdt_gate"]["passes"])
    old = event["status"]
    measurement = {"report": report_path, "series": result["series"], "basis": result["price_basis"],
                   "input_sha256": _stable_hash(result), "r1_pass": bool(r1["r1_pass"]),
                   "measured_utc": result["measured_utc"]}
    event["measurement"] = measurement
    if not usd_verified:
        event["status"], rule = "DATA_VERIFIED", "R1 measured on a non-USD-verified basis; cannot be ACCEPTED"
    elif r1["r1_pass"] and result.get("coverage_ok"):
        event["status"], rule = "ACCEPTED", "R1 passed on USD basis with baseline/event/recovery coverage"
        event["coverage_ok"] = True
    elif r1["r1_pass"]:
        event["status"], rule = "DATA_VERIFIED", "R1 passed but R3 window coverage incomplete"
    else:
        event["status"], rule = "REJECTED", "R1 not met on USD basis"
        event["reason"] = (f"R1 not met: max {r1.get('max_breach_minutes_in_window')} breaching traded minutes "
                           f"in 24h (need {r1.get('min_minutes')})")
    if event["status"] != "REJECTED":
        event.pop("reason", None)
    return {"event_id": event["id"], "old_status": old, "new_status": event["status"], "rule": rule,
            "measured_utc": result["measured_utc"], "report": report_path}


def _stable_hash(result: Mapping[str, Any]) -> str:
    prov = result.get("provenance", {}).get("stable") or {}
    if prov.get("sha256"):
        return prov["sha256"]
    files = prov.get("files") or []
    return hashlib.sha256("".join(f["sha256"] for f in files).encode()).hexdigest() if files else ""


def run_batch(root: Path, runs: list[Mapping[str, Any]], *, write: bool = True) -> dict[str, Any]:
    registry_path = root / "configs/event_registry.json"
    registry = json.loads(registry_path.read_text())
    freeze = json.loads((root / "configs/plan_freeze.json").read_text())
    by_id = {e["id"]: e for e in registry["events"]}
    executed, skipped, log = [], [], []
    for spec in runs:
        event = by_id.get(spec["event_id"])
        data_path = Path(spec["path"]) if Path(spec["path"]).is_absolute() else root / spec["path"]
        if event is None:
            skipped.append({"event_id": spec["event_id"], "reason": "not in registry"})
            continue
        if not data_path.exists():
            skipped.append({"event_id": event["id"], "reason": f"data not acquired: {spec['path']}"})
            continue
        spec = {**spec, "path": data_path}
        if spec.get("quote_usd_source"):
            qs = dict(spec["quote_usd_source"])
            qpath = Path(qs["path"]) if Path(qs["path"]).is_absolute() else root / qs["path"]
            if not qpath.exists():
                skipped.append({"event_id": event["id"], "reason": f"USD reference leg not acquired: {qs['path']}"})
                continue
            spec["quote_usd_source"] = {**qs, "path": qpath}
        result = run_from_spec(event, spec, root / "configs/plan_freeze.json")
        rel = f"reports/events/{event['id']}_protocol.json"
        if write:
            (root / rel).write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n")
        record = apply_status(event, result, rel, freeze["measured_before_freeze"])
        if record:
            log.append(record)
        executed.append(event["id"])
    errors = validate_registry(registry["events"])
    if errors:
        raise ValueError(f"registry invalid after status updates: {errors}")
    if write:
        registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n")
        log_path = root / "reports/events/status_log.json"
        history = json.loads(log_path.read_text()) if log_path.is_file() else []
        log_path.write_text(json.dumps(history + log, indent=2) + "\n")
        protocols = [json.loads(p.read_text()) for p in sorted((root / "reports/events").glob("*_protocol.json"))]
        summary = build_summary(registry["events"], protocols)
        (root / "reports/events/cross_event_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return {"executed": executed, "skipped": skipped, "status_changes": log}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--runs", type=Path, default=Path("configs/event_runs.json"))
    args = parser.parse_args()
    runs = json.loads((args.root / args.runs).read_text())["runs"]
    out = run_batch(args.root, runs)
    print(json.dumps(out, indent=2))
    print("Next: uv run python -m www_paper.macros && uv run python -m www_paper.figures")


if __name__ == "__main__":
    main()
