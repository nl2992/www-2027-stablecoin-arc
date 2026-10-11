"""Explicit ACCEPT / CONDITIONAL / REJECT gate for historical L2 source candidates."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum


class Evidence(StrEnum):
    VERIFIED = "VERIFIED"      # established from primary docs or an acquired artifact
    UNVERIFIED = "UNVERIFIED"  # not established; requires gated access or provider confirmation
    FAILED = "FAILED"          # primary evidence shows the requirement is not met


class ContinuityStandard(StrEnum):
    NATIVE_SEQUENCE = "NATIVE_SEQUENCE"          # exchange update ids must be present to prove continuity
    PROVIDER_NORMALIZED = "PROVIDER_NORMALIZED"  # provider-ordered stream accepted with disclosed limitation


class SourceDecision(StrEnum):
    ACCEPT = "ACCEPT"
    CONDITIONAL = "CONDITIONAL"
    REJECT = "REJECT"


GATES = (
    "venue",
    "symbol_day_availability",
    "transfer_size_and_cost",
    "snapshot_update_semantics",
    "native_sequence_ids",
    "research_rights",
)


@dataclass(frozen=True)
class GateResult:
    decision: SourceDecision
    failed: tuple[str, ...]
    open: tuple[str, ...]
    disclosed_limitations: tuple[str, ...]


def decide_source(evidence: Mapping[str, Evidence | str], standard: ContinuityStandard | str) -> GateResult:
    """Every gate must be stated; nothing missing is treated as passing."""
    standard = ContinuityStandard(standard)
    missing = sorted(set(GATES) - evidence.keys())
    extra = sorted(evidence.keys() - set(GATES))
    if missing or extra:
        raise ValueError(f"evidence gates mismatch: missing={missing} unexpected={extra}")
    status = {gate: Evidence(evidence[gate]) for gate in GATES}
    required = [g for g in GATES if g != "native_sequence_ids" or standard is ContinuityStandard.NATIVE_SEQUENCE]
    failed = tuple(g for g in required if status[g] is Evidence.FAILED)
    open_ = tuple(g for g in required if status[g] is Evidence.UNVERIFIED)
    limitations = ()
    if standard is ContinuityStandard.PROVIDER_NORMALIZED and status["native_sequence_ids"] is not Evidence.VERIFIED:
        limitations = ("native exchange sequence continuity cannot be independently proven",)
    if failed:
        decision = SourceDecision.REJECT
    elif open_:
        decision = SourceDecision.CONDITIONAL
    else:
        decision = SourceDecision.ACCEPT
    return GateResult(decision, failed, open_, limitations)
