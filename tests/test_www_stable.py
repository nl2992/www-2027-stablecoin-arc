"""STABLE harness on synthetic panels (no raw data needed)."""

import json
import re
import subprocess

import numpy as np
import pandas as pd
import pytest

from www_stable import baselines as B
from www_stable import harness as H
from www_stable import panel as P


def median_fuse(markets, meta, side):
    """The round-3 starting fuser (naive median, commit f9ef57d). The tracked fuser.py is now the loop's best fuser."""
    return pd.concat([markets[m]["BTC"] for m in sorted(markets)], axis=1).median(axis=1)

INDEX = pd.date_range("2020-01-01", "2020-07-05 23:00", freq="h", tz="UTC", name="timestamp_utc")
EPISODES = (
    P.Episode("S1", "dev", (("2020-02-15", "2020-03-31"),)),
    P.Episode("S3", "dev", (("2020-04-10", "2020-04-30"),), calm=True),
    P.Episode("X1", "test", (("2020-05-15", "2020-06-15"),)),
    P.Episode("X4", "test", (("2020-05-10", "2020-05-12"), ("2020-06-20", "2020-06-30")), calm=True),
)
DEPEG = ("2020-02-25", "2020-03-12")  # planted: the shared stablecoin unit loses up to 300 bps


def synthetic(depeg=True, seed=0, noise=1.0):
    """Five BTC markets: two in the dollar unit, three (different venues) in one stablecoin unit that depegs for 16 days.
    ETH in the same units, two stablecoin/USD side rates, Kraken-like reference = truth."""
    rng = np.random.default_rng(seed)
    n = len(INDEX)
    btc = np.log(30000.0) + np.cumsum(rng.normal(0, 3e-3, n))
    eth = np.log(2000.0) + np.cumsum(rng.normal(0, 3e-3, n))
    v = np.zeros(n)  # log value of one stablecoin unit in USD
    if depeg:
        m = (INDEX >= DEPEG[0]) & (INDEX < DEPEG[1])
        v[m] = -0.03 * np.sin(np.pi * np.linspace(0, 1, int(m.sum()))) ** 2
    flat = {}
    layout = {"coinbase.USD": (0 * v, True), "bitfinex.USD": (0 * v, True), "binance.USDT": (v, True),
              "binance_us.USDT": (v, False), "bitstamp.USDT": (v, False)}
    for key, (unit, has_eth) in layout.items():
        flat[f"{key}|BTC"] = btc - unit + rng.normal(0, noise, n) / 1e4
        flat[f"{key}|BTC_vol"] = rng.uniform(1, 2, n)
        if has_eth:
            flat[f"{key}|ETH"] = eth - unit + rng.normal(0, noise, n) / 1e4
            flat[f"{key}|ETH_vol"] = rng.uniform(1, 2, n)
    flat["side|USDT.USD@binance_us"] = v + rng.normal(0, 0.05, n) / 1e4
    flat["side|USDT.USD@bitstamp"] = v + rng.normal(0, 0.05, n) / 1e4
    flat["kraken|BTC"] = btc
    return pd.DataFrame(flat, index=INDEX)


def write(tmp_path, frame):
    path = tmp_path / "p.parquet"
    frame.to_parquet(path)
    path.with_name(P.META_PATH.name).write_text(json.dumps({"build_version": P.BUILD_VERSION}))
    return path


def load(tmp_path, frame, mode="dev"):
    return P.load_panel(mode, write(tmp_path, frame), EPISODES)


def run(tmp_path, fn, frame=None, mode="dev", seed=5):
    frame = synthetic() if frame is None else frame
    markets, side, ref, _ = load(tmp_path, frame, mode)
    return H.evaluate(markets, side, ref, lambda: fn, mode, seed, EPISODES, None)


def aware(markets, meta, side):
    """Unit-aware test fuser: the unit that is most often the quote of a side rate is the numeraire; convert and take the median."""
    pairs = []
    for c in side.columns:
        ab, _ = c.split("@")
        a, b = ab.split("/")
        pairs.append((c, a, b))
    num = max({b for _, _, b in pairs}, key=lambda u: sum(q == u for _, _, q in pairs))
    cols = []
    for m in sorted(markets):
        u = meta[m]["unit"]
        r = [side[c] for c, a, b in pairs if a == u and b == num]
        adj = 0.0 if u == num or not r else pd.concat(r, axis=1).median(axis=1).ffill()
        cols.append(markets[m]["BTC"] + adj)
    return pd.concat(cols, axis=1).median(axis=1)


def test_planted_unit_depeg_is_recovered_by_unit_aware_fuser_and_missed_by_naive_baselines(tmp_path):
    res = run(tmp_path, aware)
    m = res["episodes"]["S1"]["methods"]
    assert m["B0"]["mae"] > 20 and m["B1"]["mae"] > 20  # three of five markets share the depegged unit: median and VWAP fail
    assert m["B0"]["n50"] > 0 and m["B1"]["n50"] > 0
    assert m["fuser"]["mae"] < 0.2 * m["B0"]["mae"] and m["fuser"]["rel_e"] < 0.2
    assert m["B2"]["mae"] < 0.2 * m["B0"]["mae"]  # conversion at the side rate recovers it too
    assert m["oracle"]["mae"] < 5  # the two dollar markets
    assert res["episodes"]["S3"]["methods"]["fuser"]["rel_e"] <= 1.02 and res["placebo_ok"] and res["all_checks"]


def test_naive_median_fuser_equals_b0_and_passes_all_checks(tmp_path):
    res = run(tmp_path, median_fuse)
    assert res["all_checks"] and res["causal_ok"] and res["perm_ok"] and res["coverage_ok"] and res["placebo_ok"]
    assert res["score"] == pytest.approx(1.0)
    for e in res["episodes"].values():
        assert e["methods"]["fuser"]["mae"] == pytest.approx(e["methods"]["B0"]["mae"])
        assert set(e["methods"]) == {"fuser", *B.METHODS}


def test_leaky_fuser_fails_causal(tmp_path):
    res = run(tmp_path, lambda m, meta, side: median_fuse(m, meta, side).shift(-1))
    assert not res["causal_ok"] and not res["all_checks"]


def test_full_sample_statistic_fails_causal(tmp_path):
    res = run(tmp_path, lambda m, meta, side: median_fuse(m, meta, side) - median_fuse(m, meta, side).mean())
    assert not res["causal_ok"]


def test_label_dependent_fuser_fails_perm(tmp_path):
    named = lambda m, meta, side: m[sorted(m)[0]]["BTC"]  # noqa: E731 - whichever market got the lowest label
    res = run(tmp_path, named)
    assert not res["perm_ok"] and not res["all_checks"]


def test_withholding_output_cannot_lower_error_and_fails_coverage(tmp_path):
    def sparse(m, meta, side):
        out = median_fuse(m, meta, side)
        out.iloc[::10] = np.nan
        return out
    res = run(tmp_path, sparse)
    assert not res["coverage_ok"]
    assert res["episodes"]["S1"]["methods"]["fuser"]["mae"] == pytest.approx(res["episodes"]["S1"]["methods"]["B0"]["mae"])


def test_placebo_constraint_blocks_calm_losses(tmp_path):
    res = run(tmp_path, lambda m, meta, side: median_fuse(m, meta, side) + 5e-4, synthetic(depeg=False))  # 5 bps bias
    assert not res["placebo_ok"] and not res["all_checks"]


def test_dev_mode_loads_and_passes_no_test_rows(tmp_path):
    frame = synthetic()
    markets, side, ref, _ = load(tmp_path, frame, "dev")
    dev = [e for e in EPISODES if e.split == "dev"]
    lo = min(b[0] for e in dev for b in e.load_bounds())
    hi = max(b[1] for e in dev for b in e.load_bounds())
    test_lo = min(b[0] for e in EPISODES if e.split == "test" for b in e.bounds())
    for f in [*markets.values(), side, ref]:
        assert f.index.min() >= lo and f.index.max() <= hi and f.index.max() < test_lo
    seen = []

    def spy(m, meta, s):
        seen.extend(f.index.max() for f in m.values())
        seen.append(s.index.max())
        return median_fuse(m, meta, s)
    H.evaluate(markets, side, ref, lambda: spy, "dev", 3, EPISODES, None)
    assert seen and all(t < test_lo for t in seen)
    fm, _, _, _ = load(tmp_path, frame, "final")
    assert fm["coinbase.USD"].index.max() >= test_lo and fm["coinbase.USD"].index.min() > lo


def test_fuser_sees_only_anonymous_labels_and_never_the_reference(tmp_path):
    seen = []

    def spy(m, meta, side):
        seen.append((m, meta, side))
        return median_fuse(m, meta, side)
    run(tmp_path, spy)
    assert seen
    labels = []
    for m, meta, side in seen:
        assert all(re.fullmatch(r"m\d+", k) for k in m) and set(meta) == set(m)
        for k, f in m.items():
            assert re.fullmatch(r"u\d+", meta[k]["unit"]) and re.fullmatch(r"v\d+", meta[k]["venue"])
            assert set(f.columns) <= {"BTC", "BTC_vol", "ETH", "ETH_vol"}
            assert np.nanmax(np.abs(f[["BTC"]].to_numpy())) < 100  # the reference column is not among them
        assert all(re.fullmatch(r"u\d+/u\d+@v\d+", c) for c in side.columns)
        assert "kraken" not in " ".join(side.columns).lower()
        labels.append(sorted(meta[k]["unit"] for k in m))
    # markets that share a quote unit share its label (three stablecoin markets, two dollar markets)
    sizes = sorted(np.bincount(pd.factorize(np.array(labels[0]))[0]).tolist())
    assert sizes == [2, 3]


def test_dollar_unit_label_changes_with_the_seed(tmp_path):
    markets, side, ref, _ = load(tmp_path, synthetic())
    w = H.episode_windows(markets, side, ref, EPISODES[0])[0]
    usd_labels = set()
    for seed in range(12):
        _, meta, _ = H.fuser_inputs(w, seed)
        _, um, _ = H.anonymise(w, seed)
        usd_labels.add(um["USD"])
        assert {v["unit"] for v in meta.values()} == {um["USD"], um["USDT"]}
    assert len(usd_labels) > 1  # the fuser cannot learn which label is the dollar from the label itself


def test_only_markets_quoting_btc_in_the_rows_are_passed(tmp_path):
    frame = synthetic()
    frame.loc[:, "bitstamp.USDT|BTC"] = np.nan
    frame["lonely.USD|ETH"] = 5.0  # an ETH-only market is not a BTC source
    frame.loc[frame.index < "2020-04-01", "binance_us.USDT|BTC"] = np.nan
    markets, side, ref, _ = load(tmp_path, frame)
    w1 = H.episode_windows(markets, side, ref, EPISODES[0])[0]
    assert set(w1.markets) == {"coinbase.USD", "bitfinex.USD", "binance.USDT"}
    w2 = H.episode_windows(markets, side, ref, EPISODES[1])[0]
    assert set(w2.markets) == {"coinbase.USD", "bitfinex.USD", "binance.USDT", "binance_us.USDT"}


def test_final_refuses_without_unlock(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(P, "load_panel", lambda *a, **k: pytest.fail("data must not be loaded"))
    assert H.main(["--final"], root=tmp_path) == 2
    assert "FINAL_UNLOCK_STABLE" in capsys.readouterr().err


def test_final_with_unlock_scores_test_episodes_only_including_two_window_episode(tmp_path, capsys):
    (tmp_path / "autoresearch").mkdir()
    (tmp_path / "autoresearch" / "FINAL_UNLOCK_STABLE").write_text("x")
    code = H.main(["--final", "--seed", "2"], root=tmp_path, factory=lambda: aware,
                  panel_path=write(tmp_path, synthetic()), episodes=EPISODES)
    out = capsys.readouterr().out
    assert code == 0 and "test_score:" in out and "mae_X1_fuser:" in out and "mae_X4_fuser:" in out and "mae_S1_fuser" not in out
    assert "hours_X4: " in out


def test_cli_prints_keys(tmp_path, capsys):
    code = H.main(["--seed", "3", "--coverage"], factory=lambda: median_fuse, panel_path=write(tmp_path, synthetic()), episodes=EPISODES)
    out = capsys.readouterr().out
    assert code == 0
    for key in ("dev_score:", "causal_ok: True", "perm_ok: True", "static_ok: True", "coverage_ok: True", "placebo_ok: True",
                "all_checks: True", "mae_S1_fuser:", "p95_S3_B2:", "n25_S1_B4:", "n50_S3_oracle:", "rel_e_S1_B3:",
                "present_S1[0]_coinbase.USD:", "present_S1[0]_reference:"):
        assert key in out


def test_static_guard_catches_names_io_dates_and_foreign_imports():
    assert H.static_ok(H.FUSER_PATH.read_text())[0]
    for bad in ("x = open('f')", "import os", "# kraken", "a = 'bitfinex'", "t = '2020-01-01'", "from www_auto import x",
                "import scipy", "pd.read_csv('a')", "pd.Timestamp('2020')", "from www_stable import baselines",
                "u = 'USDT'", "u = 'usdc'", "# busd", "# TUSD peg", "x = 'fdusd'", "ust = 1", "c = 'Binance'", "k = 'coinbase'",
                "b = 'bitstamp'"):
        assert not H.static_ok("import numpy as np\n" + bad + "\n")[0], bad
    ok = "import numpy as np\n# a robust adjustment: we must trust the median, just in case\nx = 'dusty'\n"
    assert H.static_ok(ok)[0]
    assert H.static_ok("from __future__ import annotations\nimport numpy as np\nimport pandas as pd\n")[0]


def test_baseline_primitives():
    nan = np.nan
    p = np.array([[1.0, 2.0, 9.0], [1.0, nan, 9.0], [nan, nan, nan]])
    assert B.b0(p)[:2].tolist() == [2.0, 5.0] and np.isnan(B.b0(p)[2])
    v = np.array([[1.0, 1.0, 2.0], [1.0, 5.0, 3.0], [1.0, 1.0, 1.0]])
    assert B.b1(p, v)[0] == pytest.approx((1 + 2 + 18) / 4) and B.b1(p, v)[1] == pytest.approx((1 + 27) / 4) and np.isnan(B.b1(p, v)[2])
    names = ["a.USD", "b.USDT", "c.USD"]
    assert B.oracle(np.array([[1.0, 100.0, 3.0]]), names)[0] == 2.0
    assert np.isnan(B.oracle(np.array([[1.0, 100.0]]), ["b.USDT", "c.UST"])[0])


def test_conversion_rates_chain_through_the_quote_stablecoin_and_stop_after_24_hours():
    idx = pd.date_range("2020-01-01", periods=60, freq="h", tz="UTC")
    side = pd.DataFrame({"USDT.USD@binance_us": 0.001, "USDT.USD@bitstamp": 0.003, "UST.USDT@binance": -0.5,
                         "USDC.USD@bitstamp": -0.01}, index=idx)
    side.loc[idx[10]:, ["UST.USDT@binance", "USDC.USD@bitstamp"]] = np.nan
    r = B.usd_log_rates(side, ["USD", "USDT", "UST", "USDC", "BUSD"])
    assert r["USD"].tolist() == [0.0] * 60
    np.testing.assert_allclose(r["USDT"], 0.002)  # median of two venues
    np.testing.assert_allclose(r["UST"][:10], -0.498)  # chained: UST in USDT plus USDT in USD
    np.testing.assert_allclose(r["UST"][10:34], -0.498)  # carried at most 24 hours
    assert np.isnan(r["UST"][36])
    np.testing.assert_allclose(r["USDC"][:34], -0.01)
    assert np.isnan(r["USDC"][40])
    assert np.isnan(r["BUSD"]).all()  # no rate at all: B2 leaves that market unconverted


def test_b2_uses_the_side_rate_and_falls_back_to_unconverted():
    idx = pd.date_range("2020-01-01", periods=5, freq="h", tz="UTC")
    mk = {"a.USD": pd.DataFrame({"BTC": 10.0}, index=idx), "b.USDT": pd.DataFrame({"BTC": 10.3}, index=idx),
          "c.UST": pd.DataFrame({"BTC": 10.3}, index=idx), "d.USDT": pd.DataFrame({"BTC": 10.3}, index=idx)}
    side = pd.DataFrame({"USDT.USD@x": -0.3}, index=idx)
    out = B.b2(mk, sorted(mk), side, 5)
    # a.USD 10.0, b/d converted to 10.0, c.UST unconverted 10.3 -> median 10.0
    np.testing.assert_allclose(out, 10.0)


def test_baselines_are_causal(tmp_path):
    markets, side, ref, _ = load(tmp_path, synthetic())
    w = H.episode_windows(markets, side, ref, EPISODES[0])[0]
    full = B.all_baselines(w.markets, w.side, w.index)
    cut = 1100
    part = B.all_baselines({k: f.iloc[:cut] for k, f in w.markets.items()}, w.side.iloc[:cut], w.index[:cut])
    for m in B.METHODS:
        np.testing.assert_allclose(part[m].to_numpy(), full[m].iloc[:cut].to_numpy(), atol=1e-12, equal_nan=True, err_msg=m)


def test_frozen_round2_fuser_is_the_commit_914b3cb_file():
    try:
        shown = subprocess.run(["git", "show", "914b3cb:src/www_fuse/fuser.py"], capture_output=True, check=True, cwd=P.REPO).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git history unavailable")
    assert B.FROZEN_PATH.read_bytes() == shown


def test_frozen_fuser_runs_through_the_market_adapter(tmp_path):
    markets, side, ref, _ = load(tmp_path, synthetic())
    w = H.episode_windows(markets, side, ref, EPISODES[1])[0]
    out = B.all_baselines(w.markets, w.side, w.index)["B4"]
    assert out.notna().mean() > 0.99
    assert np.nanmax(np.abs(1e4 * (out - w.ref.reindex(w.index)))) < 100


def test_real_episodes_are_fixed_and_split_as_registered():
    names = {e.name: e for e in P.EPISODES}
    assert [e.name for e in P.episodes_for("dev")] == ["S1", "S2", "S3"]
    assert [e.name for e in P.episodes_for("final")] == ["X1", "X2", "X3", "X4"]
    assert names["S1"].windows == (("2022-05-01", "2022-05-31"),) and names["S2"].windows == (("2022-11-01", "2022-11-30"),)
    assert names["S3"].windows == (("2023-02-01", "2023-02-28"),) and names["S3"].calm and not names["S1"].calm
    assert names["X1"].windows == (("2023-03-08", "2023-03-20"),) and names["X2"].windows == (("2024-01-01", "2024-01-31"),)
    assert names["X3"].windows == (("2025-04-01", "2025-04-30"),)
    assert names["X4"].windows == (("2023-12-01", "2023-12-31"), ("2025-02-01", "2025-03-31"))
    lo, hi = names["S1"].load_bounds()[0]
    assert (hi - lo) == pd.Timedelta(hours=720 + 31 * 24 - 1)
    assert hi < min(b[0] for e in P.EPISODES if e.split == "test" for b in e.bounds())
    assert max(b[1] for e in P.EPISODES if e.split == "dev" for b in e.load_bounds()) < pd.Timestamp("2023-03-01", tz="UTC")
