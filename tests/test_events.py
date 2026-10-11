import copy
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from www_events.coverage import coverage_rows, parse_monthly_kline_listing, summarize
from www_events.registry import (
    RULES, analysis_windows, independent_clusters, load_registry, r1_severity, validate_registry,
)

ROOT = Path(__file__).parents[1]
REGISTRY = ROOT / "configs/event_registry.json"


def events():
    return load_registry(REGISTRY)


def test_committed_registry_is_structurally_valid():
    assert validate_registry(events()) == []


def test_only_measured_events_are_accepted_and_multi_event_target_is_not_claimed():
    evs = events()
    accepted = [e for e in evs if e["status"] == "ACCEPTED"]
    assert [e["id"] for e in accepted] == ["E2023-03-USDC-SVB"]
    assert independent_clusters(evs, {"ACCEPTED"}) == ["CL-2023-03-SVB"]
    # Linked legs never count as extra independent episodes.
    assert len(independent_clusters(evs, {"SOURCE_DOCUMENTED", "ACCEPTED"})) < len(
        [e for e in evs if e["status"] in {"SOURCE_DOCUMENTED", "ACCEPTED"}])


def test_anchor_measurement_matches_committed_report():
    anchor = next(e for e in events() if e["id"] == "E2023-03-USDC-SVB")
    report = json.loads((ROOT / anchor["measurement"]["report"]).read_text())
    assert report["input_sha256"] == anchor["measurement"]["input_sha256"]
    assert report["r1_pass"] is anchor["measurement"]["r1_pass"] is True


@pytest.mark.parametrize("mutation, message", [
    (lambda e: e.update(status="ACCEPTED", measurement=None), "requires a measurement"),
    (lambda e: e.update(sources=e["sources"][:1]), "distinct publishers"),
    (lambda e: e.update(mechanism="VIBES"), "invalid mechanism"),
    (lambda e: e.update(sample_role="OUT_OF_SAMPLE"), "pre-registered out-of-sample"),
    (lambda e: e.update(reported_window_utc={"start": "2022-05-13", "end": "2022-05-07"}), "start after end"),
    (lambda e: e["sources"][0].update(url="http://insecure"), "https"),
])
def test_validator_rejects_inconsistent_entries(mutation, message):
    evs = copy.deepcopy(events())
    ust = next(e for e in evs if e["id"] == "E2022-05-UST-COLLAPSE")
    mutation(ust)
    assert any(message in err for err in validate_registry(evs))


def test_duplicate_primary_in_cluster_and_orphan_linked_leg_are_rejected():
    evs = copy.deepcopy(events())
    leg = next(e for e in evs if e["id"] == "E2022-05-USDT-TERRA-CONTAGION")
    leg["role"] = "PRIMARY"
    assert any("already has primary" in err for err in validate_registry(evs))
    evs = copy.deepcopy(events())
    next(e for e in evs if e["id"] == "E2023-03-DAI-SVB")["linked_to"] = "NOPE"
    assert any("linked_to" in err for err in validate_registry(evs))


def test_rejected_or_unresolved_need_reason():
    evs = copy.deepcopy(events())
    next(e for e in evs if e["id"] == "U2026-06-MIM").pop("reason")
    assert any("requires a reason" in err for err in validate_registry(evs))


def minute_index(n):
    return pd.date_range("2023-03-10", periods=n, freq="1min", tz="UTC")


def test_r1_counts_only_traded_minutes_and_uses_rolling_window():
    n = 3000
    price = np.ones(n)
    price[100:130] = 0.98  # 30 minutes at about -202 bps
    volume = np.ones(n)
    result = r1_severity(minute_index(n), price, volume)
    assert result["r1_pass"] and result["max_breach_minutes_in_window"] == 30
    volume[100] = 0  # an untraded minute cannot count
    assert not r1_severity(minute_index(n), price, volume)["r1_pass"]


def test_r1_rejects_spread_out_breaches_and_flags_severe_class():
    n = 4 * 24 * 60
    price = np.ones(n)
    price[::1440][:4] = 0.9  # one breach per day, never 30 within 24h
    out = r1_severity(minute_index(n), price, np.ones(n))
    assert not out["r1_pass"] and out["breach_minutes"] == 4 and out["severe_class"]


def test_analysis_windows_follow_preregistered_offsets():
    w = analysis_windows(date(2023, 3, 10), date(2023, 3, 13))
    assert w == {
        "baseline": {"start": "2023-03-02", "end": "2023-03-08"},
        "event": {"start": "2023-03-10", "end": "2023-03-13"},
        "recovery": {"start": "2023-03-14", "end": "2023-03-20"},
        "control": {"start": "2023-02-04", "end": "2023-02-10"},
    }
    assert RULES["R3_windows_days"]["control_min_lead"] == 28


def test_listing_parser_keeps_monthly_zips_only():
    xml = (ROOT / "tests/fixtures/events/usdeusdt_listing.xml").read_text()
    listing = parse_monthly_kline_listing(xml, "USDEUSDT")
    assert set(listing) == {"2025-09", "2025-10"}
    assert listing["2025-10"]["bytes"] == 931777 and listing["2025-10"]["etag"].startswith("1e08")


def test_coverage_rows_mark_listed_months_and_local_observations():
    evs = [e for e in events() if e["id"] in {"E2025-10-USDE-BINANCE", "E2023-03-USDC-SVB"}]
    xml = (ROOT / "tests/fixtures/events/usdeusdt_listing.xml").read_text()
    listings = {"USDEUSDT": parse_monthly_kline_listing(xml, "USDEUSDT"), "USDCUSDT": {}}
    rows = coverage_rows(evs, lambda s: listings[s])
    summary = summarize(rows)
    usde = summary["E2025-10-USDE-BINANCE|binance|USDEUSDT"]
    assert usde["event"] == {"LISTED": 2} and usde["control"] == {"LISTED": 7}
    local = summary["E2023-03-USDC-SVB|binance-us|USDCUSD"]
    assert local["event"] == {"OBSERVED_LOCAL": 4} and local["control"] == {"NOT_LISTED": 7}
