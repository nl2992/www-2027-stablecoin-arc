from datetime import date
from decimal import Decimal

from www_c2.access import AccessRequest, SourceOffer, Verdict, estimate_orderbook_transfer_cost, evaluate_access


def request():
    return AccessRequest(date(2023, 3, 10), date(2023, 3, 12), "binance-us", frozenset({"BTCUSD"}), "csv")


def offer(start=date(2022, 10, 11), *, delivery=frozenset({"csv"}), symbols=frozenset({"BTCUSD"}), **kwargs):
    defaults = dict(coverage_start=start, coverage_end=date(2026, 10, 11), venues=frozenset({"binance-us"}),
                    symbols=symbols, delivery=delivery, authenticated=True, licensed=True,
                    access_window_verified=True, exact_files_verified=False)
    defaults.update(kwargs)
    return SourceOffer("synthetic", **defaults)


def test_four_year_annual_window_covers_march_2023_but_files_still_unknown():
    result = evaluate_access(request(), offer())
    assert result.verdict == Verdict.UNKNOWN
    assert any("not been obtained" in reason for reason in result.reasons)


def test_quarterly_window_does_not_cover_march_2023():
    result = evaluate_access(request(), offer(start=date(2025, 10, 11)))
    assert result.verdict == Verdict.INSUFFICIENT


def test_monthly_window_does_not_cover_march_2023():
    result = evaluate_access(request(), offer(start=date(2026, 6, 11)))
    assert result.verdict == Verdict.INSUFFICIENT


def test_wrong_venue_and_missing_symbol_are_rejected():
    result = evaluate_access(request(), offer(venues=frozenset({"binance"}), symbols=frozenset({"ETHUSD"})))
    assert result.verdict == Verdict.INSUFFICIENT
    assert len(result.reasons) >= 2


def test_raw_replay_not_included_in_academic_csv_offer():
    raw_request = AccessRequest(date(2023, 3, 10), date(2023, 3, 12), "binance-us", frozenset({"BTCUSD"}), "raw_replay")
    assert evaluate_access(raw_request, offer()).verdict == Verdict.INSUFFICIENT


def test_unverified_metadata_does_not_count_as_coverage():
    result = evaluate_access(request(), offer(coverage_start=None, coverage_end=None, access_window_verified=False))
    assert result.verdict == Verdict.UNKNOWN


def test_unauthorized_or_unlicensed_source_is_blocked():
    result = evaluate_access(request(), offer(authenticated=True, licensed=False))
    assert result.verdict == Verdict.BLOCKED


def test_invalid_date_interval_raises():
    bad = AccessRequest(date(2023, 3, 12), date(2023, 3, 10), "binance-us", frozenset({"BTCUSD"}), "csv")
    try:
        evaluate_access(bad, offer())
    except ValueError as exc:
        assert "on or before" in str(exc)
    else:
        raise AssertionError("invalid interval accepted")


def test_binance_com_coverage_cannot_satisfy_binance_us_request():
    binance_com = offer(venues=frozenset({"binance"}), exact_files_verified=True)
    assert evaluate_access(request(), binance_com).verdict == Verdict.INSUFFICIENT


def test_generic_l2_product_without_exact_dates_remains_unknown():
    coinapi_candidate = offer(access_window_verified=False, exact_files_verified=False,
                              capabilities=frozenset({"incremental_l2", "snapshot_l2"}))
    l2_request = AccessRequest(date(2023, 3, 10), date(2023, 3, 12), "binance-us",
                               frozenset({"BTCUSD"}), "csv", frozenset({"incremental_l2"}))
    assert evaluate_access(l2_request, coinapi_candidate).verdict == Verdict.UNKNOWN


def test_snapshot_only_offer_cannot_satisfy_incremental_l2_request():
    snapshot_only = offer(capabilities=frozenset({"snapshot_l2"}))
    l2_request = AccessRequest(date(2023, 3, 10), date(2023, 3, 12), "binance-us",
                               frozenset({"BTCUSD"}), "csv", frozenset({"incremental_l2"}))
    result = evaluate_access(l2_request, snapshot_only)
    assert result.verdict == Verdict.INSUFFICIENT
    assert any("incremental_l2" in reason for reason in result.reasons)


def test_missing_native_sequence_capability_cannot_verify_continuity():
    offer_without_sequence = offer(capabilities=frozenset({"incremental_l2", "snapshot_l2"}))
    request_with_sequence = AccessRequest(date(2023, 3, 10), date(2023, 3, 12), "binance-us",
                                          frozenset({"BTCUSD"}), "csv",
                                          frozenset({"incremental_l2", "native_sequence_ids"}))
    assert evaluate_access(request_with_sequence, offer_without_sequence).verdict == Verdict.INSUFFICIENT
    assert evaluate_access(request_with_sequence, offer(capabilities=None)).verdict == Verdict.UNKNOWN


def test_unknown_licensing_never_produces_sufficient_access():
    result = evaluate_access(request(), offer(licensed=None, exact_files_verified=True))
    assert result.verdict == Verdict.UNKNOWN


def test_transfer_price_requires_measured_size_and_respects_daily_tiers():
    assert estimate_orderbook_transfer_cost(None) is None
    assert estimate_orderbook_transfer_cost(Decimal("0.5")) == Decimal("4.0")
    assert estimate_orderbook_transfer_cost(Decimal("12")) == Decimal("48")


def test_negative_transfer_size_is_rejected():
    try:
        estimate_orderbook_transfer_cost(Decimal("-0.1"))
    except ValueError as exc:
        assert "negative" in str(exc)
    else:
        raise AssertionError("negative size accepted")
