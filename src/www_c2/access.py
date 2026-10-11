"""Offline evaluator for whether a documented source entitlement fits a request."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class Verdict(StrEnum):
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    UNKNOWN = "UNKNOWN"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class AccessRequest:
    start: date
    end: date
    venue: str
    symbols: frozenset[str]
    required_delivery: str  # "csv" or "raw_replay"
    required_capabilities: frozenset[str] = frozenset()


@dataclass(frozen=True)
class SourceOffer:
    name: str
    coverage_start: date | None
    coverage_end: date | None
    venues: frozenset[str] | None
    symbols: frozenset[str] | None
    delivery: frozenset[str] | None
    authenticated: bool | None
    licensed: bool | None
    access_window_verified: bool
    exact_files_verified: bool = False
    capabilities: frozenset[str] | None = None


@dataclass(frozen=True)
class AccessDecision:
    verdict: Verdict
    reasons: tuple[str, ...]


def evaluate_access(request: AccessRequest, offer: SourceOffer) -> AccessDecision:
    """Evaluate documented entitlement; never infer that files were delivered."""
    unknown: list[str] = []
    blockers: list[str] = []
    failures: list[str] = []

    if request.start > request.end:
        raise ValueError("request start must be on or before end")
    if request.required_delivery not in {"csv", "raw_replay"}:
        raise ValueError("required_delivery must be csv or raw_replay")
    if offer.coverage_start is None or offer.coverage_end is None:
        unknown.append("historical coverage dates are not documented")
    elif request.start < offer.coverage_start or request.end > offer.coverage_end:
        failures.append("requested dates fall outside documented access window")
    if offer.venues is None:
        unknown.append("venue coverage is not verified")
    elif request.venue not in offer.venues:
        failures.append("requested venue is not included")
    if offer.symbols is None:
        unknown.append("instrument-level coverage is not verified")
    elif not request.symbols.issubset(offer.symbols):
        failures.append("one or more requested symbols are not included")
    if offer.delivery is None:
        unknown.append("delivery capabilities are not documented")
    elif request.required_delivery not in offer.delivery:
        failures.append("required delivery format is not included")
    if request.required_capabilities:
        if offer.capabilities is None:
            unknown.append("required market-data capabilities are not verified")
        else:
            missing_capabilities = sorted(request.required_capabilities - offer.capabilities)
            if missing_capabilities:
                failures.append("missing required capabilities: " + ", ".join(missing_capabilities))
    if offer.authenticated is None:
        unknown.append("authentication requirement is unknown")
    elif offer.authenticated:
        unknown.append("authenticated entitlement is required and has not been exercised")
    if offer.licensed is None:
        unknown.append("license suitability is not verified")
    elif not offer.licensed:
        blockers.append("license does not authorize the intended research use")
    if not offer.access_window_verified:
        unknown.append("subscription access window has not been verified")
    if not offer.exact_files_verified:
        unknown.append("exact requested historical files have not been obtained")

    if blockers:
        return AccessDecision(Verdict.BLOCKED, tuple(blockers + failures + unknown))
    if failures:
        return AccessDecision(Verdict.INSUFFICIENT, tuple(failures + unknown))
    if unknown:
        return AccessDecision(Verdict.UNKNOWN, tuple(unknown))
    return AccessDecision(Verdict.SUFFICIENT, ("documented request and files verified",))


def estimate_orderbook_transfer_cost(gib_per_day_per_sku: Decimal | None) -> Decimal | None:
    """Estimate CoinAPI PAYG full-book transfer only; excludes LIST/API charges and tax."""
    if gib_per_day_per_sku is None:
        return None
    if gib_per_day_per_sku < 0:
        raise ValueError("transfer size cannot be negative")
    first_tier = min(gib_per_day_per_sku, Decimal("1"))
    second_tier = min(max(gib_per_day_per_sku - Decimal("1"), Decimal("0")), Decimal("9"))
    third_tier = max(gib_per_day_per_sku - Decimal("10"), Decimal("0"))
    return first_tier * Decimal("8") + second_tier * Decimal("4") + third_tier * Decimal("2")
