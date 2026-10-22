"""Build the DERIVED-series release for the WWW 2027 Resource track.

    uv run python -m www_resource.build                       # writes resource/release/ (git-ignored)
    uv run python -m www_resource.build --record resource/RELEASE_HASHES.json   # also commits the hashes

Inputs are the committed pipeline's cached hourly panels (``www_auto.panel``, ``www_stable.panel``; rebuilt from the
manifest-verified raw files when absent), Kraken's USDT/USD minute file, ``configs/fiat_rail_labels.json``, the benchmark
episode definitions in the three panel modules, and the locked-test logs ``autoresearch/final_*.log``.

Every price-level column is removed: the release holds only differences between venues (basis points), cross-asset
medians and dispersions, benchmark definitions and recorded results. No raw exchange price (level) is written.
Files are written deterministically (sorted rows, fixed rounding, no timestamps), so two builds from the same inputs have
identical CSV bytes; CSV hashes are the canonical ones (Parquet bytes can vary with the pyarrow version).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
RELEASE = REPO / "resource" / "release"
ROUND = 4  # decimals of a basis point
RELEASE_VERSION = "1.0"

# ---------------------------------------------------------------- table specifications (the schema file is generated from these)

TABLES: dict[str, dict[str, Any]] = {
    "unit_offsets_pairs": {
        "description": "Hourly exchange-dollar unit offset of venue A minus venue B (bps), 2017-01..2023-12, over the three venue pairs of "
                       "Bitfinex, Coinbase and Bitstamp, using every asset quoted on both venues. Differences only; no price levels.",
        "columns": {
            "timestamp_utc": ("datetime64[ns, UTC]", "hour start, UTC"),
            "pair": ("string", "'A-B' with A, B in {bitfinex, coinbase, bitstamp}; values are A minus B"),
            "b2_median_bps": ("float64", "bps; median over assets quoted on both venues of 1e4*(log p_A - log p_B) in the same hour (baseline b2)"),
            "estimator_bps": ("float64", "bps; u_A - u_B from the committed www_auto.estimator (shrunk cross-asset median, numeraire Coinbase), all assets visible"),
            "dispersion_bps": ("float64", "bps; 1.4826 * MAD of the per-asset gaps around their median (cross-asset dispersion); null when fewer than 2 assets"),
            "n_assets": ("int64", "number of assets with a gap in this hour"),
        },
        "key": ["timestamp_utc", "pair"],
    },
    "unit_offsets_stablecoin": {
        "description": "Hourly offset (bps) of each (venue, quote unit) BTC market against the same-hour median of the USD-quoted markets, "
                       "2022-03..2025-04 where covered, with the B2 stablecoin conversion rate. Differences only.",
        "columns": {
            "timestamp_utc": ("datetime64[ns, UTC]", "hour start, UTC"),
            "market": ("string", "venue.UNIT, e.g. binance.USDT"),
            "venue": ("string", "venue"),
            "unit": ("string", "quote unit (USD, USDT, USDC, BUSD, TUSD, FDUSD, UST)"),
            "gap_btc_bps": ("float64", "bps; 1e4*(log BTC price in the market - median log BTC price over USD-quoted markets, same hour); null when fewer than 2 USD markets"),
            "gap_eth_bps": ("float64", "bps; the same for ETH where the market lists ETH (null otherwise)"),
            "b2_unit_bps": ("float64", "bps; B2 baseline log USD value of one unit of the quote unit from stablecoin cross-rates (0 for USD; null when unseen for 24 h)"),
            "cross_asset_spread_bps": ("float64", "bps; |gap_btc - gap_eth| (a unit shift moves both; a token-specific move does not); null unless both exist"),
            "n_usd_markets": ("int64", "USD-quoted markets with a BTC price in this hour"),
        },
        "key": ["timestamp_utc", "market"],
    },
    "anchor_usdt": {
        "description": "Hourly USDT/USD price on a venue, net of Kraken's USDT/USD price (bps). Kraken is the external anchor.",
        "columns": {
            "timestamp_utc": ("datetime64[ns, UTC]", "hour start, UTC"),
            "venue": ("string", "bitfinex (USDT/USD as ticker UST), binance_us or bitstamp"),
            "anchor_bps": ("float64", "bps; 1e4*(log P_venue(USDT/USD) - log P_kraken(USDT/USD)), both hourly last traded close"),
        },
        "key": ["timestamp_utc", "venue"],
    },
    "fiat_rail_labels": {
        "description": "The 33-episode fiat-rail event registry (configs/fiat_rail_labels.json), one row per episode. Compiled from public "
                       "news and filings before any price data were opened; carries no exchange data.",
        "columns": {
            "id": ("string", "episode identifier"),
            "venue": ("string", "venue"),
            "type": ("string", "deposit_pause | withdrawal_delay | banking_partner_loss | rail_shutdown | restoration | confounder"),
            "first_public_report_date": ("string", "UTC date of first public report"),
            "impairment_start": ("string", "UTC date or null"),
            "impairment_end": ("string", "UTC date or null (open-ended)"),
            "evidence_quality": ("string", "primary_statement | major_outlet | secondary | rumor"),
            "description": ("string", "one-sentence description"),
            "first_report_source_url": ("string", "URL of the earliest report"),
            "source_urls": ("string", "space-separated URLs of all sources"),
            "notes": ("string", "caveats such as conflicting dates"),
        },
        "key": ["id"],
    },
    "benchmark_splits": {
        "description": "Episode definitions and splits of the three benchmarks (UNIT-TD, FUSE, STABLE), read from the harness modules.",
        "columns": {
            "benchmark": ("string", "UNIT-TD | FUSE | STABLE"),
            "unit_type": ("string", "asset | control | episode"),
            "name": ("string", "asset ticker or episode name"),
            "split": ("string", "dev | test | control"),
            "window": ("string", "first..last UTC day; ';' separates windows of one episode; empty for assets"),
            "excluded_windows": ("string", "sub-windows not scored; ';' separated"),
            "calm": ("bool", "placebo episode (no stress): a method must not lose to the baseline there"),
        },
        "key": ["benchmark", "unit_type", "name"],
    },
    "benchmark_results": {
        "description": "Locked-test results recorded in autoresearch/final_*.log, plus the dev score of the locked commit from the committed loop logs.",
        "columns": {
            "benchmark": ("string", "UNIT-TD | FUSE | STABLE"),
            "locked_commit": ("string", "commit of the method that was tested once"),
            "split": ("string", "test | dev"),
            "episode": ("string", "episode, asset, year or empty for overall"),
            "method": ("string", "fuser/estimator or a baseline name; empty for overall"),
            "metric": ("string", "metric name as printed by the harness"),
            "value": ("float64", "numeric value (booleans are 1.0/0.0)"),
        },
        "key": ["benchmark", "split", "episode", "method", "metric"],
    },
}

ASSET_STATS = ("mae", "rel_e", "p95", "n25", "n50", "cov")
PAIRS = (("bitfinex", "coinbase"), ("coinbase", "bitstamp"), ("bitfinex", "bitstamp"))
NUMERAIRE = "coinbase"
NON_SHARED = ("USDT", "ETHBTC")  # Bitfinex-only feeds, never an asset gap
LOCKED = {  # benchmark -> (log file, locked commit, loop log, harness module, unlock file, final command)
    "UNIT-TD": ("autoresearch/final_test_724455b.log", "724455b", "autoresearch/results_unit_td_run1.tsv", "www_auto.harness", "autoresearch/FINAL_UNLOCK"),
    "FUSE": ("autoresearch/final_fuse_914b3cb.log", "914b3cb", "autoresearch/results_fuse_run1.tsv", "www_fuse.harness", "autoresearch/FINAL_UNLOCK_FUSE"),
    "STABLE": ("autoresearch/final_stable_ca38772.log", "ca38772", "autoresearch/results_stable_run1.tsv", "www_stable.harness", "autoresearch/FINAL_UNLOCK_STABLE"),
}


# ---------------------------------------------------------------- derived series

def _mad_sd(gaps: pd.DataFrame, loc: pd.Series) -> pd.Series:
    n = gaps.notna().sum(axis=1)
    dev = gaps.sub(loc, axis=0).abs().median(axis=1, skipna=True)
    return (1.4826 * dev).where(n >= 2)


def pair_offsets(unit_panel: pd.DataFrame) -> pd.DataFrame:
    """Long table of b2 / estimator / dispersion for each venue pair from the UNIT-TD hourly panel (log prices)."""
    from www_auto import estimator

    venues = sorted({c.split("|", 1)[0] for c in unit_panel.columns if "|" in c})
    panel = {v: unit_panel[[c for c in unit_panel.columns if c.startswith(v + "|")]].rename(columns=lambda c: c.split("|", 1)[1])
             for v in venues}
    units = estimator.estimate_units(panel, NUMERAIRE)
    parts = []
    for a, b in PAIRS:
        if a not in panel or b not in panel:
            continue
        shared = [c for c in panel[a].columns if c in panel[b].columns and not c.endswith("_vol") and c not in NON_SHARED]
        gaps = 1e4 * (panel[a][shared] - panel[b][shared])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            loc = gaps.median(axis=1, skipna=True)
        out = pd.DataFrame({
            "timestamp_utc": unit_panel.index, "pair": f"{a}-{b}", "b2_median_bps": loc.to_numpy(),
            "estimator_bps": (units[a] - units[b]).reindex(unit_panel.index).to_numpy(),
            "dispersion_bps": _mad_sd(gaps, loc).to_numpy(), "n_assets": gaps.notna().sum(axis=1).to_numpy().astype("int64"),
        })
        parts.append(out[out["n_assets"] > 0])
    res = pd.concat(parts, ignore_index=True)
    return _finish(res, TABLES["unit_offsets_pairs"]["key"])


def stablecoin_offsets(stable_panel: pd.DataFrame) -> pd.DataFrame:
    """Long table of per-market offsets against the USD-market median, plus the B2 conversion rate."""
    from www_stable.baselines import usd_log_rates

    cols = [c for c in stable_panel.columns if "|" in c and not c.endswith("_vol")]
    markets = sorted({c.split("|", 1)[0] for c in cols if not c.startswith(("side|", "kraken|"))})
    side = stable_panel[[c for c in cols if c.startswith("side|")]].rename(columns=lambda c: c.split("|", 1)[1])
    units = sorted({m.split(".", 1)[1] for m in markets})
    rates = usd_log_rates(side, units)
    usd = [m for m in markets if m.endswith(".USD")]

    def med(item: str) -> tuple[pd.Series, pd.Series]:
        m = stable_panel[[f"{k}|{item}" for k in usd if f"{k}|{item}" in stable_panel.columns]]
        n = m.notna().sum(axis=1)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return m.median(axis=1, skipna=True).where(n >= 2), n

    med_btc, n_usd = med("BTC")
    med_eth, _ = med("ETH")
    parts = []
    for m in markets:
        venue, unit = m.split(".", 1)
        btc = stable_panel[f"{m}|BTC"] if f"{m}|BTC" in stable_panel.columns else pd.Series(np.nan, index=stable_panel.index)
        eth = stable_panel[f"{m}|ETH"] if f"{m}|ETH" in stable_panel.columns else pd.Series(np.nan, index=stable_panel.index)
        gb, ge = 1e4 * (btc - med_btc), 1e4 * (eth - med_eth)
        r = rates[unit]
        out = pd.DataFrame({
            "timestamp_utc": stable_panel.index, "market": m, "venue": venue, "unit": unit,
            "gap_btc_bps": gb.to_numpy(), "gap_eth_bps": ge.to_numpy(), "b2_unit_bps": 1e4 * np.asarray(r, float),
            "cross_asset_spread_bps": (gb - ge).abs().to_numpy(), "n_usd_markets": n_usd.to_numpy().astype("int64"),
        })
        parts.append(out[btc.notna().to_numpy() | eth.notna().to_numpy()])
    return _finish(pd.concat(parts, ignore_index=True), TABLES["unit_offsets_stablecoin"]["key"])


def anchor_series(unit_panel: pd.DataFrame, stable_panel: pd.DataFrame, kraken_usdt_log: pd.Series) -> pd.DataFrame:
    """USDT/USD per venue net of Kraken's USDT/USD, in bps. Venue and Kraken series are hourly last traded closes (log)."""
    venues = {"bitfinex": unit_panel["bitfinex|USDT"] if "bitfinex|USDT" in unit_panel.columns else None,
              "binance_us": stable_panel.get("side|USDT.USD@binance_us"), "bitstamp": stable_panel.get("side|USDT.USD@bitstamp")}
    parts = []
    for venue, s in venues.items():
        if s is None:
            continue
        k = kraken_usdt_log.reindex(s.index)
        d = (1e4 * (s - k)).dropna()
        parts.append(pd.DataFrame({"timestamp_utc": d.index, "venue": venue, "anchor_bps": d.to_numpy()}))
    return _finish(pd.concat(parts, ignore_index=True), TABLES["anchor_usdt"]["key"])


def kraken_usdt_hourly_log(path: Path, start: str = "2017-01-01", end: str = "2025-04-30 23:00") -> pd.Series:
    """Hourly last traded close (log) of Kraken USDT/USD from the 1-minute OHLCVT file; traded minutes only."""
    x = pd.read_csv(path, header=None, names=["t", "o", "h", "l", "c", "v", "n"], usecols=["t", "c", "v"])
    x = x[(x["c"] > 0) & (x["v"] > 0)]
    x.index = pd.to_datetime(x.pop("t"), unit="s", utc=True)
    x = x.sort_index()
    s = np.log(x["c"]).groupby(x.index.floor("h")).last()
    return s.reindex(pd.date_range(start, end, freq="h", tz="UTC", name="timestamp_utc"))


def fiat_labels(path: Path) -> pd.DataFrame:
    eps = json.loads(path.read_text())["episodes"]
    rows = [{"id": e["id"], "venue": e["venue"], "type": e["type"], "first_public_report_date": e.get("first_public_report_date"),
             "impairment_start": e.get("impairment_start"), "impairment_end": e.get("impairment_end"),
             "evidence_quality": e.get("evidence_quality"), "description": e.get("description"),
             "first_report_source_url": e.get("first_report_source_url"), "source_urls": " ".join(e.get("source_urls") or []),
             "notes": e.get("notes")} for e in eps]
    return _finish(pd.DataFrame(rows), TABLES["fiat_rail_labels"]["key"])


def benchmark_splits() -> pd.DataFrame:
    """Definitions read from the harness/panel modules, so they cannot drift from the code."""
    from www_auto import harness as H
    from www_auto import panel as AP
    from www_fuse import panel as FP
    from www_stable import panel as SP

    rows: list[dict[str, Any]] = []
    for a in AP.VISIBLE:
        rows.append(dict(benchmark="UNIT-TD", unit_type="asset", name=a, split="dev", window="", excluded_windows="", calm=False))
    for a in AP.TEST_SCORED:
        rows.append(dict(benchmark="UNIT-TD", unit_type="asset", name=a, split="test", window="", excluded_windows="", calm=False))
    rows.append(dict(benchmark="UNIT-TD", unit_type="control", name=f"{H.CONTROL_PAIR[0]}-{H.CONTROL_PAIR[1]}:{H.CONTROL_ASSET}",
                     split="control", window=f"{H.CONTROL_START:%Y-%m-%d}..2023-12-31", excluded_windows="", calm=True))
    for e in FP.EPISODES:
        rows.append(dict(benchmark="FUSE", unit_type="episode", name=e.name, split=e.split, window=f"{e.start}..{e.end}",
                         excluded_windows=";".join(f"{a}..{b}" for a, b in e.exclude), calm=e.calm))
    for e in SP.EPISODES:
        rows.append(dict(benchmark="STABLE", unit_type="episode", name=e.name, split=e.split,
                         window=";".join(f"{a}..{b}" for a, b in e.windows), excluded_windows="", calm=e.calm))
    return _finish(pd.DataFrame(rows), TABLES["benchmark_splits"]["key"])


def _num(v: str) -> float | None:
    v = v.strip()
    if v in ("True", "False"):
        return 1.0 if v == "True" else 0.0
    try:
        return float(v)
    except ValueError:
        return None


def parse_final_log(text: str, benchmark: str, commit: str) -> list[dict[str, Any]]:
    """Numeric ``key: value`` lines of a locked-test log as long rows (warnings and non-numeric lines are skipped)."""
    rows = []
    for line in text.splitlines():
        m = re.fullmatch(r"([A-Za-z0-9_]+): (\S+)", line.strip())
        if not m:
            continue
        key, val = m.group(1), _num(m.group(2))
        if val is None or key == "seed":
            continue
        ep = meth = ""
        mm = re.fullmatch(rf"({'|'.join(ASSET_STATS)})_([A-Z]\d)_(.+)", key)
        if mm:
            key, ep, meth = mm.group(1), mm.group(2), mm.group(3)
        else:
            mm = re.fullmatch(r"hours_([A-Z]\d)", key)
            if mm:
                key, ep = "hours", mm.group(1)
            else:
                mm = re.fullmatch(r"(asset|year)_(\w+)", key)
                if mm:
                    key, ep = f"score_by_{mm.group(1)}", mm.group(2)
                else:
                    mm = re.fullmatch(r"(b[012])_(test|control)", key)
                    if mm:
                        key, meth = f"{mm.group(2)}_score", mm.group(1)
        rows.append(dict(benchmark=benchmark, locked_commit=commit, split="test", episode=ep, method=meth, metric=key, value=val))
    return rows


def benchmark_results(repo: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for bench, (log, commit, loop, _mod, _unlock) in LOCKED.items():
        rows += parse_final_log((repo / log).read_text(), bench, commit)
        tsv = pd.read_csv(repo / loop, sep="\t", dtype=str)
        hit = tsv[tsv["commit"].str.startswith(commit)]
        if len(hit):
            rows.append(dict(benchmark=bench, locked_commit=commit, split="dev", episode="", method="", metric="dev_score",
                             value=float(hit.iloc[0]["dev_score"])))
    return _finish(pd.DataFrame(rows), TABLES["benchmark_results"]["key"], ndigits=6)  # harness prints 6 decimals


# ---------------------------------------------------------------- writing

def _finish(df: pd.DataFrame, key: list[str], ndigits: int = ROUND) -> pd.DataFrame:
    for c in df.columns:
        if df[c].dtype.kind == "f":
            df[c] = df[c].round(ndigits)
    return df.sort_values(key, kind="mergesort").reset_index(drop=True)


def _coerce(df: pd.DataFrame, name: str) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    for col, (dtype, _d) in TABLES[name]["columns"].items():
        s = df[col]
        if dtype == "string":
            out[col] = s.astype("object").where(s.notna(), None)
        elif dtype == "bool":
            out[col] = s.astype(bool)
        elif dtype == "int64":
            out[col] = s.astype("int64")
        elif dtype == "float64":
            out[col] = s.astype("float64")
        else:
            out[col] = pd.to_datetime(s, utc=True)
    return out


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_table(df: pd.DataFrame, name: str, out: Path) -> dict[str, Any]:
    df = _coerce(df, name)
    csv_df = df.copy()
    if "timestamp_utc" in csv_df.columns:
        csv_df["timestamp_utc"] = csv_df["timestamp_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    csv_df.to_csv(out / f"{name}.csv", index=False, lineterminator="\n")
    df.to_parquet(out / f"{name}.parquet", index=False, compression="zstd")
    info: dict[str, Any] = {"rows": int(len(df))}
    if "timestamp_utc" in df.columns and len(df):
        info["first_utc"], info["last_utc"] = df["timestamp_utc"].min().isoformat(), df["timestamp_utc"].max().isoformat()
    return info


def schema_document() -> dict[str, Any]:
    return {"release_version": RELEASE_VERSION, "format": "each table is written as <name>.csv and <name>.parquet with identical content",
            "timestamps": "UTC hour starts; CSV ISO-8601 'YYYY-MM-DDTHH:MM:SSZ'", "units": f"basis points rounded to {ROUND} decimals",
            "tables": {n: {"description": t["description"], "primary_key": t["key"],
                           "columns": [{"name": c, "dtype": d, "description": desc} for c, (d, desc) in t["columns"].items()]}
                       for n, t in TABLES.items()}}


def build_release(out: Path, tables: dict[str, pd.DataFrame], provenance: dict[str, Any], extra_files: dict[str, bytes] | None = None) -> dict[str, Any]:
    """Write all tables, schema.json, provenance.json, benchmarks.json (extra_files) and MANIFEST.sha256 / manifest.json."""
    out.mkdir(parents=True, exist_ok=True)
    stats = {name: write_table(df, name, out) for name, df in tables.items()}
    (out / "schema.json").write_text(json.dumps(schema_document(), indent=1, sort_keys=True) + "\n")
    (out / "provenance.json").write_text(json.dumps({"inputs": provenance, "tables": stats}, indent=1, sort_keys=True) + "\n")
    for fname, data in (extra_files or {}).items():
        (out / fname).write_bytes(data)
    files = sorted(p for p in out.iterdir() if p.is_file() and p.name not in ("MANIFEST.sha256", "manifest.json"))
    entries = {p.name: {"sha256": sha256_file(p), "bytes": p.stat().st_size} for p in files}
    (out / "MANIFEST.sha256").write_text("".join(f"{v['sha256']}  {k}\n" for k, v in entries.items()))
    manifest = {"release_version": RELEASE_VERSION, "files": entries, "tables": stats}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return manifest


def benchmarks_json(repo: Path) -> bytes:
    doc = {}
    for bench, (log, commit, loop, mod, unlock) in LOCKED.items():
        doc[bench] = {"dev_command": f"uv run python -m {mod}", "locked_test_command": f"uv run python -m {mod} --final",
                      "unlock_file": unlock, "locked_commit": commit, "locked_test_log": log, "locked_test_log_sha256": sha256_file(repo / log),
                      "loop_log": loop, "loop_log_sha256": sha256_file(repo / loop)}
    return (json.dumps(doc, indent=1, sort_keys=True) + "\n").encode()


def load_inputs(repo: Path = REPO) -> dict[str, Any]:
    from www_auto import anchor_external as KX
    from www_auto import panel as AP
    from www_stable import panel as SP

    AP.ensure()
    SP.ensure()
    kraken = KX.KRAKEN / "USDTUSD_1.csv"
    return {"unit_panel": pd.read_parquet(AP.PANEL_PATH), "stable_panel": pd.read_parquet(SP.PANEL_PATH),
            "kraken_usdt": kraken_usdt_hourly_log(kraken),
            "hashes": {"unit_td_panel.parquet": sha256_file(AP.PANEL_PATH), "stable_panel.parquet": sha256_file(SP.PANEL_PATH),
                       "kraken_USDTUSD_1.csv": sha256_file(kraken),
                       "fiat_rail_labels.json": sha256_file(repo / "configs" / "fiat_rail_labels.json")}}


def build(out: Path = RELEASE, repo: Path = REPO, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    inp = inputs or load_inputs(repo)
    tables = {
        "unit_offsets_pairs": pair_offsets(inp["unit_panel"]),
        "unit_offsets_stablecoin": stablecoin_offsets(inp["stable_panel"]),
        "anchor_usdt": anchor_series(inp["unit_panel"], inp["stable_panel"], inp["kraken_usdt"]),
        "fiat_rail_labels": fiat_labels(repo / "configs" / "fiat_rail_labels.json"),
        "benchmark_splits": benchmark_splits(),
        "benchmark_results": benchmark_results(repo),
    }
    prov = {"input_sha256": inp["hashes"], "note": "inputs are not part of the release; hashes let a rebuilder confirm identical inputs"}
    return build_release(out, tables, prov, {"benchmarks.json": benchmarks_json(repo)})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=RELEASE)
    ap.add_argument("--record", type=Path, default=None, help="also write the file hashes here (committed copy)")
    args = ap.parse_args(argv)
    manifest = build(args.out)
    total = sum(v["bytes"] for v in manifest["files"].values())
    print(f"wrote {len(manifest['files'])} files, {total / 1e6:.1f} MB to {args.out}")
    for name, st in manifest["tables"].items():
        print(f"  {name}: {st['rows']} rows")
    if args.record:
        args.record.write_text(json.dumps({"release_version": RELEASE_VERSION, "files": {k: v["sha256"] for k, v in manifest["files"].items()}},
                                          indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
