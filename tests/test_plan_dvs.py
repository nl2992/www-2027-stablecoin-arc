import numpy as np
import pandas as pd
import pytest

from www_events.plan_dvs import (
    coverage_gate, covariates, dv1_contrast, dv3_recovery_minutes, longest_missing_run, usdt_stability_gate,
)
from www_events.runner import run_event


def idx(n, start="2024-03-01"):
    return pd.date_range(start, periods=n, freq="1min", tz="UTC")


def test_dv1_detects_shift_reports_p_value_and_is_deterministic():
    rng = np.random.default_rng(0)
    ref, ev = rng.normal(0, 2, 2000), rng.normal(0, 20, 2000)
    out = dv1_contrast(ev, ref, draws=200)
    assert out["estimate"] > 0 and out["ci_excludes_zero"] and out["p_value"] < 0.01
    assert out == dv1_contrast(ev, ref, draws=200)
    null = dv1_contrast(rng.normal(0, 2, 2000), ref, draws=200)
    assert not null["ci_excludes_zero"] and null["p_value"] > 0.05
    assert dv1_contrast(np.array([1.0]), ref)["estimate"] is None


def test_dv3_uses_only_trailing_data_and_censors():
    t = idx(24 * 60)
    dev = pd.Series(0.0, index=t)
    dev[(t >= "2024-03-01 02:00") & (t < "2024-03-01 04:00")] = -300.0
    dev[t == pd.Timestamp("2024-03-01 03:00", tz="UTC")] = -900.0  # extreme
    traded = pd.Series(True, index=t)
    out = dv3_recovery_minutes(dev, traded, t[0], t[0] + pd.Timedelta("6h"), t[-1] + pd.Timedelta("1min"))
    assert out["extreme_utc"].startswith("2024-03-01T03:00") and not out["censored"]
    # Trailing 6h median of |D| falls below 25 once fewer than half of the trailing minutes are stressed:
    # stress covers 02:00-04:00 (120 min), so this happens before 04:00 + some time; must be after the extreme.
    assert pd.Timestamp(out["recovered_utc"]) > pd.Timestamp(out["extreme_utc"])
    never = dv3_recovery_minutes(dev * 0 - 300, traded, t[0], t[0] + pd.Timedelta("6h"), t[-1])
    assert never["censored"] is True


def test_dv3_is_invariant_to_data_after_recovery():
    """No look-ahead: changing values after the recovery time cannot change the recovery time."""
    t = idx(24 * 60)
    base = pd.Series(0.0, index=t)
    base[(t >= "2024-03-01 01:00") & (t < "2024-03-01 02:00")] = -500.0
    traded = pd.Series(True, index=t)
    args = (t[0], t[0] + pd.Timedelta("3h"), t[-1])
    first = dv3_recovery_minutes(base, traded, *args)
    assert first["recovered_utc"].startswith("2024-03-01T03:0")  # 60 stressed minutes need >60 calm ones
    altered = base.copy()
    cutoff = max(args[1], pd.Timestamp(first["recovered_utc"]))
    altered[t > cutoff] = -1000.0  # change only data strictly after the event window and the recovery time
    assert dv3_recovery_minutes(altered, traded, *args)["recovered_utc"] == first["recovered_utc"]


def test_gates_and_covariates():
    present = pd.Series([True] * 40 + [False] * 60, index=idx(100))
    assert coverage_gate(present, 100) == {"present_share": 0.4, "passes": False}
    assert usdt_stability_gate(np.array([1.0, -3.0, 2.0]))["passes"]
    assert not usdt_stability_gate(np.array([50.0, -60.0]))["passes"]
    assert not usdt_stability_gate(np.array([np.nan]))["passes"]
    assert longest_missing_run(present) == 60
    cov = covariates(pd.Series(np.exp(np.linspace(0, 0.01, 100)), index=idx(100)), present, present)
    assert cov["missing_runs_over_15m"] == 1 and cov["traded_minute_share"] == 0.4
    assert cov["btc_realized_vol_bps_per_hour"] == pytest.approx(0.0, abs=1e-6)  # constant drift, no variance


def _grid(start, days, prefix, price=1.0):
    t = pd.date_range(start, periods=days * 1440, freq="1min", tz="UTC")
    f = pd.DataFrame(index=t)
    f[f"{prefix}_close"], f[f"{prefix}_volume"] = price, 1.0
    f[f"{prefix}_present"], f[f"{prefix}_traded"] = True, True
    return f


EVENT = {"id": "SYN", "reported_window_utc": {"start": "2024-03-10", "end": "2024-03-11"}}


def test_run_event_plan_block_uses_control_when_covered_and_gates_usdt():
    s = _grid("2024-02-01", 50, "s")
    s.loc[(s.index >= "2024-03-10 06:00") & (s.index < "2024-03-11 18:00"), "s_close"] = 0.97  # >50% of window
    q_bad = _grid("2024-02-01", 50, "q", price=0.995)  # USDT 50 bps off par: gate must fail
    out = run_event(EVENT, s, "s", "USDT", q_bad, "q")["plan"]
    assert out["dv1_reference_window"] == "control" and not out["dv1_reference_is_fallback"]
    assert out["dv1"]["estimate"] > 0 and not out["usdt_gate"]["passes"] and not out["confirmatory_eligible"]
    q_ok = _grid("2024-02-01", 50, "q", price=1.0)
    ok = run_event(EVENT, s, "s", "USDT", q_ok, "q")["plan"]
    assert ok["usdt_gate"]["passes"] and ok["confirmatory_eligible"]


def test_run_event_falls_back_to_baseline_and_flags_it():
    s = _grid("2024-03-01", 25, "s")  # control window (Feb) not covered
    out = run_event(EVENT, s, "s", "USD")["plan"]
    assert out["dv1_reference_window"] == "baseline" and out["dv1_reference_is_fallback"]
    assert not out["coverage_gates"]["control"]["passes"]


def test_bootstrap_p_value_is_floored_and_anchor_is_exploratory(tmp_path):
    from www_events.runner import analysis_status
    out = dv1_contrast(np.full(500, 100.0) + np.arange(500) % 3, np.zeros(500) + np.arange(500) % 3, draws=100)
    assert out["p_value"] == pytest.approx(0.01)
    freeze = tmp_path / "freeze.json"
    freeze.write_text('{"measured_before_freeze": ["E2023-03-USDC-SVB"]}')
    assert analysis_status("E2023-03-USDC-SVB", True, freeze) == "EXPLORATORY"
    assert analysis_status("E2024-01-TUSD", True, freeze) == "CONFIRMATORY"
    assert analysis_status("E2024-01-TUSD", False, freeze) == "DESCRIPTIVE_ONLY"
