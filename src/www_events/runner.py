"""Run the pre-specified event protocol (R1 + window diagnostics) for one registry event.

Data come only from local, already-acquired artifacts: the audited IAQF panel or
checksum-verified Binance public kline archives. Nothing is downloaded here.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from www_c0.quality import validate_utc_minutes
from www_c3.fragmentation import ar1_to_parity
from www_c3.robustness import horizon_medians

from .binance_klines import gap_summary, read_kline_zip, sha256_file, to_minute_grid, verify_checksum
from .plan_dvs import coverage_gate, covariates, dv1_contrast, dv3_recovery_minutes, dv5_ratio, usdt_stability_gate
from .registry import RULES, _parse_date, analysis_windows, load_registry, r1_severity


def window_bounds(window: Mapping[str, str]) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Inclusive UTC dates -> half-open minute range [start 00:00, day after end 00:00)."""
    start = pd.Timestamp(window["start"], tz="UTC")
    return start, pd.Timestamp(window["end"], tz="UTC") + pd.Timedelta("1D")


def usd_price(stable: pd.DataFrame, s_prefix: str, quote_basis: str,
              quote_usd: pd.DataFrame | None = None, q_prefix: str | None = None) -> pd.DataFrame:
    """Stablecoin price in USD plus a traded mask; USDT-quoted series need a USDT/USD leg or stay relative."""
    out = pd.DataFrame(index=stable.index)
    price = stable[f"{s_prefix}_close"]
    traded = stable[f"{s_prefix}_traded"]
    if quote_basis == "USD":
        out["price"], out["traded"], out["basis"] = price, traded, "USD"
    elif quote_usd is not None and q_prefix is not None:
        q = quote_usd.reindex(stable.index)
        out["price"] = price * q[f"{q_prefix}_close"]
        out["traded"] = traded & q[f"{q_prefix}_traded"].fillna(False).astype(bool)
        out["basis"] = "USD_VIA_" + quote_basis
    else:
        out["price"], out["traded"], out["basis"] = price, traded, quote_basis + "_RELATIVE"
    return out


def window_diagnostics(series: pd.DataFrame, peg: float = 1.0) -> dict[str, Any]:
    traded = series["traded"].fillna(False).astype(bool).to_numpy()
    price = series["price"].to_numpy(dtype=float)
    dev = 10_000 * np.log(price / peg)
    obs = traded & np.isfinite(dev)
    a = np.abs(dev[obs])
    bins = horizon_medians(pd.Series(dev, index=series.index), pd.Series(obs, index=series.index), 15, min_obs=3)
    arr = bins.to_numpy()
    fit = ar1_to_parity(arr, np.isfinite(arr))
    return {
        "grid_minutes": int(len(series)),
        "traded_minutes": int(obs.sum()),
        "mean_dev_bps": float(dev[obs].mean()) if a.size else None,
        "median_abs_dev_bps": float(np.median(a)) if a.size else None,
        "p95_abs_dev_bps": float(np.percentile(a, 95)) if a.size else None,
        "max_abs_dev_bps": float(a.max()) if a.size else None,
        "share_traded_minutes_ge_100bps": float((a >= 100).mean()) if a.size else None,
        "half_life_to_parity_minutes_15m_bins": None if fit.half_life_minutes is None else fit.half_life_minutes * 15,
        "bins_15m": int(np.isfinite(arr).sum()),
        "adjacent_bin_pairs_15m": fit.pairs,
    }


def run_event(event: Mapping[str, Any], stable: pd.DataFrame, s_prefix: str, quote_basis: str,
              quote_usd: pd.DataFrame | None = None, q_prefix: str | None = None,
              btc_close: pd.Series | None = None, wedge: pd.DataFrame | None = None) -> dict[str, Any]:
    windows = analysis_windows(_parse_date(event["reported_window_utc"]["start"]),
                               _parse_date(event["reported_window_utc"]["end"]))
    series = usd_price(stable, s_prefix, quote_basis, quote_usd, q_prefix)
    result: dict[str, Any] = {"event_id": event["id"], "series": s_prefix, "price_basis": str(series["basis"].iloc[0]),
                              "windows": {}, "rules": RULES}
    for name, window in windows.items():
        lo, hi = window_bounds(window)
        part = series[(series.index >= lo) & (series.index < hi)]
        expected = int((hi - lo) / pd.Timedelta("1min"))
        entry: dict[str, Any] = {"dates": window, "expected_minutes": expected, "covered_minutes": int(len(part))}
        entry["coverage_complete"] = entry["covered_minutes"] == expected
        entry["diagnostics"] = window_diagnostics(part) if len(part) else None
        result["windows"][name] = entry
    # R1 is judged over the event window extended by one day on each side (reported dates are approximate).
    lo = window_bounds(windows["event"])[0] - pd.Timedelta("1D")
    hi = window_bounds(windows["event"])[1] + pd.Timedelta("1D")
    ev = series[(series.index >= lo) & (series.index < hi)]
    if len(ev):
        volume = np.where(ev["traded"].fillna(False).astype(bool), 1.0, 0.0)
        result["r1"] = r1_severity(ev.index, ev["price"].to_numpy(dtype=float), volume)
        result["r1"]["judged_range_utc"] = [lo.isoformat(), hi.isoformat()]
    else:
        result["r1"] = None
    result["coverage_ok"] = all(result["windows"][w]["coverage_complete"] for w in ("baseline", "event", "recovery"))
    if series["basis"].iloc[0].endswith("_RELATIVE"):
        result["warning"] = "deviation measured against the quote stablecoin, not USD; R1 is not USD-verified"
    result["plan"] = plan_block(windows, series, stable[f"{s_prefix}_present"], quote_basis, quote_usd, q_prefix,
                                btc_close, wedge)
    return result


def plan_block(windows: Mapping[str, Mapping[str, str]], series: pd.DataFrame, present: pd.Series, quote_basis: str,
               quote_usd: pd.DataFrame | None, q_prefix: str | None, btc_close: pd.Series | None,
               wedge: pd.DataFrame | None = None) -> dict[str, Any]:
    """Pre-analysis-plan quantities (docs/PRE_ANALYSIS_PLAN.md sections 2, 5 and 6)."""
    dev = 10_000 * np.log(series["price"].astype(float))
    traded = series["traded"].fillna(False).astype(bool)
    present = present.reindex(series.index).fillna(False).astype(bool)
    bounds = {name: window_bounds(w) for name, w in windows.items()}

    def part(x: pd.Series, name: str) -> pd.Series:
        lo, hi = bounds[name]
        return x[(x.index >= lo) & (x.index < hi)]

    gates = {name: coverage_gate(part(present, name), int((hi - lo) / pd.Timedelta("1min")))
             for name, (lo, hi) in bounds.items()}
    reference = "control" if gates["control"]["passes"] else "baseline"
    out: dict[str, Any] = {"coverage_gates": gates, "dv1_reference_window": reference,
                           "dv1_reference_is_fallback": reference != "control"}
    if gates["event"]["passes"] and gates[reference]["passes"]:
        out["dv1"] = dv1_contrast(part(dev[traded], "event").to_numpy(), part(dev[traded], reference).to_numpy())
    else:
        out["dv1"] = {"estimate": None, "reason": "coverage gate failed"}
    out["dv3"] = dv3_recovery_minutes(dev, traded, *bounds["event"], bounds["recovery"][1])
    if quote_basis == "USD":
        out["usdt_gate"] = {"passes": True, "reason": "USD-quoted series; gate not applicable"}
    elif quote_usd is not None and q_prefix is not None:
        q = quote_usd.reindex(series.index)
        q_dev = 10_000 * np.log(q[f"{q_prefix}_close"].where(q[f"{q_prefix}_traded"].fillna(False).astype(bool)))
        out["usdt_gate"] = usdt_stability_gate(part(q_dev, "event").to_numpy())
    else:
        out["usdt_gate"] = {"passes": False, "reason": "no quote/USD leg supplied"}
    out["confirmatory_eligible"] = bool(out["dv1"].get("estimate") is not None and out["usdt_gate"]["passes"]
                                        and not str(series["basis"].iloc[0]).endswith("_RELATIVE"))
    if wedge is None:
        out["dv4"] = out["dv5"] = {"estimate": None, "reason": "no triangle legs supplied"}
    else:
        w = wedge.reindex(series.index)
        w_obs = w["observed"].fillna(False).astype(bool)
        w_val = w["wedge_bps"].astype(float)
        if gates["event"]["passes"] and gates[reference]["passes"]:
            out["dv4"] = dv1_contrast(part(w_val[w_obs], "event").to_numpy(), part(w_val[w_obs], reference).to_numpy())
        else:
            out["dv4"] = {"estimate": None, "reason": "coverage gate failed"}
        out["dv5"] = dv5_ratio(part(dev, "event"), part(traded, "event"), part(w_val, "event"), part(w_obs, "event"))
    out["covariates"] = {name: covariates(None if btc_close is None else part(btc_close, name),
                                          part(present, name), part(traded, name)) for name in bounds}
    return out


def analysis_status(event_id: str, eligible: bool, freeze_path: Path = Path("configs/plan_freeze.json")) -> str:
    """EXPLORATORY for events measured before the plan freeze; otherwise CONFIRMATORY only if data-eligible."""
    measured_before = json.loads(freeze_path.read_text())["measured_before_freeze"] if freeze_path.is_file() else []
    if event_id in measured_before:
        return "EXPLORATORY"
    return "CONFIRMATORY" if eligible else "DESCRIPTIVE_ONLY"


def load_iaqf(panel_path: Path, prefix: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    panel = pd.read_parquet(panel_path)
    index = validate_utc_minutes(panel["timestamp_utc"])
    frame = pd.DataFrame(index=index)
    frame[f"{prefix}_close"] = panel[f"{prefix}_close"].to_numpy()
    frame[f"{prefix}_volume"] = panel[f"{prefix}_volume"].to_numpy()
    frame[f"{prefix}_present"] = frame[f"{prefix}_close"].notna()
    frame[f"{prefix}_traded"] = frame[f"{prefix}_volume"].fillna(0) > 0
    return frame, {"source": "iaqf_panel", "sha256": sha256_file(panel_path)}


def load_binance_months(directory: Path, symbol: str, prefix: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load every ``{symbol}-1m-YYYY-MM.zip`` in ``directory``; each must pass its .CHECKSUM."""
    archives = sorted(directory.glob(f"{symbol}-1m-*.zip"))
    if not archives:
        raise FileNotFoundError(f"no {symbol} archives in {directory}")
    frames, manifest = [], []
    for archive in archives:
        digest = verify_checksum(archive, archive.with_name(archive.name + ".CHECKSUM"))
        parsed = read_kline_zip(archive)
        frames.append(parsed.frame)
        manifest.append({"file": archive.name, "sha256": digest, "time_unit": parsed.time_unit,
                         "rows": parsed.rows, "issues": list(parsed.issues)})
    frame = pd.concat(frames).sort_index()
    if frame.index.has_duplicates:
        raise ValueError("overlapping archives")
    grid = to_minute_grid(frame, frame.index[0].floor("D"), frame.index[-1].floor("D") + pd.Timedelta("1D"), prefix)
    return grid, {"source": "binance_vision_monthly_klines", "files": manifest, "gaps": gap_summary(grid, prefix)}


def binance_triangle(directory: Path, coin: str, quote: str = "USDT") -> tuple[pd.DataFrame, dict[str, Any]]:
    """Within-venue triangle W = log BTC/coin + log coin/quote - log BTC/quote from Binance archives.

    The quote currency cancels, so W does not depend on the quote's own USD value. ``observed`` requires a
    traded minute on all three legs; missing minutes stay missing.
    """
    legs = {"btc_coin": f"BTC{coin}", "coin_quote": f"{coin}{quote}", "btc_quote": f"BTC{quote}"}
    frames, prov = {}, {}
    for name, symbol in legs.items():
        prefix = "binance_" + symbol.lower()
        grid, provenance = load_binance_months(directory, symbol, prefix)
        frames[name] = grid.rename(columns=lambda c, p=prefix: c.replace(p + "_", ""))
        prov[symbol] = provenance
    index = frames["btc_coin"].index.intersection(frames["coin_quote"].index).intersection(frames["btc_quote"].index)
    f = {k: v.reindex(index) for k, v in frames.items()}
    wedge = 10_000 * (np.log(f["btc_coin"]["close"]) + np.log(f["coin_quote"]["close"]) - np.log(f["btc_quote"]["close"]))
    observed = f["btc_coin"]["traded"] & f["coin_quote"]["traded"] & f["btc_quote"]["traded"]
    return pd.DataFrame({"wedge_bps": wedge, "observed": observed & wedge.notna()}), prov


def run_from_spec(event: Mapping[str, Any], spec: Mapping[str, Any],
                  freeze_path: Path = Path("configs/plan_freeze.json")) -> dict[str, Any]:
    """Run the protocol for one event from a run spec (shared by the CLI and the batch driver).

    spec: {"source": "iaqf"|"binance", "path": ..., "stable": ..., "quote_basis": ..., optional "quote_usd",
    "btc", "triangle" (IAQF), "triangle_coin" (Binance)}.
    """
    path = Path(spec["path"])
    if spec["source"] == "iaqf":
        stable, prov = load_iaqf(path, spec["stable"])
        quote, qprov = load_iaqf(path, spec["quote_usd"]) if spec.get("quote_usd") else (None, None)
        s_prefix, q_prefix = spec["stable"], spec.get("quote_usd")
        btc = load_iaqf(path, spec["btc"])[0][f"{spec['btc']}_close"] if spec.get("btc") else None
        wedge, wprov = None, None
        if spec.get("triangle"):
            from www_c3.fragmentation import build_wedges
            w = build_wedges(pd.read_parquet(path))
            wedge = pd.DataFrame({"wedge_bps": w[f"{spec['triangle']}_wedge_bps"], "observed": w[f"{spec['triangle']}_fresh"]})
            wprov = {"source": "iaqf_panel", "triangle": spec["triangle"]}
    elif spec["source"] == "binance":
        s_prefix = "binance_" + spec["stable"].lower()
        stable, prov = load_binance_months(path, spec["stable"], s_prefix)
        q_prefix = "binance_" + spec["quote_usd"].lower() if spec.get("quote_usd") else None
        quote, qprov = load_binance_months(path, spec["quote_usd"], q_prefix) if spec.get("quote_usd") else (None, None)
        wedge, wprov = binance_triangle(path, spec["triangle_coin"]) if spec.get("triangle_coin") else (None, None)
        btc_prefix = "binance_" + spec["btc"].lower() if spec.get("btc") else None
        btc = load_binance_months(path, spec["btc"], btc_prefix)[0][btc_prefix + "_close"] if btc_prefix else None
    else:
        raise ValueError(f"unknown source {spec['source']}")
    result = run_event(event, stable, s_prefix, spec["quote_basis"], quote, q_prefix, btc, wedge)
    result["measured_utc"] = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%MZ")
    result["plan"]["analysis_status"] = analysis_status(event["id"], result["plan"]["confirmatory_eligible"],
                                                        freeze_path)
    result["provenance"] = {"stable": prov, "quote_usd": qprov, "triangle": wprov}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("configs/event_registry.json"))
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--iaqf-panel", type=Path)
    src.add_argument("--binance-dir", type=Path)
    parser.add_argument("--stable", required=True, help="IAQF prefix (e.g. bnus_usdcusd) or Binance symbol")
    parser.add_argument("--quote-basis", required=True, choices=["USD", "USDT", "BUSD"])
    parser.add_argument("--quote-usd", help="optional quote/USD series (same source) to convert to USD")
    parser.add_argument("--btc", help="optional BTC/USD series (same source) for the volatility covariate")
    parser.add_argument("--triangle", choices=["usdc", "usdt"], help="IAQF only: within-venue triangle for DV4/DV5")
    parser.add_argument("--triangle-coin", help="Binance only: coin for BTC/coin, coin/USDT, BTC/USDT triangle")
    args = parser.parse_args()
    event = next(e for e in load_registry(args.registry) if e["id"] == args.event_id)
    spec = {"source": "iaqf" if args.iaqf_panel else "binance", "path": args.iaqf_panel or args.binance_dir,
            "stable": args.stable, "quote_basis": args.quote_basis, "quote_usd": args.quote_usd, "btc": args.btc,
            "triangle": args.triangle, "triangle_coin": args.triangle_coin}
    result = run_from_spec(event, spec)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    r1 = result["r1"] or {}
    print(f"{event['id']}: r1_pass={r1.get('r1_pass')} coverage_ok={result['coverage_ok']} basis={result['price_basis']}")


if __name__ == "__main__":
    main()
