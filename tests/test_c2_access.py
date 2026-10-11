from datetime import date

from www_c2.access import AccessRequest, SourceOffer, Verdict, evaluate_access


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
