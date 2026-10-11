"""Amendment A4: pre-registered UST series continuation, executed exactly as registered.

Series = Binance USTUSDT up to its last minute, then Binance USTCBUSD from its first
minute, converted to USD with BUSD/USDT (Binance) x USDT/USD (Binance.US). Minutes
between the two series stay missing. The registered event windows are unchanged.
The result is written to reports/events/E2022-05-UST-COLLAPSE_a4_splice.json and the
registry status follows the same fixed rules as every other event.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .registry import load_registry
from .runner import load_binance_months, run_event

EVENT_ID = "E2022-05-UST-COLLAPSE"


def preconditions(ustusdt: pd.DataFrame, ustcbusd: pd.DataFrame, busdusdt: pd.DataFrame,
                  usdtusd: pd.DataFrame, recovery: tuple[pd.Timestamp, pd.Timestamp]) -> dict[str, Any]:
    first_c = ustcbusd.index[ustcbusd["present"]][0]
    last_u = ustusdt.index[ustusdt["present"]][-1]
    lo, hi = recovery
    cover = lambda f: bool(f.loc[(f.index >= lo) & (f.index < hi), "present"].mean() >= 0.5)
    return {
        "a_rename_documented": {"passes": True, "evidence": "Binance rename announced 2022-05-26; USTC/BUSD trading "
                                "opened 2022-05-30 09:30 UTC; 1 UST = 1 USTC (secondary reports; see docs)"},
        "b_ustc_starts_after_ust_ends": {"passes": bool(first_c > last_u), "ust_last": last_u.isoformat(),
                                         "ustc_first": first_c.isoformat()},
        "c_conversion_legs_cover_recovery": {"passes": cover(busdusdt) and cover(usdtusd)},
    }


def build_series(ustusdt: pd.DataFrame, ustcbusd: pd.DataFrame, busdusdt: pd.DataFrame,
                 usdtusd: pd.DataFrame) -> pd.DataFrame:
    index = ustusdt.index.union(ustcbusd.index)
    u, c = ustusdt.reindex(index), ustcbusd.reindex(index)
    b, t = busdusdt.reindex(index), usdtusd.reindex(index)
    last_u = ustusdt.index[ustusdt["present"]][-1]
    first_c = ustcbusd.index[ustcbusd["present"]][0]
    tr = lambda f: f["traded"].astype("boolean").fillna(False).to_numpy(dtype=bool)
    pre, post = np.asarray(index <= last_u), np.asarray(index >= first_c)
    price = np.full(len(index), np.nan)
    traded = np.zeros(len(index), dtype=bool)
    price[pre] = (u["close"] * t["close"]).to_numpy()[pre]
    traded[pre] = (tr(u) & tr(t))[pre]
    price[post] = (c["close"] * b["close"] * t["close"]).to_numpy()[post]
    traded[post] = (tr(c) & tr(b) & tr(t))[post]
    price, traded = pd.Series(price, index=index), pd.Series(traded, index=index)
    out = pd.DataFrame(index=index)
    out["ust_close"], out["ust_traded"] = price, traded & price.notna()
    out["ust_present"], out["ust_volume"] = price.notna(), traded.astype(float)
    return out


def _grid(directory: Path, symbol: str) -> pd.DataFrame:
    grid, _ = load_binance_months(directory, symbol, "x")
    return grid.rename(columns=lambda col: col[2:])


def main() -> None:
    root = Path(".")
    event = next(e for e in load_registry(root / "configs/event_registry.json") if e["id"] == EVENT_ID)
    ustusdt, ustcbusd = _grid(root / "data/raw/binance", "USTUSDT"), _grid(root / "data/raw/binance", "USTCBUSD")
    busdusdt, usdtusd = _grid(root / "data/raw/binance", "BUSDUSDT"), _grid(root / "data/raw/binance_us", "USDTUSD")
    recovery = (pd.Timestamp("2022-05-14", tz="UTC"), pd.Timestamp("2022-05-21", tz="UTC"))
    gates = preconditions(ustusdt, ustcbusd, busdusdt, usdtusd, recovery)
    result: dict[str, Any] = {"event_id": EVENT_ID, "amendment": "A4", "preconditions": gates,
                              "measured_utc": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%MZ")}
    if all(g["passes"] for g in gates.values()):
        series = build_series(ustusdt, ustcbusd, busdusdt, usdtusd)
        run = run_event(event, series, "ust", "USD")
        result.update(splice_used=True, protocol=run)
    else:
        result.update(splice_used=False, decision="precondition failed; UST not acceptable under R3")
    log_path = root / "reports/events/status_log.json"
    log = json.loads(log_path.read_text()) if log_path.is_file() else []
    covered = result.get("protocol", {}).get("coverage_ok", False)
    log.append({"event_id": EVENT_ID, "old_status": event["status"], "new_status": event["status"],
                "rule": ("A4 splice executed as registered; recovery window uncovered (USTC/BUSD opened 2022-05-30), "
                         "R3 still fails" if result["splice_used"] and not covered else "A4 evaluated"),
                "measured_utc": result["measured_utc"], "report": "reports/events/E2022-05-UST-COLLAPSE_a4_splice.json"})
    log_path.write_text(json.dumps(log, indent=2) + "\n")
    out = root / "reports/events/E2022-05-UST-COLLAPSE_a4_splice.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n")
    print(json.dumps({"preconditions": {k: v["passes"] for k, v in gates.items()},
                      "splice_used": result["splice_used"],
                      "coverage_ok": result.get("protocol", {}).get("coverage_ok"),
                      "recovery_covered_minutes": result.get("protocol", {}).get("windows", {})
                      .get("recovery", {}).get("covered_minutes")}, indent=1))


if __name__ == "__main__":
    main()
