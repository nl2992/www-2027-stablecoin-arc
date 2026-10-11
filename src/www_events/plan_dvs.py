"""Dependent variables, gates and covariates exactly as fixed in docs/PRE_ANALYSIS_PLAN.md."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from www_c3.robustness import _block_resample

SEED = 20230310
COVERAGE_MIN_SHARE = 0.5
USDT_STABLE_MAX_BPS = 10.0
RECOVERY_THRESHOLD_BPS = 25.0
RECOVERY_TRAILING = "6h"


def as_bool(series: pd.Series) -> pd.Series:
    """Missing -> False without pandas' deprecated object-dtype downcasting."""
    return series.astype("boolean").fillna(False).astype(bool)


def dv1_contrast(event_dev: np.ndarray, reference_dev: np.ndarray, *, block: int = 60, draws: int = 1000,
                 seed: int = SEED) -> dict[str, Any]:
    """DV1: median|D| event minus reference, with moving-block bootstrap CI and two-sided p-value."""
    a = np.abs(np.asarray(reference_dev, float))
    b = np.abs(np.asarray(event_dev, float))
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    if a.size < 2 or b.size < 2:
        return {"estimate": None, "reason": "fewer than two observations in a window"}
    rng = np.random.default_rng(seed)
    diffs = np.array([np.median(_block_resample(b, block, rng)) - np.median(_block_resample(a, block, rng))
                      for _ in range(draws)])
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    # A bootstrap p-value cannot resolve below 1/draws; report that floor rather than zero.
    p = min(1.0, max(2 * min((diffs <= 0).mean(), (diffs >= 0).mean()), 1 / draws))
    return {"estimate": float(np.median(b) - np.median(a)), "ci95": [float(lo), float(hi)],
            "se": float(diffs.std(ddof=1)), "p_value": float(p), "ci_excludes_zero": bool(lo > 0 or hi < 0),
            "bootstrap": {"block": block, "draws": draws, "seed": seed}}


def dv3_recovery_minutes(dev: pd.Series, traded: pd.Series, event_lo: pd.Timestamp, event_hi: pd.Timestamp,
                         horizon_hi: pd.Timestamp, *, threshold_bps: float = RECOVERY_THRESHOLD_BPS,
                         trailing: str = RECOVERY_TRAILING) -> dict[str, Any]:
    """Minutes from the event-window extreme until the trailing median |D| first drops below the threshold.

    The trailing median at time t uses traded minutes in (max(t - trailing, extreme), t] only, so no future
    data enter the recovery decision. The extreme itself is an ex-post property of the event window.
    Right-censored at ``horizon_hi`` (end of the recovery window).
    """
    obs = dev.where(traded.astype(bool)).abs().dropna()
    in_event = obs[(obs.index >= event_lo) & (obs.index < event_hi)]
    if in_event.empty:
        return {"recovery_minutes": None, "censored": None, "reason": "no traded minutes in event window"}
    t_extreme = in_event.idxmax()
    # Trailing window clipped at the extreme (amendment A1): calm minutes before the extreme must not
    # make recovery look instantaneous. Still uses only data at or before each evaluation time.
    since = obs[obs.index >= t_extreme]
    trailing_median = since.rolling(trailing).median()
    after = trailing_median[(trailing_median.index > t_extreme) & (trailing_median.index < horizon_hi)]
    below = after[after < threshold_bps]
    if below.empty:
        last = after.index[-1] if len(after) else t_extreme
        return {"extreme_utc": t_extreme.isoformat(), "extreme_abs_bps": float(in_event.max()),
                "recovery_minutes": float((last - t_extreme) / pd.Timedelta("1min")), "censored": True}
    return {"extreme_utc": t_extreme.isoformat(), "extreme_abs_bps": float(in_event.max()),
            "recovered_utc": below.index[0].isoformat(),
            "recovery_minutes": float((below.index[0] - t_extreme) / pd.Timedelta("1min")), "censored": False}


def coverage_gate(present: pd.Series, expected_minutes: int) -> dict[str, Any]:
    share = float(present.astype(bool).sum() / expected_minutes) if expected_minutes else 0.0
    return {"present_share": share, "passes": share >= COVERAGE_MIN_SHARE}


def usdt_stability_gate(usdt_usd_dev_bps: np.ndarray) -> dict[str, Any]:
    """Plan 5: USDT-quoted series are confirmatory only if median |USDT/USD dev| < 10 bps in the window."""
    a = np.abs(np.asarray(usdt_usd_dev_bps, float))
    a = a[np.isfinite(a)]
    if a.size == 0:
        return {"median_abs_bps": None, "passes": False, "reason": "no USDT/USD observations"}
    med = float(np.median(a))
    return {"median_abs_bps": med, "passes": med < USDT_STABLE_MAX_BPS}


def longest_missing_run(present: pd.Series) -> int:
    longest = run = 0
    for p in present.astype(bool).to_numpy():
        run = 0 if p else run + 1
        longest = max(longest, run)
    return longest


def covariates(btc_close: pd.Series | None, stable_present: pd.Series, stable_traded: pd.Series) -> dict[str, Any]:
    """Alternative-explanation covariates (plan 6), reported as associations only."""
    out: dict[str, Any] = {
        "traded_minute_share": float(stable_traded.astype(bool).mean()) if len(stable_traded) else None,
        "longest_missing_run_minutes": longest_missing_run(stable_present),
        "missing_runs_over_15m": int(_runs_over(stable_present, 15)),
    }
    if btc_close is not None and len(btc_close):
        r = np.log(btc_close.astype(float)).diff()
        out["btc_realized_vol_bps_per_hour"] = float(r.std(ddof=1) * np.sqrt(60) * 1e4) if r.notna().sum() > 2 else None
    return out


def _runs_over(present: pd.Series, minutes: int) -> int:
    count = run = 0
    for p in present.astype(bool).to_numpy():
        if p:
            count += run > minutes
            run = 0
        else:
            run += 1
    return count + (run > minutes)


def half_life_15m(values: pd.Series, observed: pd.Series, minutes: int = 15) -> float | None:
    """Parity-anchored AR(1) half-life (clock minutes) on ``minutes``-bin medians with >= minutes/5 observations."""
    from www_c3.fragmentation import ar1_to_parity
    from www_c3.robustness import horizon_medians

    bins = horizon_medians(values, observed.astype(bool), minutes, min_obs=max(3, minutes // 5)).to_numpy()
    fit = ar1_to_parity(bins, np.isfinite(bins))
    return None if fit.half_life_minutes is None else fit.half_life_minutes * minutes


def robustness_block(dev: pd.Series, traded: pd.Series, event_lo: pd.Timestamp, event_hi: pd.Timestamp,
                     reference: pd.Series, judged: tuple[pd.Timestamp, pd.Timestamp]) -> dict[str, Any]:
    """Plan section 7 robustness checks. Reported alongside the primary result; never used for status."""
    from .registry import r1_severity

    lo, hi = judged
    window = dev[(dev.index >= lo) & (dev.index < hi)]
    w_traded = as_bool(traded.reindex(window.index))
    price = np.exp(window.to_numpy(dtype=float) / 10_000)
    volume = np.where(w_traded.to_numpy(), 1.0, 0.0)
    r1_alt = {str(int(t)): r1_severity(window.index, price, volume, threshold_bps=t)["r1_pass"] for t in (50.0, 200.0)}
    in_event = (dev.index >= event_lo) & (dev.index < event_hi)
    ev, ev_obs = dev[in_event], as_bool(traded[in_event])
    trimmed = (ev.index >= event_lo + pd.Timedelta("6h")) & (ev.index < event_hi - pd.Timedelta("6h"))
    trim_vals = ev[trimmed & ev_obs.to_numpy()].to_numpy()
    dv1_trim = (dv1_contrast(trim_vals, reference.to_numpy()) if trim_vals.size >= 2
                else {"estimate": None, "reason": "event window shorter than 12 hours after trimming"})
    return {
        "r1_threshold_50": r1_alt["50"], "r1_threshold_200": r1_alt["200"],
        "dv1_trimmed_6h": dv1_trim,
        "half_life_D_minutes": {str(m): half_life_15m(ev, ev_obs, m) for m in (15, 30, 60)},
    }


def dv5_ratio(peg_dev: pd.Series, peg_obs: pd.Series, wedge: pd.Series, wedge_obs: pd.Series) -> dict[str, Any]:
    """DV5: half-life of D divided by half-life of W in the same window (H2 predicts > 1)."""
    hl_d, hl_w = half_life_15m(peg_dev, peg_obs), half_life_15m(wedge, wedge_obs)
    if hl_d is None or hl_w is None:
        return {"half_life_D_minutes": hl_d, "half_life_W_minutes": hl_w, "ratio": None,
                "reason": "a half-life is undefined (no mean reversion or too few bins)"}
    return {"half_life_D_minutes": hl_d, "half_life_W_minutes": hl_w, "ratio": hl_d / hl_w,
            "h2_direction": hl_d > hl_w}
