"""Hourly UTC panel for the Q1 events (2018-08 .. 2022-10), cached to data/derived/q1_panel.parquet.

Same conventions as ``www_stable.panel`` (hourly last traded close, zero-volume hours dropped, isolated log spike dropped,
every raw file checked against its manifest hash); its loaders are reused unchanged. Only the grid, the market list and the
side series differ. Kraken BTC/USD is stored as the reference (``kraken|BTC``) and is used only for scoring in ``run.py``;
``gate.py`` never reads it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from www_auto import anchor_external as KX
from www_stable import panel as SP

REPO, RAW, MANIFEST = SP.REPO, SP.RAW, SP.MANIFEST
PANEL_PATH = REPO / "data" / "derived" / "q1_panel.parquet"
META_PATH = PANEL_PATH.with_name("q1_panel_meta.json")
BUILD_VERSION = 1
GRID_START, GRID_END = "2018-08-01", "2022-10-31 23:00"
WARMUP_HOURS = SP.WARMUP_HOURS

# (id, window first day, window last day, shifted unit, unit family)
EVENTS = (
    ("Q-E1", "2018-10-08", "2018-10-31", "USDT"),
    ("Q-E2", "2018-11-27", "2018-12-31", "USDT"),
    ("Q-E3", "2019-04-20", "2019-05-31", "USDT"),
    ("Q-E4", "2020-03-09", "2020-03-31", "USDT"),
    ("Q-E5", "2022-09-05", "2022-10-05", "BUSD"),
)
KEEP_MARKETS = {("binance", "USDT"), ("binance", "BUSD"), ("coinbase", "USD"), ("bitstamp", "USD"), ("bitfinex", "USD"),
                ("binance_us", "USD"), ("binance_us", "USDT")}
MARKETS = tuple(m for m in SP.MARKETS if (m[0], m[1]) in KEEP_MARKETS)
SIDE = (
    ("USDT", "USD", "binance_us", "binance-us", "binance_us", "USDTUSD"),
    ("USDT", "USD", "bitstamp", "bitstamp", "bitstamp", "USDTUSD"),
    ("USDT", "USD", "bitfinex", "bitfinex", "bitfinex", "USTUSD"),  # Bitfinex's own USDT/USD, raw
)
BITFINEX_USDT = "side|USDT.USD@bitfinex"
BINANCE_US_USDT = "side|USDT.USD@binance_us"
BITSTAMP_USDT = "side|USDT.USD@bitstamp"


def episodes() -> tuple[SP.Episode, ...]:
    return tuple(SP.Episode(i, "test", ((a, b),)) for i, a, b, _ in EVENTS)


def shifted_unit(event_id: str) -> str:
    return {i: u for i, _, _, u in EVENTS}[event_id]


def grid() -> pd.DatetimeIndex:
    return pd.date_range(GRID_START, GRID_END, freq="h", tz="UTC", name="timestamp_utc")


def needed_months() -> list[str]:
    return SP.needed_months(episodes())


def clean(frame: pd.DataFrame, counts: dict[str, Any]) -> pd.DataFrame:
    """``www_stable.panel.clean_series`` on this panel's grid (identical rules)."""
    g = grid()
    frame = frame[(frame.index >= g[0]) & (frame.index <= g[-1])]
    counts["rows_raw"] = int(len(frame))
    bad = ~(frame["v"] > 0) | frame["p"].isna()
    counts["dropped_zero_volume_or_bad_price"] = int(bad.sum())
    frame = frame[~bad].reindex(g)
    p = frame["p"]
    up, down = p - p.shift(1), p - p.shift(-1)
    spike = ((up > SP.SPIKE) & (down > SP.SPIKE)) | ((up < -SP.SPIKE) & (down < -SP.SPIKE))
    counts["dropped_isolated_spike"] = int(spike.sum())
    frame[spike.to_numpy()] = np.nan
    counts["rows_final"] = int(frame["p"].notna().sum())
    return frame


def kraken_hourly(pair: str = "XBTUSD", raw: Path = KX.KRAKEN) -> pd.DataFrame:
    x = pd.read_csv(raw / f"{pair}_1.csv", header=None, names=["t", "o", "h", "l", "c", "v", "n"], usecols=["t", "c", "v"])
    x = x[(x["c"] > 0) & (x["v"] > 0)]
    x.index = pd.to_datetime(x.pop("t"), unit="s", utc=True)
    x = x.sort_index()
    x = x[(x.index >= grid()[0]) & (x.index <= grid()[-1] + pd.Timedelta(hours=1))]
    hour = x.index.floor("h")
    return pd.DataFrame({"p": np.log(x["c"]).groupby(hour).last(), "v": x["v"].groupby(hour).sum()})


def build(raw: Path = RAW, manifest: Path = MANIFEST, months: list[str] | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    months = months or needed_months()
    records = SP.AP._manifest_records(manifest)
    cols: dict[str, pd.Series] = {}
    meta: dict[str, Any] = {"build_version": BUILD_VERSION, "months_read": months, "series": {}, "missing_months": {},
                            "source_files": {}}

    def add(key: str, frame: pd.DataFrame, note: str, hashes: list[str], missing: list[str], volume: bool = True) -> None:
        counts: dict[str, Any] = {"source": note}
        s = clean(frame, counts)
        counts["first_utc"], counts["last_utc"] = str(s["p"].first_valid_index()), str(s["p"].last_valid_index())
        meta["series"][key], meta["source_files"][key], meta["missing_months"][key] = counts, hashes, missing
        cols[key] = s["p"]
        if volume:
            cols[key + "_vol"] = s["v"]

    for venue, unit, mvenue, directory, btc, eth in MARKETS:
        for item, pair in (("BTC", btc), ("ETH", eth)):
            if pair is None:
                continue
            frame, hashes, missing = SP._read(raw, directory, mvenue, pair, months, records, manifest)
            if not hashes:
                continue
            add(f"{SP.market_key(venue, unit)}|{item}", frame, f"{mvenue} {pair} 1m -> last traded close per hour", hashes, missing)
    for base, quote, venue, mvenue, directory, pair in SIDE:
        frame, hashes, missing = SP._read(raw, directory, mvenue, pair, months, records, manifest)
        if hashes:
            add("side|" + SP.side_key(base, quote, venue), frame, f"{mvenue} {pair} 1m -> last traded close per hour", hashes,
                missing, volume=False)
    meta["kraken_file_sha256"] = KX.verify(manifest, KX.KRAKEN)
    add("kraken|BTC", kraken_hourly(), "kraken ohlcvt XBTUSD 1m -> last traded close per hour", [], [], volume=False)
    return pd.DataFrame(cols, index=grid()).sort_index(axis=1), meta


def ensure(path: Path = PANEL_PATH, rebuild: bool = False) -> None:
    meta_path = path.with_name(META_PATH.name)
    if path.exists() and meta_path.exists() and not rebuild:
        if json.loads(meta_path.read_text()).get("build_version") == BUILD_VERSION:
            return
    frame, meta = build()
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path)
    meta_path.write_text(json.dumps(meta, indent=1, default=str))


def load_all(path: Path = PANEL_PATH, with_reference: bool = True):
    """(markets, side, reference-or-None, meta) over the whole grid. ``with_reference=False`` never reads Kraken."""
    ensure(path)
    frame = pd.read_parquet(path)
    if "timestamp_utc" in frame.columns:
        frame = frame.set_index("timestamp_utc")
    markets: dict[str, pd.DataFrame] = {}
    for c in frame.columns:
        head, item = c.split("|", 1)
        if head in ("kraken", "side"):
            continue
        markets.setdefault(head, pd.DataFrame(index=frame.index))[item] = frame[c]
    side = frame[[c for c in frame.columns if c.startswith("side|")]].rename(columns=lambda c: c.split("|", 1)[1])
    ref = frame["kraken|BTC"] if with_reference else None
    return markets, side, ref, json.loads(path.with_name(META_PATH.name).read_text())


if __name__ == "__main__":
    ensure(rebuild=True)
    print(f"wrote {PANEL_PATH}")
