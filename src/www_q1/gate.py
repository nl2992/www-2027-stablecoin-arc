"""Q1 feasibility gate, exactly as pre-registered in autoresearch/program_q1.md.

Uses only volumes and non-Kraken stablecoin/USD rates; Kraken is never loaded and no fusion error is computed.

  volume share  share of hourly BTC volume (all held markets) quoted in the event's shifted unit
  unit offset   1e4 * log(unit/USD) from, in order: Binance.US USDT/USD, Bitstamp USDT/USD, the Bitfinex netted anchor
                T = D - L (D = Bitfinex USDT/USD, L = Bitfinex BTC/USD minus Bitstamp BTC/USD, both in log). The order is applied hour by
                hour. These are USDT rates: for a BUSD event no listed source exists, so the offset is missing and the event fails.
  S_hi          window hours with share >= 0.5 and |offset| >= 25 bps
  event rule    keep an event with >= 40 S_hi hours; study rule: >= 200 pooled S_hi hours over >= 3 kept events
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import panel as P

REPO = P.REPO
OUT = REPO / "reports" / "q1" / "gate.json"
SHARE_MIN, OFFSET_MIN_BPS = 0.5, 25.0
EVENT_MIN_HOURS, STUDY_MIN_HOURS, STUDY_MIN_EVENTS = 40, 200, 3


def unit_of(key: str) -> str:
    return key.split(".", 1)[1]


def volume_share(markets: dict[str, pd.DataFrame], unit: str) -> pd.Series:
    vols = pd.DataFrame({k: f["BTC_vol"].where(f["BTC"].notna()) for k, f in markets.items() if "BTC_vol" in f})
    tot = vols.sum(axis=1, min_count=1)
    num = vols[[k for k in vols if unit_of(k) == unit]].sum(axis=1, min_count=1)
    return (num / tot).where(tot > 0)


def offset_bps(markets: dict[str, pd.DataFrame], side: pd.DataFrame, unit: str) -> tuple[pd.Series, pd.Series]:
    """(offset in bps, source label per hour). Only USDT has listed sources."""
    idx = side.index
    if unit != "USDT":
        return pd.Series(np.nan, index=idx), pd.Series("none", index=idx)
    bus = 1e4 * side[P.BINANCE_US_USDT.split("|", 1)[1]] if P.BINANCE_US_USDT.split("|", 1)[1] in side else pd.Series(np.nan, index=idx)
    bst = 1e4 * side[P.BITSTAMP_USDT.split("|", 1)[1]] if P.BITSTAMP_USDT.split("|", 1)[1] in side else pd.Series(np.nan, index=idx)
    d = side[P.BITFINEX_USDT.split("|", 1)[1]]
    gap = markets["bitfinex.USD"]["BTC"] - markets["bitstamp.USD"]["BTC"]
    anchor = 1e4 * (d - gap)
    off = bus.copy()
    src = pd.Series(np.where(bus.notna(), "binance_us", "none"), index=idx)
    use = off.isna() & bst.notna()
    off[use], src[use] = bst[use], "bitstamp"
    use = off.isna() & anchor.notna()
    off[use], src[use] = anchor[use], "bitfinex_netted_anchor"
    return off, src


def run(path: Path = P.PANEL_PATH) -> dict:
    markets, side, _, _ = P.load_all(path, with_reference=False)
    events = {}
    for eid, a, b, unit in P.EVENTS:
        lo, hi = pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC") + pd.Timedelta(hours=23)
        win = (side.index >= lo) & (side.index <= hi)
        share = volume_share(markets, unit)[win]
        off, src = offset_bps(markets, side, unit)
        off, src = off[win], src[win]
        hi_mask = (share >= SHARE_MIN) & (off.abs() >= OFFSET_MIN_BPS)
        n = int(hi_mask.sum())
        events[eid] = {
            "window": [a, b], "shifted_unit": unit, "window_hours": int(win.sum()),
            "hours_with_share": int(share.notna().sum()), "hours_with_offset": int(off.notna().sum()),
            "hours_share_ge_0.5": int((share >= SHARE_MIN).sum()), "hours_abs_offset_ge_25": int((off.abs() >= OFFSET_MIN_BPS).sum()),
            "median_share": float(share.median()) if share.notna().any() else None,
            "median_abs_offset_bps": float(off.abs().median()) if off.notna().any() else None,
            "offset_source_hours": {k: int(v) for k, v in src[off.notna()].value_counts().items()},
            "offset_source_used": (src[off.notna()].value_counts().idxmax() if off.notna().any() else "none"),
            "s_hi_hours": n, "kept": bool(n >= EVENT_MIN_HOURS),
        }
    kept = [e for e, v in events.items() if v["kept"]]
    pooled = sum(events[e]["s_hi_hours"] for e in kept)
    proceed = bool(pooled >= STUDY_MIN_HOURS and len(kept) >= STUDY_MIN_EVENTS)
    return {"preregistration": "autoresearch/program_q1.md", "events": events, "kept_events": kept, "pooled_s_hi_hours": pooled,
            "n_kept": len(kept), "proceed": proceed,
            "note": "gate computed from volumes and non-Kraken stablecoin rates only; no fusion error computed"}


if __name__ == "__main__":
    res = run()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    for e, v in res["events"].items():
        print(e, v["s_hi_hours"], v["kept"], v["offset_source_used"], v["median_share"], v["median_abs_offset_bps"])
    print("pooled", res["pooled_s_hi_hours"], "kept", res["kept_events"], "proceed", res["proceed"])
