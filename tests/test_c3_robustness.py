import numpy as np
import pandas as pd
import pytest

from www_c3.robustness import horizon_medians, horizon_profile, regime_difference, robustness_report


def series(values):
    idx = pd.date_range("2023-03-01", periods=len(values), freq="1min", tz="UTC")
    return pd.Series(np.asarray(values, float), index=idx)


def test_horizon_medians_use_observed_minutes_and_minimum_count():
    v = series([1, 100, 3, 5, 7, 9])
    obs = series([1, 0, 1, 1, 0, 0]).astype(bool)
    out = horizon_medians(v, obs, 3, min_obs=2)
    assert out.iloc[0] == 2.0  # median of 1 and 3; the unobserved 100 is ignored
    assert np.isnan(out.iloc[1])  # only one observed minute in the second bin
    with pytest.raises(ValueError):
        horizon_medians(v, obs, 0)


def test_horizon_half_life_is_reported_in_clock_minutes():
    rng = np.random.default_rng(0)
    x = np.zeros(6000)
    for t in range(1, len(x)):
        x[t] = 0.95 * x[t - 1] + rng.normal()
    v = series(x)
    prof = horizon_profile(v, series(np.ones(len(x))).astype(bool), pd.Series("r", index=v.index))
    one, five = prof["1"]["r"], prof["5"]["r"]
    assert one["half_life_to_parity_minutes"] == pytest.approx(np.log(0.5) / np.log(0.95), rel=0.2)
    assert five["bins"] == 1200
    assert five["half_life_to_parity_minutes"] == pytest.approx(one["half_life_to_parity_minutes"], rel=0.5)


def test_regime_difference_detects_shift_and_not_null_and_is_deterministic():
    rng = np.random.default_rng(1)
    a, same, wide = rng.normal(0, 2, 3000), rng.normal(0, 2, 3000), rng.normal(0, 8, 3000)
    shifted = regime_difference(a, wide, "median_abs", draws=200)
    assert shifted["estimate"] > 0 and shifted["ci_excludes_zero"]
    assert not regime_difference(a, same, "median_abs", draws=200)["ci_excludes_zero"]
    assert shifted == regime_difference(a, wide, "median_abs", draws=200)
    with pytest.raises(ValueError):
        regime_difference(a, wide, "mean", draws=10)


def test_robustness_report_runs_on_minimal_panel():
    n = 480
    idx = pd.date_range("2023-03-01", periods=n, freq="1min", tz="UTC")
    rng = np.random.default_rng(2)
    btc = 20000 * np.exp(np.cumsum(rng.normal(0, 1e-4, n)))
    regime = np.where(np.arange(n) < 240, "pre_crisis", "crisis")
    frame = pd.DataFrame({"timestamp_utc": idx, "regime": regime})
    for leg, price in {"btcusd": btc, "usdcusd": np.ones(n), "btcusdc": btc * np.exp(rng.normal(0, 1e-4, n)),
                       "usdtusd": np.ones(n), "btcusdt": btc}.items():
        frame[f"bnus_{leg}_close"] = price
        frame[f"bnus_{leg}_volume"] = 1.0
    frame["cb_btcusd_close"] = btc
    frame["cb_btcusd_volume"] = 1.0
    frame.loc[200:, "regime"] = np.where(np.arange(200, n) < 320, "crisis", np.where(np.arange(200, n) < 400, "recovery", "post"))
    out = robustness_report(frame, draws=20)
    assert set(out["horizons"]["usdc"]) == {"1", "5", "15", "60"}
    assert out["regime_differences"]["usdc"]["crisis_minus_pre_crisis"]["median_abs"]["bootstrap"]["draws"] == 20
    assert out["alternative_dollar_leg"]["usdc_coinbase_btcusd"]["pre_crisis"]["observed_minutes"] == 200
