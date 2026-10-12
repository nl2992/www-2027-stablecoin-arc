import numpy as np
import pandas as pd
import pytest

from www_c0.quality import (
    age_since_observation_minutes,
    audit_panel,
    audit_parquet,
    parity_wedge_bps,
    require_quote_direction,
    validate_utc_minutes,
)


def fixture_panel() -> pd.DataFrame:
    return pd.DataFrame({
        "timestamp_utc": pd.date_range("2023-03-01", periods=3, freq="1min", tz="UTC"),
        "bnus_btcusdc_close": [10_000.0, 10_100.0, 10_100.0],
        "bnus_btcusdc_volume": [1.0, 0.0, 0.0],
        "bnus_usdcusd_close": [0.99, 0.99, 0.99],
        "bnus_usdcusd_volume": [1.0, 0.0, 0.0],
        "bnus_btcusd_close": [9_900.0, 10_000.0, 10_000.0],
        "bnus_btcusd_volume": [1.0, 2.0, 0.0],
    })


def test_parity_wedge_uses_dollars_per_stablecoin():
    assert float(parity_wedge_bps(10_000, 0.99, 9_900)) == pytest.approx(0, abs=1e-8)
    assert float(parity_wedge_bps(10_000, 0.99, 10_000)) == pytest.approx(10_000 * np.log(0.99))
    with pytest.raises(ValueError):
        parity_wedge_bps(10_000, -0.99, 9_900)


def test_quote_direction_rejects_inverse_pair():
    require_quote_direction("USDCUSD", base="USDC", quote="USD")
    with pytest.raises(ValueError):
        require_quote_direction("USDUSDC", base="USDC", quote="USD")


def test_time_validation_rejects_naive_duplicate_and_subminute():
    with pytest.raises(ValueError, match="timezone"):
        validate_utc_minutes(pd.Series([pd.Timestamp("2023-03-01")]))
    with pytest.raises(ValueError, match="duplicate"):
        validate_utc_minutes(pd.Series([pd.Timestamp("2023-03-01T00:00Z")] * 2))
    with pytest.raises(ValueError, match="minute aligned"):
        validate_utc_minutes(pd.Series([pd.Timestamp("2023-03-01T00:00:01Z")]))


def test_age_since_explicit_observation_and_trade_proxy():
    frame = fixture_panel()
    timestamps = validate_utc_minutes(frame["timestamp_utc"])
    assert age_since_observation_minutes(timestamps, pd.Series([False, True, False])) == [None, 0, 1]
    result = audit_panel(frame, stale_after_minutes=1)
    stat = result["pair_coverage"]["bnus_btcusdc"]
    assert stat["close_present_without_trade_minutes"] == 2
    assert stat["max_age_since_positive_volume_minutes"] == 2
    assert stat["minutes_over_stale_threshold_by_volume_proxy"] == 1
    assert result["missing_expected_minutes"] == 30_237


def test_invalid_price_is_flagged_and_missing_file_is_explicit(tmp_path):
    frame = fixture_panel()
    frame.loc[1, "bnus_btcusd_close"] = 0.0
    assert audit_panel(frame)["pair_coverage"]["bnus_btcusd"]["invalid_nonpositive_close"] == 1
    assert audit_parquet(tmp_path / "missing.parquet")["status"] == "NOT_AVAILABLE"


def test_missing_minute_is_counted():
    frame = fixture_panel().drop(index=1).reset_index(drop=True)
    result = audit_panel(frame)
    assert result["non_minute_gaps"] == 1
    assert result["missing_expected_minutes"] == 30_238
    assert result["validation"]["expected_grid_complete"] is False


def test_nonpositive_price_fails_validation():
    frame = fixture_panel()
    frame.loc[1, "bnus_btcusd_close"] = -1
    result = audit_panel(frame)
    assert result["validation"]["invalid_nonpositive_close_count"] == 1
    assert result["validation"]["invalid_prices_pass"] is False


def test_unsorted_timestamps_are_rejected():
    frame = fixture_panel().iloc[::-1]
    with pytest.raises(ValueError, match="increasing"):
        audit_panel(frame)
