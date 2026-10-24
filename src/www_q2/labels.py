"""Q2 onset labels (autoresearch/program_q2.md). Label source only; no detector is imported or run here.

Onset = first window hour at which |deviation from USD| >= 50 bps for 3 consecutive hours. Deviation, in this order per hour:
  1. Binance.US unit/USD, then Bitstamp unit/USD (where they exist);
  2. USDT only: the Bitfinex netted anchor T = D - L (``www_q1.gate.offset_bps``);
  3. the unit/USDT rate (Binance) chained with USDT/USD (Binance.US, then Bitstamp).
Kraken is never read. An event with no label source, or that never reaches the rule, is unscorable.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from www_q1 import gate as G

from . import common as C

THRESH_BPS, RUN_HOURS = 50.0, 3


def deviation_bps(markets, side: pd.DataFrame, unit: str, panel: str) -> tuple[pd.Series, pd.Series]:
    idx = side.index
    off = pd.Series(np.nan, index=idx)
    src = pd.Series("none", index=idx, dtype=object)

    def fill(series: pd.Series, name: str) -> None:
        use = off.isna() & series.notna()
        off[use], src[use] = series[use], name

    for venue in ("binance_us", "bitstamp"):
        col = f"{unit}.USD@{venue}"
        if col in side:
            fill(1e4 * side[col], venue)
    if unit == "USDT" and panel == "q1":
        fill(G.offset_bps(markets, side, "USDT")[0], "bitfinex_netted_anchor")
    chain = f"{unit}.USDT@binance"
    if chain in side and unit != "USDT":
        usdt = pd.Series(np.nan, index=idx)
        for venue in ("binance_us", "bitstamp"):
            col = f"USDT.USD@{venue}"
            if col in side:
                usdt = usdt.where(usdt.notna(), side[col])
        fill(1e4 * (side[chain] + usdt), "chain_usdt")
    return off, src


def onset(dev: pd.Series, lo: pd.Timestamp, hi: pd.Timestamp) -> pd.Timestamp | None:
    d = dev[(dev.index >= lo) & (dev.index <= hi)]
    ok = (d.abs() >= THRESH_BPS).astype(float).where(d.notna())
    run = ok.rolling(RUN_HOURS).min()  # NaN or a 0 inside the 3-hour run breaks it
    hit = run[run == 1.0]
    if hit.empty:
        return None
    return hit.index[0] - pd.Timedelta(hours=RUN_HOURS - 1)


def build() -> dict:
    cache, out = {}, {}
    for eid, unit, a, b, panel in C.EVENTS:
        if panel not in cache:
            cache[panel] = C.load(panel)
        markets, side = cache[panel]
        lo, hi = C.bounds(a, b)
        dev, src = deviation_bps(markets, side, unit, panel)
        w = (dev.index >= lo) & (dev.index <= hi)
        d, s = dev[w], src[w]
        t = onset(dev, lo, hi) if d.notna().any() else None
        rec = {"unit": unit, "window": [a, b], "panel": panel, "window_hours": int(w.sum()),
               "hours_with_label": int(d.notna().sum()),
               "label_source_hours": {k: int(v) for k, v in s[d.notna()].value_counts().items()},
               "hours_abs_dev_ge_50": int((d.abs() >= THRESH_BPS).sum()),
               "max_abs_dev_bps": float(d.abs().max()) if d.notna().any() else None,
               "onset_utc": str(t) if t is not None else None, "scorable": t is not None}
        if t is None:
            rec["reason"] = "no label source in window" if not d.notna().any() else "never reaches the onset rule"
        out[eid] = rec
    return {"preregistration": "autoresearch/program_q2.md", "rule": "first hour with |dev|>=50 bps for 3 consecutive hours",
            "scorable": [e for e, v in out.items() if v["scorable"]], "events": out,
            "note": "computed from label-source series only; Kraken not read; no detector run"}


if __name__ == "__main__":
    res = build()
    C.OUT_DIR.mkdir(parents=True, exist_ok=True)
    C.LABELS.write_text(json.dumps(res, indent=1) + "\n")
    for e, v in res["events"].items():
        print(e, v["unit"], v["onset_utc"], v["max_abs_dev_bps"], v["label_source_hours"], v.get("reason", ""))
