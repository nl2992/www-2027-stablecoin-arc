import math

import numpy as np
import pandas as pd
import pytest

from www_c3.fragmentation import (
    ar1, ar1_to_parity, block_bootstrap_phi, build_wedges, excursions, fragmentation_report, half_life,
)


def minutes(n):
    return pd.date_range("2023-03-01", periods=n, freq="1min", tz="UTC")


def synthetic_ar1(phi, n=5000, seed=7):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + rng.normal()
    return x


def test_ar1_recovers_known_persistence_and_half_life():
    fit = ar1(synthetic_ar1(0.9))
    assert fit.phi == pytest.approx(0.9, abs=0.02)
    assert fit.half_life_minutes == pytest.approx(math.log(0.5) / math.log(fit.phi))


def test_parity_anchored_ar1_sees_persistent_level_shift_that_demeaned_ar1_misses():
    x = 50 + np.random.default_rng(3).normal(size=2000)  # iid noise around a 50 bps offset
    assert abs(ar1(x).phi) < 0.1
    assert ar1_to_parity(x).phi > 0.99


def test_half_life_undefined_without_mean_reversion():
    assert half_life(1.0) is None and half_life(-0.2) is None and half_life(None) is None
    assert half_life(0.5) == pytest.approx(1.0)


def test_mask_drops_pairs_spanning_unobserved_minutes():
    values = np.arange(10, dtype=float)
    mask = np.ones(10, bool)
    mask[4] = False
    assert ar1(values, mask).pairs == 7  # 9 pairs minus the two touching minute 4


def test_bootstrap_interval_covers_truth_and_is_deterministic():
    x = synthetic_ar1(0.8)
    first = block_bootstrap_phi(x, draws=200)
    assert first == block_bootstrap_phi(x, draws=200)
    assert first[0] < 0.8 < first[1]
    assert block_bootstrap_phi(x[:50], draws=10) is None


def test_excursions_judged_only_at_observed_minutes_and_censored_at_end():
    t = minutes(8)
    v = np.array([0, 30, 5, 40, 40, 0, 0, 60], dtype=float)
    observed = np.array([1, 1, 0, 1, 1, 1, 1, 1], bool)  # minute 2 (inside band) is unobserved
    eps = excursions(t, v, observed, 25)
    assert [(e.duration_minutes, e.end is None) for e in eps] == [(4.0, False), (0.0, True)]
    assert eps[0].peak_abs_bps == 40
    with pytest.raises(ValueError):
        excursions(t, v, observed, 0)


def panel(n=240):
    t = minutes(n)
    rng = np.random.default_rng(1)
    btcusd = 20000 * np.exp(np.cumsum(rng.normal(0, 1e-4, n)))
    usdcusd = np.where(np.arange(n) < n // 2, 1.0, 0.95)
    frame = pd.DataFrame({"timestamp_utc": t, "regime": np.where(np.arange(n) < n // 2, "pre", "crisis")})
    frame["bnus_btcusd_close"] = btcusd
    frame["bnus_usdcusd_close"] = usdcusd
    frame["bnus_btcusdc_close"] = btcusd / usdcusd  # parity holds exactly
    frame["bnus_usdtusd_close"] = 1.0
    frame["bnus_btcusdt_close"] = btcusd * 1.001  # constant 10 bps premium
    for leg in ("btcusd", "usdcusd", "btcusdc", "usdtusd", "btcusdt"):
        frame[f"bnus_{leg}_volume"] = 1.0
    frame.loc[::3, "bnus_usdcusd_volume"] = 0.0
    return frame


def test_wedges_are_fx_corrected_and_fresh_mask_requires_every_leg():
    w = build_wedges(panel())
    assert np.allclose(w["usdc_wedge_bps"], 0, atol=1e-6)
    assert np.allclose(w["usdt_wedge_bps"], 10_000 * math.log(1.001))
    assert not w["usdc_fresh"].iloc[0] and w["usdc_fresh"].iloc[1]
    assert w["usdt_fresh"].all()
    assert w["usdc_depeg_bps"].iloc[-1] == pytest.approx(10_000 * math.log(0.95))


def test_report_is_deterministic_and_separates_regimes_and_rules():
    p = panel()
    first = fragmentation_report(p, bootstrap_draws=20)
    assert first == fragmentation_report(p, bootstrap_draws=20)
    usdc = first["wedges"]["usdc"]
    assert set(usdc) == {"all_minutes_last_close", "all_legs_traded"}
    assert set(usdc["all_legs_traded"]) == {"full_sample", "pre", "crisis"}
    assert usdc["all_legs_traded"]["full_sample"]["observed_minutes"] == 160
    assert usdc["all_minutes_last_close"]["pre"]["observed_minutes"] == 120
    assert first["wedges"]["usdt"]["all_legs_traded"]["full_sample"]["thresholds"]["25.0"]["episodes"] == 0


def test_markdown_tables_are_rendered_from_report_values():
    from www_c3.cli import render_markdown
    report = {"input_sha256": "abc", **fragmentation_report(panel(), bootstrap_draws=20)}
    text = render_markdown(report)
    assert "sha256 abc" in text and "**USDC wedge" in text and "**USDT wedge" in text
    assert "| pre | " not in text  # only the documented regime labels are rendered
    assert "| full_sample | 160 |" in text
