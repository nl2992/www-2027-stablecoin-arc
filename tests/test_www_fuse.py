"""FUSE harness on synthetic panels (no raw data needed)."""

import json
import re

import numpy as np
import pandas as pd
import pytest

from www_fuse import baselines as B
from www_fuse import harness as H
from www_fuse import panel as P
from www_fuse.fuser import fuse as median_fuse

INDEX = pd.date_range("2020-01-01", "2020-07-05 23:00", freq="h", tz="UTC", name="timestamp_utc")
EPISODES = (
    P.Episode("D1", "dev", "2020-02-15", "2020-03-31"),
    P.Episode("D2", "dev", "2020-04-10", "2020-04-30", calm=True),
    P.Episode("T1", "test", "2020-05-15", "2020-06-15"),
)
ASSETS = ["BTC", "ETH", "LTC", "XLM", "USDT"]


def synthetic(offset_bps=0.0, noise=1.0, seed=0, four=False):
    """Flat panel: bitfinex carries a slowly drifting unit offset on every item; bitstamp has no ETH; reference = truth."""
    rng = np.random.default_rng(seed)
    n = len(INDEX)
    latent = {a: np.log(100.0) + np.cumsum(rng.normal(0, 3e-3, n)) for a in ASSETS}
    unit = offset_bps + np.cumsum(rng.normal(0, 0.5, n))
    flat = {}
    layout = {"bitfinex": (ASSETS, unit), "coinbase": (ASSETS, 0 * unit), "bitstamp": (["BTC", "LTC", "XLM", "USDT"], 0 * unit)}
    if four:
        layout["binance_us"] = (["BTC", "USDT"], 0 * unit)
    for src, (assets, u) in layout.items():
        for a in assets:
            flat[f"{src}|{a}"] = latent[a] + (u + rng.normal(0, noise, n)) / 1e4
            flat[f"{src}|{a}_vol"] = rng.uniform(1, 2, n)
    for a in ("BTC", "ETH"):
        flat[f"kraken|{a}"] = latent[a] + 12345.0  # distinctive: must never reach a fuser (checked via the truth itself below)
    frame = pd.DataFrame(flat, index=INDEX)
    truth = {a: latent[a] for a in ("BTC", "ETH")}
    return frame, truth


def write(tmp_path, frame):
    path = tmp_path / "p.parquet"
    frame.to_parquet(path)
    path.with_name(P.META_PATH.name).write_text(json.dumps({"build_version": P.BUILD_VERSION}))
    return path


def load(tmp_path, frame, mode="dev"):
    return P.load_panel(mode, write(tmp_path, frame), EPISODES)


def run(tmp_path, fn, frame=None, mode="dev", seed=5):
    frame = synthetic()[0] if frame is None else frame
    sources, ref, _ = load(tmp_path, frame, mode)
    return H.evaluate(sources, ref, lambda: fn, mode, seed, EPISODES, None)


def truth_reference(frame, truth):
    out = frame.copy()
    for a in ("BTC", "ETH"):
        out[f"kraken|{a}"] = truth[a]
    return out


def test_planted_unit_offset_is_recovered_by_unit_aware_fuser(tmp_path):
    frame, truth = synthetic(offset_bps=150.0)
    res = run(tmp_path, median_fuse, truth_reference(frame, truth))
    for ep in ("D1", "D2"):
        m = res["episodes"][ep]["methods"]
        # ETH has two sources (one offset): the median is off by about half the offset; the unit-aware fuser removes it
        assert m["median"]["mae"] > 30
        assert m["unit_aware"]["mae"] < 0.2 * m["median"]["mae"]
        assert m["oracle"]["mae"] < 5


def test_median_fuser_equals_median_baseline_and_passes_all_checks(tmp_path):
    frame, truth = synthetic()
    res = run(tmp_path, median_fuse, truth_reference(frame, truth))
    assert res["all_checks"] and res["causal_ok"] and res["perm_ok"] and res["coverage_ok"] and res["calm_ok"]
    assert res["score"] == pytest.approx(1.0)
    for ep, e in res["episodes"].items():
        assert e["methods"]["fuser"]["mae"] == pytest.approx(e["methods"]["median"]["mae"])
        assert set(e["methods"]) == {"fuser", *B.METHODS}


def test_leaky_fuser_fails_causal(tmp_path):
    leaky = lambda panel, items: median_fuse(panel, items).shift(-1)  # noqa: E731
    res = run(tmp_path, leaky)
    assert not res["causal_ok"] and not res["all_checks"]


def test_full_sample_statistic_fails_causal(tmp_path):
    stat = lambda panel, items: median_fuse(panel, items) - median_fuse(panel, items).mean()  # noqa: E731
    assert not run(tmp_path, stat)["causal_ok"]


def test_name_dependent_fuser_fails_perm(tmp_path):
    def named(panel, items):
        key = sorted(panel)[0]
        return pd.DataFrame({a: panel[key][a] if a in panel[key].columns else np.nan for a in items})
    res = run(tmp_path, named)
    assert not res["perm_ok"] and not res["all_checks"]


def test_withholding_output_cannot_lower_error_and_fails_coverage(tmp_path):
    def sparse(panel, items):
        out = median_fuse(panel, items)
        out.iloc[::10] = np.nan
        return out
    res = run(tmp_path, sparse)
    assert not res["coverage_ok"]
    assert res["episodes"]["D1"]["methods"]["fuser"]["mae"] == pytest.approx(res["episodes"]["D1"]["methods"]["median"]["mae"])


def test_calm_constraint_blocks_calm_losses(tmp_path):
    worse = lambda panel, items: median_fuse(panel, items) + 5e-4  # 5 bps bias  # noqa: E731
    frame, truth = synthetic()
    res = run(tmp_path, worse, truth_reference(frame, truth))
    assert not res["calm_ok"] and not res["all_checks"]


def test_dev_mode_loads_and_passes_no_test_rows(tmp_path):
    frame, _ = synthetic()
    sources, ref, _ = load(tmp_path, frame, "dev")
    lo = min(e.load_bounds()[0] for e in EPISODES if e.split == "dev")
    hi = max(e.bounds()[1] for e in EPISODES if e.split == "dev")
    test_lo = min(e.bounds()[0] for e in EPISODES if e.split == "test")
    for f in [*sources.values(), ref]:
        assert f.index.min() >= lo and f.index.max() <= hi and f.index.max() < test_lo
    seen = []

    def spy(panel, items):
        for f in panel.values():
            seen.append((f.index.min(), f.index.max()))
        return median_fuse(panel, items)
    H.evaluate(sources, ref, lambda: spy, "dev", 3, EPISODES, None)
    assert seen and all(b < test_lo for _, b in seen)
    final, _, _ = load(tmp_path, frame, "final")
    assert final["bitfinex"].index.max() >= test_lo and final["bitfinex"].index.min() > lo


def test_kraken_columns_never_reach_the_fuser(tmp_path):
    frame, _ = synthetic(four=True)
    seen = []

    def spy(panel, items):
        seen.append(panel)
        return median_fuse(panel, items)
    sources, ref, _ = load(tmp_path, frame)
    assert set(ref.columns) == {"BTC", "ETH"}
    H.evaluate(sources, ref, lambda: spy, "dev", 4, EPISODES, None)
    assert seen
    for panel in seen:
        assert all(re.fullmatch(r"s\d+", k) for k in panel)
        for f in panel.values():
            assert set(f.columns) <= {c for a in ASSETS for c in (a, a + "_vol")}
            assert np.nanmax(np.abs(f[[c for c in f.columns if not c.endswith("_vol")]].to_numpy())) < 100  # reference sits near 12345


def test_binance_like_source_appears_only_where_it_quotes(tmp_path):
    frame, _ = synthetic(four=True)
    frame.loc[frame.index < "2020-04-01", ["binance_us|BTC", "binance_us|USDT"]] = np.nan
    sources, _, _ = load(tmp_path, frame)
    assert set(H.episode_slice(sources, EPISODES[0])) == {"bitfinex", "coinbase", "bitstamp"}
    assert set(H.episode_slice(sources, EPISODES[1])) == {"bitfinex", "coinbase", "bitstamp", "binance_us"}


def test_final_refuses_without_unlock(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(P, "load_panel", lambda *a, **k: pytest.fail("data must not be loaded"))
    assert H.main(["--final"], root=tmp_path) == 2
    assert "FINAL_UNLOCK_FUSE" in capsys.readouterr().err


def test_final_with_unlock_scores_test_episodes_only(tmp_path):
    frame, truth = synthetic()
    (tmp_path / "autoresearch").mkdir()
    (tmp_path / "autoresearch" / "FINAL_UNLOCK_FUSE").write_text("x")
    code = H.main(["--final", "--seed", "2"], root=tmp_path, factory=lambda: median_fuse,
                  panel_path=write(tmp_path, truth_reference(frame, truth)), episodes=EPISODES)
    assert code == 0


def test_cli_prints_keys(tmp_path, capsys):
    frame, truth = synthetic()
    code = H.main(["--seed", "3", "--coverage"], factory=lambda: median_fuse, panel_path=write(tmp_path, frame), episodes=EPISODES)
    out = capsys.readouterr().out
    assert code == 0
    for key in ("dev_score:", "causal_ok: True", "perm_ok: True", "static_ok: True", "coverage_ok: True", "calm_ok: True",
                "all_checks: True", "mae_D1_fuser:", "p95_D2_crh:", "n25_D1_gtm:", "n50_D2_oracle:", "rel_e_D1_unit_aware:",
                "present_D1_kraken:"):
        assert key in out


def test_static_guard():
    assert H.static_ok(H.FUSER_PATH.read_text())[0]
    for bad in ("x = open('f')", "import os", "# kraken", "a = 'bitfinex'", "t = '2020-01-01'", "from www_auto import x",
                "import scipy", "pd.read_csv('a')", "pd.Timestamp('2020')"):
        assert not H.static_ok("import numpy as np\n" + bad + "\n")[0], bad
    assert H.static_ok("from __future__ import annotations\nimport numpy as np\nimport pandas as pd\n")[0]


def test_array_baselines():
    nan = np.nan
    p = np.array([[1.0, 2.0, 9.0, 3.0], [1.0, 2.0, 9.0, nan], [5.0, nan, nan, nan], [nan] * 4])
    v = np.ones_like(p)
    assert B.median(p, v)[:3].tolist() == [2.5, 2.0, 5.0] and np.isnan(B.median(p, v)[3])
    assert B.trimmed(p, v)[:3].tolist() == [2.5, 2.0, 5.0]  # four quotes: drop 1 and 9 -> mean(2, 3); three quotes: median
    assert B.drop_deviant(p, v)[:3].tolist() == [2.0, 1.5, 5.0]
    w = np.array([[1.0, 3.0, nan]])
    assert B.vwap(w, np.array([[1.0, 3.0, 5.0]]))[0] == pytest.approx(2.5)
    assert B.oracle(np.array([[1.0, 3.0, 100.0]]), ["coinbase", "bitstamp", "bitfinex"])[0] == 2.0


def test_baseline_fusers_are_causal(tmp_path):
    frame, _ = synthetic(offset_bps=80.0, four=True)
    sources, _, _ = load(tmp_path, frame)
    sl = H.episode_slice(sources, EPISODES[0])
    full = B.all_baselines(sl, ["BTC", "ETH"], 720)
    cut = 1500
    part = B.all_baselines({k: f.iloc[:cut] for k, f in sl.items()}, ["BTC", "ETH"], 720)
    for m in B.METHODS:
        a, b = part[m].to_numpy(), full[m].iloc[:cut].to_numpy()
        np.testing.assert_allclose(a, b, atol=1e-12, equal_nan=True, err_msg=m)


def test_real_episodes_are_fixed_and_disjoint_by_split():
    names = {e.name: e for e in P.EPISODES}
    assert [e.name for e in P.episodes_for("dev")] == ["D1", "D2", "D3"]
    assert [e.name for e in P.episodes_for("final")] == ["T1", "T2", "T3", "T4", "T5"]
    assert (names["D1"].start, names["D1"].end) == ("2017-03-01", "2017-08-31")
    assert names["T2"].start == "2023-05-01" and names["T4"].end == "2023-03-20"
    idx = pd.date_range("2022-01-01", "2023-12-31 23:00", freq="h", tz="UTC")
    m = names["T5"].scored_mask(idx)
    assert not m[(idx >= "2022-11-10") & (idx < "2022-11-11")].any() and m[(idx >= "2022-12-01") & (idx < "2022-12-02")].all()
