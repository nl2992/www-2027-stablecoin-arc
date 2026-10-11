import hashlib
import zipfile

import numpy as np
import pandas as pd
import pytest

from www_events.runner import load_binance_months, run_event, usd_price, window_bounds


EVENT = {"id": "SYN", "reported_window_utc": {"start": "2024-03-10", "end": "2024-03-11"}}


def grid(start, days, prefix, price=1.0, traded=True):
    idx = pd.date_range(start, periods=days * 1440, freq="1min", tz="UTC")
    f = pd.DataFrame(index=idx)
    f[f"{prefix}_close"] = price
    f[f"{prefix}_volume"] = 1.0 if traded else 0.0
    f[f"{prefix}_present"] = True
    f[f"{prefix}_traded"] = traded
    return f


def test_window_bounds_are_half_open_whole_days():
    lo, hi = window_bounds({"start": "2024-03-10", "end": "2024-03-11"})
    assert (hi - lo) == pd.Timedelta("2D")


def test_usdt_quoted_series_is_relative_without_fx_leg_and_usd_with_it():
    s = grid("2024-03-01", 1, "s", price=0.99)
    q = grid("2024-03-01", 1, "q", price=1.002)
    assert usd_price(s, "s", "USDT")["basis"].iloc[0] == "USDT_RELATIVE"
    conv = usd_price(s, "s", "USDT", q, "q")
    assert conv["basis"].iloc[0] == "USD_VIA_USDT"
    assert conv["price"].iloc[0] == pytest.approx(0.99 * 1.002)


def test_fx_leg_untraded_minutes_do_not_count_as_observed():
    s = grid("2024-03-01", 1, "s")
    q = grid("2024-03-01", 1, "q", traded=False)
    assert not usd_price(s, "s", "USDT", q, "q")["traded"].any()


def test_run_event_detects_synthetic_depeg_and_reports_coverage():
    s = grid("2024-02-01", 50, "s")  # covers control (Feb 6-12) through recovery
    crash = (s.index >= "2024-03-10 12:00") & (s.index < "2024-03-10 14:00")
    s.loc[crash, "s_close"] = 0.95
    out = run_event(EVENT, s, "s", "USD")
    assert out["r1"]["r1_pass"] and out["r1"]["severe_class"]
    assert out["coverage_ok"] and out["windows"]["control"]["coverage_complete"]
    ev = out["windows"]["event"]["diagnostics"]
    assert ev["max_abs_dev_bps"] == pytest.approx(10_000 * -np.log(0.95))
    assert out["windows"]["baseline"]["diagnostics"]["max_abs_dev_bps"] == 0


def test_run_event_flags_missing_windows_and_relative_basis():
    s = grid("2024-03-05", 10, "s")  # baseline (Mar 2-8) only partly covered, no control
    out = run_event(EVENT, s, "s", "USDT")
    assert not out["coverage_ok"]
    assert out["windows"]["control"]["covered_minutes"] == 0
    assert "warning" in out


def _archive(tmp_path, symbol, month, times_ms):
    name = f"{symbol}-1m-{month}.zip"
    path = tmp_path / name
    rows = "\n".join(f"{t},1,1.001,0.999,1,5,{t + 59_999},5,3,1,1,0" for t in times_ms) + "\n"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(name.replace(".zip", ".csv"), rows)
    (tmp_path / (name + ".CHECKSUM")).write_text(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {name}\n")


def test_load_binance_months_verifies_checksums_and_builds_gap_preserving_grid(tmp_path):
    t0 = 1_709_251_200_000  # 2024-03-01T00:00Z
    _archive(tmp_path, "USDEUSDT", "2024-03", [t0, t0 + 60_000, t0 + 180_000])
    g, prov = load_binance_months(tmp_path, "USDEUSDT", "binance_usdeusdt")
    assert len(g) == 1440 and prov["gaps"]["missing_minutes"] == 1437
    assert prov["files"][0]["time_unit"] == "ms"
    (tmp_path / "USDEUSDT-1m-2024-03.zip.CHECKSUM").write_text("0" * 64 + "  USDEUSDT-1m-2024-03.zip\n")
    with pytest.raises(ValueError, match="mismatch"):
        load_binance_months(tmp_path, "USDEUSDT", "binance_usdeusdt")
