"""Bitfinex and Coinbase candle adapters and the ledger panel, on synthetic data; no network."""

import json

import numpy as np
import pandas as pd

from www_events.bitstamp import month_bounds, save_month
from www_events.candles import fetch_bitfinex_month, fetch_coinbase_month, load_venue_months
from www_rescue.ledger_panel import predictions


def fake_bitfinex(skip=()):
    def get(url):
        start = int(url.split("start=")[1].split("&")[0]) // 1000
        end = int(url.split("end=")[1].split("&")[0]) // 1000
        return [[t * 1000, 1.0, 2.0, 3.0, 0.5, 4.0] for t in range(start, min(start + 600_000, end + 1), 60)
                if t not in skip]
    return get


def fake_coinbase():
    def get(url):
        start = pd.Timestamp(url.split("start=")[1].split("&")[0]).value // 10**9
        end = pd.Timestamp(url.split("end=")[1]).value // 10**9
        return [[t, 0.5, 3.0, 1.0, 2.0, 4.0] for t in range(end, start - 60, -60)]  # newest first, inclusive end
    return get


def test_bitfinex_month_maps_columns_and_pages_without_duplicates():
    lo, hi = month_bounds("2017-02")
    frame, pages = fetch_bitfinex_month("BTCUSD", "2017-02", get=fake_bitfinex(skip={lo + 60}), pause=0)
    assert len(frame) == 28 * 1440 - 1 and frame["timestamp"].is_unique
    assert frame["timestamp"].iloc[0] == lo and frame["timestamp"].iloc[-1] == hi - 60
    assert list(frame.iloc[0, 1:]) == [1.0, 3.0, 0.5, 2.0, 4.0]  # open, high, low, close, volume
    assert pages == 5


def test_coinbase_month_covers_every_minute_once():
    lo, hi = month_bounds("2017-02")
    frame, pages = fetch_coinbase_month("BTC-USD", "2017-02", get=fake_coinbase(), pause=0)
    assert len(frame) == 28 * 1440 and frame["timestamp"].is_unique
    assert list(frame.iloc[0, 1:]) == [1.0, 3.0, 0.5, 2.0, 4.0]
    assert pages == 28 * 1440 // 300 + 1


def test_load_venue_months_checks_hash_and_filters_months(tmp_path):
    frames = {}
    for m in ("2017-02", "2017-03"):
        frames[m], _ = fetch_bitfinex_month("BTCUSD", m, get=fake_bitfinex(), pause=0)
    records = []
    for m, f in frames.items():
        path = tmp_path / f"BTCUSD-1m-{m}.csv"
        records.append({"venue": "bitfinex", "status": "VERIFIED", "file": f"data/raw/bitfinex/{path.name}",
                        "sha256": save_month(f, path)})
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps({"records": records}))
    grid, _ = load_venue_months(tmp_path, "BTCUSD", "x", manifest, "bitfinex", ["2017-03"])
    assert grid.index[0] == pd.Timestamp("2017-03-01", tz="UTC") and len(grid) == 31 * 1440
    (tmp_path / "BTCUSD-1m-2017-02.csv").write_text("tampered")
    try:
        load_venue_months(tmp_path, "BTCUSD", "x", manifest, "bitfinex")
    except ValueError as exc:
        assert "manifest hash" in str(exc)
    else:
        raise AssertionError("tampered file was loaded")


def _rows(values):
    return [{"phase": p, "minutes": 100, "median_bps": v} for p, v in values.items()]


def test_predictions_score_agreement_sign_triangle_and_reversion():
    ok = {"corr_hourly": 0.95}
    ep = {"pd_btc": _rows({"pre": 5, "stress": 400, "later": 30}), "pd_eth": _rows({"pre": 4, "stress": 380, "later": 20}),
          "triangle": _rows({"pre": 0, "stress": 3, "later": 1}),
          "identification_btc_eth": {"pre": ok, "stress": ok, "later": ok}}
    s = predictions({"E": ep})["E"]
    assert s == {"stress_phases": ["stress"], "Q1_identification": True, "Q2_triangle": True,
                 "Q3_discount_sign": True, "Q4_reversion": True, "falsified": False}
    ep["pd_eth"] = _rows({"pre": 4, "stress": -50, "later": 20})
    assert predictions({"E": ep})["E"]["falsified"] and not np.isnan(0.0)
