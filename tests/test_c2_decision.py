import json
from pathlib import Path

import pytest

from www_c2.decision import GATES, ContinuityStandard, Evidence, SourceDecision, decide_source


def evidence(**overrides):
    base = {gate: Evidence.VERIFIED for gate in GATES}
    base.update(overrides)
    return base


def test_all_verified_is_accept_under_both_standards():
    for standard in ContinuityStandard:
        assert decide_source(evidence(), standard).decision == SourceDecision.ACCEPT


def test_any_unverified_required_gate_is_conditional():
    result = decide_source(evidence(research_rights=Evidence.UNVERIFIED), ContinuityStandard.PROVIDER_NORMALIZED)
    assert result.decision == SourceDecision.CONDITIONAL
    assert result.open == ("research_rights",)


def test_failed_gate_rejects_even_when_others_are_open():
    result = decide_source(evidence(symbol_day_availability=Evidence.FAILED, research_rights=Evidence.UNVERIFIED),
                           ContinuityStandard.PROVIDER_NORMALIZED)
    assert result.decision == SourceDecision.REJECT
    assert result.failed == ("symbol_day_availability",)


def test_missing_native_ids_rejects_only_under_native_standard():
    ev = evidence(native_sequence_ids=Evidence.FAILED)
    assert decide_source(ev, ContinuityStandard.NATIVE_SEQUENCE).decision == SourceDecision.REJECT
    normalized = decide_source(ev, ContinuityStandard.PROVIDER_NORMALIZED)
    assert normalized.decision == SourceDecision.ACCEPT
    assert normalized.disclosed_limitations


def test_missing_or_unknown_gate_is_an_error_not_a_pass():
    incomplete = evidence()
    del incomplete["research_rights"]
    with pytest.raises(ValueError, match="missing"):
        decide_source(incomplete, ContinuityStandard.PROVIDER_NORMALIZED)
    with pytest.raises(ValueError, match="unexpected"):
        decide_source(evidence(extra=Evidence.VERIFIED), ContinuityStandard.PROVIDER_NORMALIZED)


def test_invalid_status_string_is_rejected():
    with pytest.raises(ValueError):
        decide_source(evidence(venue="PROBABLY"), ContinuityStandard.PROVIDER_NORMALIZED)


def load_report():
    return json.loads((Path(__file__).parents[1] / "reports/c2/source_decision.json").read_text())


def test_committed_decisions_match_the_gate_engine():
    for candidate in load_report()["candidates"]:
        statuses = {gate: item["status"] for gate, item in candidate["evidence"].items()}
        assert all(item["basis"] for item in candidate["evidence"].values())
        for standard, recorded in candidate["decisions"].items():
            result = decide_source(statuses, standard)
            assert recorded == {"decision": result.decision, "failed": list(result.failed),
                                "open": list(result.open),
                                "disclosed_limitations": list(result.disclosed_limitations)}, candidate["id"]


def test_coinapi_is_conditional_not_accepted_and_no_source_is_selected():
    report = load_report()
    coinapi = next(c for c in report["candidates"] if c["id"] == "coinapi_flat_files_payg")
    assert coinapi["decisions"][report["project_standard"]]["decision"] == "CONDITIONAL"
    assert coinapi["decisions"]["NATIVE_SEQUENCE"]["decision"] == "REJECT"
    assert report["gated_activity_authorized"] is False
    assert report["selected_empirical_l2_source"] is None
    assert not any(d["decision"] == "ACCEPT" for c in report["candidates"] for d in c["decisions"].values())
