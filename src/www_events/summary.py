"""Apply the frozen pre-analysis plan's decision rules across all measured events.

Inputs: ``configs/event_registry.json`` and every ``reports/events/*_protocol.json``.
Output: ``reports/events/cross_event_summary.json``. With too few qualifying
events the decision fields say so explicitly; nothing is extrapolated.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .crossevent import holm, sign_test, summarize_by_mechanism

ALPHA = 0.05
MIN_INDEPENDENT_EPISODES = 3


def _row(protocol: Mapping[str, Any], event: Mapping[str, Any]) -> dict[str, Any]:
    plan = protocol.get("plan", {})
    dv1 = plan.get("dv1", {})
    return {
        "event_id": event["id"], "cluster_id": event["cluster_id"], "role": event["role"],
        "registry_status": event["status"],
        "mechanism": event["mechanism"], "sample_role": event["sample_role"],
        "analysis_status": plan.get("analysis_status", "UNLABELLED"),
        "estimate": dv1.get("estimate"), "se": dv1.get("se"), "p_value": dv1.get("p_value"),
        "ci95": dv1.get("ci95"), "reference_is_fallback": plan.get("dv1_reference_is_fallback"),
        "recovery_minutes": plan.get("dv3", {}).get("recovery_minutes"),
        "recovery_censored": plan.get("dv3", {}).get("censored"),
        "dv5_ratio": plan.get("dv5", {}).get("ratio"),
    }


def _satisfies_h1(row: Mapping[str, Any], adjusted_p: float | None) -> bool:
    return bool(row["estimate"] is not None and row["estimate"] > 0 and row["ci95"]
                and row["ci95"][0] > 0 and adjusted_p is not None and adjusted_p < ALPHA)


def _h1_family(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    usable = [r for r in rows if r["p_value"] is not None]
    adjusted = holm({r["event_id"]: r["p_value"] for r in usable}) if usable else {}
    satisfied = [r["event_id"] for r in usable if _satisfies_h1(r, adjusted.get(r["event_id"]))]
    return {"n": len(usable), "satisfied": satisfied, "holm_adjusted_p": adjusted}


def _h2(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Plan 3: count DV5 > 1 across independent confirmatory clusters; sign test is descriptive below six."""
    measured = [r for r in rows if r.get("dv5_ratio") is not None]
    n, k = len(measured), sum(r["dv5_ratio"] > 1 for r in measured)
    if n == 0:
        return {"n": 0, "decision": "INSUFFICIENT_EVENTS"}
    p = sign_test(k, n)
    return {"n": n, "ratio_above_one": k, "sign_test_p": p,
            "decision": ("DESCRIPTIVE_ONLY" if n < 6 else "SUPPORTED" if p < ALPHA and k > n / 2 else "NOT_SUPPORTED")}


def build_summary(registry: Sequence[Mapping[str, Any]], protocols: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_id = {e["id"]: e for e in registry}
    rows = [_row(p, by_id[p["event_id"]]) for p in protocols if p["event_id"] in by_id]
    primaries = [r for r in rows if r["role"] == "PRIMARY"]
    # Plan section 1: confirmatory sets are ACCEPTED primaries only (qualified stress episodes), never events
    # that failed R1/R3 or whose USD basis is invalid, and never the exploratory anchor.
    confirmed = [r for r in primaries if r["analysis_status"] == "CONFIRMATORY" and r["registry_status"] == "ACCEPTED"]
    confirm_in = [r for r in confirmed if r["sample_role"] == "IN_SAMPLE"]
    confirm_oos = [r for r in confirmed if r["sample_role"] == "OUT_OF_SAMPLE"]
    placebos = [r for r in primaries if r["sample_role"] == "PLACEBO"]
    accepted_clusters = sorted({e["cluster_id"] for e in registry if e["role"] == "PRIMARY" and e["status"] == "ACCEPTED"})

    h1_in, h1_oos = _h1_family(confirm_in), _h1_family(confirm_oos)
    placebo_hits = _h1_family(placebos)["satisfied"]
    if h1_in["n"] == 0:
        h1_decision = "INSUFFICIENT_EVENTS"
    else:
        share = len(h1_in["satisfied"]) / h1_in["n"]
        h1_decision = "SUPPORTED" if share >= 2 / 3 and not placebo_hits else "NOT_SUPPORTED"
    if h1_oos["n"] == 0:
        oos_decision = "INSUFFICIENT_EVENTS"
    elif h1_decision == "INSUFFICIENT_EVENTS":
        # Replication presupposes an in-sample result; report the raw count without a replication verdict.
        oos_decision = f"NO_IN_SAMPLE_RESULT ({len(h1_oos['satisfied'])}/{h1_oos['n']} out-of-sample events satisfy H1)"
    else:
        oos_decision = "REPLICATED" if len(h1_oos["satisfied"]) > h1_oos["n"] / 2 else "NOT_REPLICATED"
    pooled_rows = [{"cluster_id": r["cluster_id"], "mechanism": r["mechanism"], "role": r["role"],
                    "estimate": r["estimate"], "se": r["se"]}
                   for r in confirm_in + confirm_oos if r["estimate"] is not None and r["se"]]
    return {
        "plan": "docs/PRE_ANALYSIS_PLAN.md (frozen; see configs/plan_freeze.json)",
        "independent_accepted_clusters": accepted_clusters,
        "multi_event_criterion_met": len(accepted_clusters) >= MIN_INDEPENDENT_EPISODES,
        "framing": ("CONFIRMATORY_MULTI_EVENT" if len(confirm_in) + len(confirm_oos) >= MIN_INDEPENDENT_EPISODES
                    else "DESCRIPTIVE: fewer than three independent confirmatory episodes"),
        "events": rows,
        "exploratory_events": [r["event_id"] for r in rows if r["analysis_status"] == "EXPLORATORY"],
        "h1": {"in_sample": {**h1_in, "decision": h1_decision}, "placebo_satisfying_h1": placebo_hits,
               "out_of_sample": {**h1_oos, "decision": oos_decision}},
        "h2": _h2(confirm_in + confirm_oos),
        "h3": {"decision": "NOT_TESTABLE", "reason": "capacity gate closed: no validated execution state or authorization"},
        "mechanism_summaries": summarize_by_mechanism(pooled_rows) if pooled_rows else {},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("configs/event_registry.json"))
    parser.add_argument("--reports", type=Path, default=Path("reports/events"))
    parser.add_argument("--output", type=Path, default=Path("reports/events/cross_event_summary.json"))
    args = parser.parse_args()
    registry = json.loads(args.registry.read_text())["events"]
    protocols = [json.loads(p.read_text()) for p in sorted(args.reports.glob("*_protocol.json"))]
    summary = build_summary(registry, protocols)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"WROTE {args.output}: framing={summary['framing']}; H1 in-sample={summary['h1']['in_sample']['decision']}")


if __name__ == "__main__":
    main()
