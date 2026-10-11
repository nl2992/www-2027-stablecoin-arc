"""Structural validation and pre-specified qualification rules for stress events."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


STATUSES = {"CANDIDATE", "SOURCE_DOCUMENTED", "DATA_VERIFIED", "ACCEPTED", "REJECTED", "UNRESOLVED"}
MECHANISMS = {
    "ALGORITHMIC_COLLAPSE", "BANK_RESERVE_RUN", "COLLATERAL_CONTAGION", "EXCHANGE_FAILURE_CONTAGION",
    "DEFI_POOL_IMBALANCE", "REGULATORY_ISSUANCE_HALT", "ISSUER_SOLVENCY_ALLEGATION",
    "RESERVE_TRANSPARENCY", "VENUE_INFRASTRUCTURE", "DELEVERAGING_PREMIUM", "UNBACKED_MINT", "DEMAND_PREMIUM",
}
ROLES = {"PRIMARY", "LINKED_LEG"}
SAMPLE_ROLES = {"IN_SAMPLE", "OUT_OF_SAMPLE", "PLACEBO", "UNASSIGNED"}
SOURCE_TYPES = {"PRIMARY", "RESEARCH", "NEWS"}
DIRECTIONS = {"DISCOUNT", "PREMIUM", "NONE_REPORTED"}

# Pre-specified rules (fixed before any event-level measurement; see docs/e1_event_registry.md).
RULES = {
    "R1_severity": {"threshold_bps": 100.0, "min_minutes": 30, "window": "24h",
                    "observation": "minute closes with positive volume on the stablecoin leg"},
    "R1_severe_class_bps": 500.0,
    "R2_cluster_gap_days": 14,
    "R3_windows_days": {"baseline": 7, "baseline_gap": 1, "recovery": 7, "control_min_lead": 28, "control": 7},
    "R4_min_distinct_publishers": 2,
    "out_of_sample_start": "2024-01-01",
}


def _parse_date(value: Any) -> date:
    return date.fromisoformat(str(value))


def validate_registry(events: Sequence[Mapping[str, Any]]) -> list[str]:
    """Return structural and rule-consistency errors; an empty list means the registry is coherent."""
    errors: list[str] = []
    seen: set[str] = set()
    ids = {e.get("id") for e in events}
    required = {"id", "cluster_id", "role", "stablecoin", "peg", "mechanism", "direction", "reported_window_utc",
                "sources", "status", "sample_role", "data_candidates"}
    for e in events:
        eid = e.get("id", "<missing id>")
        missing = sorted(required - e.keys())
        if missing:
            errors.append(f"{eid}: missing {', '.join(missing)}")
            continue
        if eid in seen:
            errors.append(f"{eid}: duplicate id")
        seen.add(eid)
        if e["status"] not in STATUSES:
            errors.append(f"{eid}: invalid status {e['status']}")
        if e["mechanism"] not in MECHANISMS:
            errors.append(f"{eid}: invalid mechanism {e['mechanism']}")
        if e["role"] not in ROLES:
            errors.append(f"{eid}: invalid role")
        if e["sample_role"] not in SAMPLE_ROLES:
            errors.append(f"{eid}: invalid sample_role")
        if e["direction"] not in DIRECTIONS:
            errors.append(f"{eid}: invalid direction")
        try:
            start = _parse_date(e["reported_window_utc"]["start"])
            end = _parse_date(e["reported_window_utc"]["end"])
            if start > end:
                errors.append(f"{eid}: window start after end")
        except (KeyError, ValueError, TypeError):
            errors.append(f"{eid}: reported_window_utc needs ISO start/end dates")
            start = None
        publishers = set()
        for s in e["sources"]:
            if not str(s.get("url", "")).startswith("https://"):
                errors.append(f"{eid}: source url must be https")
            if s.get("type") not in SOURCE_TYPES:
                errors.append(f"{eid}: invalid source type")
            publishers.add(s.get("publisher"))
        documented = {"SOURCE_DOCUMENTED", "DATA_VERIFIED", "ACCEPTED"}
        if e["status"] in documented and len(publishers) < RULES["R4_min_distinct_publishers"]:
            errors.append(f"{eid}: {e['status']} requires sources from >= 2 distinct publishers")
        if e["status"] in {"DATA_VERIFIED", "ACCEPTED"}:
            m = e.get("measurement")
            if not m or not m.get("input_sha256") or "r1_pass" not in m:
                errors.append(f"{eid}: {e['status']} requires a measurement with input_sha256 and r1_pass")
            elif e["status"] == "ACCEPTED" and not m["r1_pass"]:
                errors.append(f"{eid}: ACCEPTED requires r1_pass")
        if e["status"] == "ACCEPTED" and not e.get("coverage_ok"):
            errors.append(f"{eid}: ACCEPTED requires coverage_ok for baseline, event and recovery windows")
        if e["status"] in {"REJECTED", "UNRESOLVED"} and not e.get("reason"):
            errors.append(f"{eid}: {e['status']} requires a reason")
        if e["role"] == "LINKED_LEG" and e.get("linked_to") not in ids:
            errors.append(f"{eid}: LINKED_LEG must reference an existing event via linked_to")
        if start is not None and e["sample_role"] in {"IN_SAMPLE", "OUT_OF_SAMPLE"}:
            oos = start >= _parse_date(RULES["out_of_sample_start"])
            if oos != (e["sample_role"] == "OUT_OF_SAMPLE"):
                errors.append(f"{eid}: sample_role contradicts the pre-registered out-of-sample date")
    # Independence: primaries within one cluster must not repeat; linked legs share the primary's cluster.
    primaries: dict[str, str] = {}
    by_id = {e.get("id"): e for e in events}
    for e in events:
        if e.get("role") == "PRIMARY":
            if e.get("cluster_id") in primaries:
                errors.append(f"{e['id']}: cluster {e['cluster_id']} already has primary {primaries[e['cluster_id']]}")
            primaries[e.get("cluster_id")] = e.get("id")
        elif e.get("role") == "LINKED_LEG" and e.get("linked_to") in by_id:
            if by_id[e["linked_to"]].get("cluster_id") != e.get("cluster_id"):
                errors.append(f"{e['id']}: linked leg must share its primary's cluster")
    return errors


def independent_clusters(events: Sequence[Mapping[str, Any]], statuses: set[str]) -> list[str]:
    """Clusters whose PRIMARY event has one of ``statuses``; linked legs never add clusters."""
    return sorted({e["cluster_id"] for e in events if e["role"] == "PRIMARY" and e["status"] in statuses})


def r1_severity(times: pd.DatetimeIndex, price: np.ndarray, volume: np.ndarray, *, peg: float = 1.0,
                threshold_bps: float = RULES["R1_severity"]["threshold_bps"],
                min_minutes: int = RULES["R1_severity"]["min_minutes"], window: str = "24h") -> dict[str, Any]:
    """Apply R1: >= min_minutes traded minutes with |deviation| >= threshold inside any rolling window."""
    price = np.asarray(price, float)
    traded = (np.asarray(volume, float) > 0) & np.isfinite(price) & (price > 0)
    dev = 10_000 * np.log(np.where(traded, price, np.nan) / peg)
    breach = pd.Series((np.abs(dev) >= threshold_bps).astype(int), index=times)
    rolling = breach.rolling(window).sum()
    worst = int(rolling.max()) if len(rolling) else 0
    extreme_idx = int(np.nanargmax(np.abs(dev))) if np.isfinite(dev).any() else None
    return {
        "threshold_bps": threshold_bps,
        "min_minutes": min_minutes,
        "window": window,
        "traded_minutes": int(traded.sum()),
        "breach_minutes": int(breach.sum()),
        "max_breach_minutes_in_window": worst,
        "first_breach_utc": breach[breach > 0].index[0].isoformat() if breach.any() else None,
        "last_breach_utc": breach[breach > 0].index[-1].isoformat() if breach.any() else None,
        "extreme_deviation_bps": None if extreme_idx is None else float(dev[extreme_idx]),
        "extreme_utc": None if extreme_idx is None else times[extreme_idx].isoformat(),
        "r1_pass": worst >= min_minutes,
        "severe_class": bool(extreme_idx is not None and abs(dev[extreme_idx]) >= RULES["R1_severe_class_bps"]),
    }


def analysis_windows(start: date, end: date) -> dict[str, dict[str, str]]:
    """Pre-specified baseline / event / recovery / matched-control windows (UTC dates, inclusive)."""
    w = RULES["R3_windows_days"]
    baseline_end = start - timedelta(days=w["baseline_gap"] + 1)
    control_end = start - timedelta(days=w["control_min_lead"])

    def span(a: date, b: date) -> dict[str, str]:
        return {"start": a.isoformat(), "end": b.isoformat()}

    return {
        "baseline": span(baseline_end - timedelta(days=w["baseline"] - 1), baseline_end),
        "event": span(start, end),
        "recovery": span(end + timedelta(days=1), end + timedelta(days=w["recovery"])),
        "control": span(control_end - timedelta(days=w["control"] - 1), control_end),
    }


def load_registry(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text())["events"]


def window_days(window: Mapping[str, str]) -> list[str]:
    start, end = datetime.fromisoformat(window["start"]).date(), datetime.fromisoformat(window["end"]).date()
    return [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]
