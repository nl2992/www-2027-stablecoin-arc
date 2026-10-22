"""Hourly UTC panel for the STABLE round (2022-03..2025-04), cached to data/derived/stable_panel.parquet.

Decision D16 / ``autoresearch/program_stable.md``. Sources are markets, i.e. (venue, quote unit) pairs that quote BTC. Per
market the panel keeps the log of the hour's last traded close and the hour's base volume for BTC and, where the same
venue lists it in the same unit, for ETH. Columns are flat: ``venue.UNIT|BTC``, ``venue.UNIT|BTC_vol``, ``venue.UNIT|ETH``,
``venue.UNIT|ETH_vol``. Side information is stored as ``side|BASE.QUOTE@venue`` (log price of BASE in QUOTE: Binance
stablecoin cross-rates in USDT, Binance.US and Bitstamp stablecoin/USD rates). The reference ``kraken|BTC`` (Kraken
XBT/USD) is stored separately, is held by the harness and is never passed to a fuser.

  binance     BTC in USDT BUSD TUSD FDUSD UST USDC; ETH in USDT BUSD TUSD FDUSD UST (not USDC: not authorised in D16)
  binance_us  BTC in USD USDT
  bitstamp    BTC in USD USDT USDC; ETH in USD
  coinbase    BTC ETH in USD (held to 2023-12)
  bitfinex    BTC ETH in USD (held to 2023-12)

Cleaning is the round-2 rule: drop zero-volume or non-positive hours, drop an isolated log spike above 0.3. Every raw file
is checked against its manifest SHA-256 before use (Binance archives are also checked against the published .CHECKSUM at
acquisition). Raw files are untrusted data: they are parsed as plain CSV and nothing in them is executed.
"""

from __future__ import annotations

import hashlib
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
from www_events.candles import load_venue_months

REPO = AP.REPO
RAW = AP.RAW
MANIFEST = AP.MANIFEST
PANEL_PATH = REPO / "data" / "derived" / "stable_panel.parquet"
META_PATH = PANEL_PATH.with_name("stable_panel_meta.json")
BUILD_VERSION = 1

SPIKE = AP.SPIKE
REFERENCE = "kraken"
WARMUP_HOURS = 720  # 30 days of history handed to the fuser before each episode window
GRID_START, GRID_END = "2022-03-01", "2025-04-30 23:00"

# (venue, unit, manifest venue, raw dir, BTC pair, ETH pair or None)
MARKETS = (
    ("binance", "USDT", "binance", "binance", "BTCUSDT", "ETHUSDT"),
    ("binance", "BUSD", "binance", "binance", "BTCBUSD", "ETHBUSD"),
    ("binance", "TUSD", "binance", "binance", "BTCTUSD", "ETHTUSD"),
    ("binance", "FDUSD", "binance", "binance", "BTCFDUSD", "ETHFDUSD"),
    ("binance", "UST", "binance", "binance", "BTCUST", "ETHUST"),
    ("binance", "USDC", "binance", "binance", "BTCUSDC", None),
    ("binance_us", "USD", "binance-us", "binance_us", "BTCUSD", None),
    ("binance_us", "USDT", "binance-us", "binance_us", "BTCUSDT", None),
    ("bitstamp", "USD", "bitstamp", "bitstamp", "BTCUSD", "ETHUSD"),
    ("bitstamp", "USDT", "bitstamp", "bitstamp", "BTCUSDT", None),
    ("bitstamp", "USDC", "bitstamp", "bitstamp", "BTCUSDC", None),
    ("coinbase", "USD", "coinbase", "coinbase", "BTCUSD", "ETHUSD"),
    ("bitfinex", "USD", "bitfinex", "bitfinex", "BTCUSD", "ETHUSD"),
)
# (base, quote, venue, manifest venue, raw dir, pair)
SIDE = (
    ("TUSD", "USDT", "binance", "binance", "binance", "TUSDUSDT"),
    ("FDUSD", "USDT", "binance", "binance", "binance", "FDUSDUSDT"),
    ("BUSD", "USDT", "binance", "binance", "binance", "BUSDUSDT"),
    ("UST", "USDT", "binance", "binance", "binance", "USTUSDT"),
    ("USDC", "USDT", "binance", "binance", "binance", "USDCUSDT"),
    ("USDT", "USD", "binance_us", "binance-us", "binance_us", "USDTUSD"),
    ("USDC", "USD", "binance_us", "binance-us", "binance_us", "USDCUSD"),
    ("TUSD", "USD", "binance_us", "binance-us", "binance_us", "TUSDUSD"),
    ("USDT", "USD", "bitstamp", "bitstamp", "bitstamp", "USDTUSD"),
    ("USDC", "USD", "bitstamp", "bitstamp", "bitstamp", "USDCUSD"),
)
BINANCE_LIKE = ("binance", "binance-us")


@dataclass(frozen=True)
class Episode:
    name: str
    split: str  # "dev" | "test"
    windows: tuple[tuple[str, str], ...]  # (first UTC day, last UTC day inclusive); each window is one fuser call
    calm: bool = False  # placebo episode: rel_e must stay <= 1.02

    def bounds(self) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
        return [(pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC") + pd.Timedelta(hours=23)) for a, b in self.windows]

    def load_bounds(self) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
        return [(lo - pd.Timedelta(hours=WARMUP_HOURS), hi) for lo, hi in self.bounds()]


EPISODES: tuple[Episode, ...] = (  # fixed 2026-10-21, before any result (autoresearch/program_stable.md)
    Episode("S1", "dev", (("2022-05-01", "2022-05-31"),)),
    Episode("S2", "dev", (("2022-11-01", "2022-11-30"),)),
    Episode("S3", "dev", (("2023-02-01", "2023-02-28"),), calm=True),
    Episode("X1", "test", (("2023-03-08", "2023-03-20"),)),
    Episode("X2", "test", (("2024-01-01", "2024-01-31"),)),
    Episode("X3", "test", (("2025-04-01", "2025-04-30"),)),
    Episode("X4", "test", (("2023-12-01", "2023-12-31"), ("2025-02-01", "2025-03-31")), calm=True),
)


def episodes_for(mode: str, episodes: tuple[Episode, ...] = EPISODES) -> tuple[Episode, ...]:
    if mode not in ("dev", "final"):
        raise ValueError(mode)
    want = "dev" if mode == "dev" else "test"
    return tuple(e for e in episodes if e.split == want)


def grid() -> pd.DatetimeIndex:
    return pd.date_range(GRID_START, GRID_END, freq="h", tz="UTC", name="timestamp_utc")


def needed_months(episodes: tuple[Episode, ...] = EPISODES) -> list[str]:
    out: set[str] = set()
    for e in episodes:
        for lo, hi in e.load_bounds():
            out |= {p.strftime("%Y-%m") for p in pd.period_range(lo.tz_convert(None), hi.tz_convert(None), freq="M")}
    return sorted(out)


def market_key(venue: str, unit: str) -> str:
    return f"{venue}.{unit}"


def side_key(base: str, quote: str, venue: str) -> str:
    return f"{base}.{quote}@{venue}"


# ---------------------------------------------------------------- loading

def _hourly(close: pd.Series, volume: pd.Series) -> pd.DataFrame:
    traded = volume > 0
    px, vol = close[traded], volume[traded]
    hour = px.index.floor("h")
    return pd.DataFrame({"p": np.log(px.where(px > 0)).groupby(hour).last(), "v": vol.groupby(hour).sum()})


def _binance_hourly(directory: Path, venue: str, pair: str, months: list[str],
                    records: dict[tuple[str, str], dict[str, Any]]) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Hourly (log last traded close, volume) from Binance.com / Binance.US monthly zips whose SHA-256 matches the manifest."""
    parts, hashes, missing = [], [], []
    for m in months:
        f = directory / f"{pair}-1m-{m}.zip"
        if not f.is_file():
            missing.append(m)
            continue
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        rec = records.get((venue, f.name))
        if rec is None or rec["sha256"] != digest:
            raise ValueError(f"{f.name} does not match its recorded manifest hash ({venue})")
        with zipfile.ZipFile(f) as zf:
            members = [n for n in zf.namelist() if n.endswith(".csv")]
            if len(members) != 1:
                raise ValueError(f"{f.name}: expected one CSV member")
            frame = parse_kline_csv(zf.read(members[0]).decode("utf-8")).frame
        hashes.append(f"{f.name}:{digest}")
        parts.append(_hourly(frame["close"], frame["volume"]))
    frame = pd.concat(parts).sort_index() if parts else pd.DataFrame(columns=["p", "v"])
    return frame, hashes, missing


def _candle_hourly(raw: Path, directory: str, venue: str, pair: str, months: list[str],
                   manifest: Path) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Hourly frame from the self-hashed minute CSVs (Bitstamp, Coinbase, Bitfinex); hash checked inside the loader."""
    parts, hashes, missing = [], [], []
    for m in months:
        for folder in (directory, directory + "_stable"):  # round-3 files sit apart so older analyses' globs are unchanged
            try:
                g, prov = load_venue_months(raw / folder, pair, "x", manifest, venue, [m])
                break
            except FileNotFoundError:
                continue
        else:
            missing.append(m)
            continue
        hashes += [f"{f['file']}:{f['sha256']}" for f in prov["files"]]
        traded = g["x_traded"].astype(bool)
        parts.append(_hourly(g["x_close"].astype(float).where(traded), g["x_volume"].astype(float).where(traded)))
    frame = pd.concat(parts).sort_index() if parts else pd.DataFrame(columns=["p", "v"])
    return frame, hashes, missing


def _read(raw: Path, directory: str, venue: str, pair: str, months: list[str], records: dict[tuple[str, str], dict[str, Any]],
          manifest: Path) -> tuple[pd.DataFrame, list[str], list[str]]:
    if venue in BINANCE_LIKE:
        return _binance_hourly(raw / directory, venue, pair, months, records)
    return _candle_hourly(raw, directory, venue, pair, months, manifest)


def clean_series(frame: pd.DataFrame, counts: dict[str, Any]) -> pd.DataFrame:
    """Round-2 rules 2 and 3 on a (p, v) hourly frame, on this panel's grid; mutates ``counts``."""
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


def _kraken_hourly(pair: str, raw: Path = KX.KRAKEN) -> pd.DataFrame:
    x = pd.read_csv(raw / f"{pair}_1.csv", header=None, names=["t", "o", "h", "l", "c", "v", "n"], usecols=["t", "c", "v"])
    x = x[(x["c"] > 0) & (x["v"] > 0)]
    x.index = pd.to_datetime(x.pop("t"), unit="s", utc=True)
    x = x.sort_index()
    x = x[(x.index >= grid()[0]) & (x.index <= grid()[-1] + pd.Timedelta(hours=1))]
    hour = x.index.floor("h")
    return pd.DataFrame({"p": np.log(x["c"]).groupby(hour).last(), "v": x["v"].groupby(hour).sum()})


def build(raw: Path = RAW, manifest: Path = MANIFEST, months: list[str] | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    months = months or needed_months()
    records = AP._manifest_records(manifest)
    cols: dict[str, pd.Series] = {}
    meta: dict[str, Any] = {"build_version": BUILD_VERSION, "cleaning": {"spike_log_threshold": SPIKE}, "months_read": months,
                            "markets": [], "side": [], "series": {}, "missing_months": {}, "source_files": {}}

    def add(key: str, frame: pd.DataFrame, note: str, hashes: list[str], missing: list[str], volume: bool = True) -> None:
        counts: dict[str, Any] = {"source": note}
        s = clean_series(frame, counts)
        counts["first_utc"] = str(s["p"].first_valid_index())
        counts["last_utc"] = str(s["p"].last_valid_index())
        meta["series"][key] = counts
        meta["source_files"][key] = hashes
        meta["missing_months"][key] = missing
        cols[key] = s["p"]
        if volume:
            cols[key + "_vol"] = s["v"]

    for venue, unit, mvenue, directory, btc, eth in MARKETS:
        meta["markets"].append({"key": market_key(venue, unit), "venue": venue, "unit": unit})
        for item, pair in (("BTC", btc), ("ETH", eth)):
            if pair is None:
                continue
            frame, hashes, missing = _read(raw, directory, mvenue, pair, months, records, manifest)
            if not hashes:
                continue  # the pair has no held file in any needed month (e.g. no ETH leg): no column
            add(f"{market_key(venue, unit)}|{item}", frame, f"{mvenue} {pair} 1m -> last traded close per hour", hashes, missing)
    for base, quote, venue, mvenue, directory, pair in SIDE:
        frame, hashes, missing = _read(raw, directory, mvenue, pair, months, records, manifest)
        if not hashes:
            continue
        meta["side"].append({"key": side_key(base, quote, venue), "base": base, "quote": quote, "venue": venue})
        add("side|" + side_key(base, quote, venue), frame, f"{mvenue} {pair} 1m -> last traded close per hour", hashes, missing,
            volume=False)
    meta["kraken_file_sha256"] = KX.verify(manifest, KX.KRAKEN)
    add(f"{REFERENCE}|BTC", _kraken_hourly("XBTUSD"), "kraken ohlcvt XBTUSD 1m -> last traded close per hour", [], [], volume=False)
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


def load_panel(mode: str, path: Path = PANEL_PATH, episodes: tuple[Episode, ...] = EPISODES,
               ) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, pd.Series, dict[str, Any]]:
    """(markets, side, reference, meta). Only rows inside the mode's episode windows (plus warm-up) are read from disk:
    dev mode never reads a test row. ``markets`` maps ``venue.UNIT`` to a frame with BTC, BTC_vol (and ETH, ETH_vol),
    ``side`` holds the ``BASE.QUOTE@venue`` log rates, ``reference`` is Kraken BTC/USD (harness only)."""
    ensure(path)
    eps = episodes_for(mode, episodes)
    ranges = [b for e in eps for b in e.load_bounds()]
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
    markets: dict[str, pd.DataFrame] = {}
    for c in want:
        head, item = c.split("|", 1)
        if head in (REFERENCE, "side"):
            continue
        markets.setdefault(head, pd.DataFrame(index=frame.index))[item] = frame[c]
    side = frame[[c for c in want if c.startswith("side|")]].rename(columns=lambda c: c.split("|", 1)[1])
    ref = frame[f"{REFERENCE}|BTC"]
    meta = json.loads(path.with_name(META_PATH.name).read_text())
    return markets, side, ref, meta


def availability(path: Path = PANEL_PATH, episodes: tuple[Episode, ...] = EPISODES) -> list[str]:
    """Diagnostic: hours with a BTC (and ETH) price per market inside each episode window and in its warm-up. Counts only: no
    price, error or fusion output is computed, so it can describe the test episodes without scoring them."""
    ensure(path)
    names = pq.read_schema(path).names
    cols = [n for n in names if n.endswith("|BTC") and not n.startswith(REFERENCE) or n.endswith("|ETH")]
    ref_col = f"{REFERENCE}|BTC"
    frame = pd.read_parquet(path, columns=cols + [ref_col] + ["timestamp_utc"])
    if "timestamp_utc" in frame.columns:
        frame = frame.set_index("timestamp_utc")
    out = []
    for e in episodes:
        for k, ((lo, hi), (wlo, _)) in enumerate(zip(e.bounds(), e.load_bounds())):
            win = (frame.index >= lo) & (frame.index <= hi)
            warm = (frame.index >= wlo) & (frame.index < lo)
            n = int(win.sum())
            out.append(f"{e.name}[{k}] ({e.split}) window {lo:%Y-%m-%d}..{hi:%Y-%m-%d} hours={n} warm-up hours={int(warm.sum())}")
            for key in sorted(c.split("|")[0] for c in cols if c.endswith("|BTC")):
                btc, eth = f"{key}|BTC", f"{key}|ETH"
                wb = int(frame.loc[win, btc].notna().sum()) if btc in frame else 0
                if wb == 0 and not frame.loc[warm, btc].notna().any():
                    continue
                we = int(frame.loc[win, eth].notna().sum()) if eth in frame else 0
                out.append(f"    {key:18} BTC={wb:5d} ETH={we:5d} warm-up BTC={int(frame.loc[warm, btc].notna().sum()):4d}")
            out.append(f"    {REFERENCE:18} (reference) BTC={int(frame.loc[win, ref_col].notna().sum()):5d}")
    return out


if __name__ == "__main__":
    import sys

    if "--availability" in sys.argv:
        print("\n".join(availability()))
    else:
        ensure(rebuild=True)
        print(f"wrote {PANEL_PATH}")
