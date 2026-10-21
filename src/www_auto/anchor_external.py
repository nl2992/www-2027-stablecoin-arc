"""External-price anchor test: does the Bitfinex USDT residual equal USDT's own deviation measured on Kraken?

anchor.py finds that Bitfinex's USDT/USD price D follows the BTC gap L with slope below 1 in the 2019 stress. If USDT itself
traded below par at that time (a token effect, not Bitfinex's dollar), the shortfall T = D - L should equal USDT's own
deviation X, measured on a venue whose dollar is ordinary:
  X = 1e4 log P_Kraken(USDT/USD)                            (USDT in Kraken's dollars)
  L = 1e4 [log P_bfx(BTC/USD) - log P_bst(BTC/USD)]          (as in anchor.py)
  D = 1e4 log P_bfx(USDT/USD),   T = D - L
Hypothesis: T = X, so D - X = L + noise and the slope of (D - X) on L is 1. The same slope is estimated with the Bitfinex ETH
gap against Coinbase (E) as an instrument for L (E - L shares no BTC-specific noise with L). Kraken's BTC gap against
Bitstamp, K = 1e4 [log P_kr(BTC/USD) - log P_bst(BTC/USD)], shows whether Kraken's dollar was ordinary.

Kraken series come from the 1-minute OHLCVT bundle (candles exist only for traded minutes); the hourly value is the median of
traded-minute log closes, as in probe.py. Slices are those of anchor.py (stress window, then each year). On hourly medians and
on daily medians (of hours where every series of the sample exists) each slice reports OLS slopes with weekly and monthly
block-bootstrap 95% intervals (1,000 draws, seed 20261020), the medians of T, X and T - X over hours with |L| >= 50 bps,
corr(T, X) and the IV slope.

    uv run python -m www_auto.anchor_external             # writes reports/unit_td/anchor_external.json
    uv run python -m www_auto.anchor_external --register  # (re)writes the kraken-ohlcvt records in the acquisition manifest
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import anchor, probe

REPO = probe.REPO
KRAKEN = REPO / "data" / "raw" / "kraken_ohlcvt"
OUTPUT = REPO / "reports" / "unit_td" / "anchor_external.json"
MANIFEST = probe.MANIFEST
VENUE = "kraken-ohlcvt"
PAIRS = ("USDTUSD", "XBTUSD", "ETHUSD")
INTERVALS = (1, 60)
SLICES = anchor.BFX_SLICES
STRESS = anchor.STRESS
BIG_BPS, DRAWS, SEED, MIN_DAYS = anchor.BIG_BPS, anchor.DRAWS, anchor.SEED, anchor.MIN_DAYS
SOURCE_URL = "https://assets.kraken.com/marketing/institutions/Kraken_OHLCVT_Full.zip.part00..part04"
ARCHIVE_SHA256 = "bc273e9027470b07d790a7fa4df9bb43f0dfc527c20c6ecae48402e123e7b1c7"
ARCHIVE_BYTES = 9546553626
AUTH = ("User authorization 2026-10-20 (decision D15): download Kraken's free OHLCVT bundle from assets.kraken.com, linked from "
        "Kraken's support page, and extract USDTUSD, XBTUSD and ETHUSD at 1 and 60 minutes; no paid or authenticated access.")
TERMS = ("Public bulk download linked from Kraken's support page; provider terms of use apply; raw files are not redistributed "
         "in this repository.")


# ---- data ------------------------------------------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def _read(path: Path) -> pd.DataFrame:
    x = pd.read_csv(path, header=None, names=["t", "o", "h", "l", "c", "v", "n"], usecols=["t", "c", "v", "n"])
    x.index = pd.to_datetime(x.pop("t"), unit="s", utc=True)
    return x.sort_index()


def verify(manifest: Path = MANIFEST, raw: Path = KRAKEN) -> dict[str, str]:
    """sha256 of every extracted file against the manifest record; returns {file name: sha256}."""
    recs = {r["file"]: r for r in json.loads(manifest.read_text())["records"] if r["venue"] == VENUE and r.get("interval")}
    out = {}
    for p in PAIRS:
        for i in INTERVALS:
            f = raw / f"{p}_{i}.csv"
            rec = recs[f"data/raw/kraken_ohlcvt/{f.name}"]
            got = sha256_file(f)
            if got != rec["sha256"]:
                raise ValueError(f"{f.name}: sha256 {got} does not match the manifest {rec['sha256']}")
            out[f.name] = got
    return out


def hourly_log_close(pair: str, raw: Path = KRAKEN) -> tuple[pd.Series, pd.Series]:
    """Hourly median of traded-minute log closes (probe.py convention) and the count of traded minutes per hour."""
    x = _read(raw / f"{pair}_1.csv")
    x = x[x["c"] > 0]
    idx = pd.date_range(f"{probe.START}-01", "2023-12-31 23:00", freq="h", tz="UTC", name="timestamp_utc")
    med = np.log(x["c"]).groupby(x.index.floor("h")).median().reindex(idx)
    cnt = x["c"].groupby(x.index.floor("h")).size().reindex(idx).fillna(0).astype(int)
    return med, cnt


def load_series(raw: Path = KRAKEN) -> dict[str, Any]:
    s = anchor.load_series()
    kr = {f"kraken|{a}": hourly_log_close(p, raw) for a, p in (("USDT", "USDTUSD"), ("BTC", "XBTUSD"), ("ETH", "ETHUSD"))}
    s.update({k: v[0] for k, v in kr.items()})
    return {"series": s, "minutes": {k: v[1] for k, v in kr.items()}}


# ---- statistics ------------------------------------------------------------------------------------------------------

def _ols(x: np.ndarray, y: np.ndarray) -> float:
    return anchor._slope(x, y)


def _iv(z: np.ndarray, x: np.ndarray, y: np.ndarray) -> float:
    zc = z - z.mean()
    den = float((zc * (x - x.mean())).sum())
    return float((zc * (y - y.mean())).sum() / den) if abs(den) > 0 else float("nan")


def block_ci(df: pd.DataFrame, fn, freq: str, draws: int = DRAWS, seed: int = SEED) -> list[float] | None:
    """95% interval of fn(array of df columns) resampling whole calendar blocks (freq 'W' or 'M'); the seed and resampling
    rule are those of anchor.slope_ci, so the weekly interval of the plain daily slope reproduces anchor.json."""
    blocks = [g.to_numpy() for _, g in df.groupby(df.index.tz_localize(None).to_period(freq))]
    if len(blocks) < 5:
        return None
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(draws):
        m = np.concatenate([blocks[i] for i in rng.integers(0, len(blocks), len(blocks))])
        out.append(fn(m))
    lo, hi = np.nanpercentile(out, [2.5, 97.5])
    return [float(lo), float(hi)]


def _est(df: pd.DataFrame, cols: tuple[str, ...], fn, point: float | None = None) -> dict[str, Any]:
    d = df[list(cols)]
    return {"est": float(fn(d.to_numpy())) if point is None else point, "ci95_week": block_ci(d, fn, "W"),
            "ci95_month": block_ci(d, fn, "M")}


def level_stats(h: pd.DataFrame, daily: bool) -> dict[str, Any]:
    """Slopes of D and D-X on L, and the IV slope, on the frame h (columns L, D, X, E) at one frequency."""
    out: dict[str, Any] = {"n": int(len(h))}
    if len(h) < (MIN_DAYS if daily else 24) or h["L"].std() == 0:
        return out
    h = h.assign(A=h["D"] - h["X"])
    out["slope_D_on_L"] = _est(h, ("L", "D"), lambda m: _ols(m[:, 0], m[:, 1]))
    out["slope_D_minus_X_on_L"] = _est(h, ("L", "A"), lambda m: _ols(m[:, 0], m[:, 1]))
    out["slope_X_on_L"] = _est(h, ("L", "X"), lambda m: _ols(m[:, 0], m[:, 1]))
    if "E" in h and h["E"].notna().all() and h["E"].std() > 0:
        out["iv_slope_D_on_L"] = _est(h, ("E", "L", "D"), lambda m: _iv(m[:, 0], m[:, 1], m[:, 2]))
        out["iv_slope_D_minus_X_on_L"] = _est(h, ("E", "L", "A"), lambda m: _iv(m[:, 0], m[:, 1], m[:, 2]))
        out["first_stage_slope_L_on_E"] = _ols(h["E"].to_numpy(), h["L"].to_numpy())
    return out


def slice_stats(L: pd.Series, D: pd.Series, X: pd.Series, E: pd.Series) -> dict[str, Any]:
    """All statistics for one slice, on hourly and daily medians."""
    out: dict[str, Any] = {}
    samples = {"anchor_LD": pd.concat([L.rename("L"), D.rename("D")], axis=1).dropna(),
               "adjusted_LDX": pd.concat([L.rename("L"), D.rename("D"), X.rename("X")], axis=1).dropna(),
               "iv_LDXE": pd.concat([L.rename("L"), D.rename("D"), X.rename("X"), E.rename("E")], axis=1).dropna()}
    a = samples["anchor_LD"]
    out["hours_LD"], out["hours_LDX"], out["hours_LDXE"] = (int(len(samples[k])) for k in samples)
    if len(a) >= 24:
        d = a.groupby(a.index.floor("D")).median()
        out["reproduce_anchor_daily"] = {"slope": float(_ols(d["L"].to_numpy(), d["D"].to_numpy())) if len(d) >= MIN_DAYS else None,
                                         "ci95_week": anchor.slope_ci(d) if len(d) >= MIN_DAYS else None, "days": int(len(d))}
    for key, h in (("adjusted_LDX", samples["adjusted_LDX"]), ("iv_LDXE", samples["iv_LDXE"])):
        if len(h) < 24:
            continue
        daily = h.groupby(h.index.floor("D")).median()
        out[key] = {"hourly": level_stats(h, daily=False), "daily": level_stats(daily, daily=True)}
    h = samples["adjusted_LDX"]
    if len(h) >= 24:
        h = h.assign(T=h["D"] - h["L"])
        h["TmX"] = h["T"] - h["X"]
        out["corr_T_X_hourly"] = float(h["T"].corr(h["X"])) if h["T"].std() > 0 and h["X"].std() > 0 else None
        daily = h.groupby(h.index.floor("D")).median()
        out["corr_T_X_daily"] = float(daily["T"].corr(daily["X"])) if len(daily) >= MIN_DAYS and daily["X"].std() > 0 else None
        b = h[h["L"].abs() >= BIG_BPS]
        out["hours_big"] = int(len(b))
        if len(b):
            out.update({"median_L": float(b["L"].median()), "median_T": float(b["T"].median()), "median_X": float(b["X"].median()),
                        "median_T_minus_X": float(b["TmX"].median()),
                        "corr_T_X_big_hours": float(b["T"].corr(b["X"])) if len(b) > 2 and b["X"].std() > 0 else None})
    return out


def kraken_gap(K: pd.Series) -> dict[str, Any]:
    k = K.dropna()
    if len(k) < 24:
        return {"hours": int(len(k))}
    return {"hours": int(len(k)), "median": float(k.median()), "median_abs": float(k.abs().median()),
            "p05": float(k.quantile(0.05)), "p95": float(k.quantile(0.95)),
            "share_abs_ge_50": float((k.abs() >= BIG_BPS).mean()), "max_abs": float(k.abs().max())}


def coverage(med: pd.Series, minutes: pd.Series, lo: str, hi: str, bfx_d: pd.Series) -> dict[str, Any]:
    """Traded hours, gaps (runs of untraded hours), traded minutes and the overlap with Bitfinex USDT, in the window."""
    m, c, d = anchor._cut(med, lo, hi), anchor._cut(minutes, lo, hi), anchor._cut(bfx_d, lo, hi)
    traded = m.notna()
    runs, run = [], 0
    for t in traded.to_numpy():
        if not t:
            run += 1
        elif run:
            runs.append(run)
            run = 0
    if run:
        runs.append(run)
    by_month = traded.groupby(traded.index.tz_localize(None).to_period("M")).agg(["sum", "size"])
    return {"window": [lo, hi], "hours_in_window": int(len(m)), "hours_traded": int(traded.sum()),
            "share_hours_traded": float(traded.mean()), "traded_minutes": int(c.sum()),
            "median_minutes_per_traded_hour": float(c[traded].median()), "untraded_gap_runs": len(runs),
            "longest_untraded_gap_hours": int(max(runs)) if runs else 0, "days_with_no_trade": int((traded.groupby(traded.index.floor("D")).sum() == 0).sum()),
            "hours_traded_and_bitfinex_usdt": int((traded & d.notna()).sum()),
            "traded_hours_by_month": {str(p): [int(a), int(b)] for p, (a, b) in by_month.iterrows()},
            "first_trade_utc": str(med.dropna().index.min()) if med.notna().any() else None}


def crosscheck_60min(raw: Path = KRAKEN) -> dict[str, Any]:
    """Hourly median of 1-minute closes against the 60-minute file's close, USDT/USD, stress window (bps)."""
    h, _ = hourly_log_close("USDTUSD", raw)
    s = _read(raw / "USDTUSD_60.csv")
    s = s[s["c"] > 0]
    c60 = np.log(s["c"]).reindex(h.index)
    lo, hi = STRESS
    d = anchor._cut(1e4 * (h - c60), lo, hi).dropna()
    return {"hours": int(len(d)), "median_abs_diff_bps": float(d.abs().median()), "p95_abs_diff_bps": float(d.abs().quantile(0.95)),
            "corr": float(anchor._cut(h, lo, hi).corr(anchor._cut(c60, lo, hi)))}


def build(data: dict[str, Any], raw: Path = KRAKEN, hashes: dict[str, str] | None = None) -> dict[str, Any]:
    s, minutes = data["series"], data["minutes"]
    L = 1e4 * (s["bitfinex|BTC"] - s["bitstamp|BTC"])
    E = 1e4 * (s["bitfinex|ETH"] - s["coinbase|ETH"])
    D = 1e4 * s["bitfinex|USDT"]
    X = 1e4 * s["kraken|USDT"]
    K = 1e4 * (s["kraken|BTC"] - s["bitstamp|BTC"])
    KE = 1e4 * (s["kraken|ETH"] - s["coinbase|ETH"])
    slices = {n: slice_stats(*(anchor._cut(v, lo, hi) for v in (L, D, X, E))) for n, (lo, hi) in SLICES.items()}
    x_levels = {}
    for n, (lo, hi) in SLICES.items():
        x = anchor._cut(X, lo, hi).dropna()
        x_levels[n] = {"hours": int(len(x)), "median": float(x.median()), "p05": float(x.quantile(0.05)),
                       "p95": float(x.quantile(0.95)), "min": float(x.min()), "max": float(x.max())} if len(x) else {"hours": 0}
    return {"method": __doc__.strip().split("\n\n")[0], "big_bps": BIG_BPS,
            "bootstrap": {"draws": DRAWS, "seed": SEED, "blocks": ["week", "month"]},
            "definitions": "X = Kraken USDT/USD; L = Bitfinex BTC vs Bitstamp BTC; D = Bitfinex USTUSD; T = D - L; E = Bitfinex ETH vs "
                           "Coinbase ETH (instrument for L); K = Kraken BTC vs Bitstamp BTC; all 1e4 log, hourly medians of traded-minute closes",
            "source": {"archive": "Kraken_OHLCVT_Full.zip", "archive_sha256": ARCHIVE_SHA256, "archive_bytes": ARCHIVE_BYTES,
                       "files_sha256": hashes or {}},
            "coverage_kraken_usdt_stress": coverage(s["kraken|USDT"], minutes["kraken|USDT"], *STRESS, D),
            "coverage_kraken_usdt_2019": coverage(s["kraken|USDT"], minutes["kraken|USDT"], "2019-01-01", "2019-12-31", D),
            "coverage_kraken_btc_stress": coverage(s["kraken|BTC"], minutes["kraken|BTC"], *STRESS, L),
            "crosscheck_60min_usdt_stress": crosscheck_60min(raw),
            "kraken_usdt_level_X": x_levels,
            "kraken_btc_gap_vs_bitstamp": {n: kraken_gap(anchor._cut(K, lo, hi)) for n, (lo, hi) in SLICES.items()},
            "kraken_eth_gap_vs_coinbase": {n: kraken_gap(anchor._cut(KE, lo, hi)) for n, (lo, hi) in SLICES.items()},
            "bitfinex_btc_gap_L": {n: kraken_gap(anchor._cut(L, lo, hi)) for n, (lo, hi) in SLICES.items()},
            "slices": slices}


# ---- manifest ----------------------------------------------------------------------------------------------------------

def register(manifest: Path = MANIFEST, raw: Path = KRAKEN) -> int:
    """Replace the kraken-ohlcvt records (keeping every other record) with one per extracted file plus the archive."""
    m = json.loads(manifest.read_text())
    keep = [r for r in m["records"] if r["venue"] != VENUE]
    new = [{"venue": VENUE, "symbol": "Kraken_OHLCVT_Full.zip", "month": "full history", "url": SOURCE_URL,
            "status": "VERIFIED", "file": "(deleted after extraction)", "bytes": ARCHIVE_BYTES, "sha256": ARCHIVE_SHA256,
            "hash_kind": "published by Kraken on its support page for the joined five-part archive; verified after download",
            "note": "archive deleted after extracting the three pairs below", "terms_note": TERMS, "authorization": AUTH}]
    for p in PAIRS:
        for i in INTERVALS:
            f = raw / f"{p}_{i}.csv"
            x = _read(f)
            new.append({"venue": VENUE, "symbol": p, "interval": i, "month": "full history",
                        "url": SOURCE_URL, "status": "VERIFIED", "file": f"data/raw/kraken_ohlcvt/{f.name}",
                        "bytes": f.stat().st_size, "sha256": sha256_file(f),
                        "hash_kind": "self-recorded after extraction from the checksum-verified archive",
                        "rows": int(len(x)), "first_utc": x.index.min().strftime("%Y-%m-%dT%H:%MZ"),
                        "last_utc": x.index.max().strftime("%Y-%m-%dT%H:%MZ"), "terms_note": TERMS, "authorization": AUTH})
    m["records"] = keep + new
    m["summary"] = {s: sum(r["status"] == s for r in m["records"]) for s in ("VERIFIED", "NOT_AVAILABLE", "CHECKSUM_FAILED")}
    manifest.write_text(json.dumps(m, indent=1) + "\n")
    print(f"WROTE {len(new)} {VENUE} records to {manifest}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="www_auto.anchor_external")
    ap.add_argument("--out", type=Path, default=OUTPUT)
    ap.add_argument("--register", action="store_true", help="write the kraken-ohlcvt manifest records and exit")
    args = ap.parse_args(argv)
    if args.register:
        return register()
    hashes = verify()
    result = build(load_series(), hashes=hashes)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(f"WROTE {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
