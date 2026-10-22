"""Hourly frames for the applied GMM, built from the series the anchor tests already use (all bps, 1e4 log).

Bitfinex stress window (2018-11-27..2019-05-31):  L = Bitfinex BTC vs Bitstamp BTC; D = Bitfinex USTUSD; X = Kraken USDT/USD;
E = Bitfinex ETH vs Coinbase ETH (hourly median of traded minutes); LTC, ETC, BCH = Bitfinex vs Coinbase hourly last-close gaps
from the cached UNIT-TD panel (XLM and XRP on Coinbase cover under half the window and are left out; LINK, SOL, DOGE and ADA
are not listed on Coinbase then).

Binance.US 2023:  L = Binance.US BTC vs Bitstamp BTC; D_USDT, D_USDC the coins' Binance.US USD prices; X_USDT, X_USDC their
Bitstamp USD prices (external).  Binance.US lists no other crypto item in the held files, so instruments are the lags of L.
Bitstamp USDC is held for 2023-02..07 only, so the two-anchor sample is that window.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
PANEL = REPO / "data" / "derived" / "unit_td_panel.parquet"
STRESS = ("2018-11-27", "2019-05-31")
ALTS = ("LTC", "ETC", "BCH")


def _cut(x, lo: str, hi: str):
    return x[(x.index >= pd.Timestamp(lo, tz="UTC")) & (x.index < pd.Timestamp(hi, tz="UTC") + pd.Timedelta(days=1))]


def bitfinex_frame() -> pd.DataFrame:
    from www_auto import anchor_external as ae

    s = ae.load_series()["series"]
    panel = pd.read_parquet(PANEL)
    f = pd.DataFrame({"L": 1e4 * (s["bitfinex|BTC"] - s["bitstamp|BTC"]), "D": 1e4 * s["bitfinex|USDT"],
                      "X": 1e4 * s["kraken|USDT"], "E": 1e4 * (s["bitfinex|ETH"] - s["coinbase|ETH"])})
    for a in ALTS:
        f[a] = 1e4 * (panel[f"bitfinex|{a}"] - panel[f"coinbase|{a}"]).reindex(f.index)
    return _cut(f, *STRESS)


def binance_us_frame(raw: Path | None = None) -> pd.DataFrame:
    from www_events.bitstamp import load_months
    from www_events.runner import load_binance_months
    from www_rescue.decompose import components
    from www_rescue.platform_dollar import traded_log_close

    raw = raw or REPO / "data" / "raw"
    manifest = REPO / "reports" / "events" / "acquisition_manifest.json"
    bus = lambda sym: traded_log_close(load_binance_months(raw / "binance_us", sym, "x")[0], "x")  # noqa: E731
    bst = lambda pair: traded_log_close(load_months(raw / "bitstamp", pair, "y", manifest)[0], "y")  # noqa: E731
    btc_v, btc_r = bus("BTCUSD"), bst("BTCUSD")
    t = components(bus("USDTUSD"), btc_v, btc_r, bst("USDTUSD"))
    c = components(bus("USDCUSD"), btc_v, btc_r, bst("USDCUSD"))
    f = pd.DataFrame({"L": t["L"], "D_USDT": t["D"], "X_USDT": t["D_ref"], "D_USDC": c["D"], "X_USDC": c["D_ref"]})
    return _cut(f, "2023-01-01", "2023-12-31")


def complete(f: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    return f[cols].dropna()


def add_lags(f: pd.DataFrame, col: str, lags: tuple[int, ...]) -> pd.DataFrame:
    """Lags of col by whole hours on the hourly index (shift by time, not by row, so gaps give NaN)."""
    g = f.copy()
    for k in lags:
        g[f"{col}_l{k}"] = f[col].reindex(f.index - pd.Timedelta(hours=k)).to_numpy()
    return g
