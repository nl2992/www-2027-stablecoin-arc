"""Hourly UTC panel for the FUSE round (2017-01..2023-12), cached to data/derived/fuse_panel.parquet.

Per (source, item): the log of the hour's last traded close and the hour's volume, stored flat as ``source|ITEM`` and
``source|ITEM_vol`` (same convention and cleaning rule as ``www_auto.panel``: drop zero-volume or non-positive hours, drop
an isolated >0.3 log spike). Sources and items:

  bitfinex   BTC ETH USDT (minute files) + nine altcoins (hourly files; BCH spliced across the BCH forks)
  coinbase   BTC ETH (minute) + nine altcoins (hourly)
  bitstamp   BTC ETH USDT (minute; USDT from 2022-04) + LTC XRP XLM LINK BCH (hourly)
  binance_us BTC USDT (minute; BTC from 2022-10)
  kraken     BTC ETH  (reference only; never given to a fuser)

Every raw file is checked against its manifest SHA-256 before use. Raw files are untrusted data: they are read as plain
CSV (or a zipped CSV) and nothing in them is executed.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from www_auto import anchor_external as KX
from www_auto import panel as AP
from www_events.binance_klines import parse_kline_csv

REPO = AP.REPO
RAW = AP.RAW
MANIFEST = AP.MANIFEST
PANEL_PATH = REPO / "data" / "derived" / "fuse_panel.parquet"
META_PATH = PANEL_PATH.with_name("fuse_panel_meta.json")
BUILD_VERSION = 1

FUSED = ("BTC", "ETH")
ALTS = ("LTC", "ETC", "XLM", "XRP", "LINK", "SOL", "DOGE", "ADA", "BCH")
BITSTAMP_ALTS = ("LTC", "XRP", "XLM", "LINK", "BCH")
SOURCES = ("bitfinex", "coinbase", "bitstamp", "binance_us")
REFERENCE = "kraken"
WARMUP_HOURS = 720  # 30 days of history handed to the fuser before each episode window


@dataclass(frozen=True)
class Episode:
    name: str
    split: str  # "dev" | "test"
    start: str  # first UTC day of the window
    end: str  # last UTC day of the window (inclusive)
    exclude: tuple[tuple[str, str], ...] = ()  # (first day, last day) sub-windows that are not scored
    calm: bool = False

    def bounds(self) -> tuple[pd.Timestamp, pd.Timestamp]:
        return pd.Timestamp(self.start, tz="UTC"), pd.Timestamp(self.end, tz="UTC") + pd.Timedelta(hours=23)

    def load_bounds(self) -> tuple[pd.Timestamp, pd.Timestamp]:
        lo, hi = self.bounds()
        return lo - pd.Timedelta(hours=WARMUP_HOURS), hi

    def scored_mask(self, index: pd.DatetimeIndex) -> np.ndarray:
        lo, hi = self.bounds()
        m = (index >= lo) & (index <= hi)
        for a, b in self.exclude:
            m &= ~((index >= pd.Timestamp(a, tz="UTC")) & (index <= pd.Timestamp(b, tz="UTC") + pd.Timedelta(hours=23)))
        return np.asarray(m)


EPISODES: tuple[Episode, ...] = (  # fixed 2026-10-21, before any result (autoresearch/program_fuse.md)
    Episode("D1", "dev", "2017-03-01", "2017-08-31"),
    Episode("D2", "dev", "2020-01-01", "2020-12-31", calm=True),
    Episode("D3", "dev", "2021-01-01", "2021-12-31", calm=True),
    Episode("T1", "test", "2018-10-01", "2019-05-31"),
    Episode("T2", "test", "2023-05-01", "2023-07-31"),
    Episode("T3", "test", "2022-11-01", "2022-11-30"),
    Episode("T4", "test", "2023-03-08", "2023-03-20"),
    Episode("T5", "test", "2022-01-01", "2023-12-31", calm=True,
            exclude=(("2023-05-01", "2023-07-31"), ("2022-11-01", "2022-11-30"), ("2023-03-08", "2023-03-20"))),
)


def episodes_for(mode: str, episodes: tuple[Episode, ...] = EPISODES) -> tuple[Episode, ...]:
    if mode not in ("dev", "final"):
        raise ValueError(mode)
    want = "dev" if mode == "dev" else "test"
    return tuple(e for e in episodes if e.split == want)


def column(source: str, name: str) -> str:
    return f"{source}|{name}"


# ---------------------------------------------------------------- loading

def _binance_us_hourly(raw: Path, pair: str, records: dict[tuple[str, str], dict[str, Any]]) -> tuple[pd.DataFrame, list[str], list[str]]:
    parts, hashes, missing = [], [], []
    import hashlib
    for m in AP.months():
        f = raw / "binance_us" / f"{pair}-1m-{m}.zip"
        if not f.is_file():
            missing.append(m)
            continue
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        rec = records.get(("binance-us", f.name))
        if rec is None or rec["sha256"] != digest:
            raise ValueError(f"{f.name} does not match its recorded manifest hash (binance-us)")
        with zipfile.ZipFile(f) as zf:
            members = [n for n in zf.namelist() if n.endswith(".csv")]
            if len(members) != 1:
                raise ValueError(f"{f.name}: expected one CSV member")
            frame = parse_kline_csv(zf.read(members[0]).decode("utf-8")).frame
        hashes.append(f"{f.name}:{digest}")
        traded = frame["volume"] > 0
        px, vol = frame.loc[traded, "close"], frame.loc[traded, "volume"]
        hour = px.index.floor("h")
        parts.append(pd.DataFrame({"p": np.log(px.where(px > 0)).groupby(hour).last(), "v": vol.groupby(hour).sum()}))
    frame = pd.concat(parts).sort_index() if parts else pd.DataFrame(columns=["p", "v"])
    return frame, hashes, missing


def _kraken_hourly(pair: str, raw: Path = KX.KRAKEN) -> pd.DataFrame:
    x = pd.read_csv(raw / f"{pair}_1.csv", header=None, names=["t", "o", "h", "l", "c", "v", "n"], usecols=["t", "c", "v"])
    x = x[(x["c"] > 0) & (x["v"] > 0)]
    x.index = pd.to_datetime(x.pop("t"), unit="s", utc=True)
    x = x.sort_index()
    x = x[x.index <= AP.grid()[-1] + pd.Timedelta(hours=1)]
    hour = x.index.floor("h")
    return pd.DataFrame({"p": np.log(x["c"]).groupby(hour).last(), "v": x["v"].groupby(hour).sum()})


def build(raw: Path = RAW, manifest: Path = MANIFEST) -> tuple[pd.DataFrame, dict[str, Any]]:
    records = AP._manifest_records(manifest)
    series: dict[str, pd.DataFrame] = {}
    meta: dict[str, Any] = {"build_version": BUILD_VERSION, "cleaning": {"spike_log_threshold": AP.SPIKE}, "series": {},
                            "missing_months": {}, "source_files": {}}

    def add(source: str, item: str, frame: pd.DataFrame, note: str, hashes: list[str]) -> None:
        key = column(source, item)
        counts: dict[str, Any] = {"source": note}
        series[key] = AP.clean_series(frame, counts)
        counts["first_utc"] = str(series[key]["p"].first_valid_index())
        counts["last_utc"] = str(series[key]["p"].last_valid_index())
        meta["series"][key] = counts
        meta["source_files"][key] = hashes

    for source, pair, item in [("bitfinex", "BTCUSD", "BTC"), ("bitfinex", "ETHUSD", "ETH"), ("bitfinex", "USTUSD", "USDT"),
                               ("coinbase", "BTCUSD", "BTC"), ("coinbase", "ETHUSD", "ETH"),
                               ("bitstamp", "BTCUSD", "BTC"), ("bitstamp", "ETHUSD", "ETH"), ("bitstamp", "USDTUSD", "USDT")]:
        frame, hashes, missing = AP.minute_to_hourly(raw, pair, source, manifest)
        if missing:
            meta["missing_months"][column(source, item)] = missing
        add(source, item, frame, f"{source} {pair} 1m -> last traded close per hour", hashes)
    for source, pair, item in [("binance_us", "BTCUSD", "BTC"), ("binance_us", "USDTUSD", "USDT")]:
        frame, hashes, missing = _binance_us_hourly(raw, pair, records)
        meta["missing_months"][column(source, item)] = missing
        add(source, item, frame, f"binance-us {pair} 1m -> last traded close per hour", hashes)
    for source, tag in (("bitfinex", "bitfinex-1h"), ("coinbase", "coinbase-1h")):
        for item in ALTS:
            if source == "bitfinex" and item == "BCH":
                continue
            frame, h = AP.read_hourly_csv(raw / f"{source}_1h" / f"{item}USD-1h-2017-2023.csv", tag, records)
            add(source, item, frame, f"{tag} {item}USD", [h])
    bch, splice, hashes = AP.build_bch_bitfinex(raw, records)
    add("bitfinex", "BCH", bch, "bitfinex-1h BCHUSD|BABUSD|BCHNUSD spliced", hashes)
    for item in BITSTAMP_ALTS:
        frame, h = AP.read_hourly_csv(raw / "bitstamp_1h" / f"{item}USD-1h-2017-2023.csv", "bitstamp-1h", records)
        add("bitstamp", item, frame, f"bitstamp-1h {item}USD", [h])
    meta["kraken_file_sha256"] = KX.verify(manifest, KX.KRAKEN)
    for item, pair in (("BTC", "XBTUSD"), ("ETH", "ETHUSD")):
        add(REFERENCE, item, _kraken_hourly(pair), f"kraken ohlcvt {pair} 1m -> last traded close per hour", [])
    cols = {}
    for key in sorted(series):
        cols[key] = series[key]["p"]
        cols[key + "_vol"] = series[key]["v"]
    return pd.DataFrame(cols, index=AP.grid()), meta


def ensure(path: Path = PANEL_PATH, rebuild: bool = False) -> None:
    meta_path = path.with_name(META_PATH.name)
    if path.exists() and meta_path.exists() and not rebuild:
        if json.loads(meta_path.read_text()).get("build_version") == BUILD_VERSION:
            return
    frame, meta = build()
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path)
    meta_path.write_text(json.dumps(meta, indent=1, default=str))


def load_panel(mode: str, path: Path = PANEL_PATH, episodes: tuple[Episode, ...] = EPISODES,
               ) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, dict[str, Any]]:
    """(sources, reference, meta). Only rows inside the mode's episode windows (plus warm-up) are read from disk:
    dev mode never reads a test row. ``sources`` holds the fuser-visible columns, ``reference`` the Kraken columns."""
    ensure(path)
    eps = episodes_for(mode, episodes)
    ranges = [e.load_bounds() for e in eps]
    names = pq.read_schema(path).names
    want = [n for n in names if "|" in n]
    filters = [[("timestamp_utc", ">=", lo), ("timestamp_utc", "<=", hi)] for lo, hi in ranges]
    frame = pd.read_parquet(path, columns=want + ["timestamp_utc"], filters=filters)
    if "timestamp_utc" in frame.columns:
        frame = frame.set_index("timestamp_utc")
    frame = frame.sort_index()
    keep = np.zeros(len(frame), bool)
    for lo, hi in ranges:
        keep |= (frame.index >= lo) & (frame.index <= hi)
    frame = frame[keep]
    sources = {s: frame[[c for c in want if c.startswith(s + "|")]].rename(columns=lambda c: c.split("|", 1)[1])
               for s in SOURCES}
    ref = frame[[c for c in want if c.startswith(REFERENCE + "|")]].rename(columns=lambda c: c.split("|", 1)[1])
    meta = json.loads(path.with_name(META_PATH.name).read_text())
    return sources, ref, meta


if __name__ == "__main__":
    ensure(rebuild=True)
    print(f"wrote {PANEL_PATH}")
