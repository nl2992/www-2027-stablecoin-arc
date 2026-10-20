"""Hourly UTC panel for the UNIT-TD benchmark (2017-01..2023-12), cached to data/derived/unit_td_panel.parquet.

Per (venue, asset): the log of the hour's last traded close and the hour's volume. Columns are stored flat as
``venue|ASSET`` and ``venue|ASSET_vol``. Hour labels are hour starts (see ``label_check`` for the empirical check).

Fixed cleaning rule (decided before any estimator was run, applied to every series; counts go to the metadata):
  1. Bitfinex BCH: splice BCHUSD [.., 2018-11-15 00:00), BABUSD [2018-11-15 00:00, 2020-11-15 13:00), BCHNUSD
     [2020-11-15 13:00, ..); the first bar of each segment file is dropped before the splice (BABUSD's is a placeholder print).
  2. Drop hours with zero (or missing) volume or a non-positive price.
  3. Drop an hour whose log price differs from the same series' previous AND next hour by more than 0.3 in the same
     direction (an isolated bad print). One simultaneous pass; needs both neighbours present.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from www_events.candles import load_venue_months

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "data" / "raw"
MANIFEST = REPO / "reports" / "events" / "acquisition_manifest.json"
PANEL_PATH = REPO / "data" / "derived" / "unit_td_panel.parquet"
META_PATH = PANEL_PATH.with_name("unit_td_panel_meta.json")
BUILD_VERSION = 1

START, END = "2017-01", "2023-12"
SPIKE = 0.3
DEV_SCORED = ("ETH", "LTC", "BCH", "ETC", "XLM")
VISIBLE = ("BTC",) + DEV_SCORED
TEST_SCORED = ("XRP", "LINK", "SOL", "DOGE", "ADA")
EXTRA = ("USDT", "ETHBTC")  # Bitfinex-only feeds
VENUES = ("bitfinex", "coinbase", "bitstamp")

MINUTE_SERIES = [  # (venue, pair, asset)
    ("bitfinex", "BTCUSD", "BTC"), ("bitfinex", "ETHUSD", "ETH"), ("bitfinex", "USTUSD", "USDT"),
    ("bitfinex", "ETHBTC", "ETHBTC"), ("coinbase", "BTCUSD", "BTC"), ("coinbase", "ETHUSD", "ETH"),
    ("bitstamp", "BTCUSD", "BTC"), ("bitstamp", "ETHUSD", "ETH"),
]
HOURLY_ASSETS = ("LTC", "ETC", "XLM", "XRP", "LINK", "SOL", "DOGE", "ADA")
BCH_SEGMENTS = [  # (file pair, first hour included, first hour excluded)
    ("BCHUSD", None, "2018-11-15 00:00"),
    ("BABUSD", "2018-11-15 00:00", "2020-11-15 13:00"),
    ("BCHNUSD", "2020-11-15 13:00", None),
]


def grid() -> pd.DatetimeIndex:
    return pd.date_range(f"{START}-01", "2023-12-31 23:00", freq="h", tz="UTC", name="timestamp_utc")


def months() -> list[str]:
    return [m.strftime("%Y-%m") for m in pd.period_range(START, END, freq="M")]


def column(venue: str, name: str) -> str:
    return f"{venue}|{name}"


# ---------------------------------------------------------------- loading

def _manifest_records(manifest: Path) -> dict[tuple[str, str], dict[str, Any]]:
    return {(r["venue"], r["file"].rsplit("/", 1)[-1]): r for r in json.loads(manifest.read_text())["records"]
            if r.get("status") == "VERIFIED"}


def minute_to_hourly(raw: Path, pair: str, venue: str, manifest: Path) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Hourly (log last traded close, volume) from verified minute months; returns (frame, hashes, missing months)."""
    parts, hashes, missing = [], [], []
    for m in months():
        try:
            g, prov = load_venue_months(raw / venue, pair, "x", manifest, venue, [m])
        except FileNotFoundError:
            missing.append(m)
            continue
        hashes += [f"{f['file']}:{f['sha256']}" for f in prov["files"]]
        traded = g["x_traded"].astype(bool)
        px, vol = g.loc[traded, "x_close"].astype(float), g.loc[traded, "x_volume"].astype(float)
        hour = px.index.floor("h")
        parts.append(pd.DataFrame({"p": np.log(px.where(px > 0)).groupby(hour).last(),
                                   "v": vol.groupby(hour).sum()}))
    frame = pd.concat(parts).sort_index() if parts else pd.DataFrame(columns=["p", "v"])
    return frame, hashes, missing


def read_hourly_csv(path: Path, venue_tag: str, records: dict[tuple[str, str], dict[str, Any]]) -> tuple[pd.DataFrame, str]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    rec = records.get((venue_tag, path.name))
    if rec is None or rec["sha256"] != digest:
        raise ValueError(f"{path.name} does not match its recorded manifest hash ({venue_tag})")
    raw = pd.read_csv(path)
    if list(raw.columns) != ["timestamp", "open", "high", "low", "close", "volume"]:
        raise ValueError(f"{path.name}: unexpected columns {list(raw.columns)}")
    if (raw["timestamp"] % 3600).any():
        raise ValueError(f"{path.name}: timestamps are not on the hour")
    idx = pd.DatetimeIndex(pd.to_datetime(raw["timestamp"], unit="s", utc=True), name="timestamp_utc")
    close = raw["close"].astype(float).to_numpy()
    out = pd.DataFrame({"p": np.log(np.where(close > 0, close, np.nan)), "v": raw["volume"].astype(float).to_numpy()}, index=idx)
    if out.index.has_duplicates:
        raise ValueError(f"{path.name}: duplicate hours")
    return out.sort_index(), f"{path.name}:{digest}"


# ---------------------------------------------------------------- cleaning

def clean_series(frame: pd.DataFrame, counts: dict[str, int]) -> pd.DataFrame:
    """Rules 2 and 3 on a (p, v) hourly frame; mutates ``counts``; returns the frame on the full hourly grid."""
    g = grid()
    frame = frame[(frame.index >= g[0]) & (frame.index <= g[-1])]
    counts["rows_raw"] = int(len(frame))
    bad = ~(frame["v"] > 0) | frame["p"].isna()
    counts["dropped_zero_volume_or_bad_price"] = int(bad.sum())
    frame = frame[~bad].reindex(g)
    p = frame["p"]
    up, down = p - p.shift(1), p - p.shift(-1)
    spike = ((up > SPIKE) & (down > SPIKE)) | ((up < -SPIKE) & (down < -SPIKE))
    counts["dropped_isolated_spike"] = int(spike.sum())
    frame[spike.to_numpy()] = np.nan
    counts["rows_final"] = int(frame["p"].notna().sum())
    return frame


def build_bch_bitfinex(raw: Path, records: dict[tuple[str, str], dict[str, Any]]) -> tuple[pd.DataFrame, dict[str, Any], list[str]]:
    parts, info, hashes = [], [], []
    for pair, lo, hi in BCH_SEGMENTS:
        seg, h = read_hourly_csv(raw / "bitfinex_1h" / f"{pair}-1h-2017-2023.csv", "bitfinex-1h", records)
        hashes.append(h)
        n0 = len(seg)
        seg = seg.iloc[1:]  # first bar of each segment file
        first_dropped = n0 - len(seg)
        keep = np.ones(len(seg), bool)
        if lo is not None:
            keep &= seg.index >= pd.Timestamp(lo, tz="UTC")
        if hi is not None:
            keep &= seg.index < pd.Timestamp(hi, tz="UTC")
        info.append({"file": pair, "first_included_utc": lo, "first_excluded_utc": hi, "rows_in_file": n0,
                     "dropped_first_bar": first_dropped, "dropped_outside_splice_window": int((~keep).sum()),
                     "rows_used": int(keep.sum())})
        parts.append(seg[keep])
    return pd.concat(parts).sort_index(), {"segments": info}, hashes


def build(raw: Path = RAW, manifest: Path = MANIFEST) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build the full panel (all assets) and its metadata from verified raw files."""
    records = _manifest_records(manifest)
    series: dict[str, pd.DataFrame] = {}
    meta: dict[str, Any] = {"build_version": BUILD_VERSION, "cleaning": {"spike_log_threshold": SPIKE}, "series": {},
                            "missing_minute_months": {}, "source_files": {}}

    def add(venue: str, asset: str, frame: pd.DataFrame, extra: dict[str, Any], hashes: list[str]) -> None:
        key = column(venue, asset)
        counts: dict[str, Any] = dict(extra)
        series[key] = clean_series(frame, counts)
        counts["first_utc"] = str(series[key]["p"].first_valid_index())
        counts["last_utc"] = str(series[key]["p"].last_valid_index())
        meta["series"][key] = counts
        meta["source_files"][key] = hashes

    for venue, pair, asset in MINUTE_SERIES:
        frame, hashes, missing = minute_to_hourly(raw, pair, venue, manifest)
        if missing:
            meta["missing_minute_months"][column(venue, asset)] = missing
        add(venue, asset, frame, {"source": f"{venue} 1m -> last traded close per hour"}, hashes)
    for venue, tag in (("bitfinex", "bitfinex-1h"), ("coinbase", "coinbase-1h")):
        for asset in HOURLY_ASSETS:
            frame, h = read_hourly_csv(raw / f"{venue}_1h" / f"{asset}USD-1h-2017-2023.csv", tag, records)
            add(venue, asset, frame, {"source": f"{tag} {asset}USD"}, [h])
    bch, splice, hashes = build_bch_bitfinex(raw, records)
    add("bitfinex", "BCH", bch, {"source": "bitfinex-1h BCHUSD|BABUSD|BCHNUSD spliced", **splice}, hashes)
    frame, h = read_hourly_csv(raw / "coinbase_1h" / "BCHUSD-1h-2017-2023.csv", "coinbase-1h", records)
    add("coinbase", "BCH", frame, {"source": "coinbase-1h BCHUSD (ABC from 2018-11, BCHN from 2020-11)"}, [h])
    meta["bch_splice"] = {"bitfinex": splice["segments"], "coinbase": "single BCHUSD product (followed ABC, then BCHN)"}

    cols = {}
    for key in sorted(series):
        cols[key] = series[key]["p"]
        cols[key + "_vol"] = series[key]["v"]
    return pd.DataFrame(cols, index=grid()), meta


def label_check(panel: pd.DataFrame) -> dict[str, Any]:
    """Hourly-file label convention: correlate LTC hourly log-returns (Bitfinex, Coinbase hourly files) with the BTC
    return built from last-traded minute closes, at hour shifts -1, 0, +1. Peak at 0 means a file's hour label is
    the hour start, the same as the minute-derived label (last traded close within [t, t+1h))."""
    out: dict[str, Any] = {}
    btc = panel["bitfinex|BTC"].diff()
    for venue in ("bitfinex", "coinbase"):
        ret = panel[f"{venue}|LTC"].diff()
        out[venue] = {str(k): float(ret.corr(btc.shift(k))) for k in (-1, 0, 1)}
    return out


def ensure(path: Path = PANEL_PATH, rebuild: bool = False) -> None:
    meta_path = path.with_name(META_PATH.name)
    if path.exists() and meta_path.exists() and not rebuild:
        if json.loads(meta_path.read_text()).get("build_version") == BUILD_VERSION:
            return
    frame, meta = build()
    meta["label_check_corr_by_shift"] = label_check(frame)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path)
    meta_path.write_text(json.dumps(meta, indent=1, default=str))


def allowed_assets(mode: str) -> tuple[str, ...]:
    if mode == "dev":
        return VISIBLE + EXTRA
    if mode == "final":
        return VISIBLE + EXTRA + TEST_SCORED
    raise ValueError(mode)


def load_panel(mode: str, path: Path = PANEL_PATH) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    """Read only the columns the mode may see (dev mode never reads the test-asset columns); builds the cache if absent."""
    ensure(path)
    allowed = set(allowed_assets(mode))
    names = pq.read_schema(path).names
    want = []
    for n in names:
        if "|" not in n:
            continue
        venue, rest = n.split("|", 1)
        if rest.removesuffix("_vol") in allowed:
            want.append(n)
    frame = pd.read_parquet(path, columns=want)
    panel: dict[str, pd.DataFrame] = {}
    for venue in VENUES:
        cols = [c for c in want if c.startswith(venue + "|")]
        panel[venue] = frame[cols].rename(columns=lambda c: c.split("|", 1)[1])
    meta = json.loads(path.with_name(META_PATH.name).read_text())
    return panel, meta
