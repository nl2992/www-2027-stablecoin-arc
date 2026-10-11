import json
from pathlib import Path

from www_events.summary import build_summary

ROOT = Path(__file__).parents[1]


def ev(eid, cluster, sample_role="IN_SAMPLE", role="PRIMARY", mechanism="BANK_RESERVE_RUN", status="ACCEPTED"):
    return {"id": eid, "cluster_id": cluster, "role": role, "sample_role": sample_role,
            "mechanism": mechanism, "status": status}


def proto(eid, est, p, status="CONFIRMATORY", lo=None):
    lo = (est - 1) if lo is None else lo
    return {"event_id": eid, "plan": {"analysis_status": status, "dv1_reference_is_fallback": False,
                                      "dv1": {"estimate": est, "se": 1.0, "p_value": p, "ci95": [lo, est + 1]},
                                      "dv3": {"recovery_minutes": 60.0, "censored": False}}}


def test_current_repository_state_reports_insufficient_events_honestly():
    registry = json.loads((ROOT / "configs/event_registry.json").read_text())["events"]
    protocols = [json.loads(p.read_text()) for p in (ROOT / "reports/events").glob("*_protocol.json")]
    out = build_summary(registry, protocols)
    assert out["h1"]["in_sample"]["decision"] == "INSUFFICIENT_EVENTS"
    assert out["exploratory_events"] == ["E2023-03-USDC-SVB"]
    assert not out["multi_event_criterion_met"] and out["framing"].startswith("DESCRIPTIVE")
    assert out["h3"]["decision"] == "NOT_TESTABLE"


def test_h1_supported_needs_two_thirds_after_holm_and_clean_placebo():
    reg = [ev("A", "CA"), ev("B", "CB"), ev("C", "CC"), ev("P", "CP", sample_role="PLACEBO")]
    protos = [proto("A", 10, 0.001), proto("B", 8, 0.004), proto("C", 0.5, 0.40, lo=-0.5), proto("P", 0.1, 0.9, lo=-1)]
    out = build_summary(reg, protos)
    assert out["h1"]["in_sample"]["satisfied"] == ["A", "B"]
    assert out["h1"]["in_sample"]["decision"] == "SUPPORTED"
    assert out["framing"] == "CONFIRMATORY_MULTI_EVENT"
    protos[-1] = proto("P", 9, 0.001)  # placebo also "shows" stress -> H1 not supported
    assert build_summary(reg, protos)["h1"]["in_sample"]["decision"] == "NOT_SUPPORTED"


def test_holm_can_overturn_a_nominally_significant_event():
    reg = [ev("A", "CA"), ev("B", "CB"), ev("C", "CC")]
    protos = [proto("A", 5, 0.02), proto("B", 5, 0.03), proto("C", 5, 0.04)]
    out = build_summary(reg, protos)["h1"]["in_sample"]
    # Holm step-down: 3*0.02 = 0.06, then max(0.06, 2*0.03), then max(0.06, 1*0.04) = 0.06 -> none survive.
    assert out["satisfied"] == [] and out["decision"] == "NOT_SUPPORTED"


def test_linked_legs_exploratory_and_oos_are_separated():
    reg = [ev("A", "CA"), ev("L", "CA", role="LINKED_LEG"), ev("X", "CX"), ev("O", "CO", sample_role="OUT_OF_SAMPLE")]
    protos = [proto("A", 10, 0.001), proto("L", 50, 0.001), proto("X", 10, 0.001, status="EXPLORATORY"),
              proto("O", 7, 0.002)]
    out = build_summary(reg, protos)
    assert out["h1"]["in_sample"]["n"] == 1 and out["h1"]["out_of_sample"]["decision"] == "REPLICATED"
    assert out["exploratory_events"] == ["X"]
    assert out["mechanism_summaries"]["BANK_RESERVE_RUN"]["k"] == 2  # A and O; never the linked leg L


def test_committed_cross_event_summary_is_current():
    registry = json.loads((ROOT / "configs/event_registry.json").read_text())["events"]
    protocols = [json.loads(p.read_text()) for p in sorted((ROOT / "reports/events").glob("*_protocol.json"))]
    committed = json.loads((ROOT / "reports/events/cross_event_summary.json").read_text())
    assert committed == json.loads(json.dumps(build_summary(registry, protocols))), "run python -m www_events.summary"
