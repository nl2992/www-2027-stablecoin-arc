"""Resource-package tests: the release builder is deterministic, the schema matches the files, the manifest matches the bytes."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

from www_resource import build as B

ROOT = Path(__file__).parents[1]
PARQUET_TYPES = {"string": ("string", "large_string"), "float64": ("double",), "int64": ("int64",), "bool": ("bool",)}


def _inputs(n: int = 240) -> dict:
    rng = np.random.default_rng(7)
    idx = pd.date_range("2022-04-01", periods=n, freq="h", tz="UTC", name="timestamp_utc")
    base = 11.0 + np.cumsum(rng.normal(0, 1e-3, n))
    unit = {}
    for v, off in (("bitfinex", 8e-4), ("coinbase", 0.0), ("bitstamp", 1e-4)):
        for a, k in (("BTC", 0.0), ("ETH", -3.0), ("LTC", -6.0), ("XRP", -9.0)):
            if v == "bitstamp" and a == "XRP":
                continue
            unit[f"{v}|{a}"] = base + k + off + rng.normal(0, 2e-4, n)
            unit[f"{v}|{a}_vol"] = rng.uniform(1, 2, n)
    unit["bitfinex|USDT"] = rng.normal(5e-4, 1e-4, n)
    unit["bitfinex|ETHBTC"] = rng.normal(-3, 1e-3, n)
    unit = pd.DataFrame(unit, index=idx)
    st = {}
    for m, off in (("bitstamp.USD", 0.0), ("coinbase.USD", 2e-4), ("binance.USDT", 9e-4)):
        st[f"{m}|BTC"] = base + off + rng.normal(0, 1e-4, n)
        st[f"{m}|BTC_vol"] = rng.uniform(1, 2, n)
        st[f"{m}|ETH"] = base - 3 + off + rng.normal(0, 1e-4, n)
        st[f"{m}|ETH_vol"] = rng.uniform(1, 2, n)
    st["side|USDT.USD@bitstamp"] = rng.normal(-3e-4, 5e-5, n)
    st["kraken|BTC"] = base
    stable = pd.DataFrame(st, index=idx)
    return {"unit_panel": unit, "stable_panel": stable, "kraken_usdt": pd.Series(rng.normal(0, 5e-5, n), index=idx),
            "hashes": {"synthetic": "x"}}


@pytest.fixture(scope="module")
def release(tmp_path_factory):
    a, b = tmp_path_factory.mktemp("rel_a"), tmp_path_factory.mktemp("rel_b")
    inp = _inputs()
    ma, mb = B.build(a, ROOT, inp), B.build(b, ROOT, _inputs())
    return a, b, ma, mb


def test_builder_is_deterministic(release):
    a, b, ma, mb = release
    assert ma == mb
    for name in ma["files"]:
        assert (a / name).read_bytes() == (b / name).read_bytes(), name


def test_schema_matches_files(release):
    a, _, ma, _ = release
    assert json.loads((a / "schema.json").read_text()) == B.schema_document()
    assert set(B.TABLES) == set(ma["tables"])
    for name, spec in B.TABLES.items():
        cols = list(spec["columns"])
        csv = pd.read_csv(a / f"{name}.csv")
        assert list(csv.columns) == cols, name
        schema = pq.read_schema(a / f"{name}.parquet")
        assert schema.names == cols, name
        for col, (dtype, _desc) in spec["columns"].items():
            t = str(schema.field(col).type)
            if dtype.startswith("datetime"):
                assert t.startswith("timestamp") and "UTC" in t, (name, col, t)
            else:
                assert t in PARQUET_TYPES[dtype], (name, col, t)
        pqt = pd.read_parquet(a / f"{name}.parquet")
        assert len(pqt) == len(csv) == ma["tables"][name]["rows"]
        assert not pqt.duplicated(spec["key"]).any(), f"{name}: primary key not unique"
        assert pqt.equals(pqt.sort_values(spec["key"], kind="mergesort").reset_index(drop=True)), f"{name}: not sorted"


def test_manifest_matches_bytes(release):
    a, _, ma, _ = release
    listed = {}
    for line in (a / "MANIFEST.sha256").read_text().splitlines():
        digest, name = line.split("  ", 1)
        listed[name] = digest
    on_disk = {p.name for p in a.iterdir() if p.is_file()} - {"MANIFEST.sha256", "manifest.json"}
    assert set(listed) == on_disk == set(ma["files"])
    for name, digest in listed.items():
        assert hashlib.sha256((a / name).read_bytes()).hexdigest() == digest == ma["files"][name]["sha256"]
        assert (a / name).stat().st_size == ma["files"][name]["bytes"]
    assert json.loads((a / "manifest.json").read_text()) == ma


def test_release_carries_differences_not_price_levels(release):
    a, *_ = release
    for name in ("unit_offsets_pairs", "unit_offsets_stablecoin", "anchor_usdt"):
        df = pd.read_csv(a / f"{name}.csv")
        for c in df.columns:
            assert not any(w in c for w in ("price", "close", "open", "volume", "_vol")), c
        num = df.select_dtypes("float").abs()
        assert num.max().max() < 1e3, name  # bps of differences; a log price would be ~11 (1e5 bps) or a level in dollars
    assert not any(p.name.startswith(("panel", "raw")) for p in a.iterdir())


def test_pair_table_sign_and_dispersion(release):
    a, *_ = release
    df = pd.read_csv(a / "unit_offsets_pairs.csv")
    bc = df[df["pair"] == "bitfinex-coinbase"]
    assert 5 < bc["b2_median_bps"].median() < 11  # constructed offset is 8 bps
    assert (bc["n_assets"] == 4).all()
    assert (df.loc[df["n_assets"] < 2, "dispersion_bps"].isna()).all()


def test_benchmark_tables_match_code_and_logs(release):
    a, *_ = release
    sp = pd.read_csv(a / "benchmark_splits.csv")
    assert set(sp["benchmark"]) == {"UNIT-TD", "FUSE", "STABLE"}
    assert sorted(sp[(sp.benchmark == "FUSE") & (sp.split == "test")]["name"]) == ["T1", "T2", "T3", "T4", "T5"]
    assert sorted(sp[(sp.benchmark == "STABLE") & (sp.split == "test")]["name"]) == ["X1", "X2", "X3", "X4"]
    res = pd.read_csv(a / "benchmark_results.csv")
    score = res[(res["metric"] == "test_score") & res["method"].isna()].set_index("benchmark")["value"]
    assert score["UNIT-TD"] == pytest.approx(0.846410) and score["FUSE"] == pytest.approx(1.062935) and score["STABLE"] == pytest.approx(1.455931)
    b2 = res[(res["metric"] == "test_score") & (res["method"] == "b2")]["value"].iloc[0]
    assert b2 > score["UNIT-TD"]  # the dev-tuned estimator did not beat b2 on the locked test
    assert len(pd.read_csv(a / "fiat_rail_labels.csv")) == 33
    doc = json.loads((a / "benchmarks.json").read_text())
    for bench, d in doc.items():
        assert hashlib.sha256((ROOT / d["locked_test_log"]).read_bytes()).hexdigest() == d["locked_test_log_sha256"]


def test_committed_hashes_match_a_rebuild_when_data_present(tmp_path):
    rec = ROOT / "resource" / "RELEASE_HASHES.json"
    if not rec.is_file():
        pytest.skip("no recorded hashes")
    needed = [ROOT / "data/derived/unit_td_panel.parquet", ROOT / "data/derived/stable_panel.parquet",
              ROOT / "data/raw/kraken_ohlcvt/USDTUSD_1.csv"]
    if not all(p.is_file() for p in needed):
        pytest.skip("local panels are git-ignored and absent")
    manifest = B.build(tmp_path, ROOT)
    recorded = json.loads(rec.read_text())["files"]
    for name, digest in recorded.items():
        if name.endswith((".csv", ".json")):  # parquet bytes can differ across pyarrow versions; CSV hashes are canonical
            assert manifest["files"][name]["sha256"] == digest, name
